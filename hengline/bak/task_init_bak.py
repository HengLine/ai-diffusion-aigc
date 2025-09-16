#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动任务监听器模块
功能：
1. 在应用程序启动时只查询一次历史记录
2. 筛选今天未完成且重试未超过3次的任务
3. 根据不同任务状态进行相应处理并加入队列
4. 处理完成后自动结束，不再定时运行 
"""

import os
import sys
import time
from datetime import datetime
from threading import Lock
from typing import Dict, Any

from hengline.task.task_base import TaskBase
from hengline.utils.config_utils import get_task_config, get_comfyui_config
from hengline.utils.log_utils import print_log_exception

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.logger import error, warning, debug, info
from hengline.task.task_manage import task_queue_manager
# 导入邮件发送模块
from hengline.task.task_email import async_send_failure_email
# 导入工作流状态检查器
from hengline.workflow.workflow_status_checker import workflow_status_checker


class StartupTaskListener(TaskBase):
    """启动任务监听器类，只在应用启动时运行一次"""

    def __init__(self):
        """初始化启动任务监听器"""
        super().__init__()
        self.lock = Lock()
        self.processed_tasks_count = 0
        task_config = get_task_config()
        self.task_max_retry = task_config.get('task_max_retry', 3)  # 最大重试次数
        self.task_timeout_seconds = task_config.get('task_timeout_seconds', 7200)  # 最大运行时间（秒）
        self.comfyui_api_url = get_comfyui_config().get('api_url', 'http://127.0.0.1:8188')


        # 加载今天排队中的任务到队列
        queued_tasks_added = 0
        # 获取今天的日期
        today_date = datetime.now().strftime('%Y-%m-%d')

        # 筛选今天且状态为queued的任务
        today_queued_tasks = []
        for task in self.history_tasks.values():
            task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
            if task_date == today_date and task.status == "queued":
                today_queued_tasks.append(task)

        # 按时间戳排序
        today_queued_tasks.sort(key=lambda x: x.timestamp)

        # 将任务加入队列
        for task in today_queued_tasks:
            self.task_queue.put(task)
            queued_tasks_added += 1

        debug(f"已将今天 {queued_tasks_added} 个排队中的任务添加到队列")

    def start(self):
        """启动监听器，处理历史任务"""
        info("=" * 50)
        info("          启动历史任务监听器          ")
        info("=" * 50)

        try:
            # 获取今天的日期
            today_date = datetime.now().strftime('%Y-%m-%d')

            # 加载并处理历史任务
            self._process_historical_tasks(today_date)

            info(f"启动任务监听器处理完成，共处理了 {self.processed_tasks_count} 个任务")
            debug("=" * 50)

        except Exception as e:
            error(f"启动任务监听器执行异常: {str(e)}")

    def _process_historical_tasks(self, today_date: str):
        """处理历史任务
        
        Args:
            today_date: 今天的日期，格式为'YYYY-MM-DD'
        """
        # 获取任务历史的副本，避免长时间持有全局锁
        task_history_copy = {}
        with task_queue_manager.lock:
            debug(f"总任务历史记录数: {len(task_queue_manager.task_history)}")
            # 创建任务历史的副本
            task_history_copy = {task_id: task for task_id, task in task_queue_manager.task_history.items()}

        # 筛选今天未完成且重试未超过最大重试次数的任务
        pending_tasks = []

        # 在锁外处理任务筛选
        for task_id, task in task_history_copy.items():
            # 检查是否为今天的任务
            task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
            if task_date != today_date:
                continue

            # 检查是否未完成（状态为queued、failed或running）
            if task.status not in ['queued', 'failed', 'running']:
                continue

            # 检查重试次数是否未超过最大重试次数
            if task.execution_count > self.task_max_retry:
                warning(f"任务 {task_id} 重试次数已超过{self.task_max_retry}次，跳过处理")
                continue

            # 构建任务信息字典
            task_info = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'status': task.status,
                'timestamp': task.timestamp,
                'execution_count': task.execution_count,
                'params': task.params
            }
            if task.start_time:
                task_info['start_time'] = task.start_time

            pending_tasks.append(task_info)

        debug(f"符合条件的待处理任务数: {len(pending_tasks)}")

        # 按时间戳排序（最早的任务优先）
        pending_tasks.sort(key=lambda x: x['timestamp'])

        # 处理每个任务
        for task_info in pending_tasks:
            self._process_task(task_info)

    def _process_task(self, task_info: Dict[str, Any]):
        """处理单个任务，根据状态进行相应操作
        
        Args:
            task_info: 任务信息字典
        """
        try:
            task_id = task_info['task_id']
            task_type = task_info['task_type']
            status = task_info['status']
            execution_count = task_info.get('execution_count', 1)

            debug(f"处理任务: {task_id}, 类型: {task_type}, 状态: {status}, 执行次数: {execution_count}")

            # 根据不同状态进行处理
            if status == 'queued':
                # 排队中的任务，直接加入队列
                self._requeue_task(task_id, task_type, "排队中的任务重新加入队列")
            elif status == 'failed':
                # 失败的任务，根据重试次数决定是否重新加入队列
                if execution_count <= self.task_max_retry:
                    self._requeue_task(task_id, task_type, f"失败任务重新加入队列，当前重试次数: {execution_count}")
                else:
                    warning(f"任务 {task_id} 重试次数已达上限，不再重新加入队列")
                    # 标记为最终失败
                    self._mark_task_as_final_failure(task_id, task_type, execution_count)
                    return
            elif status == 'running':
                # 运行中的任务，加入异步结果检查
                self._handle_running_task_with_async_check(task_id, task_info)

            self.processed_tasks_count += 1
        except Exception as e:
            error(f"处理任务 {task_info.get('task_id', '未知')} 时发生异常: {str(e)}")

    def _handle_running_task_with_async_check(self, task_id: str, task_info: Dict[str, Any]):
        """处理运行中的任务，加入异步结果检查
        
        Args:
            task_id: 任务ID
            task_info: 任务信息字典
        """
        try:
            # 从任务历史中获取完整的任务对象
            task = task_queue_manager.task_history.get(task_id)
            if not task:
                error(f"未找到任务 {task_id} 的完整信息")
                return

            # 检查任务是否有开始时间
            if not task.start_time:
                warning(f"任务 {task_id} 状态为运行中，但没有开始时间，将其视为排队中任务")
                self._requeue_task(task_id, task.task_type, "运行中任务但无开始时间，重新加入队列")
                return

            # 计算任务已运行时间
            current_time = time.time()
            runtime_seconds = current_time - task.start_time

            # 获取prompt_id用于查询ComfyUI状态
            prompt_id = task.params.get('prompt_id')

            # 如果超过最大运行时间，直接标记为失败
            if runtime_seconds > self.task_timeout_seconds:
                debug(f"任务 {task_id} 运行时间超过{self.task_timeout_seconds} 秒，标记为失败")
                task.status = "failed"
                task.task_msg = f"任务运行时间超过{self.task_timeout_seconds} 秒上限"
                task.end_time = current_time

                # 从运行中任务列表移除
                with task_queue_manager.lock:
                    if task_id in task_queue_manager.running_tasks:
                        del task_queue_manager.running_tasks[task_id]

                # 保存任务历史
                task_queue_manager._save_task_history()

                # 发送失败邮件
                async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)
                return

            # 如果没有prompt_id，则重新加入队列
            if not prompt_id:
                debug(f"任务 {task_id} 没有prompt_id，重新加入队列")
                self._requeue_task(task_id, task.task_type, "运行中任务无prompt_id，重新加入队列")
                return

            # 定义回调函数处理工作流完成或失败的情况
            def on_complete(prompt_id, success):
                try:
                    with task_queue_manager._get_task_lock(task_id):
                        if task_id not in task_queue_manager.task_history:
                            return

                        task = task_queue_manager.task_history[task_id]

                        if success:
                            # 任务完成
                            task.status = "completed"
                            task.task_msg = f"任务执行成功，ComfyUI流程已完成: {prompt_id}"
                            # 设置结束时间为当前时间
                            if not task.end_time:
                                task.end_time = time.time()
                            debug(f"任务 {task_id} 已成功完成")
                        else:
                            # 任务失败，重新加入队列
                            if task.execution_count <= self.task_max_retry:
                                warning(f"任务 {task_id} 在异步检查中失败，重新加入队列")
                                task.status = "queued"
                                task.task_msg = "ComfyUI 工作流连接失败，任务将在稍后重试"
                                task.end_time = None  # 清除结束时间

                                # 将任务重新加入队列
                                task_queue_manager.task_queue.put(task)
                                with task_queue_manager.lock:
                                    task_queue_manager.task_type_counters[task.task_type] = task_queue_manager.task_type_counters.get(task.task_type, 0) + 1
                            else:
                                # 超过重试次数，标记为最终失败
                                task.status = "failed"
                                task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次"
                                task.end_time = time.time()

                                # 发送失败邮件
                                async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)

                        # 从运行中任务列表移除
                        with task_queue_manager.lock:
                            if task_id in task_queue_manager.running_tasks:
                                del task_queue_manager.running_tasks[task_id]

                        # 保存任务历史
                        task_queue_manager._save_task_history()
                except Exception as e:
                    error(f"处理工作流完成回调时出错: {str(e)}")

            # 定义超时回调函数
            def on_timeout(prompt_id):
                try:
                    with task_queue_manager._get_task_lock(task_id):
                        if task_id not in task_queue_manager.task_history:
                            return

                        task = task_queue_manager.task_history[task_id]

                        # 超时，标记为失败并重试
                        if task.execution_count <= self.task_max_retry:
                            warning(f"任务 {task_id} 异步检查超时，重新加入队列")
                            task.status = "queued"
                            task.task_msg = "ComfyUI 工作流检查超时，任务将在稍后重试"
                            task.end_time = None  # 清除结束时间

                            # 将任务重新加入队列
                            task_queue_manager.task_queue.put(task)
                            with task_queue_manager.lock:
                                task_queue_manager.task_type_counters[task.task_type] = task_queue_manager.task_type_counters.get(task.task_type, 0) + 1
                        else:
                            # 超过重试次数，标记为最终失败
                            task.status = "failed"
                            task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次"
                            task.end_time = time.time()

                            # 发送失败邮件
                            async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)

                        # 从运行中任务列表移除
                        with task_queue_manager.lock:
                            if task_id in task_queue_manager.running_tasks:
                                del task_queue_manager.running_tasks[task_id]

                        # 保存任务历史
                        task_queue_manager._save_task_history()
                except Exception as e:
                    error(f"处理工作流超时回调时出错: {str(e)}")

            # 计算剩余超时时间（基于最大运行时间）
            remaining_time_seconds = max(0, (self.task_timeout_seconds) - runtime_seconds)
            timeout_seconds = min(3600, remaining_time_seconds)  # 最大超时1小时

            # 加入异步结果检查
            debug(f"将任务 {task_id} 加入异步结果检查，prompt_id: {prompt_id}")
            workflow_status_checker.check_workflow_status_async(
                prompt_id=prompt_id,
                api_url=self.comfyui_api_url,
                on_complete=on_complete,
                on_timeout=on_timeout,
                timeout_seconds=timeout_seconds
            )
        except Exception as e:
            error(f"处理运行中任务 {task_id} 时发生异常: {str(e)}")
            # 发生异常时，尝试将任务重新加入队列
            try:
                self._requeue_task(task_id, task_info.get('task_type', 'unknown'), "查询状态异常，重新加入队列")
            except:
                pass

    def _requeue_task(self, task_id: str, task_type: str, reason: str):
        """将任务重新加入队列
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            reason: 重新加入队列的原因
        """
        try:
            with task_queue_manager._get_task_lock(task_id):
                # 检查任务是否存在于历史记录中
                if task_id not in task_queue_manager.task_history:
                    warning(f"任务 {task_id} 不存在于历史记录中，无法重新加入队列")
                    return

                # 获取任务对象
                task = task_queue_manager.task_history[task_id]

                # 更新任务状态为queued
                task.status = "queued"

                # 设置任务消息
                task.task_msg = reason

                # 重置开始和结束时间
                task.start_time = None
                task.end_time = None

                # 将任务重新加入队列
                task_queue_manager.task_queue.put(task)
                
                # 更新任务类型计数器
                with task_queue_manager.lock:
                    task_queue_manager.task_type_counters[task_type] = task_queue_manager.task_type_counters.get(task_type, 0) + 1

                debug(f"任务 {task_id} ({task_type}) 已重新加入队列: {reason}")
        except Exception as e:
            error(f"将任务 {task_id} 重新加入队列时发生异常: {str(e)}")

    def _mark_task_as_final_failure(self, task_id: str, task_type: str, execution_count: int):
        """将任务标记为最终失败
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            execution_count: 已执行次数
        """
        try:
            with task_queue_manager._get_task_lock(task_id):
                # 检查任务是否存在于历史记录中
                if task_id not in task_queue_manager.task_history:
                    warning(f"任务 {task_id} 不存在于历史记录中，无法标记为失败")
                    return

                # 获取任务对象
                task = task_queue_manager.task_history[task_id]

                # 更新任务状态为failed
                task.status = "failed"

                # 设置失败消息
                failure_reason = task.task_msg if task.task_msg else "未知原因"
                task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次，原因：{failure_reason}"

                # 设置结束时间（如果还没有）
                if not task.end_time:
                    task.end_time = time.time()

                # 保存任务历史
                task_queue_manager._save_task_history()

                warning(f"任务 {task_id} ({task_type}) 已标记为最终失败，执行次数: {execution_count}")

                # 异步发送邮件通知
                async_send_failure_email(task_id, task_type, task.task_msg, self.task_max_retry)

        except Exception as e:
            error(f"将任务 {task_id} 标记为失败时发生异常: {str(e)}")
            print_log_exception()


# 创建全局启动任务监听器实例
startup_task_listener = StartupTaskListener()

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
import threading
import time
import uuid
from threading import Lock

from hengline.task.task_base import TaskBase
from hengline.task.task_history import task_history
from hengline.task.task_queue import Task
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
        self._running = False
        self._init_thread = None
        self._instance_id = None  # 生成一个简短的实例ID
        self._process_id = os.getpid()  # 获取当前进程ID
        self._task_init_lock = threading.Lock()  # 添加线程锁以防止并发执行

    def start(self):
        """启动监听器，处理历史任务"""

        with self._task_init_lock:
            if self._running:
                debug("历史任务监控器已经在运行中")
                return

            info("=" * 50)
            info("          启动历史任务监听器          ")
            info("=" * 50)

            self._instance_id = str(uuid.uuid4())[:8]  # 生成一个简短的实例ID
            self._running = True
            self._init_thread = threading.Thread(target=self._process_historical_tasks, name=f"StartupTaskListenerThread-{self._instance_id}")
            self._init_thread.daemon = True
            self._init_thread.start()

            info(f"历史任务监控器已启动({threading.current_thread().name}) - 实例ID: {self._instance_id}, 进程ID: {self._process_id}")

            # 加载并处理历史任务
            # info(f"启动任务监听器处理完成，共处理了 {self.processed_tasks_count} 个任务")

    def _process_historical_tasks(self):
        """处理历史任务
        
        """
        # 筛选今天未完成且重试未超过最大重试次数的任务
        pending_tasks = self.cache_init_tasks.values()

        debug(f"符合条件的待处理任务数: {len(pending_tasks)}")

        # 按时间戳排序（最早的任务优先）
        # pending_tasks.sort(key=lambda x: x['timestamp'])

        # 处理每个任务
        for task_info in pending_tasks:
            self._process_task(task_info)

        # 处理完成，清空
        self.cache_init_tasks.clear()

    def _process_task(self, task: Task):
        """处理单个任务，根据状态进行相应操作
        
        """
        try:
            debug(f"处理任务: {task.task_id}, 类型: {task.task_type}, 状态: {task.status}, 执行次数: {task.execution_count}")

            # 根据不同状态进行处理
            if task.status == 'queued':
                # 排队中的任务，直接加入队列
                self._requeue_task(task.task_id, task.task_type, "排队中的任务重新加入队列")
            elif task.status == 'failed':
                # 失败的任务，根据重试次数决定是否重新加入队列
                if task.execution_count <= self.task_max_retry:
                    self._requeue_task(task.task_id, task.task_type, f"失败任务重新加入队列，当前重试次数: {task.execution_count}")
                else:
                    warning(f"任务 {task.task_id} 重试次数已达上限，不再重新加入队列")
                    # 标记为最终失败
                    self._mark_task_as_final_failure(task.task_id, task.task_type, task.execution_count)
                    return
            elif task.status == 'running':
                # 运行中的任务，加入异步结果检查
                self._handle_running_task_with_async_check(task.task_id, task.task_type)

            self.processed_tasks_count += 1
        except Exception as e:
            error(f"处理任务 {task.task_type} 时发生异常: {str(e)}")

    def _handle_running_task_with_async_check(self, task_id: str, task_type):
        """处理运行中的任务，加入异步结果检查
        
        Args:
            task_id: 任务ID
        """
        try:
            # 从任务历史中获取完整的任务对象
            task = self.history_tasks.get(task_id)
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
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]

                # 保存任务历史
                task_history.async_save_task_history()

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
                    with self._get_task_lock(task_id):
                        if task_id not in self.history_tasks:
                            return

                        task = self.history_tasks[task_id]

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
                                self.add_queue_task(task)
                                with task_queue_manager.lock:
                                    self.task_type_counters[task.task_type] = self.task_type_counters.get(task.task_type, 0) + 1
                            else:
                                # 超过重试次数，标记为最终失败
                                task.status = "failed"
                                task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次"
                                task.end_time = time.time()

                                # 发送失败邮件
                                async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)

                        # 从运行中任务列表移除
                        with task_queue_manager.lock:
                            if task_id in self.running_tasks:
                                del self.running_tasks[task_id]

                        # 保存任务历史
                        task_history.async_save_task_history()


                except Exception as e:
                    error(f"处理工作流完成回调时出错: {str(e)}")
                    print_log_exception()

            # 定义超时回调函数
            def on_timeout(prompt_id):
                try:
                    with self._get_task_lock(task_id):
                        if task_id not in self.history_tasks:
                            return

                        task = self.history_tasks[task_id]

                        # 超时，标记为失败并重试
                        if task.execution_count <= self.task_max_retry:
                            warning(f"任务 {task_id} 异步检查超时，重新加入队列")
                            task.status = "queued"
                            task.task_msg = "ComfyUI 工作流检查超时，任务将在稍后重试"
                            task.end_time = None  # 清除结束时间

                            # 将任务重新加入队列
                            self.add_queue_task(task)
                            with task_queue_manager.lock:
                                self.task_type_counters[task.task_type] = self.task_type_counters.get(task.task_type, 0) + 1
                        else:
                            # 超过重试次数，标记为最终失败
                            task.status = "failed"
                            task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次"
                            task.end_time = time.time()

                            # 发送失败邮件
                            async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)

                        # 从运行中任务列表移除
                        with task_queue_manager.lock:
                            if task_id in self.running_tasks:
                                del self.running_tasks[task_id]

                        # 保存任务历史
                        task_history.async_save_task_history()

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
                self._requeue_task(task_id, task_type, "查询状态异常，重新加入队列")
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
            with self._get_task_lock(task_id):
                # 检查任务是否存在于历史记录中
                if task_id not in self.history_tasks:
                    warning(f"任务 {task_id} 不存在于历史记录中，无法重新加入队列")
                    return

                # 获取任务对象
                task = self.history_tasks[task_id]

                # 更新任务状态为queued
                task.status = "queued"

                # 设置任务消息
                task.task_msg = reason

                # 重置开始和结束时间
                task.start_time = None
                task.end_time = None

                # 将任务重新加入队列
                self.add_queue_task(task_id, task)

                # 更新任务类型计数器
                with task_queue_manager.lock:
                    self.task_type_counters[task_type] = self.task_type_counters.get(task_type, 0) + 1

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
            with self._get_task_lock(task_id):
                # 检查任务是否存在于历史记录中
                if task_id not in self.history_tasks:
                    warning(f"任务 {task_id} 不存在于历史记录中，无法标记为失败")
                    return

                # 获取任务对象
                task = self.history_tasks[task_id]

                # 更新任务状态为failed
                task.status = "failed"

                # 设置失败消息
                failure_reason = task.task_msg if task.task_msg else "未知原因"
                task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次，原因：{failure_reason}"

                # 设置结束时间（如果还没有）
                if not task.end_time:
                    task.end_time = time.time()

                # 保存任务历史
                task_history.async_save_task_history()

                warning(f"任务 {task_id} ({task_type}) 已标记为最终失败，执行次数: {execution_count}")

                # 异步发送邮件通知
                async_send_failure_email(task_id, task_type, task.task_msg, self.task_max_retry)

        except Exception as e:
            error(f"将任务 {task_id} 标记为失败时发生异常: {str(e)}")


# 创建全局启动任务监听器实例
task_init = StartupTaskListener()

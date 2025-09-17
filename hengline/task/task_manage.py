#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理模块
用于管理生图和生视频任务的排队执行
"""

import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, List, Callable

from hengline.logger import error, debug, info, warning
from hengline.task.task_base import TaskBase
from hengline.task.task_email import async_send_failure_email
# 导入邮件发送模块
from hengline.task.task_history import task_history
from hengline.task.task_queue import Task, TaskStatus
from hengline.utils.log_utils import print_log_exception


class TaskQueueManager(TaskBase):
    """任务队列管理器类"""

    def __init__(self):
        super().__init__()
        """
        初始化任务队列管理器
        
        """
        self.lock = threading.Lock()  # 用于线程同步的主锁

    def enqueue_task(self, task_id: str, task_type: str, params: Dict[str, Any], callback: Callable) -> Tuple[str, int, float]:
        """
        将任务加入队列（仅对队列操作部分加锁）
        
        Args:
            task_type: 任务类型
            params: 任务参数

        Returns:
            Tuple[str, int, float]: (任务ID, 队列中的位置, 预估等待时间(秒))
        """

        # 创建或获取任务锁
        if task_id:
            task_lock = self._get_task_lock(task_id)
        else:
            # 临时锁，用于新任务创建过程
            task_lock = threading.Lock()

        with task_lock:
            # 再次检查任务ID是否存在

            if not task_id or task_id not in self.history_tasks:
                task_id = str(uuid.uuid4())
                task_lock = self._get_task_lock(task_id)  # 为新任务创建并获取锁

                # 创建新任务对象
                task = Task(
                    task_type=task_type,
                    task_id=task_id,
                    timestamp=time.time(),
                    params=params,
                    task_lock=task_lock,
                    callback=callback  # (task_type, params, task_id)
                )
                debug(f"新任务已加入队列: {task_id}, 类型: {task_type}")

            else:
                # 如果task_id已存在，则更新现有任务
                task = self.history_tasks[task_id]
                if callback:
                    task.callback = callback
                    # task.callback = workflow_manager.execute_common
                # 更新任务参数
                if params:
                    task.params.update(params)
                # 更新时间戳
                task.timestamp = time.time()
                # 重置任务状态为排队中
                task.status = TaskStatus.QUEUED.value
                # 重置执行时间
                task.start_time = None
                task.end_time = None

            debug(f"任务已更新并重新加入队列: {task_id}, 类型: {task_type}")

            # 计算预估等待时间
            queue_position, waiting_str = self.estimate_waiting_time(task_type, task.params)
            task.task_msg = f"任务排队等待执行。预计等待时间：{waiting_str}"

            # 将任务加入队列
            self.add_queue_task(task)

            # 将任务添加到历史记录
            self.add_history_task(task_id, task)

            # 异步保存任务历史
            task_history.async_save_task_history()

            return task_id, queue_position, waiting_str

    def requeue_task(self, task_id: str, task_type: str, reason: str, callback: Callable):
        """将任务重新加入队列

        Args:
            task_id: 任务ID
            task_type: 任务类型
            reason: 重新加入队列的原因
        """
        try:
            # 检查任务是否存在于历史记录中
            if task_id not in self.history_tasks:
                warning(f"任务 {task_id} 不存在于历史记录中，无法重新加入队列")
                return task_id, None, None

            # 设置任务消息
            # task.task_msg = reason
            info(f"任务 {task_id} ({task_type}) 已重新加入队列: {reason}")
            return self.enqueue_task(task_id, task_type, {}, callback)

        except Exception as e:
            error(f"将任务 {task_id} 重新加入队列时发生异常: {str(e)}")
            print_log_exception()

    def mark_task_as_final_failure(self, task_id: str, task_type: str, execution_count: int):
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
                task.status = TaskStatus.FAILED.value

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
            print_log_exception()

    def update_task_status(self, task_id: str, status: TaskStatus, task_msg: str = None,
                           output_filenames: list = None, prompt_id: str = None):
        """
        更新指定任务的状态

        Args:
            task_id: 任务ID
            status: 新的任务状态
            task_msg: 可选的任务消息
            output_filenames: 可选的输出文件名列表
        """
        task = self.get_history_task(task_id)
        if not task:
            debug(f"任务不存在，无法更新状态: {task_id}")
            return

        with self._get_task_lock(task_id):
            old_status = task.status
            task.status = status.value

            # 更新任务消息
            if task_msg:
                task.task_msg = task_msg

            if prompt_id:
                task.prompt_id = prompt_id

            # 更新输出文件名列表
            if output_filenames:
                task.output_filenames = output_filenames

            # 根据状态更新时间信息
            if TaskStatus.is_running(status.value) and not TaskStatus.is_running(old_status):
                task.start_time = time.time()
            elif TaskStatus.is_finished(status.value) and old_status != status.value:
                task.end_time = time.time()

            # 如果任务完成，从running_tasks中移除
            if TaskStatus.is_finished(status.value) and task_id in self.running_tasks:
                del self.running_tasks[task_id]

            debug(f"更新任务状态成功: {task_id}, 状态从 {old_status} 变为 {status.value}")

        # 异步保存任务历史
        task_history.async_save_task_history()

    def get_all_tasks(self, date=None):
        """
        获取所有任务历史记录，可选按日期筛选 - 优化版本

        Args:
            date: 可选的日期字符串，格式为'YYYY-MM-DD'

        Returns:
            List[Dict[str, Any]]: 任务的状态信息列表

        注意：根据用户建议，此查询接口不需要加锁，提高响应速度
        """
        try:
            # 获取运行中任务的ID集合
            running_task_ids = set(self.running_tasks.keys())

            # 获取任务类型计数器的副本
            task_type_counters_copy = self.task_type_counters.copy()

            # 获取历史任务的副本
            if date == datetime.now().strftime('%Y-%m-%d'):
                history_tasks = list(self.history_tasks.values())
            else:
                history_tasks = list(task_history.get_before_history_task(date).values())

            # 创建任务信息列表
            all_tasks = []

            for task in history_tasks:
                # 应用日期筛选
                if date:
                    task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
                    if task_date != date:
                        continue

                # 确定任务状态和估算队列位置
                if task.task_id in running_task_ids:
                    current_status = TaskStatus.RUNNING.value
                    queue_position = None
                elif TaskStatus.is_queued(task.status):
                    current_status = TaskStatus.QUEUED.value
                    # 使用任务类型计数器估算队列位置
                    task_type = task.task_type
                    if task_type in task_type_counters_copy:
                        # 这是一个估算值，避免遍历整个队列
                        queue_position = task_type_counters_copy[task_type] // 2 + 1
                    else:
                        queue_position = None
                else:
                    current_status = task.status
                    queue_position = None

                # 构建任务信息
                task_info = {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "status": current_status,
                    "timestamp": task.timestamp,
                    "queue_position": queue_position,
                    "execution_count": task.execution_count
                }

                # 添加可选字段
                if task.task_msg:
                    task_info["task_msg"] = task.task_msg
                if task.start_time:
                    task_info["start_time"] = task.start_time
                if task.end_time:
                    task_info["end_time"] = task.end_time
                    if task.start_time:
                        task_info["duration"] = task.end_time - task.start_time

                # 添加任务参数信息（不包含敏感数据）
                if task.params:
                    task_info["prompt"] = task.params.get("prompt", "")
                    task_info["negative_prompt"] = task.params.get("negative_prompt", "")

                all_tasks.append(task_info)

            # 按时间戳降序排序（最新的任务在前）
            all_tasks.sort(key=lambda x: x["timestamp"], reverse=True)

            return all_tasks
        except Exception as e:
            error(f"获取任务列表失败: {str(e)}")
            print_log_exception()
            return []


# 全局任务队列管理器实例
task_queue_manager = TaskQueueManager()

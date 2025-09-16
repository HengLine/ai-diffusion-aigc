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
from typing import Dict, Any, Callable, Tuple, List

from hengline.common import get_timestamp_by_type
from hengline.logger import error, debug
from hengline.task.task_base import TaskBase
# 导入邮件发送模块
from hengline.task.task_history import task_history
from hengline.task.task_monitor import task_monitor
from hengline.task.task_queue import Task
from hengline.utils.log_utils import print_log_exception


class TaskQueueManager(TaskBase):
    """任务队列管理器类"""

    def __init__(self):
        super().__init__()
        """
        初始化任务队列管理器
        
        """
        self.lock = threading.Lock()  # 用于线程同步的主锁


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

        # 启动任务处理线程
        task_monitor.start()

    def enqueue_task(self, task_id: str, task_type: str, params: Dict[str, Any], callback: Callable) -> Tuple[str, int, float]:
        """
        将任务加入队列（仅对队列操作部分加锁）
        
        Args:
            task_type: 任务类型
            params: 任务参数
            callback: 任务完成后的回调函数
        
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
            if not task_id or task_id not in task_history.tasks:
                task_id = str(uuid.uuid4())
                task_lock = self._get_task_lock(task_id)  # 为新任务创建并获取锁

                # 创建新任务对象
                task = Task(
                    task_type=task_type,
                    task_id=task_id,
                    timestamp=time.time(),
                    params=params,
                    task_lock=task_lock,
                    callback=callback
                )
                debug(f"新任务已加入队列: {task_id}, 类型: {task_type}")

            else:
                # 如果task_id已存在，则更新现有任务
                task = task_history.tasks[task_id]
                # 更新任务参数
                task.params.update(params)
                # 更新时间戳
                task.timestamp = time.time()
                # 重置任务状态为排队中
                task.status = "queued"
                # 重置执行时间
                task.start_time = None
                task.end_time = None
                debug(f"任务已更新并重新加入队列: {task_id}, 类型: {task_type}")

            # 将任务加入队列
            self.task_queue.put(task)

            # 更新任务类型计数器
            self.task_type_counters[task_type] = self.task_type_counters.get(task_type, 0) + 1

            # 计算队列中的位置（包括正在运行的任务）
            queue_position = len(self.running_tasks) + self.task_queue.qsize()

            # 计算预估等待时间
            waiting_time = self._estimate_waiting_time(task_type, queue_position)

            # 将任务添加到历史记录
            task_history.tasks[task_id] = task

            # 异步保存任务历史
            task_history.async_save_task_history()

            return task_id, queue_position, waiting_time

    def _estimate_waiting_time(self, task_type: str, queue_position: int) -> float:
        """
        预估任务等待时间
        
        Args:
            task_type: 任务类型
            queue_position: 任务在队列中的位置
        
        Returns:
            float: 预估等待时间（秒）
        """
        # 获取该类型任务的平均执行时间
        avg_duration = get_timestamp_by_type().get(task_type, 100)  # 默认任务执行时间（秒）

        # 如果队列位置小于等于最大并发数，无需等待
        if queue_position <= self.max_concurrent_tasks:
            return avg_duration

        # 计算前面有多少个任务在等待
        waiting_tasks = queue_position - self.max_concurrent_tasks

        # 预估等待时间 = 前面等待的任务数 * 该类型任务的平均执行时间
        estimated_waiting_time = waiting_tasks * avg_duration

        return estimated_waiting_time + avg_duration

    def _execute_callback_with_timeout(self, task: Task, timeout: int = 1200):
        """执行任务回调函数，并设置超时时间（同步版本，保持向后兼容）"""
        result = None
        exception = None

        # 创建一个线程来执行回调函数
        def callback_thread_func():
            nonlocal result, exception
            try:
                result = task.callback(task.params)
            except Exception as e:
                exception = e

        # 启动线程执行回调
        callback_thread = threading.Thread(target=callback_thread_func)
        callback_thread.daemon = True
        callback_thread.start()

        # 等待线程完成，但设置超时
        callback_thread.join(timeout=timeout)

        # 检查线程是否还在运行
        if callback_thread.is_alive():
            error(f"任务执行超时: {task.task_id}")
            return {'success': False, 'message': f'任务执行超时({timeout}秒)', 'timeout': True}

        # 检查是否有异常
        if exception:
            raise exception

        return result

    def shutdown(self):
        """关闭任务队列管理器"""
        self._running = False

        # 将队列中排队的任务添加到任务历史记录中
        temp_tasks = []
        while not self.task_queue.empty():
            task = self.task_queue.get()
            temp_tasks.append(task)
            # 将任务添加到历史记录，保持"queued"状态
            self.add_history_task(task.task_id, task)
            debug(f"将排队任务添加到历史记录: {task.task_id}, 类型: {task.task_type}")

        # 保存任务历史
        self._save_task_history()

        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        debug("任务队列管理器已关闭，已保存所有排队任务到历史记录")

    def update_task_status(self, task_id: str, status: str, task_msg: str = None, output_filename: str = None,
                           output_filenames: list = None):
        """
        更新指定任务的状态
        
        Args:
            task_id: 任务ID
            status: 新的任务状态
            task_msg: 可选的任务消息
            output_filename: 可选的输出文件名
            output_filenames: 可选的输出文件名列表
        """
        task = self.get_history_task(task_id)
        if not task:
            debug(f"任务不存在，无法更新状态: {task_id}")
            return

        with task.task_lock:
            old_status = task.status
            task.status = status

            # 更新任务消息
            if task_msg:
                task.task_msg = task_msg

            # 更新输出文件名
            if output_filename:
                task.output_filename = output_filename

            # 更新输出文件名列表
            if output_filenames:
                task.output_filenames = output_filenames

            # 根据状态更新时间信息
            if status == "running" and old_status != "running":
                task.start_time = time.time()
            elif status in ["completed", "failed"] and old_status != status:
                task.end_time = time.time()

            # 如果任务完成，从running_tasks中移除
            if status in ["completed", "failed"] and task_id in self.running_tasks:
                del self.running_tasks[task_id]

            debug(f"更新任务状态成功: {task_id}, 状态从 {old_status} 变为 {status}")

        # 异步保存任务历史
        self._save_task_history()

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
            # 重新导入datetime，确保在任何环境中可用
            from datetime import datetime

            # 添加日志，查看task_history的长度
            debug(f"get_all_tasks被调用，date={date}，task_history长度={len(self.history_tasks)}")

            # 直接访问数据，不使用锁以提高查询速度
            # 获取运行中任务的ID集合
            running_task_ids = set(self.running_tasks.keys())

            # 获取任务类型计数器的副本
            task_type_counters_copy = self.task_type_counters.copy()

            # 获取历史任务的副本
            history_tasks = list(self.history_tasks.values())

            # 创建任务信息列表
            all_tasks = []

            # 在锁外处理所有任务，避免长时间持有锁
            for task in history_tasks:
                # 应用日期筛选
                if date:
                    task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
                    if task_date != date:
                        continue

                # 确定任务状态和估算队列位置
                if task.task_id in running_task_ids:
                    current_status = "running"
                    queue_position = None
                elif task.status == "queued":
                    current_status = "queued"
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

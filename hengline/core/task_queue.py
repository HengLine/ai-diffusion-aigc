#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理模块
用于管理生图和生视频任务的排队执行
"""

import json
import os
import queue
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Callable, Tuple, Optional, List

# 导入邮件发送模块
from hengline.core.task_email import _async_send_failure_email
from hengline.logger import error, debug, warning, info
from hengline.utils.config_utils import max_concurrent_tasks


class Task:
    """表示一个任务的类"""

    def __init__(self, task_type: str, task_id: str, timestamp: float
                 , params: Dict[str, Any], task_lock: threading.Lock, callback: Callable):
        self.task_type = task_type  # 任务类型: text_to_image, image_to_image, text_to_video, image_to_video
        self.task_id = task_id  # 任务唯一ID
        # 确保timestamp始终是数值类型
        try:
            self.timestamp = float(timestamp) if timestamp is not None else time.time()
        except (ValueError, TypeError):
            self.timestamp = time.time()
        self.params = params  # 任务参数
        self.callback = callback  # 任务完成后的回调函数
        self.start_time = None  # 任务开始执行时间
        self.end_time = None  # 任务结束时间
        self.task_lock = task_lock  # 使用传入的任务锁
        self.status = "queued"  # 任务状态: queued, running, completed, failed
        self.output_filename = None  # 任务输出文件名
        self.task_msg = None  # 任务消息，用于存储错误或状态信息
        self.execution_count = 0  # 任务执行次数，默认为0

    def __lt__(self, other):
        # 任务排序基于时间戳，确保先进先出
        # 添加类型检查，确保安全比较
        if hasattr(other, 'timestamp') and isinstance(other.timestamp, (int, float)) and isinstance(self.timestamp,
                                                                                                    (int, float)):
            return self.timestamp < other.timestamp
        # 当比较类型不兼容时，确保队列稳定性
        return id(self) < id(other)


class TaskQueueManager:
    """任务队列管理器类"""

    def __init__(self, max_concurrent_tasks: int = 5):
        """
        初始化任务队列管理器
        
        Args:
            max_concurrent_tasks: 最大并发任务数，默认为5
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = queue.PriorityQueue()  # 优先队列，按时间戳排序
        self.running_tasks = {}  # 当前运行中的任务 {task_id: Task}
        # self.lock = threading.Lock()  # 用于线程同步的主锁
        self.task_history = {}  # 任务历史记录 {task_id: Task}
        self.average_task_durations = {
            "text_to_image": 60.0,  # 默认平均文生图任务时长（秒）
            "image_to_image": 70.0,  # 默认平均图生图任务时长（秒）
            "text_to_video": 300.0,  # 默认平均文生视频任务时长（秒）
            "image_to_video": 320.0  # 默认平均图生视频任务时长（秒）
        }
        self.task_locks = {}  # 任务级别的锁 {task_id: threading.Lock}
        self.task_locks_lock = threading.Lock()  # 用于保护task_locks字典的锁

        # 添加任务类型计数器，用于精确跟踪不同类型任务的排队数量
        # 避免每次查询时遍历整个队列
        self.task_type_counters = {
            "text_to_image": 0,
            "image_to_image": 0,
            "text_to_video": 0,
            "image_to_video": 0
        }

        # 持久化配置
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

        # 加载已保存的任务历史
        self._load_task_history()
        debug(f"TaskQueueManager初始化完成，task_history长度={len(self.task_history)}")

        # 启动任务处理线程
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_tasks)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        # 加载今天排队中的任务到队列
        queued_tasks_added = 0
        # 获取今天的日期
        today_date = datetime.now().strftime('%Y-%m-%d')

        # 筛选今天且状态为queued的任务
        today_queued_tasks = []
        for task in self.task_history.values():
            task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
            if task_date == today_date and task.status == "queued":
                today_queued_tasks.append(task)

        # 按时间戳排序
        today_queued_tasks.sort(key=lambda x: x.timestamp)

        # 将任务加入队列
        for task in today_queued_tasks:
            self.task_queue.put(task)
            queued_tasks_added += 1

        debug(f"任务队列管理器已启动，最大并发任务数: {max_concurrent_tasks}")
        debug(f"已加载任务历史记录: {len(self.task_history)} 个任务")
        debug(f"已将今天 {queued_tasks_added} 个排队中的任务添加到队列")

    def _get_task_lock(self, task_id: str) -> threading.Lock:
        """获取指定任务的锁，如果不存在则创建"""
        with self.task_locks_lock:
            if task_id not in self.task_locks:
                self.task_locks[task_id] = threading.Lock()
            return self.task_locks[task_id]

    def enqueue_task(self, task_type: str, params: Dict[str, Any], callback: Callable) -> Tuple[str, int, float]:
        """
        将任务加入队列（仅对队列操作部分加锁）
        
        Args:
            task_type: 任务类型
            params: 任务参数
            callback: 任务完成后的回调函数
        
        Returns:
            Tuple[str, int, float]: (任务ID, 队列中的位置, 预估等待时间(秒))
        """
        # 检查任务参数中是否已提供task_id
        task_id = params.get('task_id')
        timestamp = time.time()

        # 创建或获取任务锁
        if task_id:
            task_lock = self._get_task_lock(task_id)
        else:
            # 临时锁，用于新任务创建过程
            task_lock = threading.Lock()

        with task_lock:
            # 再次检查任务ID是否存在
            if not task_id or task_id not in self.task_history:
                task_id = str(uuid.uuid4())
                task_lock = self._get_task_lock(task_id)  # 为新任务创建并获取锁

                # 创建新任务对象
                task = Task(
                    task_type=task_type,
                    task_id=task_id,
                    timestamp=timestamp,
                    params=params,
                    task_lock=task_lock,
                    callback=callback
                )

                # 将任务加入队列
                self.task_queue.put(task)

                # 更新任务类型计数器
                self.task_type_counters[task_type] = self.task_type_counters.get(task_type, 0) + 1

                debug(f"新任务已加入队列: {task_id}, 类型: {task_type}")

                # 计算队列中的位置（包括正在运行的任务）
                queue_position = len(self.running_tasks) + self.task_queue.qsize()

                # 计算预估等待时间
                waiting_time = self._estimate_waiting_time(task_type, queue_position)

                # 将任务添加到历史记录
                self.task_history[task_id] = task

                # 异步保存任务历史
                self._async_save_history()

                return task_id, queue_position, waiting_time
            else:
                # 如果task_id已存在，则更新现有任务
                task = self.task_history[task_id]
                # 更新任务参数
                task.params.update(params)
                # 更新时间戳
                task.timestamp = timestamp
                # 重置任务状态为排队中
                task.status = "queued"
                # 重置执行时间
                task.start_time = None
                task.end_time = None
                # 将任务重新加入队列
                self.task_queue.put(task)

                # 更新任务类型计数器
                self.task_type_counters[task_type] = self.task_type_counters.get(task_type, 0) + 1

                debug(f"任务已更新并重新加入队列: {task_id}, 类型: {task_type}")

                # 计算队列中的位置（包括正在运行的任务）
                queue_position = len(self.running_tasks) + self.task_queue.qsize()

                # 计算预估等待时间
                waiting_time = self._estimate_waiting_time(task_type, queue_position)

                # 将任务添加到历史记录
                self.task_history[task_id] = task

                # 异步保存任务历史
                self._async_save_history()

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
        task_default_duration = 20.0  # 默认任务执行时间（秒）

        # 如果队列位置小于等于最大并发数，无需等待
        if queue_position <= self.max_concurrent_tasks:
            return task_default_duration

        # 计算前面有多少个任务在等待
        waiting_tasks = queue_position - self.max_concurrent_tasks

        # 获取该类型任务的平均执行时间
        avg_duration = self.average_task_durations.get(task_type, 60.0)

        # 预估等待时间 = 前面等待的任务数 * 该类型任务的平均执行时间
        estimated_waiting_time = waiting_tasks * avg_duration

        return estimated_waiting_time + task_default_duration

    def _process_tasks(self):
        """处理队列中的任务 - 任务级锁优化版本"""
        while self.running:
            try:
                # 检查是否可以启动新任务
                current_running = len(self.running_tasks)
                can_start_new = current_running < self.max_concurrent_tasks and not self.task_queue.empty()

                if can_start_new:
                    try:
                        task = None
                        task_lock = None

                        # 获取下一个任务
                        if not self.task_queue.empty() and len(self.running_tasks) < self.max_concurrent_tasks:
                            task = self.task_queue.get()
                            task_lock = self._get_task_lock(task.task_id)

                            # 减少任务类型计数器
                            self.task_type_counters[task.task_type] = max(0, self.task_type_counters.get(task.task_type,
                                                                                                         0) - 1)

                        if task and task_lock:
                            # 使用任务级锁更新任务状态
                            with task_lock:
                                # 再次检查是否可以启动新任务
                                if len(self.running_tasks) >= self.max_concurrent_tasks:
                                    # 无法启动新任务，将任务放回队列
                                    self.task_queue.put(task)
                                    self.task_type_counters[task.task_type] = self.task_type_counters.get(
                                        task.task_type, 0) + 1
                                    continue

                                # 更新任务状态和执行次数
                                task.status = "running"
                                task.start_time = time.time()
                                task.execution_count += 1  # 执行次数加1
                                self.running_tasks[task.task_id] = task

                                # 记录到历史
                                self.task_history[task.task_id] = task

                            debug(f"开始执行任务: {task.task_id}, 类型: {task.task_type}")

                            # 直接异步保存任务历史，避免阻塞
                            self._async_save_history()

                            # 启动任务线程
                            task_thread = threading.Thread(
                                target=self._execute_task,
                                args=(task,)
                            )
                            task_thread.daemon = True
                            task_thread.start()

                    except Exception as e:
                        error(f"处理队列任务时发生错误: {str(e)}")
                else:
                    # 等待较短时间再检查，减少CPU占用
                    time.sleep(0.05)
            except Exception as e:
                error(f"任务处理循环错误: {str(e)}")
                time.sleep(0.1)

    def _execute_task(self, task: Task):
        """执行单个任务 - 任务级锁优化版本"""
        task_lock = self._get_task_lock(task.task_id)

        try:
            # 使用单独的方法执行任务回调，避免长时间阻塞主处理流程
            result = self._execute_callback_with_timeout(task)

            # 使用任务级锁更新任务状态
            with task_lock:
                # 检查任务是否遇到连接异常
                if result and isinstance(result, dict) and result.get('queued'):
                    # 从配置中获取最大重试次数（默认为3）
                    max_retry_count = 3
                    try:
                        from hengline.utils.config_utils import get_settings_config
                        settings_config = get_settings_config()
                        max_retry_count = settings_config.get('task', {}).get('max_retry_count', 3)
                    except:
                        pass

                    # 检查是否超过最大重试次数
                    if task.execution_count > max_retry_count:
                        warning(f"任务 {task.task_id} 执行次数已达到最大限制 {max_retry_count}，不再重试")
                        task.status = "failed"
                        task.task_msg = f"ComfyUI 工作流连接超时，任务已重试 {max_retry_count} 次。请检查ComfyUI服务器是否运行，或配置中URL是否正确。"
                        task.end_time = time.time()

                        _async_send_failure_email(task.task_id, task.task_type, task.task_msg, max_retry_count)

                    else:
                        # 如果未超过最大重试次数，将任务重新加入队列
                        warning(f"任务执行失败，ComfyUI服务器连接异常，将任务重新加入队列: {task.task_id}")
                        task.status = "queued"
                        task.task_msg = "ComfyUI 工作流连接超时，任务将在稍后重试。请检查ComfyUI服务器是否运行，或配置中URL是否正确。"
                        task.end_time = None  # 清除结束时间

                        # 将任务重新加入队列
                        self.task_queue.put(task)
                        self.task_type_counters[task.task_type] = self.task_type_counters.get(task.task_type, 0) + 1

                    # 从运行中任务列表移除
                    if task.task_id in self.running_tasks:
                        del self.running_tasks[task.task_id]

                    # 直接异步保存任务历史，避免阻塞
                    self._async_save_history()

                    return  # 提前返回，避免后续处理
                elif result is None:
                    # 任务未返回结果，可能是执行过程中出错
                    task.status = "failed"
                    task.task_msg = f"任务执行未返回结果: {task.task_id}"
                    task.end_time = time.time()

                    _async_send_failure_email(task.task_id, task.task_type, task.task_msg, task.execution_count)

                elif isinstance(result, dict) and not result.get('success', True):
                    # 任务返回结果但标记为失败
                    task.status = "failed"
                    task.task_msg = result.get('message', '任务执行失败')
                    task.end_time = time.time()
                else:
                    task.status = "completed"
                    task.end_time = time.time()

                    # 保存输出文件名
                    if result and isinstance(result, dict):
                        if 'output_path' in result:
                            # 从output_path中提取文件名
                            task.output_filename = os.path.basename(result['output_path'])
                        elif 'filename' in result:
                            task.output_filename = result['filename']

                    # 更新平均执行时间（在锁外异步执行）
                    if task.end_time and task.start_time:
                        duration = task.end_time - task.start_time
                        # 启动一个短时间的线程来更新平均执行时间，避免阻塞
                        threading.Thread(
                            target=self._async_update_average_duration,
                            args=(task.task_type, duration),
                            daemon=True
                        ).start()

                # 从运行中任务列表移除
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]

                # 直接异步保存任务历史，避免阻塞
                self._async_save_history()

            info(f"任务执行完成: {task.task_id}, 类型: {task.task_type}, 状态: {task.status}")

        except Exception as e:
            error(f"任务执行异常: {task.task_id}, 错误: {str(e)}")

            # 使用任务级锁更新任务状态
            with task_lock:
                task.status = "failed"
                task.task_msg = f"任务执行异常: {str(e)}"
                task.end_time = time.time()

                # 从运行中任务列表移除
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]

                # 直接异步保存任务历史，避免阻塞
                self._async_save_history()

    def _execute_callback_with_timeout(self, task: Task, timeout: int = 1200):
        """执行任务回调函数，并设置超时时间"""
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

    def _async_update_average_duration(self, task_type: str, duration: float):
        """异步更新任务类型的平均执行时间，避免阻塞主流程"""
        try:
            # 使用简单移动平均，权重为0.8（旧值）和0.2（新值）
            old_avg = self.average_task_durations.get(task_type, 60.0)
            new_avg = old_avg * 0.8 + duration * 0.2
            self.average_task_durations[task_type] = new_avg

            debug(f"更新任务类型 {task_type} 的平均执行时间: 旧值={old_avg:.1f}秒, 新值={new_avg:.1f}秒")
        except Exception as e:
            error(f"异步更新平均执行时间失败: {str(e)}")

    def _update_average_duration(self, task_type: str, duration: float):
        """更新任务类型的平均执行时间"""
        # 使用简单移动平均，权重为0.8（旧值）和0.2（新值）
        old_avg = self.average_task_durations.get(task_type, 60.0)
        new_avg = old_avg * 0.8 + duration * 0.2
        self.average_task_durations[task_type] = new_avg

        debug(f"更新任务类型 {task_type} 的平均执行时间: 旧值={old_avg:.1f}秒, 新值={new_avg:.1f}秒")

    def get_queue_status(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取队列状态
        
        Args:
            task_type: 可选的任务类型过滤参数，如果提供则只统计该类型的任务
        
        Returns:
            Dict[str, Any]: 队列状态信息，包含前端期望的字段
        
        注意：根据用户建议，此查询接口不需要加锁，提高响应速度
        """
        # 直接访问数据，不使用锁以提高查询速度
        # 计算总运行任务数和排队任务数
        running_count = len(self.running_tasks)
        queued_count = self.task_queue.qsize()

        # 如果提供了任务类型参数，则过滤任务
        if task_type and task_type != 'all':
            # 计算该类型的运行任务数
            running_count = sum(1 for task in self.running_tasks.values() if task.task_type == task_type)

            # 使用任务类型计数器获取该类型的排队任务数
            queued_count = self.task_type_counters.get(task_type, 0)

        # 计算总任务数
        total_tasks = running_count + queued_count

        # 计算队列位置
        position = 1

        # 计算预计等待时间（基于平均执行时间）
        avg_duration = 0
        if task_type and task_type in self.average_task_durations:
            avg_duration = self.average_task_durations[task_type] / 60  # 转换为分钟
        else:
            # 如果没有指定任务类型或任务类型不存在，使用所有类型的平均值
            avg_durations = list(self.average_task_durations.values())
            if avg_durations:
                avg_duration = sum(avg_durations) / len(avg_durations) / 60  # 转换为分钟

        # 计算预计等待时间
        estimated_time = queued_count * avg_duration if avg_duration > 0 else 20

        # 计算进度
        progress = 0
        if total_tasks > 0:
            progress = min(100, int((position / total_tasks) * 100))

        # 计算历史任务总数
        total_history_tasks = len(self.task_history)

        # 返回兼容测试文件的格式 - 修复缩进问题，确保总是返回字典
        return {
            "total_tasks": total_tasks,
            "in_queue": queued_count,
            "running_tasks": running_count,
            "position": position,
            "estimated_time": round(estimated_time, 1),
            "progress": progress,
            "running_tasks_count": running_count,  # 保留原始字段以保持兼容性
            "queued_tasks_count": queued_count,  # 保留原始字段以保持兼容性
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "average_task_durations": self.average_task_durations,

            # 兼容测试文件的字段
            "queued_tasks": queued_count,  # 兼容test_get_queue_status.py
            "total_history_tasks": total_history_tasks,  # 兼容test_get_queue_status.py
            "avg_execution_time": self.average_task_durations  # 兼容check_queue.py
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定任务的状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息，如果任务不存在则返回None
        """
        task = self.task_history.get(task_id)
        if not task:
            return None

        # 确保状态值的正确性
        current_status = task.status

        # 优化：不再遍历整个队列来计算位置，避免长时间持锁
        queue_position = 1

        # 检查任务状态的一致性
        if current_status == "queued":
            # 检查是否在running_tasks中
            if task_id in self.running_tasks:
                current_status = "running"
            else:
                # 使用任务类型计数器估算队列位置
                # 注意：这是一个估算值，但避免了遍历整个队列
                task_type = task.task_type
                if task_type in self.task_type_counters:
                    queue_position = self.task_type_counters[task_type] // 2 + 1  # 简单估算

        status_info = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": current_status,
            "timestamp": task.timestamp,
            "queue_position": queue_position
        }

        # 添加开始和结束时间
        if task.start_time:
            status_info["start_time"] = task.start_time
        if task.end_time:
            status_info["end_time"] = task.end_time
            if task.start_time:
                status_info["duration"] = task.end_time - task.start_time

        return status_info

    def shutdown(self):
        """关闭任务队列管理器"""
        self.running = False

        # 将队列中排队的任务添加到任务历史记录中
        temp_tasks = []
        while not self.task_queue.empty():
            task = self.task_queue.get()
            temp_tasks.append(task)
            # 将任务添加到历史记录，保持"queued"状态
            self.task_history[task.task_id] = task
            debug(f"将排队任务添加到历史记录: {task.task_id}, 类型: {task.task_type}")

        # 保存任务历史
        self._save_task_history()

        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        debug("任务队列管理器已关闭，已保存所有排队任务到历史记录")

    def _save_task_history(self):
        """保存任务历史到按日期分类的文件 - 优化版本"""
        # 使用异步保存，减少阻塞
        if not hasattr(self, '_save_history_thread') or not self._save_history_thread.is_alive():
            self._save_history_thread = threading.Thread(target=self._async_save_history)
            self._save_history_thread.daemon = True
            self._save_history_thread.start()

    def _async_save_history(self):
        """异步保存任务历史"""
        try:
            # 重新导入datetime和timedelta，确保在异步线程中可用
            from datetime import datetime, timedelta

            # 创建任务数据的深拷贝
            task_history_copy = self.task_history.copy()

            # 按日期分组任务
            tasks_by_date = {}
            for task in task_history_copy.values():
                # 只保存今天和昨天的任务，减少文件操作量
                task_time = datetime.fromtimestamp(task.timestamp)
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday = today - timedelta(days=1)

                # 只处理今天和昨天的任务，以及状态为queued的任务
                if (task_time >= yesterday and task_time < today + timedelta(days=1)) or task.status == "queued":
                    task_date = task_time.strftime('%Y-%m-%d')
                    if task_date not in tasks_by_date:
                        tasks_by_date[task_date] = []

                    # 创建可序列化的任务数据
                    task_data = {
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'timestamp': task.timestamp,
                        'params': task.params,
                        'status': task.status,
                        'output_filename': task.output_filename,
                        'execution_count': task.execution_count
                    }

                    # 添加任务消息
                    if task.task_msg:
                        task_data['task_msg'] = task.task_msg

                    # 添加可选字段
                    if task.start_time:
                        task_data['start_time'] = task.start_time
                    if task.end_time:
                        task_data['end_time'] = task.end_time
                        if task.start_time:
                            task_data['duration'] = task.end_time - task.start_time

                    tasks_by_date[task_date].append(task_data)

            # 保存每个日期的任务到对应文件
            for date, tasks in tasks_by_date.items():
                date_file = os.path.join(self.data_dir, f'task_history_{date}.json')

                # 只处理有变化的任务
                if len(tasks) > 0:
                    # 如果文件已存在，先读取现有内容
                    existing_tasks = []
                    if os.path.exists(date_file):
                        try:
                            with open(date_file, 'r', encoding='utf-8') as f:
                                existing_tasks = json.load(f)
                        except:
                            existing_tasks = []

                    # 合并任务数据（避免重复）
                    task_dict = {t['task_id']: t for t in existing_tasks}
                    for task in tasks:
                        task_dict[task['task_id']] = task

                    # 按时间戳排序
                    sorted_tasks = sorted(task_dict.values(), key=lambda x: x['timestamp'])

                    # 保存到文件
                    with open(date_file, 'w', encoding='utf-8') as f:
                        json.dump(sorted_tasks, f, ensure_ascii=False, indent=2)

            debug(f"已异步保存任务历史")
        except Exception as e:
            error(f"异步保存任务历史失败: {str(e)}")

    def _load_task_history(self):
        """从按日期分类的文件加载任务历史 - 优化版本"""
        try:
            # 重新导入datetime和timedelta，确保在任何环境中可用
            from datetime import datetime, timedelta

            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
                debug(f"创建数据目录: {self.data_dir}")
                return

            # 查找所有历史文件
            history_files = []
            for filename in os.listdir(self.data_dir):
                if filename.startswith('task_history_') and filename.endswith('.json'):
                    history_files.append(os.path.join(self.data_dir, filename))
                    debug(f"找到任务历史文件: {filename}")

            if not history_files:
                debug(f"没有找到任务历史文件")
                return

            # 按日期排序，先加载最近的任务
            history_files.sort(reverse=True)

            # 加载所有任务历史记录到缓存中，不再限制只加载活跃任务
            loaded_task_count = 0

            for file_path in history_files:
                file_name = os.path.basename(file_path)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tasks_data = json.load(f)

                    for task_data in tasks_data:
                        # 创建任务对象
                        # 为加载的任务获取锁
                        task_lock = self._get_task_lock(task_data['task_id'])

                        task = Task(
                            task_type=task_data['task_type'],
                            task_id=task_data['task_id'],
                            timestamp=task_data['timestamp'],
                            params=task_data.get('params', {}),
                            task_lock=task_lock,  # 传入任务锁
                            callback=lambda params: None  # 加载的任务不需要回调函数
                        )

                        # 恢复输出文件名
                        if 'output_filename' in task_data:
                            task.output_filename = task_data['output_filename']

                        # 恢复任务状态
                        task.status = task_data.get('status', 'queued')

                        # 恢复任务消息
                        if 'task_msg' in task_data:
                            task.task_msg = task_data['task_msg']

                        # 恢复时间信息
                        if 'start_time' in task_data:
                            task.start_time = task_data['start_time']
                        if 'end_time' in task_data:
                            task.end_time = task_data['end_time']

                        # 恢复执行次数
                        task.execution_count = task_data.get('execution_count', 1)

                        # 将任务添加到历史记录
                        self.task_history[task.task_id] = task
                        loaded_task_count += 1

                except Exception as e:
                    error(f"处理任务历史文件 {file_name} 失败: {str(e)}")

            debug(f"已加载任务历史，共 {loaded_task_count} 个任务")
        except Exception as e:
            error(f"加载任务历史失败: {str(e)}")

    def get_all_tasks(self, date=None):
        """获取所有任务历史记录，可选按日期筛选 - 优化版本
        
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
            debug(f"get_all_tasks被调用，date={date}，task_history长度={len(self.task_history)}")

            # 直接访问数据，不使用锁以提高查询速度
            # 获取运行中任务的ID集合
            running_task_ids = set(self.running_tasks.keys())

            # 获取任务类型计数器的副本
            task_type_counters_copy = self.task_type_counters.copy()

            # 获取历史任务的副本
            history_tasks = list(self.task_history.values())

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
            return []


# 全局任务队列管理器实例
task_queue_manager = TaskQueueManager(max_concurrent_tasks)

from typing import Optional, Dict, Any

from hengline.common import get_timestamp_by_type
from hengline.task.task_common import TaskCommonBorg
from hengline.task.task_queue import Task, TaskStatus


class TaskBase(TaskCommonBorg):
    """
    基于Borg模式的共享基类
    """

    """添加任务到运行中缓存"""

    def add_running_task(self, key, value: Task):
        with self._running_tasks_lock:
            self.running_tasks[key] = value

    def get_running_task(self, key):
        return self.running_tasks.get(key)

    """添加任务到历史记录缓存"""

    def add_history_task(self, key, value: Task):
        with self._history_tasks_lock:
            self.history_tasks[key] = value

    def get_history_task(self, key):
        task = self.history_tasks.get(key)
        if not task:
            task = next((v.get(key) for k, v in self.cache_query_tasks.items()), None)

        return task

    """添加任务到优先队列"""

    def add_queue_task(self, task: Task, priority=None):
        if priority:
            self.task_queue.put(priority, task)
        else:
            self.task_queue.put(task)

        with self._task_type_counters_lock:
            # 更新任务类型计数器
            self.task_type_counters[task.task_type] = self.task_type_counters.get(task.task_type, 0) + 1

    def get_queue_task(self):
        return self.task_queue.get(timeout=2)

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
        task_default_time = get_timestamp_by_type()  # 用于获取默认等待时间
        task_type_default_time = get_timestamp_by_type().get(task_type, 100)  # 默认等待时间，单位秒

        # 计算预计等待时间（基于平均执行时间）
        avg_duration = task_type_default_time
        if task_type and task_type in task_default_time:
            avg_duration = task_default_time[task_type] / 60  # 转换为分钟
        else:
            # 如果没有指定任务类型或任务类型不存在，使用所有类型的平均值
            avg_durations = list(task_default_time.values())
            if avg_durations:
                avg_duration = sum(avg_durations) / len(avg_durations) / 60  # 转换为分钟

        # 计算预计等待时间
        estimated_time = queued_count * avg_duration

        # 计算进度
        progress = 0
        if total_tasks > 0:
            progress = min(100, int((position / total_tasks) * 100))

        # 计算历史任务总数
        total_history_tasks = len(self.history_tasks)

        # 返回兼容测试文件的格式 - 修复缩进问题，确保总是返回字典
        return {
            "total_tasks": total_tasks,
            "in_queue": queued_count,
            "running_tasks": running_count,
            "position": position,
            "estimated_time": round(task_type_default_time / 60, 1) if estimated_time < 1 else round(estimated_time, 1),
            "progress": progress,
            "running_tasks_count": running_count,  # 保留原始字段以保持兼容性
            "queued_tasks_count": queued_count,  # 保留原始字段以保持兼容性
            "max_concurrent_tasks": self.task_max_concurrent,
            "average_task_durations": task_type_default_time,

            # 兼容测试文件的字段
            "queued_tasks": queued_count,  # 兼容test_get_queue_status.py
            "total_history_tasks": total_history_tasks,  # 兼容test_get_queue_status.py
            "avg_execution_time": task_type_default_time  # 兼容check_queue.py
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定任务的状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict[str, Any]]: 任务状态信息，如果任务不存在则返回None
        """
        task = self.get_history_task(task_id)
        if not task:
            return None

        # 确保状态值的正确性
        current_status = task.status

        # 优化：不再遍历整个队列来计算位置，避免长时间持锁
        queue_position = 1

        # 检查任务状态的一致性
        if TaskStatus.is_queued(current_status):
            # 检查是否在running_tasks中
            if task_id in self.running_tasks:
                current_status = TaskStatus.RUNNING.value
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

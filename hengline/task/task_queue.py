#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理模块
用于管理生图和生视频任务的排队执行
"""

import threading
import time
from enum import Enum
from typing import Dict, Any, Callable


# 导入邮件发送模块


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
        self.prompt_id = None  # 任务关联的，提交任务生成的prompt_id
        self.callback = callback  # 任务完成后的回调函数
        self.start_time = None  # 任务开始执行时间
        self.end_time = None  # 任务结束时间
        self.task_lock = task_lock  # 使用传入的任务锁
        self.status: str = TaskStatus.QUEUED.value  # 任务状态: queued, running, completed, failed
        self.output_filename = None  # 任务输出文件名（向后兼容）
        self.output_filenames = []  # 任务输出文件名列表，支持多个输出文件
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


class TaskStatus(Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'

    def __str__(self):
        return self.value

    @staticmethod
    def is_success(status) -> bool:
        return status == TaskStatus.SUCCESS.value

    @staticmethod
    def is_failed(status) -> bool:
        return status == TaskStatus.FAILED.value

    @staticmethod
    def is_running(status) -> bool:
        return status == TaskStatus.RUNNING.value

    @staticmethod
    def is_queued(status) -> bool:
        return status == TaskStatus.QUEUED.value

    @staticmethod
    def no_finished(status) -> bool:
        return status in [TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]

    @staticmethod
    def is_finished(status) -> bool:
        return status in [TaskStatus.SUCCESS.value, TaskStatus.FAILED.value]

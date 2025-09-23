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
from hengline.task.task_callback import task_callback_handler
from hengline.task.task_history import task_history
from hengline.task.task_queue import Task, TaskStatus
from hengline.utils.file_utils import generate_output_filename
from hengline.utils.log_utils import print_log_exception
from hengline.workflow.workflow_manage import workflow_manager

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.logger import error, warning, debug, info
from hengline.task.task_manage import task_queue_manager
# 导入邮件发送模块
from hengline.task.task_email import async_send_failure_email
# 导入工作流状态检查器
from hengline.workflow.workflow_status_checker import workflow_status_checker

# 导入SocketIO路由模块，用于WebSocket初始化
from hengline.flask.route.socketio_route import init_socketio


class StartupTaskListener(TaskBase):
    """启动任务监听器类，只在应用启动时运行一次"""

    def __init__(self):
        """初始化启动任务监听器"""
        super().__init__()
        self.lock = Lock()
        self._init_running = False
        self._init_thread = None
        self._init_instance_id = None  # 生成一个简短的实例ID
        self._init_process_id = os.getpid()  # 获取当前进程ID
        self._task_init_lock = threading.Lock()  # 添加线程锁以防止并发执行

    def start(self):
        """启动监听器，处理历史任务"""

        with self._task_init_lock:
            if self._init_running:
                debug("历史任务监控器已经在运行中")
                return

            info("=" * 50)
            info("          启动历史任务监听器          ")
            info("=" * 50)

            self._init_instance_id = str(uuid.uuid4())[:8]  # 生成一个简短的实例ID
            self._init_running = True
            self._init_thread = threading.Thread(target=self._process_historical_tasks, name=f"StartupTaskListenerThread-{self._init_instance_id}")
            self._init_thread.daemon = True
            self._init_thread.start()

            info(f"历史任务监控器已启动({threading.current_thread().name}) - 实例ID: {self._init_instance_id}, 进程ID: {self._init_process_id}")

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
            if TaskStatus.is_queued(task.status):
                # 排队中的任务，直接加入队列
                task_queue_manager.requeue_task(task.task_id, task.task_type, "排队中的任务重新加入队列", workflow_manager.execute_common)
            elif TaskStatus.is_failed(task.status):
                # 失败的任务，根据重试次数决定是否重新加入队列
                if task.execution_count <= self.task_max_retry:
                    task_queue_manager.requeue_task(task.task_id, task.task_type, f"失败任务重新加入队列，当前重试次数: {task.execution_count}", workflow_manager.execute_common)
                else:
                    warning(f"任务 {task.task_id} 重试次数已达上限，不再重新加入队列")
                    # 标记为最终失败
                    task_queue_manager.mark_task_as_final_failure(task.task_id, task.task_type, task.execution_count)
                    return
            elif TaskStatus.is_running(task.status):
                # 运行中的任务，加入异步结果检查
                self._handle_running_task_with_async_check(task.task_id, task.task_type)

        except Exception as e:
            error(f"处理任务 {task.task_type} 时发生异常: {str(e)}")
            print_log_exception()

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
                task_queue_manager.requeue_task(task_id, task.task_type, "运行中任务但无开始时间，重新加入队列", workflow_manager.execute_common)
                return

            # 计算任务已运行时间
            current_time = time.time()
            runtime_seconds = current_time - task.start_time

            # 如果超过最大运行时间，直接标记为失败
            if runtime_seconds > self.task_timeout_seconds:
                debug(f"任务 {task_id} 运行时间超过{self.task_timeout_seconds} 秒，标记为失败")
                task.status = TaskStatus.FAILED.value
                task.task_msg = f"任务运行时间超过{self.task_timeout_seconds} 秒上限"
                task.end_time = current_time

                # 从运行中任务列表移除
                with self._running_tasks_lock:
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]

                # 保存任务历史
                task_history.async_save_task_history()

                # 发送失败邮件
                async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)
                return

            # 如果没有prompt_id，则重新加入队列
            if not task.prompt_id:
                debug(f"任务 {task_id} 没有prompt_id，重新加入队列")
                task_queue_manager.requeue_task(task_id, task.task_type, "任务可能没提交，重新执行一次", workflow_manager.execute_common)
                time.sleep(1)  # 短暂等待，避免过快重试

            # 计算剩余超时时间（基于最大运行时间）
            remaining_time_seconds = max(0, self.task_timeout_seconds - runtime_seconds)
            timeout_seconds = min(7200, remaining_time_seconds)  # 最大超时1小时

            # 加入异步结果检查
            debug(f"将任务 {task_id} 加入异步结果检查，prompt_id: {task.prompt_id}")
            workflow_status_checker.check_workflow_status_async(
                prompt_id=task.prompt_id,
                output_name=generate_output_filename(task_type),
                api_url=self.comfyui_api_url,
                on_complete=task_callback_handler.handle_workflow_completion,
                on_timeout=task_callback_handler.handle_workflow_timeout,
                timeout_seconds=timeout_seconds,
                task_id=task_id
            )
        except Exception as e:
            error(f"处理运行中任务 {task_id} 时发生异常: {str(e)}")
            print_log_exception()
            # 发生异常时，尝试将任务重新加入队列
            try:
                task_queue_manager.requeue_task(task_id, task_type, "查询状态异常，重新加入队列", workflow_manager.execute_common)
            except:
                pass


# 创建全局启动任务监听器实例
task_init = StartupTaskListener()

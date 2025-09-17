# -*- coding: utf-8 -*-
"""
任务监控器模块
用于定期检查任务状态并处理失败重试
"""

import os
import threading
import time
import uuid
from typing import Callable

# 导入自定义日志模块
from hengline.logger import error, debug, warning, info
from hengline.task.task_base import TaskBase
from hengline.task.task_email import async_send_failure_email, async_send_success_email
from hengline.task.task_history import task_history
from hengline.task.task_queue import Task, TaskStatus
from hengline.utils.log_utils import print_log_exception


class TaskMonitor(TaskBase):
    """任务监控器类"""

    def __init__(self):
        """
        初始化任务监控器

        """
        super().__init__()
        self._monitor_running = False
        self._monitor_thread = None
        self.comfyui_runner = None
        self._monitor_instance_id = str(uuid.uuid4())[:8]  # 生成一个简短的实例ID  # 生成一个简短的实例ID
        self._monitor_process_id = os.getpid()  # 获取当前进程ID
        self._task_monitor_lock = threading.Lock()  # 添加线程锁以防止并发执行

    def start(self):
        """启动任务监控器"""
        with self._task_monitor_lock:
            if self._monitor_running:
                debug("队列任务监控器已经在运行中")
                return

            info("=" * 50)
            info("          启动实时任务监听器          ")
            info("=" * 50)

            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, name=f"TaskMonitorThread-{self._monitor_instance_id}")
            self._monitor_thread.daemon = True
            self._monitor_thread.start()

            info(f"队列任务监控器已启动({threading.current_thread().name}) - 实例ID: {self._monitor_instance_id}, 进程ID: {self._monitor_process_id}")

    def stop(self):
        """停止任务监控器"""
        with self._task_monitor_lock:
            if not self._monitor_running:
                warning("队列任务监控器未运行")
                return

            # 将队列中排队的任务添加到任务历史记录中
            temp_tasks = []
            while not self.task_queue.empty():
                task = self.task_queue.get()
                temp_tasks.append(task)
                # 将任务添加到历史记录，保持"queued"状态
                self.add_history_task(task.task_id, task)
                debug(f"将排队任务添加到历史记录: {task.task_id}, 类型: {task.task_type}")

            # 保存任务历史
            task_history.save_task_history()

            self._monitor_running = False
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)

            debug("任务队列管理器已关闭，已保存所有排队任务到历史记录")

    def _monitor_loop(self):
        """监控循环"""
        current_thread = threading.current_thread()

        debug(f"监控循环开始执行 - 线程ID: {current_thread.ident}, 线程名称: {current_thread.name}")

        while self._monitor_running:
            try:
                self._process_tasks()
            except Exception as e:
                error(f"任务检查过程中出错: {str(e)}")
                print_log_exception()
            finally:
                # 等待指定的检查间隔
                time.sleep(0.5)

        debug(f"任务监控器线程已退出 - 线程ID: {current_thread.ident}, 线程名称: {current_thread.name}")

    def _process_tasks(self):
        """处理队列中的任务 - 任务级锁优化版本"""
        # 检查是否可以启动新任务
        current_running = len(self.running_tasks)

        if current_running < self.task_max_concurrent and not self.task_queue.empty():
            try:
                task = None
                task_lock = None

                # 获取下一个任务
                if not self.task_queue.empty() and len(self.running_tasks) < self.task_max_concurrent:
                    task = self.task_queue.get_nowait()
                    task_lock = self._get_task_lock(task.task_id)

                    # 减少任务类型计数器
                    self.task_type_counters[task.task_type] = max(0, self.task_type_counters.get(task.task_type,
                                                                                                 0) - 1)

                if task and task_lock:
                    # 使用任务级锁更新任务状态
                    with task_lock:
                        # 再次检查是否可以启动新任务
                        if len(self.running_tasks) >= self.task_max_concurrent:
                            # 无法启动新任务，将任务放回队列
                            self.add_queue_task(task)
                            return

                            # 更新任务状态和执行次数
                        task.status = TaskStatus.RUNNING.value
                        task.start_time = time.time()
                        task.execution_count += 1  # 执行次数加1
                        self.add_running_task(task.task_id, task)

                        # 记录到历史
                        self.add_history_task(task.task_id, task)

                    debug(f"开始执行任务: {task.task_id}, 类型: {task.task_type}")

                    # 直接异步保存任务历史，避免阻塞
                    task_history.async_save_task_history()

                    # 启动任务线程
                    task_thread = threading.Thread(
                        target=self._execute_task,
                        args=(task, self.task_timeout_seconds)
                    )
                    task_thread.daemon = True
                    task_thread.start()

            except Exception as e:
                error(f"处理队列任务时发生错误: {str(e)}")
                print_log_exception()



    def _execute_task(self, task: Task, timeout: int = 1800):
        """执行单个任务 - 异步版本"""
        task_lock = self._get_task_lock(task.task_id)

        try:
            # 定义任务完成后的回调函数
            def task_completion_callback(result, exception=None):
                nonlocal task_lock
                try:
                    # 使用任务级锁更新任务状态
                    with task_lock:
                        # 检查是否遇到异常
                        if exception:
                            task.status = TaskStatus.FAILED.value
                            task.task_msg = f"任务执行异常: {str(exception)}"
                            task.end_time = time.time()
                        # 检查任务是否遇到连接异常
                        elif result and isinstance(result, dict) and result.get(TaskStatus.QUEUED.value):
                            # 从配置中获取最大重试次数（默认为3）
                            # 检查是否超过最大重试次数
                            if task.execution_count > self.task_max_retry:
                                warning(f"任务 {task.task_id} 执行次数已达到最大限制 {self.task_max_retry}，不再重试")
                                task.status = TaskStatus.FAILED.value
                                task.task_msg = f"ComfyUI 工作流连接超时，任务已重试 {self.task_max_retry} 次。请检查ComfyUI服务器是否运行，或配置中URL是否正确。"
                                task.end_time = time.time()

                                async_send_failure_email(task.task_id, task.task_type, task.task_msg, self.task_max_retry)

                            else:
                                # 如果未超过最大重试次数，将任务重新加入队列
                                warning(f"任务执行失败，ComfyUI服务器连接异常，将任务重新加入队列: {task.task_id}")
                                task.status = TaskStatus.QUEUED.value
                                task.task_msg = "ComfyUI 工作流连接超时，任务将在稍后重试。请检查ComfyUI服务器是否运行，或配置中URL是否正确。"
                                task.end_time = None  # 清除结束时间

                                # 将任务重新加入队列
                                self.add_queue_task(task)

                        elif result is None:
                            # 任务未返回结果，可能是执行过程中出错
                            task.status = TaskStatus.FAILED.value
                            task.task_msg = f"任务执行未返回结果: {task.task_id}"
                            task.end_time = time.time()

                            async_send_failure_email(task.task_id, task.task_type, task.task_msg, task.execution_count)

                        elif isinstance(result, dict) and not result.get('success', True):
                            # 任务返回结果但标记为失败
                            task.status = TaskStatus.FAILED.value
                            task.task_msg = result.get('message', '任务执行失败')
                            task.end_time = time.time()
                        else:
                            # 任务执行成功，但需要等待实际工作流完成
                            # 不立即设置为completed状态
                            task.status = TaskStatus.RUNNING.value
                            task.task_msg = "任务已提交到工作流服务器，正在处理..."

                            # 保存输出文件名（如果有）
                            if result and isinstance(result, dict):
                                # 处理多个输出文件
                                if 'output_paths' in result:
                                    # 从output_paths中提取文件名列表
                                    task.output_filenames = [os.path.basename(path) for path in result['output_paths']]
                                    # 设置第一个输出文件为默认输出文件名（向后兼容）
                                    if task.output_filenames:
                                        task.output_filename = task.output_filenames[0]
                                elif 'filenames' in result:
                                    task.output_filenames = result['filenames']
                                    # 设置第一个输出文件为默认输出文件名（向后兼容）
                                    if task.output_filenames:
                                        task.output_filename = task.output_filenames[0]
                                # 处理单个输出文件（向后兼容）
                                elif 'output_path' in result:
                                    # 从output_path中提取文件名
                                    task.output_filename = os.path.basename(result['output_path'])
                                    # 同时添加到文件名列表中
                                    task.output_filenames = [task.output_filename]
                                elif 'filename' in result:
                                    task.output_filename = result['filename']
                                    # 同时添加到文件名列表中
                                    task.output_filenames = [task.output_filename]

                        # 从运行中任务列表移除
                        if task.task_id in self.running_tasks and not TaskStatus.is_running(task.status):
                            del self.running_tasks[task.task_id]

                        # 直接异步保存任务历史，避免阻塞
                        task_history.async_save_task_history()

                    info(f"任务执行状态更新: {task.task_id}, 类型: {task.task_type}, 状态: {task.status}")

                    # 异步发送邮件通知
                    if TaskStatus.is_success(task.status):
                        async_send_success_email(task.task_id, task.task_type, task.start_time, task.end_time)
                    elif TaskStatus.is_failed(task.status):
                        async_send_failure_email(task.task_id, task.task_type, task.task_msg, task.execution_count)

                except Exception as e:
                    error(f"任务完成回调处理异常: {task.task_id}, 错误: {str(e)}")
                    print_log_exception()

            # 使用异步方式执行回调函数，不阻塞主线程
            self._execute_callback_async(task, timeout, task_completion_callback)

        except Exception as e:
            error(f"任务执行异常: {task.task_id}, 错误: {str(e)}")
            print_log_exception()
            # 使用任务级锁更新任务状态
            with task_lock:
                task.status = TaskStatus.FAILED.value
                task.task_msg = f"任务执行异常了: {str(e)}"
                task.end_time = time.time()

                # 从运行中任务列表移除
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]

                # 直接异步保存任务历史，避免阻塞
                task_history.async_save_task_history()


    @staticmethod
    def _execute_callback_async(task: Task, timeout: int = 1800, completion_callback: Callable = None):
        """
        异步执行任务回调函数，支持同步和异步回调

        Args:
            task: 任务对象
            timeout: 超时时间（秒）
            completion_callback: 任务完成后的回调函数
        """
        import asyncio
        import inspect

        result = None
        exception = None
        task_completed = False

        # 创建一个线程来执行回调函数
        def callback_thread_func():
            nonlocal result, exception, task_completed
            try:
                # 检查回调函数是否是协程函数
                if inspect.iscoroutinefunction(task.callback):
                    # 对于协程函数，使用asyncio执行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # 使用事件循环运行协程函数
                        result =  loop.run_until_complete(
                            asyncio.wait_for(
                                task.callback(task.task_type, task.params, task.task_id),
                                timeout=timeout - 10  # 留出一点时间处理超时逻辑
                            )
                        )
                    except asyncio.TimeoutError:
                        raise TimeoutError(f"任务执行超时({timeout}秒)")
                    finally:
                        loop.close()
                else:
                    # 对于普通函数，直接调用
                    result = task.callback(task.params)
                    task_completed = True
            except Exception as e:
                error(f"任务执行异常: {task.task_id}, 错误: {str(e)}")
                print_log_exception()
                exception = e
                task_completed = True
            finally:
                # 如果任务已完成，调用完成回调
                if task_completed:
                    if exception:
                        completion_callback(None, exception)
                    else:
                        completion_callback(result)

        # 启动线程执行回调
        callback_thread = threading.Thread(target=callback_thread_func)
        callback_thread.daemon = True
        callback_thread.start()

        # 创建一个超时检测线程
        def timeout_check_thread_func():
            nonlocal task_completed
            # 等待指定时间
            time.sleep(timeout)
            # 检查任务是否已完成
            if not task_completed:
                error(f"任务执行超时: {task.task_id}")
                completion_callback({'success': False, 'message': f'任务执行超时({timeout}秒)', 'timeout': True})

        # 启动超时检测线程
        timeout_thread = threading.Thread(target=timeout_check_thread_func)
        timeout_thread.daemon = True
        timeout_thread.start()


# 全局任务监控器实例
task_monitor = TaskMonitor()

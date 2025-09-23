#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流状态检查器模块
用于异步定时检查ComfyUI工作流的执行状态
"""
import functools
import threading
import time
import weakref
from typing import Callable

import requests

from hengline.logger import debug, error, warning
from hengline.utils.config_utils import get_task_config
from hengline.utils.log_utils import print_log_exception

# 导入SocketIO路由模块，用于实时推送任务状态
from hengline.flask.route.socketio_route import emit_task_status_update


class WorkflowStatusChecker:
    """异步定时任务队列，用于检查工作流执行状态"""

    def __init__(self):
        """初始化工作流状态检查器"""
        self.checking_tasks = {}
        self.checking_tasks_lock = threading.Lock()
        self.default_check_interval = 10  # 默认检查间隔（秒）
        self.max_check_interval = 30  # 最大检查间隔（秒）
        self.task_timeout_seconds = get_task_config().get('task_timeout_seconds', 1800)  # 默认超时时间
        self.max_consecutive_failures = get_task_config().get('task_max_retry', 5)  # 连续失败次数上限

    def check_workflow_status_async(self, prompt_id: str, api_url: str, output_name: str,
                                    on_complete: Callable[[str, bool], None],
                                    on_timeout: Callable[[str], None],
                                    check_interval: int = None,
                                    timeout_seconds: int = None,
                                    task_id: str = None) -> str:
        """
        异步检查工作流状态
        
        Args:
            prompt_id: 工作流的prompt_id
            api_url: ComfyUI API的基础URL
            on_complete: 工作流完成时的回调函数
            on_timeout: 工作流超时时的回调函数
            check_interval: 检查间隔（秒），默认为None（使用默认值）
            timeout_seconds: 超时时间（秒），默认为None（使用默认值）
            task_id: 可选的外部任务ID，如果不提供则内部生成
        
        Returns:
            str: 任务ID，用于后续操作
        """
        # 如果没有提供task_id，则在内部生成
        if task_id is None:
            task_id = f"check_{prompt_id}_{int(time.time())}"
        check_interval = check_interval if check_interval else self.default_check_interval
        timeout_seconds = timeout_seconds if timeout_seconds else self.task_timeout_seconds
        max_consecutive_failures = self.max_consecutive_failures

        # 限制检查间隔在合理范围内
        check_interval = max(1, min(check_interval, self.max_check_interval))

        # 记录任务信息
        task_info = {
            'prompt_id': prompt_id,
            'api_url': api_url,
            'start_time': time.time(),
            'check_interval': check_interval,
            'output_name': output_name,
            'timeout_seconds': timeout_seconds,
            'on_complete': on_complete,
            'on_timeout': on_timeout,
            'consecutive_failures': 0,
            'max_consecutive_failures': max_consecutive_failures
        }

        with self.checking_tasks_lock:
            self.checking_tasks[task_id] = task_info

        # 启动异步检查
        self._schedule_check(task_id)

        debug(f"已启动异步工作流状态检查，任务ID: {task_id}, prompt_id: {prompt_id}")
        return task_id

    def _schedule_check(self, task_id: str):
        """安排下一次检查"""
        with self.checking_tasks_lock:
            if task_id not in self.checking_tasks:
                return

            task_info = self.checking_tasks[task_id]
            check_interval = task_info['check_interval']

        # 创建定时器，在指定间隔后执行检查
        timer = threading.Timer(check_interval, self._check_workflow_status, args=[task_id])
        timer.daemon = True
        timer.start()

    def _check_workflow_status(self, task_id: str):
        """检查工作流状态的核心方法"""
        with self.checking_tasks_lock:
            if task_id not in self.checking_tasks:
                debug(f"任务ID {task_id} 不在检查任务列表中，跳过检查")
                return

            task_info = self.checking_tasks[task_id].copy()

        prompt_id = task_info['prompt_id']
        api_url = task_info['api_url']
        start_time = task_info['start_time']
        output_name = task_info['output_name']
        timeout_seconds = task_info['timeout_seconds']
        on_complete = task_info['on_complete']
        on_timeout = task_info['on_timeout']
        consecutive_failures = task_info['consecutive_failures']
        max_consecutive_failures = task_info['max_consecutive_failures']

        # 检查是否超时
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            debug(f"工作流状态检查超时，任务ID: {task_id}, prompt_id: {prompt_id}")

            # 执行超时回调
            try:
                callback_with_args = functools.partial(
                    on_timeout,
                    task_id,
                    prompt_id
                )

                weak_callback = weakref.ref(callback_with_args)
                # 调用弱引用回调
                if weak_callback() is not None:
                    weak_callback()()
                else:
                    warning("weak_callback(on_timeout) 对象已被垃圾回收")

            except Exception as e:
                error(f"执行超时回调时出错: {str(e)}")
                print_log_exception()

            # 移除任务
            with self.checking_tasks_lock:
                self.checking_tasks.pop(task_id, None)

            return

        try:
            # 发送请求检查工作流状态
            response = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)  # 增加超时时间到10秒
            if response.status_code == 200:
                history = response.json()

                # 确保history是字典类型
                if not isinstance(history, dict):
                    debug(f"历史记录不是字典类型，而是: {type(history)}")
                    # 增加检查间隔但继续检查
                    with self.checking_tasks_lock:
                        if task_id in self.checking_tasks:
                            self.checking_tasks[task_id]['check_interval'] = min(
                                self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                            )

                    self._schedule_check(task_id)
                    return

                if prompt_id in history:
                    prompt_data = history[prompt_id]

                    # 确保prompt_data是字典类型
                    if not isinstance(prompt_data, dict):
                        debug(f"prompt_data不是字典类型，而是: {type(prompt_data)}")
                        # 增加检查间隔但继续检查
                        with self.checking_tasks_lock:
                            if task_id in self.checking_tasks:
                                self.checking_tasks[task_id]['check_interval'] = min(
                                    self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                                )

                        self._schedule_check(task_id)
                        return

                    # 检查工作流是否完成
                    if "outputs" in prompt_data:
                        # {'9': {'images': [{'filename': 'ComfyUI_00055_.png', 'subfolder': '', 'type': 'output'}]}}
                        debug(f"工作流处理完成，任务ID: {task_id}, prompt_id: {prompt_id}, 输出: {prompt_data['outputs']}")

                        file_num = 0
                        file_name = '图像文件'
                        for value in prompt_data['outputs'].values():
                            if 'images' in value:
                                images_list = value.get('images', [])
                                file_num += len(images_list)
                                file_name = '图像文件'
                            elif 'video' in value:
                                videos_list = value.get('video', [])
                                file_num += len(videos_list)
                                file_name = '视频文件'
                            elif 'audio' in value:
                                audios_list = value.get('audio', [])
                                file_num += len(audios_list)
                                file_name = '音频文件'
                            else:
                                files_list = value.get('text', [])
                                file_num += len(files_list)
                                file_name = '文本'

                        # 执行完成回调，标记为成功
                        msg = f"共生成 {file_num} 个 {file_name} "
                        self.callback_with_complete(task_id, prompt_id, True, output_name, msg, on_complete)

                        return
                    elif "error" in prompt_data:
                        # 工作流执行出错
                        debug(f"工作流执行出错，任务ID: {task_id}, prompt_id: {prompt_id}, 错误: {prompt_data['error']}")

                        # 执行完成回调，标记为失败
                        self.callback_with_complete(task_id, prompt_id, False, output_name
                                                    , f"工作流执行出错，任务ID: {task_id}, 错误: {prompt_data['error']}", on_complete)
                        return
                    else:
                        # 工作流仍在执行中，增加检查间隔但继续检查
                        with self.checking_tasks_lock:
                            if task_id in self.checking_tasks:
                                self.checking_tasks[task_id]['check_interval'] = min(
                                    self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                                )

                        self._schedule_check(task_id)
                        return
                else:
                    # prompt_id不在历史记录中，可能仍在处理中
                    debug(f"prompt_id {prompt_id} 不在历史记录中，可能仍在处理中")

                    # 增加检查间隔但继续检查
                    with self.checking_tasks_lock:
                        if task_id in self.checking_tasks:
                            self.checking_tasks[task_id]['check_interval'] = min(
                                self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                            )

                    self._schedule_check(task_id)
                    return
            else:
                # 非200响应码，记录错误但继续尝试
                debug(f"获取历史记录失败，状态码: {response.status_code}, 任务ID: {task_id}, prompt_id: {prompt_id}")

                # 重置连续失败计数
                with self.checking_tasks_lock:
                    if task_id in self.checking_tasks:
                        self.checking_tasks[task_id]['consecutive_failures'] = 0

                # 继续检查
                self._schedule_check(task_id)
                return

        except requests.exceptions.ConnectionError:
            # 特别处理连接错误，这通常表示ComfyUI服务宕机
            consecutive_failures += 1
            error(f"ComfyUI服务连接失败（第{consecutive_failures}次）: 服务器可能已宕机")

            # 更新连续失败计数
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['consecutive_failures'] = consecutive_failures

            # 如果连续失败次数过多，视为服务宕机
            if consecutive_failures >= max_consecutive_failures:
                error(f"连续{max_consecutive_failures}次连接ComfyUI服务失败，确认服务器已宕机")

                # 执行完成回调，标记为失败
                self.callback_with_complete(task_id, prompt_id, False, output_name
                                            , "ComfyUI服务连接失败，服务器可能已宕机", on_complete)

                return

            # 增加检查间隔但继续检查
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['check_interval'] = min(
                        self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                    )

            self._schedule_check(task_id)
        except Exception as e:
            consecutive_failures += 1
            error(f"检查工作流状态时出错（第{consecutive_failures}次）: {str(e)}")
            print_log_exception()

            # 更新连续失败计数
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['consecutive_failures'] = consecutive_failures

            # 如果连续失败次数过多，视为连接失败
            if consecutive_failures >= max_consecutive_failures:
                error(f"连续{max_consecutive_failures}次检查工作流状态失败，认为连接失败")

                # 执行完成回调，标记为失败
                self.callback_with_complete(task_id, prompt_id, False, output_name
                                            , "检查工作流状态失败，可能连接有问题，请检查ComfyUI服务是否正常运行", on_complete)
                return

            # 增加检查间隔但继续检查
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['check_interval'] = min(
                        self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                    )

            self._schedule_check(task_id)

    def callback_with_complete(self, task_id: str, prompt_id: str, success: bool, output_name: str, msg: str, on_complete):

        # 执行完成回调，标记为失败
        try:
            callback_with_args = functools.partial(
                on_complete,
                task_id,
                prompt_id,
                success,
                output_name,
                msg
            )

            weak_callback = weakref.ref(callback_with_args)
            # 调用弱引用回调
            if weak_callback() is not None:
                weak_callback()()
            else:
                warning("weak_callback_complete 对象已被垃圾回收")

            # 通过WebSocket推送任务状态更新
            try:
                # 从task_id中提取原始任务ID（去掉可能的前缀）
                original_task_id = task_id
                if task_id.startswith('check_'):
                    parts = task_id.split('_', 2)
                    if len(parts) > 2:
                        # 尝试从剩余部分中提取原始任务ID
                        # 假设格式为 'check_promptId_timestamp'
                        potential_task_id = parts[1]  # 使用prompt_id作为任务标识
                        original_task_id = potential_task_id
                
                emit_task_status_update(original_task_id, {
                    'task_id': original_task_id,
                    'prompt_id': prompt_id,
                    'status': 'completed' if success else 'failed',
                    'message': msg,
                    'output_name': output_name,
                    'completion_time': time.time(),
                    'progress': 100 if success else 0
                })
                debug(f"通过WebSocket推送工作流状态更新: {original_task_id}, 状态: {'completed' if success else 'failed'}")
            except Exception as e:
                error(f"推送工作流状态更新失败: {str(e)}")

            # 移除任务
            with self.checking_tasks_lock:
                self.checking_tasks.pop(task_id, None)

        except Exception as e:
            error(f"weak_callback_complete 执行完成回调时出错: {str(e)}")
            print_log_exception()

    def cancel_check(self, task_id: str) -> bool:
        """
        取消工作流状态检查

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        with self.checking_tasks_lock:
            if task_id in self.checking_tasks:
                self.checking_tasks.pop(task_id, None)
                debug(f"已取消工作流状态检查，任务ID: {task_id}")
                return True

            debug(f"未找到要取消的工作流状态检查任务，任务ID: {task_id}")
            return False

    def get_checking_tasks_count(self) -> int:
        """
        获取当前正在检查的任务数量

        Returns:
            int: 任务数量
        """
        with self.checking_tasks_lock:
            return len(self.checking_tasks)

    def shutdown(self):
        """关闭检查器，清除所有检查任务"""
        with self.checking_tasks_lock:
            task_count = len(self.checking_tasks)
            self.checking_tasks.clear()
            debug(f"已关闭工作流状态检查器，清除了 {task_count} 个检查任务")


# 创建全局工作流状态检查器实例
workflow_status_checker = WorkflowStatusChecker()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流状态检查器模块
用于异步定时检查ComfyUI工作流的执行状态
"""

import threading
import time
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from hengline.logger import debug, error, info
from hengline.utils.config_utils import get_task_config

import requests


class WorkflowStatusChecker:
    """异步定时任务队列，用于检查工作流执行状态"""
    
    def __init__(self):
        """初始化工作流状态检查器"""
        self.checking_tasks = {}
        self.checking_tasks_lock = threading.Lock()
        self.default_check_interval = 5  # 默认检查间隔（秒）
        self.max_check_interval = 30  # 最大检查间隔（秒）
        self.task_timeout_seconds = get_task_config().get('task_timeout_seconds', 1800)  # 默认超时时间
        self.max_consecutive_failures = get_task_config().get('task_view_max_retries', 5)  # 连续失败次数上限
    
    def check_workflow_status_async(self, prompt_id: str, api_url: str, 
                                  on_complete: Callable[[str, bool], None],
                                  on_timeout: Callable[[str], None],
                                  check_interval: int = None, 
                                  timeout_seconds: int = None) -> str:
        """
        异步检查工作流状态
        
        Args:
            prompt_id: 工作流的prompt_id
            api_url: ComfyUI API的基础URL
            on_complete: 工作流完成时的回调函数
            on_timeout: 工作流超时时的回调函数
            check_interval: 检查间隔（秒），默认为None（使用默认值）
            timeout_seconds: 超时时间（秒），默认为None（使用默认值）
        
        Returns:
            str: 任务ID，用于后续操作
        """
        task_id = f"check_{prompt_id}_{int(time.time())}"
        check_interval = check_interval or self.default_check_interval
        timeout_seconds = timeout_seconds or self.task_timeout_seconds
        max_consecutive_failures = self.max_consecutive_failures
        
        # 限制检查间隔在合理范围内
        check_interval = max(1, min(check_interval, self.max_check_interval))
        
        # 记录任务信息
        task_info = {
            'prompt_id': prompt_id,
            'api_url': api_url,
            'start_time': time.time(),
            'check_interval': check_interval,
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
                on_timeout(prompt_id)
            except Exception as e:
                error(f"执行超时回调时出错: {str(e)}")
            
            # 移除任务
            with self.checking_tasks_lock:
                self.checking_tasks.pop(task_id, None)
            
            return
        
        try:
            # 发送请求检查工作流状态
            response = requests.get(f"{api_url}/history/{prompt_id}", timeout=5)
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
                        debug(f"工作流处理完成，任务ID: {task_id}, prompt_id: {prompt_id}")
                        
                        # 执行完成回调
                        try:
                            on_complete(prompt_id, True)
                        except Exception as e:
                            error(f"执行完成回调时出错: {str(e)}")
                        
                        # 移除任务
                        with self.checking_tasks_lock:
                            self.checking_tasks.pop(task_id, None)
                        
                        return
            
            # 重置连续失败计数
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['consecutive_failures'] = 0
            
            # 继续检查
            self._schedule_check(task_id)
            
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
                try:
                    on_complete(prompt_id, False)
                except Exception as e:
                    error(f"执行完成回调时出错: {str(e)}")
                
                # 移除任务
                with self.checking_tasks_lock:
                    self.checking_tasks.pop(task_id, None)
                
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
            
            # 更新连续失败计数
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['consecutive_failures'] = consecutive_failures
            
            # 如果连续失败次数过多，视为连接失败
            if consecutive_failures >= max_consecutive_failures:
                error(f"连续{max_consecutive_failures}次检查工作流状态失败，认为连接失败")
                
                # 执行完成回调，标记为失败
                try:
                    on_complete(prompt_id, False)
                except Exception as e:
                    error(f"执行完成回调时出错: {str(e)}")
                
                # 移除任务
                with self.checking_tasks_lock:
                    self.checking_tasks.pop(task_id, None)
                
                return
            
            # 增加检查间隔但继续检查
            with self.checking_tasks_lock:
                if task_id in self.checking_tasks:
                    self.checking_tasks[task_id]['check_interval'] = min(
                        self.checking_tasks[task_id]['check_interval'] * 1.5, self.max_check_interval
                    )
            
            self._schedule_check(task_id)
    
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
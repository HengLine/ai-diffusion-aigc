#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动任务监听器模块

功能：
1. 在应用程序启动时只查询一次历史记录
2. 筛选今天未完成且重试未超过3次的任务
3. 根据不同任务状态进行相应处理并加入队列
4. 处理完成后自动结束，不再定时运行
"""

import os
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from threading import Lock

from .logger import info, error, warning, debug
from .task_queue_utils import task_queue_manager
from .workflow_utils import config


class StartupTaskListener:
    """启动任务监听器类，只在应用启动时运行一次"""
    
    def __init__(self):
        """初始化启动任务监听器"""
        self.lock = Lock()
        self.processed_tasks_count = 0
        self.max_retry_count = 3  # 最大重试次数
        self.max_runtime_hours = 2  # 最大运行时间（小时）
        self.comfyui_api_url = config.get('comfyui', {}).get('api_url', 'http://127.0.0.1:8188')
        
    def start(self):
        """启动监听器，处理历史任务"""
        info("="*50)
        info("          启动历史任务监听器          ")
        info("="*50)
        
        try:
            # 获取今天的日期
            today_date = datetime.now().strftime('%Y-%m-%d')
            info(f"当前日期: {today_date}")
            
            # 加载并处理历史任务
            self._process_historical_tasks(today_date)
            
            info(f"启动任务监听器处理完成，共处理了 {self.processed_tasks_count} 个任务")
            info("启动任务监听器已结束")
            info("="*50)
            
        except Exception as e:
            error(f"启动任务监听器执行异常: {str(e)}")
    
    def _process_historical_tasks(self, today_date: str):
        """处理历史任务
        
        Args:
            today_date: 今天的日期，格式为'YYYY-MM-DD'
        """
        # with self.lock:
        # 获取所有任务历史记录
        all_tasks = task_queue_manager.get_all_tasks(today_date)
        info(f"总任务历史记录数: {len(all_tasks)}")
        
        # 筛选今天未完成且重试未超过3次的任务
        pending_tasks = []
        
        for task_info in all_tasks:
            # 检查是否为今天的任务
            # task_date = datetime.fromtimestamp(task_info['timestamp']).strftime('%Y-%m-%d')
            # if task_date != today_date:
            #     continue
            
            # 检查是否未完成（状态为queued、failed或running）
            if task_info['status'] not in ['failed', 'running']:
                continue
            
            # 检查重试次数是否未超过3次
            execution_count = task_info.get('execution_count', 1)
            if execution_count > self.max_retry_count:
                warning(f"任务 {task_info['task_id']} 重试次数已超过{self.max_retry_count}次，跳过处理")
                continue
            
            pending_tasks.append(task_info)
            
            debug(f"符合条件的待处理任务数: {len(pending_tasks)}")
            
            # 按时间戳排序（最早的任务优先）
            pending_tasks.sort(key=lambda x: x['timestamp'])
            
            # 处理每个任务
            for task_info in pending_tasks:
                self._process_task(task_info)
    
    def _process_task(self, task_info: Dict[str, Any]):
        """处理单个任务，根据状态进行相应操作
        
        Args:
            task_info: 任务信息字典
        """
        try:
            task_id = task_info['task_id']
            task_type = task_info['task_type']
            status = task_info['status']
            execution_count = task_info.get('execution_count', 1)
            
            info(f"处理任务: {task_id}, 类型: {task_type}, 状态: {status}, 执行次数: {execution_count}")
            
            # 根据不同状态进行处理
            if status == 'queued':
                # 排队中的任务，直接加入队列
                self._requeue_task(task_id, task_type, "排队中的任务重新加入队列")
            elif status == 'failed':
                # 失败的任务，根据重试次数决定是否重新加入队列
                if execution_count <= self.max_retry_count:
                    self._requeue_task(task_id, task_type, f"失败任务重新加入队列，当前重试次数: {execution_count}")
                else:
                    warning(f"任务 {task_id} 重试次数已达上限，不再重新加入队列")
                    # 标记为最终失败
                    self._mark_task_as_final_failure(task_id, task_type, execution_count)
                    return
            elif status == 'running':
                # 运行中的任务，调用ComfyUI API查询状态
                self._handle_running_task(task_id, task_info)
            
            self.processed_tasks_count += 1
        except Exception as e:
            error(f"处理任务 {task_info.get('task_id', '未知')} 时发生异常: {str(e)}")
    
    def _handle_running_task(self, task_id: str, task_info: Dict[str, Any]):
        """处理运行中的任务
        
        Args:
            task_id: 任务ID
            task_info: 任务信息字典
        """
        try:
            # 从任务历史中获取完整的任务对象
            with task_queue_manager.lock:
                task = task_queue_manager.task_history.get(task_id)
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
                runtime_hours = runtime_seconds / 3600
                
                # 获取prompt_id用于查询ComfyUI状态
                prompt_id = task.params.get('prompt_id')
                
                # 如果超过最大运行时间或没有prompt_id，则重新加入队列
                if runtime_hours > self.max_runtime_hours or not prompt_id:
                    info(f"任务 {task_id} 运行时间超过{self.max_runtime_hours}小时或没有prompt_id，重新加入队列")
                    self._requeue_task(task_id, task.task_type, "运行时间过长或无prompt_id，重新加入队列")
                    return
                
            # 调用ComfyUI API查询任务状态
            self._query_comfyui_task_status(task_id, task.task_type, prompt_id)
        except Exception as e:
            error(f"处理运行中任务 {task_id} 时发生异常: {str(e)}")
            # 发生异常时，尝试将任务重新加入队列
            try:
                self._requeue_task(task_id, task_info.get('task_type', 'unknown'), "查询状态异常，重新加入队列")
            except:
                pass
    
    def _query_comfyui_task_status(self, task_id: str, task_type: str, prompt_id: str):
        """查询ComfyUI任务状态
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            prompt_id: ComfyUI的prompt_id
        """
        try:
            # 使用ComfyUI API查询任务状态
            response = requests.get(f"{self.comfyui_api_url}/history/{prompt_id}", timeout=10)
            
            if response.status_code == 200:
                history = response.json()
                
                # 检查任务是否完成
                if isinstance(history, dict) and prompt_id in history:
                    prompt_data = history[prompt_id]
                    
                    if isinstance(prompt_data, dict) and "outputs" in prompt_data:
                        # 任务已完成，更新任务状态并保存结果
                        info(f"任务 {task_id} 在ComfyUI中已完成，正在更新状态")
                        with task_queue_manager.lock:
                            task = task_queue_manager.task_history.get(task_id)
                            if task:
                                task.status = "completed"
                                task.end_time = time.time()
                                
                                # 尝试从输出中提取文件名
                                if "outputs" in prompt_data:
                                    for node_id, node_output in prompt_data["outputs"].items():
                                        if isinstance(node_output, dict):
                                            # 处理图像输出
                                            if "images" in node_output and isinstance(node_output["images"], list):
                                                for image_info in node_output["images"]:
                                                    if isinstance(image_info, dict) and "filename" in image_info:
                                                        task.output_filename = image_info["filename"]
                                                        break
                                        if task.output_filename:
                                            break
                                
                                # 从运行中任务列表移除
                                if task_id in task_queue_manager.running_tasks:
                                    del task_queue_manager.running_tasks[task_id]
                                
                                # 保存任务历史
                                task_queue_manager._save_task_history()
                        return
                    else:
                        # 任务尚未完成
                        info(f"任务 {task_id} 在ComfyUI中仍在处理中")
                        # 不做任何操作，让任务继续在ComfyUI中运行
                        return
                else:
                    info(f"任务 {task_id} 在ComfyUI中未找到，可能已被清理")
                    # 重新加入队列
                    self._requeue_task(task_id, task_type, "ComfyUI中未找到任务，重新加入队列")
            else:
                warning(f"查询任务 {task_id} 状态失败，状态码: {response.status_code}")
                # 查询失败，重新加入队列
                self._requeue_task(task_id, task_type, f"查询ComfyUI状态失败，状态码: {response.status_code}")
        except Exception as e:
            error(f"查询ComfyUI API时出错: {str(e)}")
            # 发生异常时，尝试将任务重新加入队列
            try:
                self._requeue_task(task_id, task_type, f"查询ComfyUI API异常: {str(e)}")
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
            with task_queue_manager._get_task_lock(task_id):
                # 检查任务是否存在于历史记录中
                if task_id not in task_queue_manager.task_history:
                    warning(f"任务 {task_id} 不存在于历史记录中，无法重新加入队列")
                    return
                
                # 获取任务对象
                task = task_queue_manager.task_history[task_id]
                
                # 更新任务状态为queued
                task.status = "queued"
                
                # 设置任务消息
                task.task_msg = reason
                
                # 重置开始和结束时间
                task.start_time = None
                task.end_time = None
                
                # 将任务重新加入队列
                task_queue_manager.task_queue.put(task)
                
                info(f"任务 {task_id} ({task_type}) 已重新加入队列: {reason}")
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
            with task_queue_manager._get_task_lock(task_id):
                # 检查任务是否存在于历史记录中
                if task_id not in task_queue_manager.task_history:
                    warning(f"任务 {task_id} 不存在于历史记录中，无法标记为失败")
                    return
                
                # 获取任务对象
                task = task_queue_manager.task_history[task_id]
                
                # 更新任务状态为failed
                task.status = "failed"
                
                # 设置失败消息
                failure_reason = task.task_msg if task.task_msg else "未知原因"
                task.task_msg = f"任务执行失败，重试超过{self.max_retry_count}次，原因：{failure_reason}"
                
                # 设置结束时间（如果还没有）
                if not task.end_time:
                    task.end_time = time.time()
                
                # 保存任务历史
                task_queue_manager._save_task_history()
                
                info(f"任务 {task_id} ({task_type}) 已标记为最终失败，执行次数: {execution_count}")
        except Exception as e:
            error(f"将任务 {task_id} 标记为失败时发生异常: {str(e)}")


# 创建全局启动任务监听器实例
startup_task_listener = StartupTaskListener()
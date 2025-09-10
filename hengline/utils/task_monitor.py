# -*- coding: utf-8 -*-
"""
任务监控器模块
用于定期检查任务状态并处理失败重试
"""

import threading
import time
import os
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

# 导入自定义日志模块
from hengline.utils.logger import info, error, debug, warning

# 导入任务队列管理器
from hengline.utils.task_queue_utils import task_queue_manager

# 导入ComfyUIRunner
from hengline.run_workflow import ComfyUIRunner

# 导入配置
from hengline.utils.workflow_utils import config

# 导入邮件发送模块
from hengline.utils.email_utils import EmailSender, init_email_sender, send_email

class TaskMonitor:
    """任务监控器类"""
    
    def __init__(self, check_interval: int = 30):
        """
        初始化任务监控器
        
        Args:
            check_interval: 检查间隔（秒），默认为30秒
        """
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        self.comfyui_api_url = config.get('comfyui', {}).get('api_url', 'http://127.0.0.1:8188')
        self.comfyui_runner = None
        self.max_execution_count = 3  # 最大执行次数
        self.max_runtime_hours = 2  # 最大运行时间（小时）
        self.instance_id = str(uuid.uuid4())[:8]  # 生成一个简短的实例ID
        self.process_id = os.getpid()  # 获取当前进程ID
        self._task_check_lock = threading.Lock()  # 添加线程锁以防止并发执行
    
    def start(self):
        """启动任务监控器"""
        if self.running:
            info("任务监控器已经在运行中")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, name=f"TaskMonitorThread-{self.instance_id}")
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # current_thread = threading.current_thread()
        info(f"任务监控器已启动，检查间隔：{self.check_interval}秒 - 实例ID: {self.instance_id}, 进程ID: {self.process_id}")
        # debug(f"启动线程ID: {current_thread.ident}, 线程名称: {current_thread.name}")
        # debug(f"监控线程ID: {self.monitor_thread.ident}, 线程名称: {self.monitor_thread.name}")


    def stop(self):
        """停止任务监控器"""
        if not self.running:
            info("任务监控器未运行")
            return
        
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        info("任务监控器已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        current_thread = threading.current_thread()
        debug(f"监控循环开始执行 - 线程ID: {current_thread.ident}, 线程名称: {current_thread.name}")
        
        while self.running:
            try:
                self._check_tasks(current_thread)
            except Exception as e:
                error(f"任务检查过程中出错: {str(e)}")
            
            # 等待指定的检查间隔
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)
            
        debug(f"任务监控器线程已退出 - 线程ID: {current_thread.ident}, 线程名称: {current_thread.name}")
    
    def _check_tasks(self, current_thread: threading.current_thread()):
        """检查任务状态 - 优化版本"""

        # 尝试获取锁，如果获取失败，说明已有线程在执行，直接返回
        if not self._task_check_lock.acquire(blocking=False):
            debug(f"跳过任务检查 - 已有线程在执行检查，实例ID: {self.instance_id}, 进程ID: {self.process_id}, 线程ID: {current_thread.ident}, 线程名称: {current_thread.name}")
            return
        
        try:
            # 只在debug模式下记录详细信息
            debug(f"开始检查任务状态 - 实例ID: {self.instance_id}, 进程ID: {self.process_id}")
            
            # 获取今天的日期
            today_date = datetime.now().strftime('%Y-%m-%d')
            
            # 获取今天的所有任务 - get_all_tasks内部已有锁保护
            today_tasks = task_queue_manager.get_all_tasks(date=today_date)
            
            # 筛选执行次数不超过max_execution_count次的任务
            eligible_tasks = [task for task in today_tasks if task.get('execution_count', 0) <= self.max_execution_count]
            
            debug(f"找到{len(eligible_tasks)}个符合条件的任务（执行次数<={self.max_execution_count}）")
            
            # 收集需要保存的任务ID，避免多次调用_save_task_history
            tasks_to_save = set()
            
            for task_info in eligible_tasks:
                task_id = task_info.get('task_id')
                status = task_info.get('status')
                execution_count = task_info.get('execution_count', 0)
                
                if not task_id or not status:
                    continue
                
                try:
                    if status == "failed":
                        # 处理失败的任务
                        if self._handle_failed_task(task_id, task_info, execution_count):
                            tasks_to_save.add(task_id)
                    elif status == "running":
                        # 处理运行中的任务
                        if self._handle_running_task(task_id, task_info):
                            tasks_to_save.add(task_id)
                except Exception as e:
                    error(f"处理任务 {task_id} 时出错: {str(e)}")
            
            # 如果有任务需要保存，批量异步保存
            if tasks_to_save:
                debug(f"批量保存 {len(tasks_to_save)} 个任务历史")
                task_queue_manager._async_save_history()
        finally:
            # 确保锁被释放
            self._task_check_lock.release()
    
    def _handle_failed_task(self, task_id: str, task_info: Dict[str, Any], execution_count: int) -> bool:
        """处理失败的任务 - 优化版本"""
        debug(f"处理失败的任务: {task_id}, 当前执行次数: {execution_count}")
        
        # 从任务历史中获取完整的任务对象
        with task_queue_manager.lock:
            task = task_queue_manager.task_history.get(task_id)
            if not task:
                error(f"未找到任务 {task_id} 的完整信息")
                return False
            
            # 检查是否超过最大执行次数
            if execution_count > self.max_execution_count:
                # 达到最大执行次数，标记为最终失败
                debug(f"任务 {task_id} 执行次数已达到最大限制 {self.max_execution_count}，不再重试")
                task.status = "failed"
                failure_reason = task.task_msg if task.task_msg else "未知原因"
                task.task_msg = f"任务执行失败，重试超过{self.max_execution_count}次，原因：{failure_reason}"
                if not task.end_time:
                    task.end_time = time.time()
                
                # 从运行中任务列表移除（如果存在）
                if task_id in task_queue_manager.running_tasks:
                    del task_queue_manager.running_tasks[task_id]
                
                # 任务已更新，需要保存
                needs_save = True
                
                error(f"任务 {task_id} 执行失败，已达到最大重试次数")
                
                # 异步发送邮件通知
                threading.Thread(
                    target=self._async_send_failure_email, 
                    args=(task_id, task.task_type, task.task_msg, self.max_execution_count),
                    daemon=True
                ).start()
                
                return needs_save
            
            # 更新任务状态为排队中
            task.status = "queued"
            
            # 保留任务消息作为失败原因
            failure_reason = task.task_msg if task.task_msg else "任务执行失败"
            
            # 重置开始和结束时间
            task.start_time = None
            task.end_time = None
            
            # 将任务重新加入队列
            task_queue_manager.task_queue.put(task)
            
            # 从运行中任务列表移除（如果存在）
            if task_id in task_queue_manager.running_tasks:
                del task_queue_manager.running_tasks[task_id]
            
            info(f"任务 {task_id} 已重新加入队列，等待重试，失败原因：{failure_reason}")
            
            # 任务已更新，需要保存
            return True
        
        return False
    
    def _async_send_failure_email(self, task_id: str, task_type: str, task_msg: str, max_execution_count: int):
        """异步发送任务失败邮件通知"""
        try:
            send_email(
                subject=f"任务 {task_id} 执行失败",
                message=f"您提交的{task_type}任务已重试（{max_execution_count}次），但是由于：{task_msg}，请检查后再次提交任务"
            )
        except Exception as e:
            error(f"发送任务失败邮件通知失败: {str(e)}")
    
    def _handle_running_task(self, task_id: str, task_info: Dict[str, Any]) -> bool:
        """处理运行中的任务 - 优化版本"""
        debug(f"检查运行中的任务: {task_id}")
        
        needs_save = False
        
        # 从任务历史中获取完整的任务对象
        with task_queue_manager.lock:
            task = task_queue_manager.task_history.get(task_id)
            if not task:
                error(f"未找到任务 {task_id} 的完整信息")
                return False
            
            # 检查任务是否有开始时间
            if not task.start_time:
                warning(f"任务 {task_id} 状态为运行中，但没有开始时间")
                # 修复：将状态重置为queued以便重新执行
                task.status = "queued"
                task.start_time = None
                task.end_time = None
                # 从运行中任务列表移除
                if task_id in task_queue_manager.running_tasks:
                    del task_queue_manager.running_tasks[task_id]
                needs_save = True
                return needs_save
            
            # 计算任务已运行时间
            current_time = time.time()
            runtime_seconds = current_time - task.start_time
            runtime_hours = runtime_seconds / 3600
            
            # 检查是否超过最大运行时间
            if runtime_hours > self.max_runtime_hours:
                # 标记为失败
                task.status = "failed"
                task.task_msg = "任务运行时间超过2小时，已停止监控"
                task.end_time = current_time
                
                # 从运行中任务列表移除
                if task_id in task_queue_manager.running_tasks:
                    del task_queue_manager.running_tasks[task_id]
                
                needs_save = True
                error(f"任务 {task_id} 运行时间超过{self.max_runtime_hours}小时，已标记为失败")
                return needs_save
        
        # 调用ComfyUI API查询任务状态 - 放在锁外执行，避免API调用阻塞
        prompt_id = task.params.get('prompt_id')
        if not prompt_id:
            debug(f"任务 {task_id} 没有prompt_id，无法查询ComfyUI状态")
            return False
        
        # 使用带超时的查询
        result = self._query_comfyui_api_with_timeout(prompt_id)
        if result is not None:
            history, current_time = result
            if history is not None:
                with task_queue_manager.lock:
                    # 再次获取任务对象，确保状态最新
                    task = task_queue_manager.task_history.get(task_id)
                    if not task:
                        return False
                    
                    # 检查任务是否完成
                    if isinstance(history, dict) and prompt_id in history:
                        prompt_data = history[prompt_id]
                        
                        if isinstance(prompt_data, dict) and "outputs" in prompt_data:
                            # 任务已完成
                            info(f"任务 {task_id} 在ComfyUI中已完成，正在更新状态")
                            
                            # 更新任务状态
                            task.status = "completed"
                            task.end_time = current_time
                            
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
                            
                            needs_save = True
                            
                            # 异步发送完成邮件通知
                            threading.Thread(
                                target=self._async_send_success_email,
                                args=(task_id, task.task_type, task.start_time, task.end_time),
                                daemon=True
                            ).start()
        
        return needs_save
    
    def _query_comfyui_api_with_timeout(self, prompt_id: str, timeout: int = 10) -> Optional[Tuple[Optional[Dict], float]]:
        """带超时的ComfyUI API查询"""
        result = [None]
        exception = [None]
        
        def _query():
            try:
                import requests
                response = requests.get(f"{self.comfyui_api_url}/history/{prompt_id}", timeout=timeout)
                
                if response.status_code == 200:
                    result[0] = response.json()
                else:
                    debug(f"查询任务状态失败，状态码: {response.status_code}")
            except Exception as e:
                exception[0] = e
        
        # 创建线程执行查询
        query_thread = threading.Thread(target=_query, daemon=True)
        query_thread.start()
        query_thread.join(timeout)
        
        # 检查线程是否超时
        if query_thread.is_alive():
            debug(f"查询ComfyUI API超时: {prompt_id}")
            return None
        
        # 检查是否有异常
        if exception[0]:
            debug(f"查询ComfyUI API时出错: {str(exception[0])}")
            return None
        
        return result[0], time.time()

    def _async_send_success_email(self, task_id: str, task_type: str, start_time: float, end_time: float):
        """异步发送任务成功邮件通知"""
        try:
            send_email(
                subject=f"任务 {task_id} 执行成功",
                message=f"您提交的{task_type}任务已成功完成！\n\n任务类型: {task_type}\n开始时间: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}\n结束时间: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}\n耗时: {end_time - start_time:.1f}秒"
            )
        except Exception as e:
            error(f"发送任务成功邮件通知失败: {str(e)}")

# 全局任务监控器实例
task_monitor = TaskMonitor()
# -*- coding: utf-8 -*-
"""
任务监控器模块
用于定期检查任务状态并处理失败重试
"""

import threading
import time
import datetime
from typing import Dict, Any, List
from datetime import datetime, timedelta

# 导入自定义日志模块
from .logger import info, error, debug, warning
# 导入任务队列管理器
from .task_queue_utils import task_queue_manager
# 导入工作流运行器
from scripts.run_workflow import ComfyUIRunner
# 导入配置
from .workflow_utils import config
# 导入邮件发送工具
from scripts.utils.email_utils import EmailSender, init_email_sender, send_email

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
    
    def start(self):
        """启动任务监控器"""
        if self.running:
            info("任务监控器已经在运行中")
            return
        
        # 初始化ComfyUI运行器
        comfyui_path = config.get('comfyui', {}).get('path', '')
        output_dir = config.get('paths', {}).get('output_folder', 'outputs')
        self.comfyui_runner = ComfyUIRunner(comfyui_path, output_dir, self.comfyui_api_url)
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        info(f"任务监控器已启动，检查间隔：{self.check_interval}秒")
    
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
        while self.running:
            try:
                self._check_tasks()
            except Exception as e:
                error(f"任务检查过程中出错: {str(e)}")
            
            # 等待指定的检查间隔
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_tasks(self):
        """检查任务状态"""
        info("开始检查任务状态")
        
        # 获取今天的日期
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        # 获取今天的所有任务
        today_tasks = task_queue_manager.get_all_tasks(date=today_date)
        
        # 筛选执行次数不超过3次的任务
        eligible_tasks = [task for task in today_tasks if task.get('execution_count', 0) <= self.max_execution_count]
        
        info(f"找到{len(eligible_tasks)}个符合条件的任务（执行次数<={self.max_execution_count}）")
        
        for task_info in eligible_tasks:
            task_id = task_info.get('task_id')
            status = task_info.get('status')
            execution_count = task_info.get('execution_count', 0)
            
            if not task_id or not status:
                continue
            
            try:
                if status == "failed":
                    # 处理失败的任务
                    self._handle_failed_task(task_id, task_info, execution_count)
                elif status == "running":
                    # 处理运行中的任务
                    self._handle_running_task(task_id, task_info)
            except Exception as e:
                error(f"处理任务 {task_id} 时出错: {str(e)}")
    
    def _handle_failed_task(self, task_id: str, task_info: Dict[str, Any], execution_count: int):
        """处理失败的任务"""
        debug(f"处理失败的任务: {task_id}, 当前执行次数: {execution_count}")
        
        # 从任务历史中获取完整的任务对象
        task = task_queue_manager.task_history.get(task_id)
        if not task:
            error(f"未找到任务 {task_id} 的完整信息")
            return
        
        # 检查是否超过最大执行次数
        if execution_count > self.max_execution_count:
            # 达到最大执行次数，标记为失败
            debug(f"任务 {task_id} 执行次数已达到最大限制 {self.max_execution_count}，不再重试")
            task.status = "failed"
            task.task_msg = f"任务已重试（{self.max_execution_count}次）：{task.task_msg}"
            if not task.end_time:
                task.end_time = time.time()
            # 保存任务历史
            task_queue_manager._save_task_history()
            error(f"任务 {task_id} 执行失败，已达到最大重试次数")

            send_email(
                subject=f"任务 {task_id} 执行失败",
                message=f"您提交的{task.task_type}任务已重试（{self.max_execution_count}次）,但是由于：{task.task_msg}，请检查后再次提交任务"
            )
            return
        
        # 更新任务状态为排队中
        task.status = "queued"
        
        # 清空任务消息
        task.task_msg = ""
        
        # 重置开始和结束时间
        task.start_time = None
        task.end_time = None
        
        # 将任务重新加入队列
        task_queue_manager.task_queue.put(task)
        
        info(f"任务 {task_id} 已重新加入队列，等待重试")
    
    def _handle_running_task(self, task_id: str, task_info: Dict[str, Any]):
        """处理运行中的任务"""
        debug(f"检查运行中的任务: {task_id}")
        
        # 从任务历史中获取完整的任务对象
        task = task_queue_manager.task_history.get(task_id)
        if not task:
            error(f"未找到任务 {task_id} 的完整信息")
            return
        
        # 检查任务是否有开始时间
        if not task.start_time:
            warning(f"任务 {task_id} 状态为运行中，但没有开始时间")
            return
        
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
            
            # 保存任务历史
            task_queue_manager._save_task_history()
            
            error(f"任务 {task_id} 运行时间超过{self.max_runtime_hours}小时，已标记为失败")
            return
        
        # 调用ComfyUI API查询任务状态
        prompt_id = task.params.get('prompt_id')
        if not prompt_id:
            debug(f"任务 {task_id} 没有prompt_id，无法查询ComfyUI状态")
            return
        
        try:
            # 使用ComfyUI API查询任务状态
            import requests
            response = requests.get(f"{self.comfyui_api_url}/history/{prompt_id}")
            
            if response.status_code == 200:
                history = response.json()
                
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
                        
                        # 保存任务历史
                        task_queue_manager._save_task_history()
                        
            else:
                debug(f"查询任务 {task_id} 状态失败，状态码: {response.status_code}")
        except Exception as e:
            debug(f"查询ComfyUI API时出错: {str(e)}")

# 全局任务监控器实例
task_monitor = TaskMonitor()
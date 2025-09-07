#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理模块
用于管理生图和生视频任务的排队执行
"""

import queue
import threading
import time
import json
import os
from typing import Dict, Any, Callable, Tuple, Optional, List
import uuid
from datetime import datetime

from .logger import info, error, debug

class Task:
    """表示一个任务的类"""
    def __init__(self, task_type: str, task_id: str, timestamp: float, params: Dict[str, Any], callback: Callable):
        self.task_type = task_type  # 任务类型: text_to_image, image_to_image, text_to_video, image_to_video
        self.task_id = task_id      # 任务唯一ID
        self.timestamp = timestamp  # 任务创建时间戳
        self.params = params        # 任务参数
        self.callback = callback    # 任务完成后的回调函数
        self.start_time = None      # 任务开始执行时间
        self.end_time = None        # 任务结束时间
        self.status = "queued"      # 任务状态: queued, running, completed, failed
        self.output_filename = None  # 任务输出文件名
        self.task_msg = None        # 任务消息，用于存储错误或状态信息
        self.execution_count = 1    # 任务执行次数，默认为1

    def __lt__(self, other):
        # 任务排序基于时间戳，确保先进先出
        return self.timestamp < other.timestamp

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
        self.lock = threading.Lock()  # 用于线程同步的锁
        self.task_history = {}  # 任务历史记录 {task_id: Task}
        self.average_task_durations = {
            "text_to_image": 60.0,  # 默认平均文生图任务时长（秒）
            "image_to_image": 70.0,  # 默认平均图生图任务时长（秒）
            "text_to_video": 300.0,  # 默认平均文生视频任务时长（秒）
            "image_to_video": 320.0  # 默认平均图生视频任务时长（秒）
        }
        
        # 持久化配置
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载已保存的任务历史
        self._load_task_history()
        
        # 启动任务处理线程
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_tasks)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        # 加载今天排队中的任务到队列
        queued_tasks_added = 0
        with self.lock:
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
        
        info(f"任务队列管理器已启动，最大并发任务数: {max_concurrent_tasks}")
        info(f"已加载任务历史记录: {len(self.task_history)} 个任务")
        info(f"已将今天 {queued_tasks_added} 个排队中的任务添加到队列")
    
    def enqueue_task(self, task_type: str, params: Dict[str, Any], callback: Callable) -> Tuple[str, int, float]:
        """
        将任务加入队列
        
        Args:
            task_type: 任务类型
            params: 任务参数
            callback: 任务完成后的回调函数
        
        Returns:
            Tuple[str, int, float]: (任务ID, 队列中的位置, 预估等待时间(秒))
        """
        with self.lock:
            # 检查任务参数中是否已提供task_id
            task_id = params.get('task_id')
            timestamp = time.time()
            
            # 如果没有提供task_id或该task_id不存在，则生成新的唯一ID
            if not task_id or task_id not in self.task_history:
                task_id = str(uuid.uuid4())
                
                # 创建新任务对象
                task = Task(
                    task_type=task_type,
                    task_id=task_id,
                    timestamp=timestamp,
                    params=params,
                    callback=callback
                )
                
                # 将任务加入队列
                self.task_queue.put(task)
                
                info(f"新任务已加入队列: {task_id}, 类型: {task_type}")
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
                
                info(f"任务已更新并重新加入队列: {task_id}, 类型: {task_type}")
            
            # 计算队列中的位置（包括正在运行的任务）
            queue_position = len(self.running_tasks) + self.task_queue.qsize()
            
            # 计算预估等待时间
            waiting_time = self._estimate_waiting_time(task_type, queue_position)
            
            # 将任务添加到历史记录
            self.task_history[task_id] = task
            
            # 保存任务历史
            self._save_task_history()
            
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
        # 如果队列位置小于等于最大并发数，无需等待
        if queue_position <= self.max_concurrent_tasks:
            return 0.0
        
        # 计算前面有多少个任务在等待
        waiting_tasks = queue_position - self.max_concurrent_tasks
        
        # 获取该类型任务的平均执行时间
        avg_duration = self.average_task_durations.get(task_type, 60.0)
        
        # 预估等待时间 = 前面等待的任务数 * 该类型任务的平均执行时间
        estimated_waiting_time = waiting_tasks * avg_duration
        
        return estimated_waiting_time
    
    def _process_tasks(self):
        """处理队列中的任务"""
        while self.running:
            with self.lock:
                # 检查是否可以开始新任务
                if len(self.running_tasks) < self.max_concurrent_tasks and not self.task_queue.empty():
                    # 获取下一个任务
                    task = self.task_queue.get()
                    
                    # 更新任务状态和执行次数
                    task.status = "running"
                    task.start_time = time.time()
                    task.execution_count += 1  # 执行次数加1
                    self.running_tasks[task.task_id] = task
                    
                    # 记录到历史
                    self.task_history[task.task_id] = task
                    
                    # 保存任务历史，确保状态和时间更新被持久化
                    self._save_task_history()
                    
                    info(f"开始执行任务: {task.task_id}, 类型: {task.task_type}")
                    
                    # 启动任务线程
                    task_thread = threading.Thread(
                        target=self._execute_task, 
                        args=(task,)
                    )
                    task_thread.daemon = True
                    task_thread.start()
            
            # 短暂休眠，避免CPU占用过高
            time.sleep(0.1)
    
    def _execute_task(self, task: Task):
        """执行单个任务"""
        try:
            # 执行任务回调函数
            result = task.callback(task.params)
            
            # 更新任务状态
            with self.lock:
                # 检查任务是否遇到连接异常
                if result and isinstance(result, dict) and result.get('queued'):
                    # 如果ComfyUI服务器连接失败，将任务标记为连接异常状态
                    info(f"任务执行失败，ComfyUI服务器连接异常: {task.task_id}")
                    task.status = "failed"
                    task.task_msg = "ComfyUI 工作流连接超时"
                    task.end_time = time.time()
                    # 从running_tasks中移除
                    if task.task_id in self.running_tasks:
                        del self.running_tasks[task.task_id]
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
                    
                    # 更新平均执行时间
                    if task.end_time and task.start_time:
                        duration = task.end_time - task.start_time
                        # 使用移动平均更新平均执行时间
                        self._update_average_duration(task.task_type, duration)
                
                # 从运行中任务列表移除
                self.running_tasks.pop(task.task_id, None)
                
                # 保存任务历史
                self._save_task_history()
            
            info(f"任务执行完成: {task.task_id}, 类型: {task.task_type}")
            
        except Exception as e:
            error(f"任务执行失败: {task.task_id}, 错误: {str(e)}")
            
            # 更新任务状态
            with self.lock:
                task.status = "failed"
                task.task_msg = f"任务执行失败: {task.task_id}, 错误: {str(e)}"
                task.end_time = time.time()
                
                # 从运行中任务列表移除
                self.running_tasks.pop(task.task_id, None)
                
                # 保存任务历史
                self._save_task_history()
    
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
        """
        with self.lock:
            # 计算总运行任务数和排队任务数
            running_count = len(self.running_tasks)
            queued_count = self.task_queue.qsize()
            
            # 如果提供了任务类型参数，则过滤任务
            if task_type and task_type != 'all':
                # 计算该类型的运行任务数
                running_count = sum(1 for task in self.running_tasks.values() if task.task_type == task_type)
                
                # 计算该类型的排队任务数
                # 需要临时复制队列来避免修改原始队列
                temp_queue = []
                queued_count = 0
                
                # 将队列中的所有任务移动到临时列表
                while not self.task_queue.empty():
                    task = self.task_queue.get()
                    temp_queue.append(task)
                    if task.task_type == task_type:
                        queued_count += 1
                
                # 将任务放回原始队列
                for task in temp_queue:
                    self.task_queue.put(task)
                
            # 计算总任务数
            total_tasks = running_count + queued_count
            
            # 计算队列位置（这里简单地返回1，实际应用中可能需要更复杂的逻辑）
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
            estimated_time = queued_count * avg_duration if avg_duration > 0 else 0
            
            # 计算进度（这里简单地基于队列位置和总任务数）
            progress = 0
            if total_tasks > 0:
                progress = min(100, int((position / total_tasks) * 100))
                
            # 返回前端期望的数据结构
            return {
                "total_tasks": total_tasks,
                "in_queue": queued_count,
                "running_tasks": running_count,
                "position": position,
                "estimated_time": round(estimated_time, 1),
                "progress": progress,
                "running_tasks_count": running_count,  # 保留原始字段以保持兼容性
                "queued_tasks_count": queued_count,    # 保留原始字段以保持兼容性
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "average_task_durations": self.average_task_durations
            }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定任务的状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息，如果任务不存在则返回None
        """
        with self.lock:
            task = self.task_history.get(task_id)
            if not task:
                return None
            
            status_info = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "timestamp": task.timestamp,
                "queue_position": len(self.running_tasks) + self.task_queue.qsize()
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
        with self.lock:
            temp_tasks = []
            while not self.task_queue.empty():
                task = self.task_queue.get()
                temp_tasks.append(task)
                # 将任务添加到历史记录，保持"queued"状态
                self.task_history[task.task_id] = task
                info(f"将排队任务添加到历史记录: {task.task_id}, 类型: {task.task_type}")
            
            # 保存任务历史
            self._save_task_history()
            
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        info("任务队列管理器已关闭，已保存所有排队任务到历史记录")
        
    def _save_task_history(self):
        """保存任务历史到按日期分类的文件"""
        try:
            # 按日期分组任务
            tasks_by_date = {}
            for task in self.task_history.values():
                # 根据任务创建时间确定日期
                task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
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
                
            info(f"已保存任务历史到按日期分类的文件")
        except Exception as e:
            error(f"保存任务历史失败: {str(e)}")
            
    def _load_task_history(self):
        """从按日期分类的文件加载任务历史"""
        try:
            # 查找所有符合格式的任务历史文件
            history_files = []
            if os.path.exists(self.data_dir):
                for filename in os.listdir(self.data_dir):
                    if filename.startswith('task_history_') and filename.endswith('.json'):
                        history_files.append(os.path.join(self.data_dir, filename))
            
            if not history_files:
                info(f"没有找到任务历史文件")
                return
            
            total_tasks = 0
            # 加载每个文件中的任务
            for file_path in history_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        serializable_tasks = json.load(f)
                    
                    # 重建任务对象
                    for task_data in serializable_tasks:
                        # 创建任务对象
                        task = Task(
                            task_type=task_data['task_type'],
                            task_id=task_data['task_id'],
                            timestamp=task_data['timestamp'],
                            params=task_data.get('params', {}),
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
                        total_tasks += 1
                    
                except Exception as file_error:
                    error(f"加载任务历史文件 {file_path} 失败: {str(file_error)}")
            
            info(f"已从文件加载 {total_tasks} 个任务历史记录")
        except Exception as e:
            error(f"加载任务历史失败: {str(e)}")
        
    def get_all_tasks(self, date=None):
        """
        获取所有任务历史记录，可选按日期筛选
        
        Args:
            date: 可选的日期字符串，格式为'YYYY-MM-DD'
        
        Returns:
            List[Dict[str, Any]]: 任务的状态信息列表
        """
        with self.lock:
            all_tasks = []
            for task in self.task_history.values():
                # 如果提供了日期参数，则只返回该日期的任务
                if date:
                    # 将任务时间戳转换为日期格式
                    task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
                    if task_date != date:
                        continue
                
                task_info = {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "timestamp": task.timestamp,
                    "queue_position": len(self.running_tasks) + self.task_queue.qsize(),
                    "execution_count": task.execution_count
                }
                
                # 添加任务消息
                if task.task_msg:
                    task_info["task_msg"] = task.task_msg
                
                # 添加开始和结束时间
                if task.start_time:
                    task_info["start_time"] = task.start_time
                if task.end_time:
                    task_info["end_time"] = task.end_time
                    if task.start_time:
                        task_info["duration"] = task.end_time - task.start_time
                
                # 添加任务参数信息（不包含敏感数据）
                if task.params:
                    # 只保留非敏感的参数信息
                    task_info["prompt"] = task.params.get("prompt", "")
                    task_info["negative_prompt"] = task.params.get("negative_prompt", "")
                
                all_tasks.append(task_info)
            
            # 按时间戳降序排序（最新的任务在前）
            all_tasks.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return all_tasks

# 全局任务队列管理器实例
task_queue_manager = TaskQueueManager(2)
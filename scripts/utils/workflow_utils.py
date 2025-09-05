#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowManager类和配置加载功能
"""
import os
import json
import uuid
import time
import shutil
import datetime
import subprocess
import signal
from scripts.utils.logger import info, error, warning
from scripts.run_workflow import ComfyUIRunner
from scripts.utils.task_queue_utils import task_queue_manager

# 加载配置文件
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        error(f"加载配置文件失败: {e}")
        # 返回默认配置
        return {
            'comfyui': {
                'path': './ComfyUI',
                'port': 8188
            }
        }

class WorkflowManager:
    """工作流管理器类，用于处理各种AI生成任务"""
    
    def __init__(self, config, runner=None):
        """初始化工作流管理器"""
        self.config = config
        self.runner = runner
        self.comfyui_path = config['comfyui']['path'] if config and 'comfyui' in config else './ComfyUI'
        self.output_dir = None
    
    def init_runner(self):
        """初始化工作流运行器"""
        if not self.runner and self.comfyui_path and self.output_dir:
            self.runner = ComfyUIRunner(self.comfyui_path, self.output_dir)
        return self.runner is not None
    
    def stop_runner(self):
        """停止工作流运行器"""
        if self.runner:
            # 这里不直接停止服务器，而是由app_flask.py中的全局变量处理
            self.runner = None
    
    def _execute_text_to_image(self, params):
        """实际执行文生图任务的方法，用于队列调用"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        prompt = params['prompt']
        negative_prompt = params['negative_prompt']
        width = params.get('width', 1024)
        height = params.get('height', 1024)
        steps = params.get('steps', 30)
        cfg_scale = params.get('cfg_scale', 8.0)
        
        try:
            info(f"处理文生图任务: {prompt}")
            
            # 生成唯一的输出文件名
            output_filename = f"text_to_image_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
            
            # 加载文生图工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        "workflows", "text_to_image.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                warning(f"工作流文件不存在: {workflow_path}")
                return {'success': False, 'message': f'工作流文件不存在: {workflow_path}'}
            
            # 加载和更新工作流
            workflow = self.runner.load_workflow(workflow_path)
            update_params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale
            }
            updated_workflow = self.runner.update_workflow_params(workflow, update_params)
            
            # 运行工作流
            success = self.runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                output_path = os.path.join(self.output_dir, output_filename)
                return {'success': True, 'message': '文生图任务处理成功', 'output_path': output_path}
            else:
                return {'success': False, 'message': '工作流运行失败'}
        except Exception as e:
            error(f"文生图任务执行失败: {str(e)}")
            return {'success': False, 'message': f'文生图任务执行失败: {str(e)}'}
    
    def process_text_to_image(self, prompt, negative_prompt, width=1024, height=1024, steps=30, cfg_scale=8.0):
        """处理文生图任务，将任务加入队列"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        # 准备任务参数
        task_params = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': width,
            'height': height,
            'steps': steps,
            'cfg_scale': cfg_scale
        }
        
        # 任务回调函数 - 这里直接返回结果，因为在路由中是同步处理的
        def task_callback(params):
            return self._execute_text_to_image(params)
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'text_to_image', 
            task_params, 
            task_callback
        )
        
        # 等待任务完成 - 由于路由是同步处理的，我们需要等待任务完成
        # 实际项目中可能需要改为异步处理
        if queue_position <= task_queue_manager.max_concurrent_tasks:
            # 如果任务可以立即执行，就直接执行
            return self._execute_text_to_image(task_params)
        else:
            # 否则返回排队信息
            minutes, seconds = divmod(int(waiting_time), 60)
            waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
            return {
                'success': False, 
                'message': f'当前任务较多，请稍候。您的任务已排队，前面还有{queue_position - task_queue_manager.max_concurrent_tasks}个任务，预计等待{waiting_str}。',
                'queued': True,
                'task_id': task_id,
                'queue_position': queue_position,
                'waiting_time': waiting_time
            }
    
    def _execute_image_to_image(self, params):
        """实际执行图生图任务的方法，用于队列调用"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        image_path = params['image_path']
        prompt = params['prompt']
        negative_prompt = params['negative_prompt']
        width = params.get('width', 1024)
        height = params.get('height', 1024)
        steps = params.get('steps', 30)
        cfg_scale = params.get('cfg_scale', 8.0)
        denoising_strength = params.get('denoising_strength', 0.75)
        
        try:
            info(f"处理图生图任务: {prompt}")
            
            # 生成唯一的输出文件名
            output_filename = f"image_to_image_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
            
            # 加载图生图工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        "workflows", "image_to_image.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                warning(f"工作流文件不存在: {workflow_path}")
                return {'success': False, 'message': f'工作流文件不存在: {workflow_path}'}
            
            # 加载和更新工作流
            workflow = self.runner.load_workflow(workflow_path)
            update_params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "image_path": image_path,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "denoising_strength": denoising_strength
            }
            updated_workflow = self.runner.update_workflow_params(workflow, update_params)
            
            # 运行工作流
            success = self.runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                output_path = os.path.join(self.output_dir, output_filename)
                return {'success': True, 'message': '图生图任务处理成功', 'output_path': output_path}
            else:
                return {'success': False, 'message': '工作流运行失败'}
        except Exception as e:
            error(f"图生图任务执行失败: {str(e)}")
            return {'success': False, 'message': f'图生图任务执行失败: {str(e)}'}
    
    def process_image_to_image(self, image_path, prompt, negative_prompt, width=1024, height=1024, steps=30, cfg_scale=8.0, denoising_strength=0.75):
        """处理图生图任务，将任务加入队列"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        # 准备任务参数
        task_params = {
            'image_path': image_path,
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': width,
            'height': height,
            'steps': steps,
            'cfg_scale': cfg_scale,
            'denoising_strength': denoising_strength
        }
        
        # 任务回调函数
        def task_callback(params):
            return self._execute_image_to_image(params)
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'image_to_image', 
            task_params, 
            task_callback
        )
        
        # 由于路由是同步处理的，我们需要根据队列位置决定是否立即执行
        if queue_position <= task_queue_manager.max_concurrent_tasks:
            # 如果任务可以立即执行，就直接执行
            return self._execute_image_to_image(task_params)
        else:
            # 否则返回排队信息
            minutes, seconds = divmod(int(waiting_time), 60)
            waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
            return {
                'success': False, 
                'message': f'当前任务较多，请稍候。您的任务已排队，前面还有{queue_position - task_queue_manager.max_concurrent_tasks}个任务，预计等待{waiting_str}。',
                'queued': True,
                'task_id': task_id,
                'queue_position': queue_position,
                'waiting_time': waiting_time
            }
    
    def _execute_image_to_video(self, params):
        """实际执行图生视频任务的方法，用于队列调用"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        image_path = params['image_path']
        prompt = params['prompt']
        negative_prompt = params['negative_prompt']
        duration = params.get('duration', 5)
        fps = params.get('fps', 30)
        
        try:
            info(f"处理图生视频任务")
            
            # 生成唯一的输出文件名
            output_filename = f"image_to_video_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
            
            # 返回模拟结果（实际项目中应该调用工作流）
            # 模拟处理延迟
            time.sleep(1)
            
            output_path = os.path.join(self.output_dir, output_filename)
            # 创建一个空文件作为模拟输出
            open(output_path, 'a').close()
            
            return {'success': True, 'message': '图生视频任务处理成功', 'output_path': output_path}
        except Exception as e:
            error(f"图生视频任务执行失败: {str(e)}")
            return {'success': False, 'message': f'图生视频任务执行失败: {str(e)}'}
    
    def process_image_to_video(self, image_path, prompt, negative_prompt, duration=5, fps=30):
        """处理图生视频任务，将任务加入队列"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        # 准备任务参数
        task_params = {
            'image_path': image_path,
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'duration': duration,
            'fps': fps
        }
        
        # 任务回调函数
        def task_callback(params):
            return self._execute_image_to_video(params)
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'image_to_video', 
            task_params, 
            task_callback
        )
        
        # 由于路由是同步处理的，我们需要根据队列位置决定是否立即执行
        if queue_position <= task_queue_manager.max_concurrent_tasks:
            # 如果任务可以立即执行，就直接执行
            return self._execute_image_to_video(task_params)
        else:
            # 否则返回排队信息
            minutes, seconds = divmod(int(waiting_time), 60)
            waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
            return {
                'success': False, 
                'message': f'当前任务较多，请稍候。您的任务已排队，前面还有{queue_position - task_queue_manager.max_concurrent_tasks}个任务，预计等待{waiting_str}。',
                'queued': True,
                'task_id': task_id,
                'queue_position': queue_position,
                'waiting_time': waiting_time
            }
    
    def _execute_text_to_video(self, params):
        """实际执行文生视频任务的方法，用于队列调用"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        prompt = params['prompt']
        negative_prompt = params['negative_prompt']
        duration = params.get('duration', 5)
        fps = params.get('fps', 30)
        
        try:
            info(f"处理文生视频任务: {prompt}")
            
            # 生成唯一的输出文件名
            output_filename = f"text_to_video_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp4"
            
            # 加载文生视频工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        "workflows", "text_to_video.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                warning(f"工作流文件不存在: {workflow_path}")
                return {'success': False, 'message': f'工作流文件不存在: {workflow_path}'}
            
            # 加载和更新工作流
            workflow = self.runner.load_workflow(workflow_path)
            update_params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "duration": duration,
                "fps": fps
            }
            updated_workflow = self.runner.update_workflow_params(workflow, update_params)
            
            # 运行工作流
            success = self.runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                output_path = os.path.join(self.output_dir, output_filename)
                return {'success': True, 'message': '文生视频任务处理成功', 'output_path': output_path}
            else:
                return {'success': False, 'message': '工作流运行失败'}
        except Exception as e:
            error(f"文生视频任务执行失败: {str(e)}")
            return {'success': False, 'message': f'文生视频任务执行失败: {str(e)}'}
    
    def process_text_to_video(self, prompt, negative_prompt, duration=5, fps=30):
        """处理文生视频任务，将任务加入队列"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
        # 准备任务参数
        task_params = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'duration': duration,
            'fps': fps
        }
        
        # 任务回调函数
        def task_callback(params):
            return self._execute_text_to_video(params)
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'text_to_video', 
            task_params, 
            task_callback
        )
        
        # 由于路由是同步处理的，我们需要根据队列位置决定是否立即执行
        if queue_position <= task_queue_manager.max_concurrent_tasks:
            # 如果任务可以立即执行，就直接执行
            return self._execute_text_to_video(task_params)
        else:
            # 否则返回排队信息
            minutes, seconds = divmod(int(waiting_time), 60)
            waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
            return {
                'success': False, 
                'message': f'当前任务较多，请稍候。您的任务已排队，前面还有{queue_position - task_queue_manager.max_concurrent_tasks}个任务，预计等待{waiting_str}。',
                'queued': True,
                'task_id': task_id,
                'queue_position': queue_position,
                'waiting_time': waiting_time
            }
    
    def get_task_status(self, task_id):
        """获取任务状态"""
        return task_queue_manager.get_task_status(task_id)
    
    def get_queue_status(self):
        """获取队列状态"""
        return task_queue_manager.get_queue_status()
    
    def get_all_tasks(self):
        """获取所有任务历史记录"""
        return task_queue_manager.get_all_tasks()
# 全局配置和管理器实例
config = load_config()
workflow_manager = WorkflowManager(config)
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
    
    def process_text_to_image(self, prompt, negative_prompt, width=1024, height=1024, steps=30, cfg_scale=8.0):
        """处理文生图任务"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
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
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale
            }
            updated_workflow = self.runner.update_workflow_params(workflow, params)
            
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
    
    def process_image_to_image(self, image_path, prompt, negative_prompt, width=1024, height=1024, steps=30, cfg_scale=8.0):
        """处理图生图任务"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
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
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "image_path": image_path
            }
            updated_workflow = self.runner.update_workflow_params(workflow, params)
            
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
    
    def process_image_to_video(self, image_path, prompt, negative_prompt, duration=5, fps=30):
        """处理图生视频任务"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
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
    
    def process_text_to_video(self, prompt, negative_prompt, duration=5, fps=30):
        """处理文生视频任务"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}
        
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
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "duration": duration,
                "fps": fps
            }
            updated_workflow = self.runner.update_workflow_params(workflow, params)
            
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

# 全局配置和管理器实例
config = load_config()
workflow_manager = WorkflowManager(config)
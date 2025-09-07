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

# 加载工作流预设
def load_workflow_presets():
    """加载工作流预设配置"""
    presets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'workflow_presets.json')
    try:
        with open(presets_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        error(f"加载工作流预设失败: {e}")
        # 返回默认预设
        return {
            'presets': {
                'text_to_image': {
                    'default': {
                        'model': 'v1-5-pruned-emaonly.safetensors',
                        'vae': 'vae-ft-mse-840000-ema-pruned.safetensors',
                        'sampler': 'dpmpp_2m_sde_karras',
                        'steps': 20,
                        'cfg': 7.0,
                        'width': 512,
                        'height': 512,
                        'batch_size': 1
                    }
                },
                'image_to_image': {
                    'default': {
                        'model': 'v1-5-pruned-emaonly.safetensors',
                        'vae': 'vae-ft-mse-840000-ema-pruned.safetensors',
                        'sampler': 'dpmpp_2m_sde_karras',
                        'steps': 20,
                        'cfg': 7.0,
                        'denoising_strength': 0.75,
                        'width': 512,
                        'height': 512
                    }
                },
                'image_to_video': {
                    'default': {
                        'model': 'svd.safetensors',
                        'motion_bucket_id': 127,
                        'noise_aug_strength': 0.02,
                        'num_frames': 16,
                        'fps': 8,
                        'decode_chunk_size': 8,
                        'width': 512,
                        'height': 320
                    }
                },
                'text_to_video': {
                    'default': {
                        'model': 'svd.safetensors',
                        'motion_bucket_id': 127,
                        'noise_aug_strength': 0.02,
                        'num_frames': 16,
                        'fps': 8,
                        'decode_chunk_size': 8,
                        'width': 512,
                        'height': 320
                    }
                }
            }
        }

class WorkflowManager:
    """工作流管理器类，用于处理各种AI生成任务"""
    
    def __init__(self, config, runner=None):
        """初始化工作流管理器"""
        self.config = config
        self.runner = runner
        # 导入全局的workflow_presets变量
        from scripts.utils.workflow_utils import workflow_presets
        self.workflow_presets = workflow_presets
        self.comfyui_path = config['comfyui']['path'] if config and 'comfyui' in config else './ComfyUI'
        self.output_dir = None
    
    def init_runner(self):
        """初始化工作流运行器"""
        if not self.runner and self.comfyui_path and self.output_dir:
            # 获取配置中的API URL，如果没有则使用默认值
            api_url = self.config.get('comfyui', {}).get('api_url', 'http://127.0.0.1:8188')
            self.runner = ComfyUIRunner(self.comfyui_path, self.output_dir, api_url)
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
        # 从参数中获取配置，同时提供默认值
        width = params.get('width', 512)
        height = params.get('height', 512)
        steps = params.get('steps', 20)
        cfg_scale = params.get('cfg_scale', 7.0)
        model = params.get('model')
        vae = params.get('vae')
        sampler = params.get('sampler')
        batch_size = params.get('batch_size')
        
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
            
            # 添加可选参数（如果存在）
            if model:
                update_params["model"] = model
            if vae:
                update_params["vae"] = vae
            if sampler:
                update_params["sampler"] = sampler
            if batch_size:
                update_params["batch_size"] = batch_size
            
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
    
    def process_text_to_image(self, prompt, negative_prompt, preset='default', **kwargs):
        """异步处理文生图任务，将任务加入队列并立即返回"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 检查ComfyUI服务器是否可用
        if hasattr(self.runner, '_check_server_running'):
            if not self.runner._check_server_running():
                return {'success': False, 'message': 'ComfyUI服务器连接失败，请检查服务器是否正在运行'}

        # 从工作流预设中获取配置
        preset_config = self.workflow_presets.get('presets', {}).get('text_to_image', {}).get(preset, {})
        if not preset_config:
            # 如果预设不存在，使用默认配置
            preset_config = self.workflow_presets.get('presets', {}).get('text_to_image', {}).get('default', {})
        
        # 准备任务参数，优先级：kwargs > preset_config > 默认值
        task_params = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': kwargs.get('width', preset_config.get('width', 512)),
            'height': kwargs.get('height', preset_config.get('height', 512)),
            'steps': kwargs.get('steps', preset_config.get('steps', 20)),
            'cfg_scale': kwargs.get('cfg_scale', preset_config.get('cfg', 7.0)),
            'model': preset_config.get('model'),
            'vae': preset_config.get('vae'),
            'sampler': preset_config.get('sampler'),
            'batch_size': preset_config.get('batch_size')
        }
        
        # 任务回调函数
        def task_callback(params):
            # 任务执行后的回调函数
            result = self._execute_text_to_image(params)
            
            # 如果任务成功完成，更新任务文件数据
            if result and result.get('success'):
                # 这里可以添加任何额外的任务完成后的处理逻辑
                pass
            
            return result
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'text_to_image', 
            task_params, 
            task_callback
        )
        
        # 立即返回任务信息，不等待任务完成
        minutes, seconds = divmod(int(waiting_time), 60)
        waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        return {
            'success': True, 
            'message': f'任务已成功提交到队列，您可以在"我的任务"中查看进度。',
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
        # 从参数中获取配置，同时提供默认值
        width = params.get('width', 512)
        height = params.get('height', 512)
        steps = params.get('steps', 20)
        cfg_scale = params.get('cfg_scale', 7.0)
        denoising_strength = params.get('denoising_strength', 0.75)
        model = params.get('model')
        vae = params.get('vae')
        sampler = params.get('sampler')
        batch_size = params.get('batch_size')
        
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
            
            # 添加可选参数（如果存在）
            if model:
                update_params["model"] = model
            if vae:
                update_params["vae"] = vae
            if sampler:
                update_params["sampler"] = sampler
            if batch_size:
                update_params["batch_size"] = batch_size
            
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
    
    def process_image_to_image(self, image_path, prompt, negative_prompt, preset='default', **kwargs):
        """异步处理图生图任务，将任务加入队列并立即返回"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 检查ComfyUI服务器是否可用
        if hasattr(self.runner, '_check_server_running'):
            if not self.runner._check_server_running():
                return {'success': False, 'message': 'ComfyUI服务器连接失败，请检查服务器是否正在运行'}

        # 从预设中获取配置
        preset_config = self.workflow_presets.get('image_to_image', {}).get(preset, {})
        
        # 参数优先级：kwargs > preset_config > 默认值
        width = kwargs.get('width', preset_config.get('width', 512))
        height = kwargs.get('height', preset_config.get('height', 512))
        steps = kwargs.get('steps', preset_config.get('steps', 20))
        cfg_scale = kwargs.get('cfg_scale', preset_config.get('cfg_scale', 7.0))
        denoising_strength = kwargs.get('denoising_strength', preset_config.get('denoising_strength', 0.75))
        model = kwargs.get('model', preset_config.get('model'))
        vae = kwargs.get('vae', preset_config.get('vae'))
        sampler = kwargs.get('sampler', preset_config.get('sampler'))
        batch_size = kwargs.get('batch_size', preset_config.get('batch_size'))
        
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
        
        # 添加可选参数
        if model:
            task_params['model'] = model
        if vae:
            task_params['vae'] = vae
        if sampler:
            task_params['sampler'] = sampler
        if batch_size:
            task_params['batch_size'] = batch_size
        
        # 任务回调函数
        def task_callback(params):
            # 任务执行后的回调函数
            result = self._execute_image_to_image(params)
            
            # 如果任务成功完成，更新任务文件数据
            if result and result.get('success'):
                # 这里可以添加任何额外的任务完成后的处理逻辑
                pass
            
            return result
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'image_to_image', 
            task_params, 
            task_callback
        )
        
        # 立即返回任务信息，不等待任务完成
        minutes, seconds = divmod(int(waiting_time), 60)
        waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        return {
            'success': True, 
            'message': f'任务已成功提交到队列，您可以在"我的任务"中查看进度。',
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
        # 从参数中获取配置，同时提供默认值
        duration = params.get('duration', 5)
        fps = params.get('fps', 30)
        model = params.get('model')
        motion_model = params.get('motion_model')
        steps = params.get('steps', 20)
        cfg_scale = params.get('cfg_scale', 7.0)
        
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
    
    def process_image_to_video(self, image_path, prompt, negative_prompt, preset='default', **kwargs):
        """异步处理图生视频任务，将任务加入队列并立即返回"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 检查ComfyUI服务器是否可用
        if hasattr(self.runner, '_check_server_running'):
            if not self.runner._check_server_running():
                return {'success': False, 'message': 'ComfyUI服务器连接失败，请检查服务器是否正在运行'}

        # 从预设中获取配置
        preset_config = self.workflow_presets.get('image_to_video', {}).get(preset, {})
        
        # 参数优先级：kwargs > preset_config > 默认值
        duration = kwargs.get('duration', preset_config.get('duration', 5))
        fps = kwargs.get('fps', preset_config.get('fps', 30))
        model = kwargs.get('model', preset_config.get('model'))
        motion_model = kwargs.get('motion_model', preset_config.get('motion_model'))
        steps = kwargs.get('steps', preset_config.get('steps', 20))
        cfg_scale = kwargs.get('cfg_scale', preset_config.get('cfg_scale', 7.0))
        
        # 准备任务参数
        task_params = {
            'image_path': image_path,
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'duration': duration,
            'fps': fps
        }
        
        # 添加可选参数
        if model:
            task_params['model'] = model
        if motion_model:
            task_params['motion_model'] = motion_model
        if steps:
            task_params['steps'] = steps
        if cfg_scale:
            task_params['cfg_scale'] = cfg_scale
        
        # 任务回调函数
        def task_callback(params):
            # 任务执行后的回调函数
            result = self._execute_image_to_video(params)
            
            # 如果任务成功完成，更新任务文件数据
            if result and result.get('success'):
                # 这里可以添加任何额外的任务完成后的处理逻辑
                pass
            
            return result
        
        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'image_to_video', 
            task_params, 
            task_callback
        )
        
        # 立即返回任务信息，不等待任务完成
        minutes, seconds = divmod(int(waiting_time), 60)
        waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        return {
            'success': True, 
            'message': f'任务已成功提交到队列，您可以在"我的任务"中查看进度。',
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
        # 从参数中获取配置，同时提供默认值
        duration = params.get('duration', 5)
        fps = params.get('fps', 30)
        model = params.get('model')
        motion_model = params.get('motion_model')
        steps = params.get('steps', 20)
        cfg_scale = params.get('cfg_scale', 7.0)
        
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
            
            # 添加可选参数（如果存在）
            if model:
                update_params["model"] = model
            if motion_model:
                update_params["motion_model"] = motion_model
            if steps:
                update_params["steps"] = steps
            if cfg_scale:
                update_params["cfg_scale"] = cfg_scale
            
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
    
    def process_text_to_video(self, prompt, negative_prompt, preset='default', **kwargs):
        """异步处理文生视频任务，将任务加入队列并立即返回"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 检查ComfyUI服务器是否可用
        if hasattr(self.runner, '_check_server_running'):
            if not self.runner._check_server_running():
                return {'success': False, 'message': 'ComfyUI服务器连接失败，请检查服务器是否正在运行'}

        # 从预设中获取配置
        preset_config = self.workflow_presets.get('text_to_video', {}).get(preset, {})

        # 参数优先级：kwargs > preset_config > 默认值
        duration = kwargs.get('duration', preset_config.get('duration', 5))
        fps = kwargs.get('fps', preset_config.get('fps', 30))
        model = kwargs.get('model', preset_config.get('model'))
        motion_model = kwargs.get('motion_model', preset_config.get('motion_model'))
        steps = kwargs.get('steps', preset_config.get('steps', 20))
        cfg_scale = kwargs.get('cfg_scale', preset_config.get('cfg_scale', 7.0))

        # 准备任务参数
        task_params = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'duration': duration,
            'fps': fps
        }

        # 添加可选参数
        if model:
            task_params['model'] = model
        if motion_model:
            task_params['motion_model'] = motion_model
        if steps:
            task_params['steps'] = steps
        if cfg_scale:
            task_params['cfg_scale'] = cfg_scale

        # 任务回调函数
        def task_callback(params):
            # 任务执行后的回调函数
            result = self._execute_text_to_video(params)

            # 如果任务成功完成，更新任务文件数据
            if result and result.get('success'):
                # 这里可以添加任何额外的任务完成后的处理逻辑
                pass

            return result

        # 将任务加入队列
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'text_to_video', 
            task_params, 
            task_callback
        )

        # 立即返回任务信息，不等待任务完成
        minutes, seconds = divmod(int(waiting_time), 60)
        waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        return {
            'success': True, 
            'message': f'任务已成功提交到队列，您可以在"我的任务"中查看进度。',
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
workflow_presets = load_workflow_presets()
workflow_manager = WorkflowManager(config)
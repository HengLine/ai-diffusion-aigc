#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowManager类和配置加载功能
"""
import time
import uuid
from typing import Dict, Any, Callable, Optional
from hengline.core.task_queue import task_queue_manager
# 导入配置工具
from hengline.utils.config_utils import load_workflow_presets, get_comfyui_api_url, \
    get_output_folder
from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.workflow.workflow_comfyui import comfyui_api
from hengline.logger import error


class WorkflowManager:
    """工作流管理器类，用于处理各种AI生成任务"""

    def __init__(self, runner=None):
        """初始化工作流管理器"""
        # 不再依赖传入的config参数，统一使用config_utils
        self.runner = runner
        # 导入全局的workflow_presets变量
        self.workflow_presets = load_workflow_presets()
        self.output_dir = get_output_folder()

    def init_runner(self):
        """初始化工作流运行器"""
        if not self.runner and self.output_dir:
            # 使用配置工具获取API URL
            api_url = get_comfyui_api_url()
            self.runner = ComfyUIRunner(self.output_dir, api_url)
        return self.runner is not None

    def stop_runner(self):
        """停止工作流运行器"""
        if self.runner:
            # 这里不直接停止服务器，而是由app_flask.py中的全局变量处理
            self.runner = None

    def get_task_status(self, task_id):
        """获取任务状态"""
        return task_queue_manager.get_task_status(task_id)

    def get_queue_status(self):
        """获取队列状态"""
        return task_queue_manager.get_queue_status()

    def get_all_tasks(self):
        """获取所有任务历史记录"""
        return task_queue_manager.get_all_tasks()
        
    def async_execute_task(self, task_type: str, params: Dict[str, Any], 
                          on_completion: Optional[Callable] = None, 
                          on_error: Optional[Callable] = None) -> str:
        """
        异步执行任务的通用方法
        
        Args:
            task_type: 任务类型
            params: 任务参数
            on_completion: 任务完成时的回调函数
            on_error: 任务失败时的回调函数
            
        Returns:
            str: 任务ID
        """
        if not self.init_runner():
            error_msg = '无法初始化工作流运行器'
            if on_error:
                on_error(error_msg)
            return ""
        
        # 检查ComfyUI服务器是否可用
        if not self.runner._check_server_running():
            error_msg = 'ComfyUI服务器连接异常'
            if on_error:
                on_error(error_msg)
            return ""
        
        try:
            # 生成唯一的输出文件名
            timestamp = int(time.time())
            uuid_str = uuid.uuid4().hex[:8]
            output_ext = 'mp4' if task_type == 'image_to_video' or task_type == 'text_to_video' else 'png'
            output_filename = f"{task_type}_{timestamp}_{uuid_str}.{output_ext}"
            
            # 加载对应的工作流
            workflow_filename = f"{task_type}.json" if task_type != 'text_to_image' else 'text_to_image.json'
            workflow_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "workflows", workflow_filename
            )
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                error_msg = f'工作流文件不存在: {workflow_path}'
                if on_error:
                    on_error(error_msg)
                return ""
            
            # 加载工作流
            workflow = self.runner.load_workflow(workflow_path)
            
            # 根据任务类型进行特殊处理
            updated_workflow = workflow
            if task_type == 'image_to_video' or task_type == 'image_to_image':
                # 图生视频/图生图任务需要上传图片
                image_path = params.get('image_path', '')
                if image_path and os.path.exists(image_path):
                    # 使用comfyui_api上传图片并将文件名填充到工作流中
                    updated_workflow = comfyui_api.upload_and_fill_image(image_path, workflow)
                    if not updated_workflow:
                        error_msg = f'上传图片失败: {image_path}'
                        if on_error:
                            on_error(error_msg)
                        return ""
            else:
                # 更新工作流参数
                updated_workflow = self.runner.update_workflow_params(workflow, params)
            
            # 异步运行工作流
            task_id = self.runner.async_run_workflow(
                updated_workflow,
                output_filename,
                on_completion=on_completion,
                on_error=on_error
            )
            
            return task_id
        except Exception as e:
            error_msg = f'任务执行失败: {str(e)}'
            if on_error:
                on_error(error_msg)
            return ""

# 全局配置和管理器实例
# workflow_manager = WorkflowManager()

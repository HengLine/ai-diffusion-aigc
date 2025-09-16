#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowManager类和配置加载功能
"""
import os
import random
from typing import Dict, Any

from hengline.logger import info, error, debug
from hengline.task.task_manage import task_queue_manager
# 导入配置工具
from hengline.utils.config_utils import load_workflow_presets, get_comfyui_api_url, \
    get_output_folder, get_effective_config, get_workflow_path
from hengline.utils.file_utils import generate_output_filename
from hengline.utils.log_utils import print_log_exception
from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.workflow.workflow_comfyui import comfyui_api
from hengline.workflow.workflow_node import load_workflow, update_workflow_params


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

    def _process_common(self, task_type, image_path, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """
        异步处理任务，将任务加入队列并立即返回

        Args:
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 任务提交结果
        """
        # 获取最终的有效配置，遵循优先级：页面输入 > setting节点 > default节点
        preset_config = get_effective_config(task_type, **kwargs)

        task_params = preset_config.copy()
        # 确保关键参数被正确设置
        task_params['prompt'] = prompt
        task_params['negative_prompt'] = negative_prompt
        if image_path:
            task_params['image_path'] = image_path

        # 从有效配置中提取参数
        seed = task_params.get('seed', -1)
        if seed < 0:
            task_params['seed'] = random.randint(0, 2 ** 50 - 1)

        # 将任务加入队列，获取task_id
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            None,
            task_type,
            task_params,
            self._execute_common
        )

        # 立即返回任务信息，不等待任务完成
        minutes, seconds = divmod(int(waiting_time), 60)
        waiting_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
        return {
            'success': True,
            'message': f'任务已成功提交，您可以在"我的任务"中查看进度。',
            'queued': True,
            'task_id': task_id,
            'queue_position': queue_position,
            'waiting_time': waiting_str
        }

    def _execute_common(self, task_type, params: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        执行文本到图像的工作流（异步版本）

        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID

        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        try:
            info(f"执行{task_type}的{task_id}工作流...")
            if not self.init_runner():
                return {'success': False, 'message': '无法初始化工作流运行器'}

            # 确保ComfyUI服务器正在运行
            # 使用异步版本的服务器检查方法
            server_running = comfyui_api.check_server_status()
            if not server_running:
                error("无法连接到ComfyUI服务器，请确保服务器已启动")
                return {"success": False, "message": "无法连接到ComfyUI服务器，请确保服务器已启动"}

            # 获取工作流文件路径
            workflow_path = get_workflow_path(task_type)
            if not workflow_path:
                error(f"未找到{task_type}工作流文件")
                return {"success": False, "message": f"未找到{task_type}工作流文件"}

            # 加载工作流
            workflow = load_workflow(workflow_path)
            if workflow is None:
                error("工作流加载失败")
                return {"success": False, "message": "工作流加载失败"}

            # 上传图片到ComfyUI服务器并更新工作流
            image_path = params.get('image_path', '')
            updated_workflow = workflow
            if image_path and os.path.exists(image_path):
                # 使用comfyui_api上传图片并将文件名填充到工作流中
                updated_workflow = comfyui_api.upload_and_fill_image(image_path, updated_workflow)
                if not updated_workflow:
                    error("图片上传失败，无法继续处理图生图任务")
                    return {"success": False, "message": "图片上传失败"}
            elif task_type in ['image_to_image', 'image_to_video']:
                # 如果没有图片路径或图片文件不存在
                error(f"无效的图片路径: {image_path}")
                return {"success": False, "message": f"无效的图片路径: {image_path}"}

            # 创建params的副本，并移除image_path参数以避免覆盖已设置的图片节点值
            params_without_image = params.copy()
            if 'image_path' in params_without_image:
                del params_without_image['image_path']
                debug("已从参数中移除image_path以避免覆盖已设置的图片节点值")

            # 更新其他工作流参数
            updated_workflow = update_workflow_params(updated_workflow, params_without_image)
            if updated_workflow is None:
                error("更新工作流参数失败")
                return {"success": False, "message": "更新工作流参数失败"}

            # 生成唯一的输出文件名
            output_filename = generate_output_filename(task_type)

            # 异步运行工作流并设置回调函数
            def on_completion(output_paths, task_id, prompt_id):
                debug(f"文生图工作流完成，输出文件路径: {output_paths}")
                task_queue_manager.history_tasks[task_id].params['prompt_id'] = prompt_id

            def on_error(error_message):
                debug(f"文生图工作流失败: {error_message}")
                # 这里可以添加任何工作流失败后的处理逻辑

            prompt_id = self.runner.async_run_workflow(
                updated_workflow,
                output_filename,
                on_complete=on_completion,
                on_error=on_error,
                task_id=task_id
            )

            # 返回任务信息，而不是等待结果
            return {
                "success": True,
                "message": "工作流已成功提交",
                "task_id": task_id,
                "prompt_id": prompt_id,
                "output_filename": output_filename
            }

        except Exception as e:
            error(f"执行{task_id}工作流时出错: {str(e)}")
            # 添加详细的异常信息
            print_log_exception()
            return {"success": False, "message": f"执行{task_id}工作流时出错: {str(e)}"}

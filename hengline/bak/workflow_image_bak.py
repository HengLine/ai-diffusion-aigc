#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowImageManager类，用于处理AI图像生成任务
"""
import asyncio
import os
import random
import sys
import traceback
import uuid
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入需要的模块
from hengline.logger import info, debug, warning, error
from hengline.task.task_manage import task_queue_manager
from hengline.utils.config_utils import get_effective_config, get_workflow_path
from hengline.workflow.workflow_comfyui import comfyui_api
from hengline.utils.file_utils import generate_output_filename
from hengline.workflow.workflow_core import WorkflowManager
from hengline.workflow.workflow_node import load_workflow, update_workflow_params


class WorkflowImageManager(WorkflowManager):
    """工作流图像管理器类，用于处理各种AI图像生成任务"""

    def _execute_text_to_image(self, params: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        执行文本到图像的工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        try:
            info(f"执行文生图工作流...")

            # 确保ComfyUI服务器正在运行
            # 使用异步版本的服务器检查方法
            server_running = comfyui_api.check_server_running()
            if not server_running:
                warning("ComfyUI服务器未运行，正在尝试启动...")
                # 尝试启动ComfyUI服务器（如果配置了自动启动）
                # workflow_core_manager.try_start_comfyui_server()

                # 再次检查服务器状态
                if not comfyui_api.check_server_running():
                    error("无法连接到ComfyUI服务器，请确保服务器已启动")
                    return {"success": False, "message": "无法连接到ComfyUI服务器，请确保服务器已启动"}

            # 获取工作流文件路径
            workflow_path = get_workflow_path("text_to_image")
            if not workflow_path:
                error("未找到文生图工作流文件")
                return {"success": False, "message": "未找到文生图工作流文件"}

            # 加载工作流
            workflow = load_workflow(workflow_path)
            if workflow is None:
                error("工作流加载失败")
                return {"success": False, "message": "工作流加载失败"}

            # 更新工作流参数
            updated_workflow = update_workflow_params(workflow, params)
            if updated_workflow is None:
                error("更新工作流参数失败")
                return {"success": False, "message": "更新工作流参数失败"}

            # 生成唯一的输出文件名
            output_filename = generate_output_filename("text_to_image")

            # 异步运行工作流并设置回调函数
            def on_completion(output_paths):
                debug(f"文生图工作流完成，输出文件路径: {output_paths}")
                # 这里可以添加任何工作流完成后的处理逻辑

            def on_error(error_message):
                debug(f"文生图工作流失败: {error_message}")
                # 这里可以添加任何工作流失败后的处理逻辑

            asyncio.run(self.runner.async_run_workflow(
                updated_workflow,
                output_filename,
                on_complete=on_completion,
                on_error=on_error,
                task_id=task_id
            ))

            # 返回任务信息，而不是等待结果
            return {
                "success": True,
                "message": "文生图工作流已成功提交",
                "task_id": task_id,
                "output_filename": output_filename
            }

        except Exception as e:
            error(f"执行文生图工作流时出错: {str(e)}")
            # 添加详细的异常信息
            debug(f"异常详情: {traceback.format_exc()}")
            return {"success": False, "message": f"执行文生图工作流时出错: {str(e)}"}

    async def _execute_image_to_image(self, params: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        执行图像到图像的工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        try:
            info(f"执行图生图工作流...")

            # 确保ComfyUI服务器正在运行
            server_running = comfyui_api.check_server_running()
            if not server_running:
                warning("ComfyUI服务器未运行，正在尝试启动...")
                # 尝试启动ComfyUI服务器（如果配置了自动启动）
                # workflow_core_manager.try_start_comfyui_server()

                # 再次检查服务器状态
                if not comfyui_api.check_server_running():
                    error("无法连接到ComfyUI服务器，请确保服务器已启动")
                    return {"success": False, "message": "无法连接到ComfyUI服务器，请确保服务器已启动"}

            # 获取工作流文件路径
            workflow_path = get_workflow_path("image_to_image")
            if not workflow_path:
                error("未找到图生图工作流文件")
                return {"success": False, "message": "未找到图生图工作流文件"}

            # 加载工作流
            workflow = load_workflow(workflow_path)
            if workflow is None:
                error("工作流加载失败")
                return {"success": False, "message": "工作流加载失败"}

            # 上传图片到ComfyUI服务器并更新工作流
            image_path = params.get('image_path', '')
            if image_path and os.path.exists(image_path):
                # 使用comfyui_api上传图片并将文件名填充到工作流中
                updated_workflow = comfyui_api.upload_and_fill_image(image_path, workflow)
                if not updated_workflow:
                    error("图片上传失败，无法继续处理图生图任务")
                    return {"success": False, "message": "图片上传失败"}
            else:
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
            output_filename = generate_output_filename("image_to_image")

            # 异步运行工作流并设置回调函数
            def on_complete(output_paths):
                debug(f"图生图工作流完成，输出文件路径: {output_paths}")
                # 这里可以添加任何工作流完成后的处理逻辑

            def on_error(error_message):
                debug(f"图生图工作流失败: {error_message}")
                # 这里可以添加任何工作流失败后的处理逻辑

            # 异步运行工作流，传入外部创建的task_id
            await self.runner.async_run_workflow(
                updated_workflow,
                output_filename,
                on_complete=on_complete,
                on_error=on_error,
                task_id=task_id
            )

            # 返回任务信息，而不是等待结果
            return {
                "success": True,
                "message": "图生图工作流已成功提交",
                "task_id": task_id,
                "output_filename": output_filename
            }

        except Exception as e:
            error(f"执行图生图工作流时出错: {str(e)}")
            # 添加详细的异常信息
            debug(f"异常详情: {traceback.format_exc()}")
            return {"success": False, "message": f"执行图生图工作流时出错: {str(e)}"}

    def process_text_to_image(self, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """
        异步处理文生图任务，将任务加入队列并立即返回
        
        Args:
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 任务提交结果
        """
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 获取最终的有效配置，遵循优先级：页面输入 > setting节点 > default节点
        preset_config = get_effective_config('text_to_image', **kwargs)

        task_params = preset_config.copy()
        # 确保关键参数被正确设置
        task_params['prompt'] = prompt
        task_params['negative_prompt'] = negative_prompt

        # 从有效配置中提取参数
        seed = preset_config.get('seed', -1)
        if seed < 0:
            preset_config['seed'] = random.randint(0, 2 ** 50 - 1)

        # 准备任务参数
        task_id = str(uuid.uuid4())
        result = self._execute_text_to_image(task_params, task_id)
        if not result.get('success', False):
            error(f"执行文生图任务失败: {result.get('message', '未知错误')}")
            return result

        # 创建一个辅助函数来确保正确捕获task_id
        def create_execute_callback():
            # 这里不需要传入task_id，因为它将由task_queue_manager自动处理
            info(f"将文生图任务加入队列，task_id: {task_id}")

        # 将任务加入队列，获取task_id
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'text_to_image',
            task_params,
            create_execute_callback
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
            'waiting_time': waiting_str
        }

    def process_image_to_image(self, image_path: str, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[
        str, Any]:
        """
        异步处理图生图任务，将任务加入队列并立即返回
        
        Args:
            image_path: 输入图像路径
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 任务提交结果
        """
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 获取最终的有效配置，遵循优先级：页面输入 > setting节点 > default节点
        preset_config = get_effective_config('image_to_image', **kwargs)

        # 确保关键参数被正确设置
        preset_config['image_path'] = image_path
        preset_config['prompt'] = prompt
        preset_config['negative_prompt'] = negative_prompt

        # 从有效配置中提取参数
        seed = preset_config.get('seed', -1)
        if seed < 0:
            preset_config['seed'] = random.randint(0, 2 ** 50 - 1)

        # 准备任务参数
        task_params = preset_config.copy()

        # 创建一个辅助函数来确保正确捕获task_id
        def create_execute_callback():
            async def execute_callback(params):
                # 这里不需要传入task_id，因为它将由task_queue_manager自动处理
                return await self._execute_image_to_image(params, task_id)

            return execute_callback

        # 将任务加入队列，获取task_id
        task_id, queue_position, waiting_time = task_queue_manager.enqueue_task(
            'image_to_image',
            task_params,
            create_execute_callback()
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
            'waiting_time': waiting_str
        }


# 全局配置和管理器实例
workflow_image_manager = WorkflowImageManager()

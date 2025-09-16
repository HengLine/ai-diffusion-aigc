#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowManager类和配置加载功能
"""
import asyncio
import os
import time
import uuid
from typing import Dict, Any, Callable, Optional, Tuple

from hengline.task.task_manage import task_queue_manager
# 导入配置工具
from hengline.utils.config_utils import load_workflow_presets, get_comfyui_api_url, \
    get_output_folder
from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.workflow.workflow_comfyui import comfyui_api


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

    async def async_execute_task(self, task_type: str, params: Dict[str, Any],
                           on_completion: Optional[Callable] = None,
                           on_error: Optional[Callable] = None) -> str:
        """
        异步执行任务的通用方法（异步版本）
        
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
        if not comfyui_api.check_server_running():
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
            task_id = await self.runner.async_run_workflow(
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

    #  异步将任务加入队列
    async def async_enqueue_task(self, task_type: str, params: Dict[str, Any], 
                                task_id: str = None, 
                                on_completion: Optional[Callable] = None, 
                                on_error: Optional[Callable] = None) -> Tuple[str, int, float]:
        """
        异步将任务加入队列
        
        Args:
            task_type: 任务类型
            params: 任务参数
            task_id: 可选的任务ID，如果不提供则自动生成
            on_completion: 任务完成时的回调函数
            on_error: 任务失败时的回调函数
            
        Returns:
            Tuple[str, int, float]: (任务ID, 队列位置, 预估等待时间(秒))
        """
        # 初始化工作流运行器
        if not self.init_runner():
            error_msg = '无法初始化工作流运行器'
            if on_error:
                on_error(error_msg)
            raise Exception(error_msg)
        
        # 创建适合TaskQueueManager的回调函数
        async def task_callback(task_params):
            try:
                # 这里会在任务实际执行时调用
                # 加载对应的工作流
                workflow_filename = f"{task_type}.json"
                workflow_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "workflows", workflow_filename
                )
                
                # 检查工作流文件是否存在
                if not os.path.exists(workflow_path):
                    error_msg = f'工作流文件不存在: {workflow_path}'
                    if on_error:
                        on_error(error_msg)
                    return {"success": False, "message": error_msg}
                
                # 加载工作流
                workflow = self.runner.load_workflow(workflow_path)
                
                # 根据任务类型进行特殊处理
                updated_workflow = workflow
                if task_type == 'image_to_video' or task_type == 'image_to_image':
                    # 图生视频/图生图任务需要上传图片
                    image_path = task_params.get('image_path', '')
                    if image_path and os.path.exists(image_path):
                        # 使用comfyui_api上传图片并将文件名填充到工作流中
                        updated_workflow = comfyui_api.upload_and_fill_image(image_path, workflow)
                        if not updated_workflow:
                            error_msg = f'上传图片失败: {image_path}'
                            if on_error:
                                on_error(error_msg)
                            return {"success": False, "message": error_msg}
                else:
                    # 更新工作流参数
                    updated_workflow = self.runner.update_workflow_params(workflow, task_params)
                
                # 异步运行工作流
                result = await self.runner.async_run_workflow(
                    updated_workflow,
                    task_params.get('output_filename', ''),
                    on_completion=on_completion,
                    on_error=on_error
                )
                
                return result
            except Exception as e:
                error_msg = f'任务执行失败: {str(e)}'
                if on_error:
                    on_error(error_msg)
                return {"success": False, "message": error_msg}
        
        # 生成唯一的输出文件名
        timestamp = int(time.time())
        uuid_str = uuid.uuid4().hex[:8]
        output_ext = 'mp4' if task_type == 'image_to_video' or task_type == 'text_to_video' else 'png'
        output_filename = f"{task_type}_{timestamp}_{uuid_str}.{output_ext}"
        
        # 添加输出文件名到参数
        task_params = params.copy()
        task_params['output_filename'] = output_filename
        
        # 同步执行enqueue_task，因为它已经是线程安全的
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: task_queue_manager.enqueue_task(
                task_id=task_id,
                task_type=task_type,
                params=task_params,
                callback=lambda p: asyncio.run_coroutine_threadsafe(task_callback(p), loop)
            )
        )
        
        return result

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

        # 创建一个辅助函数来确保正确捕获task_id
        def create_execute_callback():
            # 这里不需要传入task_id，因为它将由task_queue_manager自动处理
            info(f"将文生图任务加入队列")

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
            def on_completion(output_paths, task_id, prompt_id):
                debug(f"文生图工作流完成，输出文件路径: {output_paths}")
                task_queue_manager.history_tasks[task_id].params['prompt_id'] = prompt_id

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
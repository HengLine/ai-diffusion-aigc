#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowManager类和配置加载功能
"""
import os
import time
import uuid

from hengline.core.task_queue import task_queue_manager
from hengline.logger import error, warning, debug
# 从配置工具导入获取有效配置的函数
from hengline.utils.config_utils import get_effective_config
# 导入配置工具
from hengline.workflow.workflow_core import WorkflowManager


class WorkflowImageManager(WorkflowManager):
    """工作流管理器类，用于处理各种AI生成任务"""

    """
    实际执行文生图任务的方法，用于队列调用
    """

    def _execute_text_to_image(self, params):
        """实际执行文生图任务的方法，用于队列调用"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        try:
            debug(f"处理文生图任务: {params['prompt']}")

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

            updated_workflow = self.runner.update_workflow_params(workflow, params)

            # 检查ComfyUI服务器是否可用
            if not self.runner._check_server_running():
                warning("ComfyUI服务器连接异常，将任务放入任务记录")
                return {'success': False, 'queued': True, 'message': 'ComfyUI服务器连接异常'}

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

    """
    文生图任务处理方法
    """

    def process_text_to_image(self, prompt, negative_prompt, **kwargs):
        """异步处理文生图任务，将任务加入队列并立即返回"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 获取最终的有效配置，遵循优先级：页面输入 > setting节点 > default节点
        preset_config = get_effective_config('text_to_image', **kwargs)

        # 确保prompt和negative_prompt被正确设置
        preset_config['prompt'] = prompt
        preset_config['negative_prompt'] = negative_prompt

        # 准备任务参数，直接使用有效配置
        task_params = {
            'prompt': preset_config.get('prompt', ''),
            'negative_prompt': preset_config.get('negative_prompt', ''),
            'width': preset_config.get('width', 512),
            'height': preset_config.get('height', 512),
            'steps': preset_config.get('steps', 20),
            'cfg': preset_config.get('cfg', 7.0),
            'seed': preset_config.get('seed', -1),
            'batch_size': preset_config.get('batch_size', 1)
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
            'waiting_time': waiting_str
        }

    """
    实际执行图生图任务的方法，用于队列调用
    """

    def _execute_image_to_image(self, params):
        """实际执行图生图任务的方法，用于队列调用"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        try:
            debug(f"处理图生图任务: {params['prompt']}")

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

            updated_workflow = self.runner.update_workflow_params(workflow, params)

            # 检查ComfyUI服务器是否可用
            if not self.runner._check_server_running():
                warning("ComfyUI服务器连接异常，将任务放入任务记录")
                return {'success': False, 'queued': True, 'message': 'ComfyUI服务器连接异常'}

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

    """
    图生图任务处理方法
    """

    def process_image_to_image(self, image_path, prompt, negative_prompt, **kwargs):
        """异步处理图生图任务，将任务加入队列并立即返回"""
        if not self.init_runner():
            return {'success': False, 'message': '无法初始化工作流运行器'}

        # 获取最终的有效配置，遵循优先级：页面输入 > setting节点 > default节点
        preset_config = get_effective_config('image_to_image', **kwargs)

        # 确保关键参数被正确设置
        preset_config['image_path'] = image_path
        preset_config['prompt'] = prompt
        preset_config['negative_prompt'] = negative_prompt

        # 从有效配置中提取参数
        # 准备任务参数
        task_params = {
            'image_path': image_path,
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': preset_config.get('width', 512),
            'height': preset_config.get('height', 512),
            'steps': preset_config.get('steps', 20),
            'cfg': preset_config.get('cfg', 7.0),
            'denoise': preset_config.get('denoise', 0.75),
            'seed': preset_config.get('seed', -1),
            'batch_size': preset_config.get('batch_size', 1)
        }

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
            'waiting_time': waiting_str
        }


# 全局配置和管理器实例
workflow_image_manager = WorkflowImageManager()

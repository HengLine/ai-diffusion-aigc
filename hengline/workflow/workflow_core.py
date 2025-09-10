#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowManager类和配置加载功能
"""
from hengline.core.task_queue import task_queue_manager
# 导入配置工具
from hengline.utils.config_utils import max_concurrent_tasks, load_workflow_presets, get_comfyui_api_url, \
    get_output_folder
from hengline.workflow.run_workflow import ComfyUIRunner


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

# 全局配置和管理器实例
# workflow_manager = WorkflowManager(max_concurrent_tasks)

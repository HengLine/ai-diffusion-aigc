#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流工具模块，包含WorkflowVideoManager类，用于处理AI视频生成任务
"""
import os
import sys
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入需要的模块
from hengline.logger import info
from hengline.workflow.workflow_manage import WorkflowManager


class WorkflowVideoManager(WorkflowManager):
    """工作流视频管理器类，用于处理各种AI视频生成任务"""

    def execute_image_to_video(self, params: Dict[str, Any], task_id: str = None) -> Dict[str, Any]:
        """
        执行图像到视频的工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        info(f"执行图生视频工作流...")
        return self._execute_common(self, "image_to_video", params, task_id)

    def process_image_to_video(self, image_path: str, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """
        异步处理图生视频任务，将任务加入队列并立即返回
        
        Args:
            image_path: 输入图像路径
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 任务提交结果
        """
        return self._process_common(self, 'image_to_video', image_path, prompt, negative_prompt, **kwargs)

    def execute_text_to_video(self, params: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        执行文本到视频的工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        info(f"执行文生视频工作流...")
        return self._execute_common(self, "text_to_video", params, task_id)

    def process_text_to_video(self, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """
        异步处理文生视频任务，将任务加入队列并立即返回

        Args:
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 任务提交结果
        """
        return self._process_common('text_to_video', None, prompt, negative_prompt, **kwargs)


# 全局配置和管理器实例
workflow_video_manager = WorkflowVideoManager()

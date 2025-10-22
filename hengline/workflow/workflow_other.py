#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@FileName: workflow_other.py
@Description: 其他功能工作流管理器，负责处理换装、换脸等特殊图像处理任务
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
import os
import sys
from typing import Dict, Any, Coroutine

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入需要的模块
from hengline.workflow.workflow_manage import WorkflowManager


class WorkflowOtherManager(WorkflowManager):
    """工作流图像管理器类，用于处理各种AI图像生成任务"""

    def execute_change_clothes(self, params: Dict[str, Any], task_id: str) -> Coroutine[Any, Any, dict[str, Any]]:
        """
        执行换装工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        return self._execute_common("change_clothes", params, task_id)

    def execute_change_face(self, params: Dict[str, Any], task_id: str) -> Coroutine[Any, Any, dict[str, Any]]:
        """
        执行换脸工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        return self._execute_common("change_face", params, task_id)

    def execute_change_hair_style(self, params: Dict[str, Any], task_id: str) -> Coroutine[Any, Any, dict[str, Any]]:
        """
        执行换发型工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        return self._execute_common("change_hair_style", params, task_id)

    def process_change_clothes(self, image_path: str, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[
        str, Any]:
        """
        异步处理换装任务，将任务加入队列并立即返回
        
        Args:
            image_path: 输入图像路径
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 任务提交结果
        """
        return self._process_common('change_clothes', image_path, prompt, negative_prompt, **kwargs)

    def process_change_face(self, image_path: str, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[
        str, Any]:
        """
        异步处理换脸任务，将任务加入队列并立即返回
        
        Args:
            image_path: 输入图像路径
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 任务提交结果
        """
        return self._process_common('change_face', image_path, prompt, negative_prompt, **kwargs)

    def process_change_hair_style(self, image_path: str, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[
        str, Any]:
        """
        异步处理换发型任务，将任务加入队列并立即返回
        
        Args:
            image_path: 输入图像路径
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数
        
        Returns:
            Dict[str, Any]: 任务提交结果
        """
        return self._process_common('change_hair_style', image_path, prompt, negative_prompt, **kwargs)


# 全局配置和管理器实例
workflow_other_manager = WorkflowOtherManager()

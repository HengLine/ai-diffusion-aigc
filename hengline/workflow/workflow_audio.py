#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@FileName: workflow_audio.py
@Description: 音频工作流管理器，负责处理AI音频生成任务的工作流
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
import os
import sys
from typing import Dict, Any, Coroutine

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入需要的模块
from hengline.logger import info
from hengline.workflow.workflow_manage import WorkflowManager


class WorkflowAudioManager(WorkflowManager):
    """工作流音频管理器类，用于处理各种AI音频生成任务"""

    def execute_text_to_audio(self, params: Dict[str, Any], task_id: str) -> Coroutine[Any, Any, dict[str, Any]]:
        """
        执行文本到音频的工作流（异步版本）
        
        Args:
            params: 工作流参数
            task_id: 从外部传入的任务ID
        
        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        info(f"执行文生音频工作流...")
        return self._execute_common("text_to_audio", params, task_id)

    def process_text_to_audio(self, prompt: str, negative_prompt: str = "", **kwargs) -> Dict[str, Any]:
        """
        异步处理文生音频任务，将任务加入队列并立即返回

        Args:
            prompt: 提示词
            negative_prompt: 负面提示词
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 任务提交结果
        """
        return self._process_common('text_to_audio', None, prompt, negative_prompt, **kwargs)


# 全局配置和管理器实例
workflow_audio_manager = WorkflowAudioManager()

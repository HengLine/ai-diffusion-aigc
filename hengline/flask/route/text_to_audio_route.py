# -*- coding: utf-8 -*-
"""
文生音频路由模块
"""

import os
import sys
import time

from flask import Blueprint, render_template, request, jsonify

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入WorkflowManager
from hengline.workflow.workflow_audio import workflow_audio_manager
# 从配置工具获取页面显示的参数（setting节点优先于default节点）
from hengline.utils.config_utils import get_workflow_preset
# 配置日志
from hengline.logger import warning, error, debug

# 创建Blueprint
text_to_audio_bp = Blueprint('text_to_audio', __name__)


@text_to_audio_bp.route('/text_to_audio', methods=['GET'])
def text_to_audio():
    """文生音频页面路由"""

    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
    display_params = get_workflow_preset('text_to_audio', 'setting')
    if not display_params:  # 如果setting节点为空，则使用default节点
        display_params = get_workflow_preset('text_to_audio', 'default')

    return render_template('text_to_audio.html', default_params=display_params)


@text_to_audio_bp.route('/api/text_to_audio', methods=['POST'])
def api_text_to_audio():
    """
    文生音频功能的API端点
    接受JSON或multipart/form-data格式的请求
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    debug(f"[{request_id}] 接收到文生音频API请求")

    try:
        # 确定请求数据来源（JSON或表单）
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        # 获取请求参数
        prompt = data.get('prompt', '').strip()
        negative_prompt = data.get('negative_prompt', '')
        sampler_name = data.get('sampler_name', None)

        # 验证输入
        if not prompt:
            warning(f"[{request_id}] 提示词为空")
            return jsonify({
                'success': False,
                'message': '请输入提示词'
            }), 400

        # 记录任务信息
        debug(f"[{request_id}] 开始处理文生音频任务 - prompt: {prompt[:50]}...")

        # 执行文生音频任务
        result = workflow_audio_manager.process_text_to_audio(
            prompt,
            negative_prompt,
            steps=data.get('steps'),
            cfg=data.get('cfg'),
            seconds=data.get('seconds'),
            batch_size=data.get('batch_size'),
            sampler_name=sampler_name
        )

        if result:
            if result.get('queued'):
                # 任务已排队
                debug(f"[{request_id}] 任务已排队: {result.get('message')}")
                return jsonify({
                    'success': True,
                    'message': result.get('message'),
                    'queued': True
                }), 200
            elif result.get('success'):
                # 任务立即完成
                debug(f"[{request_id}] 任务提交成功")
                return jsonify({
                    'success': True,
                    'message': '任务提交成功，请在"我的任务"中查看进度'
                }), 200
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查配置！')
                error(f"[{request_id}] 任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            error(f"[{request_id}] 任务处理返回空结果")
            return jsonify({
                'success': False,
                'message': '生成失败，请稍后重试'
            }), 500

    except Exception as e:
        error(f"[{request_id}] 处理文生音频请求时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理请求时发生错误: {str(e)}'
        }), 500

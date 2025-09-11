# -*- coding: utf-8 -*-
"""
文生视频路由模块
"""

from flask import Blueprint, render_template, request, flash

# 创建Blueprint
text_to_video_bp = Blueprint('text_to_video', __name__)

# 导入WorkflowManager
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.workflow.workflow_video import workflow_video_manager


@text_to_video_bp.route('/text_to_video', methods=['GET', 'POST'])
def text_to_video():
    """文生视频页面路由"""
    if request.method == 'POST':
        # 从配置工具获取有效参数，遵循页面输入 > setting节点 > default节点的优先级
        from hengline.utils.config_utils import get_effective_config
        
        # 获取表单提交的参数
        form_params = {
            'prompt': request.form.get('prompt', ''),
            'negative_prompt': request.form.get('negative_prompt', ''),
            'video_length': request.form.get('video_length'),
            'motion_amount': request.form.get('motion_amount'),
            'steps': request.form.get('steps'),
            'fps': request.form.get('fps'),
            'consistency_scale': request.form.get('consistency_scale')
        }
        
        # 过滤掉空值
        filtered_params = {k: v for k, v in form_params.items() if v not in (None, '')}
        
        # 获取最终的有效配置
        effective_config = get_effective_config('text_to_video', **filtered_params)
        
        # 从有效配置中获取参数
        prompt = effective_config.get('prompt', '')
        negative_prompt = effective_config.get('negative_prompt', '')
        video_length = effective_config.get('video_length', 16)
        motion_amount = effective_config.get('motion_amount', 0.5)
        steps = effective_config.get('steps', 30)
        fps = effective_config.get('fps', 16)
        consistency_scale = effective_config.get('consistency_scale', 1.0)

        # 验证输入
        if not prompt:
            flash('请输入提示词！', 'error')
            # 确保使用正确的参数变量名
            return render_template('text_to_video.html', default_params=display_params)

        # 视频长度（秒）
        duration = video_length

        # 执行文生视频任务
        result = workflow_video_manager.process_text_to_video(
            prompt,
            negative_prompt,
            duration=duration,
            fps=fps
        )

        if result:
            if result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return render_template('text_to_video.html', default_params=display_params)
            elif result.get('success'):
                # 任务立即完成（这种情况在异步模式下不会发生）
                if 'output_path' in result:
                    import os
                    result_filename = os.path.basename(result['output_path'])
                    flash('任务提交成功，已生成结果', 'success')
                    return render_template('text_to_video.html', default_params=default_params)
                else:
                    flash('任务提交成功，请在"我的任务"中查看进度', 'success')
                    return render_template('text_to_video.html', default_params=display_params)
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                flash(error_message, 'error')
                return render_template('text_to_video.html', default_params=display_params)
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return render_template('text_to_video.html', default_params=display_params)

    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
    from hengline.utils.config_utils import get_workflow_preset
    display_params = get_workflow_preset('text_to_video', 'setting')
    if not display_params:  # 如果setting节点为空，则使用default节点
        display_params = get_workflow_preset('text_to_video', 'default')
    
    return render_template('text_to_video.html', default_params=display_params)

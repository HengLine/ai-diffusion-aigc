# -*- coding: utf-8 -*-
"""
文生视频路由模块
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash

# 创建Blueprint
text_to_video_bp = Blueprint('text_to_video', __name__)

# 导入WorkflowManager和配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils.workflow_utils import workflow_manager, config

@text_to_video_bp.route('/text_to_video', methods=['GET', 'POST'])
def text_to_video():
    """文生视频页面路由"""
    if request.method == 'POST':
        # 从配置文件获取默认参数
        default_params = config['settings']['text_to_video']
        
        prompt = request.form.get('prompt', '')
        video_length = int(request.form.get('video_length', default_params.get('video_length', 16)))
        motion_amount = float(request.form.get('motion_amount', default_params.get('motion_amount', 0.5)))
        fps = int(request.form.get('fps', default_params.get('fps', 16)))
        consistency_scale = float(request.form.get('consistency_scale', default_params.get('consistency_scale', 1.0)))
        
        # 验证输入
        if not prompt:
            flash('请输入提示词！', 'error')
            return redirect(url_for('text_to_video.text_to_video'))
        
        # 执行文生视频任务
        result = workflow_manager.process_text_to_video(
            prompt,
            "",  # 使用空字符串作为negative_prompt
            video_length,
            fps
        )
        
        if result and result.get('success'):
            # 获取结果文件名
            import os
            result_filename = os.path.basename(result['output_path'])
            return redirect(url_for('result', filename=result_filename, task_type='text_to_video'))
        else:
            error_message = result.get('message', '生成失败，请检查ComfyUI配置！') if result else '生成失败，请检查ComfyUI配置！'
            flash(error_message, 'error')
            return redirect(url_for('text_to_video.text_to_video'))
    
    # 获取默认参数
    default_params = config['settings'].get('text_to_video', {
        'frames': 16,
        'motion_bucket_id': 127,
        'fps': 8,
        'noise_aug_strength': 0.02,
        'default_prompt': 'beautiful forest scene with a river and mountains in the background, sunlight filtering through the trees'
    })
    return render_template('text_to_video.html', default_params=default_params)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..app_flask import WorkflowManager, config

text_to_image_bp = Blueprint('text_to_image', __name__)

@text_to_image_bp.route('/text_to_image', methods=['GET', 'POST'])
def text_to_image():
    """文生图页面路由"""
    if request.method == 'POST':
        prompt = request.form.get('prompt', '')
        negative_prompt = request.form.get('negative_prompt', '')
        width = int(request.form.get('width', 1024))
        height = int(request.form.get('height', 1024))
        steps = int(request.form.get('steps', 30))
        cfg_scale = float(request.form.get('cfg_scale', 8.0))
        
        # 验证输入
        if not prompt:
            flash('请输入提示词！', 'error')
            return redirect(url_for('text_to_image.text_to_image'))
        
        # 执行文生图任务
        result_path = WorkflowManager.text_to_image(
            prompt, 
            negative_prompt,
            width,
            height,
            steps,
            cfg_scale
        )
        
        if result_path:
            # 获取结果文件名
            import os
            result_filename = os.path.basename(result_path)
            return redirect(url_for('result', filename=result_filename, task_type='text_to_image'))
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return redirect(url_for('text_to_image.text_to_image'))
    
    # 获取默认参数
    default_params = config['settings']['text_to_image']
    return render_template('text_to_image.html', default_params=default_params)
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..app_flask import WorkflowManager, config

image_to_image_bp = Blueprint('image_to_image', __name__)

@image_to_image_bp.route('/image_to_image', methods=['GET', 'POST'])
def image_to_image():
    """图生图页面路由"""
    if request.method == 'POST':
        prompt = request.form.get('prompt', '')
        negative_prompt = request.form.get('negative_prompt', '')
        strength = float(request.form.get('strength', 0.6))
        steps = int(request.form.get('steps', 30))
        cfg_scale = float(request.form.get('cfg_scale', 8.0))
        
        # 检查是否有文件上传
        if 'image' not in request.files:
            flash('请上传图像！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
        
        file = request.files['image']
        if file.filename == '':
            flash('请选择一个文件！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
        
        if not prompt:
            flash('请输入提示词！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
        
        # 保存上传的文件
        image_path = WorkflowManager.save_uploaded_file(file)
        if not image_path:
            flash('文件类型不支持！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
        
        # 执行图生图任务
        result_path = WorkflowManager.image_to_image(
            prompt, 
            negative_prompt,
            image_path,
            strength,
            steps,
            cfg_scale
        )
        
        if result_path:
            # 获取结果文件名
            import os
            result_filename = os.path.basename(result_path)
            return redirect(url_for('result', filename=result_filename, task_type='image_to_image'))
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
    
    # 获取默认参数
    default_params = config['settings']['image_to_image']
    return render_template('image_to_image.html', default_params=default_params)
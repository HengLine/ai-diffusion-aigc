from flask import Blueprint, render_template, request, redirect, url_for, flash
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils.workflow_utils import workflow_manager, config
from scripts.utils.file_utils import save_uploaded_file

# 从配置文件获取上传目录
UPLOAD_FOLDER = config['paths']['temp_folder']

image_to_image_bp = Blueprint('image_to_image', __name__)

@image_to_image_bp.route('/image_to_image', methods=['GET', 'POST'])
def image_to_image():
    """图生图页面路由"""
    if request.method == 'POST':
        # 从配置文件获取默认参数
        default_params = config['settings']['image_to_image']
        
        prompt = request.form.get('prompt', '')
        negative_prompt = request.form.get('negative_prompt', default_params.get('negative_prompt', ''))
        width = int(request.form.get('width', default_params.get('width', 512)))
        height = int(request.form.get('height', default_params.get('height', 512)))
        denoising_strength = float(request.form.get('denoising_strength', default_params.get('denoising_strength', 0.75)))
        steps = int(request.form.get('steps', default_params.get('steps', 5)))
        cfg_scale = float(request.form.get('cfg_scale', default_params.get('cfg', 3.0)))
        
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
        image_path = save_uploaded_file(file, UPLOAD_FOLDER)
        if not image_path:
            flash('文件类型不支持！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
        
        # 执行图生图任务
        result = workflow_manager.process_image_to_image(
            image_path,
            prompt,
            negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            denoising_strength=denoising_strength
        )
        
        if result:
            if result.get('success'):
                # 获取结果文件名
                import os
                result_filename = os.path.basename(result['output_path'])
                return redirect(url_for('result', filename=result_filename, task_type='image_to_image'))
            elif result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return redirect(url_for('image_to_image.image_to_image'))
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                flash(error_message, 'error')
                return redirect(url_for('image_to_image.image_to_image'))
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return redirect(url_for('image_to_image.image_to_image'))
    
    # 获取默认参数
    default_params = config['settings']['image_to_image']
    return render_template('image_to_image.html', default_params=default_params)
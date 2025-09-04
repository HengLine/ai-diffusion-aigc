from flask import Blueprint, render_template, request, redirect, url_for, flash
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils.workflow_utils import workflow_manager, config

text_to_image_bp = Blueprint('text_to_image', __name__)

@text_to_image_bp.route('/text_to_image', methods=['GET', 'POST'])
def text_to_image():
    """文生图页面路由"""
    if request.method == 'POST':
        # 从配置文件获取默认参数
        default_params = config['settings']['text_to_image']
        
        prompt = request.form.get('prompt', '')
        negative_prompt = request.form.get('negative_prompt', default_params.get('negative_prompt', ''))
        width = int(request.form.get('width', default_params.get('width', 512)))
        height = int(request.form.get('height', default_params.get('height', 512)))
        steps = int(request.form.get('steps', default_params.get('steps', 5)))
        cfg_scale = float(request.form.get('cfg_scale', default_params.get('cfg', 2.0)))
        
        # 验证输入
        if not prompt:
            flash('请输入提示词！', 'error')
            return redirect(url_for('text_to_image.text_to_image'))
        
        # 执行文生图任务
        result = workflow_manager.process_text_to_image(
            prompt, 
            negative_prompt,
            width,
            height,
            steps,
            cfg_scale
        )
        
        if result and result.get('success'):
            # 获取结果文件名
            import os
            result_filename = os.path.basename(result['output_path'])
            return redirect(url_for('result', filename=result_filename, task_type='text_to_image'))
        else:
            error_message = result.get('message', '生成失败，请检查ComfyUI配置！') if result else '生成失败，请检查ComfyUI配置！'
            flash(error_message, 'error')
            return redirect(url_for('text_to_image.text_to_image'))
    
    # 获取默认参数
    default_params = config['settings']['text_to_image']
    return render_template('text_to_image.html', default_params=default_params)
from flask import Blueprint, render_template, request, redirect, url_for, flash
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.utils.workflow_utils import workflow_manager, config
from hengline.utils.file_utils import save_uploaded_file

# 从配置文件获取上传目录
UPLOAD_FOLDER = config['paths']['temp_folder']

image_to_video_bp = Blueprint('image_to_video', __name__)

@image_to_video_bp.route('/image_to_video', methods=['GET', 'POST'])
def image_to_video():
    """图生视频页面路由"""
    if request.method == 'POST':
        # 从配置文件获取默认参数
        default_params = config['settings']['image_to_video']
        
        prompt = request.form.get('prompt', '')
        video_length = int(request.form.get('video_length', default_params.get('video_length', 16)))
        motion_amount = float(request.form.get('motion_amount', default_params.get('motion_amount', 0.5)))
        fps = int(request.form.get('fps', default_params.get('fps', 16)))
        consistency_scale = float(request.form.get('consistency_scale', default_params.get('consistency_scale', 1.0)))
        
        # 检查是否有文件上传
        if 'image' not in request.files:
            flash('请上传图像！', 'error')
            return render_template('image_to_video.html', default_params=default_params)
        
        file = request.files['image']
        if file.filename == '':
            flash('请选择一个文件！', 'error')
            return render_template('image_to_video.html', default_params=default_params)
        
        if not prompt:
            flash('请输入提示词！', 'error')
            return render_template('image_to_video.html', default_params=default_params)
        
        # 保存上传的文件
        image_path = save_uploaded_file(file, UPLOAD_FOLDER)
        if not image_path:
            flash('文件类型不支持！', 'error')
            return render_template('image_to_video.html', default_params=default_params)
        
        # 获取正确的参数
        negative_prompt = request.form.get('negative_prompt', '')
        duration = video_length  # 视频长度（秒）
        
        # 执行图生视频任务
        result = workflow_manager.process_image_to_video(
            image_path,
            prompt,
            negative_prompt,
            duration=duration,
            fps=fps
        )
        
        if result:
            if result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return render_template('image_to_video.html', default_params=default_params)
            elif result.get('success'):
                # 任务立即完成（这种情况在异步模式下不会发生）
                if 'output_path' in result:
                    import os
                    result_filename = os.path.basename(result['output_path'])
                    # 不重定向，显示成功信息
                    flash('任务提交成功，已生成结果', 'success')
                    return render_template('image_to_video.html', default_params=default_params)
                else:
                    flash('任务提交成功，请在"我的任务"中查看进度', 'success')
                    return render_template('image_to_video.html', default_params=default_params)
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                flash(error_message, 'error')
                return render_template('image_to_video.html', default_params=default_params)
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return render_template('image_to_video.html', default_params=default_params)
    
    # 获取默认参数
    default_params = config['settings']['image_to_video']
    return render_template('image_to_video.html', default_params=default_params)
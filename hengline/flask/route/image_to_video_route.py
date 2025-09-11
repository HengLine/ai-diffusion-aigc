# 导入必要的模块
import os
import sys

from flask import Blueprint, render_template, request, flash, jsonify

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.workflow.workflow_video import workflow_video_manager
from hengline.utils.file_utils import save_uploaded_file
import time
import logging

# 上传文件夹配置
from hengline.utils.config_utils import get_paths_config

UPLOAD_FOLDER = get_paths_config().get('temp_folder', 'temp')

image_to_video_bp = Blueprint('image_to_video', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('image_to_video_api')


@image_to_video_bp.route('/image_to_video', methods=['GET', 'POST'])
def image_to_video():
    """图生视频页面路由"""
    if request.method == 'POST':
        # 从配置工具获取有效参数，遵循页面输入 > setting节点 > default节点的优先级
        from hengline.utils.config_utils import get_effective_config
        
        # 获取表单提交的参数
        form_params = {
            'prompt': request.form.get('prompt', ''),
            'negative_prompt': request.form.get('negative_prompt', ''),
            'video_length': request.form.get('video_length'),
            'motion_amount': request.form.get('motion_amount'),
            'fps': request.form.get('fps'),
            'consistency_scale': request.form.get('consistency_scale')
        }
        
        # 过滤掉空值
        filtered_params = {k: v for k, v in form_params.items() if v not in (None, '')}
        
        # 获取最终的有效配置
        effective_config = get_effective_config('image_to_video', **filtered_params)
        
        # 从有效配置中获取参数
        prompt = effective_config.get('prompt', '')
        negative_prompt = effective_config.get('negative_prompt', '')
        video_length = effective_config.get('video_length', 16)
        motion_amount = effective_config.get('motion_amount', 0.5)
        fps = effective_config.get('fps', 16)
        consistency_scale = effective_config.get('consistency_scale', 1.0)

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
        result = workflow_video_manager.process_image_to_video(
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

    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
    from hengline.utils.config_utils import get_workflow_preset
    display_params = get_workflow_preset('image_to_video', 'setting')
    if not display_params:  # 如果setting节点为空，则使用default节点
        display_params = get_workflow_preset('image_to_video', 'default')
    
    return render_template('image_to_video.html', default_params=display_params)


@image_to_video_bp.route('/api/image_to_video', methods=['POST'])
def api_image_to_video():
    """
    图生视频功能的API端点
    接受multipart/form-data格式的请求，包含图像文件和参数
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    logger.info(f"[{request_id}] 接收到图生视频API请求")

    try:
        # 记录所有请求头，用于调试
        logger.debug(f"[{request_id}] 请求头: {dict(request.headers)}")

        # 检查Content-Type
        content_type = request.headers.get('Content-Type')
        if not content_type or 'multipart/form-data' not in content_type:
            logger.warning(f"[{request_id}] 不支持的Content-Type: {content_type}")
            return jsonify({
                'success': False,
                'message': '请求Content-Type必须是multipart/form-data'
            }), 415

        # 从配置工具获取默认参数
        from hengline.utils.config_utils import get_task_settings
        default_params = get_task_settings('image_to_video')

        # 获取请求参数，如果不存在则使用默认值
        prompt = request.form.get('prompt', '')
        negative_prompt = request.form.get('negative_prompt', '')
        video_length = int(request.form.get('video_length', default_params.get('video_length', 16)))
        motion_amount = float(request.form.get('motion_amount', default_params.get('motion_amount', 0.5)))
        fps = int(request.form.get('fps', default_params.get('fps', 16)))

        # 检查是否有文件上传
        if 'image' not in request.files:
            logger.warning(f"[{request_id}] 没有上传图像文件")
            return jsonify({
                'success': False,
                'message': '请上传图像！'
            }), 400

        file = request.files['image']
        if file.filename == '':
            logger.warning(f"[{request_id}] 没有选择文件")
            return jsonify({
                'success': False,
                'message': '请选择一个文件！'
            }), 400

        if not prompt:
            logger.warning(f"[{request_id}] 没有输入提示词")
            return jsonify({
                'success': False,
                'message': '请输入提示词！'
            }), 400

        # 保存上传的文件
        image_path = save_uploaded_file(file, UPLOAD_FOLDER)
        if not image_path:
            logger.warning(f"[{request_id}] 文件类型不支持")
            return jsonify({
                'success': False,
                'message': '文件类型不支持！'
            }), 400

        # 执行图生视频任务
        result = workflow_video_manager.process_image_to_video(
            image_path,
            prompt,
            negative_prompt,
            duration=video_length,
            fps=fps
        )

        if result:
            if result.get('queued'):
                # 任务已排队
                logger.info(f"[{request_id}] 任务已排队: {result.get('message')}")
                return jsonify({
                    'success': True,
                    'message': result.get('message'),
                    'queued': True
                }), 200
            elif result.get('success'):
                # 任务立即完成
                logger.info(f"[{request_id}] 任务提交成功")
                return jsonify({
                    'success': True,
                    'message': '任务提交成功，请在"我的任务"中查看进度'
                }), 200
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                logger.error(f"[{request_id}] 任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            logger.error(f"[{request_id}] 生成失败，任务处理返回None")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置！'
            }), 500

    except Exception as e:
        logger.exception(f"[{request_id}] API请求处理异常")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}'
        }), 500

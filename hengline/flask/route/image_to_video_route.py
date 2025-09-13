# 导入必要的模块
import os
import sys
import time
from flask import Blueprint, render_template, request, jsonify

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.workflow.workflow_video import workflow_video_manager
from hengline.utils.file_utils import save_uploaded_file

# 从配置工具获取页面显示的参数（setting节点优先于default节点）
from hengline.utils.config_utils import get_workflow_preset, get_paths_config
# 配置日志
from hengline.logger import warning, error, debug

image_to_video_bp = Blueprint('image_to_video', __name__)


@image_to_video_bp.route('/image_to_video', methods=['GET'])
def image_to_video():
    """图生视频页面路由"""

    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
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
    debug(f"[{request_id}] 接收到图生视频API请求")

    try:
        # 检查Content-Type
        content_type = request.headers.get('Content-Type')
        if not content_type or 'multipart/form-data' not in content_type:
            warning(f"[{request_id}] 不支持的Content-Type: {content_type}")
            return jsonify({
                'success': False,
                'message': '请求Content-Type必须是multipart/form-data'
            }), 415

        # 获取请求参数，如果不存在则使用默认值
        prompt = request.form.get('prompt', '')

        # 检查是否有文件上传
        if 'image' not in request.files:
            warning(f"[{request_id}] 没有上传图像文件")
            return jsonify({
                'success': False,
                'message': '请上传图像！'
            }), 400

        file = request.files['image']
        if file.filename == '':
            warning(f"[{request_id}] 没有选择文件")
            return jsonify({
                'success': False,
                'message': '请选择一个文件！'
            }), 400

        if not prompt:
            warning(f"[{request_id}] 没有输入提示词")
            return jsonify({
                'success': False,
                'message': '请输入提示词！'
            }), 400

        # 保存上传的文件
        image_path = save_uploaded_file(file, get_paths_config().get('temp_folder', 'temp')
                                        )
        if not image_path:
            warning(f"[{request_id}] 文件类型不支持")
            return jsonify({
                'success': False,
                'message': '文件类型不支持！'
            }), 400

        # 执行图生视频任务
        result = workflow_video_manager.process_image_to_video(
            image_path,
            prompt,
            request.form.get('negative_prompt', ''),
            length=request.form.get('length'),
            width=request.form.get('width'),
            height=request.form.get('height'),
            steps=request.form.get('steps'),
            cfg=request.form.get('cfg'),
            batch_size=request.form.get('batch_size')
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
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                error(f"[{request_id}] 任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            error(f"[{request_id}] 生成失败，任务处理返回None")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置！'
            }), 500

    except Exception as e:
        error(f"[{request_id}] API请求处理异常")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}'
        }), 500

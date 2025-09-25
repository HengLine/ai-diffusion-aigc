import sys
import time
import os

from flask import Blueprint, render_template, request, jsonify

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.workflow.workflow_other import workflow_other_manager
from hengline.utils.file_utils import save_uploaded_file
# 从配置工具获取页面显示的参数（setting节点优先于default节点）
from hengline.utils.config_utils import get_workflow_preset, get_paths_config
# 配置日志
from hengline.logger import warning, error, debug

change_face_bp = Blueprint('change_face', __name__)


@change_face_bp.route('/change_face', methods=['GET'])
def change_face():
    """换脸页面路由"""
    default_params = get_workflow_preset('change_face', 'setting')
    if not default_params:  # 如果setting节点为空，则使用default节点
        default_params = get_workflow_preset('change_face', 'default')

    return render_template('change_face.html', default_params=default_params)


@change_face_bp.route('/api/change_face', methods=['POST'])
def api_change_face():
    """
    换脸功能的API端点
    接受multipart/form-data格式的请求，包含图像文件和参数
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    debug(f"[{request_id}] 接收到换脸API请求")

    try:
        # 检查Content-Type
        content_type = request.headers.get('Content-Type')
        if not content_type or 'multipart/form-data' not in content_type:
            warning(f"[{request_id}] 不支持的Content-Type: {content_type}")
            return jsonify({
                'success': False,
                'message': '请求Content-Type必须是multipart/form-data'
            }), 415

        prompt = request.form.get('prompt', '').strip()

        # 验证输入
        if not prompt:
            warning(f"[{request_id}] 提示词为空")
            return jsonify({
                'success': False,
                'message': '请输入提示词'
            }), 400

        # 检查是否有目标图像文件上传
        if 'target_image' not in request.files:
            warning(f"[{request_id}] 未上传目标图像文件")
            return jsonify({
                'success': False,
                'message': '请上传目标图像'
            }), 400

        # 检查是否有源图像文件上传
        if 'source_image' not in request.files:
            warning(f"[{request_id}] 未上传源图像文件")
            return jsonify({
                'success': False,
                'message': '请上传源图像'
            }), 400

        target_file = request.files['target_image']
        source_file = request.files['source_image']
        
        if target_file.filename == '':
            warning(f"[{request_id}] 未选择目标文件")
            return jsonify({
                'success': False,
                'message': '请选择一个目标文件'
            }), 400
        
        if source_file.filename == '':
            warning(f"[{request_id}] 未选择源文件")
            return jsonify({
                'success': False,
                'message': '请选择一个源文件'
            }), 400

        # 保存上传的文件
        target_image_path = save_uploaded_file(target_file, get_paths_config().get('temp_folder', 'temp'))
        if not target_image_path:
            warning(f"[{request_id}] 目标文件类型不支持")
            return jsonify({
                'success': False,
                'message': '目标文件类型不支持'
            }), 400

        source_image_path = save_uploaded_file(source_file, get_paths_config().get('temp_folder', 'temp'))
        if not source_image_path:
            warning(f"[{request_id}] 源文件类型不支持")
            return jsonify({
                'success': False,
                'message': '源文件类型不支持'
            }), 400

        # 记录任务信息
        debug(f"[{request_id}] 开始处理换脸任务 - prompt: {prompt[:50]}..., target_image: {target_file.filename}, source_image: {source_file.filename}")

        # 获取人脸融合强度参数
        face_strength = request.form.get('face_strength', '0.7')
        try:
            face_strength = float(face_strength)
            # 确保参数在合理范围内
            face_strength = max(0.0, min(1.0, face_strength))
        except ValueError:
            face_strength = 0.7

        # 执行换脸任务
        result = workflow_other_manager.process_change_face(
            target_image_path,
            prompt,
            request.form.get('negative_prompt'),
            source_image_path=source_image_path,
            face_strength=face_strength,
            width=request.form.get('width'),
            height=request.form.get('height'),
            steps=request.form.get('steps'),
            cfg=request.form.get('cfg'),
            denoise=request.form.get('denoise'),
            batch_size=request.form.get('batch_size'),
            sampler_name=request.form.get('sampler_name')
        )

        if result:
            if result.get('queued'):
                # 任务已排队，返回排队信息
                queue_position = result.get('queue_position', 0)
                debug(f"[{request_id}] 换脸任务已排队 - 队列位置: {queue_position}")
                return jsonify({
                    'success': True,  # 任务成功提交到队列
                    'queued': True,
                    'message': result.get('message', f'任务已加入队列，位置: {queue_position}'),
                    'data': {
                        'task_id': result.get('task_id', request_id),
                        'queue_position': queue_position,
                        'waiting_time': result.get('waiting_time', 0)
                    }
                }), 202
            elif result.get('success'):
                # 任务立即完成（这种情况在异步模式下不会发生）
                if 'output_path' in result:
                    result_filename = os.path.basename(result['output_path'])
                    debug(f"[{request_id}] 换脸任务处理成功 - 文件名: {result_filename}")
                    return jsonify({
                        'success': True,
                        'message': '换脸任务处理成功',
                        'data': {
                            'filename': result_filename,
                            'output_path': result['output_path'],
                            'task_id': request_id
                        }
                    }), 200
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置')
                error(f"[{request_id}] 换脸任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            error(f"[{request_id}] 换脸任务执行失败: 未知错误")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置'
            }), 500
    except Exception as e:
        error(f"[{request_id}] 换脸API请求处理异常: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'API请求处理异常: {str(e)}'
        }), 500
"""
@FileName: change_hair_style_route.py
@Description: 换发型功能路由模块，提供发型更换相关的Web接口
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
import sys
import time
import os

from flask import Blueprint, render_template, request, jsonify

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.workflow.workflow_other import workflow_other_manager
from utils.file_utils import save_uploaded_file
# 从配置工具获取页面显示的参数（setting节点优先于default节点）
from utils.config_utils import get_workflow_preset, get_paths_config
# 配置日志
from hengline.logger import warning, error, debug

change_hair_style_bp = Blueprint('change_hair_style', __name__)


@change_hair_style_bp.route('/change_hair_style', methods=['GET'])
def change_hair_style():
    """换发型页面路由"""
    default_params = get_workflow_preset('change_hair_style', 'setting')
    if not default_params:  # 如果setting节点为空，则使用default节点
        default_params = get_workflow_preset('change_hair_style', 'default')

    return render_template('change_hair_style.html', default_params=default_params)


@change_hair_style_bp.route('/api/change_hair_style', methods=['POST'])
def api_change_hair_style():
    """
    换发型功能的API端点
    接受multipart/form-data格式的请求，包含图像文件和参数
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    debug(f"[{request_id}] 接收到换发型API请求")

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

        # 检查是否有图像文件上传
        if 'image' not in request.files:
            warning(f"[{request_id}] 未上传图像文件")
            return jsonify({
                'success': False,
                'message': '请上传图像'
            }), 400

        image_file = request.files['image']
        
        if image_file.filename == '':
            warning(f"[{request_id}] 未选择文件")
            return jsonify({
                'success': False,
                'message': '请选择一个文件'
            }), 400

        # 保存上传的文件
        image_path = save_uploaded_file(image_file, get_paths_config().get('temp_folder', 'temp'))
        if not image_path:
            warning(f"[{request_id}] 文件类型不支持")
            return jsonify({
                'success': False,
                'message': '文件类型不支持'
            }), 400

        # 记录任务信息
        debug(f"[{request_id}] 开始处理换发型任务 - prompt: {prompt[:50]}..., image: {image_file.filename}")

        # 获取换发型相关参数
        hair_prompt = request.form.get('hair_prompt', '')
        if not hair_prompt:
            # 如果没有单独的发型提示词，使用主提示词
            hair_prompt = prompt

        strength = request.form.get('strength', '0.6')
        try:
            strength = float(strength)
            # 确保参数在合理范围内
            strength = max(0.0, min(1.0, strength))
        except ValueError:
            strength = 0.6

        # 执行换发型任务
        result = workflow_other_manager.process_change_hair_style(
            image_path,
            prompt,
            request.form.get('negative_prompt'),
            hair_prompt=hair_prompt,
            strength=strength,
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
                debug(f"[{request_id}] 换发型任务已排队 - 队列位置: {queue_position}")
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
                    debug(f"[{request_id}] 换发型任务处理成功 - 文件名: {result_filename}")
                    return jsonify({
                        'success': True,
                        'message': '换发型任务处理成功',
                        'data': {
                            'filename': result_filename,
                            'output_path': result['output_path'],
                            'task_id': request_id
                        }
                    }), 200
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置')
                error(f"[{request_id}] 换发型任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            error(f"[{request_id}] 换发型任务执行失败: 未知错误")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置'
            }), 500
    except Exception as e:
        error(f"[{request_id}] 换发型API请求处理异常: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'API请求处理异常: {str(e)}'
        }), 500
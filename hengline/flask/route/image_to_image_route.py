import sys
import os
import time
import logging
from flask import Blueprint, render_template, request, jsonify, flash
import logging
import os
import sys
import time

from flask import Blueprint, render_template, request, jsonify, flash

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.workflow.workflow_image import workflow_image_manager
from hengline.utils.file_utils import save_uploaded_file

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('image_to_image_api')

# 从配置工具获取上传目录
from hengline.utils.config_utils import get_paths_config
UPLOAD_FOLDER = get_paths_config().get('temp_folder', 'temp')

image_to_image_bp = Blueprint('image_to_image', __name__)

@image_to_image_bp.route('/image_to_image', methods=['GET', 'POST'])
def image_to_image():
    """图生图页面路由"""
    if request.method == 'POST':
        # 从配置工具获取有效参数，遵循页面输入 > setting节点 > default节点的优先级
        from hengline.utils.config_utils import get_effective_config
        
        # 获取表单提交的参数
        form_params = {
            'prompt': request.form.get('prompt', ''),
            'negative_prompt': request.form.get('negative_prompt', ''),
            'width': request.form.get('width'),
            'height': request.form.get('height'),
            'strength': request.form.get('strength'),
            'steps': request.form.get('steps'),
            'cfg': request.form.get('cfg_scale')
        }
        
        # 过滤掉空值
        filtered_params = {k: v for k, v in form_params.items() if v not in (None, '')}
        
        # 获取最终的有效配置
        effective_config = get_effective_config('image_to_image', **filtered_params)
        
        # 从有效配置中获取参数
        prompt = effective_config.get('prompt', '')
        negative_prompt = effective_config.get('negative_prompt', '')
        width = effective_config.get('width', 512)
        height = effective_config.get('height', 512)
        denoising_strength = effective_config.get('denoising_strength', 0.6)  # 注意配置文件中是denoising_strength
        steps = effective_config.get('steps', 30)
        cfg_scale = effective_config.get('cfg', 8.0)
        
        # 检查是否有文件上传
        if 'image' not in request.files:
            flash('请上传图像！', 'error')
            return render_template('image_to_image.html', default_params=default_params)
        
        file = request.files['image']
        if file.filename == '':
            flash('请选择一个文件！', 'error')
            return render_template('image_to_image.html', default_params=default_params)
        
        if not prompt:
            flash('请输入提示词！', 'error')
            return render_template('image_to_image.html', default_params=default_params)
        
        # 保存上传的文件
        image_path = save_uploaded_file(file, UPLOAD_FOLDER)
        if not image_path:
            flash('文件类型不支持！', 'error')
            return render_template('image_to_image.html', default_params=default_params)
        
        # 执行图生图任务
        result = workflow_image_manager.process_image_to_image(
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
            if result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return render_template('image_to_image.html', default_params=default_params)
            elif result.get('success'):
                # 任务立即完成（这种情况在异步模式下不会发生）
                if 'output_path' in result:
                    import os
                    result_filename = os.path.basename(result['output_path'])
                    # 不重定向，显示成功信息
                    flash('任务提交成功，已生成结果', 'success')
                    return render_template('image_to_image.html', default_params=default_params)
                else:
                    flash('任务提交成功，请在"我的任务"中查看进度', 'success')
                    return render_template('image_to_image.html', default_params=default_params)
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                flash(error_message, 'error')
                return render_template('image_to_image.html', default_params=default_params)
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return render_template('image_to_image.html', default_params=default_params)
    
    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
    from hengline.utils.config_utils import get_workflow_preset
    display_params = get_workflow_preset('image_to_image', 'setting')
    if not display_params:  # 如果setting节点为空，则使用default节点
        display_params = get_workflow_preset('image_to_image', 'default')
    
    # 将denoising_strength重命名为strength，以匹配前端表单
    if 'denoising_strength' in display_params:
        display_params['strength'] = display_params['denoising_strength']
    
    return render_template('image_to_image.html', default_params=display_params)

@image_to_image_bp.route('/api/image_to_image', methods=['POST'])
def api_image_to_image():
    """
    图生图功能的API端点
    接受multipart/form-data格式的请求，包含图像文件和参数
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    logger.debug(f"[{request_id}] 接收到图生图API请求")
    
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
        default_params = get_task_settings('image_to_image')
        
        # 获取请求参数，如果不存在则使用默认值
        prompt = request.form.get('prompt', '')
        negative_prompt = request.form.get('negative_prompt', default_params.get('negative_prompt', ''))
        width = int(request.form.get('width', default_params.get('width', 512)))
        height = int(request.form.get('height', default_params.get('height', 512)))
        denoising_strength = float(request.form.get('strength', default_params.get('strength', 0.6)))
        steps = int(request.form.get('steps', default_params.get('steps', 30)))
        cfg_scale = float(request.form.get('cfg_scale', default_params.get('cfg', 8.0)))
        
        # 验证输入
        if not prompt:
            logger.warning(f"[{request_id}] 提示词为空")
            return jsonify({
                'success': False,
                'message': '请输入提示词'
            }), 400
        
        # 检查是否有文件上传
        if 'image' not in request.files:
            logger.warning(f"[{request_id}] 未上传图像文件")
            return jsonify({
                'success': False,
                'message': '请上传图像'
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            logger.warning(f"[{request_id}] 未选择文件")
            return jsonify({
                'success': False,
                'message': '请选择一个文件'
            }), 400
        
        # 从配置工具获取上传目录
        from hengline.utils.config_utils import get_paths_config
        UPLOAD_FOLDER = get_paths_config().get('temp_folder', 'temp')
        
        # 保存上传的文件
        image_path = save_uploaded_file(file, UPLOAD_FOLDER)
        if not image_path:
            logger.warning(f"[{request_id}] 文件类型不支持")
            return jsonify({
                'success': False,
                'message': '文件类型不支持'
            }), 400
        
        # 记录任务信息
        logger.debug(f"[{request_id}] 开始处理图生图任务 - prompt: {prompt[:50]}..., image: {file.filename}")
        
        # 执行图生图任务
        result = workflow_image_manager.process_image_to_image(
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
            if result.get('queued'):
                # 任务已排队，返回排队信息
                queue_position = result.get('queue_position', 0)
                logger.debug(f"[{request_id}] 图生图任务已排队 - 队列位置: {queue_position}")
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
                    logger.debug(f"[{request_id}] 图生图任务处理成功 - 文件名: {result_filename}")
                    return jsonify({
                        'success': True,
                        'message': '图生图任务处理成功',
                        'data': {
                            'filename': result_filename,
                            'output_path': result['output_path'],
                            'task_id': request_id
                        }
                    }), 200
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置')
                logger.error(f"[{request_id}] 图生图任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            logger.error(f"[{request_id}] 图生图任务执行失败: 未知错误")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置'
            }), 500
    except Exception as e:
        logger.error(f"[{request_id}] 图生图API请求处理异常: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'API请求处理异常: {str(e)}'
        }), 500
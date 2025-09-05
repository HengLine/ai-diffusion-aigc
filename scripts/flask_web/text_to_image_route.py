# 导入必要的模块
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import sys
import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流管理器和配置
from scripts.utils.workflow_utils import workflow_manager, config

# 创建蓝图
text_to_image_bp = Blueprint('text_to_image', __name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('text_to_image_api')

# 创建线程池执行器，用于异步处理长时间运行的任务
executor = ThreadPoolExecutor(max_workers=2)

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
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale
        )
        
        if result:
            if result.get('success'):
                # 获取结果文件名
                result_filename = os.path.basename(result['output_path'])
                return redirect(url_for('result', filename=result_filename, task_type='text_to_image'))
            elif result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return redirect(url_for('text_to_image.text_to_image'))
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                flash(error_message, 'error')
                return redirect(url_for('text_to_image.text_to_image'))
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return redirect(url_for('text_to_image.text_to_image'))
    
    # 获取默认参数
    default_params = config['settings']['text_to_image']
    return render_template('text_to_image.html', default_params=default_params)

@text_to_image_bp.route('/api/text_to_image', methods=['POST'])
def api_text_to_image():
    """
    文生图功能的API端点
    接受JSON格式的请求参数，返回JSON格式的响应
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    logger.info(f"[{request_id}] 接收到文生图API请求")
    
    try:
        # 记录所有请求头，用于调试
        logger.debug(f"[{request_id}] 请求头: {dict(request.headers)}")
        
        # 检查Content-Type - 宽松检查，允许包含额外参数如charset
        content_type = request.headers.get('Content-Type')
        if not content_type or not content_type.startswith('application/json'):
            logger.warning(f"[{request_id}] 不支持的Content-Type: {content_type}")
            return jsonify({
                'success': False,
                'message': '请求Content-Type必须是application/json'
            }), 415
        
        # 从请求体中获取JSON数据
        logger.info(f"[{request_id}] 尝试获取JSON数据")
        # 添加异常处理，以便更好地诊断JSON解析问题
        try:
            data = request.get_json()
            logger.info(f"[{request_id}] JSON数据获取成功")
        except Exception as e:
            logger.error(f"[{request_id}] JSON数据解析失败: {str(e)}")
            # 尝试直接读取原始请求体，用于调试
            try:
                raw_data = request.get_data().decode('utf-8')
                logger.info(f"[{request_id}] 原始请求体: {raw_data[:200]}...")  # 只记录前200个字符
            except Exception as e2:
                logger.error(f"[{request_id}] 无法读取原始请求体: {str(e2)}")
            return jsonify({
                'success': False,
                'message': f'JSON数据解析失败: {str(e)}'
            }), 400
        
        if not data:
            logger.warning(f"[{request_id}] 请求体不包含JSON数据")
            return jsonify({
                'success': False,
                'message': '请求体必须包含JSON数据'
            }), 400
        
        logger.info(f"[{request_id}] 接收到的请求数据: {data}")
        
        # 从配置文件获取默认参数
        default_params = config['settings']['text_to_image']
        
        # 获取请求参数，如果不存在则使用默认值
        prompt = data.get('prompt', '')
        negative_prompt = data.get('negative_prompt', default_params.get('negative_prompt', ''))
        width = int(data.get('width', default_params.get('width', 512)))
        height = int(data.get('height', default_params.get('height', 512)))
        steps = int(data.get('steps', default_params.get('steps', 5)))
        cfg_scale = float(data.get('cfg_scale', default_params.get('cfg', 2.0)))
        
        # 验证输入
        if not prompt:
            logger.warning(f"[{request_id}] 提示词为空")
            return jsonify({
                'success': False,
                'message': '请输入提示词'
            }), 400
        
        # 记录任务信息
        logger.info(f"[{request_id}] 开始处理文生图任务 - prompt: {prompt[:50]}..., size: {width}x{height}")
        
        # 执行文生图任务，设置任务ID
        result = workflow_manager.process_text_to_image(
            prompt,
            negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale
        )
        
        if result:
            if result.get('success'):
                # 获取结果文件名
                result_filename = os.path.basename(result['output_path'])
                logger.info(f"[{request_id}] 文生图任务处理成功 - 文件名: {result_filename}")
                return jsonify({
                    'success': True,
                    'message': '文生图任务处理成功',
                    'data': {
                        'filename': result_filename,
                        'output_path': result['output_path'],
                        'task_id': request_id
                    }
                }), 200
            elif result.get('queued'):
                # 任务已排队，返回排队信息
                queue_position = result.get('queue_position', 0)
                logger.info(f"[{request_id}] 文生图任务已排队 - 队列位置: {queue_position}")
                return jsonify({
                    'success': False,
                    'queued': True,
                    'message': result.get('message', f'任务已加入队列，位置: {queue_position}'),
                    'data': {
                        'task_id': result.get('task_id', request_id),
                        'queue_position': queue_position,
                        'waiting_time': result.get('waiting_time', 0)
                    }
                }), 202
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置')
                logger.error(f"[{request_id}] 文生图任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            logger.error(f"[{request_id}] 文生图任务处理返回空结果")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置'
            }), 500
    except Exception as e:
        logger.exception(f"[{request_id}] 处理请求时发生异常")
        return jsonify({
            'success': False,
            'message': f'处理请求时发生错误: {str(e)}'
        }), 500
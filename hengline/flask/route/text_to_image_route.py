# 导入必要的模块
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, render_template, request, flash, jsonify

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流管理器
from hengline.workflow.workflow_image import workflow_image_manager

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
        # 从配置工具获取有效参数，遵循页面输入 > setting节点 > default节点的优先级
        from hengline.utils.config_utils import get_effective_config
        
        # 获取表单提交的参数
        form_params = {
            'prompt': request.form.get('prompt', ''),
            'negative_prompt': request.form.get('negative_prompt', ''),
            'width': request.form.get('width'),
            'height': request.form.get('height'),
            'steps': request.form.get('steps'),
            'cfg': request.form.get('cfg_scale')
        }
        
        # 过滤掉空值
        filtered_params = {k: v for k, v in form_params.items() if v not in (None, '')}
        
        # 获取最终的有效配置
        effective_config = get_effective_config('text_to_image', **filtered_params)
        
        # 从有效配置中获取参数
        prompt = effective_config.get('prompt', '')
        negative_prompt = effective_config.get('negative_prompt', '')
        width = effective_config.get('width', 512)
        height = effective_config.get('height', 512)
        steps = effective_config.get('steps', 5)
        cfg_scale = effective_config.get('cfg', 2.0)

        # 验证输入
        if not prompt:
            flash('请输入提示词！', 'error')
            return render_template('text_to_image.html', default_params=default_params)

        # 执行文生图任务
        result = workflow_image_manager.process_text_to_image(
            prompt,
            negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale
        )

        if result:
            if result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return render_template('text_to_image.html', default_params=default_params)
            elif result.get('success'):
                # 任务立即完成（这种情况在异步模式下不会发生）
                if 'output_path' in result:
                    result_filename = os.path.basename(result['output_path'])
                    # 不重定向，显示成功信息
                    flash('任务提交成功，已生成结果', 'success')
                    return render_template('text_to_image.html', default_params=default_params)
                else:
                    flash('任务提交成功，请在"我的任务"中查看进度', 'success')
                    return render_template('text_to_image.html', default_params=default_params)
            else:
                # 任务执行失败
                error_message = result.get('message', '生成失败，请检查ComfyUI配置！')
                flash(error_message, 'error')
                return render_template('text_to_image.html', default_params=default_params)
        else:
            flash('生成失败，请检查ComfyUI配置！', 'error')
            return render_template('text_to_image.html', default_params=default_params)

    # 从配置工具获取页面显示的参数（setting节点优先于default节点）
    from hengline.utils.config_utils import get_workflow_preset
    display_params = get_workflow_preset('text_to_image', 'setting')
    if not display_params:  # 如果setting节点为空，则使用default节点
        display_params = get_workflow_preset('text_to_image', 'default')
    
    return render_template('text_to_image.html', default_params=display_params)


@text_to_image_bp.route('/api/text_to_image', methods=['POST'])
def api_text_to_image():
    """
    文生图功能的API端点
    接受JSON格式的请求参数，返回JSON格式的响应
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    logger.debug(f"[{request_id}] 接收到文生图API请求")

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
        logger.debug(f"[{request_id}] 尝试获取JSON数据")
        # 添加异常处理，以便更好地诊断JSON解析问题
        try:
            data = request.get_json()
            logger.debug(f"[{request_id}] JSON数据获取成功")
        except Exception as e:
            logger.error(f"[{request_id}] JSON数据解析失败: {str(e)}")
            # 尝试直接读取原始请求体，用于调试
            try:
                raw_data = request.get_data().decode('utf-8')
                logger.debug(f"[{request_id}] 原始请求体: {raw_data[:200]}...")  # 只记录前200个字符
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

        logger.debug(f"[{request_id}] 接收到的请求数据: {data}")

        # 从配置工具获取默认参数
        from hengline.utils.config_utils import get_task_settings
        default_params = get_task_settings('text_to_image')

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
        logger.debug(f"[{request_id}] 开始处理文生图任务 - prompt: {prompt[:50]}..., size: {width}x{height}")

        # 执行文生图任务，设置任务ID
        result = workflow_image_manager.process_text_to_image(
            prompt,
            negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale
        )

        if result:
            if result.get('queued'):
                # 任务已排队，返回排队信息
                queue_position = result.get('queue_position', 0)
                logger.debug(f"[{request_id}] 文生图任务已排队 - 队列位置: {queue_position}")
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
                    logger.debug(f"[{request_id}] 文生图任务处理成功 - 文件名: {result_filename}")
                    return jsonify({
                        'success': True,
                        'message': '文生图任务处理成功',
                        'data': {
                            'filename': result_filename,
                            'output_path': result['output_path'],
                            'task_id': request_id
                        }
                    }), 200
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

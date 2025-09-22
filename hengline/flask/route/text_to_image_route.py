# 导入必要的模块
import os
import sys
import time

from flask import Blueprint, render_template, request, jsonify

from hengline.utils.log_utils import print_log_exception

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.logger import warning, error, debug
# 导入工作流管理器
from hengline.workflow.workflow_image import workflow_image_manager
# 从配置工具获取页面显示的参数（setting节点优先于default节点）
from hengline.utils.config_utils import get_workflow_preset

# 创建蓝图
text_to_image_bp = Blueprint('text_to_image', __name__)


@text_to_image_bp.route('/text_to_image', methods=['GET'])
def text_to_image():
    default_params = get_workflow_preset('text_to_image', 'setting')
    if not default_params:  # 如果setting节点为空，则使用default节点
        default_params = get_workflow_preset('text_to_image', 'default')

    return render_template('text_to_image.html', default_params=default_params)


@text_to_image_bp.route('/api/text_to_image', methods=['POST'])
def api_text_to_image():
    """
    文生图功能的API端点
    接受JSON格式的请求参数，返回JSON格式的响应
    """
    request_id = f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

    try:
        # 检查Content-Type - 宽松检查，允许包含额外参数如charset
        content_type = request.headers.get('Content-Type')
        if not content_type or not content_type.startswith('application/json'):
            warning(f"[{request_id}] 不支持的Content-Type: {content_type}")
            return jsonify({
                'success': False,
                'message': '请求Content-Type必须是application/json'
            }), 415

        # 添加异常处理，以便更好地诊断JSON解析问题
        try:
            data = request.get_json()
        except Exception as e:
            error(f"[{request_id}] JSON数据解析失败: {str(e)}")
            print_log_exception()
            # 尝试直接读取原始请求体，用于调试
            try:
                raw_data = request.get_data().decode('utf-8')
                debug(f"[{request_id}] 原始请求体: {raw_data[:200]}...")  # 只记录前200个字符
            except Exception as e2:
                error(f"[{request_id}] 无法读取原始请求体: {str(e2)}")
            return jsonify({
                'success': False,
                'message': f'JSON数据解析失败: {str(e)}'
            }), 400

        if not data:
            warning(f"[{request_id}] 请求体不包含JSON数据")
            return jsonify({
                'success': False,
                'message': '请求体必须包含JSON数据'
            }), 400

        debug(f"[{request_id}] 接收到的请求数据: {data}")

        # 获取请求参数，如果不存在则使用默认值
        prompt = data.get('prompt', '')

        # 验证输入
        if not prompt:
            warning(f"[{request_id}] 提示词为空")
            return jsonify({
                'success': False,
                'message': '请输入提示词'
            }), 400

        # 记录任务信息
        debug(f"[{request_id}] 开始处理文生图任务 - prompt: {prompt[:50]}...")

        # 获取请求参数，如果不存在则使用默认值
        negative_prompt = data.get('negative_prompt', '')
        width = data.get('width', 1024)
        height = data.get('height', 512)
        steps = data.get('steps', 20)
        cfg = data.get('cfg', 7.5)
        batch_size = data.get('batch_size', 5)
        denoise = data.get('denoise', 0.75)

        # 执行文生图任务，设置任务ID
        result = workflow_image_manager.process_text_to_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            batch_size=batch_size,
            denoise=denoise
        )

        if result:
            if result.get('queued'):
                # 任务已排队，返回排队信息
                queue_position = result.get('queue_position', 0)
                debug(f"[{request_id}] 文生图任务已排队 - 队列位置: {queue_position}")
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
                    debug(f"[{request_id}] 文生图任务处理成功 - 文件名: {result_filename}")
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
                error(f"[{request_id}] 文生图任务执行失败: {error_message}")
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
        else:
            error(f"[{request_id}] 文生图任务处理返回空结果")
            return jsonify({
                'success': False,
                'message': '生成失败，请检查ComfyUI配置'
            }), 500
    except Exception as e:
        error(f"[{request_id}] 处理请求时发生异常")
        print_log_exception()
        return jsonify({
            'success': False,
            'message': f'处理请求时发生错误: {str(e)}'
        }), 500

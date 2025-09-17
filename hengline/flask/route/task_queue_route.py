from flask import Blueprint, jsonify, url_for, request

from hengline.common import get_name_by_type
from hengline.logger import debug
from hengline.task.task_manage import task_queue_manager
from hengline.task.task_queue import TaskStatus

# 创建任务队列管理的蓝图
task_queue_bp = Blueprint('task_queue', __name__)


@task_queue_bp.route('/api/task_queue/status', methods=['GET'])
def get_task_queue_status():
    """
    获取任务队列状态的API端点
    返回当前正在执行的任务数、排队任务数以及平均任务执行时间
    同时包含当天未完成任务的统计结果
    支持按任务类型过滤
    """
    try:
        debug(f"获取任务队列状态")
        # 获取任务类型参数
        task_type = request.args.get('task_type')

        # 获取队列状态，传入任务类型参数
        queue_status = task_queue_manager.get_queue_status(task_type=task_type)

        # 获取日期参数，如果没有提供则使用今天
        date = request.args.get('date')
        if not date:
            # 如果没有提供日期，使用今天的日期
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')

        # 获取所有任务
        all_tasks = task_queue_manager.get_all_tasks(date=date)

        # 过滤未完成任务（状态为queued或running）
        unfinished_tasks = [task for task in all_tasks if not TaskStatus.is_success(task['status'])]

        # 如果提供了任务类型参数，则进一步过滤
        if task_type and task_type != 'all':
            unfinished_tasks = [task for task in unfinished_tasks if task['task_type'] == task_type]

        # 将未完成任务数添加到队列状态数据中
        queue_status['unfinished_tasks_count'] = len(unfinished_tasks)

        # 返回队列状态信息
        return jsonify({
            'success': True,
            'data': queue_status
        }), 200
    except Exception as e:
        # 处理异常并返回错误信息
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@task_queue_bp.route('/api/task_queue/all_tasks', methods=['GET'])
# @auto_serialize
def get_all_tasks():
    """
    获取所有任务历史记录的API端点
    返回所有已提交任务的列表，包括状态和基本信息
    支持按日期、状态和类型筛选任务
    """
    try:
        # 获取日期参数
        date = request.args.get('date')
        # 获取状态参数
        status = request.args.get('status')
        # 获取任务类型参数
        task_type = request.args.get('task_type')

        # 获取任务列表（可能按日期筛选）
        all_tasks = task_queue_manager.get_all_tasks(date=date)

        # 如果提供了状态参数且不是'all'，则根据状态过滤任务
        if status and status != 'all':
            all_tasks = [task for task in all_tasks if task['status'] == status]

        # 如果提供了任务类型参数且不是'all'，则根据任务类型过滤任务
        if task_type and task_type != 'all':
            all_tasks = [task for task in all_tasks if task['task_type'] == task_type]

        # 返回任务列表
        return jsonify({
            'success': True,
            'data': all_tasks
        }), 200
    except Exception as e:
        # 处理异常并返回错误信息
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@task_queue_bp.route('/api/task_queue/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取指定任务状态的API端点
    """
    try:
        debug(f"获取任务详情: {task_id}")
        # 获取任务状态
        task_status = task_queue_manager.get_task_status(task_id)

        if task_status:
            return jsonify({
                'success': True,
                'data': task_status
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
    except Exception as e:
        # 处理异常并返回错误信息
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@task_queue_bp.route('/api/task_queue/result/<task_id>', methods=['GET'])
def get_task_result(task_id):
    """
    获取指定任务结果的API端点
    """
    try:
        # 获取任务状态
        task_status = task_queue_manager.get_task_status(task_id)

        if not task_status:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404

        # 从task_history中获取原始任务对象，以获取完整的参数信息
        task = task_queue_manager.get_history_task(task_id)
        prompt = task.params.get("prompt", "") if task and task.params else ""
        negative_prompt = task.params.get("negative_prompt", "") if task and task.params else ""

        # 构建结果URL列表
        result_filenames = []

        # 优先使用多个输出文件（如果有）
        if task and hasattr(task, 'output_filenames') and task.output_filenames:
            result_filenames = task.output_filenames
        elif task and hasattr(task, 'output_filename') and task.output_filename:
            # 向后兼容：如果只有单个输出文件
            result_filenames = task.output_filename

        # 构建完整的结果URL列表
        result_urls = [url_for('serve_output', filename=filename, _external=True) for filename in result_filenames]

        # 返回完整的任务结果数据
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_status['task_id'],
                'task_type': get_name_by_type(task_status['task_type']),
                'status': task_status['status'],
                'timestamp': task_status['timestamp'],
                'start_time': task_status.get('start_time'),
                'end_time': task_status.get('end_time'),
                'duration': task_status.get('duration'),
                'queue_position': task_status.get('queue_position'),
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'filename': result_filenames[0] if result_filenames else None,  # 向后兼容
                'filenames': result_filenames,
                'result_url': result_urls[0] if result_urls else None,  # 向后兼容
                'result_urls': result_urls,  # 返回URL列表，支持多个输出文件
                'total_results': len(result_urls)  # 添加结果总数字段
            }
        }), 200
    except Exception as e:
        # 处理异常并返回错误信息
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

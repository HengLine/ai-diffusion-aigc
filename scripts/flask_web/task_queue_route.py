from flask import Blueprint, jsonify, url_for, request
from scripts.utils.task_queue_utils import task_queue_manager

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
        unfinished_tasks = [task for task in all_tasks if task['status'] in ['queued', 'running']]
        
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
        with task_queue_manager.lock:
            task = task_queue_manager.task_history.get(task_id)
            prompt = task.params.get("prompt", "") if task and task.params else ""
            negative_prompt = task.params.get("negative_prompt", "") if task and task.params else ""
        
        # 使用实际的输出文件名
        result_filename = None
        if task and hasattr(task, 'output_filename'):
            result_filename = task.output_filename
            
        # 如果没有保存输出文件名，尝试使用旧的命名方式
        if not result_filename:
            # 根据任务类型确定扩展名
            extensions = {
                'text_to_image': 'png',
                'image_to_image': 'png',
                'text_to_video': 'mp4',
                'image_to_video': 'mp4'
            }
            
            extension = extensions.get(task_status['task_type'], 'png')
            result_filename = f"{task_status['task_id']}.{extension}"
        
        # 构建完整的结果URL
        result_url = url_for('serve_output', filename=result_filename, _external=True)
        
        # 返回完整的任务结果数据
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_status['task_id'],
                'task_type': task_status['task_type'],
                'status': task_status['status'],
                'timestamp': task_status['timestamp'],
                'start_time': task_status.get('start_time'),
                'end_time': task_status.get('end_time'),
                'duration': task_status.get('duration'),
                'queue_position': task_status.get('queue_position'),
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'filename': result_filename,
                'result_url': result_url,  # 返回完整的URL路径
                'task_type': task_status['task_type']
            }
        }), 200
    except Exception as e:
        # 处理异常并返回错误信息
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
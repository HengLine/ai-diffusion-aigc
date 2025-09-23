# -*- coding: utf-8 -*-
"""
WebSocket路由模块，用于实时推送任务状态更新
"""

from flask import Blueprint, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from threading import Lock
from hengline.logger import debug, info, error

# 延迟导入task_monitor，避免循环依赖
import hengline.task.task_monitor

# 创建蓝图
socketio_bp = Blueprint('socketio', __name__)

# 全局SocketIO实例和线程锁
socketio = None
thread_lock = Lock()

def init_socketio(app):
    """
    初始化SocketIO
    
    Args:
        app: Flask应用实例
    """
    global socketio
    with thread_lock:
        if socketio is None:
            # 使用eventlet作为异步引擎，添加优化配置以提高连接稳定性
            socketio = SocketIO(app, 
                               cors_allowed_origins="*", 
                               async_mode='eventlet',
                               ping_timeout=60,  # 增加ping超时时间（秒）
                               ping_interval=25,  # 增加ping间隔时间（秒）
                               max_http_buffer_size=10 * 1024 * 1024,  # 增加HTTP请求缓冲区大小到10MB
                               logger=True,  # 启用日志记录
                               engineio_logger=False)  # 禁用底层engineio日志
            # 注册事件处理器
            register_socketio_handlers()
            info("SocketIO初始化成功")
    return socketio

def register_socketio_handlers():
    """
    注册SocketIO事件处理器
    """
    @socketio.on('connect')
    def handle_connect():
        """处理客户端连接"""
        debug(f"客户端连接: {request.sid}")
        emit('connection_established', {'message': '连接成功'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """处理客户端断开连接"""
        debug(f"客户端断开连接: {request.sid}")
    
    @socketio.on('join_task_room')
    def handle_join_task_room(data):
        """处理客户端加入任务房间的请求"""
        task_id = data.get('task_id')
        if task_id:
            join_room(task_id)
            debug(f"客户端 {request.sid} 加入任务房间: {task_id}")
            emit('room_joined', {'task_id': task_id, 'message': f'已加入任务房间: {task_id}'})
    
    @socketio.on('leave_task_room')
    def handle_leave_task_room(data):
        """处理客户端离开任务房间的请求"""
        task_id = data.get('task_id')
        if task_id:
            leave_room(task_id)
            debug(f"客户端 {request.sid} 离开任务房间: {task_id}")
            emit('room_left', {'task_id': task_id, 'message': f'已离开任务房间: {task_id}'})
    
    @socketio.on('request_task_status')
    def handle_request_task_status(data):
        """处理客户端请求任务状态的请求"""
        task_id = data.get('task_id')
        if task_id:
            try:
                # 获取任务状态
                task_status = hengline.task.task_monitor.task_monitor.get_task_status(task_id)
                if task_status:
                    emit('task_status_update', {
                        'success': True,
                        'task_id': task_id,
                        'status': task_status
                    })
                else:
                    emit('task_status_update', {
                        'success': False,
                        'task_id': task_id,
                        'message': '任务不存在'
                    })
            except Exception as e:
                error(f"获取任务状态失败: {str(e)}")
                emit('task_status_update', {
                    'success': False,
                    'task_id': task_id,
                    'message': f'获取任务状态失败: {str(e)}'
                })

def emit_task_status_update(task_id, status_data):
    """
    向特定任务房间广播任务状态更新
    
    Args:
        task_id: 任务ID
        status_data: 任务状态数据
    """
    global socketio
    if socketio:
        try:
            debug(f"向任务房间 {task_id} 广播状态更新: {status_data}")
            socketio.emit('task_status_update', {
                'success': True,
                'task_id': task_id,
                'status': status_data
            }, room=task_id)
        except ConnectionAbortedError:
            # 专门捕获连接中断错误，避免程序崩溃
            debug(f"客户端连接已中断，无法发送状态更新到任务房间 {task_id}")
        except Exception as e:
            error(f"广播任务状态更新失败: {str(e)}")

def emit_queue_status_update():
    """
    向所有连接的客户端广播队列状态更新
    自动调用task_monitor获取最新队列状态
    """
    global socketio
    if socketio:
        try:
            # 获取最新队列状态
            queue_data = hengline.task.task_monitor.task_monitor.get_queue_status()
            debug(f"广播队列状态更新: {queue_data}")
            socketio.emit('queue_status_update', {
                'success': True,
                'data': queue_data
            })
        except ConnectionAbortedError:
            # 专门捕获连接中断错误，避免程序崩溃
            debug("检测到客户端连接中断，无法广播队列状态更新")
        except Exception as e:
            error(f"广播队列状态更新失败: {str(e)}")
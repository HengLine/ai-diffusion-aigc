#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Flask + Jinja2构建的AIGC Web界面
"""

import datetime
import os
import signal
import sys
import threading
import time

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入工作流运行器
# 导入自定义日志模块
from hengline.logger import info
# 导入配置工具模块
from hengline.utils.config_utils import (
    get_flask_secret_key,
    get_temp_folder,
    get_output_folder,
    get_allowed_extensions
)

# 导入拆分后的路由模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from route.text_to_image_route import text_to_image_bp
from route.image_to_image_route import image_to_image_bp
from route.image_to_video_route import image_to_video_bp
from route.text_to_video_route import text_to_video_bp
from route.task_queue_route import task_queue_bp
from route.flask_config_route import config_bp

# 初始化Flask应用
app = Flask(__name__, template_folder='templates')

# 从配置工具获取Flask配置
app.secret_key = get_flask_secret_key()
# 不再从配置文件读取debug设置，直接在app.run()中设置
# app.debug = get_flask_debug()

# 获取项目根目录（而不是henglin目录）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 使用配置工具获取路径配置
UPLOAD_FOLDER = os.path.join(project_root, get_temp_folder())
OUTPUT_FOLDER = os.path.join(project_root, get_output_folder())
TEMP_FOLDER = os.path.join(project_root, 'temp')  # 使用固定的临时目录

# 全局变量存储任务队列管理器
from hengline.core.task_queue import task_queue_manager

# from hengline.core.task_monitor import task_monitor
# 导入启动任务监听器
from hengline.core.task_init import startup_task_listener

# 确保目录存在
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 使用配置工具获取允许上传的文件类型
ALLOWED_EXTENSIONS = get_allowed_extensions()

# 全局变量存储运行器实例
runner = None
server_process = None

# 注意：file_utils相关函数已在其他地方导入，避免重复导入

# 注册拆分后的Blueprint
app.register_blueprint(config_bp)
app.register_blueprint(text_to_image_bp)
app.register_blueprint(image_to_image_bp)
app.register_blueprint(image_to_video_bp)
app.register_blueprint(text_to_video_bp)
app.register_blueprint(task_queue_bp)


# 路由定义
@app.route('/')
def index():
    """首页路由"""
    # 从配置工具获取完整配置传递给模板
    from hengline.utils.config_utils import get_config
    return render_template('index.html', config=get_config())


# 注意：文生图、图生图和图生视频的路由处理已拆分到flask_web目录下的单独文件中
# 请参考text_to_image_route.py, image_to_image_route.py和image_to_video_route.py文件

@app.route('/result')
def result():
    """结果展示页面路由"""
    filename = request.args.get('filename', '')
    task_type = request.args.get('task_type', 'text_to_image')

    if not filename:
        flash('没有找到结果文件！', 'error')
        return redirect(url_for('index'))

    # 检查文件是否存在
    result_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(result_path):
        flash('结果文件不存在！', 'error')
        return redirect(url_for('index'))

    # 根据文件类型判断是图像还是视频
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    is_video = file_ext in ['mp4', 'webm', 'ogg']

    # 获取当前时间
    current_time = datetime.datetime.now()

    return render_template('result.html',
                           filename=filename,
                           task_type=task_type,
                           is_video=is_video,
                           current_time=current_time)


@app.route('/outputs/<filename>')
def serve_output(filename):
    """提供输出文件的路由"""
    return send_from_directory(OUTPUT_FOLDER, filename)


def handle_shutdown(signum, frame):
    """处理终止信号的回调函数"""
    info("接收到终止信号，正在异步关闭任务队列管理器...")

    # 停止任务监控器
    # task_monitor.stop()

    # 异步调用shutdown方法
    shutdown_thread = threading.Thread(target=task_queue_manager.shutdown)
    shutdown_thread.daemon = True
    shutdown_thread.start()

    # 等待一段时间让异步关闭有时间完成
    time.sleep(2)

    # 停止ComfyUI服务器
    global runner, server_process
    if server_process and runner:
        runner.stop_comfyui_server(server_process)
        server_process = None
        runner = None

    info("服务正在关闭...")

    # 在信号处理上下文中，我们不应该尝试通过request.environ获取shutdown函数
    # 因为此时没有活跃的HTTP请求上下文，直接退出程序
    sys.exit(0)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """关闭服务器的路由"""
    # 停止ComfyUI服务器
    global runner, server_process
    if server_process and runner:
        runner.stop_comfyui_server(server_process)
        server_process = None
        runner = None

    # 异步调用shutdown方法
    shutdown_thread = threading.Thread(target=task_queue_manager.shutdown)
    shutdown_thread.daemon = True
    shutdown_thread.start()

    # 关闭Flask服务器
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'


if __name__ == '__main__':
    # 注册信号处理函数
    if sys.platform != 'win32':  # Windows系统不支持SIGTERM和SIGINT
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
    else:
        # Windows系统的信号处理
        try:
            # 尝试使用win32api注册信号处理（如果安装了pywin32）
            import win32api


            def win_handler(event):
                handle_shutdown(None, None)
                return True


            win32api.SetConsoleCtrlHandler(win_handler, True)
        except ImportError:
            # 如果没有安装pywin32，使用简单的信号处理方式
            signal.signal(signal.SIGINT, handle_shutdown)

    # 异步启动任务监听器，处理历史未完成任务
    startup_task_thread = threading.Thread(target=startup_task_listener.start, name="StartupTaskListenerThread")
    startup_task_thread.daemon = True
    startup_task_thread.start()

    # 启动任务监控器
    # task_monitor.start()

    # 启动Flask应用 - 开启debug模式以便获取详细错误信息
    app.run(debug=True, host='0.0.0.0', port=5000)

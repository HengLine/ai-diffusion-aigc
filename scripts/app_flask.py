#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Flask + Jinja2构建的AIGC Web界面
"""

import os
import sys
import json
import uuid
import time
import shutil
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流运行器
from scripts.run_workflow import ComfyUIRunner
# 导入自定义日志模块
from scripts.utils.logger import info, error, warning
# 导入工作流工具模块
from scripts.utils.workflow_utils import workflow_manager, config

# 导入拆分后的路由模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask_web.text_to_image_route import text_to_image_bp
from flask_web.image_to_image_route import image_to_image_bp
from flask_web.image_to_video_route import image_to_video_bp
from flask_web.text_to_video_route import text_to_video_bp
from flask_web.task_queue_route import task_queue_bp
from flask_web.flask_config_route import config_bp

# 初始化Flask应用
app = Flask(__name__, template_folder='flask_templates')

# 从配置文件读取Flask配置
app.secret_key = config.get('flask', {}).get('secret_key', 'default-fallback-key')
app.debug = config.get('flask', {}).get('debug', False)

# 从配置文件读取路径配置
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(project_root, config.get('paths', {}).get('temp_folder', 'uploads'))
OUTPUT_FOLDER = os.path.join(project_root, config.get('paths', {}).get('output_folder', 'outputs'))
TEMP_FOLDER = os.path.join(project_root, 'temp')  # 使用固定的临时目录

# 确保目录存在
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 从配置文件读取允许上传的文件类型
allowed_extensions_list = config.get('flask', {}).get('allowed_extensions', ['png', 'jpg', 'jpeg', 'gif'])
ALLOWED_EXTENSIONS = set(allowed_extensions_list)

# 全局变量存储ComfyUI路径和运行器实例
comfyui_path = config['comfyui']['path']
runner = None
server_process = None

# 初始化全局WorkflowManager实例
workflow_manager.comfyui_path = comfyui_path
workflow_manager.output_dir = OUTPUT_FOLDER

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
    return render_template('index.html', config=config)



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

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """关闭服务器的路由"""
    # 停止ComfyUI服务器
    global runner, server_process
    if server_process and runner:
        runner.stop_comfyui_server(server_process)
        server_process = None
        runner = None
    
    # 关闭Flask服务器
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    # 启动Flask应用
    app.run(debug=True, host='0.0.0.0', port=5000)
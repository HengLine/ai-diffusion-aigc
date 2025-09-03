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

# 导入拆分后的路由模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from flask_web.text_to_image_route import text_to_image_bp
from flask_web.image_to_image_route import image_to_image_bp
from flask_web.image_to_video_route import image_to_video_bp
from flask_web.text_to_video_route import text_to_video_bp

# 初始化Flask应用
app = Flask(__name__, template_folder='templates')
app.secret_key = 'supersecretkey'

# 配置文件上传
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
TEMP_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')

# 确保目录存在
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 加载配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configs', 'config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 全局变量存储ComfyUI路径和运行器实例
comfyui_path = config['comfyui']['path']
runner = None
server_process = None

class WorkflowManager:
    """工作流管理器类，用于处理各种AI生成任务"""
    
    @staticmethod
    def init_runner():
        """初始化工作流运行器"""
        global runner, server_process, comfyui_path
        
        if not runner and comfyui_path:
            runner = ComfyUIRunner(comfyui_path, OUTPUT_FOLDER)
            
            # 启动ComfyUI服务器
            try:
                server_process = runner.start_comfyui_server()
            except Exception as e:
                print(f"启动ComfyUI服务器失败: {str(e)}")
                runner = None
                return False
        return True
    
    @staticmethod
    def stop_runner():
        """停止工作流运行器"""
        global runner, server_process
        
        if server_process:
            runner.stop_comfyui_server(server_process)
            server_process = None
        runner = None
    
    @staticmethod
    def allowed_file(filename):
        """检查文件类型是否允许上传"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_uploaded_file(file):
        """保存上传的文件并返回路径"""
        if file and WorkflowManager.allowed_file(file.filename):
            # 生成唯一文件名以避免覆盖
            unique_id = str(uuid.uuid4())[:8]
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{unique_id}_{int(time.time())}.{file_ext}"
            
            # 保存文件
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            return file_path
        return None
    
    @staticmethod
    def text_to_image(prompt, negative_prompt, output_filename=None):
        """执行文生图任务"""
        if not WorkflowManager.init_runner():
            return None
        
        try:
            # 生成唯一的输出文件名
            if not output_filename:
                output_filename = f"text_to_image_{int(time.time())}.png"
            
            # 加载工作流 - 使用基础文生图工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        "workflows", "text_to_image.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                print(f"工作流文件不存在: {workflow_path}")
                return None
            
            # 加载和更新工作流
            workflow = runner.load_workflow(workflow_path)
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt
            }
            updated_workflow = runner.update_workflow_params(workflow, params)
            
            # 运行工作流
            success = runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                return os.path.join(OUTPUT_FOLDER, output_filename)
            return None
        except Exception as e:
            print(f"文生图任务执行失败: {str(e)}")
            return None
    
    @staticmethod
    def image_to_image(prompt, negative_prompt, image_path, output_filename=None):
        """执行图生图任务"""
        if not WorkflowManager.init_runner():
            return None
        
        try:
            # 生成唯一的输出文件名
            if not output_filename:
                output_filename = f"image_to_image_{int(time.time())}.png"
            
            # 加载图生图工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        "workflows", "image_to_image_basic.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                print(f"工作流文件不存在: {workflow_path}")
                return None
            
            # 加载和更新工作流
            workflow = runner.load_workflow(workflow_path)
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "image_path": image_path
            }
            updated_workflow = runner.update_workflow_params(workflow, params)
            
            # 运行工作流
            success = runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                return os.path.join(OUTPUT_FOLDER, output_filename)
            return None
        except Exception as e:
            print(f"图生图任务执行失败: {str(e)}")
            return None
    
    @staticmethod
    def image_to_video(prompt, image_path, output_filename=None):
        """执行图生视频任务"""
        if not WorkflowManager.init_runner():
            return None
        
        try:
            # 生成唯一的输出文件名
            if not output_filename:
                output_filename = f"image_to_video_{int(time.time())}.mp4"
            
            # 加载图生视频工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        "workflows", "image_to_video_basic.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                print(f"工作流文件不存在: {workflow_path}")
                return None
            
            # 加载和更新工作流
            workflow = runner.load_workflow(workflow_path)
            params = {
                "prompt": prompt,
                "image_path": image_path
            }
            updated_workflow = runner.update_workflow_params(workflow, params)
            
            # 运行工作流
            success = runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                return os.path.join(OUTPUT_FOLDER, output_filename)
            return None
        except Exception as e:
            print(f"图生视频任务执行失败: {str(e)}")
            return None
    
    @staticmethod
    def text_to_video(prompt, output_filename=None):
        """执行文生视频任务"""
        if not WorkflowManager.init_runner():
            return None
        
        try:
            # 生成唯一的输出文件名
            if not output_filename:
                output_filename = f"text_to_video_{int(time.time())}.mp4"
            
            # 加载文生视频工作流
            workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        "workflows", "text_to_video.json")
            
            # 检查工作流文件是否存在
            if not os.path.exists(workflow_path):
                print(f"工作流文件不存在: {workflow_path}")
                return None
            
            # 加载和更新工作流
            workflow = runner.load_workflow(workflow_path)
            params = {
                "prompt": prompt
            }
            updated_workflow = runner.update_workflow_params(workflow, params)
            
            # 运行工作流
            success = runner.run_workflow(updated_workflow, output_filename)
            
            if success:
                return os.path.join(OUTPUT_FOLDER, output_filename)
            return None
        except Exception as e:
            print(f"文生视频任务执行失败: {str(e)}")
            return None

# 注册拆分后的Blueprint
app.register_blueprint(text_to_image_bp)
app.register_blueprint(image_to_image_bp)
app.register_blueprint(image_to_video_bp)
app.register_blueprint(text_to_video_bp)

# 路由定义
@app.route('/')
def index():
    """首页路由"""
    return render_template('index.html', config=config)

@app.route('/config', methods=['GET', 'POST'])
def configure():
    """配置页面路由"""
    global comfyui_path, config
    
    if request.method == 'POST':
        new_comfyui_path = request.form.get('comfyui_path', '')
        
        if new_comfyui_path:
            # 更新全局变量
            comfyui_path = new_comfyui_path
            
            # 更新配置文件
            config['comfyui']['path'] = new_comfyui_path
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 重新初始化运行器
            WorkflowManager.stop_runner()
            
            flash('配置已保存成功！')
        else:
            flash('请输入有效的ComfyUI路径！', 'error')
        
        return redirect(url_for('configure'))
    
    return render_template('config.html', comfyui_path=comfyui_path)

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
    WorkflowManager.stop_runner()
    
    # 关闭Flask服务器
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    # 启动Flask应用
    app.run(debug=True, host='0.0.0.0', port=5000)
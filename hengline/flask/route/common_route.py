"""
Flask路由公共组件模块
封装四个AIGC功能模块的共用路由逻辑
"""

from flask import Blueprint, render_template, request, jsonify, flash
import sys
import os
import time
import logging
from werkzeug.utils import secure_filename

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流管理器和配置
from hengline.utils.workflow_utils import workflow_manager, config
from hengline.utils.file_utils import save_uploaded_file

class BaseRoute:
    """基础路由类，封装共用的路由功能"""
    
    def __init__(self, blueprint_name, template_name, config_key, api_endpoint=None):
        """
        初始化基础路由类
        
        :param blueprint_name: Blueprint名称
        :param template_name: HTML模板名称
        :param config_key: 配置文件中的键名
        :param api_endpoint: API端点路径，如果为None则不创建API路由
        """
        self.blueprint_name = blueprint_name
        self.template_name = template_name
        self.config_key = config_key
        self.api_endpoint = api_endpoint
        
        # 创建Blueprint
        self.bp = Blueprint(blueprint_name, __name__)
        
        # 配置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(f'{blueprint_name}_api')
        
        # 注册页面路由
        self.bp.route(f'/{blueprint_name}', methods=['GET', 'POST'])(self.page_route)
        
        # 注册API路由（如果提供了端点）
        if api_endpoint:
            self.bp.route(api_endpoint, methods=['POST'])(self.api_route)
    
    def page_route(self):
        """页面路由处理函数，需要子类实现具体的参数获取和任务调用逻辑"""
        raise NotImplementedError("子类必须实现page_route方法")
    
    def api_route(self):
        """API路由处理函数，需要子类实现具体的参数获取和任务调用逻辑"""
        raise NotImplementedError("子类必须实现api_route方法")
    
    def get_default_params(self):
        """获取默认参数"""
        return config['settings'].get(self.config_key, {})
    
    def handle_task_result(self, result, success_message=None, error_message=None):
        """
        处理任务执行结果
        
        :param result: 任务执行结果
        :param success_message: 成功消息
        :param error_message: 错误消息
        :return: Flask响应对象
        """
        if result:
            if result.get('queued'):
                # 任务已排队，显示排队信息
                flash(result.get('message'), 'info')
                return render_template(self.template_name, default_params=self.get_default_params())
            elif result.get('success'):
                # 任务立即完成
                if 'output_path' in result:
                    result_filename = os.path.basename(result['output_path'])
                    # 显示成功信息
                    flash(success_message or '任务提交成功，已生成结果', 'success')
                    return render_template(self.template_name, default_params=self.get_default_params())
                else:
                    flash(success_message or '任务提交成功，请在"我的任务"中查看进度', 'success')
                    return render_template(self.template_name, default_params=self.get_default_params())
            else:
                # 任务执行失败
                msg = result.get('message', error_message or '生成失败，请检查ComfyUI配置！')
                flash(msg, 'error')
                return render_template(self.template_name, default_params=self.get_default_params())
        else:
            flash(error_message or '生成失败，请检查ComfyUI配置！', 'error')
            return render_template(self.template_name, default_params=self.get_default_params())
    
    def create_api_response(self, request_id, success, message, data=None, status_code=200, queued=False):
        """
        创建API响应
        
        :param request_id: 请求ID
        :param success: 是否成功
        :param message: 消息
        :param data: 附加数据
        :param status_code: HTTP状态码
        :param queued: 是否已排队
        :return: JSON响应
        """
        response = {
            'success': success,
            'message': message
        }
        
        if data:
            response['data'] = data
        
        if queued:
            response['queued'] = True
        
        return jsonify(response), status_code
    
    def generate_request_id(self):
        """生成请求ID"""
        return f"{time.strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    
    def save_uploaded_file_safe(self, file):
        """
        安全保存上传的文件
        
        :param file: 上传的文件对象
        :return: 文件保存路径或None（如果保存失败）
        """
        # 从配置文件获取上传目录
        upload_folder = config['paths']['temp_folder']
        return save_uploaded_file(file, upload_folder)

# 工具函数
def create_common_response(success, message, data=None, status_code=200):
    """
    创建通用的JSON响应
    
    :param success: 是否成功
    :param message: 消息
    :param data: 附加数据
    :param status_code: HTTP状态码
    :return: JSON响应
    """
    response = {
        'success': success,
        'message': message
    }
    
    if data:
        response['data'] = data
    
    return jsonify(response), status_code

# 表单验证装饰器
def validate_form_params(*required_params):
    """
    验证表单参数的装饰器
    
    :param required_params: 必需的参数列表
    :return: 装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            missing_params = [param for param in required_params if not request.form.get(param)]
            if missing_params:
                flash(f'请输入{"、".join(missing_params)}！', 'error')
                return render_template(func.__globals__.get('template_name', 'index.html'), 
                                      default_params=func.__globals__.get('get_default_params', lambda: {}))
            return func(*args, **kwargs)
        return wrapper
    return decorator
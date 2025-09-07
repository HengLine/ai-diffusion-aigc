# -*- coding: utf-8 -*-
"""
邮件发送工具模块
提供邮件发送功能，支持主题、邮箱地址、昵称和信息字段
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Dict, Optional
from datetime import datetime

from .logger import info, error, warning

class EmailSender:
    """邮件发送类，提供发送邮件的功能"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None, 
                 username: str = None, password: str = None, 
                 from_email: str = None, from_name: str = None):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP服务器端口
            username: SMTP用户名
            password: SMTP密码
            from_email: 发件人邮箱
            from_name: 发件人名称
        """
        # 优先从传入参数获取配置，如果没有则从环境变量获取，最后使用默认值
        self.smtp_server = smtp_server or os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.environ.get('SMTP_PORT', '587'))
        self.username = username or os.environ.get('SMTP_USERNAME', '')
        self.password = password or os.environ.get('SMTP_PASSWORD', '')
        self.from_email = from_email or os.environ.get('FROM_EMAIL', '')
        self.from_name = from_name or os.environ.get('FROM_NAME', 'AIGC Demo')
        
        # 连接状态
        self.server = None
        
    def connect(self) -> bool:
        """
        连接到SMTP服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建SMTP连接
            self.server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.server.starttls()  # 启用TLS加密
            
            # 如果提供了用户名和密码，则登录
            if self.username and self.password:
                self.server.login(self.username, self.password)
                
            info(f"成功连接到SMTP服务器: {self.smtp_server}")
            return True
        except Exception as e:
            error(f"连接SMTP服务器失败: {str(e)}")
            self.server = None
            return False
    
    def disconnect(self) -> None:
        """\断开与SMTP服务器的连接"""
        if self.server:
            try:
                self.server.quit()
                info("已断开与SMTP服务器的连接")
            except Exception as e:
                warning(f"断开SMTP连接时出错: {str(e)}")
            finally:
                self.server = None
    
    def send_email(self, to_email: str, subject: str, message: str, 
                   to_name: str = '', is_html: bool = False) -> bool:
        """
        发送邮件
        
        Args:
            to_email: 收件人邮箱地址
            subject: 邮件主题
            message: 邮件内容
            to_name: 收件人名称
            is_html: 邮件内容是否为HTML格式
            
        Returns:
            bool: 邮件是否发送成功
        """
        if not to_email:
            error("收件人邮箱地址不能为空")
            return False
        
        if not subject:
            error("邮件主题不能为空")
            return False
        
        # 如果未连接，则尝试连接
        if not self.server:
            if not self.connect():
                return False
        
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            
            # 设置发件人和收件人
            from_addr = f'{Header(self.from_name, "utf-8")} <{self.from_email}>' if self.from_name else self.from_email
            to_addr = f'{Header(to_name, "utf-8")} <{to_email}>' if to_name else to_email
            
            msg['From'] = from_addr
            msg['To'] = to_addr
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 设置邮件内容
            if is_html:
                msg.attach(MIMEText(message, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # 发送邮件
            self.server.send_message(msg)
            info(f"成功发送邮件到: {to_email}, 主题: {subject}")
            return True
        except Exception as e:
            error(f"发送邮件失败: {str(e)}")
            # 发送失败时，尝试重新连接
            self.disconnect()
            return False
    
    def __enter__(self):
        """支持上下文管理器模式"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器时断开连接"""
        self.disconnect()

# 创建全局的邮件发送器实例
email_sender = None
# 全局配置对象
_global_config = None

# 从配置文件加载配置
def _load_config_from_file():
    """从配置文件加载配置"""
    global _global_config
    
    try:
        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'configs', 'config.json')
        
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            _global_config = json.load(f)
            return True
    except Exception as e:
        error(f"加载配置文件失败: {str(e)}")
        _global_config = {}
        return False

# 获取用户配置信息
def _get_user_config():
    """获取用户配置信息"""
    if not _global_config:
        _load_config_from_file()
    
    return _global_config.get('user', {})

# 获取邮件配置信息
def _get_email_config():
    """获取邮件配置信息"""
    if not _global_config:
        _load_config_from_file()
    
    return _global_config.get('email', {})


def init_email_sender(config: Optional[Dict] = None) -> None:
    """
    初始化全局邮件发送器
    
    Args:
        config: 邮件配置字典，如果为None则从配置文件加载
    """
    global email_sender
    
    # 如果没有提供配置，则从配置文件加载
    if config is None:
        config = _get_email_config()
    
    if config:
        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port')
        username = config.get('username')
        password = config.get('password')
        from_email = config.get('from_email')
        from_name = config.get('from_name')
        
        email_sender = EmailSender(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            username=username,
            password=password,
            from_email=from_email,
            from_name=from_name
        )
    else:
        email_sender = EmailSender()

# 提供简单的发送接口，符合用户需求
def send_email(subject: str, to_email: str = None, to_name: str = None, message: str = None) -> bool:
    """
    发送邮件的简单接口
    
    Args:
        subject: 邮件主题
        to_email: 收件人邮箱地址，如果为None则使用配置中的用户邮箱
        to_name: 收件人昵称，如果为None则使用配置中的用户昵称
        message: 邮件内容
        
    Returns:
        bool: 邮件是否发送成功
    """
    global email_sender
    
    # 获取用户配置信息
    user_config = _get_user_config()
    
    # 如果未提供收件人信息，则使用配置中的用户信息
    if to_email is None:
        to_email = user_config.get('email', '')
    if to_name is None:
        to_name = user_config.get('nickname', '')
    if message is None:
        message = f"这是一封来自AIGC Demo项目的邮件\n主题: {subject}"
    
    # 验证必要信息
    if not to_email:
        error("收件人邮箱地址不能为空")
        return False
    if not subject:
        error("邮件主题不能为空")
        return False
    
    # 如果全局邮件发送器未初始化，则初始化
    if not email_sender:
        init_email_sender()
    
    return email_sender.send_email(
        to_email=to_email,
        subject=subject,
        message=message,
        to_name=to_name
    )
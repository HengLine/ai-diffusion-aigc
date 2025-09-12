# -*- coding: utf-8 -*-
"""
邮件发送工具模块
提供邮件发送功能，支持主题、邮箱地址、昵称和信息字段
"""

import os
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

from hengline.logger import info, error, warning
from hengline.utils.config_utils import get_email_config, get_user_configs
from hengline.utils.env_utils import get_env_var

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
        # 优先从传入参数获取配置，如果没有则从环境变量获取
        self.smtp_server = smtp_server or get_env_var('SMTP_SERVER', '')
        self.smtp_port = smtp_port or (int(get_env_var('SMTP_PORT', '')) if get_env_var('SMTP_PORT', '') else None)
        self.username = username or get_env_var('SMTP_USERNAME', '')
        self.password = password or get_env_var('SMTP_PASSWORD', '')
        self.from_email = from_email or get_env_var('FROM_EMAIL', '')

        # 然后从配置文件获取（非敏感信息）
        email_config = get_email_config()

        if not self.smtp_server:
            self.smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        if not self.smtp_port:
            self.smtp_port = int(email_config.get('smtp_port', '587'))
        if not self.from_email:
            self.from_email = email_config.get('from_email', '')
        if not self.from_name:
            self.from_name = email_config.get('from_name', 'AIGC 创意平台')
        if not self.username and self.from_email:
            # 如果没有单独设置用户名，使用发件人邮箱作为用户名
            self.username = self.from_email

        # 验证配置
        if not all([self.smtp_server, self.username, self.password, self.from_email]):
            error("SMTP配置不完整，无法初始化EmailSender")
            return

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

            debug(f"成功连接到SMTP服务器: {self.smtp_server}")
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
                debug("已断开与SMTP服务器的连接")
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
            debug(f"成功发送邮件到: {to_email}, 主题: {subject}")
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

def init_email_sender(config: Optional[Dict] = None) -> None:
    """
    初始化全局邮件发送器
    
    Args:
        config: 邮件配置字典，如果为None则从配置文件加载
    """
    global email_sender

    # 注意：这里不再从config中读取敏感信息，而是通过EmailSender类的初始化方法从环境变量获取
    email_sender = EmailSender()


# 提供简单的发送接口，符合用户需求
async def send_email(subject: str, message: str = None) -> bool:
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
    user_config = get_user_configs()

    # 如果未提供收件人信息，则使用配置中的用户信息
    to_email = user_config.get('email', '')
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

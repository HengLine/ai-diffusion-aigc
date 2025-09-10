# -*- coding: utf-8 -*-
"""
邮件发送工具测试文件
"""

import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入邮件发送工具
from hengline.utils.email_utils import EmailSender, init_email_sender, send_email
from hengline.utils.logger import info, error

# 导入配置工具
from hengline.utils.config_utils import get_config, get_email_config, get_user_config

def test_email_sender():
    """测试EmailSender类"""
    # 从配置工具获取邮件配置
    email_config = get_email_config()
    
    # 如果配置文件中没有完整的邮件配置，使用环境变量或默认值
    email_config.setdefault('smtp_server', os.environ.get('SMTP_SERVER', 'smtp.gmail.com'))
    email_config.setdefault('smtp_port', os.environ.get('SMTP_PORT', 587))
    email_config.setdefault('username', os.environ.get('SMTP_USERNAME', ''))
    email_config.setdefault('password', os.environ.get('SMTP_PASSWORD', ''))
    # 从配置工具获取用户配置
    user_config = get_user_config()
    email_config.setdefault('from_email', os.environ.get('FROM_EMAIL', user_config.get('email', '')))
    email_config.setdefault('from_name', os.environ.get('FROM_NAME', user_config.get('nickname', 'AIGC Demo')))
    
    # 测试使用EmailSender类发送邮件
    info("测试使用EmailSender类发送邮件...")
    
    # 使用上下文管理器方式
    try:
        with EmailSender(
            smtp_server=email_config['smtp_server'],
            smtp_port=email_config['smtp_port'],
            username=email_config['username'],
            password=email_config['password'],
            from_email=email_config['from_email'],
            from_name=email_config['from_name']
        ) as email_sender:
            # 如果配置不完整，只是测试连接和初始化
            if not (email_config['username'] and email_config['password']):
                info("SMTP配置不完整，无法实际发送邮件。请设置环境变量SMTP_USERNAME和SMTP_PASSWORD")
                return
            
            # 实际发送测试邮件
            test_to_email = email_config['from_email']  # 发送给自己
            test_subject = "AIGC Demo 邮件测试"
            test_message = "这是一封来自AIGC Demo项目的测试邮件。\n\n发送时间: " + os.environ.get('COMPUTERNAME', '') + " - " + os.environ.get('USERNAME', '')
            test_to_name = email_config['from_name']
            
            success = email_sender.send_email(
                to_email=test_to_email,
                subject=test_subject,
                message=test_message,
                to_name=test_to_name
            )
            
            if success:
                info(f"测试邮件已发送到: {test_to_email}")
            else:
                error("测试邮件发送失败")
    except Exception as e:
        error(f"EmailSender测试失败: {str(e)}")

def test_send_email_function():
    """测试简单的send_email函数接口"""
    # 直接使用自动从配置文件加载的功能，不需要手动传入配置
    # 邮件工具类会自动从配置文件和环境变量中获取配置
    
    # 从配置工具获取邮件配置
    email_config = get_email_config()
    
    # 可以选择不调用init_email_sender，让send_email函数自动初始化
    # 但为了确保测试的一致性，我们还是显式调用一次
    init_email_sender()  # 不传入参数，会自动从配置文件加载
    
    info("测试使用send_email函数接口发送邮件...")
    
    # 如果配置不完整，只是测试初始化
    if not (email_config['username'] and email_config['password']):
        info("SMTP配置不完整，无法实际发送邮件。请设置环境变量SMTP_USERNAME和SMTP_PASSWORD")
        return
    
    # 1. 测试使用显式参数发送邮件
    test_to_email = email_config['from_email']  # 发送给自己
    test_subject = "AIGC Demo 简单接口邮件测试 - 显式参数"
    test_message = "这是一封来自AIGC Demo项目的测试邮件，使用简单接口发送。\n\n发送时间: " + os.environ.get('COMPUTERNAME', '') + " - " + os.environ.get('USERNAME', '')
    test_to_name = email_config['from_name']
    
    success = send_email(
        subject=test_subject,
        to_email=test_to_email,
        to_name=test_to_name,
        message=test_message
    )
    
    if success:
        info(f"显式参数测试邮件已发送到: {test_to_email}")
    else:
        error("显式参数测试邮件发送失败")
        
    # 2. 测试只传入主题，使用默认收件人信息（从配置文件读取）
    if success:  # 如果上一个测试成功，才进行这个测试
        info("测试只传入主题，使用默认收件人信息...")
        
        success2 = send_email(subject="AIGC Demo 简单接口邮件测试 - 默认配置")
        
        if success2:
            info("默认配置测试邮件已发送到配置文件中的用户邮箱")
        else:
            error("默认配置测试邮件发送失败")

if __name__ == "__main__":
    info("开始邮件发送工具测试...")
    
    # 测试EmailSender类
    test_email_sender()
    
    # 测试简单的send_email函数接口
    test_send_email_function()
    
    info("邮件发送工具测试完成")
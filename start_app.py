#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AIGC创意平台启动脚本（Python版本）

这个脚本提供了完整的应用启动功能，按照以下步骤执行：
1. 创建虚拟环境及env目录
2. 安装依赖（用系统pip）
3. 激活虚拟环境
4. 启动服务（启动过程中缺少依赖就继续安装）

优化说明：
- 明确指定虚拟环境路径为当前目录下的env
- 统一使用自定义日志模块进行日志记录
- 增强错误处理和用户提示
- 优化代码结构和执行逻辑
- 确保中文显示正常
- 增加依赖检查和自动重试机制
"""

import os
import sys
import subprocess
import time

# 获取当前脚本所在目录（项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 添加项目根目录到Python路径
sys.path.append(PROJECT_ROOT)

# 导入自定义日志模块
from scripts.utils.logger import info, error, warning

# 设置编码为UTF-8以确保中文显示正常
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 全局变量 - 明确指定虚拟环境为当前目录下的env
VENV_DIR = os.path.join(PROJECT_ROOT, "env")  # 使用绝对路径确保一致性
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")
APP_FILE = os.path.join(PROJECT_ROOT, "scripts", "app.py")


def run_command(command, shell=True, capture_output=False, check=False):
    """运行系统命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        error(f"命令执行失败: {command}")
        error(f"错误码: {e.returncode}")
        error(f"错误输出: {e.stderr}")
        return e
    except Exception as e:
        error(f"执行命令时发生异常: {command}")
        error(f"异常信息: {str(e)}")
        return None


def check_python_installation():
    """检查Python是否安装"""
    info("检查Python环境...")
    result = run_command("python --version", capture_output=True)
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        info(f"[成功] Python环境检查通过: {result.stdout.strip()}")
        return True
    else:
        error("未找到Python！请确保Python已正确安装并添加到系统PATH。")
        return False


def create_virtual_environment():
    """创建Python虚拟环境（当前目录下的env）"""
    if os.path.exists(VENV_DIR):
        info(f"虚拟环境已存在于 '{VENV_DIR}'，检查有效性。")
        # 获取虚拟环境Python路径以验证虚拟环境是否有效
        if os.name == 'nt':  # Windows系统
            venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
        else:  # 非Windows系统
            venv_python = os.path.join(VENV_DIR, "bin", "python")
        
        if os.path.isfile(venv_python):
            info(f"虚拟环境有效，使用现有虚拟环境。")
            return True
        else:
            warning(f"虚拟环境无效，重新创建: {VENV_DIR}")
            import shutil
            shutil.rmtree(VENV_DIR)
    
    info(f"在当前目录下创建Python虚拟环境 '{VENV_DIR}'...")
    result = run_command(f"python -m venv {VENV_DIR}")
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        info("[成功] 虚拟环境创建成功。")
        return True
    else:
        error("虚拟环境创建失败！请检查权限和磁盘空间。")
        return False


def get_virtual_environment_paths():
    """获取虚拟环境中Python、pip和activate命令的绝对路径"""
    if os.name == 'nt':  # Windows系统
        python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")
        pip_exe = os.path.join(VENV_DIR, "Scripts", "pip.exe")
        activate_cmd = os.path.join(VENV_DIR, "Scripts", "activate")
    else:  # 非Windows系统
        python_exe = os.path.join(VENV_DIR, "bin", "python")
        pip_exe = os.path.join(VENV_DIR, "bin", "pip")
        activate_cmd = os.path.join(VENV_DIR, "bin", "activate")
    
    # 验证虚拟环境文件是否存在
    if not os.path.exists(python_exe):
        error(f"虚拟环境Python解释器不存在！路径: {python_exe}")
        return None, None, None
    
    info(f"使用虚拟环境Python: {python_exe}")
    return python_exe, pip_exe, activate_cmd


def install_dependencies():
    """使用系统pip安装项目依赖包"""
    if not os.path.exists(REQUIREMENTS_FILE):
        warning(f"依赖文件 {REQUIREMENTS_FILE} 不存在！跳过依赖安装。")
        return True
    
    info(f"使用系统pip安装项目依赖包（{REQUIREMENTS_FILE}）...")
    
    # 使用系统pip安装项目依赖
    result = run_command(f"pip install -r {REQUIREMENTS_FILE}")
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        info("[成功] 依赖安装成功。")
        return True
    else:
        warning("依赖安装过程中出现问题，但仍尝试启动应用。")
        return False


def check_dependencies_satisfied(python_exe):
    """检查依赖是否满足"""
    try:
        info("检查依赖是否满足...")
        # 尝试导入一些关键库来验证依赖是否安装正确
        test_imports = "import streamlit, requests, json, os, sys"
        result = run_command(f"{python_exe} -c \"{test_imports}\"", capture_output=True)
        
        if result and hasattr(result, 'returncode') and result.returncode != 0:
            warning(f"依赖检查失败: {result.stderr}")
            return False
        
        info("依赖检查通过")
        return True
    except Exception as e:
        error(f"检查依赖时出错: {str(e)}")
        return False


def start_application_with_retry(python_exe):
    """使用虚拟环境的Python启动AIGC演示应用，支持自动重试"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if not os.path.exists(APP_FILE):
                error(f"应用文件 {APP_FILE} 不存在！")
                return False
            
            # 检查依赖是否满足
            if not check_dependencies_satisfied(python_exe):
                info("依赖不满足，尝试重新安装...")
                
                # 使用系统pip重新安装依赖
                if not install_dependencies():
                    error("依赖重新安装失败")
                    retry_count += 1
                    if retry_count < max_retries:
                        info(f"等待2秒后重试 ({retry_count}/{max_retries})\n")
                        time.sleep(2)
                        continue
                    else:
                        return False
            
            info(f"启动AIGC演示应用（{APP_FILE}）...")
            info("====================================")
            info("应用启动中，请不要关闭此窗口...")
            info("如果需要停止应用，请按 Ctrl+C")
            info("====================================")
            
            # 使用run并设置shell=True以确保Streamlit在前台正确运行
            # result = run_command(f"{python_exe} -m streamlit run {APP_FILE}", shell=True)
            result = run_command(f"streamlit run {APP_FILE}", shell=True)
            return result is not None
        except KeyboardInterrupt:
            info("\n应用已被用户中断。")
            return True
        except Exception as e:
            error(f"应用程序启动失败！")
            error(f"异常信息: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                info(f"等待2秒后重试 ({retry_count}/{max_retries})\n")
                time.sleep(2)
            else:
                error("达到最大重试次数，启动失败")
                return False


def main():
    """主函数 - 协调整个启动流程"""
    info("====================================")
    info("     AIGC创意平台启动脚本（Python版本）     ")
    info("====================================")
    info(f"当前工作目录: {os.getcwd()}")
    info(f"项目根目录: {PROJECT_ROOT}")
    info(f"将使用的虚拟环境: {VENV_DIR}")
    
    # 步骤1: 检查Python安装
    if not check_python_installation():
        input("按Enter键退出...")
        sys.exit(1)
    
    # 步骤1: 创建虚拟环境及env目录
    if not create_virtual_environment():
        input("按Enter键退出...")
        sys.exit(1)
    
    # 步骤2: 使用系统pip安装依赖
    info("步骤2: 使用系统pip安装项目依赖")
    install_dependencies()
    
    # 步骤3: 激活虚拟环境（获取虚拟环境路径并执行activate命令）
    info("步骤3: 激活虚拟环境")
    python_exe, _, activate_cmd = get_virtual_environment_paths()
    if not python_exe:
        input("按Enter键退出...")
        sys.exit(1)
    
    # 执行activate命令以设置虚拟环境的环境变量
    if os.path.exists(activate_cmd):
        info(f"执行虚拟环境激活命令: {activate_cmd}")
        if os.name == 'nt':  # Windows系统
            # 在Windows上，activate是一个批处理文件
            activate_result = run_command(f"cmd /c {activate_cmd}", capture_output=True)
        else:  # 非Windows系统
            # 在Unix系统上，activate是一个shell脚本
            activate_result = run_command(f"source {activate_cmd}", capture_output=True)
        
        if activate_result and hasattr(activate_result, 'returncode') and activate_result.returncode == 0:
            info("[成功] 虚拟环境激活成功。")
        else:
            warning("虚拟环境激活命令执行完成，继续使用虚拟环境Python路径运行应用。")
    else:
        warning(f"未找到激活命令: {activate_cmd}，继续使用虚拟环境Python路径运行应用。")
    
    # 步骤4: 启动服务（启动过程中缺少依赖就继续安装）
    info("步骤4: 启动AIGC创意平台服务")
    start_application_with_retry(python_exe)
    
    info("====================================")
    info("应用程序已停止运行。")
    input("按Enter键退出...")


if __name__ == "__main__":
    main()
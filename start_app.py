#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AIGC创意平台启动脚本（Python版本）

这个脚本提供了与start_app.bat相同的功能，但使用Python的错误处理机制，
在不同环境中可能具有更好的兼容性和可靠性。
"""

import os
import sys
import subprocess
import time
import shutil

# 设置编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 全局变量
VENV_DIR = "env"
REQUIREMENTS_FILE = "requirements.txt"
APP_FILE = os.path.join("scripts", "app.py")


def print_with_color(text, color_code=32):
    """打印带颜色的文本"""
    if os.name == 'nt':  # Windows系统
        print(text)
    else:  # 非Windows系统
        print(f"\033[{color_code}m{text}\033[0m")


def print_success(text):
    """打印成功信息"""
    print_with_color(f"[成功] {text}", 32)  # 绿色


def print_warning(text):
    """打印警告信息"""
    print_with_color(f"[警告] {text}", 33)  # 黄色


def print_error(text):
    """打印错误信息"""
    print_with_color(f"[错误] {text}", 31)  # 红色


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
        print_error(f"命令执行失败: {command}")
        print_error(f"错误码: {e.returncode}")
        print_error(f"错误输出: {e.stderr}")
        return e
    except Exception as e:
        print_error(f"执行命令时发生异常: {command}")
        print_error(f"异常信息: {str(e)}")
        return None


def check_python_installation():
    """检查Python是否安装"""
    print("检查Python环境...")
    result = run_command("python --version", capture_output=True)
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        print_success(f"Python环境检查通过: {result.stdout.strip()}")
        return True
    else:
        print_error("未找到Python！请确保Python已正确安装并添加到系统PATH。")
        return False


def create_virtual_environment():
    """创建Python虚拟环境"""
    if os.path.exists(VENV_DIR):
        print(f"虚拟环境 '{VENV_DIR}' 已存在，跳过创建。")
        return True
    
    print(f"创建Python虚拟环境 '{VENV_DIR}'...")
    result = run_command(f"python -m venv {VENV_DIR}")
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        print_success("虚拟环境创建成功。")
        return True
    else:
        print_error("虚拟环境创建失败！请检查权限和磁盘空间。")
        return False


def activate_virtual_environment():
    """获取虚拟环境中Python和pip的路径"""
    if os.name == 'nt':  # Windows系统
        python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")
        pip_exe = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:  # 非Windows系统
        python_exe = os.path.join(VENV_DIR, "bin", "python")
        pip_exe = os.path.join(VENV_DIR, "bin", "pip")
    
    if not os.path.exists(python_exe) or not os.path.exists(pip_exe):
        print_error(f"虚拟环境激活脚本不存在！路径: {python_exe}")
        return None, None
    
    print(f"使用虚拟环境Python: {python_exe}")
    return python_exe, pip_exe


def install_dependencies(pip_exe):
    """安装依赖包"""
    if not os.path.exists(REQUIREMENTS_FILE):
        print_warning(f"{REQUIREMENTS_FILE}文件不存在！跳过依赖安装。")
        return True
    
    print(f"安装依赖包（{REQUIREMENTS_FILE}）...")
    result = run_command(f"{pip_exe} install -r {REQUIREMENTS_FILE}")
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        print_success("依赖安装成功。")
        return True
    else:
        print_warning("依赖安装过程中出现问题，但仍尝试启动应用。")
        return False


def start_application(python_exe):
    """启动AIGC演示应用"""
    if not os.path.exists(APP_FILE):
        print_error(f"应用文件 {APP_FILE} 不存在！")
        return False
    
    print(f"启动AIGC演示应用（{APP_FILE}）...")
    print("====================================")
    print("应用启动中，请不要关闭此窗口...")
    print("如果需要停止应用，请按 Ctrl+C")
    print("====================================")
    
    try:
        # 使用call而不是run，以便让Streamlit在前台运行
        subprocess.call([python_exe, "-m", "streamlit", "run", APP_FILE])
        return True
    except KeyboardInterrupt:
        print("\n应用已被用户中断。")
        return True
    except Exception as e:
        print_error(f"应用程序启动失败！")
        print_error(f"异常信息: {str(e)}")
        return False


def main():
    """主函数"""
    print("====================================")
    print("     AIGC创意平台启动脚本（Python版本）     ")
    print("====================================")
    
    # 检查Python安装
    if not check_python_installation():
        input("按Enter键退出...")
        sys.exit(1)
    
    # 创建虚拟环境
    if not create_virtual_environment():
        input("按Enter键退出...")
        sys.exit(1)
    
    # 激活虚拟环境（获取Python和pip路径）
    python_exe, pip_exe = activate_virtual_environment()
    if not python_exe or not pip_exe:
        input("按Enter键退出...")
        sys.exit(1)
    
    # 安装依赖
    install_dependencies(pip_exe)
    
    # 启动应用
    start_application(python_exe)
    
    print("====================================")
    print("应用程序已停止运行。")
    input("按Enter键退出...")


if __name__ == "__main__":
    main()
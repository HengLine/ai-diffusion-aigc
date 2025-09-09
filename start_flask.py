#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask应用启动脚本（优化版）

功能：
1. 检查Python环境是否安装
2. 检查虚拟环境是否存在，不存在则创建
3. 根据不同系统激活虚拟环境
4. 安装项目依赖
5. 启动Flask应用

步骤严格按顺序执行，只有上一步成功才执行下一步
"""
import os
import sys
import subprocess
import time

# 获取当前脚本所在目录（项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 设置编码为UTF-8以确保中文显示正常
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 全局变量
VENV_DIR = os.path.join(PROJECT_ROOT, "venv")  # 虚拟环境目录
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")  # 依赖文件
APP_FLASK_MODULE = "hengline.flask.app_flask"  # Flask应用模块路径


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
        print(f"[错误] 命令执行失败: {command}")
        print(f"[错误] 错误码: {e.returncode}")
        print(f"[错误] 错误输出: {e.stderr}")
        return e
    except Exception as e:
        print(f"[错误] 执行命令时发生异常: {command}")
        print(f"[错误] 异常信息: {str(e)}")
        return None


def check_python_installation():
    """步骤1: 检查Python是否安装"""
    print("=== 步骤1: 检查Python环境 ===")
    result = run_command("python --version", capture_output=True)
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        print(f"[成功] Python环境检查通过: {result.stdout.strip()}")
        return True
    else:
        print("[错误] 未找到Python！请确保Python已正确安装并添加到系统PATH。")
        return False


def create_virtual_environment():
    """步骤2: 检查并创建虚拟环境"""
    print("=== 步骤2: 检查虚拟环境 ===")
    if os.path.exists(VENV_DIR):
        print(f"虚拟环境已存在于 '{VENV_DIR}'，检查有效性。")
        # 获取虚拟环境Python路径以验证虚拟环境是否有效
        if os.name == 'nt':  # Windows系统
            venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
        else:  # 非Windows系统
            venv_python = os.path.join(VENV_DIR, "bin", "python")
        
        if os.path.isfile(venv_python):
            print(f"[成功] 虚拟环境有效，使用现有虚拟环境。")
            return True
        else:
            print(f"[警告] 虚拟环境无效，重新创建: {VENV_DIR}")
            import shutil
            shutil.rmtree(VENV_DIR)
    else:
        print(f"虚拟环境不存在于 '{VENV_DIR}'，创建新的虚拟环境。")
    
    print(f"在当前目录下创建Python虚拟环境 '{VENV_DIR}'...")
    result = run_command(f"python -m venv {VENV_DIR}")
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        print("[成功] 虚拟环境创建成功。")
        return True
    else:
        print("[错误] 虚拟环境创建失败！请检查权限和磁盘空间。")
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
        print(f"[错误] 虚拟环境Python解释器不存在！路径: {python_exe}")
        return None, None, None
    
    return python_exe, pip_exe, activate_cmd


def activate_virtual_environment():
    """步骤3: 获取虚拟环境路径并验证可用性"""
    print("=== 步骤3: 获取虚拟环境路径 ===")
    python_exe, pip_exe, activate_cmd = get_virtual_environment_paths()
    
    if not python_exe:
        print("[错误] 无法获取虚拟环境路径。")
        return None, None
    
    # 检查虚拟环境Python解释器是否可执行
    if not os.access(python_exe, os.X_OK):
        print(f"[错误] 虚拟环境Python解释器不可执行: {python_exe}")
        return None, None
    
    # 检查虚拟环境pip是否可执行
    if not os.access(pip_exe, os.X_OK):
        print(f"[错误] 虚拟环境pip不可执行: {pip_exe}")
        return None, None
    
    print(f"[成功] 虚拟环境验证通过，将使用以下路径：")
    print(f"  Python: {python_exe}")
    print(f"  pip: {pip_exe}")
    
    # 注意：在subprocess中执行activate命令不会影响当前进程的环境变量
    # 我们将直接使用虚拟环境的Python和pip完整路径来运行命令
    print("提示：本脚本将直接使用虚拟环境的Python和pip完整路径执行后续操作，无需激活虚拟环境。")
    
    return python_exe, pip_exe


def check_dependencies_satisfied(python_exe):
    """检查依赖是否满足"""
    try:
        print("检查依赖是否满足...")
        # 尝试导入一些关键库来验证依赖是否安装正确
        test_imports = "import flask, requests, json, os, sys"
        result = run_command(f"{python_exe} -c \"{test_imports}\"", capture_output=True)
        
        if result and hasattr(result, 'returncode') and result.returncode != 0:
            print(f"依赖检查失败: {result.stderr}")
            return False
        
        print("依赖检查通过")
        return True
    except Exception as e:
        print(f"检查依赖时出错: {str(e)}")
        return False


def install_dependencies(pip_exe):
    """步骤4: 安装项目依赖"""
    print("=== 步骤4: 安装项目依赖 ===")
    if not os.path.exists(REQUIREMENTS_FILE):
        print(f"[警告] 依赖文件 {REQUIREMENTS_FILE} 不存在！")
        return False
    
    print(f"使用虚拟环境pip安装项目依赖包（{REQUIREMENTS_FILE}）...")
    
    # 使用虚拟环境的pip安装项目依赖
    result = run_command(f'"{pip_exe}" install -r "{REQUIREMENTS_FILE}"')
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        print("[成功] 依赖安装成功。")
        return True
    else:
        print("[错误] 依赖安装失败！")
        return False


def ensure_directories():
    """确保必要的目录存在"""
    print("=== 确保必要的目录存在 ===")
    required_dirs = ['uploads', 'outputs', 'temp']
    
    for folder in required_dirs:
        folder_path = os.path.join(PROJECT_ROOT, folder)
        
        # 检查目录是否存在
        if os.path.exists(folder_path):
            # 检查是否是目录而不是文件
            if os.path.isdir(folder_path):
                print(f"目录 '{folder_path}' 已存在。")
            else:
                print(f"[警告] 路径 '{folder_path}' 存在但不是目录，将重新创建。")
                try:
                    import shutil
                    shutil.rmtree(folder_path)  # 删除文件或目录树
                    os.makedirs(folder_path)
                    print(f"目录 '{folder_path}' 已重新创建。")
                except Exception as e:
                    print(f"[错误] 重新创建目录 '{folder_path}' 失败: {e}")
                    return False
        else:
            # 目录不存在，创建目录
            try:
                os.makedirs(folder_path)
                print(f"目录 '{folder_path}' 已创建。")
            except Exception as e:
                print(f"[错误] 创建目录 '{folder_path}' 失败: {e}")
                return False
    
    return True


def start_flask_application(python_exe):
    """步骤5: 启动Flask应用"""
    print("=== 步骤5: 启动Flask应用 ===")
    
    # 确保必要的目录存在
    if not ensure_directories():
        return False
    
    try:
        print("正在启动Flask应用...")
        print("====================================")
        print("应用启动中，请不要关闭此窗口...")
        print("如果需要停止应用，请按 Ctrl+C")
        print("====================================")
        
        # 使用python -m方式运行Flask应用
        subprocess.run([python_exe, "-m", APP_FLASK_MODULE], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[错误] Flask应用启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n[信息] 应用已被用户中断。")
        return True
    except Exception as e:
        print(f"[错误] 发生未预期的错误: {e}")
        return False


def main():
    """主函数 - 协调整个启动流程"""
    print("====================================")
    print("     Flask应用启动脚本（优化版）     ")
    print("====================================")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"将使用的虚拟环境: {VENV_DIR}")
    print(f"将启动的Flask应用模块: {APP_FLASK_MODULE}")
    
    # 步骤1: 检查Python安装
    if not check_python_installation():
        input("按Enter键退出...")
        sys.exit(1)
    
    # 步骤2: 检查并创建虚拟环境
    if not create_virtual_environment():
        input("按Enter键退出...")
        sys.exit(1)
    
    # 步骤3: 激活虚拟环境
    python_exe, pip_exe = activate_virtual_environment()
    if not python_exe:
        input("按Enter键退出...")
        sys.exit(1)
    
    # 步骤4: 安装项目依赖
    # 先检查依赖是否已满足，如果满足则跳过安装
    if not check_dependencies_satisfied(python_exe):
        print("依赖不满足，需要安装...")
        if not install_dependencies(pip_exe):
            input("按Enter键退出...")
            sys.exit(1)
    else:
        print("依赖已满足，跳过安装步骤。")
    
    # 步骤5: 启动Flask应用
    start_flask_application(python_exe)
    
    print("====================================")
    print("应用程序已停止运行。")
    input("按Enter键退出...")


if __name__ == "__main__":
    main()
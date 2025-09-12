#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AIGC创意平台启动脚本（优化版）

功能：
1. 检查Python环境是否安装
2. 检查虚拟环境是否存在，不存在则创建
3. 根据不同系统激活虚拟环境
4. 安装项目依赖
5. 启动Streamlit应用

步骤严格按顺序执行，只有上一步成功才执行下一步
"""

import os
import subprocess
import sys
import time

# 获取当前脚本所在目录（项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 添加项目根目录到Python路径
sys.path.append(PROJECT_ROOT)

# 导入自定义日志模块
from hengline.logger import info, error, warning, debug

# 设置编码为UTF-8以确保中文显示正常
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 全局变量 - 明确指定虚拟环境为当前目录下的venv
VENV_DIR = os.path.join(PROJECT_ROOT, "venv")  # 使用绝对路径确保一致性
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")
APP_FILE = os.path.join(PROJECT_ROOT, "hengline", "app_streamlit.py")  # 修复后的应用文件路径


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
    except ModuleNotFoundError as e:
        raise e  # 👈 显式抛出捕获的异常
    except Exception as e:
        error(f"执行命令时发生异常: {command}")
        error(f"异常信息: {str(e)}")
        return None


def check_python_installation():
    """步骤1: 检查Python是否安装"""
    info("=== 检查Python环境中 ===")
    result = run_command("python --version", capture_output=True)
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        debug(f"[成功] Python环境检查通过: {result.stdout.strip()}")
        return True
    else:
        error("[错误] 未找到Python！请确保Python已正确安装并添加到系统PATH。")
        return False


def create_virtual_environment():
    """步骤2: 检查并创建虚拟环境"""
    info("=== 检查虚拟环境中 ===")
    if os.path.exists(VENV_DIR):
        debug(f"虚拟环境已存在于 '{VENV_DIR}'，检查有效性。")
        # 获取虚拟环境Python路径以验证虚拟环境是否有效
        if os.name == 'nt':  # Windows系统
            venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
        else:  # 非Windows系统
            venv_python = os.path.join(VENV_DIR, "bin", "python")

        if os.path.isfile(venv_python):
            debug(f"[成功] 虚拟环境有效，使用现有虚拟环境。")
            return True
        else:
            warning(f"[警告] 虚拟环境无效，重新创建: {VENV_DIR}")
            import shutil
            shutil.rmtree(VENV_DIR)
    else:
        debug(f"虚拟环境不存在于 '{VENV_DIR}'，创建新的虚拟环境。")

    info(f"在当前目录下创建Python虚拟环境 '{VENV_DIR}'...")
    result = run_command(f"python -m venv {VENV_DIR}")
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        debug("[成功] 虚拟环境创建成功。")
        return True
    else:
        error("[错误] 虚拟环境创建失败！请检查权限和磁盘空间。")
        return False


def get_virtual_environment_paths():
    """获取虚拟环境中Python、pip和activate命令的绝对路径"""
    if os.name == 'nt':  # Windows系统
        python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")
        pip_exe = os.path.join(VENV_DIR, "Scripts", "pip.exe")
        activate_cmd = os.path.join(VENV_DIR, "Scripts", "activate.bat")
    else:  # 非Windows系统
        python_exe = os.path.join(VENV_DIR, "bin", "python")
        pip_exe = os.path.join(VENV_DIR, "bin", "pip")
        activate_cmd = os.path.join(VENV_DIR, "bin", "activate")

    # 验证虚拟环境文件是否存在
    if not os.path.exists(python_exe):
        error(f"[错误] 虚拟环境Python解释器不存在！路径: {python_exe}")
        return None, None, None

    debug(f"使用虚拟环境Python: {python_exe}")
    return python_exe, pip_exe, activate_cmd


def activate_virtual_environment():
    """步骤3: 获取虚拟环境路径并验证可用性"""
    debug("=== 步骤3: 获取虚拟环境路径 ===")
    python_exe, pip_exe, activate_cmd = get_virtual_environment_paths()

    if not python_exe:
        error("[错误] 无法获取虚拟环境路径。")
        return None, None

    # 检查虚拟环境Python解释器是否可执行
    if not os.access(python_exe, os.X_OK):
        error(f"[错误] 虚拟环境Python解释器不可执行: {python_exe}")
        return None, None

    # 检查虚拟环境pip是否可执行
    if not os.access(pip_exe, os.X_OK):
        error(f"[错误] 虚拟环境pip不可执行: {pip_exe}")
        return None, None

    debug(f"[成功] 虚拟环境验证通过，将使用以下路径： Python: {python_exe}")

    # 注意：在subprocess中执行activate命令不会影响当前进程的环境变量
    # 我们将直接使用虚拟环境的Python和pip完整路径来运行命令
    debug("提示：本脚本将直接使用虚拟环境的Python和pip完整路径执行后续操作，无需激活虚拟环境。")

    return python_exe, pip_exe


def install_dependencies():
    """步骤4: 使用虚拟环境的pip安装项目依赖"""
    info("=== 检查项目依赖中 ===")
    if not os.path.exists(REQUIREMENTS_FILE):
        error(f"[错误] 依赖文件 {REQUIREMENTS_FILE} 不存在！")
        return False

    # 使用虚拟环境的pip安装项目依赖
    result = run_command(f'pip install -r "{REQUIREMENTS_FILE}"')
    if result and hasattr(result, 'returncode') and result.returncode == 0:
        debug("[成功] 依赖安装成功。")
        return True
    else:
        error("[错误] 依赖安装失败！")
        return False


def start_application_with_retry():
    """步骤5: 启动Streamlit应用，支持自动重试"""
    info("=== 开启启动Streamlit应用 ===")
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            if not os.path.exists(APP_FILE):
                error(f"[错误] 应用文件 {APP_FILE} 不存在！")
                return False

            # 重新获取pip路径并安装依赖
            _, pip_exe_retry, _ = get_virtual_environment_paths()
            if not pip_exe_retry:
                error("无法获取虚拟环境pip路径")
                retry_count += 1
                if retry_count < max_retries:
                    info(f"等待2秒后重试 ({retry_count}/{max_retries})\n")
                    time.sleep(2)
                    continue
                else:
                    return False

            debug(f"启动AIGC创意平台应用（{APP_FILE}）...")
            info("================HengLine AIGC====================")
            info("应用启动中，请不要关闭此窗口。如果需要停止应用，请按 Ctrl+C")

            # 使用虚拟环境的Python启动Streamlit应用
            result = run_command(f"streamlit run {APP_FILE}", shell=True)
            if result and hasattr(result, 'returncode') and result.returncode == 1:
                if not install_dependencies():
                    error("依赖重新安装失败")
                retry_count += 1
                continue

            return result is not None
        except KeyboardInterrupt:
            info("\n应用已被用户中断。")
            return True
        except ModuleNotFoundError:
            error("缺少依赖模块，请检查requirements.txt")
            if not install_dependencies():
                error("依赖重新安装失败")
            retry_count += 1

        except Exception as e:
            error(f"应用程序启动失败！,异常信息: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                info(f"等待2秒后重试 ({retry_count}/{max_retries})\n")
                time.sleep(2)
            else:
                error("达到最大重试次数，启动失败")
                return False


def main():
    """主函数 - 协调整个启动流程"""
    info("===========================================")
    info("            HengLine AIGC 创意平台          ")
    info("===========================================")
    debug(f"当前工作目录: {os.getcwd()}")
    debug(f"项目根目录: {PROJECT_ROOT}")
    debug(f"将使用的虚拟环境: {VENV_DIR}")
    debug(f"将启动的应用文件: {APP_FILE}")

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

    # 步骤5: 启动Streamlit应用
    start_application_with_retry()

    info("====================================")
    info("应用程序已停止运行。按Enter键退出...")


if __name__ == "__main__":
    main()

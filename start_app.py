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
import sys

from app_env import AppBaseEnv

# 获取当前脚本所在目录（项目根目录）
# PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = "."

# 添加项目根目录到Python路径
sys.path.append(PROJECT_ROOT)

# 导入自定义日志模块
from hengline.logger import info, error

# 设置编码为UTF-8以确保中文显示正常
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 全局变量 - 明确指定虚拟环境为当前目录下的venv
APP_FILE = os.path.join(PROJECT_ROOT, "hengline", "streamlit", "app_streamlit.py")  # 修复后的应用文件路径


class StreamlitApp(AppBaseEnv):

    def start_application(self):
        """步骤5: 启动Streamlit应用，支持自动重试"""
        info("=== 开启启动Streamlit应用 ===")

        try:
            if not os.path.exists(APP_FILE):
                error(f"[错误] 应用文件 {APP_FILE} 不存在！")
                return False

            # 使用虚拟环境的Python启动Streamlit应用
            result = self.run_command(f"streamlit run {APP_FILE}", shell=True)

            return result is not None
        except KeyboardInterrupt:
            info("应用已被用户中断。")
            return True
        except ModuleNotFoundError:
            error("缺少依赖模块，请检查requirements.txt")
            return False
        except Exception as e:
            error(f"应用程序启动失败！,异常信息: {str(e)}")
            return False


if __name__ == "__main__":
    StreamlitApp().main()

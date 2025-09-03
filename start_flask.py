#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask应用启动脚本，解决路径和导入问题
"""
import os
import sys
import subprocess

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """启动Flask应用"""
    try:
        # 确保必要的目录存在
        for folder in ['uploads', 'outputs', 'temp']:
            folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder)
            os.makedirs(folder_path, exist_ok=True)
        
        # 使用python -m方式运行Flask应用
        print("正在启动Flask应用...")
        subprocess.run([sys.executable, "-m", "scripts.app_flask"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Flask应用启动失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()
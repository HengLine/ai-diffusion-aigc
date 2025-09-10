#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证ComfyUIRunner修复的脚本
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义日志模块
from hengline.utils.logger import info, error
# 导入工作流运行器
from hengline.run_workflow import ComfyUIRunner


def verify_comfyui_runner_initialization():
    """验证ComfyUIRunner初始化是否正常"""
    try:
        # 导入配置工具
        from hengline.utils.config_utils import get_comfyui_api_url
        
        # 获取正确的参数
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
        api_url = get_comfyui_api_url()
        
        info(f"准备初始化ComfyUIRunner...")
        info(f"output_dir: {output_dir}")
        info(f"api_url: {api_url}")
        
        # 初始化ComfyUIRunner（使用修复后的正确参数顺序）
        runner = ComfyUIRunner(output_dir, api_url)
        
        info("✅ ComfyUIRunner初始化成功！")
        info(f"验证输出目录: {runner.output_dir}")
        info(f"验证API URL: {runner.api_url}")
        
        # 检查输出目录是否存在
        if os.path.exists(output_dir):
            info(f"✅ 输出目录 '{output_dir}' 已存在")
        else:
            info(f"输出目录 '{output_dir}' 不存在，ComfyUIRunner应该会在运行时创建它")
        
        return True
    except Exception as e:
        error(f"❌ ComfyUIRunner初始化失败: {str(e)}")
        import traceback
        error(f"堆栈跟踪:\n{traceback.format_exc()}")
        return False


def main():
    """主函数"""
    info("====== 开始验证ComfyUIRunner修复 ======")
    success = verify_comfyui_runner_initialization()
    if success:
        info("🎉 验证成功！ComfyUIRunner初始化问题已解决。")
    else:
        error("❌ 验证失败！请查看错误信息。")
    info("====== 验证完成 ======")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIGC演示应用的Web界面
"""

import os
import sys
import streamlit as st
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入自定义日志模块
from hengline.logger import error, warning, debug, error
# 导入启动任务监听器
from hengline.core.task_init import StartupTaskListener
# 导入配置工具
from hengline.utils.config_utils import get_config, get_paths_config, get_comfyui_api_url, get_workflow_path, get_task_settings

# 导入工作流运行器
from hengline.workflow.run_workflow import ComfyUIRunner
# 从templates文件夹导入标签页模块
from hengline.streamlit.templates.text_to_image_tab import TextToImageTab
from hengline.streamlit.templates.image_to_image_tab import ImageToImageTab
from hengline.streamlit.templates.image_to_video_tab import ImageToVideoTab
from hengline.streamlit.templates.text_to_video_tab import TextToVideoTab

class AIGCWebApp:
    """AIGC应用的Web界面类"""
    
    def __init__(self):
        """初始化Web应用"""
        # 设置页面配置
        st.set_page_config(
            page_title="AIGC AI生成内容演示",
            page_icon="🎨",
            layout="wide"
        )
        
        # 初始化会话状态
        if "runner" not in st.session_state:
            # 使用配置工具获取输出目录配置
            output_folder = get_paths_config().get("output_folder", "outputs")
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_folder)
            api_url = get_comfyui_api_url()
            st.session_state.runner = ComfyUIRunner(output_dir, api_url)

    def _configure_comfyui(self) -> None:
        """配置ComfyUI相关参数"""
        with st.expander("⚙️ ComfyUI配置"):
            # 不再配置ComfyUI路径，仅配置API URL
            st.info("ComfyUI路径配置已移除，系统将通过API直接连接到运行中的ComfyUI服务。")
    
    def run(self) -> None:
        """运行Web应用"""
        # 页面标题
        st.title("🎨 AIGC AI生成内容演示")
        
        # 配置ComfyUI
        self._configure_comfyui()
        
        # 创建标签页
        tabs = st.tabs([
            "文生图", 
            "图生图", 
            "图生视频",
            "文生视频"
        ])
        
        # 确保ComfyUI运行器已初始化
        if 'runner' not in st.session_state:
            return
        
        # 文生图标签页
        with tabs[0]:
            text_to_image_tab = TextToImageTab(st.session_state.runner)
            text_to_image_tab.render()
        
        # 图生图标签页
        with tabs[1]:
            image_to_image_tab = ImageToImageTab(st.session_state.runner)
            image_to_image_tab.render()
        
        # 图生视频标签页
        with tabs[2]:
            image_to_video_tab = ImageToVideoTab(st.session_state.runner)
            image_to_video_tab.render()
        
        # 文生视频标签页
        with tabs[3]:
            text_to_video_tab = TextToVideoTab(st.session_state.runner)
            text_to_video_tab.render()

if __name__ == "__main__":
    # 启动任务监听器，处理历史未完成任务
    StartupTaskListener().start()
    
    # 创建并运行Web应用
    app = AIGCWebApp()
    app.run()
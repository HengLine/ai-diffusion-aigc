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
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import error, warning, debug
# 导入启动任务监听器
from hengline.core.task_init import StartupTaskListener
# 导入配置工具
from hengline.utils.config_utils import get_config, get_paths_config, get_comfyui_api_url, get_comfyui_config, get_workflow_path, get_task_settings, save_comfyui_config

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
            page_title="AIGC 生成内容演示平台",
            page_icon="🎨",
            layout="wide"
        )
        
        # 初始化会话状态
        if "runner" not in st.session_state:
            # 使用配置工具获取输出目录配置
            output_folder = get_paths_config().get("output_folder", "outputs")
            
            # 获取当前文件绝对路径
            current_file = os.path.abspath(__file__)
            debug(f"当前文件路径: {current_file}")
            
            # 计算项目根目录（确保正确指向e:/Projects/blogs/ai-diffusion-aigc）
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            debug(f"计算的项目根目录: {project_root}")
            
            # 设置输出目录到项目根目录
            output_dir = os.path.join(project_root, output_folder)
            debug(f"最终输出目录: {output_dir}")
            
            # 获取ComfyUI API URL配置
            api_url = get_comfyui_api_url()
            debug(f"初始化ComfyUIRunner，API URL: {api_url}, 输出目录: {output_dir}")
            
            # 创建并保存ComfyUIRunner实例
            st.session_state.runner = ComfyUIRunner(output_dir, api_url)
            
            # 验证输出目录是否存在，如果不存在则创建
            os.makedirs(output_dir, exist_ok=True)
            debug(f"已确保输出目录存在: {output_dir}")
        else:
            # 更新现有runner的API URL
            current_api_url = get_comfyui_api_url()
            if st.session_state.runner.api_url != current_api_url:
                debug(f"更新ComfyUI API URL: 从 {st.session_state.runner.api_url} 到 {current_api_url}")
                st.session_state.runner.api_url = current_api_url

    def _configure_comfyui(self) -> None:
        """配置ComfyUI相关参数"""
        with st.expander("⚙️ ComfyUI配置"):
            # 获取当前ComfyUI API URL配置
            current_api_url = get_comfyui_api_url()
            
            # 显示可编辑的API URL输入框
            new_api_url = st.text_input(
                "ComfyUI API URL", 
                value=current_api_url,
                help="ComfyUI API服务地址，例如: http://127.0.0.1:8188"
            )
            
            # 添加保存按钮
            if st.button("保存配置"):
                # 先保存到配置文件
                if current_api_url != new_api_url:
                    # 保存配置到文件
                    if save_comfyui_config(api_url=new_api_url):
                        # 更新会话状态中的runner的API URL
                        debug(f"更新ComfyUI API URL: 从 {st.session_state.runner.api_url} 到 {new_api_url}")
                        st.session_state.runner.api_url = new_api_url
                        st.success("ComfyUI API URL已成功保存并应用！")
                    else:
                        st.error("保存配置失败，请检查文件权限。")
                else:
                    st.info("API URL没有变化")
            
            st.info("注意：配置更改会自动保存到本地配置文件，并在所有会话中生效。")
    
    def run(self) -> None:
        """运行Web应用"""
        # 页面标题
        st.title("🎨 AIGC 生成内容演示平台")
        st.html("""
        本应用基于ComfyUI，支持文生图、图生图、图生视频、文生视频等功能。</br>
        <font color="red">注意：本应用仅支持单次提交，不记录历史任务，不支持任务管理。页面刷新后任务数据会丢失。</font>
        """)

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
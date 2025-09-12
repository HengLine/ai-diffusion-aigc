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
from hengline.logger import info, error
# 导入启动任务监听器
from hengline.core.task_init import StartupTaskListener
# 导入配置工具
from hengline.utils.config_utils import get_config, get_paths_config, get_comfyui_api_url, get_workflow_path, get_task_settings

# 导入工作流运行器
from hengline.workflow.run_workflow import ComfyUIRunner
# 导入拆分后的标签页模块
from hengline.streamlit.text_to_image_tab import TextToImageTab
from hengline.streamlit.image_to_image_tab import ImageToImageTab
from hengline.streamlit.image_to_video_tab import ImageToVideoTab
from hengline.streamlit.text_to_video_tab import TextToVideoTab

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
    
    def _text_to_image_tab(self) -> None:
        """文生图标签页"""
        debug("====== 进入文生图标签页 ======")
        st.subheader("📝 文生图")
        
        # 获取默认配置
        text_to_image_settings = get_task_settings("text_to_image")
        default_width = text_to_image_settings.get("width", 512)
        default_height = text_to_image_settings.get("height", 512)
        default_steps = text_to_image_settings.get("steps", 20)
        default_cfg = text_to_image_settings.get("cfg", 7.0)
        
        # 用户输入
        col1, col2 = st.columns(2)
        with col1:
            prompt = st.text_area("提示词", height=150, key="tti_prompt")
            negative_prompt = st.text_area("负面提示词", value="low quality, blurry, bad anatomy", height=100, key="tti_negative_prompt")
        with col2:
            width = st.slider("宽度", min_value=256, max_value=1024, value=default_width, step=64, key="tti_width")
            height = st.slider("高度", min_value=256, max_value=1024, value=default_height, step=64, key="tti_height")
            steps = st.slider("步数", min_value=1, max_value=50, value=default_steps, step=1, key="tti_steps")
            cfg = st.slider("CFG Scale", min_value=1.0, max_value=15.0, value=float(default_cfg), step=0.5, key="tti_cfg")
            output_filename = st.text_input("输出文件名", value="text_to_image.png", key="tti_output_filename")

        if st.button("生成图像", key="tti_generate_button"):
            if not prompt:
                st.error("请输入提示词")
                return
            
            if not st.session_state.comfyui_path:
                st.error("请先配置ComfyUI路径")
                return
            
            try:
                with st.spinner("正在生成图像..."):
                    # 调用文生图工作流
                    workflow_file = get_workflow_path("text_to_image")
                    workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), workflow_file)
                    
                    # 检查工作流文件是否存在
                    if not os.path.exists(workflow_path):
                        st.error(f"工作流文件不存在: {workflow_path}")
                        return
                    
                    # 加载工作流
                    workflow = st.session_state.runner.load_workflow(workflow_path)
                    
                    # 更新工作流参数
                    params = {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "width": width,
                        "height": height,
                        "steps": steps,
                        "cfg": cfg
                    }
                    updated_workflow = st.session_state.runner.update_workflow_params(workflow, params)
                    
                    # 运行工作流
                    success = st.session_state.runner.run_workflow(updated_workflow, output_filename)
                    
                    # 获取输出目录
                    output_folder = get_paths_config().get("output_folder", "outputs")
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_folder)
                    output_path = os.path.join(output_dir, output_filename)
                    
                if success:
                    st.success(f"图像生成成功，结果保存至: {output_path}")
                    
                    # 显示生成的图像
                    if output_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        try:
                            st.image(output_path, caption="生成的图像", use_container_width=True)
                        except Exception as e:
                            st.info(f"无法显示结果图像: {str(e)}")
                else:
                    st.error("图像生成失败，请检查日志了解详情")
            except Exception as e:
                import traceback
                error_type = type(e).__name__
                error_message = str(e)
                error_traceback = traceback.format_exc()
                error(f"文生图生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
                st.error(f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息")
    
    def _image_to_image_tab(self) -> None:
        """图生图标签页"""
        debug("====== 进入图生图标签页 ======")
        st.subheader("🖼️ 图生图")
        
        # 获取默认配置
        image_to_image_settings = get_task_settings("image_to_image")
        default_width = image_to_image_settings.get("width", 512)
        default_height = image_to_image_settings.get("height", 512)
        default_steps = image_to_image_settings.get("steps", 20)
        default_cfg = image_to_image_settings.get("cfg", 7.0)
        default_denoising = image_to_image_settings.get("denoising_strength", 0.7)
        
        # 用户输入
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("上传图像", type=["png", "jpg", "jpeg"], key="iti_file_uploader")
            prompt = st.text_area("提示词", height=150, key="iti_prompt")
            negative_prompt = st.text_area("负面提示词", value="low quality, blurry, bad anatomy", height=100, key="iti_negative_prompt")
        with col2:
            width = st.slider("宽度", min_value=256, max_value=1024, value=default_width, step=64, key="iti_width")
            height = st.slider("高度", min_value=256, max_value=1024, value=default_height, step=64, key="iti_height")
            steps = st.slider("步数", min_value=1, max_value=50, value=default_steps, step=1, key="iti_steps")
            cfg = st.slider("CFG Scale", min_value=1.0, max_value=15.0, value=float(default_cfg), step=0.5, key="iti_cfg")
            denoising_strength = st.slider("去噪强度", min_value=0.1, max_value=1.0, value=float(default_denoising), step=0.05, key="iti_denoising")
            output_filename = st.text_input("输出文件名", value="image_to_image.png", key="iti_output_filename")

        if uploaded_file is not None:
            st.image(uploaded_file, caption="上传的图像", use_container_width=True)

        if st.button("生成变体", key="iti_generate_button"):
            if not uploaded_file:
                st.error("请先上传图像")
                return
            
            if not prompt:
                st.error("请输入提示词")
                return
            
            if not st.session_state.comfyui_path:
                st.error("请先配置ComfyUI路径")
                return
            
            try:
                with st.spinner("正在生成变体..."):
                    # 保存上传的文件
                    temp_folder = get_paths_config().get("temp_folder", "temp")
                    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), temp_folder)
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_image_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 调用图生图工作流
                    workflow_file = get_workflow_path("image_to_image")
                    workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), workflow_file)
                    
                    # 检查工作流文件是否存在
                    if not os.path.exists(workflow_path):
                        st.error(f"工作流文件不存在: {workflow_path}")
                        return
                    
                    # 加载工作流
                    workflow = st.session_state.runner.load_workflow(workflow_path)
                    
                    # 更新工作流参数
                    params = {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "image_path": temp_image_path,
                        "width": width,
                        "height": height,
                        "steps": steps,
                        "cfg": cfg,
                        "denoising_strength": denoising_strength
                    }
                    updated_workflow = st.session_state.runner.update_workflow_params(workflow, params)
                    
                    # 运行工作流
                    success = st.session_state.runner.run_workflow(updated_workflow, output_filename)
                    
                    # 获取输出目录
                    output_folder = get_paths_config().get("output_folder", "outputs")
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_folder)
                    output_path = os.path.join(output_dir, output_filename)
                    
                if success:
                    st.success(f"变体生成成功，结果保存至: {output_path}")
                    
                    # 显示生成的图像
                    if output_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        try:
                            st.image(output_path, caption="生成的变体", use_container_width=True)
                        except Exception as e:
                            st.info(f"无法显示结果图像: {str(e)}")
                else:
                    st.error("变体生成失败，请检查日志了解详情")
            except Exception as e:
                import traceback
                error_type = type(e).__name__
                error_message = str(e)
                error_traceback = traceback.format_exc()
                error(f"图生图生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
                st.error(f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息")
    
    def _image_to_video_tab(self) -> None:
        """图生视频标签页"""
        debug("====== 进入图生视频标签页 ======")
        st.subheader("🎬 图生视频")
        
        # 获取默认配置
        image_to_video_settings = get_task_settings("image_to_video")
        default_width = image_to_video_settings.get("width", 512)
        default_height = image_to_video_settings.get("height", 512)
        default_frames = image_to_video_settings.get("frames", 16)
        default_fps = image_to_video_settings.get("fps", 8)
        
        # 用户输入
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("上传图像", type=["png", "jpg", "jpeg"], key="itv_file_uploader")
            prompt = st.text_area("提示词", height=150, key="itv_prompt")
            negative_prompt = st.text_area("负面提示词", value="low quality, blurry, unrealistic, static", height=100, key="itv_negative_prompt")
        with col2:
            width = st.slider("宽度", min_value=256, max_value=1024, value=default_width, step=64, key="itv_width")
            height = st.slider("高度", min_value=256, max_value=1024, value=default_height, step=64, key="itv_height")
            frames = st.slider("帧数", min_value=4, max_value=32, value=default_frames, step=1, key="itv_frames")
            fps = st.slider("帧率", min_value=4, max_value=30, value=default_fps, step=1, key="itv_fps")
            output_filename = st.text_input("输出文件名", value="image_to_video.mp4", key="itv_output_filename")

        if uploaded_file is not None:
            st.image(uploaded_file, caption="上传的图像", use_container_width=True)

        if st.button("生成视频", key="itv_generate_button"):
            if not uploaded_file:
                st.error("请先上传图像")
                return
            
            if not prompt:
                st.error("请输入提示词")
                return
            
            if not st.session_state.comfyui_path:
                st.error("请先配置ComfyUI路径")
                return
            
            try:
                with st.spinner("正在生成视频..."):
                    # 保存上传的文件
                    temp_folder = get_paths_config().get("temp_folder", "temp")
                    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), temp_folder)
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_image_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 调用图生视频工作流
                    workflow_file = get_workflow_path("image_to_video")
                    workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), workflow_file)
                    
                    # 检查工作流文件是否存在
                    if not os.path.exists(workflow_path):
                        st.error(f"工作流文件不存在: {workflow_path}")
                        return False
                    
                    # 加载工作流
                    workflow = st.session_state.runner.load_workflow(workflow_path)
                    
                    # 更新工作流参数
                    params = {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "image_path": temp_image_path,
                        "width": width,
                        "height": height,
                        "frames": frames,
                        "fps": fps
                    }
                    updated_workflow = st.session_state.runner.update_workflow_params(workflow, params)
                    
                    # 运行工作流
                    success = st.session_state.runner.run_workflow(updated_workflow, output_filename)
                    
                    # 获取输出目录
                    output_folder = get_paths_config().get("output_folder", "outputs")
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_folder)
                    output_path = os.path.join(output_dir, output_filename)
                    
                if success:
                    st.success(f"视频生成成功，结果保存至: {output_path}")
                    
                    # 显示生成的视频
                    if output_path.lower().endswith('.mp4'):
                        try:
                            st.video(output_path)
                        except Exception as e:
                            st.info(f"无法显示结果视频: {str(e)}")
                else:
                    st.error("视频生成失败，请检查日志了解详情")
            except Exception as e:
                import traceback
                error_type = type(e).__name__
                error_message = str(e)
                error_traceback = traceback.format_exc()
                error(f"图生视频生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
                st.error(f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息")
    

    

    
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
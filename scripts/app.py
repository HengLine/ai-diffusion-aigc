#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIGC演示应用的Web界面
"""

import os
import sys
import json
import streamlit as st
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工作流运行器
from scripts.run_workflow import ComfyUIRunner, AIGCApplication

class AIGCWebApp:
    """AIGC应用的Web界面类"""
    
    def __init__(self):
        """初始化Web应用"""
        # 加载配置文件
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 设置页面配置
        st.set_page_config(
            page_title="AIGC AI生成内容演示",
            page_icon="🎨",
            layout="wide"
        )
        
        # 初始化会话状态
        if "comfyui_path" not in st.session_state:
            st.session_state.comfyui_path = self.config["comfyui"]["path"]
        
        if "runner" not in st.session_state:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
            st.session_state.runner = ComfyUIRunner(st.session_state.comfyui_path, output_dir)
        
        if "app" not in st.session_state:
            st.session_state.app = AIGCApplication(st.session_state.runner)
    
    def _configure_comfyui(self) -> None:
        """配置ComfyUI路径"""
        with st.expander("⚙️ ComfyUI配置"):
            comfyui_path = st.text_input("ComfyUI安装路径", value=st.session_state.comfyui_path, key="config_comfyui_path")

            if st.button("保存配置", key="config_save_button"):
                if os.path.exists(comfyui_path):
                    st.session_state.comfyui_path = comfyui_path
                    # 更新配置文件
                    self.config["comfyui"]["path"] = comfyui_path
                    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "config.json")
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(self.config, f, ensure_ascii=False, indent=2)
                    # 重新初始化运行器
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
                    st.session_state.runner = ComfyUIRunner(st.session_state.comfyui_path, output_dir)
                    st.session_state.app = AIGCApplication(st.session_state.runner)
                    st.success("配置保存成功")
                else:
                    st.error(f"ComfyUI路径不存在: {comfyui_path}")
    
    def _text_to_image_tab(self) -> None:
        """文生图标签页"""
        st.subheader("📝 文生图")
        
        # 获取默认配置
        default_width = self.config["settings"]["text_to_image"]["width"]
        default_height = self.config["settings"]["text_to_image"]["height"]
        default_steps = self.config["settings"]["text_to_image"]["steps"]
        default_cfg = self.config["settings"]["text_to_image"]["cfg"]
        
        # 用户输入
        col1, col2 = st.columns(2)
        with col1:
            prompt = st.text_area("提示词", height=150, key="tti_prompt")
            negative_prompt = st.text_area("负面提示词", value="low quality, blurry, bad anatomy", height=100, key="tti_negative_prompt")
        with col2:
            width = st.slider("宽度", min_value=256, max_value=1024, value=default_width, step=64, key="tti_width")
            height = st.slider("高度", min_value=256, max_value=1024, value=default_height, step=64, key="tti_height")
            steps = st.slider("步数", min_value=1, max_value=50, value=default_steps, step=1, key="tti_steps")
            cfg = st.slider("CFG Scale", min_value=1.0, max_value=15.0, value=default_cfg, step=0.5, key="tti_cfg")
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
                    # 这里应该是调用文生图工作流的代码
                    # 为了演示，我们创建一个模拟结果
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
                    output_path = os.path.join(output_dir, output_filename)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"这是一个模拟的文生图结果\n")
                        f.write(f"提示词: {prompt}\n")
                        f.write(f"参数: 宽度={width}, 高度={height}, 步数={steps}, CFG={cfg}")
                    
                st.success(f"图像生成成功，结果保存至: {output_path}")
                
                # 显示生成的图像（如果是实际图像文件）
                if output_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        st.image(output_path, caption="生成的图像")
                    except:
                        st.info("无法显示结果图像（模拟文件）")
            except Exception as e:
                st.error(f"生成失败: {str(e)}")
    
    def _image_to_image_tab(self) -> None:
        """图生图标签页"""
        st.subheader("🖼️ 图生图")
        
        # 获取默认配置
        default_width = self.config["settings"]["image_to_image"]["width"]
        default_height = self.config["settings"]["image_to_image"]["height"]
        default_steps = self.config["settings"]["image_to_image"]["steps"]
        default_cfg = self.config["settings"]["image_to_image"]["cfg"]
        default_denoising = self.config["settings"]["image_to_image"]["denoising_strength"]
        
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
            cfg = st.slider("CFG Scale", min_value=1.0, max_value=15.0, value=default_cfg, step=0.5, key="iti_cfg")
            denoising_strength = st.slider("去噪强度", min_value=0.1, max_value=1.0, value=default_denoising, step=0.05, key="iti_denoising")
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
                    temp_image_path = os.path.join("temp", uploaded_file.name)
                    os.makedirs("temp", exist_ok=True)
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 这里应该是调用图生图工作流的代码
                    # 为了演示，我们创建一个模拟结果
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
                    output_path = os.path.join(output_dir, output_filename)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"这是一个模拟的图生图结果\n")
                        f.write(f"输入图像: {uploaded_file.name}\n")
                        f.write(f"提示词: {prompt}\n")
                        f.write(f"参数: 宽度={width}, 高度={height}, 步数={steps}, CFG={cfg}, 去噪强度={denoising_strength}")
                    
                st.success(f"变体生成成功，结果保存至: {output_path}")
                
                # 显示生成的图像（如果是实际图像文件）
                if output_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        st.image(output_path, caption="生成的变体")
                    except:
                        st.info("无法显示结果图像（模拟文件）")
            except Exception as e:
                st.error(f"生成失败: {str(e)}")
    
    def _image_to_video_tab(self) -> None:
        """图生视频标签页"""
        st.subheader("🎬 图生视频")
        
        # 获取默认配置
        default_width = self.config["settings"]["image_to_video"]["width"]
        default_height = self.config["settings"]["image_to_video"]["height"]
        default_frames = self.config["settings"]["image_to_video"]["frames"]
        default_fps = self.config["settings"]["image_to_video"]["fps"]
        
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
                    temp_image_path = os.path.join("temp", uploaded_file.name)
                    os.makedirs("temp", exist_ok=True)
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 这里应该是调用图生视频工作流的代码
                    # 为了演示，我们创建一个模拟结果
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
                    output_path = os.path.join(output_dir, output_filename)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"这是一个模拟的图生视频结果\n")
                        f.write(f"输入图像: {uploaded_file.name}\n")
                        f.write(f"提示词: {prompt}\n")
                        f.write(f"参数: 宽度={width}, 高度={height}, 帧数={frames}, 帧率={fps}")
                    
                st.success(f"视频生成成功，结果保存至: {output_path}")
                
                # 显示生成的视频（如果是实际视频文件）
                if output_path.lower().endswith('.mp4'):
                    try:
                        st.video(output_path)
                    except:
                        st.info("无法显示结果视频（模拟文件）")
            except Exception as e:
                st.error(f"生成失败: {str(e)}")
    
    def _ancient_clothing_tab(self) -> None:
        """古装图片生成标签页"""
        st.subheader("👘 古装图片生成")
        
        # 获取默认配置
        default_prompt = self.config["settings"]["ancient_clothing"]["default_prompt"]
        default_negative_prompt = self.config["settings"]["ancient_clothing"]["negative_prompt"]
        
        # 用户输入
        col1, col2 = st.columns(2)
        with col1:
            prompt = st.text_area("提示词", value=default_prompt, height=150, key="ac_prompt")
            negative_prompt = st.text_area("负面提示词", value=default_negative_prompt, height=100, key="ac_negative_prompt")
        with col2:
              output_filename = st.text_input("输出文件名", value="ancient_clothing.png", key="ac_output_filename")

        if st.button("生成古装图片", key="ac_generate_button"):
            if not st.session_state.comfyui_path:
                st.error("请先配置ComfyUI路径")
                return
            
            try:
                with st.spinner("正在生成古装图片..."):
                    # 调用古装图片生成应用
                    success = st.session_state.app.generate_ancient_clothing(prompt, output_filename)
                    
                if success:
                    st.success(f"古装图片生成成功")
                    # 显示生成的图像
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
                    output_path = os.path.join(output_dir, output_filename)
                    if os.path.exists(output_path):
                        try:
                            st.image(output_path, caption="生成的古装图片")
                        except:
                            st.info("无法显示结果图像")
                else:
                    st.error("古装图片生成失败")
            except Exception as e:
                st.error(f"生成失败: {str(e)}")
    
    def _sci_fi_video_tab(self) -> None:
        """科幻视频生成标签页"""
        st.subheader("🚀 科幻视频生成")
        
        # 获取默认配置
        default_prompt = self.config["settings"]["sci_fi_video"]["default_prompt"]
        default_negative_prompt = self.config["settings"]["sci_fi_video"]["negative_prompt"]
        
        # 用户输入
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("上传图像", type=["png", "jpg", "jpeg"], key="sfv_file_uploader")
            prompt = st.text_area("提示词", value=default_prompt, height=150, key="sfv_prompt")
        with col2:
              output_filename = st.text_input("输出文件名", value="sci_fi_video.mp4", key="sfv_output_filename")

        if uploaded_file is not None:
            st.image(uploaded_file, caption="上传的图像", use_container_width=True)

        if st.button("生成科幻视频", key="sfv_generate_button"):
            if not uploaded_file:
                st.error("请先上传图像")
                return
            
            if not st.session_state.comfyui_path:
                st.error("请先配置ComfyUI路径")
                return
            
            try:
                with st.spinner("正在生成科幻视频..."):
                    # 保存上传的文件
                    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_image_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 调用科幻视频生成应用
                    success = st.session_state.app.generate_sci_fi_video(prompt, temp_image_path, output_filename)
                    
                if success:
                    st.success(f"科幻视频生成成功")
                    # 显示生成的视频
                    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
                    output_path = os.path.join(output_dir, output_filename)
                    if os.path.exists(output_path):
                        try:
                            st.video(output_path)
                        except:
                            st.info("无法显示结果视频")
                else:
                    st.error("科幻视频生成失败")
            except Exception as e:
                st.error(f"生成失败: {str(e)}")
    
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
            "古装图片生成", 
            "科幻视频生成"
        ])
        
        # 文生图标签页
        with tabs[0]:
            self._text_to_image_tab()
        
        # 图生图标签页
        with tabs[1]:
            self._image_to_image_tab()
        
        # 图生视频标签页
        with tabs[2]:
            self._image_to_video_tab()
        
        # 古装图片生成标签页
        with tabs[3]:
            self._ancient_clothing_tab()
        
        # 科幻视频生成标签页
        with tabs[4]:
            self._sci_fi_video_tab()

if __name__ == "__main__":
    # 创建并运行Web应用
    app = AIGCWebApp()
    app.run()
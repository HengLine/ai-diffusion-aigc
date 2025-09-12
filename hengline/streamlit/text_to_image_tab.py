#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文生图标签页模块
"""

import os
import sys
import streamlit as st
import time
from hengline.workflow.run_workflow import ComfyUIRunner
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import info, error, debug
# 导入配置工具
from hengline.utils.config_utils import get_task_settings, get_workflow_path, get_paths_config

class TextToImageTab:
    """文生图标签页类"""
    
    def __init__(self, runner: ComfyUIRunner):
        """初始化文生图标签页"""
        self.runner = runner
        
        # 从配置获取默认参数
        self.default_params = get_task_settings('text_to_image')
        
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    def render(self):
        """渲染文生图标签页"""
        debug("====== 进入[文生图]标签页 ======")
        st.subheader("文生图 (Text to Image)")
        
        # 创建表单
        with st.form("text_to_image_form"):
            # 输入区域
            prompt = st.text_area("提示词 (Prompt)", value=self.default_params.get('prompt', ''), 
                                placeholder="描述你想要生成的图像内容...")
            negative_prompt = st.text_area("负面提示词 (Negative Prompt)", 
                                         value=self.default_params.get('negative_prompt', ''),
                                         placeholder="描述你不想要在图像中出现的内容...")
            
            # 参数设置
            col1, col2 = st.columns(2)
            with col1:
                width = st.slider("宽度 (Width)", min_value=256, max_value=1536, 
                                value=self.default_params.get('width', 1024), step=64)
                height = st.slider("高度 (Height)", min_value=256, max_value=1536, 
                                 value=self.default_params.get('height', 1024), step=64)
            
            with col2:
                steps = st.slider("采样步数 (Steps)", min_value=1, max_value=100, 
                                value=self.default_params.get('steps', 30))
                cfg_scale = st.slider("CFG Scale", min_value=1.0, max_value=30.0, 
                                    value=float(self.default_params.get('cfg_scale', 8.0)), step=0.5)
            
            # 提交按钮
            generate_button = st.form_submit_button("✨ 生成图像")
        
        # 处理表单提交
        if generate_button:
            # 验证输入
            if not prompt:
                st.error("请输入提示词！")
                return
            
            # 显示加载状态
            with st.spinner("正在生成图像，请稍候..."):
                try:
                    # 加载工作流
                    workflow_file = get_workflow_path('text_to_image')
                    workflow_path = os.path.join(self.project_root, workflow_file)
                    workflow = self.runner.load_workflow(workflow_path)
                    
                    # 更新工作流参数
                    workflow = self.runner.update_workflow_params(
                        workflow, 
                        {
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "width": width,
                            "height": height,
                            "steps": steps,
                            "cfg_scale": cfg_scale
                        }
                    )
                    
                    # 运行工作流
                    output_filename = f"text_to_image_{int(time.time())}.png"
                    success = self.runner.run_workflow(
                        workflow, 
                        output_filename=output_filename
                    )
                    
                    # 显示结果
                    if success:
                        result_path = os.path.join(self.runner.output_dir, output_filename)
                        st.success("图像生成成功！")
                        st.image(result_path, caption=f"生成的图像: {prompt}")
                    else:
                        st.error("图像生成失败")
                except Exception as e:
                    import traceback
                    error_type = type(e).__name__
                    error_message = str(e)
                    error_traceback = traceback.format_exc()
                    error(f"文生图生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
                    st.error(f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息")
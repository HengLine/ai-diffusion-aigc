#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文生图标签页模块
"""

import sys
import streamlit as st
import os
from hengline.streamlit.components.carousel_component import CarouselComponent

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import debug
# 导入接口模块
from hengline.streamlit.interfaces.text_to_image_interface import TextToImageInterface

class TextToImageTab:
    """文生图标签页类"""
    
    def __init__(self, runner):
        """初始化文生图标签页"""
        self.runner = runner
        # 创建接口实例
        self.interface = TextToImageInterface(runner)
        
    def render(self):
        """渲染文生图标签页"""
        debug("====== 进入[文生图]标签页 ======")
        st.subheader("文生图 (Text to Image)")
        
        # 创建表单
        with st.form("text_to_image_form"):
            # 获取默认配置
            with st.expander("默认配置", expanded=False):
                st.write("当前使用的默认配置参数")
                st.json(self.interface.default_params)
            
            # 输入区域
            prompt = st.text_area("提示词 (Prompt) (描述你想要生成的图像内容)", value=self.interface.default_params.get('prompt', ''),
                                placeholder="描述你想要生成的图像内容...", height=150)
            negative_prompt = st.text_area("负面提示词 (Negative Prompt) (描述你不想要在图像中出现的内容)",
                                         value=self.interface.default_params.get('negative_prompt', ''),
                                         placeholder="描述你不想要在图像中出现的内容...", height=100)
            
            # 参数设置
            col1, col2 = st.columns(2)
            with col1:
                width = st.slider("宽度 (图像的宽度 (像素)，值过高会增加计算时间和内存消耗)", min_value=256, max_value=1024,
                                 value=self.interface.default_params.get('width', 512), step=64)
                height = st.slider("高度 (图像的高度 (像素)，值过高会增加计算时间和内存消耗)", min_value=256, max_value=1024,
                                  value=self.interface.default_params.get('height', 512), step=64)
                
            with col2:
                steps = st.slider("采样步数 (生成过程中的迭代步数，值过高会增加生成时间但效果提升有限)", min_value=1, max_value=50,
                                 value=self.interface.default_params.get('steps', 20), step=1)
                # 确保cfg值是浮点数，解决类型不匹配问题
                cfg_value = self.interface.default_params.get('cfg', 7.5)
                # 显式转换为float类型
                cfg_value = float(cfg_value)
                cfg = st.slider("CFG 权重 (控制生成内容与提示词的匹配程度，值过高会使内容过于贴近提示词而显得生硬)", min_value=1.0, max_value=15.0,
                               value=cfg_value, step=0.5)
                
            # 新增生成数量参数
            batch_size = st.slider("生成数量 (一次生成的图像数量，值过高会增加总生成时间)", min_value=1, max_value=20,
                                  value=self.interface.default_params.get('batch_size', 1), step=1)
            
            # 自动生成输出文件名
            import time
            output_filename = f"text_to_image_{int(time.time())}.png"
            
            # 提交按钮
            submit_button = st.form_submit_button("生成图像")
        
        # 处理表单提交
        if submit_button:
            try:
                with st.spinner("正在生成图像..."):
                    # 调用接口方法
                    result = self.interface.generate_image(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        steps=steps,
                        cfg=cfg,
                        output_filename=output_filename,
                        batch_size=batch_size
                    )
                    
                if result['success']:
                    st.success(result['message'])
                     
                    # 显示生成结果
                    with st.expander("生成结果"):
                        if 'output_paths' in result and len(result['output_paths']) > 0:
                            # 使用轮播组件显示多张图像
                            CarouselComponent.display_image_carousel(result['output_paths'], caption="生成结果")
                        elif result['output_path']:
                            # 兼容旧版返回格式
                            CarouselComponent.display_image_carousel([result['output_path']], caption="生成结果")
                else:
                    st.error(result['message'])
            except Exception as e:
                st.error(f"处理请求时发生错误: {str(e)}")
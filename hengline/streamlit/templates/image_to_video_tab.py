import os
import sys
import streamlit as st
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import debug, error
# 导入接口模块
from hengline.streamlit.interfaces.image_to_video_interface import ImageToVideoInterface
# 导入配置工具
from hengline.utils.config_utils import get_workflow_path, get_paths_config

class ImageToVideoTab:
    def __init__(self, runner):
        """初始化图生视频标签页"""
        self.runner = runner
        # 创建接口实例
        self.interface = ImageToVideoInterface(runner)
        # 设置项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    def render(self):
        """渲染图生视频标签页"""
        debug("====== 进入[图生视频]标签页 ======")
        st.subheader("图生视频 (Image to Video)")
        
        # 创建表单
        with st.form("image_to_video_form"):
            # 获取默认配置
            with st.expander("默认配置", expanded=False):
                st.write("当前使用的默认配置参数")
                st.json(self.interface.default_params)
            
            # 图像上传
            uploaded_file = st.file_uploader("上传图像", type=["jpg", "jpeg", "png", "webp"])
            
            # 输入区域
            prompt = st.text_area("提示词 (Prompt)", value=self.interface.default_params.get('prompt', ''),
                                placeholder="描述你想要生成的视频内容...", height=150)
            negative_prompt = st.text_area("负面提示词 (Negative Prompt)",
                                         value=self.interface.default_params.get('negative_prompt', ''),
                                         placeholder="描述你不想要在视频中出现的内容...", height=100)
            
            # 参数设置
            col1, col2 = st.columns(2)
            with col1:
                width = st.slider("宽度 (像素)", min_value=256, max_value=1024,
                                 value=self.interface.default_params.get('width', 512), step=64)
                height = st.slider("高度 (像素)", min_value=256, max_value=768,
                                  value=self.interface.default_params.get('height', 384), step=64)
                frames = st.slider("帧数", min_value=4, max_value=32,
                                 value=self.interface.default_params.get('frames', 16), step=1)
                output_filename = st.text_input("输出文件名",
                                              value=self.interface.default_params.get('output_filename', 'image_to_video.mp4'))
            
            with col2:
                fps = st.slider("帧率", min_value=4, max_value=30,
                              value=self.interface.default_params.get('fps', 8), step=1)
            
            # 提交按钮
            submit_button = st.form_submit_button("生成视频")
        
        # 显示上传的图像
        if uploaded_file is not None:
            st.image(uploaded_file, caption="上传的图像", use_container_width=True)
        
        # 处理表单提交
        if submit_button:
            try:
                with st.spinner("正在生成视频..."):
                    # 调用接口方法
                    result = self.interface.generate_video(
                        image_file=uploaded_file,
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        frames=frames,
                        fps=fps,
                        output_filename=output_filename
                    )
                
                if result['success']:
                    st.success(result['message'])
                    
                    # 显示生成的视频
                    if result['output_path'].lower().endswith('.mp4'):
                        try:
                            st.video(result['output_path'])
                        except Exception as e:
                            st.info(f"无法显示结果视频: {str(e)}")
                else:
                    st.error(result['message'])
            except Exception as e:
                st.error(f"处理请求时发生错误: {str(e)}")
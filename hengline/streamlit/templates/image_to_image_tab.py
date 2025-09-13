import os
import sys
import streamlit as st
import os
import tempfile
from PIL import Image
import base64
import time
from ..components.carousel_component import CarouselComponent

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import debug
# 导入接口模块
from hengline.streamlit.interfaces.image_to_image_interface import ImageToImageInterface

class ImageToImageTab:
    def __init__(self, runner):
        """初始化图生图标签页"""
        self.runner = runner
        # 创建接口实例
        self.interface = ImageToImageInterface(runner)
        
    def render(self):
        """渲染图生图标签页"""
        debug("====== 进入[图生图]标签页 ======")
        st.subheader("图生图 (Image to Image)")
        
        # 创建表单
        with st.form("image_to_image_form"):
            # 获取默认配置
            with st.expander("默认配置", expanded=False):
                st.write("当前使用的默认配置参数")
                st.json(self.interface.default_params)
            
            # 图像上传
            uploaded_file = st.file_uploader("上传图像", type=["jpg", "jpeg", "png", "webp"])
            
            # 输入区域
            prompt = st.text_area("提示词 (Prompt) (描述你想要生成的图像内容)", value=self.interface.default_params.get('prompt', ''),
                                placeholder="描述你想要生成的图像内容...", height=150)
            negative_prompt = st.text_area("负面提示词 (Negative Prompt) (描述你不想要在图像中出现的内容)",
                                         value=self.interface.default_params.get('negative_prompt', ''),
                                         placeholder="描述你不想要在图像中出现的内容...", height=100)
            
            # 参数设置 - 3行2列布局
            # 第一行
            row1_col1, row1_col2 = st.columns(2)
            with row1_col1:
                width = st.slider("宽度 (图像的宽度 (像素)，值过高会增加计算时间和内存消耗)", min_value=256, max_value=1024,
                                 value=self.interface.default_params.get('width', 512), step=64)
            with row1_col2:
                height = st.slider("高度 (图像的高度 (像素)，值过高会增加计算时间和内存消耗)", min_value=256, max_value=1024,
                                  value=self.interface.default_params.get('height', 512), step=64)
            
            # 第二行
            row2_col1, row2_col2 = st.columns(2)
            with row2_col1:
                steps = st.slider("采样步数 (生成过程中的迭代步数，值过高会增加生成时间但效果提升有限)", min_value=1, max_value=50,
                                 value=self.interface.default_params.get('steps', 20), step=1)
            with row2_col2:
                # 确保cfg值是浮点数，解决类型不匹配问题
                cfg_value = self.interface.default_params.get('cfg', 7.5)
                # 显式转换为float类型
                cfg_value = float(cfg_value)
                cfg = st.slider("CFG 权重 (控制生成内容与提示词的匹配程度，值过高会使内容过于贴近提示词而显得生硬)", min_value=1.0, max_value=15.0,
                               value=cfg_value, step=0.5)
            
            # 第三行
            row3_col1, row3_col2 = st.columns(2)
            with row3_col1:
                # 确保denoise值是浮点数，解决类型不匹配问题
                denoise_value = self.interface.default_params.get('denoise', 0.7)
                # 显式转换为float类型
                denoise_value = float(denoise_value)
                denoise = st.slider("去噪强度 (控制与原图的相似度，值越高越偏离原图，会导致生成内容完全脱离原图特征)", min_value=0.1, max_value=1.0,
                                               value=denoise_value, step=0.05)
            with row3_col2:
                batch_size = st.slider("生成数量 (一次生成的图像数量，值过高会增加总生成时间)", min_value=1, max_value=20,
                                  value=self.interface.default_params.get('batch_size', 1), step=1)
            
            # 自动生成输出文件名
            import time
            output_filename = f"image_to_image_{int(time.time())}.png"
            
            # 提交按钮
            submit_button = st.form_submit_button("生成变体")
        
        # 显示上传的图像
        if uploaded_file is not None:
            st.image(uploaded_file, caption="上传的图像", use_container_width=True)
        
        # 处理表单提交
        if submit_button:
            try:
                with st.spinner("正在生成变体..."):
                    # 调用接口方法
                    result = self.interface.generate_variant(
                        uploaded_file=uploaded_file,
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        steps=steps,
                        cfg=cfg,
                        denoise=denoise,
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
import os
import sys
import streamlit as st
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import debug
# 导入接口模块
from hengline.streamlit.interfaces.image_to_video_interface import ImageToVideoInterface

class ImageToVideoTab:
    def __init__(self, runner):
        """初始化图生视频标签页"""
        self.runner = runner
        # 创建接口实例
        self.interface = ImageToVideoInterface(runner)
        
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
            # 验证输入
            if not uploaded_file:
                st.error("请上传图像！")
                return
            if not prompt:
                st.error("请输入提示词！")
                return
            
            # 显示加载状态
            with st.spinner("正在生成视频，请稍候..."):
                try:
                    # 保存上传的文件到临时目录
                    temp_dir = os.path.join(self.project_root, get_paths_config()['temp_folder'])
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, uploaded_file.name)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 加载工作流
                    workflow_file = get_workflow_path('image_to_video')
                    workflow_path = os.path.join(self.project_root, workflow_file)
                    workflow = self.runner.load_workflow(workflow_path)
                    
                    # 更新工作流参数
                    workflow = self.runner.update_workflow_params(
                        workflow, 
                        {
                            "prompt": prompt,
                            "image_path": temp_path,
                            "width": width,
                            "height": height,
                            "video_length": video_length,
                            "steps": steps,
                            "cfg_scale": cfg_scale,
                            "motion_amount": motion_amount,
                            "fps": fps,
                            "consistency_scale": consistency_scale
                        }
                    )
                    
                    # 运行工作流
                    output_filename = f"image_to_video_{int(time.time())}.mp4"
                    success = self.runner.run_workflow(
                        workflow, 
                        output_filename=output_filename
                    )
                    
                    # 显示结果
                    if success:
                        result_path = os.path.join(self.runner.output_dir, output_filename)
                        st.success("视频生成成功！")
                        st.video(result_path)
                    else:
                        st.error("视频生成失败")
                except Exception as e:
                    import traceback
                    error_type = type(e).__name__
                    error_message = str(e)
                    error_traceback = traceback.format_exc()
                    error(f"图生视频生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
                    st.error(f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息")
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
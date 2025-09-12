import os
import sys
import streamlit as st
import time
from hengline.workflow.run_workflow import ComfyUIRunner

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import info, error, debug
# 导入配置工具
from hengline.utils.config_utils import get_task_settings, get_workflow_path, get_paths_config

class ImageToVideoTab:
    def __init__(self, runner: ComfyUIRunner):
        """初始化图生视频标签页"""
        self.runner = runner
        
        # 从配置获取默认参数
        self.default_params = get_task_settings('image_to_video')
        
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    def render(self):
        """渲染图生视频标签页"""
        debug("====== 进入[图生视频]标签页 ======")
        st.subheader("图生视频 (Image to Video)")
        
        # 创建表单
        with st.form("image_to_video_form"):
            # 图像上传
            uploaded_file = st.file_uploader("上传图像", type=["jpg", "jpeg", "png", "webp"])
            
            # 输入区域
            prompt = st.text_area("提示词 (Prompt)", value=self.default_params.get('prompt', ''),
                                placeholder="描述你想要生成的视频内容...")
            
            # 参数设置
            col1, col2 = st.columns(2)
            with col1:
                width = st.slider("宽度 (像素)", min_value=256, max_value=1024, 
                                 value=self.default_params.get('width', 512), step=64)
                height = st.slider("高度 (像素)", min_value=256, max_value=768, 
                                  value=self.default_params.get('height', 384), step=64)
                video_length = st.slider("视频长度 (帧数)", min_value=8, max_value=60, 
                                       value=self.default_params.get('video_length', 16), step=4)
                steps = st.slider("生成步数", min_value=1, max_value=50, 
                                 value=self.default_params.get('steps', 20), step=1)

            with col2:
                fps = st.slider("帧率 (FPS)", min_value=8, max_value=30, 
                              value=self.default_params.get('fps', 16))
                cfg_scale = st.slider("CFG Scale", min_value=0.1, max_value=20.0, 
                                    value=float(self.default_params.get('cfg', 1.0)), step=0.1)
                motion_amount = st.slider("运动强度", min_value=0.1, max_value=2.0, 
                                        value=float(self.default_params.get('motion_amount', 0.5)), step=0.1)
                consistency_scale = st.slider("一致性调整", min_value=0.1, max_value=2.0, 
                                          value=float(self.default_params.get('consistency_scale', 1.0)), step=0.1)
            
            # 提交按钮
            generate_button = st.form_submit_button("✨ 生成视频")
        
        # 处理表单提交
        if generate_button:
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
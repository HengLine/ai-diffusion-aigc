import os
import sys
import streamlit as st
import time
from hengline.workflow.run_workflow import ComfyUIRunner

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入自定义日志模块
from hengline.logger import info, error
# 导入配置工具
from hengline.utils.config_utils import get_task_settings, get_workflow_path

class TextToVideoTab:
    def __init__(self, runner: ComfyUIRunner):
        """初始化文生视频标签页"""
        self.runner = runner
        
        # 从配置获取默认参数
        self.default_params = get_task_settings('text_to_video')
        
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    def render(self):
        """渲染文生视频标签页"""
        info("====== 进入[文生视频]标签页 ======")
        st.subheader("文生视频 (Text to Video)")
        
        # 创建表单
        with st.form("text_to_video_form"):
            # 输入区域
            prompt = st.text_area("提示词 (Prompt)", 
                                value=self.default_params.get('prompt', ''),
                                placeholder="描述你想要生成的视频内容...")
            
            # 参数设置
            col1, col2 = st.columns(2)
            with col1:
                width = st.slider("宽度 (像素)", min_value=256, max_value=1024, 
                                 value=self.default_params.get('width', 576), step=64)
                height = st.slider("高度 (像素)", min_value=256, max_value=768, 
                                  value=self.default_params.get('height', 320), step=64)
                video_length = st.slider("视频长度 (帧数)", min_value=8, max_value=60, 
                                       value=self.default_params.get('frames', 16), step=4)
                steps = st.slider("生成步数", min_value=1, max_value=50, 
                                 value=self.default_params.get('steps', 20), step=1)

            with col2:
                fps = st.slider("帧率 (FPS)", min_value=8, max_value=30, 
                              value=self.default_params.get('fps', 16))
                cfg_scale = st.slider("CFG Scale", min_value=0.1, max_value=20.0, 
                                    value=float(self.default_params.get('cfg', 1.0)), step=0.1)
                motion_amount = st.slider("运动强度", min_value=0.1, max_value=2.0, 
                                        value=float(self.default_params.get('motion_bucket_id', 1.0)), step=0.1)
                noise_amount = st.slider("噪声强度", min_value=0.0, max_value=0.1, 
                                        value=float(self.default_params.get('noise_aug_strength', 0.02)), step=0.01)
            
            # 提交按钮
            generate_button = st.form_submit_button("✨ 生成视频")
        
        # 处理表单提交
        if generate_button:
            # 验证输入
            if not prompt:
                st.error("请输入提示词！")
                return
            
            # 显示加载状态
            with st.spinner("正在生成视频，请稍候..."):
                try:
                    # 加载工作流
                    workflow_file = get_workflow_path('text_to_video')
                    workflow_path = os.path.join(self.project_root, workflow_file)
                    
                    # 检查工作流文件是否存在
                    if not os.path.exists(workflow_path):
                        # 如果文生视频工作流不存在，使用图生视频工作流代替
                        workflow_file = get_workflow_path('image_to_video')
                        workflow_path = os.path.join(self.project_root, workflow_file)
                        
                        if not os.path.exists(workflow_path):
                            st.error(f"工作流文件不存在: {workflow_path}")
                            return
                    
                    workflow = self.runner.load_workflow(workflow_path)
                    
                    # 更新工作流参数
                    workflow = self.runner.update_workflow_params(
                        workflow, 
                        {
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "video_length": video_length,
                            "steps": steps,
                            "cfg_scale": cfg_scale,
                            "motion_bucket_id": motion_amount,
                            "fps": fps,
                            "noise_aug_strength": noise_amount
                        }
                    )
                    
                    # 运行工作流
                    output_filename = f"text_to_video_{int(time.time())}.mp4"
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
                    error(f"文生视频生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
                    st.error(f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息")
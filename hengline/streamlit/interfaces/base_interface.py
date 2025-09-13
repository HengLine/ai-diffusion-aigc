import os
import sys
from typing import Dict, Any, Optional
from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.logger import error, debug
from hengline.utils.config_utils import get_task_settings, get_workflow_path, get_paths_config

class BaseInterface:
    def __init__(self, runner: ComfyUIRunner, task_type: str):
        self.runner = runner
        self.task_type = task_type
        self.default_params = get_task_settings(task_type)
        # 使用四次os.path.dirname()指向项目根目录，而不是hengline目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
    def load_workflow(self) -> Optional[Dict[str, Any]]:
        """加载工作流文件"""
        try:
            workflow_file = get_workflow_path(self.task_type)
            # 标准化路径分隔符，确保在Windows系统上正确处理
            normalized_workflow_file = workflow_file.replace('/', os.path.sep)
            # 使用类中已定义的project_root属性构建正确的路径
            workflow_path = os.path.join(self.project_root, normalized_workflow_file)
            
            if not os.path.exists(workflow_path):
                error(f"工作流文件不存在: {workflow_path}")
                return None
            
            debug(f"加载工作流文件: {workflow_path}")
            return self.runner.load_workflow(workflow_path)
        except Exception as e:
            error(f"加载工作流失败: {str(e)}")
            return None
    
    def update_workflow_params(self, workflow: Dict[str, Any], params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新工作流参数"""
        try:
            debug(f"更新工作流参数: {params}")
            return self.runner.update_workflow_params(workflow, params)
        except Exception as e:
            error(f"更新工作流参数失败: {str(e)}")
            return None
    
    def run_workflow(self, workflow: Dict[str, Any], output_filename: str) -> bool:
        """运行工作流"""
        try:
            debug(f"运行工作流，输出文件名: {output_filename}")
            return self.runner.run_workflow(workflow, output_filename)
        except Exception as e:
            error(f"运行工作流失败: {str(e)}")
            return False
    
    def get_output_path(self, output_filename: str) -> str:
        """获取输出文件路径"""
        output_folder = get_paths_config().get("output_folder", "outputs")
        output_dir = os.path.join(self.project_root, output_folder)
        return os.path.join(output_dir, output_filename)
    
    def get_temp_image_path(self, uploaded_file) -> Optional[str]:
        """保存上传的图像文件并返回临时路径"""
        try:
            if not uploaded_file:
                return None
            
            temp_folder = get_paths_config().get("temp_folder", "temp")
            temp_dir = os.path.join(self.project_root, temp_folder)
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_image_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            return temp_image_path
        except Exception as e:
            error(f"保存上传图像失败: {str(e)}")
            return None
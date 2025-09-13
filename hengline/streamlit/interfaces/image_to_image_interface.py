from typing import Dict, Any, Optional
from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.logger import debug, error
from .base_interface import BaseInterface
from typing import Dict, Any

class ImageToImageInterface(BaseInterface):
    def __init__(self, runner: ComfyUIRunner):
        super().__init__(runner, 'image_to_image')
    
    def generate_variant(self, uploaded_file, prompt: str, negative_prompt: str, 
                        width: int, height: int, steps: int, cfg: float, 
                        denoise: float, output_filename: str, batch_size: int = 1) -> Dict[str, Any]:
        """生成图生图变体"""
        result = {
            'success': False,
            'message': '',
            'output_path': '',
            'output_paths': []  # 添加用于存储批量输出路径的字段
        }
        
        try:
            # 检查输入参数
            if not uploaded_file:
                result['message'] = "请先上传图像"
                return result
            
            if not prompt:
                result['message'] = "请输入提示词"
                return result
            
            # 保存上传的图像
            temp_image_path = self.get_temp_image_path(uploaded_file)
            if not temp_image_path:
                result['message'] = "保存上传图像失败"
                return result
            
            # 加载工作流
            workflow = self.load_workflow()
            if not workflow:
                result['message'] = "加载工作流失败"
                return result
            
            # 更新工作流参数
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "image_path": temp_image_path,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg": cfg,
                "denoise": denoise,
                "batch_size": batch_size
            }
            
            updated_workflow = self.update_workflow_params(workflow, params)
            if not updated_workflow:
                result['message'] = "更新工作流参数失败"
                return result
            
            # 运行工作流
            success = self.run_workflow(updated_workflow, output_filename)
            if not success:
                result['message'] = "运行工作流失败"
                return result
            
            # 获取输出路径
            output_path = self.get_output_path(output_filename)
            output_paths = self.get_batch_output_paths(output_filename, batch_size)
            
            # 更新结果
            result['success'] = True
            result['message'] = f"变体生成成功，共生成 {len(output_paths)} 个变体"
            result['output_path'] = output_path  # 保持向后兼容
            result['output_paths'] = output_paths  # 添加批量输出路径
            
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_message = str(e)
            error_traceback = traceback.format_exc()
            error(f"图生图生成异常: 类型={error_type}, 消息={error_message}\n堆栈跟踪:\n{error_traceback}")
            result['message'] = f"生成失败: 类型={error_type}, 消息={error_message}\n请查看控制台日志获取详细堆栈信息"
        
        return result
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行ComfyUI工作流的主脚本
"""

import os
import sys
import json
import argparse
import subprocess
import time
from typing import Dict, Any, Optional

class ComfyUIRunner:
    """ComfyUI工作流运行器类"""
    
    def __init__(self, comfyui_path: str, output_dir: str):
        """
        初始化ComfyUIRunner
        
        Args:
            comfyui_path: ComfyUI安装路径
            output_dir: 输出文件保存目录
        """
        self.comfyui_path = comfyui_path
        self.output_dir = output_dir
        self.api_url = "http://127.0.0.1:8188"
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def start_comfyui_server(self) -> subprocess.Popen:
        """启动ComfyUI服务器"""
        print(f"启动ComfyUI服务器...")
        
        # 根据操作系统选择启动命令
        if sys.platform == 'win32':
            cmd = ["python", "comfyui.exe"]
        else:
            cmd = ["python", "main.py"]
        
        # 在后台启动服务器
        process = subprocess.Popen(
            cmd,
            cwd=self.comfyui_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        time.sleep(5)
        print(f"ComfyUI服务器已启动")
        
        return process
    
    def stop_comfyui_server(self, process: subprocess.Popen) -> None:
        """停止ComfyUI服务器"""
        print(f"停止ComfyUI服务器...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print(f"ComfyUI服务器已停止")
    
    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """加载工作流文件"""
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        return workflow
    
    def update_workflow_params(self, workflow: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """更新工作流参数"""
        # 这里可以根据需要更新工作流中的各种参数
        # 例如提示词、负面提示词、模型选择等
        updated_workflow = workflow.copy()
        
        # 示例：更新提示词节点
        for node_id, node_data in updated_workflow.items():
            if isinstance(node_data, dict) and node_data.get('class_type') == 'CLIPTextEncode':
                if 'inputs' in node_data and 'text' in node_data['inputs']:
                    if 'prompt' in params:
                        updated_workflow[node_id]['inputs']['text'] = params['prompt']
            
            # 示例：更新负面提示词节点
            if isinstance(node_data, dict) and node_data.get('class_type') == 'CLIPTextEncodeNeg':
                if 'inputs' in node_data and 'text' in node_data['inputs']:
                    if 'negative_prompt' in params:
                        updated_workflow[node_id]['inputs']['text'] = params['negative_prompt']
        
        return updated_workflow
    
    def run_workflow(self, workflow: Dict[str, Any], output_filename: str) -> bool:
        """运行工作流并保存结果"""
        try:
            # 这里应该是与ComfyUI API交互的代码
            # 为了演示，我们先创建一个模拟结果
            print(f"运行工作流...")
            
            # 模拟处理时间
            time.sleep(2)
            
            # 创建一个模拟的输出文件
            output_path = os.path.join(self.output_dir, output_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"这是一个模拟的输出文件，对应工作流结果\n")
                f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
            print(f"工作流运行完成，结果保存至: {output_path}")
            return True
        except Exception as e:
            print(f"工作流运行失败: {str(e)}")
            return False

class AIGCApplication:
    """AIGC应用封装类"""
    
    def __init__(self, runner: ComfyUIRunner):
        """初始化AIGC应用"""
        self.runner = runner
    
    def generate_ancient_clothing(self, prompt: str, output_filename: str = "ancient_clothing.png") -> bool:
        """生成古装图片"""
        # 加载古装图片生成工作流
        workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   "workflows", "ancient_clothing_workflow.json")
        
        # 检查工作流文件是否存在
        if not os.path.exists(workflow_path):
            print(f"工作流文件不存在: {workflow_path}")
            return False
        
        # 加载工作流
        workflow = self.runner.load_workflow(workflow_path)
        
        # 更新工作流参数
        params = {
            "prompt": f"ancient Chinese clothing, {prompt}",
            "negative_prompt": "modern, low quality, blurry, bad anatomy"
        }
        updated_workflow = self.runner.update_workflow_params(workflow, params)
        
        # 运行工作流
        return self.runner.run_workflow(updated_workflow, output_filename)
    
    def generate_sci_fi_video(self, prompt: str, image_path: str, output_filename: str = "sci_fi_video.mp4") -> bool:
        """生成科幻视频"""
        # 加载科幻视频生成工作流
        workflow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   "workflows", "sci_fi_video_workflow.json")
        
        # 检查工作流文件是否存在
        if not os.path.exists(workflow_path):
            print(f"工作流文件不存在: {workflow_path}")
            return False
        
        # 加载工作流
        workflow = self.runner.load_workflow(workflow_path)
        
        # 更新工作流参数
        params = {
            "prompt": f"sci-fi scene, {prompt}",
            "negative_prompt": "low quality, blurry, unrealistic",
            "image_path": image_path
        }
        updated_workflow = self.runner.update_workflow_params(workflow, params)
        
        # 运行工作流
        return self.runner.run_workflow(updated_workflow, output_filename)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行ComfyUI工作流")
    parser.add_argument("--comfyui-path", type=str, required=True, help="ComfyUI安装路径")
    parser.add_argument("--workflow", type=str, help="工作流文件路径")
    parser.add_argument("--prompt", type=str, help="提示词")
    parser.add_argument("--output", type=str, default="output.png", help="输出文件名")
    parser.add_argument("--app", type=str, choices=["ancient_clothing", "sci_fi_video"], help="特定应用类型")
    parser.add_argument("--image-path", type=str, help="输入图像路径(用于图生图或图生视频)")
    
    args = parser.parse_args()
    
    # 初始化工作流运行器
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
    runner = ComfyUIRunner(args.comfyui_path, output_dir)
    
    # 启动ComfyUI服务器
    server_process = runner.start_comfyui_server()
    
    try:
        if args.app == "ancient_clothing":
            # 运行古装图片生成应用
            app = AIGCApplication(runner)
            app.generate_ancient_clothing(args.prompt, args.output)
        elif args.app == "sci_fi_video" and args.image_path:
            # 运行科幻视频生成应用
            app = AIGCApplication(runner)
            app.generate_sci_fi_video(args.prompt, args.image_path, args.output)
        elif args.workflow:
            # 运行指定的工作流
            workflow = runner.load_workflow(args.workflow)
            if args.prompt:
                workflow = runner.update_workflow_params(workflow, {"prompt": args.prompt})
            runner.run_workflow(workflow, args.output)
        else:
            print("请指定工作流文件或应用类型")
    finally:
        # 停止ComfyUI服务器
        runner.stop_comfyui_server(server_process)

if __name__ == "__main__":
    main()
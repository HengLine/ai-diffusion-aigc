#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行ComfyUI工作流的主脚本
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Any

import requests

from hengline.logger import debug, info, error, warning
from hengline.workflow.workflow_comfyui import comfyui_api

# 添加scripts目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class ComfyUIRunner:
    """ComfyUI工作流运行器类"""

    def __init__(self, output_dir: str, api_url: str = "http://127.0.0.1:8188"):
        """
        初始化ComfyUIRunner
        
        Args:
            output_dir: 输出文件保存目录
            api_url: ComfyUI API URL地址，默认为http://127.0.0.1:8188
        """
        self.output_dir = output_dir
        self.api_url = api_url

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """加载工作流文件并转换节点属性格式"""
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # 处理不同格式的工作流文件
        # 格式1: 根对象包含nodes数组
        if "nodes" in workflow:
            for node in workflow["nodes"]:
                if "type" in node and "class_type" not in node:
                    # 添加class_type属性，值与type相同
                    node["class_type"] = node["type"]
            return workflow

        # 格式2: 根对象包含prompt键（ComfyUI导出的完整工作流格式）
        elif "prompt" in workflow:
            # 转换为update_workflow_params方法期望的格式
            nodes = []
            for node_id, node_data in workflow["prompt"].items():
                # 确保节点有id属性
                if "id" not in node_data:
                    node_data["id"] = int(node_id) if node_id.isdigit() else node_id
                # 确保节点有type属性，如果没有则使用class_type
                if "type" not in node_data and "class_type" in node_data:
                    node_data["type"] = node_data["class_type"]
                nodes.append(node_data)
            return {"nodes": nodes}

        # 如果都不是上述格式，则尝试直接返回（可能需要进一步处理）
        return workflow


    def update_workflow_params(self, workflow: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """更新工作流参数"""
        # 使用深拷贝来确保所有属性都被正确保留
        import copy
        updated_workflow = copy.deepcopy(workflow)

        # 标记是否已经处理了正向提示词
        positive_prompt_processed = False

        # 优先处理原始格式：直接在prompt节点下更新参数
        if "prompt" in updated_workflow:
            for node_id, node_data in updated_workflow["prompt"].items():
                if "inputs" in node_data:
                    self._update_node_inputs(node_data, params, positive_prompt_processed)
                    # 检查是否处理了正向提示词
                    if node_data.get("class_type") == "CLIPTextEncode" and "text" in node_data["inputs"]:
                        if "prompt" in params and node_data["inputs"]["text"] == params["prompt"]:
                            positive_prompt_processed = True

        # 保持兼容性：继续支持nodes数组格式
        elif "nodes" in updated_workflow:
            # 遍历工作流中的所有节点
            for node_data in updated_workflow["nodes"]:
                # 确保节点有class_type属性，如果没有则从type属性复制
                if "type" in node_data and "class_type" not in node_data:
                    node_data["class_type"] = node_data["type"]

                if "inputs" in node_data:
                    self._update_node_inputs(node_data, params, positive_prompt_processed)
                    # 检查是否处理了正向提示词
                    if node_data.get("class_type") == "CLIPTextEncode" and "text" in node_data["inputs"]:
                        if "prompt" in params and node_data["inputs"]["text"] == params["prompt"]:
                            positive_prompt_processed = True

        debug(f"工作流参数已更新: {params}")
        return updated_workflow
        
    def _update_node_inputs(self, node_data: Dict[str, Any], params: Dict[str, Any], positive_prompt_processed: bool) -> None:
        """
        更新节点的输入参数
        
        Args:
            node_data: 节点数据
            params: 要更新的参数
            positive_prompt_processed: 是否已经处理了正向提示词
        """
        class_type = node_data.get("class_type", node_data.get("type", ""))
        inputs = node_data["inputs"]
        
        # 特殊处理提示词节点 (CLIPTextEncode)
        if class_type == "CLIPTextEncode" and "text" in inputs:
            # 处理正向提示词节点（通常是第一个CLIPTextEncode）
            if not positive_prompt_processed and "prompt" in params:
                # 直接使用原始提示词，确保完全保留所有空格、换行符和格式
                inputs["text"] = params["prompt"]
            # 处理反向提示词节点（通常是第二个CLIPTextEncode）
            elif "negative_prompt" in params:
                # 直接使用原始反向提示词，确保完全保留所有空格、换行符和格式
                inputs["text"] = params["negative_prompt"]
        
        # 特殊处理图像到视频节点 (WanImageToVideo)
        elif class_type == "WanImageToVideo":
            # 确保宽度、高度和批量大小参数能够正确更新
            if "width" in params:
                inputs["width"] = params["width"]
            if "height" in params:
                inputs["height"] = params["height"]
            if "batch_size" in params:
                inputs["batch_size"] = params["batch_size"]
        
        # 特殊处理图像缩放节点 (ImageScaleToTotalPixels) - 用于图生图
        # elif class_type == "ImageScaleToTotalPixels":
        #     # 确保宽度、高度参数能够正确更新
        #     if "width" in params and "height" in params:
        #         # 计算总像素数 (width * height) 并转换为百万像素 (除以1,000,000)
        #         total_pixels = params["width"] * params["height"]
        #         megapixels = total_pixels / 1000000
        #         if "megapixels" in inputs:
        #             inputs["megapixels"] = megapixels

            
        # 对于其他节点类型，动态更新所有匹配的参数
        for param_name, param_value in params.items():
            # 跳过特殊处理过的参数
            # if param_name in ["prompt", "negative_prompt", "width", "height", "batch_size"]:
            if param_name in ["prompt", "negative_prompt"]:
                continue
            
            # 处理参数名称映射（如cfg和cfg_scale可能指向同一个属性）
            if param_name == "denoise" and "denoise" in inputs:
                inputs["denoise"] = param_value
            elif param_name == "image_path" and "image" in inputs and class_type == "LoadImage":
                inputs["image"] = param_value
            # 直接更新节点输入中存在的参数
            elif param_name in inputs:
                inputs[param_name] = param_value

    def run_workflow(self, workflow: Dict[str, Any], output_filename: str) -> bool:
        """运行工作流并保存结果"""
        try:
            info(f"运行工作流...")
            debug(f"--------工作流数据: {workflow}")

            # 确保ComfyUI服务器正在运行
            server_running = self._check_server_running()
            if not server_running:
                debug("ComfyUI服务器未运行，请手动启动后再试...")

                if not self._check_server_running():
                    error("无法连接到ComfyUI服务器，请确保服务器已启动")
                    return False

            # 统一使用requests库，不使用httpx，避免混乱
            debug("ComfyUI服务器连接成功")

            # 将工作流转换为ComfyUI API期望的格式
            # 检查是否已经是正确的格式，如果不是则转换
            comfyui_workflow = {}

            if "nodes" in workflow:
                # 转换格式：将nodes数组转换为以节点ID为键的字典
                for node in workflow["nodes"]:
                    # 确保节点有class_type属性
                    if "type" in node and "class_type" not in node:
                        node["class_type"] = node["type"]
                        debug(f"为节点 {node.get('id', 'unknown')} 添加了class_type属性")

                    # 获取节点ID并确保它是字符串类型
                    node_id = str(node["id"])  # 确保节点ID是字符串
                    comfyui_workflow[node_id] = node
            else:
                # 已经是正确的格式，直接使用
                comfyui_workflow = workflow

            # 确保comfyui_workflow是有效的
            if not comfyui_workflow:
                error("转换后的工作流为空")
                return {"success": False, "message": "转换后的工作流为空"}

            info(f"准备发送工作流到ComfyUI API. comfyui_workflow: {comfyui_workflow}")
            # 发送工作流到ComfyUI API
            prompt_data = {
                "prompt": comfyui_workflow,
                "client_id": f"hengline-aigc"
            }

            # 发送POST请求运行工作流
            info(f"正在向 {self.api_url}/prompt 发送请求...")
            
            try:
                response = requests.post(f"{self.api_url}/prompt", json=prompt_data, timeout=30)
            except requests.exceptions.Timeout:
                error("向ComfyUI API发送请求超时")
                return {"success": False, "message": "向ComfyUI API发送请求超时"}
            except requests.exceptions.ConnectionError:
                error("无法连接到ComfyUI API")
                return {"success": False, "message": "无法连接到ComfyUI API"}

            if response.status_code != 200:
                error(f"API请求失败: {response.status_code}, {response.text}")
                return {"success": False, "message": f"API请求失败: {response.status_code}"}

            # 获取prompt_id
            try:
                response_json = response.json()
                # 确保response_json是字典类型
                if not isinstance(response_json, dict):
                    error(f"API响应不是字典类型，而是: {type(response_json)}")
                    return {"success": False, "message": f"API响应不是字典类型，而是: {type(response_json)}"}

                prompt_id = response_json.get("prompt_id")
                if not prompt_id:
                    error(f"无法获取prompt_id，响应内容: {response_json}")
                    return {"success": False, "message": "无法获取prompt_id"}

                debug(f"工作流已提交，prompt_id: {prompt_id}")
            except ValueError:
                error("解析API响应JSON失败")
                return {"success": False, "message": "解析API响应JSON失败"}

            # 等待工作流完成
            workflow_completed = comfyui_api.wait_for_workflow_completion(prompt_id)
            if not workflow_completed:
                error(f"工作流执行失败: 等待工作流完成超时或连接失败")
                return {"success": False, "message": "工作流执行失败: 等待工作流完成超时或连接失败"}

            # 获取工作流结果
            # 检查output_filename是否已经是完整路径
            if os.path.isabs(output_filename):
                # 如果是完整路径，直接使用
                output_path = output_filename
            else:
                # 否则使用output_dir构建路径
                output_path = os.path.join(self.output_dir, output_filename)
            
            # 确保输出目录存在
            # output_dir = os.path.dirname(output_path)
            # os.makedirs(output_dir, exist_ok=True)
            
            success, saved_file_paths = self._get_workflow_outputs(prompt_id, output_path)

            if success:
                debug(f"工作流运行完成，结果保存至: {saved_file_paths}")
                
                # 处理多输出文件的特殊情况：检查文件名（带有索引后缀）的文件是否存在
                # 当只请求一个文件但实际返回多个文件时，原始文件名可能不存在，但带索引的文件存在
                if saved_file_paths and len(saved_file_paths) > 0:
                    # 创建一个临时列表，包含原始文件名和所有可能的索引变体
                    all_possible_paths = set(saved_file_paths)
                    
                    # 检查是否至少有一个文件存在
                    if any(os.path.exists(path) for path in all_possible_paths):
                        # 返回成功状态和实际保存的文件路径列表
                        return {"success": True, "output_paths": saved_file_paths}
                    else:
                        warning(f"工作流运行成功但所有输出文件不存在: {saved_file_paths}")
                        return {"success": False, "message": "工作流运行成功但所有输出文件不存在"}
                else:
                    warning("工作流运行成功但未返回任何文件路径")
                    return {"success": False, "message": "工作流运行成功但未返回任何文件路径"}
            else:
                error("无法获取工作流结果")
                return {"success": False, "message": "无法获取工作流结果"}
        except Exception as e:
                error(f"工作流运行失败: {str(e)}")
                # 添加堆栈跟踪以帮助调试
                import traceback
                debug(f"异常详情: {traceback.format_exc()}")
                return {"success": False, "message": f"工作流运行失败: {str(e)}"}

    def _check_server_running(self) -> bool:
        """检查ComfyUI服务器是否正在运行"""
        try:
            response = requests.get(f"{self.api_url}/system_stats", timeout=3)
            return response.status_code == 200
        except:
            return False


    @staticmethod
    def _get_workflow_outputs(prompt_id: str, output_path: str) -> tuple[bool, list[str]]:
        """
        获取工作流的输出结果
        
        Args:
            prompt_id: 工作流的prompt_id
            output_path: 输出文件保存路径
        
        Returns:
            tuple[bool, list[str]]: (是否成功获取并保存输出结果, 保存的文件路径列表)
        """
        try:
            # 使用ComfyUIApi获取工作流输出（现在直接返回保存的文件路径列表）
            success, saved_file_paths = comfyui_api.get_workflow_outputs(prompt_id, output_path)
            
            # 验证返回的文件路径列表是否有效
            if success and saved_file_paths:
                # 确保所有文件路径都存在
                valid_file_paths = []
                for file_path in saved_file_paths:
                    if os.path.exists(file_path):
                        valid_file_paths.append(file_path)
                    else:
                        warning(f"保存的文件路径不存在: {file_path}")
                
                # 如果没有有效的文件路径，则返回失败
                if not valid_file_paths:
                    error(f"没有找到有效的输出文件")
                    return False, []
                
                return True, valid_file_paths
            elif success and not saved_file_paths:
                # 如果返回成功但文件路径列表为空，尝试检查默认路径
                warning(f"ComfyUIApi返回成功但文件路径列表为空，尝试检查默认路径")
                valid_file_paths = []
                if os.path.exists(output_path):
                    valid_file_paths.append(output_path)
                    
                # 检查是否有多个输出文件（带索引的文件）
                base_name, ext = os.path.splitext(output_path)
                idx = 1
                while True:
                    multi_output_path = f"{base_name}_{idx}{ext}"
                    if os.path.exists(multi_output_path):
                        valid_file_paths.append(multi_output_path)
                        idx += 1
                    else:
                        break
                
                return len(valid_file_paths) > 0, valid_file_paths
            
            return False, []
        except Exception as e:
            error(f"获取工作流输出时出错: {str(e)}")
            return False, []


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行ComfyUI工作流")
    parser.add_argument("--workflow", type=str, help="工作流文件路径")
    parser.add_argument("--prompt", type=str, help="提示词")
    parser.add_argument("--output", type=str, default="output.png", help="输出文件名")
    parser.add_argument("--image-path", type=str, help="输入图像路径(用于图生图或图生视频)")
    parser.add_argument("--api-url", type=str, default="http://127.0.0.1:8188", help="ComfyUI API URL地址")

    args = parser.parse_args()

    # 加载配置文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 从配置文件中获取输出目录配置
    output_folder = config.get("paths", {}).get("output_folder", "outputs")

    # 初始化工作流运行器 - 设置输出目录到项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, output_folder)
    runner = ComfyUIRunner(output_dir, args.api_url)

    try:
        if args.workflow:
            # 运行指定的工作流
            workflow = runner.load_workflow(args.workflow)
            if args.prompt:
                workflow = runner.update_workflow_params(workflow, {"prompt": args.prompt})
            if args.image_path:
                workflow = runner.update_workflow_params(workflow, {"image_path": args.image_path})
            runner.run_workflow(workflow, args.output)
        else:
            warning("请指定工作流文件")
    finally:
        pass


if __name__ == "__main__":
    main()

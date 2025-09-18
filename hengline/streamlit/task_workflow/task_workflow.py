#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行ComfyUI工作流的主脚本
"""
import json
import os
import sys
from typing import Dict, Any

import requests

from hengline.logger import debug, info, error, warning
from hengline.utils.config_utils import get_task_config
from hengline.workflow.workflow_comfyui import comfyui_api

# 添加scripts目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class ComfyUIRunnerManager:
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
        self.task_timeout_seconds = get_task_config().get('task_timeout_seconds', 1800)
        self.task_view_timeout_seconds = get_task_config().get('task_view_timeout_seconds', 200)

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def run_workflow(self, workflow: Dict[str, Any], output_filename: str) -> json:
        """运行工作流并保存结果（同步版本，保持向后兼容）"""
        try:
            info(f"运行工作流...")

            # 确保ComfyUI服务器正在运行
            server_running = comfyui_api.check_server_status()
            if not server_running:
                error("无法连接到ComfyUI服务器，请确保服务器已启动")
                return False

            debug("ComfyUI服务器连接成功")

            # 将工作流转换为ComfyUI API期望的格式
            comfyui_workflow = {}

            if "nodes" in workflow:
                # 转换格式：将nodes数组转换为以节点ID为键的字典
                for node in workflow["nodes"]:
                    # 确保节点有class_type属性
                    if "type" in node and "class_type" not in node:
                        node["class_type"] = node["type"]

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

            info(f"准备发送工作流到ComfyUI API. comfyui_workflow= {comfyui_workflow}")
            # 发送工作流到ComfyUI API
            prompt_data = {
                "prompt": comfyui_workflow,
                "client_id": "hengline-aigc"
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

            # 等待工作流完成 - 使用新的异步检查但保持同步接口
            workflow_completed = comfyui_api.wait_for_workflow_completion(prompt_id, output_filename)
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

            success, saved_file_paths = comfyui_api.get_workflow_outputs(prompt_id, output_path)

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

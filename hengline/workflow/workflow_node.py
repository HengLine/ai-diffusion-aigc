#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行ComfyUI工作流的主脚本
"""

import json
import os
import sys
from typing import Dict, Any, Optional

from hengline.logger import debug, warning, info

# 添加scripts目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def load_workflow(workflow_path: str) -> Dict[str, Any]:
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
    if "prompt" not in workflow:
        raise ValueError("工作流文件格式不正确，缺少 'prompt' 键")

    # 如果都不是上述格式，则尝试直接返回（可能需要进一步处理）
    return workflow


def update_workflow_params(workflow: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
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
                update_node_inputs(node_data, params, positive_prompt_processed)
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
                update_node_inputs(node_data, params, positive_prompt_processed)
                # 检查是否处理了正向提示词
                if node_data.get("class_type") == "CLIPTextEncode" and "text" in node_data["inputs"]:
                    if "prompt" in params and node_data["inputs"]["text"] == params["prompt"]:
                        positive_prompt_processed = True

    info(f"工作流参数已更新: {params}")
    return updated_workflow


def fill_image_in_workflow(workflow: Dict[str, Any], image_filename: str, node_id: Optional[str] = None) -> \
        Dict[str, Any]:
    """
    将上传的图片文件名填充到工作流中的图片节点

    Args:
        workflow: 工作流数据
        image_filename: ComfyUI服务器上的图片文件名
        node_id: 要填充的节点ID，如果为None则自动查找LoadImage节点

    Returns:
        Dict[str, Any]: 更新后的工作流数据
    """
    # 使用深拷贝避免修改原始工作流
    import copy
    updated_workflow = copy.deepcopy(workflow)

    # 检查工作流格式并填充图片文件名
    if "prompt" in updated_workflow:
        # 处理ComfyUI导出的完整工作流格式
        if node_id:
            # 指定节点ID
            if node_id in updated_workflow["prompt"]:
                node = updated_workflow["prompt"][node_id]
                if node.get("class_type") == "LoadImage" and "inputs" in node:
                    node["inputs"]["image"] = image_filename
                    debug(f"已填充图片文件名到节点 {node_id}")
                else:
                    warning(f"节点 {node_id} 不是LoadImage节点")
            else:
                warning(f"未找到节点 {node_id}")
        else:
            # 自动查找LoadImage节点
            for nid, node in updated_workflow["prompt"].items():
                if node.get("class_type") == "LoadImage" and "inputs" in node:
                    node["inputs"]["image"] = image_filename
                    debug(f"已填充图片文件名到节点 {nid}")
                    # 只填充第一个找到的LoadImage节点
                    break
    elif "nodes" in updated_workflow:
        # 处理nodes数组格式
        if node_id:
            # 指定节点ID
            for node in updated_workflow["nodes"]:
                if str(node.get("id")) == node_id:
                    if node.get("class_type") == "LoadImage" and "inputs" in node:
                        node["inputs"]["image"] = image_filename
                        debug(f"已填充图片文件名到节点 {node_id}")
                    else:
                        warning(f"节点 {node_id} 不是LoadImage节点")
                    break
            else:
                warning(f"未找到节点 {node_id}")
        else:
            # 自动查找LoadImage节点
            for node in updated_workflow["nodes"]:
                if node.get("class_type") == "LoadImage" and "inputs" in node:
                    node["inputs"]["image"] = image_filename
                    debug(f"已填充图片文件名到节点 {node.get('id', 'unknown')}")
                    # 只填充第一个找到的LoadImage节点
                    break

    return updated_workflow


def update_node_inputs(node_data: Dict[str, Any], params: Dict[str, Any],
                       positive_prompt_processed: bool) -> None:
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

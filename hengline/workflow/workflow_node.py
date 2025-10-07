#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: workflow_node.py
@Description: 工作流节点处理模块，提供工作流文件加载、节点参数更新等功能
@Author: HengLine
@Time: 2025/08 - 2025/11
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


import uuid

def wrap_workflow_for_comfyui(workflow_nodes: Dict[str, Any]) -> Dict[str, Any]:
    """
    包装工作流以符合ComfyUI API的要求格式
    
    Args:
        workflow_nodes: 工作流节点数据
        
    Returns:
        Dict[str, Any]: 包装后的完整工作流结构，包含client_id、prompt和extra_data
    """
    # 检查工作流格式并转换为正确的prompt结构
    prompt_nodes = {}
    
    # 如果workflow_nodes已经包含client_id、prompt等完整结构，直接返回
    if isinstance(workflow_nodes, dict) and "client_id" in workflow_nodes and "prompt" in workflow_nodes:
        debug("工作流已经是完整格式，无需转换")
        return workflow_nodes
    
    # 处理已经是正确prompt节点格式的工作流（如用户提供的示例格式）
    if isinstance(workflow_nodes, dict):
        prompt_nodes = convert_comfyui_visual_to_executable(workflow_nodes)

    # 如果无法识别格式或转换后prompt_nodes为空，尝试使用原始工作流
    if not prompt_nodes and isinstance(workflow_nodes, dict):
        prompt_nodes = workflow_nodes
    
    # 构建完整的工作流结构
    wrapped_workflow = {
        "client_id": str(uuid.uuid4()),
        "prompt": prompt_nodes,
        "extra_data": {
            "extra_pnginfo": {
                "workflow": workflow_nodes
            }
        }
    }
    
    debug(f"已包装工作流，包含 {len(prompt_nodes)} 个节点")
    return wrapped_workflow



# 预定义常见节点的 widget 参数名（按 widgets_values 顺序）
NODE_WIDGET_MAPPINGS = {
    # === 图像生成 ===
    "KSampler": ["seed", "control_after_generate", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
    "KSamplerAdvanced": ["add_noise", "noise_seed", "control_after_generate", "steps", "cfg", "sampler_name", "scheduler", "start_at_step", "end_at_step",
                         "return_with_leftover_noise", "model"],
    "EmptyLatentImage": ["width", "height", "batch_size"],
    "CLIPTextEncode": ["text"],
    "CheckpointLoaderSimple": ["ckpt_name"],
    "VAEDecode": [],
    "VAEEncode": [],
    "SaveImage": ["filename_prefix"],
    "PreviewImage": [],

    # === ControlNet ===
    "ControlNetLoader": ["control_net_name"],
    "ControlNetApply": ["strength"],
    "ControlNetApplyAdvanced": ["strength", "start_percent", "end_percent"],

    # === IPAdapter ===
    "IPAdapterModelLoader": ["ipadapter_file"],
    "IPAdapterClipVisionLoader": ["clip_name"],
    "IPAdapterApply": ["weight", "noise"],
    "IPAdapterApplyEncoded": ["weight", "noise"],
    "IPAdapterEncoder": ["weight", "noise"],

    # === AnimateDiff (视频) ===
    "AnimateDiffLoaderV1": ["model_name", "beta_schedule", "motion_scale", "apply_v2_models_properly"],
    "AnimateDiffUniformContextOptions": ["context_length", "context_stride", "context_overlap", "closed_loop"],
    "AnimateDiffSampler": ["noise_type", "seed"],

    # === 音频 (ComfyUI-Audio) ===
    "LoadAudio": ["audio_file"],
    "SaveAudio": ["filename_prefix", "format"],
    "AudioToMelSpectrogram": ["n_mels", "hop_length"],

    # === 视频 (ComfyUI-VideoHelperSuite) ===
    "VHS_VideoCombine": ["frame_rate", "loop_count", "filename_prefix", "format", "pix_fmt", "quality"],
    "VHS_LoadVideo": ["video"],
    "VHS_LoadImages": ["directory", "image_load_cap", "skip_first_images", "select_every_nth"],

    # === 3D / Mesh ===
    "LoadMesh": ["mesh_file"],
    "SaveMesh": ["filename_prefix"],

    # === 其他常用 ===
    "ImageScale": ["upscale_method", "width", "height", "crop"],
    "ImageScaleBy": ["upscale_method", "scale_by"],
    "LoraLoader": ["lora_name", "strength_model", "strength_clip"],
    "VAELoader": ["vae_name"],
    "CLIPLoader": ["clip_name"],
    "ConditioningZeroOut": [],
    "ConditioningSetArea": ["width", "height", "x", "y", "strength"],
    "ConditioningSetMask": ["strength", "set_cond_area"],
    "FreeU_V2": ["b1", "b2", "s1", "s2"],
    "Reroute": [],  # 透传节点
}

"""根据节点类型转换"""
def convert_comfyui_visual_to_executable(visual_workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 ComfyUI 可视化工作流 (含 nodes/links) 转换为可执行的 prompt JSON
    支持图像、视频、音频、文本、ControlNet、AnimateDiff、IPAdapter 等常见节点
    """
    nodes = visual_workflow.get("nodes", [])
    links = visual_workflow.get("links", [])

    # 构建连接映射: (to_node_id, to_input_index) -> (from_node_id, from_output_index)
    link_map = {}
    for link in links:
        # link = [link_id, from_node_id, from_output_idx, to_node_id, to_input_idx, type]
        _, from_id, from_out_idx, to_id, to_in_idx, _ = link
        link_map[(to_id, to_in_idx)] = (from_id, from_out_idx)

    executable = {}

    for node in nodes:
        node_id = str(node["id"])
        node_type = node["type"]
        widgets = node.get("widgets_values", [])
        inputs_list = node.get("inputs", [])
        input_names = [inp["name"] for inp in inputs_list]

        inputs_dict = {}
        # ==============================
        # 特殊处理：KSampler 及其变体
        # ==============================
        if node_type in ["KSampler", "KSamplerSelect", "KSamplerAdvanced"]:
            if node_type == "KSampler":
                if len(widgets) >= 7:
                    inputs_dict.update({
                        "seed": widgets[0],
                        "control_after_generate": widgets[1],  # ← 关键！不要丢
                        "steps": widgets[2],
                        "cfg": widgets[3],
                        "sampler_name": widgets[4],
                        "scheduler": widgets[5],
                        "denoise": widgets[6]
                    })
                # 处理连接输入（model, positive, negative, latent_image）
                for idx, inp in enumerate(inputs_list):
                    if (node["id"], idx) in link_map:
                        from_id, from_out = link_map[(node["id"], idx)]
                        inputs_dict[inp["name"]] = [str(from_id), from_out]

            elif node_type == "KSamplerAdvanced":
                # 类似处理，参数更多
                pass  # 可按需扩展

        # ==============================
        # 其他节点：通用逻辑
        # ==============================
        else:
            # 1. 处理连接
            for idx, inp in enumerate(inputs_list):
                if (node["id"], idx) in link_map:
                    from_id, from_out = link_map[(node["id"], idx)]
                    inputs_dict[inp["name"]] = [str(from_id), from_out]

            # 2. 处理 widgets（按 NODE_WIDGET_MAPPINGS）
            if node_type in NODE_WIDGET_MAPPINGS:
                widget_names = NODE_WIDGET_MAPPINGS[node_type]
                # 将 widgets 按顺序映射到 widget_names
                for i, name in enumerate(widget_names):
                    if i < len(widgets):
                        inputs_dict[name] = widgets[i]
            else:
                # 未知节点：保守处理
                for i, w in enumerate(widgets):
                    if i < len(inputs_list):
                        if inputs_list[i]["name"] not in inputs_dict:
                            inputs_dict[inputs_list[i]["name"]] = w
                    else:
                        inputs_dict[f"param_{i}"] = w

        executable[node_id] = {
            "class_type": node_type,
            "inputs": inputs_dict
        }

    return executable
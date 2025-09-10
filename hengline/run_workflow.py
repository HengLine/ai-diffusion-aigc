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
import uuid

import requests
import traceback
from hengline.utils.logger import debug, info, error
from hengline.utils.config_utils import config
from typing import Dict, Any, Optional

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
                    # 处理提示词节点 (CLIPTextEncode)
                    if node_data.get("class_type") == "CLIPTextEncode":
                        if "text" in node_data["inputs"]:
                            # 处理正向提示词节点（通常是第一个CLIPTextEncode）
                            if not positive_prompt_processed and "prompt" in params:
                                node_data["inputs"]["text"] = params["prompt"]
                                positive_prompt_processed = True
                            # 处理反向提示词节点（通常是第二个CLIPTextEncode）
                            elif "negative_prompt" in params:
                                node_data["inputs"]["text"] = params["negative_prompt"]
                    
                    # 处理采样器节点 (KSampler)
                    elif node_data.get("class_type") == "KSampler":
                        if "steps" in params and "steps" in node_data["inputs"]:
                            node_data["inputs"]["steps"] = params["steps"]
                        # 支持两种参数名：cfg和cfg_scale
                        if ("cfg" in params or "cfg_scale" in params) and "cfg" in node_data["inputs"]:
                            node_data["inputs"]["cfg"] = params.get("cfg_scale", params.get("cfg"))
                        if "denoise" in node_data["inputs"] and ("denoising_strength" in params or "denoise" in params):
                            node_data["inputs"]["denoise"] = params.get("denoising_strength", params.get("denoise"))
                    
                    # 处理图像大小节点 (EmptyLatentImage)
                    elif node_data.get("class_type") == "EmptyLatentImage":
                        if "width" in params and "width" in node_data["inputs"]:
                            node_data["inputs"]["width"] = params["width"]
                        if "height" in params and "height" in node_data["inputs"]:
                            node_data["inputs"]["height"] = params["height"]
                    
                    # 处理图像加载节点 (LoadImage)  
                    elif node_data.get("class_type") == "LoadImage" and "image_path" in params:
                        if "image" in node_data["inputs"]:
                            node_data["inputs"]["image"] = params["image_path"]
                    
                    # 处理通用的Denoise强度参数
                    elif "denoising_strength" in params and "denoising_strength" in node_data.get("inputs", {}):
                        node_data["inputs"]["denoising_strength"] = params["denoising_strength"]
        
        # 保持兼容性：继续支持nodes数组格式
        elif "nodes" in updated_workflow:
            # 遍历工作流中的所有节点
            for node_data in updated_workflow["nodes"]:
                # 确保节点有class_type属性，如果没有则从type属性复制
                if "type" in node_data and "class_type" not in node_data:
                    node_data["class_type"] = node_data["type"]
                
                if "type" in node_data and "inputs" in node_data:
                    # 处理提示词节点 (CLIPTextEncode)
                    if node_data["type"] == "CLIPTextEncode":
                        if "text" in node_data["inputs"]:
                            # 处理正向提示词节点（通常是第一个CLIPTextEncode）
                            if not positive_prompt_processed and "prompt" in params:
                                node_data["inputs"]["text"] = params["prompt"]
                                positive_prompt_processed = True
                            # 处理反向提示词节点（通常是第二个CLIPTextEncode）
                            elif "negative_prompt" in params:
                                node_data["inputs"]["text"] = params["negative_prompt"]
                
                # 处理图像大小节点 (EmptyLatentImage)
                elif node_data["type"] == "EmptyLatentImage":
                    if "width" in params and "width" in node_data["inputs"]:
                        node_data["inputs"]["width"] = params["width"]
                    if "height" in params and "height" in node_data["inputs"]:
                        node_data["inputs"]["height"] = params["height"]
                
                # 处理采样器节点 (KSampler)
                elif node_data["type"] == "KSampler":
                    if "steps" in params and "steps" in node_data["inputs"]:
                        node_data["inputs"]["steps"] = params["steps"]
                    # 支持两种参数名：cfg和cfg_scale
                    if ("cfg" in params or "cfg_scale" in params) and "cfg" in node_data["inputs"]:
                        node_data["inputs"]["cfg"] = params.get("cfg_scale", params.get("cfg"))
                    if "denoising_strength" in params and "denoising_strength" in node_data["inputs"]:
                        node_data["inputs"]["denoising_strength"] = params["denoising_strength"]
                
                # 处理图像加载节点 (LoadImage)  
                elif node_data["type"] == "LoadImage" and "image_path" in params:
                    if "image" in node_data["inputs"]:
                        node_data["inputs"]["image"] = params["image_path"]
                
                # 处理Denoise强度参数（可能在多个节点中）
                elif "denoising_strength" in params and "denoising_strength" in node_data.get("inputs", {}):
                    node_data["inputs"]["denoising_strength"] = params["denoising_strength"]
        
        info(f"工作流参数已更新: {params}")
        return updated_workflow
    
    def run_workflow(self, workflow: Dict[str, Any], output_filename: str) -> bool:
        """运行工作流并保存结果"""
        try:
            info(f"运行工作流...")
            debug(f"--------原工作流: {workflow}")
            
            # 确保ComfyUI服务器正在运行
            server_running = self._check_server_running()
            if not server_running:
                info("ComfyUI服务器未运行，请手动启动后再试...")
                
                if not self._check_server_running():
                    error("无法连接到ComfyUI服务器，请确保服务器已启动")
                    return False
            
            # 统一使用requests库，不使用httpx，避免混乱
            info("ComfyUI服务器连接成功")
            
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

            debug(f"--------改后工作流: {comfyui_workflow}")
            # 发送工作流到ComfyUI API
            prompt_data = {
                "prompt": comfyui_workflow,
                # "client_id": uuid.uuid4().hex
                "client_id": f"hengline-aigc"
            }
            
            # 发送POST请求运行工作流
            info(f"正在向 {self.api_url}/prompt 发送请求...")
            response = requests.post(f"{self.api_url}/prompt", json=prompt_data)
            
            if response.status_code != 200:
                error(f"API请求失败: {response.status_code}, {response.text}")
                return False
            
            # 获取prompt_id
            response_json = response.json()
            # 确保response_json是字典类型
            if not isinstance(response_json, dict):
                error(f"API响应不是字典类型，而是: {type(response_json)}")
                return False
            
            prompt_id = response_json.get("prompt_id")
            if not prompt_id:
                error(f"无法获取prompt_id，响应内容: {response_json}")
                return False
            
            info(f"工作流已提交，prompt_id: {prompt_id}")
            
            # 等待工作流完成
            workflow_completed = self._wait_for_workflow_completion(prompt_id)
            if not workflow_completed:
                error(f"工作流执行失败: 等待工作流完成超时或连接失败")
                return False
            
            # 获取工作流结果
            output_path = os.path.join(self.output_dir, output_filename)
            success = self._get_workflow_outputs(prompt_id, output_path)
            
            if success:
                info(f"工作流运行完成，结果保存至: {output_path}")
            else:
                error("无法获取工作流结果")
                
            return success
        except Exception as e:
            error(f"工作流运行失败: {str(e)}")
            return False
            
    def _check_server_running(self) -> bool:
        """检查ComfyUI服务器是否正在运行"""
        try:
            response = requests.get(f"{self.api_url}/system_stats", timeout=3)
            return response.status_code == 200
        except:
            return False
            
    def _wait_for_workflow_completion(self, prompt_id: str) -> bool:
        """等待工作流完成并返回状态"""
        info("等待工作流处理完成...")
        
        # 设置最大等待时间为300秒（5分钟）
        max_wait_time = 300
        start_time = time.time()
        # 连续失败计数
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while True:
            # 检查是否超时
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                error(f"等待工作流完成超时，已等待{max_wait_time}秒")
                return False
            
            try:
                response = requests.get(f"{self.api_url}/history/{prompt_id}", timeout=5)
                if response.status_code == 200:
                    history = response.json()
                    # 确保history是字典类型
                    if not isinstance(history, dict):
                        debug(f"历史记录不是字典类型，而是: {type(history)}")
                        time.sleep(1)
                        continue
                    
                    if prompt_id in history:
                        prompt_data = history[prompt_id]
                        # 确保prompt_data是字典类型
                        if not isinstance(prompt_data, dict):
                            debug(f"prompt_data不是字典类型，而是: {type(prompt_data)}")
                            time.sleep(1)
                            continue
                        
                        # 检查工作流是否完成
                        if "outputs" in prompt_data:
                            info("工作流处理完成")
                            return True
                time.sleep(1)  # 每秒检查一次
                # 重置连续失败计数
                consecutive_failures = 0
            except Exception as e:
                consecutive_failures += 1
                error(f"检查工作流状态时出错（第{consecutive_failures}次）: {str(e)}")
                
                # 如果连续失败次数过多，视为连接超时失败
                if consecutive_failures >= max_consecutive_failures:
                    error(f"连续{max_consecutive_failures}次检查工作流状态失败，认为连接超时")
                    return False
                
                time.sleep(2)  # 失败时等待更长时间再重试
                
    def _get_workflow_outputs(self, prompt_id: str, output_path: str) -> bool:
        """获取工作流的输出结果"""
        try:
            # 获取历史记录
            api_endpoint = f"{self.api_url}/history/{prompt_id}"
            debug(f"[ComfyUI API] 获取工作流历史记录: {api_endpoint}")
            response = requests.get(api_endpoint, timeout=30)
            
            if response.status_code != 200:
                error(f"[ComfyUI API] 获取历史记录失败: 状态码={response.status_code}, 响应内容={response.text}")
                return False
            
            debug(f"[ComfyUI API] 获取历史记录成功，状态码: {response.status_code}")
            
            # 尝试解析JSON，添加更健壮的错误处理
            try:
                history = response.json()
            except json.JSONDecodeError as json_err:
                error(f"[ComfyUI API] 解析历史记录JSON失败: {str(json_err)}")
                error(f"[ComfyUI API] 响应内容: {response.text[:500]}...")  # 只显示部分内容
                return False
            
            if not isinstance(history, dict) or prompt_id not in history:
                error(f"[ComfyUI API] 历史记录格式不正确或找不到指定的prompt_id: {prompt_id}")
                error(f"[ComfyUI API] 历史记录结构: {type(history)} - {list(history.keys())[:5] if isinstance(history, dict) else '不是字典'}")
                return False
            
            prompt_data = history[prompt_id]
            if not isinstance(prompt_data, dict) or "outputs" not in prompt_data:
                error(f"[ComfyUI API] 找不到工作流输出，prompt_data格式: {type(prompt_data)}")
                if isinstance(prompt_data, dict):
                    error(f"[ComfyUI API] prompt_data键: {list(prompt_data.keys())}")
                return False
            
            outputs = prompt_data["outputs"]
            if not isinstance(outputs, dict):
                error(f"[ComfyUI API] outputs不是字典类型，而是: {type(outputs)}")
                return False
            
            debug(f"[ComfyUI API] 找到 {len(outputs)} 个输出节点")
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    info(f"[ComfyUI API] 创建输出目录: {output_dir}")
                except Exception as mkdir_err:
                    error(f"[ComfyUI API] 创建输出目录失败: {str(mkdir_err)}")
                    return False
            
            # 查找图像或视频输出
            found_output = False
            for node_id, node_output in outputs.items():
                debug(f"[ComfyUI API] 检查输出节点: {node_id}")
                # 确保node_output是字典类型
                if not isinstance(node_output, dict):
                    debug(f"[ComfyUI API] node_output不是字典类型，node_id: {node_id}, 类型: {type(node_output)}")
                    continue
                
                # 处理图像输出
                if "images" in node_output:
                    debug(f"[ComfyUI API] 找到图像输出，节点ID: {node_id}")
                    # 确保images是列表类型
                    if not isinstance(node_output["images"], list):
                        debug(f"[ComfyUI API] images不是列表类型，node_id: {node_id}")
                        continue
                    
                    debug(f"[ComfyUI API] 图像数量: {len(node_output['images'])}")
                    for idx, image_info in enumerate(node_output["images"]):
                        # 确保image_info是字典类型
                        if not isinstance(image_info, dict):
                            debug(f"[ComfyUI API] image_info不是字典类型")
                            continue
                        
                        # 检查必要的键是否存在
                        if not all(key in image_info for key in ['filename', 'subfolder', 'type']):
                            debug(f"[ComfyUI API] image_info缺少必要的键: {list(image_info.keys())}")
                            continue
                        
                        debug(f"[ComfyUI API] 图像信息: 文件名={image_info['filename']}, 子文件夹={image_info['subfolder']}")
                        # 获取图像数据
                        try:
                            # 添加超时设置
                            view_url = f"{self.api_url}/view?filename={image_info['filename']}&subfolder={image_info['subfolder']}&type={image_info['type']}"
                            debug(f"[ComfyUI API] 获取图像数据: {view_url}")
                            
                            # 添加重试逻辑
                            max_retries = 3
                            retry_count = 0
                            success = False
                            
                            while retry_count < max_retries and not success:
                                try:
                                    image_data = requests.get(view_url, timeout=60)
                                    if image_data.status_code == 200:
                                        # 保存图像到指定路径
                                        # 如果是多个图像，修改输出路径
                                        save_path = output_path
                                        if len(node_output['images']) > 1:
                                            base_name, ext = os.path.splitext(output_path)
                                            save_path = f"{base_name}_{idx}{ext}"
                                            
                                        debug(f"[ComfyUI API] 图像数据获取成功，保存到: {save_path}")
                                        
                                        # 检查文件写入权限
                                        try:
                                            with open(save_path, 'wb') as f:
                                                f.write(image_data.content)
                                            info(f"[ComfyUI API] 图像保存成功: {save_path}")
                                            found_output = True
                                            success = True
                                        except PermissionError:
                                            error(f"[ComfyUI API] 没有写入权限，无法保存图像到: {save_path}")
                                            retry_count += 1
                                            time.sleep(1)
                                        except Exception as write_err:
                                            error(f"[ComfyUI API] 写入图像文件失败: {str(write_err)}")
                                            retry_count += 1
                                            time.sleep(1)
                                    else:
                                        error(f"[ComfyUI API] 图像数据获取失败，状态码: {image_data.status_code}")
                                        retry_count += 1
                                        time.sleep(1)
                                except requests.exceptions.Timeout:
                                    error(f"[ComfyUI API] 获取图像数据超时")
                                    retry_count += 1
                                    time.sleep(1)
                                except Exception as img_err:
                                    error(f"[ComfyUI API] 获取图像数据时出错: {str(img_err)}")
                                    retry_count += 1
                                    time.sleep(1)
                        except Exception as outer_err:
                            error(f"[ComfyUI API] 处理图像时发生外部错误: {str(outer_err)}")
                            continue
                
                # 处理视频输出
                elif "videos" in node_output:
                    debug(f"[ComfyUI API] 找到视频输出，节点ID: {node_id}")
                    # 确保videos是列表类型
                    if not isinstance(node_output["videos"], list):
                        debug(f"[ComfyUI API] videos不是列表类型，node_id: {node_id}")
                        continue
                    
                    debug(f"[ComfyUI API] 视频数量: {len(node_output['videos'])}")
                    for idx, video_info in enumerate(node_output["videos"]):
                        # 确保video_info是字典类型
                        if not isinstance(video_info, dict):
                            debug(f"[ComfyUI API] video_info不是字典类型")
                            continue
                        
                        # 检查必要的键是否存在
                        if not all(key in video_info for key in ['filename', 'subfolder', 'type']):
                            debug(f"[ComfyUI API] video_info缺少必要的键: {list(video_info.keys())}")
                            continue
                        
                        debug(f"[ComfyUI API] 视频信息: 文件名={video_info['filename']}, 子文件夹={video_info['subfolder']}")
                        # 获取视频数据
                        try:
                            # 添加超时设置
                            view_url = f"{self.api_url}/view?filename={video_info['filename']}&subfolder={video_info['subfolder']}&type={video_info['type']}"
                            debug(f"[ComfyUI API] 获取视频数据: {view_url}")
                            
                            # 添加重试逻辑
                            max_retries = 3
                            retry_count = 0
                            success = False
                            
                            while retry_count < max_retries and not success:
                                try:
                                    video_data = requests.get(view_url, timeout=120)
                                    if video_data.status_code == 200:
                                        # 保存视频到指定路径
                                        # 如果是多个视频，修改输出路径
                                        save_path = output_path
                                        if len(node_output['videos']) > 1:
                                            base_name, ext = os.path.splitext(output_path)
                                            save_path = f"{base_name}_{idx}{ext}"
                                            
                                        debug(f"[ComfyUI API] 视频数据获取成功，保存到: {save_path}")
                                        
                                        # 检查文件写入权限
                                        try:
                                            with open(save_path, 'wb') as f:
                                                f.write(video_data.content)
                                            info(f"[ComfyUI API] 视频保存成功: {save_path}")
                                            found_output = True
                                            success = True
                                        except PermissionError:
                                            error(f"[ComfyUI API] 没有写入权限，无法保存视频到: {save_path}")
                                            retry_count += 1
                                            time.sleep(1)
                                        except Exception as write_err:
                                            error(f"[ComfyUI API] 写入视频文件失败: {str(write_err)}")
                                            retry_count += 1
                                            time.sleep(1)
                                    else:
                                        error(f"[ComfyUI API] 视频数据获取失败，状态码: {video_data.status_code}")
                                        retry_count += 1
                                        time.sleep(1)
                                except requests.exceptions.Timeout:
                                    error(f"[ComfyUI API] 获取视频数据超时")
                                    retry_count += 1
                                    time.sleep(1)
                                except Exception as vid_err:
                                    error(f"[ComfyUI API] 获取视频数据时出错: {str(vid_err)}")
                                    retry_count += 1
                                    time.sleep(1)
                        except Exception as outer_err:
                            error(f"[ComfyUI API] 处理视频时发生外部错误: {str(outer_err)}")
                            continue
                
                # 检查其他可能的输出类型
                elif "gifs" in node_output:
                    debug(f"[ComfyUI API] 找到GIF输出，节点ID: {node_id}")
                    # 处理逻辑类似于图像或视频
                    # 这里只是记录日志，实际处理可以根据需要添加
                    found_output = True
            
            # 检查是否找到并成功保存了输出
            if found_output:
                info(f"[ComfyUI API] 工作流输出保存成功")
                return True
            else:
                error("[ComfyUI API] 工作流没有产生可保存的图像或视频输出")
                # 打印详细信息以帮助调试
                for node_id, node_output in outputs.items():
                    if isinstance(node_output, dict):
                        error(f"[ComfyUI API] 节点 {node_id} 输出内容: {list(node_output.keys())}")
                return False
        except Exception as e:
            error(f"[ComfyUI API] 获取工作流输出时出错: {str(e)}")
            # 添加堆栈跟踪以帮助调试
            import traceback
            error(f"[ComfyUI API] 错误详细信息: {traceback.format_exc()}")
            return False


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
    
    # 初始化工作流运行器
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), output_folder)
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
            from utils.logger import warning
            warning("请指定工作流文件")
    finally:
        pass


if __name__ == "__main__":
    main()
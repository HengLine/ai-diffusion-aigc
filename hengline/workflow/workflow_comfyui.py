#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
封装ComfyUI API的类，提供图片上传、工作流执行等接口功能
"""

import json
import os
import time
from typing import Dict, Any, Optional

import requests

from hengline.logger import debug, error, warning
from hengline.utils.config_utils import get_task_config

class ComfyUIApi:
    """ComfyUI API接口类，统一管理所有与ComfyUI的交互功能"""

    def __init__(self, api_url: str = "http://127.0.0.1:8188"):
        """
        初始化ComfyUIApi
        
        Args:
            api_url: ComfyUI API URL地址，默认为http://127.0.0.1:8188
        """
        self.api_url = api_url

    def check_server_status(self) -> bool:
        """
        检查ComfyUI服务器是否正在运行
        
        Returns:
            bool: 服务器是否正常运行
        """
        try:
            response = requests.get(f"{self.api_url}/system_stats", timeout=3)
            return response.status_code == 200
        except Exception as e:
            error(f"检查ComfyUI服务器状态失败: {str(e)}")
            return False

    def upload_image(self, image_path: str, subfolder: str = "haengline") -> Optional[str]:
        """
        将图片上传到ComfyUI服务器
        
        Args:
            image_path: 本地图片路径
            subfolder: 上传到的子文件夹，默认为"haengline"
        
        Returns:
            Optional[str]: 上传成功返回ComfyUI服务器上的文件名，失败返回None
        """
        # 检查服务器是否正常运行
        if not self.check_server_status():
            error("ComfyUI服务器未运行，无法上传图片")
            return None

        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            error(f"图片文件不存在: {image_path}")
            return None

        # 确保文件是有效的图片文件
        if not self._is_valid_image_file(image_path):
            error(f"无效的图片文件: {image_path}")
            return None

        try:
            # 准备上传数据
            files = {
                'image': (os.path.basename(image_path), open(image_path, 'rb'))
            }
            data = {
                'subfolder': subfolder
            }

            debug(f"正在上传图片到ComfyUI服务器: {image_path}")
            response = requests.post(f"{self.api_url}/upload/image", files=files, data=data, timeout=30)

            if response.status_code == 200 and response.ok:
                result = response.json()
                filename = result.get('name')
                filedir = result.get('subfolder')
                debug(f"图片上传成功，ComfyUI文件名: {filename}, 子文件夹: {filedir}")
                return os.path.join(filedir, filename)
            else:
                error(f"图片上传请求失败，状态码: {response.status_code}, 响应: {response.text}")
        except Exception as e:
            error(f"图片上传过程中发生错误: {str(e)}")
        finally:
            # 确保文件被关闭
            if 'files' in locals() and 'image' in files:
                files['image'][1].close()

        return None

    def fill_image_in_workflow(self, workflow: Dict[str, Any], image_filename: str, node_id: Optional[str] = None) -> \
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

    def upload_and_fill_image(self, image_path: str, workflow: Dict[str, Any], subfolder: str = "haengline",
                              node_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        上传图片并将文件名填充到工作流中的图片节点
        
        Args:
            image_path: 本地图片路径
            workflow: 工作流数据
            subfolder: 上传到的子文件夹，默认为"input"
            node_id: 要填充的节点ID，如果为None则自动查找LoadImage节点
        
        Returns:
            Optional[Dict[str, Any]]: 更新后的工作流数据，失败返回None
        """
        # 上传图片
        image_filename = self.upload_image(image_path, subfolder)
        if not image_filename:
            return None

        # 填充图片文件名到工作流
        return self.fill_image_in_workflow(workflow, image_filename, node_id)

    def run_workflow(self, workflow: Dict[str, Any], client_id: str = "hengline-aigc") -> Optional[str]:
        """
        向ComfyUI服务器提交工作流并返回prompt_id
        
        Args:
            workflow: 工作流数据
            client_id: 客户端ID，默认为"hengline-aigc"
        
        Returns:
            Optional[str]: 成功返回prompt_id，失败返回None
        """
        try:
            debug("提交工作流到ComfyUI服务器...")

            # 确保ComfyUI服务器正在运行
            if not self.check_server_status():
                error("无法连接到ComfyUI服务器，请确保服务器已启动")
                return None

            # 将工作流转换为ComfyUI API期望的格式
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

            # 构建提示数据
            prompt_data = {
                "prompt": comfyui_workflow,
                "client_id": client_id
            }

            # 发送POST请求运行工作流
            debug(f"正在向 {self.api_url}/prompt 发送请求...")
            response = requests.post(f"{self.api_url}/prompt", json=prompt_data)

            if response.status_code != 200:
                error(f"API请求失败: {response.status_code}, {response.text}")
                return None

            # 获取prompt_id
            response_json = response.json()
            if not isinstance(response_json, dict):
                error(f"API响应不是字典类型，而是: {type(response_json)}")
                return None

            prompt_id = response_json.get("prompt_id")
            if not prompt_id:
                error(f"无法获取prompt_id，响应内容: {response_json}")
                return None

            debug(f"工作流已提交，prompt_id: {prompt_id}")
            return prompt_id
        except Exception as e:
            error(f"提交工作流失败: {str(e)}")
            return None


    def wait_for_workflow_completion(self, prompt_id: str) -> bool:
        """等待工作流完成并返回状态"""
        debug("等待工作流处理完成...")

        # 设置最大等待时间为1800秒（30分钟），增加处理复杂任务的时间
        # 可以根据需要调整这个值
        max_wait_time = get_task_config().get('task_timeout_seconds', 1800)
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
                            debug("工作流处理完成")
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


    def get_workflow_outputs(self, prompt_id: str, output_path: str) -> tuple[bool, list[str]]:
        """
        获取工作流的输出结果
        
        Args:
            prompt_id: 工作流的prompt_id
            output_path: 输出文件保存路径
        
        Returns:
            tuple[bool, list[str]]: (是否成功获取并保存输出结果, 保存的文件路径列表)
        """
        try:
            # 获取历史记录
            api_endpoint = f"{self.api_url}/history/{prompt_id}"
            debug(f"[ComfyUI API] 获取工作流历史记录: {api_endpoint}")
            response = requests.get(api_endpoint, timeout=30)

            if response.status_code != 200:
                error(f"[ComfyUI API] 获取历史记录失败: 状态码={response.status_code}, 响应内容={response.text}")
                return False, []

            # 尝试解析JSON
            try:
                history = response.json()
            except json.JSONDecodeError as json_err:
                error(f"[ComfyUI API] 解析历史记录JSON失败: {str(json_err)}")
                error(f"[ComfyUI API] 响应内容: {response.text[:500]}...")  # 只显示部分内容
                return False, []

            if not isinstance(history, dict) or prompt_id not in history:
                error(f"[ComfyUI API] 历史记录格式不正确或找不到指定的prompt_id: {prompt_id}")
                return False, []

            prompt_data = history[prompt_id]
            if not isinstance(prompt_data, dict) or "outputs" not in prompt_data:
                error(f"[ComfyUI API] 找不到工作流输出，prompt_data格式: {type(prompt_data)}")
                return False, []

            outputs = prompt_data["outputs"]
            if not isinstance(outputs, dict):
                error(f"[ComfyUI API] outputs不是字典类型，而是: {type(outputs)}")
                return False, []

            debug(f"[ComfyUI API] 找到 {len(outputs)} 个输出节点")

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    debug(f"[ComfyUI API] 创建输出目录: {output_dir}")
                except Exception as mkdir_err:
                    error(f"[ComfyUI API] 创建输出目录失败: {str(mkdir_err)}")
                    return False, []

            # 查找图像或视频输出
            found_output = False
            saved_file_paths = []
            all_output_types = ['images', 'videos', 'gifs']
            
            # 生成基本文件名（不带扩展名）和扩展名
            base_name, ext = os.path.splitext(os.path.basename(output_path))
            # 创建输出目录的完整路径
            base_output_dir = os.path.dirname(output_path)
            for node_id, node_output in outputs.items():
                debug(f"[ComfyUI API] 检查输出节点: {node_id}")
                # 确保node_output是字典类型
                if not isinstance(node_output, dict):
                    debug(f"[ComfyUI API] node_output不是字典类型，node_id: {node_id}, 类型: {type(node_output)}")
                    continue

                # 遍历所有支持的输出类型
                for output_type in all_output_types:
                    if output_type in node_output:
                        debug(f"[ComfyUI API] 找到{output_type}输出，节点ID: {node_id}")
                        # 确保输出内容是列表类型
                        if not isinstance(node_output[output_type], list):
                            debug(f"[ComfyUI API] {output_type}不是列表类型，node_id: {node_id}")
                            continue

                        items = node_output[output_type]
                        debug(f"[ComfyUI API] {output_type}数量: {len(items)}")
                        
                        # 根据输出类型设置超时时间
                        timeout = get_task_config().get('task_view_timeout_seconds', 60)    # 默认超时时间
                        if output_type == 'videos':
                            timeout *= 3  # 视频可能需要更长的时间
                        elif output_type == 'gifs':
                            timeout *= 2  # GIF可能需要更长的时间
                        debug(f"[ComfyUI API] {output_type}超时时间: {timeout}秒")
                        max_retries = get_task_config().get('task_view_max_retries', 3)  # 默认重试次数
                        
                        for idx, item_info in enumerate(items):
                            # 确保item_info是字典类型
                            if not isinstance(item_info, dict):
                                debug(f"[ComfyUI API] {output_type}中的item_info不是字典类型")
                                continue

                            # 检查必要的键是否存在
                            if not all(key in item_info for key in ['filename', 'subfolder', 'type']):
                                debug(f"[ComfyUI API] {output_type}中的item_info缺少必要的键: {list(item_info.keys())}")
                                continue

                            debug(f"[ComfyUI API] {output_type}信息: 文件名={item_info['filename']}, 子文件夹={item_info['subfolder']}")
                            
                            try:
                                # 添加超时设置
                                view_url = f"{self.api_url}/view?filename={item_info['filename']}&subfolder={item_info['subfolder']}&type={item_info['type']}"
                                debug(f"[ComfyUI API] 获取{output_type}数据: {view_url}")

                                # 添加重试逻辑
                                retry_count = 0
                                success = False

                                while retry_count < max_retries and not success:
                                    try:
                                        # 获取文件数据
                                        item_data = requests.get(view_url, timeout=timeout)
                                        if item_data.status_code == 200:
                                            # 保存文件到指定路径
                                            # 为每个文件生成唯一的保存路径，确保多文件输出不会覆盖
                                            # 从ComfyUI原始文件名中获取扩展名，确保格式正确
                                            comfy_ext = os.path.splitext(item_info['filename'])[1]
                                            
                                            # 创建统一的命名规则：基础文件名_输出类型_索引.原始扩展名
                                            unique_filename = f"{base_name}_{output_type}_{idx+1}{comfy_ext}"
                                            save_path = os.path.join(base_output_dir, unique_filename)
                                            
                                            debug(f"[ComfyUI API] {output_type}数据获取成功，保存到: {save_path}")

                                            # 检查文件写入权限
                                            try:
                                                with open(save_path, 'wb') as f:
                                                    f.write(item_data.content)
                                                debug(f"[ComfyUI API] {output_type}保存成功: {save_path}")
                                                found_output = True
                                                success = True
                                                saved_file_paths.append(save_path)
                                            except PermissionError:
                                                error(f"[ComfyUI API] 没有写入权限，无法保存{output_type}到: {save_path}")
                                                retry_count += 1
                                                time.sleep(1)
                                            except Exception as write_err:
                                                error(f"[ComfyUI API] 写入{output_type}文件失败: {str(write_err)}")
                                                retry_count += 1
                                                time.sleep(1)
                                        else:
                                            error(f"[ComfyUI API] {output_type}数据获取失败，状态码: {item_data.status_code}")
                                            retry_count += 1
                                            time.sleep(1)
                                    except requests.exceptions.Timeout:
                                        error(f"[ComfyUI API] 获取{output_type}数据超时")
                                        retry_count += 1
                                        time.sleep(1)
                                    except Exception as data_err:
                                        error(f"[ComfyUI API] 获取{output_type}数据时出错: {str(data_err)}")
                                        retry_count += 1
                                        time.sleep(1)
                            except Exception as outer_err:
                                error(f"[ComfyUI API] 处理{output_type}时发生外部错误: {str(outer_err)}")
                                continue

            # 检查是否找到并成功保存了输出
            if found_output:
                debug(f"[ComfyUI API] 工作流输出保存成功")
                return True, saved_file_paths
            else:
                error("[ComfyUI API] 工作流没有产生可保存的图像或视频输出")
                # 打印详细信息以帮助调试
                for node_id, node_output in outputs.items():
                    if isinstance(node_output, dict):
                        error(f"[ComfyUI API] 节点 {node_id} 输出内容: {list(node_output.keys())}")
                return False, []
        except Exception as e:
            error(f"[ComfyUI API] 获取工作流输出时出错: {str(e)}")
            # 添加堆栈跟踪以帮助调试
            import traceback
            error(f"[ComfyUI API] 错误详细信息: {traceback.format_exc()}")
            return False, []

    def _is_valid_image_file(self, file_path: str) -> bool:
        """
        检查文件是否为有效的图片文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            bool: 是否为有效图片文件
        """
        # 检查文件扩展名
        valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
        _, ext = os.path.splitext(file_path.lower())
        return ext in valid_extensions


# 全局ComfyUIApi实例，方便其他模块直接使用
comfyui_api = ComfyUIApi()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
封装ComfyUI API的类，提供图片上传、工作流执行等接口功能
"""

import json
import os
import threading
import time
from typing import Dict, Any, Optional, Callable

import requests

from hengline.logger import debug, error, warning, info
from hengline.utils.config_utils import get_task_config
from hengline.utils.file_utils import is_valid_image_file
from hengline.utils.log_utils import print_log_exception
from hengline.workflow.workflow_node import fill_image_in_workflow
from hengline.workflow.workflow_status_checker import workflow_status_checker


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

    def _upload_image(self, image_path: str, subfolder: str = "haengline") -> Optional[str]:
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
        if not is_valid_image_file(image_path):
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
            print_log_exception()
        finally:
            # 确保文件被关闭
            if 'files' in locals() and 'image' in files:
                files['image'][1].close()

        return None

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
        image_filename = self._upload_image(image_path, subfolder)
        if not image_filename:
            return None

        # 填充图片文件名到工作流
        return fill_image_in_workflow(workflow, image_filename, node_id)

    def execute_workflow(self, workflow: Dict[str, Any]) -> dict[str, Any]:
        """
        执行工作流并返回prompt_id

        Args:
            workflow: 工作流数据

        Returns:
            str: 提交成功返回prompt_id，失败返回空字符串
        """
        try:
            debug("正在提交工作流到ComfyUI服务器...")
            response = requests.post(f"{self.api_url}/prompt", json=workflow, timeout=20)

            if response.status_code == 200 and response.ok:
                result = response.json()
                info(f"工作流提交成功，result: {result}")
                return {'success': True, 'prompt_id': result.get('prompt_id', '')}
            else:
                error(f"工作流提交请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return {'success': False, 'message': f"工作流提交失败: {response.reason}"}

        except Exception as e:
            error(f"工作流提交过程中发生错误: {str(e)}")
            print_log_exception()

        return {'success': False, 'message': '工作流提交失败，发生异常'}

    def wait_for_workflow_completion(self, prompt_id: str) -> bool:
        """等待工作流完成并返回状态 - 同步版本（向后兼容）
        
        这个方法会阻塞当前线程，直到工作流完成或超时
        """
        debug("等待工作流处理完成...")

        # 使用事件同步等待异步检查结果
        completion_event = threading.Event()
        result = False  # 使用列表作为可变对象来存储结果

        def on_complete(prompt_id, success):
            result = success
            completion_event.set()

        def on_timeout(prompt_id):
            completion_event.set()

        # 调用异步方法进行状态检查
        task_id = self.async_wait_for_workflow_completion(prompt_id, on_complete, on_timeout)

        # 等待工作流完成或超时
        max_wait_time = get_task_config().get('task_timeout_seconds', 1800)
        completion_event.wait(max_wait_time)

        if not completion_event.is_set():
            # 超时，取消检查
            workflow_status_checker.cancel_check(task_id)
            error(f"等待工作流完成超时，已等待{max_wait_time}秒")
            return False

        return result

    def async_wait_for_workflow_completion(self, prompt_id: str,
                                           on_complete: Callable[[str, bool], None],
                                           on_timeout: Optional[Callable[[str], None]] = None) -> str:
        """异步等待工作流完成
        
        这个方法不会阻塞当前线程，而是通过回调函数通知工作流完成状态
        
        Args:
            prompt_id: 工作流的prompt_id
            on_complete: 工作流完成时的回调函数，参数为(prompt_id, success)
            on_timeout: 工作流超时时的回调函数，参数为(prompt_id)
        
        Returns:
            str: 任务ID，可以用于后续取消检查
        """
        debug(f"启动异步工作流状态检查，prompt_id: {prompt_id}")

        # 如果没有提供超时回调，使用完成回调并标记为失败
        if not on_timeout:
            def default_on_timeout(prompt_id):
                on_complete(prompt_id, False)

            on_timeout = default_on_timeout

        # 调用工作流状态检查器
        task_id = workflow_status_checker.check_workflow_status_async(
            prompt_id=prompt_id,
            api_url=self.api_url,
            on_complete=on_complete,
            on_timeout=on_timeout,
            check_interval=5  # 初始检查间隔为5秒
        )

        return task_id

    def _get_workflow_outputs(self, prompt_id: str, output_path: str) -> tuple[bool, list[str]]:
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
                        timeout = get_task_config().get('task_view_timeout_seconds', 60)  # 默认超时时间
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

                            debug(
                                f"[ComfyUI API] {output_type}信息: 文件名={item_info['filename']}, 子文件夹={item_info['subfolder']}")

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
                                            # unique_filename = f"{base_name}_{output_type}_{idx+1}{comfy_ext}"
                                            unique_filename = f"{base_name}_{idx + 1}{comfy_ext}"
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
                                                error(
                                                    f"[ComfyUI API] 没有写入权限，无法保存{output_type}到: {save_path}")
                                                retry_count += 1
                                                time.sleep(1)
                                            except Exception as write_err:
                                                error(f"[ComfyUI API] 写入{output_type}文件失败: {str(write_err)}")
                                                print_log_exception()
                                                retry_count += 1
                                                time.sleep(1)
                                        else:
                                            error(
                                                f"[ComfyUI API] {output_type}数据获取失败，状态码: {item_data.status_code}")
                                            retry_count += 1
                                            time.sleep(1)
                                    except requests.exceptions.Timeout:
                                        error(f"[ComfyUI API] 获取{output_type}数据超时")
                                        retry_count += 1
                                        time.sleep(1)
                                    except Exception as data_err:
                                        error(f"[ComfyUI API] 获取{output_type}数据时出错: {str(data_err)}")
                                        print_log_exception()
                                        retry_count += 1
                                        time.sleep(1)
                            except Exception as outer_err:
                                error(f"[ComfyUI API] 处理{output_type}时发生外部错误: {str(outer_err)}")
                                print_log_exception()
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
            print_log_exception()
            return False, []

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
            # 使用ComfyUIApi获取工作流输出（现在直接返回保存的文件路径列表）
            success, saved_file_paths = self._get_workflow_outputs(prompt_id, output_path)

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
            print_log_exception()
            return False, []


# 全局ComfyUIApi实例，方便其他模块直接使用
comfyui_api = ComfyUIApi()

# -*- coding: utf-8 -*-
"""
测试从get_effective_config()获取的值是否都能正确填充到工作流JSON中
"""
import json
import os
import sys

# 导入logger
from hengline.logger import debug, info, warning

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.utils.config_utils import get_effective_config, load_workflow_presets, get_workflow_path


def test_effective_config_filling():
    """测试从get_effective_config()获取的值是否都能正确填充到工作流JSON中"""
    info("开始测试有效配置填充功能...")
    
    # 初始化工作流运行器
    runner = ComfyUIRunner(output_dir="./outputs")
    
    # 测试所有任务类型
    task_types = ["text_to_image", "image_to_image", "image_to_video", "text_to_video"]
    
    for task_type in task_types:
        info(f"\n\n======= 测试任务类型: {task_type} =======")
        
        # 1. 获取有效配置
        effective_config = get_effective_config(task_type)
        debug(f"\n1. 有效配置 ({len(effective_config)}个属性):")
        for key, value in effective_config.items():
            debug(f"   {key}: {value}")
        
        # 2. 创建一个模拟的工作流，包含所有可能的节点类型
        test_workflow = {
            "prompt": {
                # CLIPTextEncode节点（提示词）
                "1": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": "original_prompt"
                    }
                },
                # CLIPTextEncode节点（负提示词）
                "2": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": "original_negative_prompt"
                    }
                },
                # KSampler节点
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "steps": 0,
                        "cfg": 0.0,
                        "denoise": 0.0,
                        "seed": 0
                    }
                },
                # EmptyLatentImage节点
                "4": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": 0,
                        "height": 0,
                        "batch_size": 0
                    }
                },
                # 视频相关节点
                "5": {
                    "class_type": "VideoNode",
                    "inputs": {
                        "length": 0,
                        "shift": 0,
                        "fps": 0
                    }
                },
                # 图生图相关节点
                "6": {
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": "original_image_path"
                    }
                },
                # 用于捕获所有其他参数的节点
                "99": {
                    "class_type": "GenericNode",
                    "inputs": {}
                }
            }
        }
        
        # 为GenericNode添加所有有效配置的参数作为默认值
        for param_name in effective_config.keys():
            test_workflow["prompt"]["99"]["inputs"][param_name] = f"original_{param_name}"
        
        # 3. 更新工作流参数
        updated_workflow = runner.update_workflow_params(test_workflow, effective_config)
        
        # 4. 验证结果
        debug(f"\n3. 验证参数更新结果:")
        
        # 统计成功更新的参数数量
        success_count = 0
        total_count = len(effective_config)
        
        # 检查每个参数是否被正确更新到至少一个节点
        for param_name, expected_value in effective_config.items():
            found_and_updated = False
            updated_node_info = []
            
            # 检查所有节点
            for node_id, node_data in updated_workflow["prompt"].items():
                node_type = node_data.get("class_type", "Unknown")
                
                # 特殊处理参数名称映射
                if param_name == "cfg" and "cfg" in node_data["inputs"]:
                    if node_data["inputs"]["cfg"] == expected_value:
                        found_and_updated = True
                        updated_node_info.append(f"节点{node_id}({node_type}): cfg")
                elif param_name == "denoise" and "denoise" in node_data["inputs"]:
                    if node_data["inputs"]["denoise"] == expected_value:
                        found_and_updated = True
                        updated_node_info.append(f"节点{node_id}({node_type}): denoise")
                elif param_name == "image_path" and "image" in node_data["inputs"] and node_type == "LoadImage":
                    if node_data["inputs"]["image"] == expected_value:
                        found_and_updated = True
                        updated_node_info.append(f"节点{node_id}({node_type}): image")
                # 检查直接匹配的参数
                elif param_name in node_data["inputs"]:
                    if node_data["inputs"][param_name] == expected_value:
                        found_and_updated = True
                        updated_node_info.append(f"节点{node_id}({node_type}): {param_name}")
            
            # 输出验证结果
            status = "✓ 成功" if found_and_updated else "✗ 失败"
            if found_and_updated:
                success_count += 1
            
            debug(f"   {status} - {param_name}: {expected_value}")
            if updated_node_info:
                debug(f"     更新位置: {', '.join(updated_node_info)}")
        
        # 输出总体结果
        debug(f"\n4. 总体更新结果: {success_count}/{total_count} 个参数成功更新")
        
        # 5. 检查真实工作流文件
        workflow_path = get_workflow_path(task_type)
        if workflow_path:
            full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), workflow_path)
            if os.path.exists(full_path):
                debug(f"\n5. 检查真实工作流文件: {full_path}")
                with open(full_path, 'r', encoding='utf-8') as f:
                    real_workflow = json.load(f)
                
                # 提取所有节点的输入参数键
                all_input_keys = set()
                if "prompt" in real_workflow:
                    for node_id, node_data in real_workflow["prompt"].items():
                        if "inputs" in node_data:
                            all_input_keys.update(node_data["inputs"].keys())
                elif "nodes" in real_workflow:
                    for node_data in real_workflow["nodes"]:
                        if "inputs" in node_data:
                            all_input_keys.update(node_data["inputs"].keys())
                
                debug(f"   工作流中存在的输入参数键数量: {len(all_input_keys)}")
                
                # 检查有效配置中的参数是否在工作流中存在
                missing_in_workflow = [param for param in effective_config.keys() 
                                      if param not in all_input_keys 
                                      and param not in ["prompt", "negative_prompt"]
                                      and not (param == "cfg" and "cfg" in all_input_keys)
                                      and not (param == "denoise" and "denoise" in all_input_keys)
                                      and not (param == "image_path" and "image" in all_input_keys)]
                
                if missing_in_workflow:
                    warning(f"   有效配置中存在但工作流中不存在的参数: {missing_in_workflow}")
                else:
                    debug(f"   有效配置中的所有参数在工作流中都有对应的输入节点")
            else:
                warning(f"   工作流文件不存在: {full_path}")
        else:
            warning(f"   未找到该任务类型的工作流配置")
    
    info("\n\n======= 测试完成 =======")


if __name__ == "__main__":
    test_effective_config_filling()
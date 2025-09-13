#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试工作流参数更新功能
"""
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hengline.logger import debug, info
from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.utils.config_utils import get_effective_config, load_workflow_presets

def test_update_workflow_params():
    """测试工作流参数更新功能"""
    info("开始测试工作流参数更新功能...")
    
    # 初始化工作流运行器
    # 使用项目根目录下的outputs
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runner = ComfyUIRunner(output_dir=os.path.join(project_root, "outputs"))
    
    # 测试用的工作流数据
    test_workflow = {
        "prompt": {
            "1": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "原始提示词"
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "原始负提示词"
                }
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "steps": 20,
                    "cfg": 7.0,
                    "denoise": 1.0
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512
                }
            },
            "5": {
                "class_type": "SomeOtherNode",
                "inputs": {
                    "custom_param": 10,
                    "another_param": "default_value"
                }
            }
        }
    }
    
    # 测试用的参数
    test_params = {
        "prompt": "测试提示词",
        "negative_prompt": "测试负提示词",
        "steps": 30,
        "cfg": 8.0,
        "width": 768,
        "height": 768,
        "custom_param": 20,
        "another_param": "updated_value",
        "new_param": "new_value"  # 这个参数在任何节点中都不存在
    }
    
    # 更新参数
    updated_workflow = runner.update_workflow_params(test_workflow, test_params)
    
    # 验证结果
    info("\n更新后的工作流参数:")
    debug(json.dumps(updated_workflow, ensure_ascii=False, indent=2))
    
    # 检查特定节点的更新情况
    info("\n验证更新结果:")
    clip1 = updated_workflow["prompt"]["1"]
    clip2 = updated_workflow["prompt"]["2"]
    ksampler = updated_workflow["prompt"]["3"]
    latent = updated_workflow["prompt"]["4"]
    other = updated_workflow["prompt"]["5"]
    
    debug(f"1. CLIPTextEncode1 提示词: {clip1['inputs']['text']} (应为: {test_params['prompt']})")
    debug(f"2. CLIPTextEncode2 负提示词: {clip2['inputs']['text']} (应为: {test_params['negative_prompt']})")
    debug(f"3. KSampler steps: {ksampler['inputs']['steps']} (应为: {test_params['steps']})")
    debug(f"4. KSampler cfg: {ksampler['inputs']['cfg']} (应为: {test_params['cfg']})")
    debug(f"5. EmptyLatentImage width: {latent['inputs']['width']} (应为: {test_params['width']})")
    debug(f"6. EmptyLatentImage height: {latent['inputs']['height']} (应为: {test_params['height']})")
    debug(f"7. SomeOtherNode custom_param: {other['inputs']['custom_param']} (应为: {test_params['custom_param']})")
    debug(f"8. SomeOtherNode another_param: {other['inputs']['another_param']} (应为: {test_params['another_param']})")
    debug(f"9. SomeOtherNode new_param: {'存在' if 'new_param' in other['inputs'] else '不存在'} (应为: 不存在，因为原始节点中没有这个参数)")
    
    # 测试真实工作流预设
    info("\n测试真实工作流预设更新:")
    presets = load_workflow_presets()
    for task_type in presets.keys():
        info(f"\n任务类型: {task_type}")
        effective_config = get_effective_config(task_type)
        debug(f"有效配置: {effective_config}")
        
        # 创建一个简单的工作流来测试该任务类型的参数更新
        test_task_workflow = {
            "prompt": {
                "1": {
                    "class_type": "TestNode",
                    "inputs": {}
                }
            }
        }
        
        # 为测试节点添加该任务类型的所有参数
        for param_name in effective_config.keys():
            test_task_workflow["prompt"]["1"]["inputs"][param_name] = "original_value"
        
        # 更新参数
        updated_task_workflow = runner.update_workflow_params(test_task_workflow, effective_config)
        
        # 验证更新
        updated_node = updated_task_workflow["prompt"]["1"]
        debug(f"参数更新数量: {sum(1 for k, v in updated_node['inputs'].items() if v != 'original_value')}/{len(effective_config)}")
    
    info("\n测试完成!")

if __name__ == "__main__":
    test_update_workflow_params()
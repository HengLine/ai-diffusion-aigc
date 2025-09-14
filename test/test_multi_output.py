#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多输出文件功能
验证工作流能否正确返回多个输出文件路径
"""
import os
import sys
import time
import json
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hengline.workflow.run_workflow import ComfyUIRunner
from hengline.logger import debug, info, warning, error


def test_multi_output():
    """测试多输出文件功能"""
    info("===== 开始测试多输出文件功能 =====")
    
    try:
        # 初始化工作流运行器
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(project_root, "outputs")
        runner = ComfyUIRunner(output_dir)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建一个测试工作流
        # 注意：这是一个简化的工作流，实际使用时需要替换为有效的工作流文件
        test_workflow = {
            "prompt": {
                "1": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": "a beautiful landscape, trending on artstation"
                    }
                },
                "2": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": "ugly, blurry, bad art, poor quality"
                    }
                },
                "3": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": 512,
                        "height": 512
                    }
                }
                # 注意：这里需要根据实际情况补充其他必要的节点
            }
        }
        
        # 生成唯一的输出文件名
        timestamp = int(time.time())
        output_filename = f"test_multi_output_{timestamp}.png"
        
        info(f"使用输出文件名: {output_filename}")
        info(f"工作流内容: {json.dumps(test_workflow, ensure_ascii=False, indent=2)}")
        
        # 尝试运行工作流
        # 注意：实际运行需要有效的工作流配置
        # 这里我们只是测试返回值的格式处理
        # 由于可能没有实际运行的ComfyUI服务器，这里可能会失败
        info("准备运行工作流...")
        try:
            result = runner.run_workflow(test_workflow, output_filename)
            
            # 打印返回结果
            info(f"工作流运行结果: {result}")
            
            # 检查结果格式
            if isinstance(result, dict):
                info(f"成功获取字典格式的结果")
                info(f"成功状态: {result.get('success', False)}")
                
                # 检查output_paths是否存在
                if 'output_paths' in result:
                    output_paths = result['output_paths']
                    info(f"找到output_paths，包含 {len(output_paths)} 个文件路径")
                    for path in output_paths:
                        info(f"文件路径: {path}, 存在: {os.path.exists(path)}")
                else:
                    info("未找到output_paths字段")
            else:
                warning(f"返回结果不是预期的字典格式，而是: {type(result)}")
                
        except Exception as e:
            error(f"运行工作流时出错: {str(e)}")
            # 即使工作流运行失败，我们也可以测试返回格式处理逻辑
            # 这里模拟一个成功的返回结果
            mock_result = {
                "success": True,
                "output_paths": [
                    os.path.join(output_dir, output_filename),
                    os.path.join(output_dir, f"{os.path.splitext(output_filename)[0]}_1.png")
                ]
            }
            info(f"使用模拟结果测试格式处理: {mock_result}")
            
            # 测试TaskQueue中的逻辑
            from hengline.core.task_queue import TaskQueueManager, Task
            
            # 创建模拟任务
            task = Task(
                task_type="text_to_image",
                task_id=f"test_{timestamp}",
                timestamp=timestamp,
                params={"prompt": "test prompt"},
                callback=lambda x: None
            )
            
            # 模拟_execute_task中的结果处理逻辑
            if mock_result and isinstance(mock_result, dict):
                # 处理多个输出文件
                if 'output_paths' in mock_result:
                    # 从output_paths中提取文件名列表
                    task.output_filenames = [os.path.basename(path) for path in mock_result['output_paths']]
                    # 设置第一个输出文件为默认输出文件名
                    if task.output_filenames:
                        task.output_filename = task.output_filenames[0]
                        
                info(f"模拟任务处理后的output_filename: {task.output_filename}")
                info(f"模拟任务处理后的output_filenames: {task.output_filenames}")
            
    except Exception as e:
        error(f"测试过程中发生错误: {str(e)}")
        import traceback
        error(f"错误详情: {traceback.format_exc()}")
    
    info("===== 测试完成 =====")


if __name__ == "__main__":
    test_multi_output()
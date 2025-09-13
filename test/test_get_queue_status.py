#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TaskQueueManager的get_queue_status方法
"""

import sys
import os

# 导入logger
from hengline.logger import debug, info, warning, error

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.core.task_queue import task_queue_manager

if __name__ == '__main__':
    info("=== 测试 get_queue_status 方法 ===")
    
    # 调用get_queue_status方法
    try:
        status = task_queue_manager.get_queue_status()
        info("成功获取队列状态:")
        debug(f"- 排队中的任务数量: {status['queued_tasks']}")
        debug(f"- 正在运行的任务数量: {status['running_tasks']}")
        debug(f"- 最大并发任务数: {status['max_concurrent_tasks']}")
        debug(f"- 历史任务总数: {status['total_history_tasks']}")
        info("\n测试通过!")
    except AttributeError as e:
        error(f"测试失败: {str(e)}")
        error("TaskQueueManager对象没有get_queue_status属性")
    except Exception as e:
        error(f"测试失败: {str(e)}")

    info("\n=== 测试完成 ===")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# 导入logger
from hengline.logger import debug, info, warning, error

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.core.task_queue import TaskQueueManager
import threading

# 测试单例模式
def test_singleton():
    info("创建第一个实例...")
    manager1 = TaskQueueManager()
    debug(f"manager1 id: {id(manager1)}")
    debug(f"类变量 _instance id: {id(TaskQueueManager._instance)}")
    debug(f"类变量 _initialized: {TaskQueueManager._initialized}")
    
    info("\n创建第二个实例...")
    manager2 = TaskQueueManager()
    debug(f"manager2 id: {id(manager2)}")
    debug(f"类变量 _instance id: {id(TaskQueueManager._instance)}")
    debug(f"类变量 _initialized: {TaskQueueManager._initialized}")
    
    info("\n验证是否为同一实例:")
    debug(f"manager1 is manager2: {manager1 is manager2}")
    
    # 尝试从不同线程创建实例
    thread_instances = []
    
    def create_instance():
        instance = TaskQueueManager()
        thread_instances.append(instance)
        
    info("\n从5个不同线程创建实例...")
    threads = []
    for i in range(5):
        thread = threading.Thread(target=create_instance)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    info("验证所有线程创建的实例是否相同:")
    for i, instance in enumerate(thread_instances):
        debug(f"线程 {i+1} 创建的实例 id: {id(instance)}")
    
    # 检查所有线程创建的实例是否都是同一个
    all_same = all(instance is thread_instances[0] for instance in thread_instances)
    info(f"所有线程创建的实例是否相同: {all_same}")

if __name__ == "__main__":
    test_singleton()
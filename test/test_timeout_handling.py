import sys
import os
import time
import uuid
import threading
from threading import Thread

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.core.task_queue import TaskQueueManager, Task

# 模拟一个会超时的任务回调函数
def timeout_task_callback(params):
    # 模拟一个会执行很长时间的任务
    time.sleep(5)  # 睡眠5秒，但我们会设置较短的超时时间
    return {"success": True, "message": "任务完成"}

# 测试任务队列的超时处理
if __name__ == "__main__":
    print("开始测试任务队列的超时处理...")
    
    # 获取任务队列管理器实例
    task_queue_manager = TaskQueueManager()
    
    # 创建测试任务ID和锁
    task_id = str(uuid.uuid4())
    task_lock = threading.Lock()
    
    # 创建测试任务（使用正确的参数顺序）
    test_task = Task(
        task_type="text_to_image",
        task_id=task_id,
        timestamp=time.time(),
        params={"prompt": "测试超时任务", "model": "test_model"},
        task_lock=task_lock,
        callback=timeout_task_callback
    )
    
    # 设置start_time属性
    test_task.start_time = time.time()
    
    print(f"创建测试任务: {test_task.task_id}")
    
    # 直接调用_execute_callback_with_timeout方法测试超时处理
    # 设置一个短超时时间（2秒）来强制超时
    print("执行任务并设置2秒超时...")
    result = task_queue_manager._execute_callback_with_timeout(test_task, timeout=2)
    
    # 检查结果
    print(f"任务执行结果: {result}")
    
    if isinstance(result, dict) and not result.get('success', True) and result.get('timeout', False):
        print("测试成功: 任务超时处理正常工作，返回了包含timeout标记的错误信息")
        print(f"错误消息: {result.get('message')}")
    else:
        print("测试失败: 任务超时处理不正确")
    
    print("测试完成")
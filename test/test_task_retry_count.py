import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch
import uuid
import logging
import traceback
import threading
import inspect

# 配置日志，使其更简洁
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.utils.task_queue_utils import TaskQueueManager, Task
from hengline.logger import debug, info, warning, error

# 添加全局调试函数
def debug_log(message):
    frame = inspect.currentframe().f_back
    caller_name = frame.f_code.co_name
    caller_line = frame.f_lineno
    thread_name = threading.current_thread().name
    debug(f"[DEBUG {thread_name} {caller_name}:{caller_line}] {message}")

class TestTaskRetryCount(unittest.TestCase):
    def setUp(self):
        debug_log("setUp开始")
        # 使用patch模拟数据目录和相关方法
        self.data_dir_patch = patch('scripts.utils.task_queue_utils.TaskQueueManager._load_task_history')
        self.mock_load_history = self.data_dir_patch.start()
        self.mock_load_history.return_value = None
        debug_log("模拟_load_task_history完成")
        
        # 模拟任务历史保存，避免实际写入文件
        self.save_history_patch = patch('scripts.utils.task_queue_utils.TaskQueueManager._save_task_history')
        self.mock_save_history = self.save_history_patch.start()
        self.mock_save_history.return_value = None
        debug_log("模拟_save_task_history完成")
        
        # 初始化任务队列管理器
        debug_log("创建TaskQueueManager实例前")
        self.task_queue_manager = TaskQueueManager(max_concurrent_tasks=1)
        debug_log(f"创建TaskQueueManager实例完成，实例ID: {id(self.task_queue_manager)}")
        debug_log(f"类变量_instance ID: {id(TaskQueueManager._instance)}")
        debug_log(f"类变量_initialized: {TaskQueueManager._initialized}")
        
        # 确保任务队列是空的
        debug_log("清空任务队列前")
        while not self.task_queue_manager.task_queue.empty():
            self.task_queue_manager.task_queue.get()
        debug_log("清空任务队列完成")
        
        # 清除运行中的任务
        self.task_queue_manager.running_tasks.clear()
        debug_log("清空运行中任务完成")
        # 清除任务历史
        self.task_queue_manager.task_history.clear()
        debug_log("清空任务历史完成")
        
        # 保存原始方法
        debug_log("保存原始方法前")
        self.original_execute_task = self.task_queue_manager._execute_task
        self.original_process_tasks = self.task_queue_manager._process_tasks
        debug_log("保存原始方法完成")
        
        # 模拟_process_tasks方法，只处理一个任务
        debug_log("定义mock_process_tasks前")
        def mock_process_tasks():
            debug_log("mock_process_tasks开始执行")
            with self.task_queue_manager.lock:
                if len(self.task_queue_manager.running_tasks) < self.task_queue_manager.max_concurrent_tasks and not self.task_queue_manager.task_queue.empty():
                    task = self.task_queue_manager.task_queue.get()
                    debug_log(f"获取任务: {task.task_id}")
                    task.status = "running"
                    task.start_time = time.time()
                    self.task_queue_manager.running_tasks[task.task_id] = task
                    self.task_queue_manager.task_history[task.task_id] = task
                    debug_log(f"执行任务: {task.task_id}")
                    self.original_execute_task(task)
            debug_log("mock_process_tasks执行完成")
        
        # 替换_process_tasks方法
        debug_log("替换_process_tasks方法前")
        self.task_queue_manager._process_tasks = mock_process_tasks
        debug_log("替换_process_tasks方法完成")
        debug_log("setUp完成")
        
    def tearDown(self):
        debug_log("tearDown开始")
        # 停止任务队列管理器
        self.task_queue_manager.running = False
        # 恢复原始方法
        self.task_queue_manager._execute_task = self.original_execute_task
        self.task_queue_manager._process_tasks = self.original_process_tasks
        # 停止补丁
        self.data_dir_patch.stop()
        self.save_history_patch.stop()
        debug_log("tearDown完成")
        
    def test_task_retry_count_logic(self):
        """测试任务失败重试的执行次数逻辑"""
        try:
            debug_log("test_task_retry_count_logic开始")
            # 最大执行次数
            max_execution_count = 3
            debug_log(f"最大执行次数: {max_execution_count}")
            
            # 创建一个模拟的失败任务回调
            debug_log("定义failing_callback前")
            def failing_callback(params):
                debug_log(f"执行回调，参数: {params}")
                raise Exception("测试失败")
            debug_log("定义failing_callback完成")
            
            # 创建任务对象并手动添加到队列
            debug_log("创建任务对象前")
            task_id = str(uuid.uuid4())
            timestamp = time.time()
            task = Task(
                task_type="test_task",
                task_id=task_id,
                timestamp=timestamp,
                params={"test_param": "value"},
                callback=failing_callback
            )
            task.execution_count = 1  # 初始化为1
            
            info(f"创建任务: task_id={task_id}, execution_count={task.execution_count}")
            debug_log(f"创建任务对象完成: {task_id}")
            
            # 添加任务到队列
            debug_log("添加任务到队列前")
            with self.task_queue_manager.lock:
                self.task_queue_manager.task_queue.put(task)
                self.task_queue_manager.task_history[task_id] = task
            debug_log("添加任务到队列完成")
            
            # 运行_process_tasks来获取任务并开始执行
            info("开始执行第一次任务")
            debug_log("执行第一次任务前")
            self.task_queue_manager._process_tasks()
            debug_log("执行第一次任务完成")
            
            # 获取任务对象
            debug_log("获取任务对象前")
            task = self.task_queue_manager.task_history.get(task_id)
            debug_log(f"获取任务对象完成: {task_id}, 状态: {task.status if task else None}")
            
            if task is None:
                error("任务不在历史记录中")
                self.fail("任务不在历史记录中")
            
            # 验证任务失败，执行次数仍然为1（因为我们在_execute_task中不再增加）
            debug(f"第一次执行后: status={task.status}, execution_count={task.execution_count}")
            debug_log(f"验证第一次执行结果: status={task.status}, execution_count={task.execution_count}")
            self.assertEqual(task.status, "failed", f"第一次执行后状态应为failed，实际为{task.status}")
            self.assertEqual(task.execution_count, 1, f"第一次执行后执行次数应为1，实际为{task.execution_count}")
            info(f"第一次执行成功: status={task.status}, execution_count={task.execution_count}")
            debug_log("第一次执行验证通过")
            
            # 重新入队失败任务 - 这里应该增加执行次数到2
            info("重新入队第一次失败的任务")
            debug_log("重新入队第一次失败任务前")
            requeued_count = self.task_queue_manager.requeue_failed_tasks(max_execution_count=max_execution_count)
            debug_log(f"重新入队第一次失败任务完成，数量: {requeued_count}")
            debug(f"重新入队数量: {requeued_count}")
            
            # 运行_process_tasks来处理重新入队的任务
            info("开始执行第二次任务")
            debug_log("执行第二次任务前")
            self.task_queue_manager._process_tasks()
            debug_log("执行第二次任务完成")
            
            # 再次获取任务对象
            debug_log("获取任务对象前")
            task = self.task_queue_manager.task_history.get(task_id)
            debug_log(f"获取任务对象完成: {task_id}, 状态: {task.status}")
            
            if task is None:
                error("任务不在历史记录中")
                self.fail("任务不在历史记录中")
            
            # 验证任务再次失败，执行次数为2
            debug(f"第二次执行后: status={task.status}, execution_count={task.execution_count}")
            debug_log(f"验证第二次执行结果: status={task.status}, execution_count={task.execution_count}")
            self.assertEqual(task.status, "failed", f"第二次执行后状态应为failed，实际为{task.status}")
            self.assertEqual(task.execution_count, 2, f"第二次执行后执行次数应为2，实际为{task.execution_count}")
            info(f"第二次执行成功: status={task.status}, execution_count={task.execution_count}")
            debug_log("第二次执行验证通过")
            
            # 再次重新入队失败任务 - 这里应该增加执行次数到3
            info("重新入队第二次失败的任务")
            debug_log("重新入队第二次失败任务前")
            requeued_count = self.task_queue_manager.requeue_failed_tasks(max_execution_count=max_execution_count)
            debug_log(f"重新入队第二次失败任务完成，数量: {requeued_count}")
            debug(f"重新入队数量: {requeued_count}")
            
            # 运行_process_tasks来处理再次重新入队的任务
            info("开始执行第三次任务")
            debug_log("执行第三次任务前")
            self.task_queue_manager._process_tasks()
            debug_log("执行第三次任务完成")
            
            # 第三次获取任务对象
            debug_log("获取任务对象前")
            task = self.task_queue_manager.task_history.get(task_id)
            debug_log(f"获取任务对象完成: {task_id}, 状态: {task.status}")
            
            if task is None:
                error("任务不在历史记录中")
                self.fail("任务不在历史记录中")
            
            # 验证任务第三次失败，执行次数为3
            debug(f"第三次执行后: status={task.status}, execution_count={task.execution_count}")
            debug_log(f"验证第三次执行结果: status={task.status}, execution_count={task.execution_count}")
            self.assertEqual(task.status, "failed", f"第三次执行后状态应为failed，实际为{task.status}")
            self.assertEqual(task.execution_count, 3, f"第三次执行后执行次数应为3，实际为{task.execution_count}")
            info(f"第三次执行成功: status={task.status}, execution_count={task.execution_count}")
            debug_log("第三次执行验证通过")
            
            # 再次尝试重新入队失败任务（应该不再重新入队）
            info("尝试重新入队达到最大重试次数的任务")
            debug_log("尝试重新入队达到最大重试次数的任务前")
            requeued_count = self.task_queue_manager.requeue_failed_tasks(max_execution_count=max_execution_count)
            debug_log(f"尝试重新入队达到最大重试次数的任务完成，数量: {requeued_count}")
            debug(f"重新入队数量: {requeued_count}")
            
            # 验证没有任务被重新入队
            debug_log(f"验证重新入队数量: {requeued_count}")
            self.assertEqual(requeued_count, 0, f"达到最大重试次数后不应有任务被重新入队，实际重新入队{requeued_count}个任务")
            info(f"达到最大重试次数后未重新入队任务: requeued_count={requeued_count}")
            debug_log("重新入队数量验证通过")
            
            # 验证任务状态仍然是failed
            debug_log("获取任务对象前")
            task = self.task_queue_manager.task_history.get(task_id)
            debug_log(f"获取任务对象完成: {task_id}, 状态: {task.status}")
            
            if task is None:
                error("任务不在历史记录中")
                self.fail("任务不在历史记录中")
            
            debug_log(f"验证最终状态: {task.status}")
            self.assertEqual(task.status, "failed", f"达到最大重试次数后状态应为failed，实际为{task.status}")
            info(f"最终状态验证成功: status={task.status}")
            debug_log("最终状态验证通过")
            
            info("所有测试验证成功!")
            debug_log("所有测试验证成功!")
        except Exception as e:
            error(f"测试失败: {str(e)}")
            debug_log(f"测试失败: {str(e)}")
            traceback.print_exc()
            self.fail(f"测试失败: {str(e)}")

if __name__ == '__main__':
    info(f"测试脚本启动，进程ID: {os.getpid()}")
    debug_log("测试脚本启动")
    unittest.main()
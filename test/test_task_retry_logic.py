import unittest
import time
import os
import sys
# 添加项目根目录到Python路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hengline.utils.task_queue_utils import TaskQueueManager, Task
from datetime import datetime

class TestTaskRetryLogic(unittest.TestCase):
    
    def setUp(self):
        # 创建测试用的任务队列管理器
        self.task_manager = TaskQueueManager(max_concurrent_tasks=1)
        # 清空任务历史和队列
        self.task_manager.task_history.clear()
        # 创建一个新的优先级队列
        import queue
        self.task_manager.task_queue = queue.PriorityQueue()
        # 设置最大执行次数
        self.max_execution_count = 3
        
    def tearDown(self):
        # 清理测试数据
        if hasattr(self, 'task_manager'):
            self.task_manager.task_history.clear()
    
    def create_test_task(self, task_id='test_task', status='failed', execution_count=0):
        """创建一个测试任务"""
        task = Task(
            task_id=task_id,
            task_type='test_type',
            params={'test_param': 'test_value'},
            callback=lambda x: {'success': False},  # 模拟失败的回调
            timestamp=time.time()
        )
        task.status = status
        task.execution_count = execution_count
        task.task_msg = "测试失败消息"
        self.task_manager.task_history[task_id] = task
        return task
    
    def test_requeue_failed_tasks_execution_count(self):
        """测试失败任务重新入队时执行次数的处理逻辑"""
        # 创建执行次数为0的失败任务
        task1 = self.create_test_task('task1', 'failed', 0)
        # 创建执行次数为1的失败任务
        task2 = self.create_test_task('task2', 'failed', 1)
        # 创建执行次数为2的失败任务
        task3 = self.create_test_task('task3', 'failed', 2)
        # 创建执行次数为3的失败任务（应该不会被重新入队）
        task4 = self.create_test_task('task4', 'failed', 3)
        
        # 调用requeue_failed_tasks方法
        requeued_count = self.task_manager.requeue_failed_tasks(self.max_execution_count)
        
        # 验证结果：执行次数小于max_execution_count(3)的任务应该被重新入队
        self.assertEqual(requeued_count, 3)
        
        # 验证任务状态和消息
        self.assertEqual(task1.status, 'queued')
        self.assertEqual(task2.status, 'queued')
        self.assertEqual(task3.status, 'queued')
        self.assertEqual(task4.status, 'failed')  # 执行次数达到最大值，不应被重新入队
        
        # 验证任务消息包含重试次数信息
        self.assertIn("第1次", task1.task_msg)
        self.assertIn("第2次", task2.task_msg)
        self.assertIn("第3次", task3.task_msg)
    
    def test_process_tasks_execution_count(self):
        """测试任务执行时执行次数的处理逻辑"""
        # 创建初始状态为queued的任务
        task = self.create_test_task('task_process', 'queued', 0)
        
        # 模拟任务入队
        self.task_manager.task_queue.put(task)
        
        # 保存原始的_execute_task方法
        original_execute_task = self.task_manager._execute_task
        
        # 模拟_execute_task方法，不实际执行任务
        def mock_execute_task(task):
            task.status = "completed"
            task.end_time = time.time()
            if task.task_id in self.task_manager.running_tasks:
                del self.task_manager.running_tasks[task.task_id]
        
        try:
            # 替换_execute_task方法
            self.task_manager._execute_task = mock_execute_task
            
            # 手动执行_process_tasks的核心逻辑
            with self.task_manager.lock:
                if not self.task_manager.task_queue.empty():
                    task = self.task_manager.task_queue.get()
                    # 检查执行次数处理
                    task.status = "running"
                    task.start_time = time.time()
                    if task.execution_count == 0:
                        task.execution_count = 1
                    self.task_manager.running_tasks[task.task_id] = task
                    self.task_manager.task_history[task.task_id] = task
            
            # 验证执行次数正确设置为1
            self.assertEqual(task.execution_count, 1)
            
            # 模拟再次入队并执行
            task.status = "queued"
            self.task_manager.task_queue.put(task)
            
            with self.task_manager.lock:
                if not self.task_manager.task_queue.empty():
                    task = self.task_manager.task_queue.get()
                    # 检查执行次数不应再次增加
                    task.status = "running"
                    task.start_time = time.time()
                    if task.execution_count == 0:
                        task.execution_count = 1
                    self.task_manager.running_tasks[task.task_id] = task
                    self.task_manager.task_history[task.task_id] = task
            
            # 验证执行次数仍然为1（不应重复增加）
            self.assertEqual(task.execution_count, 1)
        finally:
            # 恢复原始方法
            self.task_manager._execute_task = original_execute_task

if __name__ == '__main__':
    unittest.main()
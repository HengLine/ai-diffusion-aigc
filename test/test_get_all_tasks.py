import time
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from hengline.utils.task_queue_utils import TaskQueueManager, Task

# 创建任务队列管理器
task_manager = TaskQueueManager(1)

# 清除现有的任务历史记录（仅用于测试）
task_manager.task_history.clear()

# 获取当前日期
today = datetime.now().strftime('%Y-%m-%d')
print(f'今天的日期: {today}')

# 创建一个测试任务，使用当前时间戳
task = Task('text_to_image', 'test_task', time.time(), {'prompt': 'test'}, lambda x: None)
task.status = 'queued'
task.execution_count = 1

# 将任务添加到历史记录
task_manager.task_history[task.task_id] = task

# 查看任务的时间戳和转换后的日期
task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
print(f'任务时间戳: {task.timestamp}, 转换后日期: {task_date}')

# 调用get_all_tasks方法并打印结果
tasks = task_manager.get_all_tasks(date=today)
print(f'通过get_all_tasks获取的任务数量: {len(tasks)}')
if tasks:
    print(f'任务信息: {tasks[0]}')

# 直接访问task_history来验证任务是否存在
print(f'task_history中的任务数量: {len(task_manager.task_history)}')
print(f'任务是否在task_history中: {task.task_id in task_manager.task_history}')

# 手动执行筛选逻辑
today_tasks = task_manager.get_all_tasks(date=today)
unfinished_tasks = [t for t in today_tasks if t['status'] in ['queued', 'running', 'failed']]
eligible_tasks = [t for t in unfinished_tasks if t.get('execution_count', 0) <= 3]
print(f'筛选后符合条件的任务数量: {len(eligible_tasks)}')
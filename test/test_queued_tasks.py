import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from hengline.core.task_queue import TaskQueueManager, Task
from hengline.utils.task_monitor import TaskMonitor
from hengline.logger import debug, info, warning, error

# 创建一个模拟的配置
sys.modules['config'] = type('Config', (), {
    'get': lambda *args, **kwargs: {
        'text_to_image': 'workflows/text_to_image.json',
        'image_to_image': 'workflows/image_to_image.json',
        'text_to_video': 'workflows/text_to_video.json',
        'image_to_video': 'workflows/image_to_video.json'
    }[args[1]] if len(args) > 1 else 'workflows/text_to_image.json'
})

# 创建任务队列管理器
task_manager = TaskQueueManager(1)

# 创建一个模拟的排队中的任务
task = Task('text_to_image', 'test_queued_task', time.time(), {'prompt': 'test prompt'}, lambda x: None)
task.status = 'queued'
task.execution_count = 1

# 将任务添加到历史记录
task_manager.task_history[task.task_id] = task

# 保存初始任务状态
task_manager._save_task_history()

info(f'初始任务状态: status={task.status}, 队列大小={task_manager.task_queue.qsize()}')

# 创建TaskMonitor实例并初始化必要的属性
monitor = TaskMonitor()
monitor.max_execution_count = 3

# 模拟TaskMonitor的comfyui_api_url属性
monitor.comfyui_api_url = 'http://localhost:8188'

# 触发_check_tasks方法来处理排队中的任务
info('触发任务检查...')
monitor._check_tasks()

# 验证结果
debug(f'检查后任务状态: status={task.status}, 队列大小={task_manager.task_queue.qsize()}')

# 验证修复是否有效
if task_manager.task_queue.qsize() > 0:
    info('测试成功: 排队中的任务已被正确地加入队列!')
else:
    error('测试失败: 排队中的任务没有被加入队列!')
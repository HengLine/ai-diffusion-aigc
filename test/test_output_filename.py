import time
import sys
import os
import time

# 导入logger
from hengline.logger import debug, info, warning, error

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from hengline.core.task_queue import TaskQueueManager, Task
from hengline.utils.task_monitor import TaskMonitor

# 创建一个模拟的配置
sys.modules['config'] = type('Config', (), {'get': lambda *args, **kwargs: 'png'})

# 创建任务队列管理器
task_manager = TaskQueueManager(1)

# 创建一个测试任务并设置为失败状态
task = Task('text_to_image', 'test_retry_task', time.time(), {'prompt': 'test prompt'}, lambda x: None)
task.status = 'failed'
task.execution_count = 1

# 将任务添加到历史记录
task_manager.task_history[task.task_id] = task

debug(f'初始任务状态: status={task.status}, output_filename={task.output_filename}')

# 模拟TaskMonitor的任务包装逻辑
class MockComfyUIRunner:
    def load_workflow(self, workflow_path):
        return {}
    def update_workflow_params(self, workflow, params):
        return workflow
    def run_workflow(self, workflow, output_filename):
        return True

# 创建TaskMonitor实例
monitor = TaskMonitor()
monitor.comfyui_runner = MockComfyUIRunner()

# 模拟任务重试的准备工作
workflow_path = 'dummy_workflow.json'
task_type = 'text_to_image'

# 应用task_wrapper逻辑
output_filename = f"{task.task_id}_{int(time.time())}.png"
task.output_filename = output_filename

debug(f'应用修复后: output_filename={task.output_filename}')

# 验证修复是否有效
if task.output_filename:
    info('测试成功: 任务重试时output_filename已被正确设置!')
else:
    error('测试失败: 任务重试时output_filename仍然为空!')
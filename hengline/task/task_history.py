import json
import os
import threading
from datetime import datetime, timedelta

from hengline.logger import error, debug, warning
from hengline.task.task_base import TaskBase
from hengline.task.task_queue import TaskStatus
from hengline.utils.log_utils import print_log_exception


class TaskHistoryManager(TaskBase):
    """任务队列管理器类"""

    def __init__(self):
        super().__init__()
        """
        初始化任务队列管理器

        """
        self.lock = threading.Lock()  # 用于线程同步的主锁

        # 使用异步保存，减少阻塞
        self._save_history_thread = None

    def get_before_history_task(self, task_date: str):
        """从按日期分类的文件加载任务历史 - 优化版本"""
        try:
            tasks = self.cache_query_tasks.get(task_date, None)
            if tasks:
                return tasks

            history_files = self._load_history_files(task_date)
            if not history_files:
                warning(f"没有找到任务历史文件")
                return []

            for file_path in history_files:
                file_name = os.path.basename(file_path)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tasks_data = json.load(f)

                    # 按时间戳排序
                    # tasks_data.sort(key=lambda x: x.timestamp)
                    sorted(tasks_data, key=lambda x: x['timestamp'])

                    tasks = {}
                    for task_data in tasks_data:
                        # 创建任务对象
                        task = self._fill_task_defaults(task_data)
                        tasks[task.task_id] = task

                    self.cache_query_tasks[task_date] = tasks
                    return tasks

                except Exception as e:
                    error(f"处理任务历史文件 {file_name} 失败: {str(e)}")
                    print_log_exception()

        except Exception as e:
            error(f"加载任务历史失败: {str(e)}")
            print_log_exception()

    def async_save_task_history(self):
        """保存任务历史到按日期分类的文件 - 优化版本"""
        # 使用异步保存，减少阻塞
        if not self._save_history_thread or not self._save_history_thread.is_alive():
            self._save_history_thread = threading.Thread(target=self.save_task_history)
            self._save_history_thread.daemon = True
            self._save_history_thread.start()

    def save_task_history(self):
        """异步保存任务历史"""
        try:
            # 创建任务数据的深拷贝
            task_history_copy = self.history_tasks.copy()

            # 按日期分组任务
            tasks_by_date = {}
            for task in task_history_copy.values():
                # 只保存今天和昨天的任务，减少文件操作量
                task_time = datetime.fromtimestamp(task.timestamp)
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday = today - timedelta(days=1)

                # 只处理今天和昨天的任务，以及状态为queued的任务
                if (task_time >= yesterday and task_time < today + timedelta(days=1)) or TaskStatus.is_queued(task.status):
                    task_date = task_time.strftime('%Y-%m-%d')
                    if task_date not in tasks_by_date:
                        tasks_by_date[task_date] = []

                    # 创建可序列化的任务数据
                    task_data = {
                        'task_id': task.task_id,
                        'task_type': task.task_type,
                        'timestamp': task.timestamp,
                        'params': task.params,
                        'status': task.status,
                        'output_filename': task.output_filename,
                        'output_filenames': task.output_filenames,
                        'execution_count': task.execution_count
                    }

                    if task.prompt_id:
                        task_data['prompt_id'] = task.prompt_id

                    # 添加任务消息
                    if task.task_msg:
                        task_data['task_msg'] = task.task_msg

                    # 添加可选字段
                    if task.start_time:
                        task_data['start_time'] = task.start_time
                    if task.end_time:
                        task_data['end_time'] = task.end_time
                        if task.start_time:
                            task_data['duration'] = task.end_time - task.start_time

                    tasks_by_date[task_date].append(task_data)

            # 保存每个日期的任务到对应文件
            for date, tasks in tasks_by_date.items():
                date_file = os.path.join(self.data_dir, f'task_history_{date}.json')

                # 只处理有变化的任务
                if len(tasks) > 0:
                    # 如果文件已存在，先读取现有内容
                    existing_tasks = []
                    if os.path.exists(date_file):
                        try:
                            with open(date_file, 'r', encoding='utf-8') as f:
                                existing_tasks = json.load(f)
                        except:
                            existing_tasks = []

                    # 合并任务数据（避免重复）
                    task_dict = {t['task_id']: t for t in existing_tasks}
                    for task in tasks:
                        task_dict[task['task_id']] = task

                    # 按时间戳排序
                    sorted_tasks = sorted(task_dict.values(), key=lambda x: x['timestamp'])

                    # 保存到文件
                    with open(date_file, 'w', encoding='utf-8') as f:
                        json.dump(sorted_tasks, f, ensure_ascii=False, indent=2)

            debug(f"已异步保存任务历史")
        except Exception as e:
            error(f"异步保存任务历史失败: {str(e)}")
            print_log_exception()


task_history = TaskHistoryManager()

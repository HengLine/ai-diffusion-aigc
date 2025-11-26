"""
@FileName: task_common.py
@Description: 任务通用模块，提供任务管理的通用功能和共享状态
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
import os
import queue
import threading
from datetime import datetime
from typing import Dict

from cachetools import LRUCache
from flask import json

from hengline.logger import info, debug, error, warning
from hengline.task.task_queue import Task, TaskStatus
from utils.config_utils import get_task_config, get_comfyui_config, get_output_folder
from utils.file_utils import file_exists
from utils.log_utils import print_log_exception

"""
@Description:
@Author: HengLine
@Time: 2025/9/17 21:11
"""
class TaskCommonBorg:
    """
        Borg模式 - 共享状态而不是实例
        所有实例共享相同的状态字典
        """
    task_config = get_task_config()
    _lock = threading.RLock()  # 可重入锁，支持嵌套调用
    _initialized = False
    task_locks: Dict[str, threading.Lock] = {}  # 任务级别的锁 {task_id: threading.Lock}
    _task_locks_lock = threading.Lock()  # 用于保护task_locks字典的锁
    running_tasks: Dict[str, Task] = {}  # 当前运行中的任务 {task_id: Task}
    _running_tasks_lock = threading.Lock()  # 用于保护running_tasks字典的锁
    history_tasks: Dict[str, Task] = {}  # 今天的任务记录 {task_id: Task}
    _history_tasks_lock = threading.Lock()  # 用于保护history_tasks字典的锁
    task_queue = queue.PriorityQueue(task_config.get("task_queue_size", 1024))  # 优先队列，按时间戳排序

    # 添加任务类型计数器，用于精确跟踪不同类型任务的排队数量
    # 避免每次查询时遍历整个队列
    _task_type_counters_lock = threading.RLock()
    task_type_counters: Dict[str, int] = {
        "text_to_image": 0,
        "image_to_image": 0,
        "text_to_video": 0,
        "image_to_video": 0
    }

    cache_query_tasks: Dict[str, Dict[str, Task]] = LRUCache(task_config.get("task_cache_size", 1024))  # 用于查询的缓存, 之前的历史记录  {date: {task_id: Task}}
    cache_init_tasks: Dict[str, Task] = {}  # 用于缓存需要初始化处理的任务  {task_id: Task}

    task_max_retry = task_config.get('task_max_retry', 3)  # 最大执行次数
    task_max_concurrent = task_config.get('task_max_concurrent', 3)  # 最大并发任务数
    task_timeout_seconds = task_config.get('task_timeout_seconds', 1800)
    comfyui_api_url = get_comfyui_config().get('api_url', 'http://127.0.0.1:8188')
    output_dir = get_output_folder()

    def __init__(self):
        # 使用锁确保线程安全的属性分配
        with self._lock:
            self.__dict__ = self.running_tasks
            self.__dict__ = self.task_type_counters
            self.__LRUCache__ = self.history_tasks
            self.__PriorityQueue__ = self.task_queue
            self.__threading__ = self._lock
            self.__dict__ = self.task_locks
            self.__threading__ = self._task_locks_lock
            self.__threading__ = self._running_tasks_lock
            self.__threading__ = self._history_tasks_lock
            self.__threading__ = self._task_type_counters_lock

            # 确保基类只初始化一次
            if not self._initialized:
                self._initialize_base()
                self._initialized = True
                info("任务全局器初始化完成")

    def _initialize_base(self):
        """基类初始化方法，只会执行一次"""
        today_date = datetime.now().strftime('%Y-%m-%d')

        # 持久化配置
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

        # 加载已保存的任务历史
        self._initialize_history_task(today_date)

    def _load_history_files(self, today_date: str) -> list:
        # 查找所有历史文件
        history_files = []
        # for filename in os.listdir(self.data_dir):
        #     if filename.startswith('task_history_') and filename.endswith('.json'):
        #         history_files.append(os.path.join(self.data_dir, filename))
        #         debug(f"找到任务历史文件: {filename}")

        # 只加载今天的任务文件，减少文件操作量
        history_files.append(os.path.join(self.data_dir, f'task_history_{today_date}.json'))

        return history_files

    def _initialize_history_task(self, today_date):
        """从按日期分类的文件加载任务历史 - 优化版本"""
        try:
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
                debug(f"创建数据目录: {self.data_dir}")
                return

            history_files = self._load_history_files(today_date)
            if not history_files:
                warning(f"没有找到任务历史文件")
                return

            # 按日期排序，先加载最近的任务
            history_files.sort(reverse=True)
            loaded_task_count = 0

            for file_path in history_files:
                if not file_exists(file_path):
                    warning(f"任务历史文件不存在: {file_path}")
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        tasks_data = json.load(f)

                    # 按时间戳排序
                    sorted(tasks_data, key=lambda x: x['timestamp'])

                    for task_data in tasks_data:
                        # 创建任务对象
                        task = self._fill_task_defaults(task_data)
                        self.history_tasks[task.task_id] = task
                        loaded_task_count += 1

                        self._select_history_task(task)

                except Exception as e:
                    error(f"处理任务历史文件 {os.path.basename(file_path)} 失败: {str(e)}")
                    print_log_exception()

            debug(f"已加载今天历史任务，共 {loaded_task_count} 个任务")
            debug(f"已将今天 {len(self.cache_init_tasks)} 个排队中的任务添加到队列")

        except Exception as e:
            error(f"加载今天的历史失败: {str(e)}")
            print_log_exception()

    def _select_history_task(self, task: Task):
        """从队列中选择任务"""
        # 检查是否未完成（状态为queued、failed或running）
        if TaskStatus.is_success(task.status):
            return

        # 获取今天的日期
        today_date = datetime.now().strftime('%Y-%m-%d')

        # 检查是否为今天的任务
        task_date = datetime.fromtimestamp(task.timestamp).strftime('%Y-%m-%d')
        if task_date != today_date:
            return

        # 检查重试次数是否未超过最大重试次数
        if TaskStatus.is_failed(task.status) and task.execution_count > self.task_max_retry:
            warning(f"任务 {task.task_id} 重试次数已超过{self.task_max_retry}次，跳过处理")
            return

        self.cache_init_tasks[task.task_id] = task
        debug(f"已添加任务 {task.task_id} 到初始化任务列表")

    # 填充任务默认值
    def _fill_task_defaults(self, task_data) -> Task:
        task_lock = self._get_task_lock(task_data['task_id'])

        task = Task(
            task_type=task_data['task_type'],
            task_id=task_data['task_id'],
            timestamp=task_data['timestamp'],
            params=task_data.get('params', {}),
            task_lock=task_lock,  # 传入任务锁
            callback=lambda params: None  # 加载的任务不需要回调函数
        )
        if 'prompt_id' in task_data:
            task.prompt_id = task_data['prompt_id']

        # 恢复输出文件名列表
        if 'output_filenames' in task_data:
            task.output_filenames = task_data['output_filenames']

        # 恢复任务状态
        task.status = task_data.get('status', TaskStatus.QUEUED.value)

        # 恢复任务消息
        if 'task_msg' in task_data:
            task.task_msg = task_data['task_msg']

        # 恢复时间信息
        if 'start_time' in task_data:
            task.start_time = task_data['start_time']
        if 'end_time' in task_data:
            task.end_time = task_data['end_time']

        # 恢复执行次数
        task.execution_count = task_data.get('execution_count', 1)

        return task

    def _get_task_lock(self, task_id: str) -> threading.Lock:
        """获取指定任务的锁，如果不存在则创建"""
        with self._task_locks_lock:
            if task_id not in self.task_locks:
                self.task_locks[task_id] = threading.Lock()
            return self.task_locks[task_id]

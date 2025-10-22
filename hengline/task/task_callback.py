"""
@FileName: task_callback.py
@Description: 任务回调处理器，负责处理任务完成、失败等状态变更时的回调逻辑
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
import os
import time
import weakref

from hengline.logger import debug, warning, error, info
from hengline.task.task_base import TaskBase
from hengline.task.task_email import async_send_failure_email
from hengline.task.task_history import task_history
from hengline.task.task_manage import task_queue_manager
from hengline.task.task_queue import TaskStatus, Task
from hengline.utils.log_utils import print_log_exception


class TaskCallbackHandler(TaskBase):
    def __init__(self):
        super().__init__()

        # 定义回调函数处理工作流完成或失败的情况

    @staticmethod
    def on_error(task, error_message):
        error(f"任务（{task.task_id}）执行失败: {error_message}")
        task.status = TaskStatus.FAILED.value
        task.task_msg = error_message
        # 设置结束时间为当前时间
        if not task.end_time:
            task.end_time = time.time()

    @staticmethod
    def on_complete(task: Task, on_prompt_id, file_names):
        info(f"任务（{task.task_id}）完成，生成文件: {file_names}")
        task.output_filenames = file_names

        # 设置结束时间为当前时间
        if not task.end_time:
            task.end_time = time.time()

        # 定义超时回调函数

    def handle_workflow_timeout(self, task_id, prompt_id):
        try:
            error_msg = f"工作流执行超时，prompt_id: {prompt_id}"
            error(error_msg)
            with self._get_task_lock(task_id):
                if task_id not in self.history_tasks:
                    return

                task = self.history_tasks[task_id]

                # 超时，标记为失败并重试
                if task.execution_count <= self.task_max_retry:
                    warning(f"任务 {task_id} 异步检查超时，重新加入队列")
                    task.status = TaskStatus.QUEUED.value
                    task.task_msg = "ComfyUI 工作流检查超时，任务将在稍后重试"
                    task.end_time = None  # 清除结束时间

                    # 将任务重新加入队列
                    self.add_queue_task(task)

                else:
                    # 超过重试次数，标记为最终失败
                    task.status = TaskStatus.FAILED.value
                    task.task_msg = f"任务执行失败，重试超过{self.task_max_retry}次"
                    task.end_time = time.time()

                    # 发送失败邮件
                    async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)

                # 从运行中任务列表移除
                with self._running_tasks_lock:
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]

                # 保存任务历史
                task_history.async_save_task_history()
                # self.on_error(task_id, error_msg)

        except Exception as e:
            error(f"处理工作流超时回调时出错: {str(e)}")
            print_log_exception()

    # 5. 定义工作流完成处理函数
    # 支持弱引用传参
    def handle_workflow_completion(self, task_id, prompt_id, success, output_name, msg, **kwargs):
        try:
            # msg = kwargs.get("msg", "")
            with self._get_task_lock(task_id):
                if task_id not in self.history_tasks:
                    error(f"任务 {task_id} 不存在于历史任务中，无法处理完成回调")
                    return

                task = self.history_tasks[task_id]
                if success:
                    # 任务完成
                    from hengline.workflow.workflow_comfyui import comfyui_api
                    task.status = TaskStatus.SUCCESS.value
                    task.task_msg = f"任务执行成功，工作流已完成：{msg}"
                    # 获取工作流输出
                    output_path = os.path.join(self.output_dir, output_name)
                    output_success, file_names = comfyui_api.get_workflow_outputs(prompt_id, output_path)
                    if output_success:
                        self.on_complete(task, prompt_id, file_names)
                    else:
                        error_msg = "工作流执行成功但获取输出失败"
                        error(error_msg)
                        self.on_error(task, error_msg)

                    debug(f"任务 {task_id} 已成功处理完成")
                else:
                    # 任务失败，重新加入队列
                    if task.execution_count <= self.task_max_retry:
                        warning(f"任务 {task_id} 在异步检查中失败，重新执行一次")
                        task.status = TaskStatus.QUEUED.value
                        task.task_msg = msg
                        task.end_time = None  # 清除结束时间

                        # 将任务重新加入队列
                        from hengline.workflow.workflow_manage import workflow_manager
                        task_queue_manager.requeue_task(task_id, task.task_type, task.task_msg, weakref.WeakMethod(workflow_manager.execute_common))

                    else:
                        self.on_error(task, f"任务执行失败：已重试超过{self.task_max_retry}次，{msg}")

                        # 发送失败邮件
                        async_send_failure_email(task_id, task.task_type, task.task_msg, task.execution_count)

                # 从运行中任务列表移除
                with self._running_tasks_lock:
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]

                # 保存任务历史
                task_history.async_save_task_history()

        except Exception as e:
            error(f"处理工作流完成回调时出错: {str(e)}")
            print_log_exception()


task_callback_handler = TaskCallbackHandler()

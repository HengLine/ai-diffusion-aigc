# 导入asyncio用于处理协程
import asyncio
import threading
from datetime import datetime

from hengline.logger import error
from hengline.utils.email_utils import email_sender


def _async_send_failure_email(task_id: str, task_type: str, task_msg: str, max_retry_count: int):
    # 异步发送邮件通知
    threading.Thread(
        target=_send_failure_email,
        args=(task_id, task_type, task_msg, max_retry_count),
        daemon=True
    ).start()


def _send_failure_email(task_id: str, task_type: str, task_msg: str, max_execution_count: int):
    """发送任务失败邮件通知"""
    try:
        # 直接同步调用邮件发送函数
        email_sender.send_user_email(
            subject=f"任务 {task_id} 执行失败",
            message=f"您提交的{task_type}任务已重试（{max_execution_count}次），但是由于：{task_msg}，请检查后再次提交任务"
        )
    except Exception as e:
        error(f"发送任务失败，邮件通知失败: {str(e)}")


def _async_send_success_email(task_id: str, task_type: str, start_time: float, end_time: float):
    """异步发送任务成功邮件通知"""
    try:
        # 直接同步调用邮件发送函数
        email_sender.send_user_email(
            subject=f"任务 {task_id} 执行成功",
            message=f"您提交的{task_type}任务已成功完成！\n\n任务类型: {task_type}\n开始时间: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}\n结束时间: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}\n耗时: {end_time - start_time:.1f}秒"
        )
    except Exception as e:
        error(f"发送任务成功邮件通知失败: {str(e)}")

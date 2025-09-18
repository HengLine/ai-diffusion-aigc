# 导入asyncio用于处理协程
from typing import Any

from hengline.logger import debug, error
from hengline.utils.config_utils import get_workflow_preset
from hengline.utils.log_utils import print_log_exception


def get_name_by_type(task_type: str):
    if task_type == 'text_to_image':
        return '文本生图片'
    elif task_type == 'image_to_image':
        return '图片生图片'
    elif task_type == 'image_to_video':
        return '图片生视频'
    elif task_type == 'text_to_video':
        return '文本生视频'
    else:
        return '未知任务类型'


def get_timestamp_by_type() -> dict[str, float]:
    return {
        "text_to_image": 100,  # 默认平均文生图任务时长（秒）
        "image_to_image": 120,  # 默认平均图生图任务时长（秒）
        "text_to_video": 600,  # 默认平均文生视频任务时长（秒）
        "image_to_video": 720  # 默认平均图生视频任务时长（秒）
    }


"""获取各类型任务的平均执行时间（秒）"""


def estimated_waiting_time(task_type: str, waiting_tasks: int, params: dict[str, Any]) -> float:
    """根据任务类型和平均执行时间估算等待时间"""
    # 获取该类型任务的平均执行时间
    avg_duration = get_timestamp_by_type().get(task_type, 100)  # 默认任务执行时间（秒）

    # 预估等待时间 = 前面等待的任务数 * 该类型任务的平均执行时间
    estimated_time_sec = waiting_tasks * avg_duration

    if not params:
        params = get_workflow_preset(task_type)

    if params:
        steps = int(params['steps'])
        width = int(params['width'])
        height = int(params['height'])
        batch_size = int(params['batch_size'])

        if task_type in ['text_to_video', 'image_to_video']:
            length = int(params['length'])
            device = str(params['device'])
            # 对于图像生成任务，考虑分辨率、步数、批量大小等因素
            if device.lower() == 'cpu':  # CPU
                estimated_time_sec *=  5  # 假设CPU比GPU慢5倍
            elif device.lower() == 'gpu':  # GPU
                estimated_time_sec *= 1  # GPU基准
            else:  # 其他设备
                estimated_time_sec *= 1.5  # 假设其他设备比GPU慢1.5倍

            if length:
                estimated_time_sec *= (length / 5)  # 假设基础是5秒

        estimated_time_sec *= (steps / 20)  # 假设基础是20步
        estimated_time_sec *= (batch_size / 1)  # 假设基础是1张
        estimated_time_sec *= (width / 512) * (height / 512)  # 假设基础是1024x1024

    return estimated_time_sec


def update_average_duration(self, task_type: str, duration: float):
    """异步更新任务类型的平均执行时间，避免阻塞主流程"""
    try:
        # 使用简单移动平均，权重为0.8（旧值）和0.2（新值）
        old_avg = get_timestamp_by_type().get(task_type, 60.0)
        new_avg = old_avg * 0.8 + duration * 0.2
        get_timestamp_by_type()[task_type] = new_avg

        debug(f"更新任务类型 {task_type} 的平均执行时间: 旧值={old_avg:.1f}秒, 新值={new_avg:.1f}秒")
    except Exception as e:
        error(f"异步更新平均执行时间失败: {str(e)}")
        print_log_exception()

# 导入asyncio用于处理协程
"""
@FileName: common.py
@Description: 通用工具函数，包含任务类型名称转换、任务执行时间估算等功能
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
from typing import Any

from hengline.logger import debug, error
from utils.config_utils import get_workflow_preset
from utils.log_utils import print_log_exception


def get_name_by_type(task_type: str):
    if task_type == 'text_to_image':
        return '文本生图片'
    elif task_type == 'image_to_image':
        return '图片生图片'
    elif task_type == 'image_to_video':
        return '图片生视频'
    elif task_type == 'text_to_video':
        return '文本生视频'
    elif task_type == 'text_to_audio':
        return '文本生音频'
    elif task_type == 'change_clothes':
        return '换装'
    elif task_type == 'change_face':
        return '换脸'
    elif task_type == 'change_hair_style':
        return '换发型'
    else:
        return '未知任务类型'


def get_timestamp_by_type() -> dict[str, float]:
    return {
        "text_to_image": 10,  # 默认平均文生图任务时长（秒）
        "image_to_image": 20,  # 默认平均图生图任务时长（秒）
        "text_to_video": 300,  # 默认平均文生视频任务时长（秒）
        "image_to_video": 400,  # 默认平均图生视频任务时长（秒）
        "text_to_audio": 10,  # 默认平均文生音频任务时长（秒）
        "change_clothes": 25,  # 默认平均换装任务时长（秒）
        "change_face": 30,  # 默认平均换脸任务时长（秒）
        "change_hair_style": 25,  # 默认平均换发型任务时长（秒）
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
        steps = int(params.get('steps', 20))
        batch_size = int(params.get('batch_size', 1))
        estimated_time_sec *= (steps / 20)  # 假设基础是20步
        estimated_time_sec *= (batch_size / 1)  # 假设基础是1张

        device = str(params.get('device', 'gpu'))
        if device and device.lower() == 'cpu':  # CPU
            estimated_time_sec *= 50  # 假设CPU比GPU慢50倍

        if task_type == 'text_to_audio':
            seconds = int(params.get('seconds', 10))
            estimated_time_sec *= (seconds / 10)  # 假设基础是5秒

        else:
            width = int(params.get('width', 512))
            height = int(params.get('height', 512))
            estimated_time_sec *= (width / 512) * (height / 512)  # 假设基础是1024x1024

            if task_type in ['text_to_video', 'image_to_video']:
                fps = int(params.get('fps', 16))
                length = int(params.get('length', 5))  # 视频长度，单位秒
                # 对于图像生成任务，考虑分辨率、步数、批量大小等因素
                if device and device.lower() == 'cpu':  # CPU
                    estimated_time_sec *=  2  # 假设CPU比GPU慢100倍
                if length:
                    estimated_time_sec *= (length / 5)  # 假设基础是5秒
                if fps:
                    estimated_time_sec *= (fps / 16)  # 假设基础是16fps


    return estimated_time_sec


def update_average_duration(task_type: str, duration: float):
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

# 导入asyncio用于处理协程
from hengline.logger import debug, error
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
        "text_to_video": 500,  # 默认平均文生视频任务时长（秒）
        "image_to_video": 600  # 默认平均图生视频任务时长（秒）
    }


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

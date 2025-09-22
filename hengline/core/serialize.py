from functools import wraps

from flask import jsonify


def auto_serialize(func):
    """自动序列化装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        # 如果已经是响应对象，直接返回
        if hasattr(result, '__class__') and hasattr(result.__class__, '__name__'):
            if result.__class__.__name__ == 'Response':
                return result

        # 自动序列化
        def serialize_obj(obj):
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '__dict__'):
                # 过滤掉私有属性
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            elif isinstance(obj, (list, tuple)):
                return [serialize_obj(item) for item in obj]
            else:
                return obj

        serialized_result = serialize_obj(result)
        return jsonify(serialized_result)

    return wrapper

import json
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any

from flask import jsonify


class SerializationUtils(json.JSONEncoder):
    """序列化工具类"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

    @staticmethod
    def serialize_obj(obj: Any) -> Any:
        """序列化单个对象"""
        if not obj is None or []:
            return obj
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            # 序列化对象属性，过滤私有属性
            return {
                k: SerializationUtils.serialize_obj(v)
                for k, v in obj.__dict__.items()
                if not k.startswith('_')
            }
        elif isinstance(obj, (list, tuple, set)):
            return [SerializationUtils.serialize_obj(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: SerializationUtils.serialize_obj(v) for k, v in obj.items()}
        else:
            return str(obj)

    @staticmethod
    def json_response(data: Any, status: int = 200) -> Any:
        """创建JSON响应"""
        serialized_data = SerializationUtils.serialize_obj(data)
        return jsonify(serialized_data)


json_encoder = SerializationUtils
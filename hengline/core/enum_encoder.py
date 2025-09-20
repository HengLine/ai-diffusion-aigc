from enum import Enum
from json import JSONEncoder
from typing import Any


class EnhancedEnumEncoder(JSONEncoder):
    """增强的枚举JSON编码器"""

    def default(self, obj: Any) -> Any:
        # 处理枚举类型
        if isinstance(obj, Enum):
            return self.serialize_enum(obj)

        # 处理包含枚举的字典、列表等
        if isinstance(obj, dict):
            return {k: self.default(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple, set)):
            return [self.default(item) for item in obj]

        return super().default(obj)

    def serialize_enum(self, enum_obj: Enum) -> Any:
        """序列化枚举对象"""
        return enum_obj.value
        # 可以根据需要返回不同的格式
        # return {
        #     'name': enum_obj.name,
        #     'value': enum_obj.value,
        #     '_type': type(enum_obj).__name__
        # }

"""
@FileName: error_code.py
@Description: 错误码枚举类，定义系统中使用的各种错误代码和消息
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
from enum import Enum

class ErrorCode(Enum):
    SUCCESS = (0, "操作成功")
    INVALID_INPUT = (1001, "输入参数无效")
    UNAUTHORIZED = (1002, "未授权访问")
    NOT_FOUND = (1003, "资源未找到")
    INTERNAL_ERROR = (5000, "服务器内部错误")

    def __init__(self, code, message):
        self._code = code
        self._message = message

    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._message

    @classmethod
    def from_code(cls, code):
        for error in cls:
            if error.code == code:
                return error
        return cls.INTERNAL_ERROR

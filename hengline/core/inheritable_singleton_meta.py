"""
@FileName: inheritable_singleton_meta.py
@Description: 支持继承的单例元类实现，每个子类都有自己的单例实例
@Author: HengLine
@Time: 2025/08 - 2025/11
"""


class InheritableSingletonMeta(type):
    """支持继承的单例元类"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # 每个子类都有自己的单例实例
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

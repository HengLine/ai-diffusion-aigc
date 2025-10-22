"""
@FileName: shared_singleton_meta.py
@Description: 共享单例元类实现，所有子类共享同一个实例
@Author: HengLine
@Time: 2025/08 - 2025/11
"""


class SharedSingletonMeta(type):
    """
    共享单例元类 - 所有子类共享同一个实例
    """
    _shared_instance = None

    def __call__(cls, *args, **kwargs):
        if SharedSingletonMeta._shared_instance is None:
            # 创建第一个实例
            SharedSingletonMeta._shared_instance = super().__call__(*args, **kwargs)
        return SharedSingletonMeta._shared_instance

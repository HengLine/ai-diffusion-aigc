"""
@FileName: singleton_meta.py
@Description: 单例模式元类实现，确保类只有一个实例
@Author: HengLine
@Time: 2025/08 - 2025/11
"""
import threading

class SingletonMeta(type):
    """单例元类"""
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]
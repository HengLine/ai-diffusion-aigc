class InheritableSingletonMeta(type):
    """支持继承的单例元类"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # 每个子类都有自己的单例实例
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

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

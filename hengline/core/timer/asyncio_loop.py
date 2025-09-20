import asyncio
from threading import Lock


class GlobalEventLoop:
    """全局事件循环管理器"""
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_loop()
            return cls._instance

    def _init_loop(self):
        """初始化事件循环"""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def run_async(self, coroutine, timeout=30):
        """运行异步任务"""
        try:
            return self.loop.run_until_complete(
                asyncio.wait_for(coroutine, timeout=timeout)
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"任务超时 ({timeout}秒)")
        except Exception as e:
            raise RuntimeError(f"任务执行错误: {e}")

    def shutdown(self):
        """关闭事件循环"""
        if hasattr(self, 'loop') and not self.loop.is_closed():
            self.loop.close()


# 使用示例
async def production_task(n):
    await asyncio.sleep(5)
    return f"{n}生产任务完成"


# 获取全局事件循环
loop_manager = GlobalEventLoop()

if __name__ == '__main__':
    try:
        result = loop_manager.run_async(production_task(1), timeout=10)
        print(f"生产任务结果: {result}")
        result = loop_manager.run_async(production_task(2), timeout=4)
        print(f"生产任务结果: {result}")
    except (TimeoutError, RuntimeError) as e:
        print(f"任务执行失败: {e}")

    # 程序退出时清理
    import atexit

    atexit.register(loop_manager.shutdown)

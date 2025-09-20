import asyncio
from datetime import datetime


class AsyncTimer:
    """异步定时任务执行器"""

    def __init__(self):
        self.tasks = []
        self.is_running = False

    async def periodic_task(self, interval, func, *args, **kwargs):
        """周期性异步任务"""
        while self.is_running:
            try:
                # 执行任务
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    # 如果是同步函数，在线程中执行
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, func, *args, **kwargs)
            except Exception as e:
                print(f"异步任务执行错误: {e}")

            # 等待指定间隔
            await asyncio.sleep(interval)

    def add_task(self, interval, func, *args, **kwargs):
        """添加异步任务"""
        task = self.periodic_task(interval, func, *args, **kwargs)
        self.tasks.append(task)
        print(f"添加异步任务，间隔: {interval}秒")

    async def start(self):
        """启动所有任务"""
        self.is_running = True
        print("异步定时器启动")

        # 启动所有任务
        await asyncio.gather(*self.tasks)

    def stop(self):
        """停止所有任务"""
        self.is_running = False
        print("异步定时器停止")


# 异步任务示例 async
async def async_backup():
    print(f"[异步备份] {datetime.now()}")
    await asyncio.sleep(0.5)  # 模拟异步操作


def sync_cleanup():
    print(f"[同步清理] {datetime.now()}")


# 使用示例
async def main():
    timer = AsyncTimer()

    # 添加任务
    timer.add_task(3, async_backup)  # 每3秒执行异步任务
    timer.add_task(5, sync_cleanup)  # 每5秒执行同步任务

    # 启动定时器，运行20秒
    try:
        await asyncio.wait_for(timer.start(), timeout=20)
    except asyncio.TimeoutError:
        timer.stop()
        print("运行超时，定时器停止")

# 运行异步主函数
# asyncio.run(main())

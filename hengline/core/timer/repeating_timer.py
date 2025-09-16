import threading
import time


class RepeatingTimer:
    """可重复执行的定时器"""

    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.timer = None
        self.is_running = False
        self.start_time = None

    def _run(self):
        """内部运行方法"""
        if self.is_running:
            self.function(*self.args, **self.kwargs)
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()

    def start(self):
        """启动定时器"""
        if not self.is_running:
            self.is_running = True
            self.start_time = time.time()
            self._run()
            print(f"定时器启动，间隔: {self.interval}秒")

    def stop(self):
        """停止定时器"""
        if self.is_running:
            self.is_running = False
            if self.timer:
                self.timer.cancel()
            run_time = time.time() - self.start_time
            print(f"定时器停止，总共运行: {run_time:.2f}秒")

    def change_interval(self, new_interval):
        """改变执行间隔"""
        if self.is_running:
            self.stop()
            self.interval = new_interval
            self.start()
            print(f"间隔已改为: {new_interval}秒")


# 使用示例
def sample_task(task_id):
    print(f"任务 {task_id} 执行 - {time.strftime('%H:%M:%S')}")


if __name__ == '__main__':
    # 创建定时器，每3秒执行一次
    timer = RepeatingTimer(3, sample_task, "日常检查")

    # 启动定时器
    # timer.start()

    # 运行一段时间后停止
    # time.sleep(15)
    # timer.stop()

    # 改变间隔后重新启动
    # timer.change_interval(1)
    # time.sleep(10)
    # timer.stop()

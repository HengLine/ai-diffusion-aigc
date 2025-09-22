from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import time

class AdvancedScheduler:
    """高级定时任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs = {}

    def add_interval_job(self, job_id, func, interval_seconds, *args, **kwargs):
        """添加间隔任务"""
        trigger = IntervalTrigger(seconds=interval_seconds)
        job = self.scheduler.add_job(
            func, trigger, id=job_id,
            args=args, kwargs=kwargs,
            misfire_grace_time=60  # 允许60秒的误差
        )
        self.jobs[job_id] = job
        print(f"添加间隔任务 '{job_id}', 间隔: {interval_seconds}秒")

    def add_cron_job(self, job_id, func, cron_expression, *args, **kwargs):
        """添加Cron表达式任务"""
        from apscheduler.triggers.cron import CronTrigger

        # cron_expression 格式: "分 时 日 月 周"
        trigger = CronTrigger.from_crontab(cron_expression)
        job = self.scheduler.add_job(
            func, trigger, id=job_id,
            args=args, kwargs=kwargs
        )
        self.jobs[job_id] = job
        print(f"添加Cron任务 '{job_id}', 表达式: {cron_expression}")

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        print("高级调度器已启动")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        print("高级调度器已停止")

    def list_jobs(self):
        """列出所有任务"""
        print("当前任务列表:")
        for job_id, job in self.jobs.items():
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else "无"
            print(f"  {job_id}: 下次运行 {next_run}")

    def remove_job(self, job_id):
        """移除任务"""
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            print(f"已移除任务: {job_id}")


# 使用示例
def backup_task():
    print(f"[备份] {datetime.now()}")


def cleanup_task():
    print(f"[清理] {datetime.now()}")


def report_task():
    print(f"[报表] {datetime.now()}")


if __name__ == '__main__':
    # 创建高级调度器
    advanced_scheduler = AdvancedScheduler()

    # 添加各种任务
    advanced_scheduler.add_interval_job("backup", backup_task, 5)  # 每5秒
    advanced_scheduler.add_interval_job("cleanup", cleanup_task, 10)  # 每10秒
    advanced_scheduler.add_cron_job("daily_report", report_task, "0 9 * * *")  # 每天9点

    # 启动调度器
    # advanced_scheduler.start()
    # advanced_scheduler.list_jobs()

    # 运行一段时间
    # time.sleep(25)

    # 停止调度器
    # advanced_scheduler.stop()
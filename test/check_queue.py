import requests
import time
import requests

# 添加项目根目录到Python路径
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hengline.logger import info, debug, error

# 检查任务队列状态
info("检查任务队列状态...")
info(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    # 发送GET请求到任务队列状态端点
    response = requests.get(
        'http://localhost:5000/api/task_queue/status',
        timeout=10  # 设置10秒超时
    )
    
    # 打印状态码和响应内容
    info(f"状态码: {response.status_code}")
    debug(f"响应内容: {response.text}")
    
    # 如果是JSON格式，解析并展示
    if 'application/json' in response.headers.get('Content-Type', ''):
        data = response.json()
        info("\n任务队列详细信息:")
        info(f"- 运行中任务数: {data.get('running_tasks_count', 0)}")
        info(f"- 等待中任务数: {data.get('queued_tasks_count', 0)}")
        info(f"- 最大并发任务数: {data.get('max_concurrent_tasks', 0)}")
        info(f"- 各类任务平均执行时长:")
        for task_type, avg_time in data.get('avg_execution_time', {}).items():
            info(f"  - {task_type}: {avg_time}秒")
    
    info(f"\n测试结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
except requests.exceptions.Timeout:
    error("错误: 请求超时")
except requests.exceptions.ConnectionError:
    error("错误: 无法连接到服务器，服务可能未启动")
except Exception as e:
    error(f"错误: {str(e)}")
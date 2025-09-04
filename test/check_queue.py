import requests
import time

# 检查任务队列状态
print("检查任务队列状态...")
print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    # 发送GET请求到任务队列状态端点
    response = requests.get(
        'http://localhost:5000/api/task_queue/status',
        timeout=10  # 设置10秒超时
    )
    
    # 打印状态码和响应内容
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 如果是JSON格式，解析并展示
    if 'application/json' in response.headers.get('Content-Type', ''):
        data = response.json()
        print("\n任务队列详细信息:")
        print(f"- 运行中任务数: {data.get('running_tasks_count', 0)}")
        print(f"- 等待中任务数: {data.get('queued_tasks_count', 0)}")
        print(f"- 最大并发任务数: {data.get('max_concurrent_tasks', 0)}")
        print(f"- 各类任务平均执行时长:")
        for task_type, avg_time in data.get('avg_execution_time', {}).items():
            print(f"  - {task_type}: {avg_time}秒")
    
    print(f"\n测试结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
except requests.exceptions.Timeout:
    print("错误: 请求超时")
except requests.exceptions.ConnectionError:
    print("错误: 无法连接到服务器，服务可能未启动")
except Exception as e:
    print(f"错误: {str(e)}")
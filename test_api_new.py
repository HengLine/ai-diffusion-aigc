import requests
import time

try:
    print(f"测试API接口: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    url = "http://localhost:5000/api/task_queue/status"
    
    # 设置超时时间
    response = requests.get(url, timeout=10)
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应内容: {response.json()}")
    else:
        print(f"错误: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"请求异常: {str(e)}")

print("\n测试get_all_tasks接口:")
try:
    url = "http://localhost:5000/api/task_queue/all_tasks"
    response = requests.get(url, timeout=10)
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"响应成功，任务数量: {len(data.get('data', []))}")
    else:
        print(f"错误: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"请求异常: {str(e)}")
import requests
import time

try:
    print(f"检查API错误: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    url = "http://localhost:5000/api/task_queue/status"
    
    # 设置较短的超时时间
    response = requests.get(url, timeout=10)
    
    print(f"状态码: {response.status_code}")
    
    # 尝试解析JSON响应
    try:
        error_data = response.json()
        print(f"错误详情: {error_data}")
    except ValueError:
        # 如果不是JSON格式，打印原始文本
        print(f"响应内容: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"请求异常: {str(e)}")
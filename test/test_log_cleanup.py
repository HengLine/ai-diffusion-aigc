import os
import sys
import datetime
import shutil

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hengline.logger import Logger

# 测试日志文件自动清理功能
def test_log_cleanup():
    # 1. 创建一个临时日志目录用于测试
    test_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_logs")
    
    # 确保测试目录为空
    if os.path.exists(test_log_dir):
        shutil.rmtree(test_log_dir)
    os.makedirs(test_log_dir, exist_ok=True)
    
    # 2. 创建测试日志文件
    # 创建1个今天的日志文件
    today = datetime.date.today()
    today_log = os.path.join(test_log_dir, f"test_logger_{today.strftime('%Y-%m-%d')}.log")
    with open(today_log, 'w') as f:
        f.write(f"这是今天的日志文件 {today}")
    print(f"创建今天的日志文件: {today_log}")
    
    # 创建1个昨天的日志文件
    yesterday = today - datetime.timedelta(days=1)
    yesterday_log = os.path.join(test_log_dir, f"test_logger_{yesterday.strftime('%Y-%m-%d')}.log")
    with open(yesterday_log, 'w') as f:
        f.write(f"这是昨天的日志文件 {yesterday}")
    print(f"创建昨天的日志文件: {yesterday_log}")
    
    # 创建1个10天前的日志文件
    ten_days_ago = today - datetime.timedelta(days=10)
    ten_days_ago_log = os.path.join(test_log_dir, f"test_logger_{ten_days_ago.strftime('%Y-%m-%d')}.log")
    with open(ten_days_ago_log, 'w') as f:
        f.write(f"这是10天前的日志文件 {ten_days_ago}")
    print(f"创建10天前的日志文件: {ten_days_ago_log}")
    
    # 创建1个20天前的日志文件（应该被清理）
    twenty_days_ago = today - datetime.timedelta(days=20)
    twenty_days_ago_log = os.path.join(test_log_dir, f"test_logger_{twenty_days_ago.strftime('%Y-%m-%d')}.log")
    with open(twenty_days_ago_log, 'w') as f:
        f.write(f"这是20天前的日志文件 {twenty_days_ago}")
    print(f"创建20天前的日志文件: {twenty_days_ago_log}")
    
    # 创建1个带序号的过期日志文件（应该被清理）
    twenty_days_ago_indexed = os.path.join(test_log_dir, f"test_logger_{twenty_days_ago.strftime('%Y-%m-%d')}_1.log")
    with open(twenty_days_ago_indexed, 'w') as f:
        f.write(f"这是20天前的带序号日志文件 {twenty_days_ago}")
    print(f"创建20天前的带序号日志文件: {twenty_days_ago_indexed}")
    
    # 创建一个非日志文件（不应该被清理）
    non_log_file = os.path.join(test_log_dir, "not_a_log.txt")
    with open(non_log_file, 'w') as f:
        f.write("这不是一个日志文件，不应该被清理")
    print(f"创建非日志文件: {non_log_file}")
    
    # 3. 初始化Logger来触发日志清理
    print("\n初始化Logger，触发日志清理...")
    # 设置max_days=15，应该清理20天前的文件，保留10天内的文件
    logger = Logger(name="test_logger", log_dir=test_log_dir, max_bytes=10*1024*1024)
    
    # 4. 验证结果
    print("\n验证清理结果:")
    
    # 检查今天的文件是否存在
    today_exists = os.path.exists(today_log)
    print(f"今天的日志文件是否存在: {today_exists}")
    assert today_exists, "今天的日志文件应该存在"
    
    # 检查昨天的文件是否存在
    yesterday_exists = os.path.exists(yesterday_log)
    print(f"昨天的日志文件是否存在: {yesterday_exists}")
    assert yesterday_exists, "昨天的日志文件应该存在"
    
    # 检查10天前的文件是否存在
    ten_days_ago_exists = os.path.exists(ten_days_ago_log)
    print(f"10天前的日志文件是否存在: {ten_days_ago_exists}")
    assert ten_days_ago_exists, "10天前的日志文件应该存在"
    
    # 检查20天前的文件是否被删除
    twenty_days_ago_exists = os.path.exists(twenty_days_ago_log)
    print(f"20天前的日志文件是否存在: {twenty_days_ago_exists}")
    assert not twenty_days_ago_exists, "20天前的日志文件应该被删除"
    
    # 检查带序号的过期文件是否被删除
    twenty_days_ago_indexed_exists = os.path.exists(twenty_days_ago_indexed)
    print(f"20天前的带序号日志文件是否存在: {twenty_days_ago_indexed_exists}")
    assert not twenty_days_ago_indexed_exists, "20天前的带序号日志文件应该被删除"
    
    # 检查非日志文件是否保留
    non_log_exists = os.path.exists(non_log_file)
    print(f"非日志文件是否存在: {non_log_exists}")
    assert non_log_exists, "非日志文件应该保留"
    
    print("\n测试完成！日志清理功能工作正常。")
    
    # 清理测试目录，但添加异常处理
    try:
        if os.path.exists(test_log_dir):
            # 强制关闭可能打开的文件句柄
            import gc
            gc.collect()
            
            # 尝试删除目录，如果失败则跳过
            try:
                shutil.rmtree(test_log_dir)
                print(f"已清理测试目录: {test_log_dir}")
            except PermissionError:
                print(f"警告: 无法立即删除测试目录 {test_log_dir}，可能有文件被占用")
    except Exception as e:
        print(f"清理测试目录时出错: {str(e)}")
    
if __name__ == "__main__":
    test_log_cleanup()
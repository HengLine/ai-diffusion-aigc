"""
RocketMQ使用示例

本文件展示了如何使用hengline.mq模块中的RocketMQ组件来发送和接收消息。

使用前请确保：
1. 已安装rocketmq-client-python依赖（非Windows系统）
2. 已配置好RocketMQ服务
3. 如果需要自定义配置，可以在config.json的settings.rocketmq部分修改配置
   或者通过环境变量设置（优先级更高）
"""

import platform
import time

# 检查是否为Windows系统
IS_WINDOWS = platform.system() == 'Windows'

# Windows系统下提供Mock实现
if IS_WINDOWS:
    print("警告: RocketMQ不支持Windows系统，示例将使用模拟实现")
    
    # Mock SendStatus枚举
    class SendStatus:
        SEND_OK = 0
        FLUSH_DISK_TIMEOUT = 1
        FLUSH_SLAVE_TIMEOUT = 2
        SLAVE_NOT_AVAILABLE = 3
    
    # 从hengline.mq导入组件（在Windows下会使用模拟实现）
    from hengline.mq import (
        RocketMQProducer,
        RocketMQConsumer,
        get_default_producer,
        get_default_consumer,
        rocketmq_config,
        get_producer_pool,
        get_consumer_pool,
        shutdown_all_pools
    )
else:
    # 非Windows系统导入实际的RocketMQ组件
    from rocketmq.client import SendStatus
    
    # 导入RocketMQ组件
    from hengline.mq import (
        RocketMQProducer,
        RocketMQConsumer,
        get_default_producer,
        get_default_consumer,
        rocketmq_config,
        get_producer_pool,
        get_consumer_pool,
        shutdown_all_pools
    )


# 示例：使用默认生产者发送消息
def producer_example():
    """生产者示例"""
    print("\n===== 生产者示例 =====")
    
    # 获取默认生产者实例
    producer = get_default_producer()
    
    try:
        # 示例1：发送同步消息
        print("\n1. 发送同步消息：")
        success = producer.send_sync_message(
            topic="test_topic",
            message_body="Hello RocketMQ - Synchronous Message",
            tags="sync_tag",
            keys="sync_message_key"
        )
        print(f"同步消息发送{'成功' if success else '失败'}")
        
        # 示例2：发送异步消息
        print("\n2. 发送异步消息：")
        
        def async_callback(send_result):
            if send_result.status == SendStatus.SEND_OK:
                print(f"异步消息发送成功，消息ID: {send_result.msg_id}")
            else:
                print(f"异步消息发送失败，状态: {send_result.status}")
        
        producer.send_async_message(
            topic="test_topic",
            message_body="Hello RocketMQ - Asynchronous Message",
            callback=async_callback,
            tags="async_tag",
            keys="async_message_key"
        )
        
        # 等待异步消息回调完成
        time.sleep(1)
        
        # 示例3：发送单向消息（不关心发送结果）
        print("\n3. 发送单向消息：")
        producer.send_oneway_message(
            topic="test_topic",
            message_body="Hello RocketMQ - Oneway Message",
            tags="oneway_tag",
            keys="oneway_message_key"
        )
        print("单向消息已发送（不等待确认）")
        
        # 示例4：使用自定义配置创建生产者
        print("\n4. 使用自定义配置创建生产者：")
        custom_producer = RocketMQProducer({
            'group_name': 'custom_producer_group',
            'name_server_address': rocketmq_config.name_server_address,
            'instance_name': 'custom_producer_instance',
            'retry_times': 5
        })
        
        custom_success = custom_producer.send_sync_message(
            topic="test_topic",
            message_body="Hello RocketMQ - Custom Producer Message",
            tags="custom_tag"
        )
        print(f"自定义生产者消息发送{'成功' if custom_success else '失败'}")
        
        # 关闭自定义生产者
        custom_producer.shutdown()
        
    finally:
        # 关闭默认生产者
        producer.shutdown()
        

# 示例：使用消费者接收消息
def consumer_example():
    """消费者示例"""
    print("\n===== 消费者示例 =====")
    
    # 获取默认消费者实例
    consumer = get_default_consumer()
    
    try:
        # 示例1：使用默认消息处理器订阅主题
        print("\n1. 使用默认消息处理器订阅主题：")
        consumer.subscribe("test_topic", "*")
        
        # 等待消息接收（实际应用中，这部分应该在后台运行）
        print("已订阅主题'test_topic'，等待接收消息...")
        print("（注意：此示例为了演示会立即返回，实际应用中可能需要持续监听）")
        print("按Ctrl+C结束消费示例")
        
        # 示例2：使用自定义消息处理器订阅主题
        print("\n2. 使用自定义消息处理器订阅主题：")
        
        def custom_message_handler(msg):
            try:
                # 获取消息内容
                msg_body = msg.body.decode('utf-8')
                print(f"\n接收到消息：")
                print(f"  主题: {msg.topic}")
                print(f"  标签: {msg.tags}")
                print(f"  键值: {msg.keys}")
                print(f"  内容: {msg_body}")
                print(f"  消息ID: {msg.id}")
                print(f"  存储时间: {msg.store_time}")
                
                # 返回True表示消息处理成功，返回False表示需要重试
                return True
            except Exception as e:
                print(f"处理消息时发生错误: {str(e)}")
                return False
        
        # 取消之前的订阅
        consumer.unsubscribe("test_topic")
        
        # 使用自定义处理器订阅主题
        consumer.subscribe("test_topic", "*", custom_message_handler)
        
        # 在实际应用中，这里应该是一个长时间运行的循环
        # 为了演示，我们只等待5秒
        print("\n使用自定义处理器订阅主题'test_topic'，等待5秒...")
        time.sleep(5)
        
        # 示例3：使用自定义配置创建消费者
        print("\n3. 使用自定义配置创建消费者：")
        custom_consumer = RocketMQConsumer({
            'group_name': 'custom_consumer_group',
            'name_server_address': rocketmq_config.name_server_address,
            'instance_name': 'custom_consumer_instance'
        })
        
        custom_consumer.subscribe("test_topic", "sync_tag", custom_message_handler)
        print("自定义消费者已订阅'test_topic'，标签为'sync_tag'")
        
        # 等待2秒
        time.sleep(2)
        
        # 关闭自定义消费者
        custom_consumer.shutdown()
        
    finally:
        # 关闭默认消费者
        consumer.shutdown()
        print("\n消费者已关闭")


# 主函数，运行示例
def main():
    """运行所有示例"""
    try:
        # 打印当前使用的RocketMQ配置
        print("当前使用的RocketMQ配置：")
        print(f"  名称服务器地址: {rocketmq_config.name_server_address}")
        print(f"  生产者组: {rocketmq_config.producer_group}")
        print(f"  消费者组: {rocketmq_config.consumer_group}")
        print(f"  实例名称: {rocketmq_config.instance_name}")
        print(f"  重试次数: {rocketmq_config.retry_times}")
        
        # 运行生产者示例
        producer_example()
        
        # 运行消费者示例
        consumer_example()
        
    except KeyboardInterrupt:
        print("\n示例已被用户中断")
    except Exception as e:
        print(f"示例运行出错: {str(e)}")
        import traceback
        traceback.print_exc()


# 示例：使用连接池管理RocketMQ连接
def connection_pool_example():
    """连接池示例"""
    print("\n===== 连接池示例 =====")
    
    # 导入连接池相关组件
    from hengline.mq import (
        get_producer_pool,
        get_consumer_pool,
        shutdown_all_pools
    )
    
    # 获取生产者连接池
    producer_pool = get_producer_pool(max_connections=3)  # 设置最大连接数为3
    
    try:
        print("\n1. 使用生产者连接池发送消息：")
        
        # 示例1：使用上下文管理器获取和归还连接
        print("\n1.1 使用上下文管理器获取连接：")
        with producer_pool.get_connection() as producer:
            success = producer.send_sync_message(
                topic="test_topic",
                message_body="Hello RocketMQ - Connection Pool Message (Context Manager)",
                tags="pool_tag",
                keys="pool_message_key"
            )
            print(f"连接池消息发送{'成功' if success else '失败'}")
        
        # 示例2：手动获取和归还连接
        print("\n1.2 手动获取和归还连接：")
        connection = producer_pool.get_connection()
        try:
            producer = connection.connection
            success = producer.send_sync_message(
                topic="test_topic",
                message_body="Hello RocketMQ - Connection Pool Message (Manual)",
                tags="pool_tag",
                keys="pool_message_key_manual"
            )
            print(f"手动连接池消息发送{'成功' if success else '失败'}")
        finally:
            # 手动归还连接
            producer_pool.return_connection(connection)
        
        # 示例3：并发使用连接池
        print("\n1.3 并发使用连接池：")
        import threading
        
        def send_message_thread(thread_id):
            try:
                with producer_pool.get_connection() as producer:
                    success = producer.send_sync_message(
                        topic="test_topic",
                        message_body=f"Hello RocketMQ - Thread {thread_id}",
                        tags=f"thread_{thread_id}_tag",
                        keys=f"thread_{thread_id}_key"
                    )
                    print(f"线程 {thread_id} 消息发送{'成功' if success else '失败'}")
            except Exception as e:
                print(f"线程 {thread_id} 出错: {str(e)}")
        
        # 创建多个线程同时使用连接池
        threads = []
        for i in range(5):  # 创建5个线程，但连接池最大连接数为3
            thread = threading.Thread(target=send_message_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 示例4：使用消费者连接池
        print("\n2. 使用消费者连接池接收消息：")
        
        # 获取消费者连接池
        consumer_pool = get_consumer_pool(max_connections=2)
        
        # 定义消息处理器
        def pool_message_handler(msg):
            try:
                msg_body = msg.body.decode('utf-8')
                print(f"\n连接池消费者接收到消息：")
                print(f"  主题: {msg.topic}")
                print(f"  标签: {msg.tags}")
                print(f"  内容: {msg_body}")
                return True
            except Exception as e:
                print(f"处理消息时发生错误: {str(e)}")
                return False
        
        # 获取一个消费者连接并订阅主题
        with consumer_pool.get_connection() as consumer:
            consumer.subscribe("test_topic", "pool_tag", pool_message_handler)
            print("连接池消费者已订阅主题'test_topic'，标签为'pool_tag'")
            print("等待5秒接收消息...")
            time.sleep(5)
            
    except Exception as e:
        print(f"连接池示例运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭所有连接池（在实际应用中，这通常在应用退出时执行）
        print("\n关闭所有连接池...")
        shutdown_all_pools()
        print("所有连接池已关闭")


# 更新主函数，添加连接池示例
def main():
    """运行所有示例"""
    try:
        # 打印当前使用的RocketMQ配置
        print("当前使用的RocketMQ配置：")
        print(f"  名称服务器地址: {rocketmq_config.name_server_address}")
        print(f"  生产者组: {rocketmq_config.producer_group}")
        print(f"  消费者组: {rocketmq_config.consumer_group}")
        print(f"  实例名称: {rocketmq_config.instance_name}")
        print(f"  重试次数: {rocketmq_config.retry_times}")
        
        # 运行生产者示例
        producer_example()
        
        # 运行消费者示例
        consumer_example()
        
        # 运行连接池示例
        connection_pool_example()
        
    except KeyboardInterrupt:
        print("\n示例已被用户中断")
    except Exception as e:
        print(f"示例运行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
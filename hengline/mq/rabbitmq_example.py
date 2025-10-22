"""
RabbitMQ使用示例

本文件展示了如何使用hengline.mq模块中的RabbitMQ组件来发送和接收消息。

使用前请确保：
1. 已安装pika依赖
2. 已配置好RabbitMQ服务
3. 如果需要自定义配置，可以在config.json的settings.rabbitmq部分修改配置
   或者通过环境变量设置（优先级更高）
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor

# 导入实际组件
from hengline.mq import (
    RabbitMQConfig,
    RabbitMQProducer,
    RabbitMQConsumer,
    get_default_producer,
    get_default_consumer,
    rabbitmq_config,
    RabbitMQConnectionPool,
    get_producer_pool,
    get_consumer_pool,
    shutdown_all_pools
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            topic="test_queue",
            message_body="Hello RabbitMQ - Synchronous Message",
            tags="sync_tag",
            keys="sync_message_key"
        )
        print(f"同步消息发送{'成功' if success else '失败'}")
        
        # 示例2：发送异步消息
        print("\n2. 发送异步消息：")
        
        def async_callback(success):
            if success:
                print(f"异步消息发送成功")
            else:
                print(f"异步消息发送失败")
        
        producer.send_async_message(
            topic="test_queue",
            message_body="Hello RabbitMQ - Asynchronous Message",
            callback=async_callback,
            tags="async_tag",
            keys="async_message_key"
        )
        
        # 等待异步消息回调完成
        time.sleep(1)
        
        # 示例3：发送单向消息（不关心发送结果）
        print("\n3. 发送单向消息：")
        producer.send_oneway_message(
            topic="test_queue",
            message_body="Hello RabbitMQ - Oneway Message",
            tags="oneway_tag",
            keys="oneway_message_key"
        )
        print("单向消息已发送（不等待确认）")
        
        # 示例4：使用自定义配置创建生产者
        print("\n4. 使用自定义配置创建生产者：")
        custom_producer = RabbitMQProducer({
            'host': rabbitmq_config.host,
            'port': rabbitmq_config.port,
            'username': rabbitmq_config.username,
            'password': rabbitmq_config.password,
            'virtual_host': rabbitmq_config.virtual_host
        })
        
        success = custom_producer.send_sync_message(
            topic="test_queue",
            message_body="Hello RabbitMQ - Custom Producer Message",
            tags="custom_tag",
            keys="custom_message_key"
        )
        print(f"自定义生产者消息发送{'成功' if success else '失败'}")
        
        # 关闭自定义生产者
        custom_producer.shutdown()
        
    finally:
        # 关闭默认生产者
        producer.shutdown()


# 示例：使用默认消费者接收消息
def consumer_example():
    """消费者示例"""
    print("\n===== 消费者示例 =====")
    
    # 获取默认消费者实例
    consumer = get_default_consumer()
    
    try:
        # 示例1：使用默认消息处理逻辑
        print("\n1. 使用默认消息处理逻辑：")
        consumer.subscribe("test_queue")
        
        # 等待一段时间让消费者有机会接收消息
        time.sleep(5)
        
        # 示例2：使用自定义消息处理逻辑
        print("\n2. 使用自定义消息处理逻辑：")
        
        def custom_message_handler(msg):
            try:
                # 获取消息内容
                msg_body = msg['body'].decode('utf-8')
                print(f"\n接收到消息：")
                print(f"  队列: {msg['topic']}")
                print(f"  标签: {msg['tags']}")
                print(f"  键值: {msg['keys']}")
                print(f"  内容: {msg_body}")
                print(f"  消息ID: {msg['id']}")
                
                # 返回True表示消息处理成功，返回False表示需要重试
                return True
            except Exception as e:
                print(f"处理消息时发生错误: {str(e)}")
                return False
        
        # 订阅另一个队列，使用自定义处理逻辑
        consumer.subscribe("custom_queue", message_listener=custom_message_handler)
        
        # 向自定义队列发送一条测试消息
        producer = get_default_producer()
        producer.send_sync_message(
            topic="custom_queue",
            message_body="Hello RabbitMQ - Custom Handler Message",
            tags="custom_handler_tag",
            keys="custom_handler_key"
        )
        producer.shutdown()
        
        # 等待一段时间让消费者有机会接收消息
        time.sleep(5)
        
        # 示例3：使用自定义配置创建消费者
        print("\n3. 使用自定义配置创建消费者：")
        custom_consumer = RabbitMQConsumer({
            'host': rabbitmq_config.host,
            'port': rabbitmq_config.port,
            'username': rabbitmq_config.username,
            'password': rabbitmq_config.password,
            'virtual_host': rabbitmq_config.virtual_host
        })
        
        custom_consumer.subscribe("custom_config_queue")
        
        # 向自定义配置队列发送一条测试消息
        producer = get_default_producer()
        producer.send_sync_message(
            topic="custom_config_queue",
            message_body="Hello RabbitMQ - Custom Config Message",
            tags="custom_config_tag",
            keys="custom_config_key"
        )
        producer.shutdown()
        
        # 等待一段时间让消费者有机会接收消息
        time.sleep(5)
        
        # 关闭自定义消费者
        custom_consumer.shutdown()
        
        # 打印当前使用的RabbitMQ配置
        print("\n当前使用的RabbitMQ配置：")
        print(f"  主机地址: {rabbitmq_config.host}")
        print(f"  端口: {rabbitmq_config.port}")
        print(f"  用户名: {rabbitmq_config.username}")
        print(f"  虚拟主机: {rabbitmq_config.virtual_host}")
        print(f"  交换器名称: {rabbitmq_config.exchange_name}")
        print(f"  默认队列名称: {rabbitmq_config.queue_name}")
        print(f"  默认路由键: {rabbitmq_config.routing_key}")
        
    finally:
        # 关闭默认消费者
        consumer.shutdown()


# 示例：使用连接池管理RabbitMQ连接
def connection_pool_example():
    """连接池示例"""
    print("\n===== 连接池示例 =====")
    
    # 获取生产者连接池
    producer_pool = get_producer_pool(max_connections=3)
    
    try:
        # 示例1：使用上下文管理器获取和归还连接
        print("\n1. 使用上下文管理器获取和归还连接：")
        with producer_pool.get_connection() as producer:
            success = producer.send_sync_message(
                topic="pool_queue",
                message_body="Hello RabbitMQ - Connection Pool Message (Context Manager)",
                tags="pool_tag",
                keys="pool_key"
            )
            print(f"连接池消息发送{'成功' if success else '失败'}")
        
        # 示例2：手动获取和归还连接
        print("\n2. 手动获取和归还连接：")
        wrapped_conn = producer_pool.get_connection()
        try:
            producer = wrapped_conn.connection
            success = producer.send_sync_message(
                topic="pool_queue",
                message_body="Hello RabbitMQ - Connection Pool Message (Manual)",
                tags="manual_tag",
                keys="manual_key"
            )
            print(f"手动获取连接消息发送{'成功' if success else '失败'}")
        finally:
            # 手动归还连接
            producer_pool.return_connection(wrapped_conn)
        
        # 示例3：多线程使用连接池
        print("\n3. 多线程使用连接池：")
        
        def send_message_thread(thread_id):
            try:
                with producer_pool.get_connection() as producer:
                    success = producer.send_sync_message(
                        topic="pool_queue",
                        message_body=f"Hello RabbitMQ - Thread {thread_id}",
                        tags=f"thread_{thread_id}_tag",
                        keys=f"thread_{thread_id}_key"
                    )
                    print(f"线程 {thread_id} 消息发送{'成功' if success else '失败'}")
            except Exception as e:
                print(f"线程 {thread_id} 出错: {str(e)}")
        
        # 创建多个线程同时使用连接池
        with ThreadPoolExecutor(max_workers=10) as executor:
            for i in range(10):
                executor.submit(send_message_thread, i)
        
        # 等待所有线程完成
        time.sleep(2)
        
        # 示例4：消费者连接池
        print("\n4. 消费者连接池：")
        
        # 获取消费者连接池
        consumer_pool = get_consumer_pool(max_connections=2)
        
        try:
            # 从连接池获取消费者并订阅队列
            with consumer_pool.get_connection() as consumer:
                
                def pool_message_handler(msg):
                    try:
                        msg_body = msg['body'].decode('utf-8')
                        print(f"\n连接池消费者接收到消息：")
                        print(f"  队列: {msg['topic']}")
                        print(f"  标签: {msg['tags']}")
                        print(f"  内容: {msg_body}")
                        return True
                    except Exception as e:
                        print(f"处理消息时发生错误: {str(e)}")
                        return False
                
                # 订阅队列
                consumer.subscribe("pool_consumer_queue", message_listener=pool_message_handler)
                
                # 发送一条测试消息
                with producer_pool.get_connection() as producer:
                    producer.send_sync_message(
                        topic="pool_consumer_queue",
                        message_body="Hello RabbitMQ - For Pool Consumer",
                        tags="pool_consumer_tag",
                        keys="pool_consumer_key"
                    )
                
                # 等待一段时间让消费者有机会接收消息
                time.sleep(5)
            
        finally:
            # 关闭消费者连接池
            consumer_pool.close()
        
        # 打印当前使用的RabbitMQ配置
        print("\n当前使用的RabbitMQ配置：")
        print(f"  主机地址: {rabbitmq_config.host}")
        print(f"  端口: {rabbitmq_config.port}")
        print(f"  用户名: {rabbitmq_config.username}")
        print(f"  虚拟主机: {rabbitmq_config.virtual_host}")
        print(f"  交换器名称: {rabbitmq_config.exchange_name}")
        print(f"  默认队列名称: {rabbitmq_config.queue_name}")
        print(f"  默认路由键: {rabbitmq_config.routing_key}")
        
    finally:
        # 关闭生产者连接池
        producer_pool.close()
        
        # 也可以使用全局的shutdown_all_pools函数关闭所有连接池
        # shutdown_all_pools()


# 运行示例
if __name__ == "__main__":
    try:
        # 运行生产者示例
        producer_example()
        
        # 运行消费者示例
        consumer_example()
        
        # 运行连接池示例
        connection_pool_example()
        
    finally:
        # 确保所有连接池都被关闭
        shutdown_all_pools()
        
        print("\n所有示例运行完成，已清理资源")
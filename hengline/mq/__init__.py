"""
hengline.mq模块

本模块提供了RabbitMQ的集成功能，包括配置管理、消息发送和消息消费等。

主要组件：
- RabbitMQConfig: 配置管理类
- RabbitMQProducer: 消息生产者类
- RabbitMQConsumer: 消息消费者类

使用示例：

# 发送消息
from hengline.mq import get_default_producer

producer = get_default_producer()
try:
    # 同步发送消息
    success = producer.send_sync_message(
        topic="test_queue",
        message_body="Hello RabbitMQ",
        tags="test_tag",
        keys="test_key"
    )
    
    # 异步发送消息
    def callback(success):
        if success:
            print("Async message sent successfully")
        else:
            print("Async message sent failed")
    
    producer.send_async_message(
        topic="test_queue",
        message_body="Hello Async RabbitMQ",
        callback=callback,
        tags="async_tag"
    )
finally:
    producer.shutdown()


# 接收消息
from hengline.mq import get_default_consumer

consumer = get_default_consumer()

def message_handler(msg):
    try:
        msg_body = msg['body'].decode('utf-8')
        print(f"Received message: {msg_body}")
        # 处理消息...
        return True  # 返回True表示处理成功
    except Exception as e:
        print(f"Error processing message: {e}")
        return False  # 返回False表示需要重试

# 订阅队列
consumer.subscribe("test_queue", message_listener=message_handler)

# 保持运行（实际应用中需要更复杂的生命周期管理）
try:
    while True:
        import time
        time.sleep(1)
except KeyboardInterrupt:
    consumer.shutdown()
"""

# 导出主要组件
__all__ = [
    'RabbitMQConfig',
    'RabbitMQProducer',
    'RabbitMQConsumer',
    'get_default_producer',
    'get_default_consumer',
    'rabbitmq_config',
    'RabbitMQConnectionPool',
    'get_producer_pool',
    'get_consumer_pool',
    'shutdown_all_pools'
]

# 导入实际组件
from hengline.mq.rabbitmq_config import RabbitMQConfig, rabbitmq_config
from hengline.mq.rabbitmq_producer import RabbitMQProducer, get_default_producer
from hengline.mq.rabbitmq_consumer import RabbitMQConsumer, get_default_consumer
from hengline.mq.rabbitmq_pool import (
    RabbitMQConnectionPool,
    get_producer_pool,
    get_consumer_pool,
    shutdown_all_pools
)
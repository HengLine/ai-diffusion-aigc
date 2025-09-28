"""
hengline.mq模块

本模块提供了RocketMQ的集成功能，包括配置管理、消息发送和消息消费等。

主要组件：
- RocketMQConfig: 配置管理类
- RocketMQProducer: 消息生产者类
- RocketMQConsumer: 消息消费者类

使用示例：

# 发送消息
from hengline.mq import get_default_producer

producer = get_default_producer()
try:
    # 同步发送消息
    success = producer.send_sync_message(
        topic="test_topic",
        message_body="Hello RocketMQ",
        tags="test_tag",
        keys="test_key"
    )
    
    # 异步发送消息
    def callback(send_result):
        if send_result.status == SendStatus.SEND_OK:
            print(f"Async message sent, msg_id: {send_result.msg_id}")
    
    producer.send_async_message(
        topic="test_topic",
        message_body="Hello Async RocketMQ",
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
        msg_body = msg.body.decode('utf-8')
        print(f"Received message: {msg_body}")
        # 处理消息...
        return True  # 返回True表示处理成功
    except Exception as e:
        print(f"Error processing message: {e}")
        return False  # 返回False表示需要重试

# 订阅主题
consumer.subscribe("test_topic", "*", message_handler)

# 保持运行（实际应用中需要更复杂的生命周期管理）
try:
    while True:
        import time
        time.sleep(1)
except KeyboardInterrupt:
    consumer.shutdown()
"""
import platform
import logging

# 检查是否为Windows系统
IS_WINDOWS = platform.system() == 'Windows'

# 导出主要组件
__all__ = [
    'RocketMQConfig',
    'RocketMQProducer',
    'RocketMQConsumer',
    'get_default_producer',
    'get_default_consumer',
    'rocketmq_config',
    'RocketMQConnectionPool',
    'get_producer_pool',
    'get_consumer_pool',
    'shutdown_all_pools'
]

# Windows系统下的兼容性处理
if IS_WINDOWS:
    logging.warning("RocketMQ不支持Windows系统，将使用模拟实现")
    
    # 提供SendStatus的模拟实现
    class SendStatus:
        SEND_OK = 0
        FLUSH_DISK_TIMEOUT = 1
        FLUSH_SLAVE_TIMEOUT = 2
        SLAVE_NOT_AVAILABLE = 3
    
    # 提供RocketMQConfig的模拟实现
    class RocketMQConfig:
        def __init__(self):
            self.name_server_address = '127.0.0.1:9876'
            self.producer_group = 'default_producer_group'
            self.consumer_group = 'default_consumer_group'
            self.instance_name = 'default_instance'
            self.retry_times = 3
        
        def get_producer_config(self):
            return {
                'group_name': self.producer_group,
                'name_server_address': self.name_server_address,
                'instance_name': self.instance_name,
                'retry_times': self.retry_times
            }
        
        def get_consumer_config(self):
            return {
                'group_name': self.consumer_group,
                'name_server_address': self.name_server_address,
                'instance_name': self.instance_name,
                'retry_times': self.retry_times
            }
    
    # 提供rocketmq_config的模拟实例
    rocketmq_config = RocketMQConfig()
    
    # 提供RocketMQProducer的模拟实现
    class RocketMQProducer:
        def __init__(self, producer_config=None):
            self.config = producer_config or rocketmq_config.get_producer_config()
            logging.warning("Windows系统下创建模拟RocketMQ生产者")
        
        def send_sync_message(self, topic, message_body, tags=None, keys=None):
            logging.warning(f"Windows系统下模拟发送同步消息到主题{topic}")
            return True
        
        def send_async_message(self, topic, message_body, callback=None, tags=None, keys=None):
            logging.warning(f"Windows系统下模拟发送异步消息到主题{topic}")
            if callback:
                # 模拟回调结果
                callback(type('obj', (object,), {'status': SendStatus.SEND_OK, 'msg_id': 'mock_msg_id'})())
        
        def send_oneway_message(self, topic, message_body, tags=None, keys=None):
            logging.warning(f"Windows系统下模拟发送单向消息到主题{topic}")
        
        def shutdown(self):
            logging.warning("Windows系统下模拟关闭RocketMQ生产者")
    
    # 提供RocketMQConsumer的模拟实现
    class RocketMQConsumer:
        def __init__(self, consumer_config=None):
            self.config = consumer_config or rocketmq_config.get_consumer_config()
            self.subscribed_topics = {}
            logging.warning("Windows系统下创建模拟RocketMQ消费者")
        
        def subscribe(self, topic, expression, callback=None):
            logging.warning(f"Windows系统下模拟订阅主题{topic}")
            self.subscribed_topics[topic] = (expression, callback)
        
        def unsubscribe(self, topic):
            logging.warning(f"Windows系统下模拟取消订阅主题{topic}")
            if topic in self.subscribed_topics:
                del self.subscribed_topics[topic]
        
        def shutdown(self):
            logging.warning("Windows系统下模拟关闭RocketMQ消费者")
    
    # 提供连接池相关模拟实现
    class ConnectionWrapper:
        def __init__(self, connection):
            self.connection = connection
        
        def __enter__(self):
            return self.connection
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.connection.shutdown()
    
    class RocketMQConnectionPool:
        def __init__(self, create_func, max_size=10):
            self.create_func = create_func
            self.max_size = max_size
            logging.warning("Windows系统下创建模拟RocketMQ连接池")
        
        def get_connection(self):
            # 创建连接并包装以支持上下文管理器
            conn = self.create_func()
            return ConnectionWrapper(conn)
        
        def return_connection(self, conn):
            # 模拟归还连接，关闭底层连接
            if hasattr(conn, 'connection'):
                conn.connection.shutdown()
            else:
                conn.shutdown()
        
        def shutdown(self):
            logging.warning("Windows系统下模拟关闭RocketMQ连接池")
    
    # 提供辅助函数的模拟实现
    def get_default_producer():
        return RocketMQProducer()
    
    def get_default_consumer():
        return RocketMQConsumer()
    
    def get_producer_pool(max_connections=5):
        return RocketMQConnectionPool(lambda: RocketMQProducer(), max_connections)
    
    def get_consumer_pool(max_connections=5):
        return RocketMQConnectionPool(lambda: RocketMQConsumer(), max_connections)
    
    def shutdown_all_pools():
        logging.warning("Windows系统下模拟关闭所有RocketMQ连接池")
else:
    # 非Windows系统导入实际组件
    from hengline.mq.rocketmq_config import RocketMQConfig, rocketmq_config
    from hengline.mq.rocketmq_producer import RocketMQProducer, get_default_producer
    from hengline.mq.rocketmq_consumer import RocketMQConsumer, get_default_consumer
    from hengline.mq.rocketmq_pool import (
        RocketMQConnectionPool,
        get_producer_pool,
        get_consumer_pool,
        shutdown_all_pools
    )
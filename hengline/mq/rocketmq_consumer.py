from rocketmq.client import Consumer, MessageExt
from typing import Dict, Optional, Callable
import logging
import platform
import traceback

# 检查是否为Windows系统
IS_WINDOWS = platform.system() == 'Windows'

# Windows系统下提供Mock实现
if IS_WINDOWS:
    logging.warning("RocketMQ不支持Windows系统，将使用模拟实现")
    
    # Mock Consumer类
    class Consumer:
        def __init__(self, group_name):
            self.group_name = group_name
            self.namesrv_addr = ''
            self.instance_name = ''
            self._subscriptions = {}
        
        def set_namesrv_addr(self, addr):
            self.namesrv_addr = addr
        
        def set_instance_name(self, name):
            self.instance_name = name
        
        def start(self):
            logging.warning("Windows系统下模拟启动RocketMQ消费者")
        
        def shutdown(self):
            logging.warning("Windows系统下模拟关闭RocketMQ消费者")
        
        def subscribe(self, topic, tags, callback):
            logging.warning(f"Windows系统下模拟订阅主题{topic}")
            self._subscriptions[topic] = (tags, callback)
            
            # 模拟消息（如果有回调函数）
            if callback:
                # 创建模拟消息对象
                mock_msg = type('obj', (object,), {
                    'topic': topic,
                    'tags': tags,
                    'keys': 'mock_key',
                    'body': b'mock_message_body',
                    'id': 'mock_msg_id',
                    'store_time': platform.ticks_ms() if hasattr(platform, 'ticks_ms') else 0
                })()
                
                # 延迟调用回调函数以模拟异步消息接收
                import threading
                def delayed_callback():
                    try:
                        callback(mock_msg)
                    except Exception as e:
                        logging.error(f"处理模拟消息时出错: {str(e)}")
                
                threading.Timer(0.1, delayed_callback).start()
        
        def unsubscribe(self, topic):
            logging.warning(f"Windows系统下模拟取消订阅主题{topic}")
            if topic in self._subscriptions:
                del self._subscriptions[topic]
    
    from hengline.mq.rocketmq_config import rocketmq_config
else:
    # 非Windows系统导入实际的RocketMQ组件
    from rocketmq.client import Consumer
    from hengline.mq.rocketmq_config import rocketmq_config


class RocketMQConsumer:
    """
    RocketMQ消费者类，用于初始化消费者并接收消息
    """
    
    def __init__(self, consumer_config: Optional[Dict[str, any]] = None):
        """
        初始化消费者
        
        Args:
            consumer_config: 消费者配置，若为None则使用默认配置
        """
        self.logger = logging.getLogger(__name__)
        # 使用提供的配置或默认配置
        self.config = consumer_config or rocketmq_config.get_consumer_config()
        
        # 初始化消费者
        self.consumer = Consumer(self.config['group_name'])
        self.consumer.set_namesrv_addr(self.config['name_server_address'])
        self.consumer.set_instance_name(self.config['instance_name'])
        
        # 启动消费者
        try:
            self.consumer.start()
            self.logger.info(f"RocketMQ consumer started successfully, group: {self.config['group_name']}")
        except Exception as e:
            self.logger.error(f"Failed to start RocketMQ consumer: {str(e)}")
            raise
    
    def subscribe(self, topic: str, tags: str = '*', 
                 message_listener: Optional[Callable] = None) -> None:
        """
        订阅主题并设置消息监听器
        
        Args:
            topic: 要订阅的主题
            tags: 消息标签过滤，默认为'*'表示所有标签
            message_listener: 消息处理回调函数，若为None则使用默认处理逻辑
        """
        try:
            # 定义默认消息监听器
            def default_message_listener(msg):
                try:
                    # 消息体内容
                    msg_body = msg.body.decode('utf-8')
                    self.logger.info(f"Received message from topic: {topic}, tags: {msg.tags}, body: {msg_body}")
                    # 返回True表示消息处理成功，返回False表示需要重试
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to process message: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    return False
            
            # 订阅主题并注册监听器
            self.consumer.subscribe(topic, tags, message_listener or default_message_listener)
            self.logger.info(f"Subscribed to topic: {topic}, tags: {tags}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to topic {topic}: {str(e)}")
            raise
    
    def unsubscribe(self, topic: str) -> None:
        """
        取消订阅主题
        
        Args:
            topic: 要取消订阅的主题
        """
        try:
            self.consumer.unsubscribe(topic)
            self.logger.info(f"Unsubscribed from topic: {topic}")
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from topic {topic}: {str(e)}")
    
    def shutdown(self) -> None:
        """
        关闭消费者
        """
        try:
            self.consumer.shutdown()
            self.logger.info(f"RocketMQ consumer shutdown successfully")
        except Exception as e:
            self.logger.error(f"Failed to shutdown RocketMQ consumer: {str(e)}")


# 创建默认消费者实例
def get_default_consumer() -> RocketMQConsumer:
    """
    获取默认的RocketMQ消费者实例（从连接池获取）
    
    Returns:
        RocketMQConsumer: 消费者实例
    """
    from hengline.mq.rocketmq_pool import get_consumer_pool
    
    # 获取消费者连接池
    consumer_pool = get_consumer_pool()
    
    # 从连接池获取一个连接
    try:
        connection = consumer_pool.get_connection()
        # 返回连接中的消费者实例
        consumer = connection.connection
        
        # 重写shutdown方法，使其归还连接而不是直接关闭
        original_shutdown = consumer.shutdown
        
        def pool_shutdown():
            consumer_pool.return_connection(connection)
            # 注意：这里不调用original_shutdown，因为连接池会管理连接的生命周期
        
        consumer.shutdown = pool_shutdown
        
        return consumer
    except Exception as e:
        # 如果从连接池获取失败，回退到直接创建
        logging.error(f"Failed to get consumer from pool: {str(e)}")
        return RocketMQConsumer()
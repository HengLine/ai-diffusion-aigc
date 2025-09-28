from rocketmq.client import Producer, Message, SendStatus
from typing import Dict, Optional, Union
import logging
import platform

# 检查是否为Windows系统
IS_WINDOWS = platform.system() == 'Windows'

# Windows系统下提供Mock实现
if IS_WINDOWS:
    logging.warning("RocketMQ不支持Windows系统，将使用模拟实现")
    
    # Mock SendStatus枚举
    class SendStatus:
        SEND_OK = 0
        FLUSH_DISK_TIMEOUT = 1
        FLUSH_SLAVE_TIMEOUT = 2
        SLAVE_NOT_AVAILABLE = 3
    
    # Mock Message类
    class Message:
        def __init__(self, topic):
            self.topic = topic
            self.body = b''
            self.tags = ''
            self.keys = ''
        
        def set_body(self, body):
            self.body = body.encode('utf-8') if isinstance(body, str) else body
        
        def set_tags(self, tags):
            self.tags = tags
        
        def set_keys(self, keys):
            self.keys = keys
    
    # Mock Producer类
    class Producer:
        def __init__(self, group_name):
            self.group_name = group_name
            self.namesrv_addr = ''
            self.instance_name = ''
            self.retry_times = 3
        
        def set_namesrv_addr(self, addr):
            self.namesrv_addr = addr
        
        def set_instance_name(self, name):
            self.instance_name = name
        
        def set_retry_times(self, times):
            self.retry_times = times
        
        def start(self):
            logging.warning("Windows系统下模拟启动RocketMQ生产者")
        
        def shutdown(self):
            logging.warning("Windows系统下模拟关闭RocketMQ生产者")
        
        def send_sync(self, msg):
            logging.warning(f"Windows系统下模拟发送同步消息到主题{msg.topic}")
            # 返回模拟的发送结果
            return type('obj', (object,), {'status': SendStatus.SEND_OK, 'msg_id': 'mock_msg_id'})()
        
        def send_async(self, msg, callback):
            logging.warning(f"Windows系统下模拟发送异步消息到主题{msg.topic}")
            # 立即调用回调函数
            if callback:
                callback(type('obj', (object,), {'status': SendStatus.SEND_OK, 'msg_id': 'mock_msg_id'})())
        
        def send_oneway(self, msg):
            logging.warning(f"Windows系统下模拟发送单向消息到主题{msg.topic}")
    
    from hengline.mq.rocketmq_config import rocketmq_config
else:
    # 非Windows系统导入实际的RocketMQ组件
    from rocketmq.client import Producer, Message, SendStatus
    from hengline.mq.rocketmq_config import rocketmq_config


class RocketMQProducer:
    """
    RocketMQ生产者类，用于初始化生产者并发送消息
    """
    
    def __init__(self, producer_config: Optional[Dict[str, any]] = None):
        """
        初始化生产者
        
        Args:
            producer_config: 生产者配置，若为None则使用默认配置
        """
        self.logger = logging.getLogger(__name__)
        # 使用提供的配置或默认配置
        self.config = producer_config or rocketmq_config.get_producer_config()
        
        # 初始化生产者
        self.producer = Producer(self.config['group_name'])
        self.producer.set_namesrv_addr(self.config['name_server_address'])
        self.producer.set_instance_name(self.config['instance_name'])
        self.producer.set_retry_times(self.config['retry_times'])
        
        # 启动生产者
        try:
            self.producer.start()
            self.logger.info(f"RocketMQ producer started successfully, group: {self.config['group_name']}")
        except Exception as e:
            self.logger.error(f"Failed to start RocketMQ producer: {str(e)}")
            raise
    
    def send_sync_message(self, topic: str, message_body: str, 
                         tags: Optional[str] = None, keys: Optional[str] = None) -> bool:
        """
        同步发送消息
        
        Args:
            topic: 消息主题
            message_body: 消息内容
            tags: 消息标签
            keys: 消息键
            
        Returns:
            bool: 发送是否成功
        """
        try:
            msg = Message(topic)
            msg.set_body(message_body)
            
            if tags:
                msg.set_tags(tags)
            
            if keys:
                msg.set_keys(keys)
            
            result = self.producer.send_sync(msg)
            
            if result.status == SendStatus.SEND_OK:
                self.logger.info(f"Message sent successfully, msg_id: {result.msg_id}")
                return True
            else:
                self.logger.error(f"Failed to send message, status: {result.status}")
                return False
        except Exception as e:
            self.logger.error(f"Exception occurred while sending sync message: {str(e)}")
            return False
    
    def send_async_message(self, topic: str, message_body: str, 
                          callback: Optional[callable] = None, 
                          tags: Optional[str] = None, keys: Optional[str] = None) -> None:
        """
        异步发送消息
        
        Args:
            topic: 消息主题
            message_body: 消息内容
            callback: 发送回调函数
            tags: 消息标签
            keys: 消息键
        """
        try:
            msg = Message(topic)
            msg.set_body(message_body)
            
            if tags:
                msg.set_tags(tags)
            
            if keys:
                msg.set_keys(keys)
            
            # 定义默认回调
            def default_callback(send_result):
                if send_result.status == SendStatus.SEND_OK:
                    self.logger.info(f"Async message sent successfully, msg_id: {send_result.msg_id}")
                else:
                    self.logger.error(f"Failed to send async message, status: {send_result.status}")
            
            # 使用提供的回调或默认回调
            self.producer.send_async(msg, callback or default_callback)
        except Exception as e:
            self.logger.error(f"Exception occurred while sending async message: {str(e)}")
    
    def send_oneway_message(self, topic: str, message_body: str, 
                          tags: Optional[str] = None, keys: Optional[str] = None) -> None:
        """
        单向发送消息（不关心发送结果）
        
        Args:
            topic: 消息主题
            message_body: 消息内容
            tags: 消息标签
            keys: 消息键
        """
        try:
            msg = Message(topic)
            msg.set_body(message_body)
            
            if tags:
                msg.set_tags(tags)
            
            if keys:
                msg.set_keys(keys)
            
            self.producer.send_oneway(msg)
            self.logger.info(f"Oneway message sent, topic: {topic}")
        except Exception as e:
            self.logger.error(f"Exception occurred while sending oneway message: {str(e)}")
    
    def shutdown(self) -> None:
        """
        关闭生产者
        """
        try:
            self.producer.shutdown()
            self.logger.info(f"RocketMQ producer shutdown successfully")
        except Exception as e:
            self.logger.error(f"Failed to shutdown RocketMQ producer: {str(e)}")


# 创建默认生产者实例
def get_default_producer() -> RocketMQProducer:
    """
    获取默认的RocketMQ生产者实例（从连接池获取）
    
    Returns:
        RocketMQProducer: 生产者实例
    """
    from hengline.mq.rocketmq_pool import get_producer_pool, RocketMQConnectionPool
    
    # 获取生产者连接池
    producer_pool = get_producer_pool()
    
    # 从连接池获取一个连接
    try:
        connection = producer_pool.get_connection()
        # 返回连接中的生产者实例
        producer = connection.connection
        
        # 重写shutdown方法，使其归还连接而不是直接关闭
        original_shutdown = producer.shutdown
        
        def pool_shutdown():
            producer_pool.return_connection(connection)
            # 注意：这里不调用original_shutdown，因为连接池会管理连接的生命周期
        
        producer.shutdown = pool_shutdown
        
        return producer
    except Exception as e:
        # 如果从连接池获取失败，回退到直接创建
        logging.error(f"Failed to get producer from pool: {str(e)}")
        return RocketMQProducer()
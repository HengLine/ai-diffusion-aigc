import logging
from typing import Optional, Dict, Any, Callable
import json

import pika

from hengline.mq.rabbitmq_config import rabbitmq_config


class RabbitMQProducer:
    """
    RabbitMQ生产者类，用于初始化生产者并发送消息
    """
    
    def __init__(self, producer_config: Optional[Dict[str, any]] = None):
        """
        初始化生产者
        
        Args:
            producer_config: 生产者配置，若为None则使用默认配置
        """
        self.logger = logging.getLogger(__name__)
        # 使用提供的配置或默认配置
        self.config = producer_config or rabbitmq_config.get_connection_params()
        
        # 存储连接和通道
        self.connection = None
        self.channel = None
        
        # 初始化连接
        self._init_connection()
    
    def _init_connection(self):
        """
        初始化RabbitMQ连接
        """
        try:
            # 建立连接
            self.connection = pika.BlockingConnection(rabbitmq_config.get_pika_connection_params())
            # 创建通道
            self.channel = self.connection.channel()
            
            # 声明交换机（如果不存在）
            self.channel.exchange_declare(
                exchange=rabbitmq_config.exchange_name,
                exchange_type='direct',
                durable=True
            )
            
            # 声明队列（如果不存在）
            self.channel.queue_declare(
                queue=rabbitmq_config.queue_name,
                durable=True
            )
            
            # 绑定队列到交换机
            self.channel.queue_bind(
                exchange=rabbitmq_config.exchange_name,
                queue=rabbitmq_config.queue_name,
                routing_key=rabbitmq_config.routing_key
            )
            
            self.logger.info(f"RabbitMQ producer started successfully, host: {self.config['host']}")
        except Exception as e:
            self.logger.error(f"Failed to start RabbitMQ producer: {str(e)}")
            self._close_connection()
            raise
    
    def _close_connection(self):
        """
        关闭连接
        """
        if self.channel and self.channel.is_open:
            try:
                self.channel.close()
            except Exception:
                pass
        
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception:
                pass
    
    def send_sync_message(self, topic: str, message_body: str, 
                         tags: Optional[str] = None, keys: Optional[str] = None) -> bool:
        """
        同步发送消息
        
        Args:
            topic: 消息主题/队列名称
            message_body: 消息内容
            tags: 消息标签
            keys: 消息键
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 如果连接已关闭，重新初始化
            if not self.connection or self.connection.is_closed:
                self._init_connection()
            
            # 构建消息属性
            properties = pika.BasicProperties(
                delivery_mode=2,  # 持久化消息
                content_type='application/json'
            )
            
            # 如果有标签或键，添加到属性中
            if tags:
                properties.headers = properties.headers or {}
                properties.headers['tags'] = tags
            
            if keys:
                properties.message_id = keys
            
            # 将消息内容转换为JSON（如果不是JSON的话）
            if isinstance(message_body, dict):
                message_body = json.dumps(message_body)
            
            # 发送消息
            self.channel.basic_publish(
                exchange=rabbitmq_config.exchange_name,
                routing_key=topic if topic else rabbitmq_config.routing_key,
                body=message_body,
                properties=properties
            )
            
            self.logger.info(f"Message sent successfully to {topic}")
            return True
        except Exception as e:
            self.logger.error(f"Exception occurred while sending sync message: {str(e)}")
            return False
    
    def send_async_message(self, topic: str, message_body: str, 
                          callback: Optional[callable] = None, 
                          tags: Optional[str] = None, keys: Optional[str] = None) -> None:
        """
        异步发送消息（RabbitMQ在BlockingConnection模式下是同步的，这里模拟异步行为）
        
        Args:
            topic: 消息主题/队列名称
            message_body: 消息内容
            callback: 发送回调函数
            tags: 消息标签
            keys: 消息键
        """
        try:
            success = self.send_sync_message(topic, message_body, tags, keys)
            
            # 如果提供了回调函数，调用它
            if callback:
                callback(success)
        except Exception as e:
            self.logger.error(f"Exception occurred while sending async message: {str(e)}")
    
    def send_oneway_message(self, topic: str, message_body: str, 
                          tags: Optional[str] = None, keys: Optional[str] = None) -> None:
        """
        单向发送消息（不关心发送结果）
        
        Args:
            topic: 消息主题/队列名称
            message_body: 消息内容
            tags: 消息标签
            keys: 消息键
        """
        try:
            self.send_sync_message(topic, message_body, tags, keys)
            self.logger.info(f"Oneway message sent, topic: {topic}")
        except Exception as e:
            self.logger.error(f"Exception occurred while sending oneway message: {str(e)}")
    
    def shutdown(self):
        """
        关闭生产者连接
        """
        try:
            self._close_connection()
            self.logger.info(f"RabbitMQ producer shutdown successfully")
        except Exception as e:
            self.logger.error(f"Failed to shutdown RabbitMQ producer: {str(e)}")


def get_default_producer() -> RabbitMQProducer:
    """
    获取默认的RabbitMQ生产者实例
    
    Returns:
        RabbitMQProducer: 生产者实例
    """
    # 在实际应用中，可以从连接池获取生产者
    # 这里为了简化，直接返回新的实例
    return RabbitMQProducer()
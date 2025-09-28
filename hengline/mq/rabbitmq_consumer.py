import logging
import traceback
import threading
from typing import Optional, Dict, Any, Callable
import json

import pika

from hengline.mq.rabbitmq_config import rabbitmq_config


class RabbitMQConsumer:
    """
    RabbitMQ消费者类，用于初始化消费者并接收消息
    """
    
    def __init__(self, consumer_config: Optional[Dict[str, any]] = None):
        """
        初始化消费者
        
        Args:
            consumer_config: 消费者配置，若为None则使用默认配置
        """
        self.logger = logging.getLogger(__name__)
        # 使用提供的配置或默认配置
        self.config = consumer_config or rabbitmq_config.get_connection_params()
        
        # 存储连接和通道
        self.connection = None
        self.channel = None
        
        # 消息监听器字典
        self.message_listeners = {}
        
        # 消费线程
        self.consuming_thread = None
        self.stop_event = threading.Event()
        
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
            
            # 设置QoS，确保公平分发
            self.channel.basic_qos(prefetch_count=1)
            
            self.logger.info(f"RabbitMQ consumer started successfully, host: {self.config['host']}")
        except Exception as e:
            self.logger.error(f"Failed to start RabbitMQ consumer: {str(e)}")
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
    
    def subscribe(self, topic: str, tags: str = '*', 
                 message_listener: Optional[Callable] = None) -> None:
        """
        订阅主题并设置消息监听器
        
        Args:
            topic: 要订阅的主题/队列名称
            tags: 消息标签过滤，默认为'*'表示所有标签
            message_listener: 消息处理回调函数，若为None则使用默认处理逻辑
        """
        try:
            # 如果连接已关闭，重新初始化
            if not self.connection or self.connection.is_closed:
                self._init_connection()
            
            # 声明队列（如果不存在）
            self.channel.queue_declare(
                queue=topic,
                durable=True
            )
            
            # 定义默认消息监听器
            def default_message_listener(msg):
                try:
                    # 消息体内容
                    msg_body = msg.body.decode('utf-8')
                    
                    # 尝试解析JSON内容
                    try:
                        msg_body = json.loads(msg_body)
                    except json.JSONDecodeError:
                        pass  # 如果不是JSON，保持原样
                    
                    self.logger.info(f"Received message from queue: {topic}")
                    
                    # 模拟RocketMQ消息对象的属性
                    class Message:
                        def __init__(self):
                            self.topic = topic
                            self.tags = msg.properties.headers.get('tags', '') if msg.properties.headers else ''
                            self.keys = msg.properties.message_id
                            self.body = msg.body
                            self.id = msg.properties.message_id
                            self.store_time = msg.timestamp
                    
                    message_obj = Message()
                    
                    # 确认消息已接收
                    self.channel.basic_ack(delivery_tag=msg.delivery_tag)
                    
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to process message: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    
                    # 拒绝消息，不重新入队
                    self.channel.basic_nack(delivery_tag=msg.delivery_tag, requeue=False)
                    return False
            
            # 保存消息监听器
            listener = message_listener or default_message_listener
            self.message_listeners[topic] = listener
            
            # 定义消息处理回调函数
            def callback(ch, method, properties, body):
                # 调用用户提供的监听器
                success = listener({
                    'topic': topic,
                    'body': body,
                    'tags': properties.headers.get('tags', '') if properties.headers else '',
                    'keys': properties.message_id,
                    'id': properties.message_id,
                    'delivery_tag': method.delivery_tag,
                    'channel': ch
                })
                
                # 根据处理结果确认或拒绝消息
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            # 开始消费消息
            self.channel.basic_consume(
                queue=topic,
                on_message_callback=callback
            )
            
            # 如果还没有启动消费线程，启动一个
            if not self.consuming_thread or not self.consuming_thread.is_alive():
                self.stop_event.clear()
                self.consuming_thread = threading.Thread(target=self._consume_messages)
                self.consuming_thread.daemon = True
                self.consuming_thread.start()
            
            self.logger.info(f"Subscribed to queue: {topic}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to queue {topic}: {str(e)}")
            raise
    
    def _consume_messages(self):
        """
        在单独的线程中消费消息
        """
        try:
            if self.connection and not self.connection.is_closed:
                self.logger.info("Starting to consume messages...")
                # 非阻塞消费，定期检查是否需要停止
                while not self.stop_event.is_set():
                    try:
                        # 使用非阻塞的consume_once方法
                        self.connection.process_data_events(time_limit=1)
                    except pika.exceptions.AMQPError as e:
                        self.logger.error(f"AMQP error during message consumption: {str(e)}")
                        break
        except Exception as e:
            self.logger.error(f"Error in message consumption thread: {str(e)}")
    
    def shutdown(self):
        """
        关闭消费者连接
        """
        try:
            # 停止消费线程
            if self.stop_event:
                self.stop_event.set()
            
            # 等待消费线程结束
            if self.consuming_thread and self.consuming_thread.is_alive():
                self.consuming_thread.join(timeout=2)
            
            # 关闭连接
            self._close_connection()
            
            self.logger.info(f"RabbitMQ consumer shutdown successfully")
        except Exception as e:
            self.logger.error(f"Failed to shutdown RabbitMQ consumer: {str(e)}")


def get_default_consumer() -> RabbitMQConsumer:
    """
    获取默认的RabbitMQ消费者实例
    
    Returns:
        RabbitMQConsumer: 消费者实例
    """
    # 在实际应用中，可以从连接池获取消费者
    # 这里为了简化，直接返回新的实例
    return RabbitMQConsumer()
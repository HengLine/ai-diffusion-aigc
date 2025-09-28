from typing import Dict, Optional
import os

from hengline.utils.config_utils import get_settings_config
from hengline.logger import debug


class RabbitMQConfig:
    """
    RabbitMQ配置类，用于存储和管理RabbitMQ的配置信息
    """
    
    def __init__(self):
        # 获取配置文件中的RabbitMQ配置
        settings_config = get_settings_config()
        rabbitmq_config = settings_config.get('rabbitmq', {})
        
        # 从环境变量获取配置，环境变量优先级最高，其次是配置文件，最后是默认值
        self.host = os.environ.get('RABBITMQ_HOST', 
                            rabbitmq_config.get('host', 'localhost'))
        self.port = int(os.environ.get('RABBITMQ_PORT', 
                        str(rabbitmq_config.get('port', '5672'))))
        self.username = os.environ.get('RABBITMQ_USERNAME', 
                            rabbitmq_config.get('username', 'guest'))
        self.password = os.environ.get('RABBITMQ_PASSWORD', 
                            rabbitmq_config.get('password', 'guest'))
        self.virtual_host = os.environ.get('RABBITMQ_VIRTUAL_HOST', 
                            rabbitmq_config.get('virtual_host', '/'))
        self.exchange_name = os.environ.get('RABBITMQ_EXCHANGE_NAME', 
                            rabbitmq_config.get('exchange_name', 'default_exchange'))
        self.queue_name = os.environ.get('RABBITMQ_QUEUE_NAME', 
                            rabbitmq_config.get('queue_name', 'default_queue'))
        self.routing_key = os.environ.get('RABBITMQ_ROUTING_KEY', 
                            rabbitmq_config.get('routing_key', 'default_routing_key'))
        self.connection_timeout = int(os.environ.get('RABBITMQ_CONNECTION_TIMEOUT', 
                            str(rabbitmq_config.get('connection_timeout', '30'))))
        self.heartbeat = int(os.environ.get('RABBITMQ_HEARTBEAT', 
                            str(rabbitmq_config.get('heartbeat', '60'))))
        
        # 记录使用的配置
        debug(f"RabbitMQ配置加载完成: host={self.host}, port={self.port}, virtual_host={self.virtual_host}")
        
    def get_connection_params(self) -> Dict[str, any]:
        """
        获取连接参数
        """
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'virtual_host': self.virtual_host,
            'connection_timeout': self.connection_timeout,
            'heartbeat': self.heartbeat
        }

    def get_pika_connection_params(self):
        """
        获取pika连接参数对象
        """
        import pika
        credentials = pika.PlainCredentials(self.username, self.password)
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=credentials,
            blocked_connection_timeout=self.connection_timeout,
            heartbeat=self.heartbeat
        )


# 创建全局配置实例
rabbitmq_config = RabbitMQConfig()
import os
from typing import Dict, Optional

from hengline.utils.config_utils import get_settings_config
from hengline.logger import debug


class RocketMQConfig:
    """
    RocketMQ配置类，用于存储和管理RocketMQ的配置信息
    """
    
    def __init__(self):
        # 获取配置文件中的RocketMQ配置
        settings_config = get_settings_config()
        rocketmq_config = settings_config.get('rocketmq', {})
        
        # 从环境变量获取配置，环境变量优先级最高，其次是配置文件，最后是默认值
        self.name_server_address = os.environ.get('ROCKETMQ_NAME_SERVER', 
                            rocketmq_config.get('name_server_address', '127.0.0.1:9876'))
        self.producer_group = os.environ.get('ROCKETMQ_PRODUCER_GROUP', 
                          rocketmq_config.get('producer_group', 'default_producer_group'))
        self.consumer_group = os.environ.get('ROCKETMQ_CONSUMER_GROUP', 
                          rocketmq_config.get('consumer_group', 'default_consumer_group'))
        self.instance_name = os.environ.get('ROCKETMQ_INSTANCE_NAME', 
                         rocketmq_config.get('instance_name', 'default_instance'))
        self.retry_times = int(os.environ.get('ROCKETMQ_RETRY_TIMES', 
                       str(rocketmq_config.get('retry_times', '3'))))
        
        # 记录使用的配置
        debug(f"RocketMQ配置加载完成: name_server={self.name_server_address}, producer_group={self.producer_group}")
        
    def get_producer_config(self) -> Dict[str, any]:
        """
        获取生产者配置
        """
        return {
            'group_name': self.producer_group,
            'name_server_address': self.name_server_address,
            'instance_name': self.instance_name,
            'retry_times': self.retry_times
        }
        
    def get_consumer_config(self) -> Dict[str, any]:
        """
        获取消费者配置
        """
        return {
            'group_name': self.consumer_group,
            'name_server_address': self.name_server_address,
            'instance_name': self.instance_name
        }


# 创建全局配置实例
rocketmq_config = RocketMQConfig()
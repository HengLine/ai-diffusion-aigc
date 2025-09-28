"""
RocketMQ连接池模块

该模块提供了RocketMQ生产者和消费者的连接池管理功能，包括连接的创建、获取、归还和关闭等。
"""
import platform
import threading
import time
from typing import Dict, List, Optional, TypeVar, Generic, Any
from queue import Queue, Empty

from hengline.logger import debug, info, warning, error

# 检查是否为Windows系统
IS_WINDOWS = platform.system() == 'Windows'

# Windows系统下提供Mock实现
if IS_WINDOWS:
    warning("RocketMQ不支持Windows系统，将使用模拟实现")
    
    # Mock RocketMQConfig类
    class RocketMQConfig:
        def __init__(self, **kwargs):
            self.name_server_address = kwargs.get('name_server_address', '')
            self.producer_group = kwargs.get('producer_group', '')
            self.consumer_group = kwargs.get('consumer_group', '')
    
    # Mock rocketmq_config全局配置
    rocketmq_config = RocketMQConfig()
    
    # Mock RocketMQProducer类
    class RocketMQProducer:
        def __init__(self, **kwargs):
            self.name_server_address = kwargs.get('name_server_address', '')
            self.producer_group = kwargs.get('producer_group', '')
        
        def start(self):
            warning("Windows系统下模拟启动RocketMQ生产者")
        
        def shutdown(self):
            warning("Windows系统下模拟关闭RocketMQ生产者")
        
        def send_sync_message(self, topic, message_body, tags=None):
            warning(f"Windows系统下模拟发送同步消息到主题{topic}")
            return type('obj', (object,), {'status': 'OK'})()
        
        def send_async_message(self, topic, message_body, callback=None, tags=None):
            warning(f"Windows系统下模拟发送异步消息到主题{topic}")
            if callback:
                callback(type('obj', (object,), {'status': 'OK'})(), None)
        
        def send_oneway_message(self, topic, message_body, tags=None):
            warning(f"Windows系统下模拟发送单向消息到主题{topic}")
    
    # Mock RocketMQConsumer类
    class RocketMQConsumer:
        def __init__(self, **kwargs):
            self.name_server_address = kwargs.get('name_server_address', '')
            self.consumer_group = kwargs.get('consumer_group', '')
            self._subscriptions = {}
        
        def start(self):
            warning("Windows系统下模拟启动RocketMQ消费者")
        
        def shutdown(self):
            warning("Windows系统下模拟关闭RocketMQ消费者")
        
        def subscribe(self, topic, callback, tags=None):
            warning(f"Windows系统下模拟订阅主题{topic}")
            self._subscriptions[topic] = callback
        
        def unsubscribe(self, topic):
            warning(f"Windows系统下模拟取消订阅主题{topic}")
            if topic in self._subscriptions:
                del self._subscriptions[topic]
else:
    # 非Windows系统导入实际的RocketMQ组件
    from hengline.mq.rocketmq_config import RocketMQConfig, rocketmq_config
    from hengline.mq.rocketmq_producer import RocketMQProducer
    from hengline.mq.rocketmq_consumer import RocketMQConsumer


class ConnectionPoolError(Exception):
    """连接池相关错误的基类"""
    pass


class ConnectionClosedError(ConnectionPoolError):
    """连接已关闭的错误"""
    pass


class ConnectionTimeoutError(ConnectionPoolError):
    """获取连接超时的错误"""
    pass


T = TypeVar('T')


class RocketMQConnection(Generic[T]):
    """RocketMQ连接包装类，用于管理连接的生命周期"""
    def __init__(self, connection: T, pool=None):
        self.connection = connection
        self.pool = pool
        self.in_use = False
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.is_closed = False

    def close(self):
        """关闭连接"""
        if not self.is_closed:
            try:
                if hasattr(self.connection, 'shutdown'):
                    self.connection.shutdown()
                self.is_closed = True
                debug(f"连接已关闭: {self.connection}")
            except Exception as e:
                warning(f"关闭连接时出错: {str(e)}")

    def __enter__(self):
        """支持上下文管理器模式"""
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器时归还连接"""
        if self.pool and not self.is_closed:
            self.pool.return_connection(self)


class RocketMQConnectionPool(Generic[T]):
    """RocketMQ连接池基类"""
    def __init__(self, 
                 create_connection_func, 
                 config: RocketMQConfig = None,
                 max_connections: int = 5,
                 max_idle_time: int = 300,  # 5分钟
                 connection_timeout: int = 3):  # 3秒
        """
        初始化连接池

        Args:
            create_connection_func: 创建连接的函数
            config: RocketMQ配置对象
            max_connections: 最大连接数
            max_idle_time: 连接最大空闲时间（秒）
            connection_timeout: 获取连接超时时间（秒）
        """
        self.create_connection_func = create_connection_func
        self.config = config or rocketmq_config
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        self.pool: Queue[RocketMQConnection[T]] = Queue(maxsize=max_connections)
        self.active_connections: Dict[str, RocketMQConnection[T]] = {}
        self.lock = threading.RLock()
        self.is_closed = False
        
        # 启动连接清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
        self.cleanup_thread.start()
        
        debug(f"连接池已初始化: max_connections={max_connections}")
    
    def _create_connection(self) -> RocketMQConnection[T]:
        """创建新的连接"""
        try:
            connection = self.create_connection_func(self.config)
            wrapped_conn = RocketMQConnection(connection, self)
            debug(f"创建新连接: {connection}")
            return wrapped_conn
        except Exception as e:
            error(f"创建连接失败: {str(e)}")
            raise ConnectionPoolError(f"创建连接失败: {str(e)}")
    
    def get_connection(self) -> RocketMQConnection[T]:
        """
        从连接池获取一个连接

        Returns:
            RocketMQConnection: 连接包装对象

        Raises:
            ConnectionPoolError: 连接池错误
            ConnectionTimeoutError: 获取连接超时
        """
        if self.is_closed:
            raise ConnectionClosedError("连接池已关闭")
        
        start_time = time.time()
        
        while True:
            # 尝试从池中获取空闲连接
            try:
                wrapped_conn = self.pool.get(block=False)
                
                # 检查连接是否有效
                if wrapped_conn.is_closed:
                    continue
                
                # 检查连接是否超时
                if time.time() - wrapped_conn.last_used_at > self.max_idle_time:
                    wrapped_conn.close()
                    continue
                
                # 标记连接为使用中
                with self.lock:
                    wrapped_conn.in_use = True
                    wrapped_conn.last_used_at = time.time()
                    self.active_connections[id(wrapped_conn)] = wrapped_conn
                
                debug(f"从池中获取连接: {wrapped_conn.connection}")
                return wrapped_conn
            except Empty:
                pass
            
            # 如果没有空闲连接且未达到最大连接数，则创建新连接
            with self.lock:
                if len(self.active_connections) < self.max_connections:
                    try:
                        wrapped_conn = self._create_connection()
                        wrapped_conn.in_use = True
                        wrapped_conn.last_used_at = time.time()
                        self.active_connections[id(wrapped_conn)] = wrapped_conn
                        return wrapped_conn
                    except Exception:
                        # 创建连接失败，继续尝试获取现有连接
                        pass
            
            # 检查是否超时
            if time.time() - start_time > self.connection_timeout:
                raise ConnectionTimeoutError(f"获取连接超时（{self.connection_timeout}秒）")
            
            # 等待一段时间后重试
            time.sleep(0.1)
    
    def return_connection(self, wrapped_conn: RocketMQConnection[T]):
        """
        将连接归还到池中

        Args:
            wrapped_conn: 要归还的连接包装对象
        """
        if self.is_closed:
            wrapped_conn.close()
            return
        
        with self.lock:
            conn_id = id(wrapped_conn)
            if conn_id in self.active_connections:
                del self.active_connections[conn_id]
                
                if not wrapped_conn.is_closed:
                    wrapped_conn.in_use = False
                    wrapped_conn.last_used_at = time.time()
                    try:
                        self.pool.put(wrapped_conn, block=False)
                        debug(f"连接已归还到池中: {wrapped_conn.connection}")
                    except Exception:
                        # 如果池已满，则关闭连接
                        wrapped_conn.close()
    
    def _cleanup_idle_connections(self):
        """清理空闲时间过长的连接"""
        while not self.is_closed:
            try:
                time.sleep(60)  # 每分钟检查一次
                
                # 创建一个临时列表来存储需要清理的连接
                to_cleanup = []
                
                # 检查队列中的连接
                temp_pool = []
                current_time = time.time()
                
                # 遍历队列中的所有连接
                while not self.pool.empty():
                    wrapped_conn = self.pool.get(block=False)
                    if wrapped_conn.is_closed or current_time - wrapped_conn.last_used_at > self.max_idle_time:
                        to_cleanup.append(wrapped_conn)
                    else:
                        temp_pool.append(wrapped_conn)
                
                # 将有效的连接放回池中
                for wrapped_conn in temp_pool:
                    self.pool.put(wrapped_conn, block=False)
                
                # 关闭需要清理的连接
                for wrapped_conn in to_cleanup:
                    wrapped_conn.close()
                
                if to_cleanup:
                    debug(f"清理了 {len(to_cleanup)} 个空闲连接")
            except Exception as e:
                warning(f"清理空闲连接时出错: {str(e)}")
    
    def close(self):
        """关闭连接池，释放所有连接"""
        with self.lock:
            if self.is_closed:
                return
            
            self.is_closed = True
            
            # 关闭所有活跃连接
            for wrapped_conn in list(self.active_connections.values()):
                wrapped_conn.close()
            self.active_connections.clear()
            
            # 关闭池中所有连接
            while not self.pool.empty():
                try:
                    wrapped_conn = self.pool.get(block=False)
                    wrapped_conn.close()
                except Empty:
                    break
            
            info(f"连接池已关闭")
    
    def __del__(self):
        """析构函数，确保连接池被关闭"""
        self.close()
    
    def __enter__(self):
        """支持上下文管理器模式"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器时关闭连接池"""
        self.close()


# 创建全局的生产者和消费者连接池实例
_producer_pool = None
_consumer_pool = None
_pool_lock = threading.RLock()


def _create_producer(config: RocketMQConfig) -> RocketMQProducer:
    """创建RocketMQ生产者"""
    producer = RocketMQProducer(
        name_server_address=config.name_server_address,
        producer_group=config.producer_group
    )
    producer.start()
    return producer


def _create_consumer(config: RocketMQConfig) -> RocketMQConsumer:
    """创建RocketMQ消费者"""
    consumer = RocketMQConsumer(
        name_server_address=config.name_server_address,
        consumer_group=config.consumer_group
    )
    consumer.start()
    return consumer


def get_producer_pool(config: RocketMQConfig = None, **kwargs) -> RocketMQConnectionPool[RocketMQProducer]:
    """
    获取RocketMQ生产者连接池实例

    Args:
        config: RocketMQ配置对象，如果为None则使用全局配置
        **kwargs: 传递给连接池的额外参数

    Returns:
        RocketMQConnectionPool: 生产者连接池实例
    """
    global _producer_pool
    
    with _pool_lock:
        if _producer_pool is None or _producer_pool.is_closed:
            _producer_pool = RocketMQConnectionPool(
                create_connection_func=_create_producer,
                config=config,
                **kwargs
            )
    
    return _producer_pool


def get_consumer_pool(config: RocketMQConfig = None, **kwargs) -> RocketMQConnectionPool[RocketMQConsumer]:
    """
    获取RocketMQ消费者连接池实例

    Args:
        config: RocketMQ配置对象，如果为None则使用全局配置
        **kwargs: 传递给连接池的额外参数

    Returns:
        RocketMQConnectionPool: 消费者连接池实例
    """
    global _consumer_pool
    
    with _pool_lock:
        if _consumer_pool is None or _consumer_pool.is_closed:
            _consumer_pool = RocketMQConnectionPool(
                create_connection_func=_create_consumer,
                config=config,
                **kwargs
            )
    
    return _consumer_pool


def shutdown_all_pools():
    """关闭所有连接池"""
    global _producer_pool, _consumer_pool
    
    with _pool_lock:
        if _producer_pool is not None:
            _producer_pool.close()
            _producer_pool = None
        
        if _consumer_pool is not None:
            _consumer_pool.close()
            _consumer_pool = None
        
        info("所有RocketMQ连接池已关闭")
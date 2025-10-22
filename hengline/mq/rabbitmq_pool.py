import time
import threading
from queue import Queue, Empty
from typing import Generic, TypeVar, Dict, Optional, Callable
import logging

from hengline.logger import debug, warning, error, info
from hengline.mq.rabbitmq_config import RabbitMQConfig, rabbitmq_config
from hengline.mq.rabbitmq_producer import RabbitMQProducer
from hengline.mq.rabbitmq_consumer import RabbitMQConsumer


T = TypeVar('T')


class ConnectionPoolError(Exception):
    """连接池错误基类"""
    pass


class ConnectionClosedError(ConnectionPoolError):
    """连接池已关闭的错误"""
    pass


class ConnectionTimeoutError(ConnectionPoolError):
    """获取连接超时的错误"""
    pass


class RabbitMQConnection(Generic[T]):
    """RabbitMQ连接包装类，用于管理连接的生命周期"""
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


class RabbitMQConnectionPool(Generic[T]):
    """RabbitMQ连接池基类"""
    def __init__(self, 
                 create_connection_func, 
                 config: RabbitMQConfig = None,
                 max_connections: int = 5,
                 max_idle_time: int = 300,  # 5分钟
                 connection_timeout: int = 3):  # 3秒
        """
        初始化连接池

        Args:
            create_connection_func: 创建连接的函数
            config: RabbitMQ配置对象
            max_connections: 最大连接数
            max_idle_time: 连接最大空闲时间（秒）
            connection_timeout: 获取连接超时时间（秒）
        """
        self.create_connection_func = create_connection_func
        self.config = config or rabbitmq_config
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.connection_timeout = connection_timeout
        
        self.pool: Queue[RabbitMQConnection[T]] = Queue(maxsize=max_connections)
        self.active_connections: Dict[str, RabbitMQConnection[T]] = {}  # 使用连接ID作为键
        self.lock = threading.RLock()
        self.is_closed = False
        
        # 启动连接清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_idle_connections, daemon=True)
        self.cleanup_thread.start()
        
        debug(f"连接池已初始化: max_connections={max_connections}")
    
    def _create_connection(self) -> RabbitMQConnection[T]:
        """创建新的连接"""
        try:
            connection = self.create_connection_func(self.config)
            wrapped_conn = RabbitMQConnection(connection, self)
            debug(f"创建新连接: {connection}")
            return wrapped_conn
        except Exception as e:
            error(f"创建连接失败: {str(e)}")
            raise ConnectionPoolError(f"创建连接失败: {str(e)}")
    
    def get_connection(self) -> RabbitMQConnection[T]:
        """
        从连接池获取一个连接

        Returns:
            RabbitMQConnection: 连接包装对象

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
                if not wrapped_conn.is_closed and self._is_connection_valid(wrapped_conn.connection):
                    with self.lock:
                        wrapped_conn.in_use = True
                        wrapped_conn.last_used_at = time.time()
                        conn_id = id(wrapped_conn.connection)
                        self.active_connections[conn_id] = wrapped_conn
                    debug(f"从池中获取连接: {wrapped_conn.connection}")
                    return wrapped_conn
                else:
                    # 连接无效，关闭并继续尝试
                    wrapped_conn.close()
                    debug("获取到无效连接，已关闭")
            except Empty:
                # 池中没有可用连接，检查是否已达到最大连接数
                with self.lock:
                    if len(self.active_connections) < self.max_connections:
                        try:
                            wrapped_conn = self._create_connection()
                            wrapped_conn.in_use = True
                            wrapped_conn.last_used_at = time.time()
                            conn_id = id(wrapped_conn.connection)
                            self.active_connections[conn_id] = wrapped_conn
                            return wrapped_conn
                        except Exception as e:
                            error(f"创建新连接失败: {str(e)}")
                            # 创建失败，继续等待
            
            # 检查是否超时
            if time.time() - start_time > self.connection_timeout:
                raise ConnectionTimeoutError(f"获取连接超时: {self.connection_timeout}秒")
            
            # 短暂休眠后重试
            time.sleep(0.1)
    
    def _is_connection_valid(self, connection: T) -> bool:
        """
        检查连接是否有效

        Args:
            connection: 要检查的连接对象

        Returns:
            bool: 连接是否有效
        """
        try:
            # 不同类型的连接有不同的检查方法
            if isinstance(connection, RabbitMQProducer):
                return connection.connection and not connection.connection.is_closed
            elif isinstance(connection, RabbitMQConsumer):
                return connection.connection and not connection.connection.is_closed
            return True
        except Exception:
            return False
    
    def return_connection(self, wrapped_conn: RabbitMQConnection[T]):
        """
        归还连接到池中

        Args:
            wrapped_conn: 要归还的连接包装对象
        """
        if self.is_closed:
            wrapped_conn.close()
            return
        
        with self.lock:
            conn_id = id(wrapped_conn.connection)
            if conn_id in self.active_connections:
                del self.active_connections[conn_id]
            
            if not wrapped_conn.is_closed and self._is_connection_valid(wrapped_conn.connection):
                wrapped_conn.in_use = False
                wrapped_conn.last_used_at = time.time()
                
                try:
                    self.pool.put(wrapped_conn, block=False)
                except Exception:
                    # 池已满，关闭连接
                    wrapped_conn.close()
            else:
                # 连接已关闭或无效，不归还
                wrapped_conn.close()
    
    def _cleanup_idle_connections(self):
        """
        清理空闲时间过长的连接
        """
        while not self.is_closed:
            try:
                # 每30秒检查一次
                time.sleep(30)
                
                current_time = time.time()
                idle_connections = []
                
                # 从池中获取所有连接
                while True:
                    try:
                        wrapped_conn = self.pool.get(block=False)
                        if not wrapped_conn.is_closed and self._is_connection_valid(wrapped_conn.connection):
                            # 检查是否超过最大空闲时间
                            if current_time - wrapped_conn.last_used_at > self.max_idle_time:
                                wrapped_conn.close()
                                debug(f"清理空闲连接: {wrapped_conn.connection}")
                            else:
                                idle_connections.append(wrapped_conn)
                        else:
                            wrapped_conn.close()
                    except Empty:
                        break
                
                # 将未超时的连接放回池中
                for wrapped_conn in idle_connections:
                    try:
                        self.pool.put(wrapped_conn, block=False)
                    except Exception:
                        wrapped_conn.close()
            except Exception as e:
                warning(f"清理空闲连接时出错: {str(e)}")
    
    def close(self):
        """
        关闭连接池并释放所有资源
        """
        if self.is_closed:
            return
        
        self.is_closed = True
        
        # 关闭所有活跃连接
        with self.lock:
            for wrapped_conn in list(self.active_connections.values()):
                wrapped_conn.close()
            self.active_connections.clear()
        
        # 关闭所有空闲连接
        while True:
            try:
                wrapped_conn = self.pool.get(block=False)
                wrapped_conn.close()
            except Empty:
                break
        
        debug("连接池已关闭")


# 全局连接池实例
_producer_pool = None
_consumer_pool = None


def _create_producer(config: RabbitMQConfig) -> RabbitMQProducer:
    """创建RabbitMQ生产者"""
    producer = RabbitMQProducer()
    return producer


def _create_consumer(config: RabbitMQConfig) -> RabbitMQConsumer:
    """创建RabbitMQ消费者"""
    consumer = RabbitMQConsumer()
    return consumer


def get_producer_pool(config: RabbitMQConfig = None, **kwargs) -> RabbitMQConnectionPool[RabbitMQProducer]:
    """
    获取RabbitMQ生产者连接池实例

    Args:
        config: RabbitMQ配置对象，如果为None则使用全局配置
        **kwargs: 其他连接池参数

    Returns:
        RabbitMQConnectionPool: 生产者连接池实例
    """
    global _producer_pool
    
    if _producer_pool is None or _producer_pool.is_closed:
        _producer_pool = RabbitMQConnectionPool(
            create_connection_func=_create_producer,
            config=config,
            **kwargs
        )
    
    return _producer_pool


def get_consumer_pool(config: RabbitMQConfig = None, **kwargs) -> RabbitMQConnectionPool[RabbitMQConsumer]:
    """
    获取RabbitMQ消费者连接池实例

    Args:
        config: RabbitMQ配置对象，如果为None则使用全局配置
        **kwargs: 其他连接池参数

    Returns:
        RabbitMQConnectionPool: 消费者连接池实例
    """
    global _consumer_pool
    
    if _consumer_pool is None or _consumer_pool.is_closed:
        _consumer_pool = RabbitMQConnectionPool(
            create_connection_func=_create_consumer,
            config=config,
            **kwargs
        )
    
    return _consumer_pool


def shutdown_all_pools():
    """
    关闭所有RabbitMQ连接池
    """
    global _producer_pool, _consumer_pool
    
    # 关闭生产者连接池
    if _producer_pool and not _producer_pool.is_closed:
        try:
            _producer_pool.close()
        except Exception as e:
            error(f"关闭生产者连接池时出错: {str(e)}")
    
    # 关闭消费者连接池
    if _consumer_pool and not _consumer_pool.is_closed:
        try:
            _consumer_pool.close()
        except Exception as e:
            error(f"关闭消费者连接池时出错: {str(e)}")
    
    # 重置全局实例
    _producer_pool = None
    _consumer_pool = None
    
    info("所有RabbitMQ连接池已关闭")
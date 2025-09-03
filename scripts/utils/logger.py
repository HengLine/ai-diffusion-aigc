# -*- coding: utf-8 -*-
"""
自定义日志模块，按天创建日志文件，最大10MB
"""

import os
import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

class DailyRotatingFileHandler(RotatingFileHandler):
    """按天和文件大小旋转的日志处理器"""
    def __init__(self, base_dir: str, base_filename: str, max_bytes: int = 10*1024*1024, backup_count: int = 30):
        self.base_dir = base_dir
        self.base_filename = base_filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.current_date = datetime.date.today()
        
        # 确保日志目录存在
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 初始文件名
        self.current_log_file = self._get_log_filename()
        
        super().__init__(self.current_log_file, maxBytes=self.max_bytes, backupCount=self.backup_count, encoding='utf-8')
    
    def _get_log_filename(self) -> str:
        """获取当前日期的日志文件名"""
        today = datetime.date.today()
        date_str = today.strftime('%Y-%m-%d')
        
        # 基础文件名格式：base_dir/base_filename_YYYY-MM-DD.log
        base_log_file = os.path.join(self.base_dir, f"{self.base_filename}_{date_str}.log")
        
        # 检查是否需要创建序号后缀的文件
        count = 1
        log_file = base_log_file
        while os.path.exists(log_file) and os.path.getsize(log_file) >= self.max_bytes:
            log_file = os.path.join(self.base_dir, f"{self.base_filename}_{date_str}_{count}.log")
            count += 1
        
        return log_file
    
    def emit(self, record):
        """重写emit方法，实现按天和大小旋转"""
        # 检查日期是否变更
        today = datetime.date.today()
        if today != self.current_date:
            self.current_date = today
            self.current_log_file = self._get_log_filename()
            self.baseFilename = self.current_log_file
            
            # 关闭当前文件并打开新文件
            self.stream.close()
            self.mode = 'a'
            self.stream = self._open()
        
        # 检查文件大小是否超过限制
        if os.path.exists(self.current_log_file) and os.path.getsize(self.current_log_file) >= self.max_bytes:
            self.current_log_file = self._get_log_filename()
            self.baseFilename = self.current_log_file
            
            # 关闭当前文件并打开新文件
            self.stream.close()
            self.mode = 'a'
            self.stream = self._open()
        
        super().emit(record)

class Logger:
    """自定义日志类"""
    def __init__(self, name: str = 'aigc_demo', log_dir: Optional[str] = None, max_bytes: int = 10*1024*1024):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录路径，默认在项目根目录下的logs目录
            max_bytes: 单个日志文件最大字节数，默认10MB
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 如果已经有处理器，则清除
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 定义日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        if log_dir is None:
            # 默认日志目录：项目根目录下的logs文件夹
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(project_root, 'logs')
        
        file_handler = DailyRotatingFileHandler(log_dir, name, max_bytes)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告信息"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """记录错误信息"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """记录严重错误信息"""
        self.logger.critical(message)

# 创建全局日志实例
logger = Logger()

# 方便使用的函数

def debug(message: str):
    logger.debug(message)

def info(message: str):
    logger.info(message)

def warning(message: str):
    logger.warning(message)

def error(message: str):
    logger.error(message)

def critical(message: str):
    logger.critical(message)
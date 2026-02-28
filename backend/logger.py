"""
统一日志模块
提供结构化日志记录，支持不同级别和上下文
"""
import logging
import sys
from datetime import datetime
from typing import Optional, Any
import os

# 日志级别配置（从环境变量读取）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 创建自定义日志格式
class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式（仅在终端中显示）"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(name: str = "emotion_learning") -> logging.Logger:
    """
    设置并返回配置好的日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # 格式化器
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.propagate = False
    
    return logger


# 全局日志器实例
logger = setup_logger()


def log_request(method: str, path: str, extra: Optional[dict] = None):
    """记录API请求"""
    msg = f"[{method}] {path}"
    if extra:
        msg += f" | {extra}"
    logger.info(msg)


def log_response(path: str, status: int, duration_ms: float):
    """记录API响应"""
    logger.info(f"[Response] {path} | status={status} | duration={duration_ms:.1f}ms")


def log_error(context: str, error: Exception, extra: Optional[dict] = None):
    """
    记录错误日志
    
    Args:
        context: 错误发生的上下文（如函数名、模块名）
        error: 异常对象
        extra: 额外信息
    """
    msg = f"[{context}] {type(error).__name__}: {str(error)}"
    if extra:
        msg += f" | {extra}"
    logger.error(msg, exc_info=True)


def log_warning(context: str, message: str, extra: Optional[dict] = None):
    """记录警告日志"""
    msg = f"[{context}] {message}"
    if extra:
        msg += f" | {extra}"
    logger.warning(msg)


def log_info(context: str, message: str, extra: Optional[dict] = None):
    """记录信息日志"""
    msg = f"[{context}] {message}"
    if extra:
        msg += f" | {extra}"
    logger.info(msg)


def log_debug(context: str, message: str, extra: Optional[dict] = None):
    """记录调试日志"""
    msg = f"[{context}] {message}"
    if extra:
        msg += f" | {extra}"
    logger.debug(msg)


def log_ai_service(service: str, action: str, success: bool, duration_ms: float = 0, extra: Optional[dict] = None):
    """
    记录AI服务调用日志
    
    Args:
        service: 服务名称（asr, tts, emotion, chat）
        action: 操作名称
        success: 是否成功
        duration_ms: 耗时（毫秒）
        extra: 额外信息
    """
    status = "✓" if success else "✗"
    msg = f"[AI:{service}] {status} {action} | duration={duration_ms:.1f}ms"
    if extra:
        msg += f" | {extra}"
    
    if success:
        logger.info(msg)
    else:
        logger.warning(msg)


# 性能计时器上下文管理器
class Timer:
    """简单的计时器，用于测量代码执行时间"""
    
    def __init__(self, context: str = ""):
        self.context = context
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, *args):
        self.end_time = datetime.now()
        if self.context:
            log_debug("Timer", f"{self.context} completed", {
                "duration_ms": self.elapsed_ms
            })
    
    @property
    def elapsed_ms(self) -> float:
        """返回已过去的毫秒数"""
        if self.start_time is None:
            return 0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() * 1000

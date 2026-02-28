"""
统一异常处理模块
提供自定义异常类和全局异常处理器
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Any
import traceback

try:
    from .logger import log_error, log_warning
except ImportError:
    from backend.logger import log_error, log_warning


# ============ 自定义异常类 ============

class AppException(Exception):
    """应用基础异常"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class ValidationError(AppException):
    """参数验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else None
        )


class NotFoundError(AppException):
    """资源未找到"""
    
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource}未找到"
        if identifier:
            message = f"{resource} '{identifier}' 未找到"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "id": identifier}
        )


class AIServiceError(AppException):
    """AI服务错误"""
    
    def __init__(self, service: str, message: str, recoverable: bool = True):
        super().__init__(
            message=f"{service}服务错误: {message}",
            status_code=503 if recoverable else 500,
            error_code="AI_SERVICE_ERROR",
            details={"service": service, "recoverable": recoverable}
        )


class AudioProcessingError(AppException):
    """音频处理错误"""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            error_code="AUDIO_PROCESSING_ERROR"
        )


class RateLimitError(AppException):
    """请求频率限制"""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"请求过于频繁，请{retry_after}秒后重试",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


# ============ 异常处理器 ============

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用自定义异常"""
    log_warning("ExceptionHandler", exc.message, {
        "path": request.url.path,
        "error_code": exc.error_code
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理FastAPI HTTP异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": None
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的通用异常"""
    log_error("UnhandledException", exc, {
        "path": request.url.path,
        "method": request.method
    })
    
    # 生产环境不暴露详细错误
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "details": None
            }
        }
    )


def register_exception_handlers(app):
    """注册所有异常处理器到FastAPI应用"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(ValidationError, app_exception_handler)
    app.add_exception_handler(NotFoundError, app_exception_handler)
    app.add_exception_handler(AIServiceError, app_exception_handler)
    app.add_exception_handler(AudioProcessingError, app_exception_handler)
    app.add_exception_handler(RateLimitError, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    # 通用异常处理器（兜底）
    app.add_exception_handler(Exception, general_exception_handler)


# ============ 辅助函数 ============

def safe_execute(func, default=None, context: str = ""):
    """
    安全执行函数，捕获异常并返回默认值
    
    Args:
        func: 要执行的函数（无参数）
        default: 异常时的默认返回值
        context: 日志上下文
    
    Returns:
        函数返回值或默认值
    """
    try:
        return func()
    except Exception as e:
        if context:
            log_warning(context, f"执行失败，使用默认值: {str(e)}")
        return default


async def safe_execute_async(coro, default=None, context: str = ""):
    """
    安全执行异步函数
    
    Args:
        coro: 要执行的协程
        default: 异常时的默认返回值
        context: 日志上下文
    
    Returns:
        协程返回值或默认值
    """
    try:
        return await coro
    except Exception as e:
        if context:
            log_warning(context, f"异步执行失败，使用默认值: {str(e)}")
        return default

"""统一错误处理模块"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK_ERROR = "network_error"
    DATA_ERROR = "data_error"
    CONFIG_ERROR = "config_error"
    SYSTEM_ERROR = "system_error"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"


class OpportunityDetectorError(Exception):
    """机会探测器基础异常类"""
    
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        recoverable: bool = True,
        details: Optional[dict] = None,
    ):
        self.error_type = error_type
        self.message = message
        self.recoverable = recoverable
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "recoverable": self.recoverable,
            "details": self.details,
        }


class DataCollectionError(OpportunityDetectorError):
    """数据采集错误"""
    
    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        recoverable: bool = True,
        details: Optional[dict] = None,
    ):
        super().__init__(
            error_type=ErrorType.DATA_ERROR,
            message=message,
            recoverable=recoverable,
            details=details or {"source": source},
        )
        self.source = source


class ConfigurationError(OpportunityDetectorError):
    """配置错误"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        recoverable: bool = False,
        details: Optional[dict] = None,
    ):
        super().__init__(
            error_type=ErrorType.CONFIG_ERROR,
            message=message,
            recoverable=recoverable,
            details=details or {"field": field},
        )
        self.field = field


class APIError(OpportunityDetectorError):
    """API调用错误"""
    
    def __init__(
        self,
        message: str,
        api: Optional[str] = None,
        status_code: Optional[int] = None,
        recoverable: bool = True,
        details: Optional[dict] = None,
    ):
        super().__init__(
            error_type=ErrorType.API_ERROR,
            message=message,
            recoverable=recoverable,
            details=details or {"api": api, "status_code": status_code},
        )
        self.api = api
        self.status_code = status_code


class ValidationError(OpportunityDetectorError):
    """验证错误"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        recoverable: bool = False,
        details: Optional[dict] = None,
    ):
        super().__init__(
            error_type=ErrorType.VALIDATION_ERROR,
            message=message,
            recoverable=recoverable,
            details=details or {"field": field},
        )
        self.field = field


def handle_error(error: Exception, context: Optional[dict] = None) -> OpportunityDetectorError:
    """
    统一错误处理函数
    
    根据错误类型自动转换为机会探测器异常，并添加上下文信息
    
    Args:
        error: 原始异常
        context: 上下文信息
        
    Returns:
        OpportunityDetectorError: 转换后的异常
    """
    context = context or {}
    
    if isinstance(error, OpportunityDetectorError):
        # 已经是机会探测器异常，直接返回
        return error
    
    # 根据错误类型转换
    if isinstance(error, (ConnectionError, TimeoutError)):
        return DataCollectionError(
            message=f"连接错误: {str(error)}",
            source=context.get("source"),
            recoverable=True,
        )
    
    if isinstance(error, ValueError):
        return ValidationError(
            message=f"验证错误: {str(error)}",
            field=context.get("field"),
            recoverable=False,
        )
    
    if isinstance(error, FileNotFoundError):
        return ConfigurationError(
            message=f"配置文件不存在: {str(error)}",
            field=context.get("field"),
            recoverable=False,
        )
    
    # 默认错误
    return OpportunityDetectorError(
        error_type=ErrorType.SYSTEM_ERROR,
        message=f"系统错误: {str(error)}",
        recoverable=False,
        details=context,
    )


class ErrorContext:
    """错误上下文管理器"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        return self.context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 异常处理
            error = handle_error(exc_val, self.context)
            # 可以在这里记录日志或发送告警
            # 重新抛出异常
            return False
        return False

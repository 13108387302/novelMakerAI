#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理机制

简化和统一错误处理，提供一致的错误处理接口。
"""

import logging
import traceback
import functools
from typing import Any, Callable, Optional, Union, TypeVar, Dict
from enum import Enum
from dataclasses import dataclass

from .base_utils import BaseUtility, UtilResult

logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    VALIDATION = "validation"
    NETWORK = "network"
    FILE_IO = "file_io"
    DATABASE = "database"
    AI_SERVICE = "ai_service"
    UI = "ui"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """错误信息"""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    traceback: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class UnifiedErrorHandler(BaseUtility):
    """
    统一错误处理器
    
    提供统一的错误处理、记录和报告功能。
    """
    
    def __init__(self, enable_user_notifications: bool = True):
        """
        初始化错误处理器
        
        Args:
            enable_user_notifications: 是否启用用户通知
        """
        super().__init__("UnifiedErrorHandler")
        self.enable_user_notifications = enable_user_notifications
        self._error_history = []
        self._error_callbacks = {}
        
    def handle_error(
        self,
        error: Exception,
        operation: str = "",
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Dict[str, Any] = None,
        show_user: bool = None
    ) -> ErrorInfo:
        """
        处理错误
        
        Args:
            error: 异常对象
            operation: 操作名称
            category: 错误类别
            severity: 错误严重程度
            context: 错误上下文
            show_user: 是否显示给用户
            
        Returns:
            ErrorInfo: 错误信息
        """
        error_info = ErrorInfo(
            message=str(error),
            category=category,
            severity=severity,
            operation=operation,
            traceback=traceback.format_exc(),
            context=context or {}
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 保存到历史记录
        self._error_history.append(error_info)
        if len(self._error_history) > 1000:  # 限制历史记录数量
            self._error_history.pop(0)
        
        # 执行回调
        self._execute_callbacks(error_info)
        
        # 用户通知
        if show_user is None:
            show_user = self.enable_user_notifications and severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        
        if show_user:
            self._notify_user(error_info)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """记录错误日志"""
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        message = f"[{error_info.category.value}] {error_info.operation}: {error_info.message}"
        
        self.logger.log(log_level, message)
        
        # 对于高严重程度的错误，记录详细堆栈
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and error_info.traceback:
            self.logger.error(f"详细堆栈:\n{error_info.traceback}")
    
    def _execute_callbacks(self, error_info: ErrorInfo) -> None:
        """执行错误回调"""
        callbacks = self._error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"错误回调执行失败: {e}")
    
    def _notify_user(self, error_info: ErrorInfo) -> None:
        """通知用户"""
        # 这里可以集成UI通知机制
        # 目前只记录日志
        self.logger.info(f"用户通知: {error_info.message}")
    
    def register_callback(self, category: ErrorCategory, callback: Callable[[ErrorInfo], None]) -> None:
        """注册错误回调"""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)
    
    def get_error_summary(self, category: Optional[ErrorCategory] = None) -> Dict[str, Any]:
        """获取错误摘要"""
        errors = self._error_history
        if category:
            errors = [e for e in errors if e.category == category]
        
        if not errors:
            return {}
        
        severity_counts = {}
        category_counts = {}
        
        for error in errors:
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
        
        return {
            'total_errors': len(errors),
            'severity_distribution': severity_counts,
            'category_distribution': category_counts,
            'recent_errors': [
                {
                    'message': e.message,
                    'category': e.category.value,
                    'severity': e.severity.value,
                    'operation': e.operation
                }
                for e in errors[-10:]  # 最近10个错误
            ]
        }
    
    def validate_config(self) -> UtilResult[bool]:
        """验证配置"""
        return UtilResult.success_result(True)
    
    def cleanup(self) -> UtilResult[bool]:
        """清理资源"""
        self._error_history.clear()
        self._error_callbacks.clear()
        return UtilResult.success_result(True)


# 错误处理装饰器
def handle_errors(
    operation: str = "",
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    return_on_error: Any = None,
    show_user: bool = False
):
    """
    统一错误处理装饰器
    
    Args:
        operation: 操作名称
        category: 错误类别
        severity: 错误严重程度
        return_on_error: 错误时的返回值
        show_user: 是否显示给用户
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                if handler:
                    handler.handle_error(
                        error=e,
                        operation=operation or func.__name__,
                        category=category,
                        severity=severity,
                        show_user=show_user
                    )
                
                return return_on_error
        
        return wrapper
    return decorator


def handle_async_errors(
    operation: str = "",
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    return_on_error: Any = None,
    show_user: bool = False
):
    """
    异步错误处理装饰器
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                if handler:
                    handler.handle_error(
                        error=e,
                        operation=operation or func.__name__,
                        category=category,
                        severity=severity,
                        show_user=show_user
                    )
                
                return return_on_error
        
        return wrapper
    return decorator


# 便捷的错误处理函数
def safe_execute(
    func: Callable,
    *args,
    operation: str = "",
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    default_return: Any = None,
    **kwargs
) -> Any:
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handler = get_error_handler()
        if handler:
            handler.handle_error(
                error=e,
                operation=operation or func.__name__,
                category=category
            )
        return default_return


# 全局错误处理器实例
_global_error_handler: Optional[UnifiedErrorHandler] = None


def get_error_handler() -> Optional[UnifiedErrorHandler]:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = UnifiedErrorHandler()
    return _global_error_handler


def set_error_handler(handler: UnifiedErrorHandler) -> None:
    """设置全局错误处理器"""
    global _global_error_handler
    _global_error_handler = handler

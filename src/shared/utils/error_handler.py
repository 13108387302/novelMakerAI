#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理模块

提供统一的错误处理和用户友好的错误消息
"""

import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QObject, pyqtSignal

from .logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity:
    """
    错误严重程度常量类

    定义应用程序中不同类型错误的严重程度级别。
    用于错误分类和处理策略选择。
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ApplicationError(Exception):
    """
    应用程序基础异常类

    所有应用程序自定义异常的基类。
    包含错误消息、严重程度、详细信息和时间戳。

    实现方式：
    - 继承标准Exception类
    - 添加严重程度和详细信息属性
    - 自动记录异常发生时间
    - 支持结构化的错误信息

    Attributes:
        message: 错误消息
        severity: 错误严重程度
        details: 详细错误信息
        timestamp: 异常发生时间
    """

    def __init__(self, message: str, severity: str = ErrorSeverity.ERROR, details: Optional[str] = None):
        """
        初始化应用程序异常

        Args:
            message: 错误消息
            severity: 错误严重程度，默认为ERROR
            details: 详细错误信息（可选）
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.details = details
        self.timestamp = datetime.now()


class ValidationError(ApplicationError):
    """
    验证错误异常类

    用于表示数据验证失败的异常。
    通常用于用户输入验证和数据格式检查。

    Attributes:
        field: 验证失败的字段名称
    """

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[str] = None):
        """
        初始化验证错误

        Args:
            message: 错误消息
            field: 验证失败的字段名称（可选）
            details: 详细错误信息（可选）
        """
        super().__init__(message, ErrorSeverity.WARNING, details)
        self.field = field


class ServiceError(ApplicationError):
    """
    服务层错误异常类

    用于表示服务层操作失败的异常。
    通常用于业务逻辑错误和外部服务调用失败。
    """
    pass


class RepositoryError(ApplicationError):
    """仓储层错误"""
    pass


class UIError(ApplicationError):
    """UI层错误"""
    pass


class ErrorHandler(QObject):
    """统一错误处理器"""
    
    # 错误信号
    error_occurred = pyqtSignal(str, str, str)  # message, severity, details
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        super().__init__()
        self.parent_widget = parent_widget
        self.error_callbacks: Dict[str, Callable] = {}
        
    def register_error_callback(self, error_type: str, callback: Callable):
        """注册错误回调"""
        self.error_callbacks[error_type] = callback
        
    def handle_exception(self, exception: Exception, context: str = "") -> None:
        """处理异常"""
        try:
            if isinstance(exception, ApplicationError):
                self._handle_application_error(exception, context)
            else:
                self._handle_system_error(exception, context)
                
        except Exception as e:
            # 错误处理器本身出错时的兜底处理
            logger.critical(f"错误处理器异常: {e}")
            self._show_critical_error("系统错误处理器异常，请重启应用程序")
            
    def _handle_application_error(self, error: ApplicationError, context: str):
        """处理应用程序错误"""
        error_type = type(error).__name__
        
        # 记录日志
        log_message = f"应用程序错误 [{context}]: {error.message}"
        if error.details:
            log_message += f" - 详情: {error.details}"
            
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
            
        # 发出信号
        self.error_occurred.emit(error.message, error.severity, error.details or "")
        
        # 执行注册的回调
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error, context)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")
                
        # 显示用户界面
        self._show_error_dialog(error, context)
        
    def _handle_system_error(self, error: Exception, context: str):
        """处理系统错误"""
        error_message = str(error)
        error_details = traceback.format_exc()
        
        # 记录日志
        logger.error(f"系统错误 [{context}]: {error_message}\n{error_details}")
        
        # 创建应用程序错误包装
        app_error = ApplicationError(
            message=self._get_user_friendly_message(error),
            severity=ErrorSeverity.ERROR,
            details=error_details
        )
        
        # 发出信号
        self.error_occurred.emit(app_error.message, app_error.severity, app_error.details)
        
        # 显示用户界面
        self._show_error_dialog(app_error, context)
        
    def _get_user_friendly_message(self, error: Exception) -> str:
        """获取用户友好的错误消息"""
        error_type = type(error).__name__
        
        friendly_messages = {
            "FileNotFoundError": "找不到指定的文件",
            "PermissionError": "没有足够的权限执行此操作",
            "ConnectionError": "网络连接失败",
            "TimeoutError": "操作超时",
            "ValueError": "输入的数据格式不正确",
            "TypeError": "数据类型错误",
            "KeyError": "缺少必要的配置信息",
            "ImportError": "缺少必要的程序组件",
            "MemoryError": "内存不足",
            "OSError": "系统操作失败"
        }
        
        return friendly_messages.get(error_type, f"发生了未知错误: {str(error)}")
        
    def _show_error_dialog(self, error: ApplicationError, context: str):
        """显示错误对话框"""
        if not self.parent_widget:
            return
            
        try:
            title = self._get_dialog_title(error.severity)
            message = error.message
            
            if context:
                message = f"在 {context} 时发生错误:\n\n{message}"
                
            if error.severity == ErrorSeverity.CRITICAL:
                QMessageBox.critical(self.parent_widget, title, message)
            elif error.severity == ErrorSeverity.ERROR:
                QMessageBox.critical(self.parent_widget, title, message)
            elif error.severity == ErrorSeverity.WARNING:
                QMessageBox.warning(self.parent_widget, title, message)
            else:
                QMessageBox.information(self.parent_widget, title, message)
                
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}")
            
    def _get_dialog_title(self, severity: str) -> str:
        """获取对话框标题"""
        titles = {
            ErrorSeverity.CRITICAL: "严重错误",
            ErrorSeverity.ERROR: "错误",
            ErrorSeverity.WARNING: "警告",
            ErrorSeverity.INFO: "信息"
        }
        return titles.get(severity, "通知")
        
    def _show_critical_error(self, message: str):
        """显示严重错误（兜底处理）"""
        try:
            if self.parent_widget:
                QMessageBox.critical(self.parent_widget, "严重错误", message)
            else:
                print(f"严重错误: {message}")
        except:
            print(f"严重错误: {message}")


# 全局错误处理器实例
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_error_handler(handler: ErrorHandler):
    """设置全局错误处理器"""
    global _global_error_handler
    _global_error_handler = handler


def handle_errors(context: str = "", show_dialog: bool = True):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                if not show_dialog:
                    # 只记录日志，不显示对话框
                    error_handler.parent_widget = None
                error_handler.handle_exception(e, context or func.__name__)
                return None
        return wrapper
    return decorator


def handle_async_errors(context: str = "", show_dialog: bool = True):
    """
    异步错误处理装饰器

    为异步函数提供统一的错误处理机制，自动捕获异常并通过错误处理器处理。

    Args:
        context: 错误上下文描述，用于日志记录
        show_dialog: 是否显示错误对话框，False时只记录日志

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                if not show_dialog:
                    # 只记录日志，不显示对话框
                    error_handler.parent_widget = None
                error_handler.handle_exception(e, context or func.__name__)
                return None
        return wrapper
    return decorator


def safe_execute(func: Callable, *args: Any, context: str = "", default_return: Any = None, **kwargs: Any) -> Any:
    """
    安全执行函数

    捕获函数执行过程中的异常，通过错误处理器处理并返回默认值。

    Args:
        func: 要执行的函数
        *args: 函数的位置参数
        context: 错误上下文描述
        default_return: 发生异常时的默认返回值
        **kwargs: 函数的关键字参数

    Returns:
        Any: 函数的返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler = get_error_handler()
        error_handler.handle_exception(e, context or func.__name__)
        return default_return


async def safe_execute_async(func: Callable, *args: Any, context: str = "", default_return: Any = None, **kwargs: Any) -> Any:
    """
    安全执行异步函数

    捕获异步函数执行过程中的异常，通过错误处理器处理并返回默认值。

    Args:
        func: 要执行的异步函数
        *args: 函数的位置参数
        context: 错误上下文描述
        default_return: 发生异常时的默认返回值
        **kwargs: 函数的关键字参数

    Returns:
        Any: 函数的返回值或默认值
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        error_handler = get_error_handler()
        error_handler.handle_exception(e, context or func.__name__)
        return default_return


# 便捷函数
def raise_validation_error(message: str, field: Optional[str] = None, details: Optional[str] = None):
    """抛出验证错误"""
    raise ValidationError(message, field, details)


def raise_service_error(message: str, details: Optional[str] = None):
    """抛出服务错误"""
    raise ServiceError(message, ErrorSeverity.ERROR, details)


def raise_repository_error(message: str, details: Optional[str] = None):
    """抛出仓储错误"""
    raise RepositoryError(message, ErrorSeverity.ERROR, details)


def raise_ui_error(message: str, details: Optional[str] = None):
    """抛出UI错误"""
    raise UIError(message, ErrorSeverity.ERROR, details)

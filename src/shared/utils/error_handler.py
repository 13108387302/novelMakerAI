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

from PyQt6.QtWidgets import QMessageBox, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QObject, pyqtSignal

from .logger import get_logger

logger = get_logger(__name__)

# 延迟导入智能恢复系统，避免循环导入
def _get_recovery_system():
    """获取智能恢复系统（延迟导入）"""
    try:
        from src.shared.stability.intelligent_recovery_system import get_recovery_system, ErrorContext
        return get_recovery_system(), ErrorContext
    except ImportError:
        return None, None


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

        # 智能恢复系统集成
        self.recovery_system = None
        self.error_context_class = None
        self._initialize_recovery_system()
        
    def _initialize_recovery_system(self):
        """初始化智能恢复系统"""
        try:
            self.recovery_system, self.error_context_class = _get_recovery_system()
            if self.recovery_system:
                logger.info("智能恢复系统已集成到错误处理器")
            else:
                logger.debug("智能恢复系统不可用")
        except Exception as e:
            logger.warning(f"初始化智能恢复系统失败: {e}")

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
        """处理应用程序错误（增强版本）"""
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

        # 尝试智能恢复（对于严重错误和普通错误）
        recovery_attempted = False
        if (self.recovery_system and self.error_context_class and
            error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]):
            try:
                recovery_attempted = self._attempt_intelligent_recovery(error, context)
            except Exception as e:
                logger.error(f"智能恢复尝试失败: {e}")

        # 发出信号
        self.error_occurred.emit(error.message, error.severity, error.details or "")

        # 执行注册的回调
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error, context)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")

        # 如果没有尝试智能恢复或恢复失败，显示用户界面
        if not recovery_attempted:
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

    def _attempt_intelligent_recovery(self, error: ApplicationError, context: str) -> bool:
        """
        尝试智能恢复

        Args:
            error: 应用程序错误
            context: 错误上下文

        Returns:
            bool: 是否尝试了恢复（不代表恢复成功）
        """
        try:
            if not self.recovery_system or not self.error_context_class:
                return False

            # 创建错误上下文
            error_context = self.error_context_class(
                exception=Exception(error.message),
                operation=context or "unknown",
                component="error_handler",
                user_data={'original_error': error}
            )

            # 异步执行恢复（在后台线程中）
            import threading
            import asyncio

            def recovery_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    async def perform_recovery():
                        result = await self.recovery_system.recover_from_error(error_context)
                        return result

                    result = loop.run_until_complete(perform_recovery())
                    loop.close()

                    # 在主线程中处理结果
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self._handle_recovery_result(result, error, context))

                except Exception as e:
                    logger.error(f"智能恢复线程异常: {e}")
                    # 恢复失败，显示错误对话框
                    QTimer.singleShot(0, lambda: self._show_error_dialog(error, context))

            # 启动恢复线程
            thread = threading.Thread(target=recovery_thread, daemon=True)
            thread.start()

            return True  # 表示已尝试恢复

        except Exception as e:
            logger.error(f"启动智能恢复失败: {e}")
            return False

    def _handle_recovery_result(self, result, error: ApplicationError, context: str):
        """处理恢复结果"""
        try:
            # 导入恢复结果枚举
            from src.shared.stability.intelligent_recovery_system import RecoveryResult

            if result == RecoveryResult.SUCCESS:
                logger.info(f"智能恢复成功: {error.message}")
                # 成功恢复，不显示错误对话框
                return
            elif result == RecoveryResult.PARTIAL_SUCCESS:
                logger.info(f"智能恢复部分成功: {error.message}")
                # 部分成功，仍显示对话框但降低严重程度
                if error.severity == ErrorSeverity.CRITICAL:
                    error.severity = ErrorSeverity.ERROR
                elif error.severity == ErrorSeverity.ERROR:
                    error.severity = ErrorSeverity.WARNING
            else:
                logger.warning(f"智能恢复失败: {error.message}, 结果: {result}")

            # 其他情况仍显示错误对话框
            self._show_error_dialog(error, context)

        except ImportError:
            logger.warning("无法导入恢复结果枚举，显示错误对话框")
            self._show_error_dialog(error, context)
        except Exception as e:
            logger.error(f"处理恢复结果失败: {e}")
            self._show_error_dialog(error, context)
        
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
        """显示错误对话框（增强版本）"""
        if not self.parent_widget:
            return

        try:
            # 对于严重错误和普通错误，使用智能错误对话框
            if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR]:
                try:
                    dialog = IntelligentErrorDialog(error, context, self.parent_widget)
                    dialog.exec()
                    return
                except Exception as e:
                    logger.warning(f"智能错误对话框创建失败，使用标准对话框: {e}")

            # 回退到标准对话框
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


class IntelligentErrorDialog(QDialog):
    """
    智能错误对话框

    提供更友好的错误处理界面，包括自动恢复选项
    """

    def __init__(self, error: ApplicationError, context: str, parent: QWidget = None):
        super().__init__(parent)
        self.error = error
        self.context = context
        self.recovery_system = None
        self.error_context_class = None

        # 尝试获取智能恢复系统
        self.recovery_system, self.error_context_class = _get_recovery_system()

        self.setWindowTitle(self._get_dialog_title())
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self._setup_ui()
        self._setup_connections()

    def _get_dialog_title(self) -> str:
        """获取对话框标题"""
        titles = {
            ErrorSeverity.CRITICAL: "严重错误",
            ErrorSeverity.ERROR: "错误",
            ErrorSeverity.WARNING: "警告",
            ErrorSeverity.INFO: "信息"
        }
        return titles.get(self.error.severity, "通知")

    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)

        # 错误信息区域
        error_layout = QVBoxLayout()

        # 错误标题
        title_label = QLabel(f"<h3>{self.error.message}</h3>")
        error_layout.addWidget(title_label)

        # 上下文信息
        if self.context:
            context_label = QLabel(f"<b>发生位置:</b> {self.context}")
            error_layout.addWidget(context_label)

        # 时间信息
        time_label = QLabel(f"<b>发生时间:</b> {self.error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        error_layout.addWidget(time_label)

        layout.addLayout(error_layout)

        # 详细信息（可展开）
        if self.error.details:
            details_label = QLabel("<b>详细信息:</b>")
            layout.addWidget(details_label)

            details_text = QTextEdit()
            details_text.setPlainText(self.error.details)
            details_text.setMaximumHeight(150)
            details_text.setReadOnly(True)
            layout.addWidget(details_text)

        # 智能恢复选项
        if self.recovery_system and self.error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            recovery_layout = self._create_recovery_options()
            layout.addLayout(recovery_layout)

        # 按钮区域
        button_layout = QHBoxLayout()

        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        # 如果有智能恢复系统，添加恢复按钮
        if self.recovery_system:
            recover_button = QPushButton("尝试自动恢复")
            recover_button.clicked.connect(self._attempt_recovery)
            button_layout.addWidget(recover_button)

        # 复制错误信息按钮
        copy_button = QPushButton("复制错误信息")
        copy_button.clicked.connect(self._copy_error_info)
        button_layout.addWidget(copy_button)

        layout.addLayout(button_layout)

    def _create_recovery_options(self) -> QVBoxLayout:
        """创建恢复选项"""
        layout = QVBoxLayout()

        recovery_label = QLabel("<b>智能恢复选项:</b>")
        layout.addWidget(recovery_label)

        info_label = QLabel("系统可以尝试自动恢复此错误。点击'尝试自动恢复'按钮开始。")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        return layout

    def _setup_connections(self):
        """设置信号连接"""
        pass

    def _attempt_recovery(self):
        """尝试自动恢复"""
        try:
            if not self.recovery_system or not self.error_context_class:
                QMessageBox.information(self, "信息", "智能恢复系统不可用")
                return

            # 创建错误上下文
            error_context = self.error_context_class(
                exception=Exception(self.error.message),
                operation=self.context or "unknown",
                component="error_handler"
            )

            # 显示恢复进度
            progress_dialog = QMessageBox(self)
            progress_dialog.setWindowTitle("自动恢复")
            progress_dialog.setText("正在尝试自动恢复，请稍候...")
            progress_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress_dialog.show()

            # 异步执行恢复
            import asyncio

            async def perform_recovery():
                try:
                    result = await self.recovery_system.recover_from_error(error_context)
                    return result
                except Exception as e:
                    logger.error(f"自动恢复失败: {e}")
                    return None

            # 在新线程中执行恢复
            import threading

            def recovery_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(perform_recovery())
                    loop.close()

                    # 在主线程中显示结果
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: self._show_recovery_result(result, progress_dialog))

                except Exception as e:
                    logger.error(f"恢复线程异常: {e}")
                    QTimer.singleShot(0, lambda: self._show_recovery_result(None, progress_dialog))

            thread = threading.Thread(target=recovery_thread, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"启动自动恢复失败: {e}")
            QMessageBox.critical(self, "错误", f"启动自动恢复失败: {e}")

    def _show_recovery_result(self, result, progress_dialog):
        """显示恢复结果"""
        try:
            progress_dialog.close()

            if result is None:
                QMessageBox.warning(self, "恢复失败", "自动恢复过程中发生错误")
                return

            # 导入恢复结果枚举
            try:
                from src.shared.stability.intelligent_recovery_system import RecoveryResult

                if result == RecoveryResult.SUCCESS:
                    QMessageBox.information(self, "恢复成功", "问题已成功自动恢复！")
                    self.accept()  # 关闭错误对话框
                elif result == RecoveryResult.PARTIAL_SUCCESS:
                    QMessageBox.information(self, "部分恢复", "问题已部分恢复，可能仍需要手动处理")
                elif result == RecoveryResult.USER_CANCELLED:
                    QMessageBox.information(self, "用户取消", "自动恢复已被用户取消")
                elif result == RecoveryResult.REQUIRES_RESTART:
                    reply = QMessageBox.question(
                        self, "需要重启",
                        "恢复需要重启应用程序，是否现在重启？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        # 这里需要实现应用程序重启逻辑
                        QMessageBox.information(self, "信息", "请手动重启应用程序")
                else:
                    QMessageBox.warning(self, "恢复失败", "自动恢复未能解决问题，请手动处理")

            except ImportError:
                QMessageBox.warning(self, "恢复失败", "无法确定恢复结果")

        except Exception as e:
            logger.error(f"显示恢复结果失败: {e}")
            QMessageBox.critical(self, "错误", f"显示恢复结果失败: {e}")

    def _copy_error_info(self):
        """复制错误信息到剪贴板"""
        try:
            from PyQt6.QtWidgets import QApplication

            error_info = f"""错误信息: {self.error.message}
发生位置: {self.context or '未知'}
发生时间: {self.error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
严重程度: {self.error.severity}

详细信息:
{self.error.details or '无'}"""

            clipboard = QApplication.clipboard()
            clipboard.setText(error_info)

            QMessageBox.information(self, "信息", "错误信息已复制到剪贴板")

        except Exception as e:
            logger.error(f"复制错误信息失败: {e}")
            QMessageBox.warning(self, "警告", f"复制失败: {e}")
        
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

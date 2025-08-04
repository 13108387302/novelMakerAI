#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线程安全工具

提供线程安全的工具函数和装饰器
"""

import threading
import functools
from typing import Callable, Any
from PyQt6.QtCore import QObject, QMetaObject, Qt, Q_ARG
from PyQt6.QtWidgets import QApplication

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_main_thread(func: Callable) -> Callable:
    """
    确保函数在主线程中执行的装饰器

    检查当前线程是否为Qt主线程，如果不是则尝试切换到主线程执行。
    主要用于UI操作必须在主线程中执行的场景。

    实现方式：
    - 检查当前线程是否为Qt应用程序的主线程
    - 如果不是主线程且第一个参数是QObject，使用QMetaObject.invokeMethod切换
    - 使用BlockingQueuedConnection确保同步执行
    - 正确传递异常和返回值

    Args:
        func: 要装饰的函数

    Returns:
        Callable: 装饰后的函数

    Raises:
        RuntimeError: 当不在主线程且无法切换时抛出
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        app = QApplication.instance()
        if app and app.thread() != threading.current_thread():
            logger.warning(f"函数 {func.__name__} 不在主线程中执行，尝试切换到主线程")

            # 如果有QObject实例，使用QMetaObject.invokeMethod
            if args and isinstance(args[0], QObject):
                result = None
                exception = None

                def invoke_in_main_thread():
                    nonlocal result, exception
                    try:
                        result = func(*args, **kwargs)
                    except Exception as e:
                        exception = e

                QMetaObject.invokeMethod(
                    args[0],
                    invoke_in_main_thread,
                    Qt.ConnectionType.BlockingQueuedConnection
                )

                if exception:
                    raise exception
                return result
            else:
                raise RuntimeError(f"函数 {func.__name__} 必须在主线程中执行")
        
        return func(*args, **kwargs)
    
    return wrapper


def is_main_thread() -> bool:
    """检查当前是否在主线程"""
    # 首先检查是否是Python主线程
    current_thread = threading.current_thread()
    if current_thread != threading.main_thread():
        return False

    # 如果有Qt应用，检查是否在Qt主线程中
    app = QApplication.instance()
    if app:
        # Qt的线程检查
        try:
            # 使用Qt的方式检查线程
            from PyQt6.QtCore import QThread
            return QThread.currentThread() == app.thread()
        except Exception:
            # 如果Qt检查失败，回退到基本检查
            return True

    return True


def get_main_thread_id() -> int:
    """获取主线程ID"""
    app = QApplication.instance()
    if app:
        return int(app.thread().currentThreadId())
    return threading.main_thread().ident


class ThreadSafeInitializer:
    """线程安全的初始化器"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._initialized = False
        self._main_thread_id = None
    
    def ensure_main_thread_init(self, init_func: Callable, *args, **kwargs) -> Any:
        """确保在主线程中初始化"""
        with self._lock:
            if self._initialized:
                return
            
            if not is_main_thread():
                raise RuntimeError("初始化必须在主线程中进行")
            
            self._main_thread_id = get_main_thread_id()
            result = init_func(*args, **kwargs)
            self._initialized = True
            return result
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def reset(self):
        """重置初始化状态"""
        with self._lock:
            self._initialized = False
            self._main_thread_id = None


class ThreadSafeQObject(QObject):
    """线程安全的QObject基类"""
    
    def __init__(self, parent=None):
        # 确保在主线程中创建
        if not is_main_thread():
            raise RuntimeError("QObject必须在主线程中创建")
        
        super().__init__(parent)
        self._creation_thread_id = get_main_thread_id()
    
    def ensure_same_thread(self):
        """确保在创建线程中操作"""
        current_thread_id = get_main_thread_id() if is_main_thread() else threading.current_thread().ident
        
        if current_thread_id != self._creation_thread_id:
            raise RuntimeError(
                f"QObject操作必须在创建线程中进行。"
                f"创建线程: {self._creation_thread_id}, 当前线程: {current_thread_id}"
            )


def safe_qt_call(func: Callable, *args, **kwargs) -> Any:
    """
    安全的Qt调用，确保在主线程中执行

    提供一个通用的方法来确保Qt相关的函数调用在主线程中执行。
    如果当前已在主线程则直接执行，否则切换到主线程执行。

    实现方式：
    - 检查当前是否在主线程
    - 如果不在主线程，使用QTimer切换到主线程
    - 使用Event对象等待执行完成
    - 正确传递返回值和异常
    - 提供超时保护机制

    Args:
        func: 要执行的函数
        *args: 函数的位置参数
        **kwargs: 函数的关键字参数

    Returns:
        Any: 函数的返回值

    Raises:
        RuntimeError: 当没有QApplication实例时抛出
        TimeoutError: 当执行超时时抛出
        Exception: 传递被调用函数抛出的异常
    """
    if is_main_thread():
        return func(*args, **kwargs)
    
    app = QApplication.instance()
    if not app:
        raise RuntimeError("没有QApplication实例")
    
    result = None
    exception = None
    finished = threading.Event()
    
    def execute():
        nonlocal result, exception
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            exception = e
        finally:
            finished.set()
    
    # 使用QTimer在主线程中执行
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(execute)
    timer.start(0)
    
    # 等待执行完成
    finished.wait(timeout=10.0)  # 10秒超时
    
    if not finished.is_set():
        raise TimeoutError("Qt调用超时")
    
    if exception:
        raise exception
    
    return result


class ThreadSafeService:
    """线程安全的服务基类"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._initialized = False
        self._main_thread_id = get_main_thread_id() if is_main_thread() else None
    
    def _ensure_initialized(self):
        """确保服务已初始化"""
        if not self._initialized:
            raise RuntimeError("服务未初始化")
    
    def _ensure_thread_safety(self):
        """确保线程安全"""
        if self._main_thread_id and not is_main_thread():
            current_thread_id = threading.current_thread().ident
            if current_thread_id != self._main_thread_id:
                logger.warning(f"服务在非主线程中访问: {current_thread_id}")
    
    def initialize(self) -> bool:
        """初始化服务"""
        with self._lock:
            if self._initialized:
                return True
            
            try:
                if not is_main_thread():
                    logger.warning("服务在非主线程中初始化")
                
                self._main_thread_id = get_main_thread_id() if is_main_thread() else threading.current_thread().ident
                self._do_initialize()
                self._initialized = True
                return True
                
            except Exception as e:
                logger.error(f"服务初始化失败: {e}")
                return False
    
    def _do_initialize(self):
        """子类重写此方法实现具体初始化逻辑"""
        pass
    
    def shutdown(self):
        """关闭服务"""
        with self._lock:
            if not self._initialized:
                return
            
            try:
                self._do_shutdown()
                self._initialized = False
                
            except Exception as e:
                logger.error(f"服务关闭失败: {e}")
    
    def _do_shutdown(self):
        """子类重写此方法实现具体关闭逻辑"""
        pass


def debug_thread_info():
    """调试线程信息"""
    current_thread = threading.current_thread()
    main_thread = threading.main_thread()
    
    app = QApplication.instance()
    app_thread = app.thread() if app else None
    
    logger.debug(f"当前线程: {current_thread.name} (ID: {current_thread.ident})")
    logger.debug(f"主线程: {main_thread.name} (ID: {main_thread.ident})")
    logger.debug(f"是否为主线程: {current_thread == main_thread}")
    
    if app_thread:
        logger.debug(f"Qt应用线程ID: {int(app_thread.currentThreadId())}")
        logger.debug(f"是否为Qt主线程: {is_main_thread()}")
    
    return {
        "current_thread_id": current_thread.ident,
        "main_thread_id": main_thread.ident,
        "is_main_thread": current_thread == main_thread,
        "qt_thread_id": int(app_thread.currentThreadId()) if app_thread else None,
        "is_qt_main_thread": is_main_thread()
    }

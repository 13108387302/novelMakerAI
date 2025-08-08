#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步操作管理器

提供统一的异步操作管理，包括：
- 统一的异步任务执行
- 线程安全的回调处理
- 任务生命周期管理
- 错误处理和重试机制
"""

import asyncio
import threading
import concurrent.futures
from typing import Callable, Any, Optional, Set, Dict, Coroutine
from functools import wraps
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.shared.utils.logger import get_logger
# 移除ensure_main_thread导入，使用Qt信号槽机制

logger = get_logger(__name__)


class AsyncTaskManager(QObject):
    """
    异步任务管理器
    
    统一管理应用程序中的异步操作，提供：
    - 任务执行和生命周期管理
    - 线程安全的回调处理
    - 错误处理和重试机制
    - 资源清理和任务取消
    """
    
    # 信号定义
    task_started = pyqtSignal(str)  # 任务开始信号
    task_completed = pyqtSignal(str, object)  # 任务完成信号
    task_failed = pyqtSignal(str, Exception)  # 任务失败信号
    callback_signal = pyqtSignal(object)  # 回调信号，用于线程安全的回调执行
    
    def __init__(self, max_workers: int = 4):
        """
        初始化异步任务管理器
        
        Args:
            max_workers: 最大工作线程数
        """
        super().__init__()
        self.max_workers = max_workers
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="AsyncTask"
        )
        self._active_tasks: Set[str] = set()
        self._task_futures: Dict[str, concurrent.futures.Future] = {}
        self._lock = threading.RLock()

        # 连接回调信号
        self.callback_signal.connect(self._execute_callback)

        logger.info(f"异步任务管理器初始化完成，最大工作线程数: {max_workers}")

    def _execute_callback(self, callback_func):
        """
        在主线程中执行回调函数

        Args:
            callback_func: 要执行的回调函数
        """
        try:
            callback_func()
        except Exception as e:
            logger.error(f"回调函数执行失败: {e}")

    def execute_async(
        self,
        coro: Coroutine,
        task_id: Optional[str] = None,
        success_callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        执行异步协程
        
        Args:
            coro: 要执行的协程
            task_id: 任务ID，如果不提供则自动生成
            success_callback: 成功回调函数
            error_callback: 错误回调函数
            timeout: 超时时间（秒）
        
        Returns:
            str: 任务ID
        """
        if task_id is None:
            import uuid
            task_id = str(uuid.uuid4())[:8]
        
        with self._lock:
            if task_id in self._active_tasks:
                logger.warning(f"任务已存在: {task_id}")
                return task_id
            
            self._active_tasks.add(task_id)
        
        def run_in_thread():
            """在线程中运行异步协程"""
            try:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # 发送任务开始信号
                    self.task_started.emit(task_id)
                    
                    # 执行协程（带超时）
                    if timeout:
                        result = loop.run_until_complete(
                            asyncio.wait_for(coro, timeout=timeout)
                        )
                    else:
                        result = loop.run_until_complete(coro)
                    
                    # 在主线程中执行成功回调
                    if success_callback:
                        # 使用Qt信号槽机制安全切换到主线程
                        self.callback_signal.emit(lambda: success_callback(result))
                    
                    # 发送任务完成信号
                    self.task_completed.emit(task_id, result)
                    
                    return result
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"异步任务执行失败: {task_id}, {e}")
                
                # 在主线程中执行错误回调
                if error_callback:
                    # 使用Qt信号槽机制安全切换到主线程
                    self.callback_signal.emit(lambda: error_callback(e))
                
                # 发送任务失败信号
                self.task_failed.emit(task_id, e)
                
                raise
                
            finally:
                # 清理任务
                with self._lock:
                    self._active_tasks.discard(task_id)
                    self._task_futures.pop(task_id, None)
        
        # 提交任务到线程池
        future = self._thread_pool.submit(run_in_thread)
        self._task_futures[task_id] = future
        
        logger.debug(f"异步任务已提交: {task_id}")
        return task_id
    
    def execute_delayed(
        self,
        func: Callable,
        delay_ms: int = 0,
        *args,
        **kwargs
    ) -> None:
        """
        延迟执行函数（在主线程中）
        
        Args:
            func: 要执行的函数
            delay_ms: 延迟时间（毫秒）
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        def wrapper():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"延迟执行函数失败: {func.__name__}, {e}")
        
        QTimer.singleShot(delay_ms, wrapper)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否成功取消
        """
        with self._lock:
            if task_id not in self._active_tasks:
                return False
            
            future = self._task_futures.get(task_id)
            if future and not future.done():
                cancelled = future.cancel()
                if cancelled:
                    self._active_tasks.discard(task_id)
                    self._task_futures.pop(task_id, None)
                    logger.info(f"任务已取消: {task_id}")
                return cancelled
            
            return False
    
    def cancel_all_tasks(self) -> int:
        """
        取消所有活跃任务
        
        Returns:
            int: 取消的任务数量
        """
        cancelled_count = 0
        
        with self._lock:
            task_ids = list(self._active_tasks)
        
        for task_id in task_ids:
            if self.cancel_task(task_id):
                cancelled_count += 1
        
        logger.info(f"已取消 {cancelled_count} 个任务")
        return cancelled_count
    
    def get_active_task_count(self) -> int:
        """
        获取活跃任务数量
        
        Returns:
            int: 活跃任务数量
        """
        with self._lock:
            return len(self._active_tasks)
    
    def get_active_task_ids(self) -> Set[str]:
        """
        获取活跃任务ID列表
        
        Returns:
            Set[str]: 活跃任务ID集合
        """
        with self._lock:
            return self._active_tasks.copy()
    
    def cleanup(self) -> None:
        """
        清理资源
        """
        try:
            # 取消所有任务
            self.cancel_all_tasks()
            
            # 关闭线程池
            self._thread_pool.shutdown(wait=False)
            
            logger.info("异步任务管理器已清理")
            
        except Exception as e:
            logger.error(f"清理异步任务管理器失败: {e}")


# 全局异步任务管理器实例
_global_async_manager: Optional[AsyncTaskManager] = None


def get_async_manager() -> AsyncTaskManager:
    """
    获取全局异步任务管理器
    
    Returns:
        AsyncTaskManager: 全局异步任务管理器实例
    """
    global _global_async_manager
    if _global_async_manager is None:
        _global_async_manager = AsyncTaskManager()
    return _global_async_manager


def set_async_manager(manager: AsyncTaskManager) -> None:
    """
    设置全局异步任务管理器
    
    Args:
        manager: 异步任务管理器实例
    """
    global _global_async_manager
    _global_async_manager = manager


def async_task(
    task_id: Optional[str] = None,
    timeout: Optional[float] = None,
    show_errors: bool = True
):
    """
    异步任务装饰器
    
    将普通的异步函数转换为使用统一异步管理器的任务。
    
    Args:
        task_id: 任务ID
        timeout: 超时时间
        show_errors: 是否显示错误
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, success_callback=None, error_callback=None, **kwargs):
            # 创建协程
            coro = func(self, *args, **kwargs)
            
            # 获取异步管理器
            manager = get_async_manager()
            
            # 包装错误回调
            def wrapped_error_callback(e):
                if show_errors and hasattr(self, '_show_error'):
                    op_name = func.__name__.replace('_', ' ').title()
                    self._show_error(f"{op_name}失败", str(e))
                
                if error_callback:
                    error_callback(e)
            
            # 执行异步任务
            return manager.execute_async(
                coro=coro,
                task_id=task_id,
                success_callback=success_callback,
                error_callback=wrapped_error_callback,
                timeout=timeout
            )
        
        return wrapper
    return decorator

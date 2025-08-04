#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具包

提供各种通用的工具函数和类，包括文本处理、文件操作、日志记录、
错误处理、线程安全、性能监控和数据验证等功能。

主要模块：
- text_utils: 文本处理和分析工具
- file_utils: 文件和目录操作工具
- logger: 日志记录工具
- error_handler: 错误处理工具
- thread_safety: 线程安全工具
- validators: 数据验证工具
- performance_monitor: 性能监控工具
"""

# 导入常用的工具函数和类
try:
    # 日志工具
    from .logger import get_logger, setup_logging

    # 文本处理工具
    from .text_utils import (
        TextProcessor, TextStatistics,
        analyze_text, clean_text, format_text
    )

    # 文件操作工具
    from .file_utils import (
        FileManager, FileInfo,
        ensure_directory, safe_copy, safe_delete
    )

    # 错误处理工具
    from .error_handler import (
        ErrorHandler, ApplicationError, ValidationError,
        handle_async_errors, safe_execute, safe_execute_async
    )

    # 线程安全工具
    from .thread_safety import (
        ensure_main_thread, ThreadSafeInitializer,
        safe_qt_call, is_main_thread
    )

    # 缓存管理工具
    from .cache_manager import (
        CacheManager, get_cache_manager, set_cache_manager
    )

    # 数据验证工具（如果需要可以从其他模块导入）
    # from .validators import ...  # 已删除，使用内联验证

    # 性能监控工具（如果需要可以从其他模块导入）
    # from .performance_monitor import ...  # 已删除，使用status_service

    __all__ = [
        # 日志工具
        "get_logger",
        "setup_logging",

        # 文本处理
        "TextProcessor",
        "TextStatistics",
        "analyze_text",
        "clean_text",
        "format_text",

        # 文件操作
        "FileManager",
        "FileInfo",
        "ensure_directory",
        "safe_copy",
        "safe_delete",

        # 错误处理
        "ErrorHandler",
        "ApplicationError",
        "ValidationError",
        "handle_async_errors",
        "safe_execute",
        "safe_execute_async",

        # 线程安全
        "ensure_main_thread",
        "ThreadSafeInitializer",
        "safe_qt_call",
        "is_main_thread",

        # 缓存管理
        "CacheManager",
        "get_cache_manager",
        "set_cache_manager"
    ]

except ImportError as e:
    # 如果某些模块导入失败，记录错误但不中断
    try:
        from .logger import get_logger
        logger = get_logger(__name__)
        logger.warning(f"工具包导入部分失败: {e}")
    except ImportError:
        # 如果连日志模块都导入失败，使用标准库
        import logging
        logging.warning(f"工具包导入部分失败: {e}")
    __all__ = []

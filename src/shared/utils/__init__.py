#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具包 - 重构版本

提供统一的工具函数和类，采用新的架构设计确保一致性和可维护性。

主要模块：
- base_utils: 工具类基础架构和统一接口
- unified_performance: 统一性能监控和缓存管理
- unified_error_handler: 统一错误处理机制
- text_utils: 文本处理和分析工具
- file_utils: 文件和目录操作工具
- logger: 日志记录工具
- thread_safety: 线程安全工具

重构改进：
- 统一的工具类接口设计
- 整合的性能监控和缓存管理
- 简化的错误处理机制
- 更好的模块化和可扩展性
"""

# 导入新的统一工具类和向后兼容的接口
try:
    # 新的统一工具类基础架构
    from .base_utils import (
        BaseUtility, UtilResult, OperationResult,
        UtilityRegistry, get_utility_registry, register_utility, get_utility,
        timed_operation, utility_method
    )

    # 统一性能监控和缓存管理
    from .unified_performance import (
        UnifiedPerformanceManager, get_performance_manager, set_performance_manager,
        performance_monitor
    )

    # 统一错误处理
    from .unified_error_handler import (
        UnifiedErrorHandler, ErrorSeverity, ErrorCategory, ErrorInfo,
        get_error_handler, set_error_handler,
        handle_errors, handle_async_errors, safe_execute
    )

    # 统一网络管理
    from .unified_network_manager import (
        UnifiedNetworkManager, NetworkQuality, NetworkMetrics,
        get_network_manager, set_network_manager,
        check_network_connectivity, get_optimal_timeout, retry_with_backoff
    )

    # 保留的原有工具类（向后兼容）
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

    # 线程安全工具
    from .thread_safety import (
        ensure_main_thread, ThreadSafeInitializer,
        safe_qt_call, is_main_thread
    )

    # 向后兼容的缓存管理（使用统一性能管理器）
    def get_cache_manager():
        """向后兼容：获取缓存管理器"""
        return get_performance_manager()

    def set_cache_manager(manager):
        """向后兼容：设置缓存管理器"""
        if isinstance(manager, UnifiedPerformanceManager):
            set_performance_manager(manager)

    __all__ = [
        # 新的统一工具类
        "BaseUtility",
        "UtilResult",
        "OperationResult",
        "UtilityRegistry",
        "get_utility_registry",
        "register_utility",
        "get_utility",
        "timed_operation",
        "utility_method",

        # 统一性能监控
        "UnifiedPerformanceManager",
        "get_performance_manager",
        "set_performance_manager",
        "performance_monitor",

        # 统一错误处理
        "UnifiedErrorHandler",
        "ErrorSeverity",
        "ErrorCategory",
        "ErrorInfo",
        "get_error_handler",
        "set_error_handler",
        "handle_errors",
        "handle_async_errors",
        "safe_execute",

        # 统一网络管理
        "UnifiedNetworkManager",
        "NetworkQuality",
        "NetworkMetrics",
        "get_network_manager",
        "set_network_manager",
        "check_network_connectivity",
        "get_optimal_timeout",
        "retry_with_backoff",

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

        # 线程安全
        "ensure_main_thread",
        "ThreadSafeInitializer",
        "safe_qt_call",
        "is_main_thread",

        # 向后兼容的缓存管理
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

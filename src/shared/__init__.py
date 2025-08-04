#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享组件包

共享组件提供跨层使用的通用功能，包括工具类、事件系统、依赖注入和插件系统。
这些组件被应用程序的各个层次使用。

主要组件：
- constants: 常量定义
- events: 事件系统，提供发布订阅机制
- ioc: 依赖注入容器
- plugins: 插件系统
- utils: 工具类集合

设计原则：
- 提供通用的基础功能
- 保持组件间的低耦合
- 支持扩展和定制
- 确保线程安全

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器共享组件"

# 导出主要组件
try:
    from .events.event_bus import EventBus
    from .ioc.container import Container
    from .utils.logger import get_logger

    __all__ = [
        "EventBus",
        "Container",
        "get_logger",
        "__version__",
        "__description__"
    ]
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ["__version__", "__description__"]

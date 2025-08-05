#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用层包

应用层是业务逻辑的协调者，负责编排领域对象完成具体的业务用例。
遵循六边形架构原则，通过端口和适配器模式与外部系统交互。

主要组件：
- services: 应用服务，实现具体的业务用例
- ai: AI相关服务，处理人工智能功能
- import_export: 导入导出服务，处理数据交换
- search: 搜索服务，提供全文搜索功能

设计原则：
- 不包含业务规则，只负责协调
- 通过依赖注入获取领域服务
- 处理事务边界和异常转换
- 提供清晰的API接口

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器应用层"

# 导出主要服务类
try:
    from .services.application_service import ApplicationService
    from .services.project_service import ProjectService
    from .services.document_service import DocumentService
    from .services.ai_service import AIService
    from .services.settings_service import SettingsService

    __all__ = [
        "ApplicationService",
        "ProjectService",
        "DocumentService",
        "AIService",
        "SettingsService",
        "__version__",
        "__description__"
    ]
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ["__version__", "__description__"]

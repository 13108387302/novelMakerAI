#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用服务包

包含AI小说编辑器的所有应用服务类。
应用服务负责协调领域对象，实现具体的业务用例。

主要服务：
- ApplicationService: 应用程序生命周期管理
- ProjectService: 项目管理服务
- DocumentService: 文档管理服务
- AIService: AI功能服务
- SettingsService: 设置管理服务
- SearchService: 搜索服务
- ImportExportService: 导入导出服务
- BackupService: 备份服务

设计模式：
- 服务层模式：封装业务逻辑
- 依赖注入：通过构造函数注入依赖
- 事件驱动：通过事件总线解耦
- 事务管理：确保数据一致性

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器应用服务包"

# 导出所有服务类
try:
    from .application_service import ApplicationService
    from .project_service import ProjectService
    from .document_service import DocumentService
    from .ai_service import AIService
    from .settings_service import SettingsService
    from .search_service import SearchService
    from .import_export_service import ImportExportService
    from .backup_service import BackupService
    from .analytics_service import AnalyticsService
    from .template_service import TemplateService
    from .ux_service import UXService
    from .ai_assistant_manager import AIAssistantManager
    from .specialized_ai_assistants import SpecializedAIAssistants

    __all__ = [
        "ApplicationService",
        "ProjectService",
        "DocumentService",
        "AIService",
        "SettingsService",
        "SearchService",
        "ImportExportService",
        "BackupService",
        "AnalyticsService",
        "TemplateService",
        "UXService",
        "AIAssistantManager",
        "SpecializedAIAssistants",
        "__version__",
        "__description__"
    ]
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ["__version__", "__description__"]

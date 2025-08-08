#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础设施层包

基础设施层提供技术实现，包括外部系统集成、数据持久化和第三方服务调用。
遵循六边形架构原则，实现领域层定义的接口。

主要组件：
- ai_clients: AI服务客户端，集成各种AI服务提供商
- repositories: 仓储实现，提供数据持久化功能
- external_services: 外部服务集成

设计原则：
- 实现领域层定义的接口
- 隔离外部依赖和技术细节
- 提供可替换的技术实现
- 确保数据一致性和事务管理

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器基础设施层"

# 导出主要组件
try:
    # 新的统一AI客户端管理器
    from .ai.unified_ai_client_manager import UnifiedAIClientManager, get_unified_ai_client_manager

    # AI客户端组件
    from .ai.clients.ai_client_factory import AIClientFactory
    from .ai.clients.base_ai_client import BaseAIClient

    # 文件仓储组件
    from .repositories.file_project_repository import FileProjectRepository
    from .repositories.file_document_repository import FileDocumentRepository

    __all__ = [
        # 统一AI客户端管理
        "UnifiedAIClientManager",
        "get_unified_ai_client_manager",

        # AI客户端组件
        "AIClientFactory",
        "BaseAIClient",

        # 文件仓储
        "FileProjectRepository",
        "FileDocumentRepository",

        # 版本信息
        "__version__",
        "__description__"
    ]
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ["__version__", "__description__"]

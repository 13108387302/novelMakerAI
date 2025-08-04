#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
领域层包

领域层是应用程序的核心，包含了业务逻辑的核心概念和规则。
遵循领域驱动设计(DDD)原则，确保业务逻辑的纯净性和可测试性。

主要组件：
- entities: 领域实体，包含业务数据和行为
- events: 领域事件，用于解耦和通信
- repositories: 仓库接口，定义数据访问契约

设计原则：
- 不依赖外部框架和基础设施
- 包含核心业务规则和逻辑
- 通过接口定义与外部的交互
- 使用事件进行松耦合通信

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器领域层"

# 导出主要领域概念
try:
    from .entities.document import Document
    from .entities.character import Character
    from .entities.project.project import Project

    __all__ = [
        "Document",
        "Character",
        "Project",
        "__version__",
        "__description__"
    ]
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ["__version__", "__description__"]

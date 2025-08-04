#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
领域实体包

包含AI小说编辑器的所有领域实体类。
实体是具有唯一标识的业务对象，包含数据和行为。

主要实体：
- Document: 文档实体，表示小说的各种文档类型
- Character: 角色实体，表示小说中的人物
- Project: 项目实体，表示小说项目的整体信息

设计原则：
- 每个实体都有唯一标识(ID)
- 封装业务规则和验证逻辑
- 保持数据的一致性和完整性
- 提供清晰的业务接口

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器领域实体包"

# 导出主要实体类
try:
    from .document import Document
    from .character import Character
    from .project.project import Project

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

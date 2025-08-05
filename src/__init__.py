#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说编辑器源代码包

这是AI小说编辑器的主要源代码包，包含了应用程序的所有核心功能模块。
采用分层架构设计，确保代码的可维护性和可扩展性。

架构层次：
- application: 应用层，包含业务逻辑和服务
- domain: 领域层，包含实体、事件和仓库接口
- infrastructure: 基础设施层，包含具体实现
- presentation: 表示层，包含用户界面和控制器
- shared: 共享层，包含通用工具和组件

版本: 2.0.0
作者: AI小说编辑器团队
"""

__version__ = "2.0.0"
__author__ = "AI小说编辑器团队"
__description__ = "AI小说编辑器源代码包"

# 导出版本信息
__all__ = [
    "__version__",
    "__author__",
    "__description__"
]

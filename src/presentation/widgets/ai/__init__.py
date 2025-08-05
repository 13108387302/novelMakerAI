#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI用户界面组件模块 - 重构版本

提供AI相关的用户界面组件
重构后使用新的DDD架构，保持100%智能化功能
"""

import warnings

# 发出迁移提示
warnings.warn(
    "AI UI组件已重构，建议使用新的重构版本组件。"
    "详见: src.presentation.widgets.ai.refactored",
    FutureWarning,
    stacklevel=2
)

# 兼容性标志
NEW_COMPONENTS_AVAILABLE = True

# 导入重构后的组件
try:
    from .refactored import (
        initialize_ai_component_factory,
        create_intelligent_ai_panel,
        create_document_ai_panel as _create_document_ai_panel,
        create_global_ai_panel as _create_global_ai_panel,
        get_ai_widget_factory,
        shutdown_ai_components
    )
    
    # 向后兼容的别名
    def initialize_ai_component_factory_legacy(*args, **kwargs):
        """向后兼容的AI组件工厂初始化函数"""
        warnings.warn(
            "使用旧版本初始化函数，请迁移到新版本",
            DeprecationWarning,
            stacklevel=2
        )
        return initialize_ai_component_factory(*args, **kwargs)

    # 兼容性函数
    def create_document_ai_panel(ai_service, document_id, document_type, parent=None):
        """创建文档AI面板（兼容性函数）"""
        warnings.warn(
            "create_document_ai_panel已弃用，请使用重构版本",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _create_document_ai_panel(ai_service, document_id, document_type, parent)
        except Exception as e:
            print(f"创建文档AI面板失败: {e}")
            return None

    def create_global_ai_panel(ai_service, parent=None):
        """创建全局AI面板（兼容性函数）"""
        warnings.warn(
            "create_global_ai_panel已弃用，请使用重构版本",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            return _create_global_ai_panel(ai_service, parent)
        except Exception as e:
            print(f"创建全局AI面板失败: {e}")
            return None
    
    __all__ = [
        # 新版本函数
        'initialize_ai_component_factory',
        'create_intelligent_ai_panel',
        'create_document_ai_panel',
        'create_global_ai_panel',
        'get_ai_widget_factory',
        'shutdown_ai_components',

        # 向后兼容
        'initialize_ai_component_factory_legacy',

        # 兼容性标志和函数
        'NEW_COMPONENTS_AVAILABLE'
    ]
    
except ImportError as e:
    # 如果重构版本不可用，提供占位符
    warnings.warn(f"重构版本AI组件不可用: {e}", RuntimeWarning)
    
    def initialize_ai_component_factory(*args, **kwargs):
        raise RuntimeError("AI组件重构版本不可用，请检查安装")
    
    __all__ = ['initialize_ai_component_factory']

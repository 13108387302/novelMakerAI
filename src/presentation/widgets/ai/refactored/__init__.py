#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的AI用户界面组件

提供重构后的AI用户界面组件，保持100%智能化功能
遵循DDD架构原则，与新的应用服务层完全兼容
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 基础组件
from .components.base_ai_widget import BaseAIWidget
from .components.ai_input_component import AIInputComponent
from .components.ai_output_component import AIOutputComponent
from .components.ai_status_component import AIStatusComponent

# 面板组件（仅保留智能面板；全局/文档面板已被 AI Studio 取代）
from .panels.intelligent_ai_panel import IntelligentAIPanel

# 工厂和管理器
from .factories.ai_widget_factory import AIWidgetFactory
from .managers.ai_ui_manager import AIUIManager

# 智能化组件
from .intelligence.smart_button_component import SmartButtonComponent
from .intelligence.auto_execution_handler import AutoExecutionHandler
from .intelligence.context_analyzer import ContextAnalyzer

# 全局AI组件工厂实例
_ai_widget_factory: Optional[AIWidgetFactory] = None
_ai_ui_manager: Optional[AIUIManager] = None


def initialize_ai_component_factory(
    ai_orchestration_service,
    ai_intelligence_service,
    event_bus,
    settings_service=None
) -> bool:
    """
    初始化AI组件工厂

    Args:
        ai_orchestration_service: AI编排服务
        ai_intelligence_service: AI智能化服务
        event_bus: 事件总线
        settings_service: 设置服务

    Returns:
        bool: 初始化是否成功
    """
    global _ai_widget_factory, _ai_ui_manager

    try:
        # 创建AI组件工厂
        _ai_widget_factory = AIWidgetFactory(
            ai_orchestration_service=ai_orchestration_service,
            ai_intelligence_service=ai_intelligence_service,
            event_bus=event_bus,
            settings_service=settings_service
        )

        # 创建AI UI管理器
        _ai_ui_manager = AIUIManager(
            ai_widget_factory=_ai_widget_factory,
            event_bus=event_bus
        )

        # 初始化组件
        if not _ai_widget_factory.initialize():
            logger.error("AI组件工厂初始化失败")
            return False

        if not _ai_ui_manager.initialize():
            logger.error("AI UI管理器初始化失败")
            return False

        logger.info("✅ 重构后的AI组件工厂初始化成功")
        return True

    except Exception as e:
        logger.error(f"AI组件工厂初始化失败: {e}")
        return False


def get_ai_widget_factory() -> Optional[AIWidgetFactory]:
    """获取AI组件工厂"""
    return _ai_widget_factory


def get_ai_ui_manager() -> Optional[AIUIManager]:
    """获取AI UI管理器"""
    return _ai_ui_manager


def create_intelligent_ai_panel(parent=None) -> Optional[IntelligentAIPanel]:
    """创建智能化AI面板"""
    if not _ai_widget_factory:
        logger.error("AI组件工厂未初始化")
        return None
    return _ai_widget_factory.create_intelligent_panel(parent)






def shutdown_ai_components():
    """关闭AI组件"""
    global _ai_widget_factory, _ai_ui_manager

    try:
        if _ai_ui_manager:
            _ai_ui_manager.shutdown()
            _ai_ui_manager = None

        if _ai_widget_factory:
            _ai_widget_factory.shutdown()
            _ai_widget_factory = None

        logger.info("AI组件已关闭")

    except Exception as e:
        logger.error(f"关闭AI组件失败: {e}")


__all__ = [
    # 基础组件
    'BaseAIWidget',
    'AIInputComponent',
    'AIOutputComponent',
    'AIStatusComponent',

    # 面板组件
    'IntelligentAIPanel',

    # 工厂和管理器
    'AIWidgetFactory',
    'AIUIManager',

    # 智能化组件
    'SmartButtonComponent',
    'AutoExecutionHandler',
    'ContextAnalyzer',

    # 初始化和工厂函数
    'initialize_ai_component_factory',
    'get_ai_widget_factory',
    'get_ai_ui_manager',
    'create_intelligent_ai_panel',
    'shutdown_ai_components'
]

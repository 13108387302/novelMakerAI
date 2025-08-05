#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI组件工厂模块

提供AI组件的创建和管理功能
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

# 导入工厂类
from .ai_widget_factory import AIWidgetFactory
from .ai_component_factory import AIComponentFactory

# 全局工厂实例
_widget_factory: Optional[AIWidgetFactory] = None
_component_factory: Optional[AIComponentFactory] = None

def initialize_ai_component_factory(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化AI组件工厂
    
    Args:
        config: 配置参数
        
    Returns:
        bool: 初始化是否成功
    """
    global _widget_factory, _component_factory
    
    try:
        # 初始化组件工厂
        _component_factory = AIComponentFactory(config or {})
        logger.info("AI组件工厂初始化成功")
        
        # 初始化组件工厂
        _widget_factory = AIWidgetFactory(_component_factory)
        logger.info("AI组件工厂初始化成功")
        
        return True
        
    except Exception as e:
        logger.error(f"AI组件工厂初始化失败: {e}")
        return False

def get_ai_widget_factory() -> Optional[AIWidgetFactory]:
    """获取AI组件工厂"""
    return _widget_factory

def get_ai_component_factory() -> Optional[AIComponentFactory]:
    """获取AI组件工厂"""
    return _component_factory

def shutdown_ai_components():
    """关闭AI组件"""
    global _widget_factory, _component_factory
    
    try:
        if _widget_factory:
            _widget_factory.shutdown()
            _widget_factory = None
            
        if _component_factory:
            _component_factory.shutdown()
            _component_factory = None
            
        logger.info("AI组件已关闭")
        
    except Exception as e:
        logger.error(f"关闭AI组件失败: {e}")

# 导出的函数
__all__ = [
    'initialize_ai_component_factory',
    'get_ai_widget_factory', 
    'get_ai_component_factory',
    'shutdown_ai_components',
    'AIWidgetFactory',
    'AIComponentFactory'
]

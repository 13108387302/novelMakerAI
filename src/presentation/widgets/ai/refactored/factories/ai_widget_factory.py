#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI组件工厂

负责创建和管理AI面板和组件
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class AIWidgetFactory:
    """
    AI组件工厂

    负责创建和管理AI面板和组件
    """

    def __init__(self, ai_orchestration_service=None, ai_intelligence_service=None, event_bus=None, settings_service=None):
        """
        初始化AI组件工厂

        Args:
            ai_orchestration_service: AI编排服务
            ai_intelligence_service: AI智能化服务
            event_bus: 事件总线
            settings_service: 设置服务
        """
        self.ai_orchestration_service = ai_orchestration_service
        self.ai_intelligence_service = ai_intelligence_service
        self.event_bus = event_bus
        self.settings_service = settings_service
        self._panels = {}
        self._initialized = False

        try:
            self._initialize()
            self._initialized = True
            logger.info("AI组件工厂初始化成功")
        except Exception as e:
            logger.error(f"AI组件工厂初始化失败: {e}")
            
    def _initialize(self):
        """初始化工厂"""
        # 注册面板类型
        self._register_panel_types()
        
    def _register_panel_types(self):
        """注册面板类型"""
        try:
            # 导入面板类
            from ..panels.intelligent_ai_panel import IntelligentAIPanel
            from ..panels.document_ai_panel import DocumentAIPanel
            from ..panels.global_ai_panel import GlobalAIPanel
            
            # 注册面板
            self._panels['intelligent'] = IntelligentAIPanel
            self._panels['document'] = DocumentAIPanel
            self._panels['global'] = GlobalAIPanel
            
            logger.debug("AI面板类型注册完成")
            
        except Exception as e:
            logger.error(f"注册AI面板类型失败: {e}")
            
    def create_intelligent_ai_panel(self, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        创建智能化AI面板

        Args:
            parent: 父组件

        Returns:
            QWidget: 创建的面板，失败返回None
        """
        return self.create_panel('intelligent', parent)

    def create_intelligent_panel(self, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        创建智能化AI面板（别名方法）

        Args:
            parent: 父组件

        Returns:
            QWidget: 创建的面板，失败返回None
        """
        return self.create_intelligent_ai_panel(parent)

    def create_document_panel(self, ai_service, document_id: str, document_type: str = "chapter", parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        创建文档AI面板（别名方法）

        Args:
            ai_service: AI服务
            document_id: 文档ID
            document_type: 文档类型
            parent: 父组件

        Returns:
            QWidget: 创建的面板，失败返回None
        """
        return self.create_document_ai_panel(ai_service, document_id, document_type, parent)

    def create_global_panel(self, ai_service, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        创建全局AI面板（别名方法）

        Args:
            ai_service: AI服务
            parent: 父组件

        Returns:
            QWidget: 创建的面板，失败返回None
        """
        return self.create_global_ai_panel(ai_service, parent)
        
    def create_document_ai_panel(self, ai_service, document_id: str, document_type: str = "chapter", parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        创建文档AI面板
        
        Args:
            ai_service: AI服务
            document_id: 文档ID
            document_type: 文档类型
            parent: 父组件
            
        Returns:
            QWidget: 创建的面板，失败返回None
        """
        panel = self.create_panel('document', parent)
        if panel and hasattr(panel, 'set_document_info'):
            panel.set_document_info(document_id, document_type)
        return panel
        
    def create_global_ai_panel(self, ai_service, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        """
        创建全局AI面板
        
        Args:
            ai_service: AI服务
            parent: 父组件
            
        Returns:
            QWidget: 创建的面板，失败返回None
        """
        return self.create_panel('global', parent)
        
    def create_panel(self, panel_type: str, parent: Optional[QWidget] = None, **kwargs) -> Optional[QWidget]:
        """
        创建AI面板
        
        Args:
            panel_type: 面板类型
            parent: 父组件
            **kwargs: 其他参数
            
        Returns:
            QWidget: 创建的面板，失败返回None
        """
        if not self._initialized:
            logger.error("AI组件工厂未初始化")
            return None
            
        if panel_type not in self._panels:
            logger.error(f"未知的面板类型: {panel_type}")
            return None
            
        try:
            panel_class = self._panels[panel_type]

            # 尝试传递设置服务到构造函数
            try:
                panel = panel_class(parent, settings_service=self.settings_service)
            except TypeError:
                # 如果构造函数不支持settings_service参数，使用默认方式
                panel = panel_class(parent)

            # 设置AI服务
            if hasattr(panel, 'set_ai_services'):
                panel.set_ai_services(self.ai_orchestration_service, self.ai_intelligence_service)

            # 设置设置服务（如果面板支持）
            if hasattr(panel, 'settings_service') and self.settings_service:
                panel.settings_service = self.settings_service

            logger.debug(f"AI面板创建成功: {panel_type}")
            return panel

        except Exception as e:
            logger.error(f"创建AI面板失败: {panel_type}, {e}")
            return None
            
    def get_available_panels(self) -> list:
        """获取可用的面板类型"""
        return list(self._panels.keys())
        
    def initialize(self) -> bool:
        """初始化工厂"""
        try:
            if not self._initialized:
                self._initialize()
                self._initialized = True
            return True
        except Exception as e:
            logger.error(f"初始化AI组件工厂失败: {e}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def shutdown(self):
        """关闭工厂"""
        try:
            self._panels.clear()
            self._initialized = False
            logger.info("AI组件工厂已关闭")
        except Exception as e:
            logger.error(f"关闭AI组件工厂失败: {e}")

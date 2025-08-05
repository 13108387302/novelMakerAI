#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI UI管理器

负责管理AI用户界面组件的生命周期和交互
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class AIUIManager:
    """
    AI UI管理器
    
    负责管理AI用户界面组件的生命周期和交互
    """
    
    def __init__(self, ai_widget_factory, event_bus=None):
        """
        初始化AI UI管理器
        
        Args:
            ai_widget_factory: AI组件工厂
            event_bus: 事件总线
        """
        self.ai_widget_factory = ai_widget_factory
        self.event_bus = event_bus
        self._active_panels: Dict[str, QWidget] = {}
        self._initialized = False
        
    def initialize(self) -> bool:
        """
        初始化管理器
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 设置事件监听
            if self.event_bus:
                self._setup_event_listeners()
                
            self._initialized = True
            logger.info("AI UI管理器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"AI UI管理器初始化失败: {e}")
            return False
            
    def _setup_event_listeners(self):
        """设置事件监听"""
        try:
            # 这里可以添加事件监听逻辑
            logger.debug("AI UI管理器事件监听设置完成")
        except Exception as e:
            logger.error(f"设置事件监听失败: {e}")
            
    def register_panel(self, panel_id: str, panel: QWidget):
        """
        注册面板
        
        Args:
            panel_id: 面板ID
            panel: 面板组件
        """
        self._active_panels[panel_id] = panel
        logger.debug(f"面板已注册: {panel_id}")
        
    def unregister_panel(self, panel_id: str):
        """
        注销面板
        
        Args:
            panel_id: 面板ID
        """
        if panel_id in self._active_panels:
            del self._active_panels[panel_id]
            logger.debug(f"面板已注销: {panel_id}")
            
    def get_panel(self, panel_id: str) -> Optional[QWidget]:
        """
        获取面板
        
        Args:
            panel_id: 面板ID
            
        Returns:
            QWidget: 面板组件，不存在返回None
        """
        return self._active_panels.get(panel_id)
        
    def get_active_panels(self) -> List[str]:
        """获取活跃面板列表"""
        return list(self._active_panels.keys())
        
    def close_panel(self, panel_id: str):
        """
        关闭面板
        
        Args:
            panel_id: 面板ID
        """
        if panel_id in self._active_panels:
            panel = self._active_panels[panel_id]
            try:
                if hasattr(panel, 'close'):
                    panel.close()
                self.unregister_panel(panel_id)
                logger.info(f"面板已关闭: {panel_id}")
            except Exception as e:
                logger.error(f"关闭面板失败: {panel_id}, {e}")
                
    def close_all_panels(self):
        """关闭所有面板"""
        panel_ids = list(self._active_panels.keys())
        for panel_id in panel_ids:
            self.close_panel(panel_id)
            
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
        
    def shutdown(self):
        """关闭管理器"""
        try:
            # 关闭所有面板
            self.close_all_panels()
            
            # 清理资源
            self._active_panels.clear()
            self._initialized = False
            
            logger.info("AI UI管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭AI UI管理器失败: {e}")
            
    def get_panel_count(self) -> int:
        """获取面板数量"""
        return len(self._active_panels)
        
    def has_panel(self, panel_id: str) -> bool:
        """检查是否存在指定面板"""
        return panel_id in self._active_panels

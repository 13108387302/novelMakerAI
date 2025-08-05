#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI组件工厂

负责创建和管理AI相关组件
"""

import logging
from typing import Optional, Dict, Any, Type
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class AIComponentFactory:
    """
    AI组件工厂
    
    负责创建和管理AI相关组件
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI组件工厂
        
        Args:
            config: 配置参数
        """
        self.config = config
        self._components = {}
        self._initialized = False
        
        try:
            self._initialize()
            self._initialized = True
            logger.info("AI组件工厂初始化成功")
        except Exception as e:
            logger.error(f"AI组件工厂初始化失败: {e}")
            
    def _initialize(self):
        """初始化工厂"""
        # 注册组件类型
        self._register_component_types()
        
    def _register_component_types(self):
        """注册组件类型"""
        try:
            # 导入组件类
            from ..components.ai_input_component import AIInputComponent
            from ..components.ai_output_component import AIOutputComponent
            from ..components.ai_status_component import AIStatusComponent
            
            # 注册组件
            self._components['input'] = AIInputComponent
            self._components['output'] = AIOutputComponent
            self._components['status'] = AIStatusComponent
            
            logger.debug("AI组件类型注册完成")
            
        except Exception as e:
            logger.error(f"注册AI组件类型失败: {e}")
            
    def create_component(self, component_type: str, parent: Optional[QWidget] = None, **kwargs) -> Optional[QWidget]:
        """
        创建AI组件
        
        Args:
            component_type: 组件类型
            parent: 父组件
            **kwargs: 其他参数
            
        Returns:
            QWidget: 创建的组件，失败返回None
        """
        if not self._initialized:
            logger.error("AI组件工厂未初始化")
            return None
            
        if component_type not in self._components:
            logger.error(f"未知的组件类型: {component_type}")
            return None
            
        try:
            component_class = self._components[component_type]
            component = component_class(parent)
            
            # 应用配置
            if hasattr(component, 'apply_config'):
                component.apply_config(self.config)
                
            logger.debug(f"AI组件创建成功: {component_type}")
            return component
            
        except Exception as e:
            logger.error(f"创建AI组件失败: {component_type}, {e}")
            return None
            
    def get_available_components(self) -> list:
        """获取可用的组件类型"""
        return list(self._components.keys())
        
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
        
    def shutdown(self):
        """关闭工厂"""
        try:
            self._components.clear()
            self._initialized = False
            logger.info("AI组件工厂已关闭")
        except Exception as e:
            logger.error(f"关闭AI组件工厂失败: {e}")
            
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.config.copy()
        
    def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        self.config.update(new_config)
        logger.debug("AI组件工厂配置已更新")

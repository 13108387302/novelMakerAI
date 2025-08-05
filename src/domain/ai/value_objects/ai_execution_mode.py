#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI执行模式值对象

定义AI功能的执行模式，支持智能化操作
"""

from enum import Enum
from typing import Dict, Any


class AIExecutionMode(Enum):
    """
    AI执行模式枚举
    
    定义AI功能如何被触发和执行，支持100%智能化
    """
    
    # 自动执行模式
    AUTO_CONTEXT = "auto_context"           # 自动基于上下文执行
    AUTO_SELECTION = "auto_selection"       # 自动基于选中文字执行
    
    # 混合模式
    HYBRID = "hybrid"                       # 混合模式（智能选择输入源）
    
    # 手动模式
    MANUAL_INPUT = "manual_input"           # 需要用户手动输入
    
    @property
    def is_automatic(self) -> bool:
        """是否为自动模式"""
        return self in [self.AUTO_CONTEXT, self.AUTO_SELECTION]
    
    @property
    def is_intelligent(self) -> bool:
        """是否为智能化模式"""
        return self in [self.AUTO_CONTEXT, self.AUTO_SELECTION, self.HYBRID]
    
    @property
    def requires_context(self) -> bool:
        """是否需要上下文"""
        return self in [self.AUTO_CONTEXT, self.HYBRID]
    
    @property
    def requires_selection(self) -> bool:
        """是否需要选中文字"""
        return self in [self.AUTO_SELECTION, self.HYBRID]
    
    @property
    def requires_user_input(self) -> bool:
        """是否需要用户输入"""
        return self == self.MANUAL_INPUT
    
    def can_execute_with(self, context: str = "", selected_text: str = "") -> bool:
        """
        检查是否可以在给定条件下执行
        
        Args:
            context: 上下文内容
            selected_text: 选中的文字
            
        Returns:
            bool: 是否可以执行
        """
        if self == self.AUTO_CONTEXT:
            return bool(context.strip())
        elif self == self.AUTO_SELECTION:
            return bool(selected_text.strip())
        elif self == self.HYBRID:
            return bool(context.strip()) or bool(selected_text.strip())
        elif self == self.MANUAL_INPUT:
            return True  # 手动模式总是可以执行
        else:
            return False
    
    def get_input_source(self, context: str = "", selected_text: str = "") -> str:
        """
        获取输入源
        
        Args:
            context: 上下文内容
            selected_text: 选中的文字
            
        Returns:
            str: 输入内容
        """
        if self == self.AUTO_CONTEXT:
            return context
        elif self == self.AUTO_SELECTION:
            return selected_text
        elif self == self.HYBRID:
            # 优先使用选中文字，其次使用上下文
            return selected_text if selected_text.strip() else context
        else:
            return ""
    
    def get_description(self) -> str:
        """获取模式描述"""
        descriptions = {
            self.AUTO_CONTEXT: "自动基于文档内容执行",
            self.AUTO_SELECTION: "自动基于选中文字执行", 
            self.HYBRID: "智能选择输入源执行",
            self.MANUAL_INPUT: "需要用户手动输入"
        }
        return descriptions.get(self, "未知模式")
    
    def get_user_hint(self) -> str:
        """获取用户提示"""
        hints = {
            self.AUTO_CONTEXT: "无需输入，AI将自动分析文档内容",
            self.AUTO_SELECTION: "请选中要处理的文字",
            self.HYBRID: "可选中文字或直接使用文档内容",
            self.MANUAL_INPUT: "请在输入框中输入内容"
        }
        return hints.get(self, "")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'value': self.value,
            'name': self.name,
            'is_automatic': self.is_automatic,
            'is_intelligent': self.is_intelligent,
            'requires_context': self.requires_context,
            'requires_selection': self.requires_selection,
            'requires_user_input': self.requires_user_input,
            'description': self.get_description(),
            'user_hint': self.get_user_hint()
        }
    
    @classmethod
    def from_string(cls, value: str) -> 'AIExecutionMode':
        """从字符串创建实例"""
        try:
            return cls(value)
        except ValueError:
            # 兼容旧版本
            legacy_mapping = {
                'auto': cls.AUTO_CONTEXT,
                'selection': cls.AUTO_SELECTION,
                'manual': cls.MANUAL_INPUT
            }
            return legacy_mapping.get(value.lower(), cls.MANUAL_INPUT)
    
    def __str__(self) -> str:
        return f"{self.name}({self.value})"
    
    def __repr__(self) -> str:
        return f"AIExecutionMode.{self.name}"

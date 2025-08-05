#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能按钮组件

提供智能化的按钮功能
"""

import logging
from typing import Optional, Dict, Any, Callable
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class SmartButtonComponent(QPushButton):
    """
    智能按钮组件
    
    提供智能化的按钮功能，支持上下文感知和自动执行
    """
    
    # 信号
    smart_action_triggered = pyqtSignal(str, dict)  # 智能操作触发信号
    
    def __init__(self, text: str = "", parent=None):
        """
        初始化智能按钮
        
        Args:
            text: 按钮文字
            parent: 父组件
        """
        super().__init__(text, parent)
        self._action_id = ""
        self._context = {}
        self._auto_execute = False
        self._smart_handler: Optional[Callable] = None
        
        # 连接信号
        self.clicked.connect(self._on_clicked)
        
    def set_smart_action(self, action_id: str, handler: Optional[Callable] = None, auto_execute: bool = False):
        """
        设置智能操作
        
        Args:
            action_id: 操作ID
            handler: 处理函数
            auto_execute: 是否自动执行
        """
        self._action_id = action_id
        self._smart_handler = handler
        self._auto_execute = auto_execute
        
        logger.debug(f"智能按钮设置操作: {action_id}")
        
    def set_context(self, context: Dict[str, Any]):
        """
        设置上下文
        
        Args:
            context: 上下文数据
        """
        self._context = context
        
        # 根据上下文更新按钮状态
        self._update_button_state()
        
    def _update_button_state(self):
        """根据上下文更新按钮状态"""
        try:
            # 检查是否有可用的上下文
            has_context = bool(self._context.get('content') or self._context.get('selected_text'))
            self.setEnabled(has_context)
            
            # 更新工具提示
            if has_context:
                content_preview = self._get_content_preview()
                self.setToolTip(f"对以下内容执行操作:\n{content_preview}")
            else:
                self.setToolTip("请先选择内容或打开文档")
                
        except Exception as e:
            logger.error(f"更新按钮状态失败: {e}")
            
    def _get_content_preview(self) -> str:
        """获取内容预览"""
        selected_text = self._context.get('selected_text', '')
        if selected_text:
            preview = selected_text[:50] + "..." if len(selected_text) > 50 else selected_text
            return f"选中文字: {preview}"
            
        content = self._context.get('content', '')
        if content:
            preview = content[:50] + "..." if len(content) > 50 else content
            return f"文档内容: {preview}"
            
        return "无内容"
        
    def _on_clicked(self):
        """处理点击事件"""
        try:
            if not self._action_id:
                logger.warning("智能按钮未设置操作ID")
                return
                
            # 执行智能处理函数
            if self._smart_handler:
                result = self._smart_handler(self._context)
                if result is False:
                    return  # 处理函数返回False表示取消操作
                    
            # 发射智能操作信号
            self.smart_action_triggered.emit(self._action_id, self._context)
            
            logger.debug(f"智能按钮操作触发: {self._action_id}")
            
        except Exception as e:
            logger.error(f"智能按钮操作失败: {e}")
            
    def get_action_id(self) -> str:
        """获取操作ID"""
        return self._action_id
        
    def get_context(self) -> Dict[str, Any]:
        """获取上下文"""
        return self._context.copy()
        
    def is_auto_execute(self) -> bool:
        """检查是否自动执行"""
        return self._auto_execute

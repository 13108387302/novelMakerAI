#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI输出组件

提供AI输出相关的用户界面组件
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QProgressBar, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from .base_ai_widget import BaseAIWidget

logger = logging.getLogger(__name__)


class AIOutputComponent(BaseAIWidget):
    """
    AI输出组件
    
    提供AI输出相关的用户界面
    """
    
    # 信号
    output_ready = pyqtSignal(str)  # 输出就绪信号
    copy_requested = pyqtSignal(str)  # 复制请求信号
    
    def __init__(self, parent=None):
        """
        初始化AI输出组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        self._is_streaming = False
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 输出区域
        output_group = QGroupBox("AI输出")
        output_layout = QVBoxLayout(output_group)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        output_layout.addLayout(status_layout)
        
        # 输出文本框
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("AI输出将显示在这里...")
        
        # 设置字体
        font = QFont("Consolas", 10)
        self.output_text.setFont(font)
        
        output_layout.addWidget(self.output_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.copy_button = QPushButton("复制")
        self.copy_button.setEnabled(False)
        button_layout.addWidget(self.copy_button)
        
        self.clear_button = QPushButton("清空")
        button_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        button_layout.addStretch()
        
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        output_layout.addLayout(button_layout)
        
        layout.addWidget(output_group)
        
    def _setup_connections(self):
        """设置信号连接"""
        self.copy_button.clicked.connect(self._on_copy)
        self.clear_button.clicked.connect(self._on_clear)
        self.save_button.clicked.connect(self._on_save)
        self.stop_button.clicked.connect(self._on_stop)
        self.output_text.textChanged.connect(self._on_text_changed)
        
    def _on_copy(self):
        """处理复制"""
        text = self.output_text.toPlainText()
        if text:
            self.copy_requested.emit(text)
            
    def _on_clear(self):
        """处理清空"""
        self.output_text.clear()
        self._update_button_states()
        
    def _on_save(self):
        """处理保存"""
        # TODO: 实现保存功能
        pass
        
    def _on_stop(self):
        """处理停止"""
        self._is_streaming = False
        self._update_status("已停止")
        self._update_button_states()
        
    def _on_text_changed(self):
        """处理文本变化"""
        self._update_button_states()
        
    def _update_button_states(self):
        """更新按钮状态"""
        has_text = bool(self.output_text.toPlainText().strip())
        self.copy_button.setEnabled(has_text)
        self.save_button.setEnabled(has_text)
        self.stop_button.setEnabled(self._is_streaming)
        
    def _update_status(self, status: str):
        """更新状态"""
        self.status_label.setText(status)
        
    def set_output(self, text: str):
        """设置输出文本"""
        self.output_text.setPlainText(text)
        self._update_button_states()
        self.output_ready.emit(text)
        
    def append_output(self, text: str):
        """追加输出文本"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.output_text.setTextCursor(cursor)
        
        # 自动滚动到底部
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def clear_output(self):
        """清空输出"""
        self.output_text.clear()
        self._update_button_states()
        
    def get_output(self) -> str:
        """获取输出文本"""
        return self.output_text.toPlainText()
        
    def start_streaming(self):
        """开始流式输出"""
        self._is_streaming = True
        self._update_status("正在生成...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self._update_button_states()
        
    def stop_streaming(self):
        """停止流式输出"""
        self._is_streaming = False
        self._update_status("完成")
        self.progress_bar.setVisible(False)
        self._update_button_states()
        
    def set_error(self, error_msg: str):
        """设置错误信息"""
        self.output_text.setPlainText(f"错误: {error_msg}")
        self._update_status("错误")
        self.progress_bar.setVisible(False)
        self._is_streaming = False
        self._update_button_states()
        
    def set_enabled(self, enabled: bool):
        """设置启用状态"""
        self.output_text.setEnabled(enabled)
        if enabled:
            self._update_button_states()
        else:
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.stop_button.setEnabled(False)

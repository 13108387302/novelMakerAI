#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI输入组件

提供AI输入相关的用户界面组件
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QComboBox, QCheckBox, QSpinBox, QSlider, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .base_ai_widget import BaseAIWidget

logger = logging.getLogger(__name__)


class AIInputComponent(BaseAIWidget):
    """
    AI输入组件
    
    提供AI输入相关的用户界面
    """
    
    # 信号
    input_submitted = pyqtSignal(str, dict)  # 输入提交信号(文本, 选项)
    input_changed = pyqtSignal(str)  # 输入变化信号
    
    def __init__(self, parent=None):
        """
        初始化AI输入组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 输入区域
        input_group = QGroupBox("AI输入")
        input_layout = QVBoxLayout(input_group)
        
        # 输入文本框
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("请输入您的问题或指令...")
        self.input_text.setMaximumHeight(100)
        input_layout.addWidget(self.input_text)
        
        # 选项区域
        options_layout = QHBoxLayout()
        
        # 模型选择
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4", "deepseek-chat"])
        model_layout.addWidget(self.model_combo)
        options_layout.addLayout(model_layout)
        
        # 温度设置
        temp_layout = QVBoxLayout()
        temp_layout.addWidget(QLabel("创意度:"))
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(70)
        self.temperature_label = QLabel("0.7")
        temp_layout.addWidget(self.temperature_slider)
        temp_layout.addWidget(self.temperature_label)
        options_layout.addLayout(temp_layout)
        
        # 最大长度
        length_layout = QVBoxLayout()
        length_layout.addWidget(QLabel("最大长度:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setValue(2000)
        length_layout.addWidget(self.max_tokens_spin)
        options_layout.addLayout(length_layout)
        
        input_layout.addLayout(options_layout)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.stream_check = QCheckBox("流式输出")
        self.stream_check.setChecked(True)
        advanced_layout.addWidget(self.stream_check)
        
        self.context_check = QCheckBox("使用上下文")
        self.context_check.setChecked(True)
        advanced_layout.addWidget(self.context_check)
        
        input_layout.addWidget(advanced_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.submit_button = QPushButton("发送")
        self.submit_button.setDefault(True)
        button_layout.addWidget(self.submit_button)
        
        self.clear_button = QPushButton("清空")
        button_layout.addWidget(self.clear_button)
        
        input_layout.addLayout(button_layout)
        
        layout.addWidget(input_group)
        
    def _setup_connections(self):
        """设置信号连接"""
        self.submit_button.clicked.connect(self._on_submit)
        self.clear_button.clicked.connect(self._on_clear)
        self.input_text.textChanged.connect(self._on_text_changed)
        self.temperature_slider.valueChanged.connect(self._on_temperature_changed)
        
    def _on_submit(self):
        """处理提交"""
        text = self.input_text.toPlainText().strip()
        if not text:
            return
            
        options = self._get_options()
        self.input_submitted.emit(text, options)
        
    def _on_clear(self):
        """处理清空"""
        self.input_text.clear()
        
    def _on_text_changed(self):
        """处理文本变化"""
        text = self.input_text.toPlainText()
        self.input_changed.emit(text)
        self.submit_button.setEnabled(bool(text.strip()))
        
    def _on_temperature_changed(self, value):
        """处理温度变化"""
        temp = value / 100.0
        self.temperature_label.setText(f"{temp:.1f}")
        
    def _get_options(self) -> Dict[str, Any]:
        """获取选项"""
        return {
            'model': self.model_combo.currentText(),
            'temperature': self.temperature_slider.value() / 100.0,
            'max_tokens': self.max_tokens_spin.value(),
            'stream': self.stream_check.isChecked(),
            'use_context': self.context_check.isChecked()
        }
        
    def set_text(self, text: str):
        """设置输入文本"""
        self.input_text.setPlainText(text)
        
    def get_text(self) -> str:
        """获取输入文本"""
        return self.input_text.toPlainText()
        
    def clear_input(self):
        """清空输入"""
        self.input_text.clear()
        
    def set_enabled(self, enabled: bool):
        """设置启用状态"""
        self.input_text.setEnabled(enabled)
        self.submit_button.setEnabled(enabled and bool(self.get_text().strip()))
        
    def set_options(self, options: Dict[str, Any]):
        """设置选项"""
        if 'model' in options:
            index = self.model_combo.findText(options['model'])
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
                
        if 'temperature' in options:
            value = int(options['temperature'] * 100)
            self.temperature_slider.setValue(value)
            
        if 'max_tokens' in options:
            self.max_tokens_spin.setValue(options['max_tokens'])
            
        if 'stream' in options:
            self.stream_check.setChecked(options['stream'])
            
        if 'use_context' in options:
            self.context_check.setChecked(options['use_context'])

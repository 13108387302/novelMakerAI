#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI状态组件

提供AI状态相关的用户界面组件
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QGroupBox, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPalette

from .base_ai_widget import BaseAIWidget

logger = logging.getLogger(__name__)


class AIStatusComponent(BaseAIWidget):
    """
    AI状态组件
    
    提供AI状态相关的用户界面
    """
    
    # 信号
    status_changed = pyqtSignal(str)  # 状态变化信号
    
    def __init__(self, parent=None):
        """
        初始化AI状态组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        self._current_status = "idle"
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 状态区域
        status_group = QGroupBox("AI状态")
        status_layout = QVBoxLayout(status_group)
        
        # 主状态显示
        main_status_layout = QHBoxLayout()
        
        # 状态指示器
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: green; font-size: 16px;")
        main_status_layout.addWidget(self.status_indicator)
        
        # 状态文本
        self.status_text = QLabel("就绪")
        font = QFont()
        font.setBold(True)
        self.status_text.setFont(font)
        main_status_layout.addWidget(self.status_text)
        
        main_status_layout.addStretch()
        
        status_layout.addLayout(main_status_layout)
        
        # 详细信息
        details_layout = QVBoxLayout()
        
        # 当前操作
        self.operation_label = QLabel("当前操作: 无")
        details_layout.addWidget(self.operation_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        details_layout.addWidget(self.progress_bar)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        
        self.requests_label = QLabel("请求: 0")
        stats_layout.addWidget(self.requests_label)
        
        self.tokens_label = QLabel("令牌: 0")
        stats_layout.addWidget(self.tokens_label)
        
        self.time_label = QLabel("耗时: 0s")
        stats_layout.addWidget(self.time_label)
        
        details_layout.addLayout(stats_layout)
        
        status_layout.addLayout(details_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setMaximumWidth(80)
        control_layout.addWidget(self.refresh_button)
        
        control_layout.addStretch()
        
        self.settings_button = QPushButton("设置")
        self.settings_button.setMaximumWidth(80)
        control_layout.addWidget(self.settings_button)
        
        status_layout.addLayout(control_layout)
        
        layout.addWidget(status_group)
        
        # 添加定时器用于更新状态
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(1000)  # 每秒更新一次
        
    def _setup_connections(self):
        """设置信号连接"""
        self.refresh_button.clicked.connect(self._on_refresh)
        self.settings_button.clicked.connect(self._on_settings)
        
    def _on_refresh(self):
        """处理刷新"""
        self._update_display()
        
    def _on_settings(self):
        """处理设置"""
        # TODO: 打开设置对话框
        pass
        
    def _update_display(self):
        """更新显示"""
        # 这里可以添加实时状态更新逻辑
        pass
        
    def set_status(self, status: str, message: str = ""):
        """
        设置状态
        
        Args:
            status: 状态类型 (idle, processing, error, success)
            message: 状态消息
        """
        self._current_status = status
        
        # 更新状态指示器和文本
        if status == "idle":
            self.status_indicator.setStyleSheet("color: green; font-size: 16px;")
            self.status_text.setText("就绪")
        elif status == "processing":
            self.status_indicator.setStyleSheet("color: orange; font-size: 16px;")
            self.status_text.setText("处理中")
        elif status == "error":
            self.status_indicator.setStyleSheet("color: red; font-size: 16px;")
            self.status_text.setText("错误")
        elif status == "success":
            self.status_indicator.setStyleSheet("color: blue; font-size: 16px;")
            self.status_text.setText("成功")
        
        # 更新操作信息
        if message:
            self.operation_label.setText(f"当前操作: {message}")
        else:
            self.operation_label.setText("当前操作: 无")
            
        self.status_changed.emit(status)
        
    def set_progress(self, value: int, maximum: int = 100):
        """
        设置进度
        
        Args:
            value: 当前值
            maximum: 最大值
        """
        if value >= 0 and maximum > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, maximum)
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.setVisible(False)
            
    def set_indeterminate_progress(self, show: bool = True):
        """
        设置不确定进度
        
        Args:
            show: 是否显示
        """
        if show:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 无限进度条
        else:
            self.progress_bar.setVisible(False)
            
    def update_stats(self, requests: int = None, tokens: int = None, time_ms: int = None):
        """
        更新统计信息
        
        Args:
            requests: 请求数
            tokens: 令牌数
            time_ms: 耗时（毫秒）
        """
        if requests is not None:
            self.requests_label.setText(f"请求: {requests}")
            
        if tokens is not None:
            self.tokens_label.setText(f"令牌: {tokens}")
            
        if time_ms is not None:
            if time_ms < 1000:
                self.time_label.setText(f"耗时: {time_ms}ms")
            else:
                self.time_label.setText(f"耗时: {time_ms/1000:.1f}s")
                
    def get_status(self) -> str:
        """获取当前状态"""
        return self._current_status
        
    def reset(self):
        """重置状态"""
        self.set_status("idle")
        self.set_progress(-1)
        self.update_stats(0, 0, 0)

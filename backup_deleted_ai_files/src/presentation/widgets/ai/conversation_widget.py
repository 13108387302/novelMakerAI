#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对话组件 - 重构版本

提供与AI进行自然对话的界面
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QScrollArea, QFrame, QLabel, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor, QFont

from .ai_widget_base import BaseAIWidget, AIWidgetState
from src.application.services.ai import AIRequestBuilder, AIRequestType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationWidget(BaseAIWidget):
    """
    AI对话组件
    
    提供与AI进行多轮对话的界面，支持上下文记忆和个性化回复
    """
    
    # 对话相关信号
    message_sent = pyqtSignal(str)  # 用户发送的消息
    message_received = pyqtSignal(str)  # AI回复的消息
    conversation_cleared = pyqtSignal()  # 对话清空
    
    def __init__(self, ai_service, widget_id: str = None, parent=None, config=None, theme=None, **kwargs):
        # 对话配置
        self.session_id = kwargs.get('session_id', 'default')
        self.max_history_length = kwargs.get('max_history_length', 20)
        self.auto_scroll = kwargs.get('auto_scroll', True)

        # 对话历史
        self.conversation_history: List[Dict[str, Any]] = []

        # 生成widget_id如果未提供
        if widget_id is None:
            widget_id = f"conversation_{id(self)}"

        super().__init__(ai_service, widget_id, parent, config, theme)
        
        # 自动聚焦到输入框
        QTimer.singleShot(100, lambda: self.input_edit.setFocus())

    def _create_ui(self):
        """创建具体UI - 实现基类抽象方法"""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("💬 AI对话助手")
        title_label.setFont(self.theme.TITLE_FONT)
        layout.addWidget(title_label)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 对话显示区域
        self.conversation_area = self._create_conversation_area()
        main_splitter.addWidget(self.conversation_area)
        
        # 输入区域
        input_widget = self._create_input_area_widget()
        main_splitter.addWidget(input_widget)
        
        # 设置分割器比例 (对话区域:输入区域 = 3:1)
        main_splitter.setSizes([300, 100])
        layout.addWidget(main_splitter)
        
        # 状态栏
        status_bar = self._create_status_bar()
        layout.addWidget(status_bar)
    
    def _create_conversation_area(self) -> QScrollArea:
        """创建对话显示区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
        
        # 对话容器
        self.conversation_container = QFrame()
        self.conversation_layout = QVBoxLayout(self.conversation_container)
        self.conversation_layout.setContentsMargins(10, 10, 10, 10)
        self.conversation_layout.setSpacing(10)
        self.conversation_layout.addStretch()  # 保持消息在底部
        
        scroll_area.setWidget(self.conversation_container)
        
        # 样式
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
            }
        """)
        
        return scroll_area
    
    def _create_input_area_widget(self) -> QFrame:
        """创建输入区域组件"""
        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(5, 5, 5, 5)
        input_layout.setSpacing(5)
        
        # 输入框
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入您的问题或想法...")
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setFont(self.theme.CONTENT_FONT)
        self.input_edit.setStyleSheet(self.theme.INPUT_STYLE % self.theme.PRIMARY_COLOR)
        
        # 监听回车键
        self.input_edit.keyPressEvent = self._on_input_key_press
        
        input_layout.addWidget(self.input_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 发送按钮
        self.send_button = self._create_action_button(
            "📤 发送", 
            color=self.theme.PRIMARY_COLOR,
            tooltip="发送消息 (Ctrl+Enter)"
        )
        self.send_button.clicked.connect(self._send_message)
        button_layout.addWidget(self.send_button)
        
        # 清空对话按钮
        self.clear_button = self._create_action_button(
            "🗑️ 清空",
            color=self.theme.WARNING_COLOR,
            tooltip="清空对话历史"
        )
        self.clear_button.clicked.connect(self._clear_conversation)
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        
        # 快捷操作按钮
        self.quick_help_button = self._create_action_button(
            "❓ 写作帮助",
            color=self.theme.SECONDARY_COLOR,
            tooltip="获取写作相关帮助"
        )
        self.quick_help_button.clicked.connect(self._quick_writing_help)
        button_layout.addWidget(self.quick_help_button)
        
        input_layout.addLayout(button_layout)
        
        return input_frame
    
    def _on_input_key_press(self, event):
        """处理输入框按键事件"""
        # Ctrl+Enter 发送消息
        if (event.key() == Qt.Key.Key_Return and 
            event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self._send_message()
        else:
            # 调用原始的按键处理
            QTextEdit.keyPressEvent(self.input_edit, event)
    
    def _send_message(self) -> None:
        """发送消息"""
        message = self.input_edit.toPlainText().strip()
        if not message:
            return
        
        if self.is_busy():
            self._show_status("AI正在回复中，请稍候...", "warning")
            return
        
        # 清空输入框
        self.input_edit.clear()
        
        # 添加用户消息到对话
        self._add_message("user", message)
        
        # 发送AI请求
        asyncio.create_task(self._process_ai_request(message))
        
        # 发出信号
        self.message_sent.emit(message)
    
    def _clear_conversation(self) -> None:
        """清空对话"""
        # 清空UI
        for i in reversed(range(self.conversation_layout.count() - 1)):  # 保留stretch
            child = self.conversation_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # 清空历史
        self.conversation_history.clear()
        
        # 发出信号
        self.conversation_cleared.emit()
        
        self._show_status("对话已清空", "info")
    
    def _quick_writing_help(self) -> None:
        """快速写作帮助"""
        help_message = "我想获得一些写作方面的帮助和建议"
        self.input_edit.setPlainText(help_message)
        self._send_message()
    
    async def _process_ai_request(self, message: str) -> None:
        """处理AI请求"""
        try:
            self.set_state(AIWidgetState.PROCESSING)
            
            # 构建请求
            request = (AIRequestBuilder()
                      .with_type(AIRequestType.CHAT)
                      .with_prompt(message)
                      .with_metadata('session_id', self.session_id)
                      .with_parameter('max_tokens', 1000)
                      .with_parameter('temperature', 0.7)
                      .build())
            
            # 发送请求
            response = await self.submit_ai_request(request)
            
            if response and response.content:
                # 添加AI回复到对话
                self._add_message("assistant", response.content)
                self.message_received.emit(response.content)
            else:
                self._add_message("assistant", "抱歉，我现在无法回复。请稍后再试。")
            
        except Exception as e:
            logger.error(f"处理AI请求失败: {e}")
            self._add_message("assistant", f"发生错误: {str(e)}")
        finally:
            self.set_state(AIWidgetState.IDLE)
    
    def _add_message(self, role: str, content: str) -> None:
        """添加消息到对话"""
        # 创建消息组件
        message_widget = self._create_message_widget(role, content)
        
        # 添加到布局（在stretch之前）
        self.conversation_layout.insertWidget(
            self.conversation_layout.count() - 1, 
            message_widget
        )
        
        # 添加到历史
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now()
        })
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history_length:
            # 移除最旧的消息
            self.conversation_history.pop(0)
            # 移除最旧的UI组件
            old_widget = self.conversation_layout.itemAt(0).widget()
            if old_widget:
                old_widget.deleteLater()
        
        # 自动滚动到底部
        if self.auto_scroll:
            QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _create_message_widget(self, role: str, content: str) -> QFrame:
        """创建消息组件"""
        message_frame = QFrame()
        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(10, 8, 10, 8)
        message_layout.setSpacing(5)
        
        # 消息头部
        header_layout = QHBoxLayout()
        
        # 角色标签
        role_label = QLabel("👤 您" if role == "user" else "🤖 AI助手")
        role_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        header_layout.addWidget(role_label)
        
        header_layout.addStretch()
        
        # 时间戳
        timestamp_label = QLabel(datetime.now().strftime("%H:%M"))
        timestamp_label.setFont(QFont("Arial", 8))
        timestamp_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(timestamp_label)
        
        message_layout.addLayout(header_layout)
        
        # 消息内容
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setFont(self.theme.CONTENT_FONT)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_layout.addWidget(content_label)
        
        # 样式
        if role == "user":
            message_frame.setStyleSheet("""
                QFrame {
                    background-color: #E3F2FD;
                    border-radius: 8px;
                    border-left: 4px solid #2196F3;
                }
            """)
        else:
            message_frame.setStyleSheet("""
                QFrame {
                    background-color: #F1F8E9;
                    border-radius: 8px;
                    border-left: 4px solid #4CAF50;
                }
            """)
        
        return message_frame
    
    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        scroll_bar = self.conversation_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
    
    def _handle_chunk_received(self, chunk: str) -> None:
        """处理流式响应块"""
        # 对话组件通常不使用流式响应，但可以在这里实现实时显示
        # 可以考虑在最后一条AI消息中实时更新内容
        pass
    
    # 公共接口
    
    def add_system_message(self, message: str) -> None:
        """添加系统消息"""
        self._add_message("system", message)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """设置自动滚动"""
        self.auto_scroll = enabled

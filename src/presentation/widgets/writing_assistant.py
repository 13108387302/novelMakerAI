#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作助手组件

提供实时写作建议、聊天功能和传统AI助手功能
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QLabel, QFrame, QScrollArea, QTabWidget,
    QSlider, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

try:
    from src.presentation.widgets.ai_workers import StreamingAIWorker, AITaskWorker, AITaskConfig, AITaskType
except ImportError:
    try:
        from .ai_workers import StreamingAIWorker, AITaskWorker, AITaskConfig, AITaskType
    except ImportError:
        # 创建占位符类
        from enum import Enum
        from PyQt6.QtCore import QObject, pyqtSignal

        class AITaskType(Enum):
            CONTINUE_WRITING = "continue_writing"
            IMPROVE_TEXT = "improve_text"
            GENERATE_IDEAS = "generate_ideas"

        class AITaskConfig:
            def __init__(self, task_type, prompt, **kwargs):
                self.task_type = task_type
                self.prompt = prompt
                self.__dict__.update(kwargs)

        class AITaskWorker(QObject):
            def __init__(self, ai_service=None):
                super().__init__()
                self.ai_service = ai_service

        class StreamingAIWorker(QObject):
            text_generated = pyqtSignal(str)
            finished = pyqtSignal()
            error_occurred = pyqtSignal(str)

            def __init__(self, ai_service=None):
                super().__init__()
                self.ai_service = ai_service
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class WritingAssistantWidget(QWidget):
    """写作助手组件"""
    
    # 信号定义
    text_applied = pyqtSignal(str)  # 文本应用到编辑器
    status_updated = pyqtSignal(str)  # 状态更新
    
    def __init__(self, ai_service, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.current_worker: Optional[StreamingAIWorker] = None
        self.traditional_worker: Optional[AITaskWorker] = None
        
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 实时写作助手标签页
        self.realtime_tab = self._create_realtime_assistant_tab()
        self.tab_widget.addTab(self.realtime_tab, "🤖 实时助手")
        
        # 聊天助手标签页
        self.chat_tab = self._create_chat_assistant_tab()
        self.tab_widget.addTab(self.chat_tab, "💬 AI聊天")
        
        # 传统AI助手标签页
        self.traditional_tab = self._create_traditional_assistant_tab()
        self.tab_widget.addTab(self.traditional_tab, "🎯 传统AI")
        
        layout.addWidget(self.tab_widget)
        
    def _create_realtime_assistant_tab(self) -> QWidget:
        """创建实时写作助手标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("🤖 实时写作助手")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 写作区域
        writing_frame = QFrame()
        writing_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        writing_layout = QVBoxLayout(writing_frame)
        
        # 写作编辑器
        self.writing_editor = QTextEdit()
        self.writing_editor.setPlaceholderText("在这里开始写作，AI将实时提供建议...")
        self.writing_editor.setMinimumHeight(200)
        writing_layout.addWidget(self.writing_editor)
        
        # 实时建议区域
        suggestion_layout = QHBoxLayout()
        
        self.streaming_suggestion = QLabel("开始写作以获取AI建议...")
        self.streaming_suggestion.setWordWrap(True)
        self.streaming_suggestion.setStyleSheet("""
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #87ceeb;
                border-radius: 5px;
                padding: 10px;
                color: #2e8b57;
            }
        """)
        suggestion_layout.addWidget(self.streaming_suggestion, 3)
        
        # 建议操作按钮
        suggestion_buttons = QVBoxLayout()
        self.accept_suggestion_btn = QPushButton("✅ 接受")
        self.reject_suggestion_btn = QPushButton("❌ 拒绝")
        suggestion_buttons.addWidget(self.accept_suggestion_btn)
        suggestion_buttons.addWidget(self.reject_suggestion_btn)
        suggestion_layout.addLayout(suggestion_buttons, 1)
        
        writing_layout.addLayout(suggestion_layout)
        
        # 自动续写选项
        options_layout = QHBoxLayout()
        self.auto_continue_check = QCheckBox("自动续写建议")
        self.auto_continue_check.setChecked(True)
        options_layout.addWidget(self.auto_continue_check)
        options_layout.addStretch()
        
        writing_layout.addLayout(options_layout)
        layout.addWidget(writing_frame)
        
        return widget
        
    def _create_chat_assistant_tab(self) -> QWidget:
        """创建聊天助手标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("💬 AI写作聊天助手")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 聊天显示区域
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(300)
        self.chat_display.setPlaceholderText("AI助手将在这里回复您的问题...")
        layout.addWidget(self.chat_display)
        
        # 聊天输入区域
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入您的问题或写作需求...")
        input_layout.addWidget(self.chat_input)
        
        self.send_chat_btn = QPushButton("发送")
        self.send_chat_btn.setFixedWidth(80)
        input_layout.addWidget(self.send_chat_btn)
        
        layout.addLayout(input_layout)
        
        # 快捷问题按钮
        quick_questions_layout = QHBoxLayout()
        quick_questions = [
            "如何改进这段对话？",
            "这个角色需要什么特点？",
            "情节如何发展？",
            "如何增强描写？"
        ]
        
        for question in quick_questions:
            btn = QPushButton(question)
            btn.clicked.connect(lambda checked, q=question: self._send_quick_question(q))
            quick_questions_layout.addWidget(btn)
            
        layout.addLayout(quick_questions_layout)
        
        return widget
        
    def _create_traditional_assistant_tab(self) -> QWidget:
        """创建传统AI助手标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("🎯 传统AI助手")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 输入区域
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        input_layout.addWidget(QLabel("输入内容:"))
        self.traditional_input = QTextEdit()
        self.traditional_input.setPlaceholderText("输入需要AI处理的内容...")
        self.traditional_input.setMaximumHeight(200)
        input_layout.addWidget(self.traditional_input)
        
        # 参数设置
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("创意度:"))
        
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(70)
        params_layout.addWidget(self.temperature_slider)
        
        self.temperature_label = QLabel("0.7")
        params_layout.addWidget(self.temperature_label)
        
        input_layout.addLayout(params_layout)
        
        # 发送按钮
        self.send_traditional_btn = QPushButton("🚀 发送请求")
        input_layout.addWidget(self.send_traditional_btn)
        
        splitter.addWidget(input_widget)
        
        # 输出区域
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        output_layout.addWidget(QLabel("AI回复:"))
        self.traditional_output = QTextEdit()
        self.traditional_output.setReadOnly(True)
        self.traditional_output.setPlaceholderText("AI的回复将显示在这里...")
        output_layout.addWidget(self.traditional_output)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        self.copy_traditional_btn = QPushButton("📋 复制")
        self.apply_traditional_btn = QPushButton("✅ 应用")
        self.clear_traditional_btn = QPushButton("🗑️ 清空")
        
        action_layout.addWidget(self.copy_traditional_btn)
        action_layout.addWidget(self.apply_traditional_btn)
        action_layout.addWidget(self.clear_traditional_btn)
        action_layout.addStretch()
        
        output_layout.addLayout(action_layout)
        
        splitter.addWidget(output_widget)
        splitter.setSizes([1, 1])
        
        layout.addWidget(splitter)
        
        return widget
        
    def _setup_connections(self):
        """设置信号连接"""
        # 实时写作助手
        self.writing_editor.textChanged.connect(self._on_writing_text_changed)
        self.accept_suggestion_btn.clicked.connect(self._accept_suggestion)
        self.reject_suggestion_btn.clicked.connect(self._reject_suggestion)
        
        # 聊天助手
        self.chat_input.returnPressed.connect(self._send_chat_message)
        self.send_chat_btn.clicked.connect(self._send_chat_message)
        
        # 传统AI助手
        self.temperature_slider.valueChanged.connect(self._update_temperature)
        self.send_traditional_btn.clicked.connect(self._send_traditional_request)
        self.copy_traditional_btn.clicked.connect(self._copy_traditional_result)
        self.apply_traditional_btn.clicked.connect(self._apply_traditional_result)
        self.clear_traditional_btn.clicked.connect(self._clear_traditional_results)
        
    def _on_writing_text_changed(self):
        """写作文本变化时的处理"""
        if not self.auto_continue_check.isChecked():
            return
            
        text = self.writing_editor.toPlainText()
        if len(text) > 50:  # 当文本足够长时才提供建议
            self._get_writing_suggestion(text)
            
    def _get_writing_suggestion(self, text: str):
        """获取写作建议"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
            self.current_worker.wait()
            
        prompt = f"""
基于以下文本内容，提供简短的写作建议或续写建议：

{text[-200:]}  # 只取最后200字符

请提供1-2句简洁的建议。
"""
        
        self.current_worker = StreamingAIWorker(prompt, max_tokens=100, temperature=0.7)
        self.current_worker.chunk_received.connect(self._on_suggestion_chunk)
        self.current_worker.response_completed.connect(self._on_suggestion_completed)
        self.current_worker.error_occurred.connect(self._on_suggestion_error)
        self.current_worker.start()
        
    def _on_suggestion_chunk(self, chunk: str):
        """处理建议流式响应"""
        current_text = self.streaming_suggestion.text()
        if current_text == "开始写作以获取AI建议...":
            self.streaming_suggestion.setText(chunk)
        else:
            self.streaming_suggestion.setText(current_text + chunk)
            
    def _on_suggestion_completed(self, response: str):
        """建议完成"""
        self.streaming_suggestion.setText(response)
        
    def _on_suggestion_error(self, error: str):
        """建议错误"""
        self.streaming_suggestion.setText(f"获取建议失败: {error}")
        
    def _accept_suggestion(self):
        """接受AI建议"""
        suggestion = self.streaming_suggestion.text()
        if suggestion and suggestion != "开始写作以获取AI建议...":
            self.text_applied.emit(suggestion)
            self.streaming_suggestion.setText("建议已应用，继续写作...")
            
    def _reject_suggestion(self):
        """拒绝AI建议"""
        self.streaming_suggestion.setText("建议已拒绝，继续写作...")
        
    def _send_chat_message(self):
        """发送聊天消息"""
        message = self.chat_input.text().strip()
        if not message:
            return
            
        # 显示用户消息
        self._append_chat_message("用户", message)
        self.chat_input.clear()
        
        # 发送AI请求
        self._execute_chat_request(message)
        
    def _send_quick_question(self, question: str):
        """发送快捷问题"""
        self.chat_input.setText(question)
        self._send_chat_message()
        
    def _execute_chat_request(self, message: str):
        """执行聊天请求"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
            self.current_worker.wait()
            
        prompt = f"""
作为专业的写作助手，请回答以下问题：

{message}

请提供专业、实用的建议。
"""
        
        self.current_worker = StreamingAIWorker(prompt, max_tokens=500, temperature=0.7)
        self.current_worker.chunk_received.connect(self._on_chat_chunk)
        self.current_worker.response_completed.connect(self._on_chat_completed)
        self.current_worker.error_occurred.connect(self._on_chat_error)
        self.current_worker.start()
        
        # 显示AI正在回复
        self._append_chat_message("AI助手", "正在思考...")
        
    def _on_chat_chunk(self, chunk: str):
        """处理聊天流式响应"""
        # 更新最后一条AI消息
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.LineUnderCursor)
        
        current_text = cursor.selectedText()
        if "正在思考..." in current_text:
            cursor.removeSelectedText()
            cursor.insertText(f"AI助手: {chunk}")
        else:
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(chunk)
            
    def _on_chat_completed(self, response: str):
        """聊天完成"""
        # 确保完整响应已显示
        pass
        
    def _on_chat_error(self, error: str):
        """聊天错误"""
        self._append_chat_message("系统", f"错误: {error}")
        
    def _append_chat_message(self, sender: str, message: str):
        """添加聊天消息"""
        self.chat_display.append(f"<b>{sender}:</b> {message}")
        
    def _update_temperature(self, value: int):
        """更新温度设置"""
        temp = value / 100.0
        self.temperature_label.setText(f"{temp:.1f}")
        
    def _send_traditional_request(self):
        """发送传统AI请求"""
        content = self.traditional_input.toPlainText().strip()
        if not content:
            return
            
        if self.traditional_worker and self.traditional_worker.isRunning():
            self.traditional_worker.cancel()
            self.traditional_worker.wait()
            
        # 创建任务配置
        config = AITaskConfig(
            task_type=AITaskType.TEXT_REWRITING,
            title="文本处理",
            description="处理用户输入的文本",
            icon="🎯",
            temperature=self.temperature_slider.value() / 100.0
        )
        
        self.traditional_worker = AITaskWorker(content, config)
        self.traditional_worker.chunk_received.connect(self._on_traditional_chunk)
        self.traditional_worker.task_completed.connect(self._on_traditional_completed)
        self.traditional_worker.task_failed.connect(self._on_traditional_error)
        self.traditional_worker.start()
        
        self.traditional_output.setText("正在处理...")
        
    def _on_traditional_chunk(self, chunk: str):
        """处理传统AI流式响应"""
        current_text = self.traditional_output.toPlainText()
        if current_text == "正在处理...":
            self.traditional_output.setText(chunk)
        else:
            self.traditional_output.setText(current_text + chunk)
            
    def _on_traditional_completed(self, response: str):
        """传统AI完成"""
        self.traditional_output.setText(response)
        
    def _on_traditional_error(self, error: str):
        """传统AI错误"""
        self.traditional_output.setText(f"处理失败: {error}")
        
    def _copy_traditional_result(self):
        """复制传统AI结果"""
        text = self.traditional_output.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self.status_updated.emit("结果已复制到剪贴板")
            
    def _apply_traditional_result(self):
        """应用传统AI结果"""
        text = self.traditional_output.toPlainText()
        if text:
            self.text_applied.emit(text)
            self.status_updated.emit("结果已应用到编辑器")
            
    def _clear_traditional_results(self):
        """清空传统AI结果"""
        self.traditional_input.clear()
        self.traditional_output.clear()
        
    def cleanup(self):
        """清理资源"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
            self.current_worker.wait()
            
        if self.traditional_worker and self.traditional_worker.isRunning():
            self.traditional_worker.cancel()
            self.traditional_worker.wait()

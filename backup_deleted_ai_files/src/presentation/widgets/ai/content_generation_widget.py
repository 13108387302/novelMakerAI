#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容生成组件 - 重构版本

提供AI辅助的内容生成功能
"""

import asyncio
from typing import Dict, Any, Optional
from enum import Enum

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QComboBox,
    QLabel, QGroupBox, QTabWidget, QWidget, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .ai_widget_base import BaseAIWidget, AIWidgetState
from src.application.services.ai import AIRequestBuilder, AIRequestType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class GenerationType(Enum):
    """生成类型"""
    CONTINUE = "continue"
    REWRITE = "rewrite"
    IMPROVE = "improve"
    EXPAND = "expand"
    SUMMARIZE = "summarize"
    CREATIVE = "creative"


class ContentGenerationWidget(BaseAIWidget):
    """
    内容生成组件
    
    提供多种AI内容生成功能，包括续写、改写、扩展等
    """
    
    # 生成相关信号
    generation_started = pyqtSignal(str)  # generation_type
    generation_completed = pyqtSignal(str, str)  # generation_type, content
    content_applied = pyqtSignal(str)  # 应用到编辑器的内容
    
    def __init__(self, ai_service, widget_id: str = None, parent=None, config=None, theme=None, **kwargs):
        # 配置
        self.enable_streaming = kwargs.get('enable_streaming', True)
        self.default_max_tokens = kwargs.get('default_max_tokens', 1000)

        # 当前生成状态
        self.current_generation_type: Optional[GenerationType] = None
        self.streaming_content = ""

        # 生成widget_id如果未提供
        if widget_id is None:
            widget_id = f"content_generation_{id(self)}"

        super().__init__(ai_service, widget_id, parent, config, theme)

    def _create_ui(self):
        """创建具体UI - 实现基类抽象方法"""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("✍️ 内容生成器")
        title_label.setFont(self.theme.TITLE_FONT)
        layout.addWidget(title_label)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 基础生成标签页
        basic_tab = self._create_basic_generation_tab()
        self.tab_widget.addTab(basic_tab, "📝 基础生成")
        
        # 高级生成标签页
        advanced_tab = self._create_advanced_generation_tab()
        self.tab_widget.addTab(advanced_tab, "⚙️ 高级设置")
        
        layout.addWidget(self.tab_widget)
        
        # 状态栏
        status_bar = self._create_status_bar()
        layout.addWidget(status_bar)
    
    def _create_basic_generation_tab(self) -> QWidget:
        """创建基础生成标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 输入区域
        input_group = QGroupBox("输入内容")
        input_layout = QVBoxLayout(input_group)
        
        self.input_text = self._create_input_area(
            placeholder="请输入需要处理的文本内容...",
            max_height=150
        )
        input_layout.addWidget(self.input_text)
        
        layout.addWidget(input_group)
        
        # 生成类型选择
        type_group = QGroupBox("生成类型")
        type_layout = QVBoxLayout(type_group)
        
        # 生成类型按钮
        button_layout = QHBoxLayout()
        
        self.continue_btn = self._create_action_button(
            "📖 续写",
            color=self.theme.PRIMARY_COLOR,
            tooltip="基于现有内容进行续写"
        )
        self.continue_btn.clicked.connect(lambda: self._start_generation(GenerationType.CONTINUE))
        button_layout.addWidget(self.continue_btn)
        
        self.rewrite_btn = self._create_action_button(
            "🔄 改写",
            color=self.theme.SECONDARY_COLOR,
            tooltip="改写现有内容"
        )
        self.rewrite_btn.clicked.connect(lambda: self._start_generation(GenerationType.REWRITE))
        button_layout.addWidget(self.rewrite_btn)
        
        self.improve_btn = self._create_action_button(
            "✨ 优化",
            color="#9C27B0",
            tooltip="优化文本质量"
        )
        self.improve_btn.clicked.connect(lambda: self._start_generation(GenerationType.IMPROVE))
        button_layout.addWidget(self.improve_btn)
        
        type_layout.addLayout(button_layout)
        
        # 第二行按钮
        button_layout2 = QHBoxLayout()
        
        self.expand_btn = self._create_action_button(
            "📈 扩展",
            color="#FF5722",
            tooltip="扩展内容细节"
        )
        self.expand_btn.clicked.connect(lambda: self._start_generation(GenerationType.EXPAND))
        button_layout2.addWidget(self.expand_btn)
        
        self.summarize_btn = self._create_action_button(
            "📋 摘要",
            color="#607D8B",
            tooltip="生成内容摘要"
        )
        self.summarize_btn.clicked.connect(lambda: self._start_generation(GenerationType.SUMMARIZE))
        button_layout2.addWidget(self.summarize_btn)
        
        self.creative_btn = self._create_action_button(
            "🎨 创意",
            color="#E91E63",
            tooltip="创意性改写"
        )
        self.creative_btn.clicked.connect(lambda: self._start_generation(GenerationType.CREATIVE))
        button_layout2.addWidget(self.creative_btn)
        
        type_layout.addLayout(button_layout2)
        layout.addWidget(type_group)
        
        # 输出区域
        output_group = QGroupBox("生成结果")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = self._create_output_area(
            placeholder="AI生成的内容将显示在这里..."
        )
        output_layout.addWidget(self.output_text)
        
        # 输出操作按钮
        output_actions_layout = QHBoxLayout()
        
        self.apply_btn = self._create_action_button(
            "📝 应用",
            color=self.theme.SUCCESS_COLOR,
            tooltip="将生成的内容应用到编辑器"
        )
        self.apply_btn.clicked.connect(self._apply_content)
        self.apply_btn.setEnabled(False)
        output_actions_layout.addWidget(self.apply_btn)
        
        self.copy_btn = self._create_action_button(
            "📋 复制",
            color=self.theme.SECONDARY_COLOR,
            tooltip="复制生成的内容"
        )
        self.copy_btn.clicked.connect(self._copy_content)
        self.copy_btn.setEnabled(False)
        output_actions_layout.addWidget(self.copy_btn)
        
        self.clear_btn = self._create_action_button(
            "🗑️ 清空",
            color=self.theme.WARNING_COLOR,
            tooltip="清空生成结果"
        )
        self.clear_btn.clicked.connect(self._clear_output)
        output_actions_layout.addWidget(self.clear_btn)
        
        output_actions_layout.addStretch()
        output_layout.addLayout(output_actions_layout)
        
        layout.addWidget(output_group)
        
        return widget
    
    def _create_advanced_generation_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 参数设置
        params_group = QGroupBox("生成参数")
        params_layout = QVBoxLayout(params_group)
        
        # 最大令牌数
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("最大长度:"))
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setValue(self.default_max_tokens)
        self.max_tokens_spin.setSuffix(" 字符")
        tokens_layout.addWidget(self.max_tokens_spin)
        tokens_layout.addStretch()
        
        params_layout.addLayout(tokens_layout)
        
        # 创意度
        creativity_layout = QHBoxLayout()
        creativity_layout.addWidget(QLabel("创意度:"))
        
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(70)
        self.temperature_slider.valueChanged.connect(self._update_temperature_label)
        creativity_layout.addWidget(self.temperature_slider)
        
        self.temperature_label = QLabel("0.7")
        creativity_layout.addWidget(self.temperature_label)
        
        params_layout.addLayout(creativity_layout)
        
        layout.addWidget(params_group)
        
        # 上下文设置
        context_group = QGroupBox("上下文设置")
        context_layout = QVBoxLayout(context_group)
        
        self.context_text = self._create_input_area(
            placeholder="可选：提供额外的背景信息或要求...",
            max_height=80
        )
        context_layout.addWidget(self.context_text)
        
        layout.addWidget(context_group)
        
        layout.addStretch()
        
        return widget
    
    def _update_temperature_label(self, value: int) -> None:
        """更新创意度标签"""
        temperature = value / 100.0
        self.temperature_label.setText(f"{temperature:.1f}")
    
    def _start_generation(self, generation_type: GenerationType) -> None:
        """开始生成内容"""
        if self.is_busy():
            self._show_status("正在生成中，请稍候...", "warning")
            return
        
        input_content = self.input_text.toPlainText().strip()
        if not input_content:
            self._show_status("请先输入内容", "warning")
            return
        
        self.current_generation_type = generation_type
        self.streaming_content = ""
        
        # 清空输出
        self.output_text.clear()
        
        # 禁用按钮
        self._set_buttons_enabled(False)
        
        # 开始生成
        asyncio.create_task(self._process_generation_request(generation_type, input_content))
        
        # 发出信号
        self.generation_started.emit(generation_type.value)
    
    async def _process_generation_request(self, generation_type: GenerationType, content: str) -> None:
        """处理生成请求"""
        try:
            self.set_state(AIWidgetState.PROCESSING)
            
            # 构建请求
            request_type = self._get_request_type(generation_type)
            prompt = self._build_prompt(generation_type, content)
            context = self.context_text.toPlainText().strip()
            
            request = (AIRequestBuilder()
                      .with_type(request_type)
                      .with_prompt(prompt)
                      .with_context(context)
                      .with_parameter('max_tokens', self.max_tokens_spin.value())
                      .with_parameter('temperature', self.temperature_slider.value() / 100.0)
                      .build())
            
            # 发送请求
            if self.enable_streaming:
                await self._process_streaming_request(request)
            else:
                response = await self.submit_ai_request(request)
                if response and response.content:
                    self.output_text.setPlainText(response.content)
                    self.generation_completed.emit(generation_type.value, response.content)
            
        except Exception as e:
            logger.error(f"生成内容失败: {e}")
            self._show_status(f"生成失败: {str(e)}", "error")
        finally:
            self.set_state(AIWidgetState.IDLE)
            self._set_buttons_enabled(True)
            self._update_output_buttons()
    
    async def _process_streaming_request(self, request) -> None:
        """处理流式请求"""
        try:
            async for chunk in self.ai_service_manager.process_request_stream(request):
                self.streaming_content += chunk
                self.output_text.setPlainText(self.streaming_content)
                
                # 自动滚动到底部
                cursor = self.output_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.output_text.setTextCursor(cursor)
            
            if self.current_generation_type:
                self.generation_completed.emit(
                    self.current_generation_type.value, 
                    self.streaming_content
                )
                
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            raise
    
    def _get_request_type(self, generation_type: GenerationType) -> AIRequestType:
        """获取请求类型"""
        mapping = {
            GenerationType.CONTINUE: AIRequestType.CONTINUE,
            GenerationType.REWRITE: AIRequestType.REWRITE,
            GenerationType.IMPROVE: AIRequestType.IMPROVE,
            GenerationType.EXPAND: AIRequestType.GENERATE,
            GenerationType.SUMMARIZE: AIRequestType.SUMMARIZE,
            GenerationType.CREATIVE: AIRequestType.REWRITE
        }
        return mapping.get(generation_type, AIRequestType.GENERATE)
    
    def _build_prompt(self, generation_type: GenerationType, content: str) -> str:
        """构建提示词"""
        prompts = {
            GenerationType.CONTINUE: f"请为以下内容进行自然流畅的续写：\n\n{content}",
            GenerationType.REWRITE: f"请改写以下内容，保持原意但改进表达：\n\n{content}",
            GenerationType.IMPROVE: f"请优化以下内容的质量和表达效果：\n\n{content}",
            GenerationType.EXPAND: f"请扩展以下内容，增加更多细节和描述：\n\n{content}",
            GenerationType.SUMMARIZE: f"请为以下内容生成简洁准确的摘要：\n\n{content}",
            GenerationType.CREATIVE: f"请对以下内容进行创意性改写：\n\n{content}"
        }
        return prompts.get(generation_type, content)
    
    def _set_buttons_enabled(self, enabled: bool) -> None:
        """设置按钮启用状态"""
        buttons = [
            self.continue_btn, self.rewrite_btn, self.improve_btn,
            self.expand_btn, self.summarize_btn, self.creative_btn
        ]
        for button in buttons:
            button.setEnabled(enabled)
    
    def _update_output_buttons(self) -> None:
        """更新输出按钮状态"""
        has_content = bool(self.output_text.toPlainText().strip())
        self.apply_btn.setEnabled(has_content)
        self.copy_btn.setEnabled(has_content)
    
    def _apply_content(self) -> None:
        """应用内容"""
        content = self.output_text.toPlainText()
        if content:
            self.content_applied.emit(content)
            self._show_status("内容已应用", "success")
    
    def _copy_content(self) -> None:
        """复制内容"""
        content = self.output_text.toPlainText()
        if content:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            self._show_status("内容已复制到剪贴板", "success")
    
    def _clear_output(self) -> None:
        """清空输出"""
        self.output_text.clear()
        self.streaming_content = ""
        self._update_output_buttons()
        self._show_status("输出已清空", "info")
    
    def _handle_chunk_received(self, chunk: str) -> None:
        """处理流式响应块"""
        # 在流式模式下，这个方法会被基类调用
        pass
    
    # 公共接口
    
    def set_input_content(self, content: str) -> None:
        """设置输入内容"""
        self.input_text.setPlainText(content)
    
    def get_output_content(self) -> str:
        """获取输出内容"""
        return self.output_text.toPlainText()
    
    def set_generation_parameters(self, max_tokens: int = None, temperature: float = None) -> None:
        """设置生成参数"""
        if max_tokens is not None:
            self.max_tokens_spin.setValue(max_tokens)
        if temperature is not None:
            self.temperature_slider.setValue(int(temperature * 100))

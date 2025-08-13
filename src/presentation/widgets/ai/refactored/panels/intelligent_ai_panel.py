#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能化AI面板

提供100%智能化的AI功能面板，支持自动执行和智能交互
"""

import logging
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTextEdit, QScrollArea,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from ..components.base_ai_widget import BaseAIWidget
from src.application.services.ai.intelligence.ai_function_registry import (
    ai_function_registry, AIFunctionCategory
)
from src.application.services.ai.intelligence.ai_intelligence_service import AIIntelligentFunction
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode

logger = logging.getLogger(__name__)


class SmartActionButton(QPushButton):
    """智能化操作按钮"""
    
    # 自定义信号
    smart_clicked = pyqtSignal(str)  # 智能点击信号，参数：功能ID
    
    def __init__(self, function: AIIntelligentFunction, parent=None):
        """
        初始化智能化操作按钮
        
        Args:
            function: AI智能化功能
            parent: 父组件
        """
        super().__init__(parent)
        
        self.function = function
        self.metadata = function.metadata
        
        # 设置按钮文本和图标
        self.setText(f"{self.metadata.icon} {self.metadata.name}")
        self.setToolTip(self._build_tooltip())
        
        # 设置按钮样式
        self._setup_button_style()
        
        # 连接信号
        self.clicked.connect(self._on_clicked)
    
    def _build_tooltip(self) -> str:
        """构建工具提示"""
        tooltip_parts = [
            f"<b>{self.metadata.name}</b>",
            f"<p>{self.metadata.description}</p>"
        ]
        
        # 添加智能化信息
        if self.metadata.execution_mode.is_intelligent:
            tooltip_parts.append(f"<p><b>智能化模式:</b> {self.metadata.execution_mode.get_description()}</p>")
            tooltip_parts.append(f"<p><i>{self.metadata.execution_mode.get_user_hint()}</i></p>")
        
        # 添加预估时间
        if self.metadata.estimated_time > 0:
            tooltip_parts.append(f"<p><b>预估时间:</b> {self.metadata.estimated_time}秒</p>")
        
        return "".join(tooltip_parts)
    
    def _setup_button_style(self) -> str:
        """设置按钮样式"""
        # 根据执行模式设置不同的样式
        if self.metadata.execution_mode == AIExecutionMode.AUTO_CONTEXT:
            # 自动基于上下文 - 蓝色
            color = "#0078D4"
        elif self.metadata.execution_mode == AIExecutionMode.AUTO_SELECTION:
            # 自动基于选中文字 - 绿色
            color = "#107C10"
        elif self.metadata.execution_mode == AIExecutionMode.HYBRID:
            # 混合模式 - 橙色
            color = "#FF8C00"
        else:
            # 手动输入 - 灰色
            color = "#605E5C"
        
        # 改为使用主题强调按钮样式，避免内联样式固定颜色
        self.setProperty("accent", True)
        self.setStyleSheet("")

    def _darken_color(self, color: str, factor: float = 0.1) -> str:
        """使颜色变暗"""
        # 简单的颜色变暗实现
        if color == "#0078D4":
            return "#106EBE" if factor < 0.2 else "#005A9E"
        elif color == "#107C10":
            return "#0E6E0E" if factor < 0.2 else "#0C5E0C"
        elif color == "#FF8C00":
            return "#E67E00" if factor < 0.2 else "#CC7000"
        else:
            return "#4A4A4A" if factor < 0.2 else "#323130"
    
    def _on_clicked(self) -> None:
        """按钮点击处理"""
        self.smart_clicked.emit(self.metadata.id)
    
    def update_availability(self, context: str = "", selected_text: str = "") -> None:
        """
        更新按钮可用性
        
        Args:
            context: 上下文内容
            selected_text: 选中文字
        """
        can_execute = self.function.can_auto_execute(context, selected_text)
        self.setEnabled(can_execute)
        
        # 更新工具提示
        if not can_execute:
            hint = self.metadata.execution_mode.get_user_hint()
            self.setToolTip(f"{self._build_tooltip()}<br><br><b>提示:</b> {hint}")


class IntelligentAIPanel(BaseAIWidget):
    """
    智能化AI面板
    
    提供100%智能化的AI功能面板，支持自动执行和智能交互
    """
    
    def __init__(self, parent=None):
        """
        初始化智能化AI面板
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 智能化功能按钮
        self.smart_buttons: Dict[str, SmartActionButton] = {}
        
        # 输出区域
        self.output_area: Optional[QTextEdit] = None
        self.status_label: Optional[QLabel] = None
        
        # 统计信息
        self.intelligence_score = 0.0
        self.total_functions = 0
        self.intelligent_functions = 0
    
    def setup_ui(self) -> None:
        """设置用户界面"""
        super().setup_ui()
        
        # 创建标题区域
        self._create_title_section()
        
        # 创建智能化统计区域
        self._create_statistics_section()
        
        # 创建智能化功能按钮区域
        self._create_smart_buttons_section()
        
        # 创建输出区域
        self._create_output_section()
        
        # 创建状态栏
        self._create_status_section()
        
        # 加载智能化功能
        self._load_intelligent_functions()
    
    def _create_title_section(self) -> None:
        """创建标题区域"""
        title_layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("🧠 AI智能助手")
        title_label.setFont(self.title_font)
        # 颜色由主题控制

        # 智能化指示器
        self.intelligence_indicator = QLabel("🤖 100%智能化")
        # 颜色由主题控制

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.intelligence_indicator)
        
        self.main_layout.addLayout(title_layout)
    
    def _create_statistics_section(self) -> None:
        """创建统计信息区域"""
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.Box)
        # 外观由主题控制
        stats_layout = QHBoxLayout(stats_frame)

        # 统计标签
        self.stats_labels = {
            'total': QLabel("总功能: 0"),
            'intelligent': QLabel("智能化: 0"),
            'score': QLabel("智能化程度: 0%")
        }
        
        for label in self.stats_labels.values():
            # 颜色交由主题控制
            stats_layout.addWidget(label)
            stats_layout.addWidget(QLabel("|"))  # 分隔符

        # 移除最后一个分隔符
        stats_layout.takeAt(stats_layout.count() - 1)
        
        self.main_layout.addWidget(stats_frame)
    
    def _create_smart_buttons_section(self) -> None:
        """创建智能化功能按钮区域"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMaximumHeight(300)
        
        # 创建按钮容器
        buttons_widget = QWidget()
        self.buttons_layout = QGridLayout(buttons_widget)
        self.buttons_layout.setSpacing(8)
        
        scroll_area.setWidget(buttons_widget)
        self.main_layout.addWidget(scroll_area)
    
    def _create_output_section(self) -> None:
        """创建输出区域"""
        # 输出标题
        output_title = QLabel("💬 AI响应")
        output_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        output_title.setStyleSheet(f"color: {self.colors['text_primary']}; margin-top: 8px;")
        self.main_layout.addWidget(output_title)
        
        # 输出文本区域
        self.output_area = QTextEdit()
        self.output_area.setPlaceholderText("AI响应将在这里显示...")
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(200)
        self.output_area.setStyleSheet(self.styles['input'])
        self.main_layout.addWidget(self.output_area)
    
    def _create_status_section(self) -> None:
        """创建状态栏"""
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(self.styles['status'])
        self.main_layout.addWidget(self.status_label)
    
    def _load_intelligent_functions(self) -> None:
        """加载智能化功能"""
        try:
            # 获取所有智能化功能
            all_functions = ai_function_registry.get_all_functions()
            
            # 更新统计信息
            self.total_functions = len(all_functions)
            self.intelligent_functions = len(ai_function_registry.get_intelligent_functions())
            self.intelligence_score = ai_function_registry.calculate_intelligence_score()
            
            # 更新统计显示
            self._update_statistics_display()
            
            # 创建按钮
            row, col = 0, 0
            max_cols = 2
            
            for function_id, function in all_functions.items():
                # 创建智能化按钮
                button = SmartActionButton(function)
                button.smart_clicked.connect(self._on_smart_button_clicked)
                
                # 添加到布局
                self.buttons_layout.addWidget(button, row, col)
                self.smart_buttons[function_id] = button
                
                # 更新位置
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            logger.info(f"加载了 {len(all_functions)} 个AI功能，其中 {self.intelligent_functions} 个智能化")
            
        except Exception as e:
            logger.error(f"加载智能化功能失败: {e}")
            self.show_status(f"加载功能失败: {str(e)}", "error")
    
    def _update_statistics_display(self) -> None:
        """更新统计信息显示"""
        self.stats_labels['total'].setText(f"总功能: {self.total_functions}")
        self.stats_labels['intelligent'].setText(f"智能化: {self.intelligent_functions}")
        self.stats_labels['score'].setText(f"智能化程度: {self.intelligence_score * 100:.0f}%")
        
        # 更新智能化指示器
        if self.intelligence_score >= 1.0:
            self.intelligence_indicator.setText("🤖 100%智能化")
            self.intelligence_indicator.setStyleSheet(f"color: {self.colors['success']}; font-weight: bold;")
        elif self.intelligence_score >= 0.8:
            self.intelligence_indicator.setText(f"🤖 {self.intelligence_score * 100:.0f}%智能化")
            self.intelligence_indicator.setStyleSheet(f"color: {self.colors['warning']}; font-weight: bold;")
        else:
            self.intelligence_indicator.setText(f"🤖 {self.intelligence_score * 100:.0f}%智能化")
            self.intelligence_indicator.setStyleSheet(f"color: {self.colors['error']}; font-weight: bold;")
    
    def _on_smart_button_clicked(self, function_id: str) -> None:
        """
        智能化按钮点击处理
        
        Args:
            function_id: 功能ID
        """
        function = ai_function_registry.get_function(function_id)
        if not function:
            self.show_status(f"功能不存在: {function_id}", "error")
            return
        
        # 显示执行状态
        self.show_status(f"正在执行 {function.metadata.name}...", "info")
        
        # 执行智能化功能
        success = self.execute_intelligent_function(
            function=function,
            callback=self._on_function_completed
        )
        
        if not success:
            self.show_status(f"执行 {function.metadata.name} 失败", "error")
    
    def _on_function_completed(self, response) -> None:
        """
        功能执行完成回调
        
        Args:
            response: AI响应
        """
        if response.is_successful:
            # 显示响应内容
            self.output_area.setPlainText(response.content)
            self.show_status("执行完成", "success")
        else:
            self.show_status(f"执行失败: {response.error_message}", "error")
    
    def _on_context_updated(self) -> None:
        """上下文更新回调"""
        # 更新所有按钮的可用性
        for button in self.smart_buttons.values():
            button.update_availability(self.document_context, self.selected_text)
    
    def _on_status_changed(self, message: str, status_type: str) -> None:
        """状态改变处理"""
        super()._on_status_changed(message, status_type)
        
        if self.status_label:
            self.status_label.setText(message)
            self.status_label.setProperty("status", status_type)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)

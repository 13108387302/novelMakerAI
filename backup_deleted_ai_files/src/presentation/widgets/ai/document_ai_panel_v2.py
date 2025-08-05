#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档AI面板 - 重构版本

为特定文档提供智能AI助手功能，支持上下文感知和文档特定操作
"""

import asyncio
from enum import Enum
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QGroupBox, QComboBox, QFrame, QTabWidget, QCheckBox,
    QSplitter, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from .ai_widget_base import BaseAIWidget, AIWidgetConfig, AIWidgetTheme, AIOutputMode
from .ai_function_modules import ai_function_registry, AIFunctionCategory, AIFunctionModule
from src.application.services.unified_ai_service import UnifiedAIService
from src.application.services.ai.core_abstractions import AIRequestBuilder, AIRequestType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentAIMode(Enum):
    """文档AI模式"""
    CONTEXT_AWARE = "context_aware"  # 上下文感知模式
    SELECTION_BASED = "selection_based"  # 基于选择的模式
    DOCUMENT_ANALYSIS = "document_analysis"  # 文档分析模式
    SMART_WRITING = "smart_writing"  # 智能写作模式


class DocumentAIPanel(BaseAIWidget):
    """
    文档AI面板 - 重构版本
    
    特性：
    - 文档上下文感知
    - 选中文本处理
    - 智能写作建议
    - 文档分析功能
    - 与编辑器深度集成
    """
    
    # 文档特定信号
    text_insert_requested = pyqtSignal(str, int)  # 请求插入文本 (text, position)
    text_replace_requested = pyqtSignal(str, int, int)  # 请求替换文本 (text, start, end)
    selection_analysis_completed = pyqtSignal(dict)  # 选择分析完成
    document_insights_ready = pyqtSignal(dict)  # 文档洞察就绪
    context_updated = pyqtSignal(str)  # 上下文更新
    selection_updated = pyqtSignal(str)  # 选中文字更新
    
    def __init__(
        self, 
        ai_service: UnifiedAIService,
        document_id: str,
        document_type: str = "chapter",
        parent: Optional[QWidget] = None,
        config: Optional[AIWidgetConfig] = None
    ):
        # 文档信息
        self.document_id = document_id
        self.document_type = document_type
        
        # 初始化配置
        if config is None:
            config = AIWidgetConfig()
            config.enable_context_awareness = True
            config.enable_streaming = True
        
        super().__init__(ai_service, f"doc_ai_{document_id}", parent, config)
        
        # 文档状态
        self.current_mode = DocumentAIMode.CONTEXT_AWARE
        self.selected_text = ""
        self.document_context = ""
        self.cursor_position = 0
        self.last_selection_start = 0
        self.last_selection_end = 0
        
        # UI组件
        self.mode_combo: Optional[QComboBox] = None
        self.context_text: Optional[QTextEdit] = None
        self.quick_actions_panel: Optional[QWidget] = None
        
        logger.info(f"文档AI面板初始化完成: {document_id}")
    
    def _create_ui(self):
        """创建UI界面（带滚动支持）"""
        try:
            logger.debug(f"开始创建文档AI面板UI（带滚动支持）: {self.document_id}")

            # 🎨 新设计：垂直布局，支持滚动
            main_container = QWidget()
            main_layout = QVBoxLayout(main_container)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            # 顶部：标题和模式选择区（固定不滚动）
            header = self._create_header_section()
            main_layout.addWidget(header)

            # 中间：可滚动的主要内容区
            scroll_area = self._create_scrollable_content_area()
            main_layout.addWidget(scroll_area, 1)  # 占据剩余空间

            # 底部：状态区（固定不滚动）
            footer = self._create_footer_section()
            main_layout.addWidget(footer)

            self.main_layout.addWidget(main_container)

            logger.info(f"✅ 文档AI面板UI创建完成（带滚动支持）: {self.document_id}")
        except Exception as e:
            logger.error(f"❌ 文档AI面板UI创建失败: {e}")
            raise

    def _create_header_section(self) -> QWidget:
        """创建顶部标题和模式选择区"""
        header = QWidget()
        header.setFixedHeight(80)
        layout = QVBoxLayout(header)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        # 文档AI标题
        title_label = QLabel(f"📄 文档AI助手")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 文档类型标签
        doc_type_label = QLabel(f"({self.document_type})")
        doc_type_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
                background-color: #ecf0f1;
                padding: 2px 8px;
                border-radius: 10px;
            }
        """)
        title_layout.addWidget(doc_type_label)

        layout.addLayout(title_layout)

        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)

        mode_label = QLabel("模式:")
        mode_label.setStyleSheet("font-size: 12px; color: #495057;")
        mode_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "📄 上下文感知", "✂️ 选择处理", "🔍 文档分析", "✍️ 智能写作"
        ])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px;
                padding: 4px 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #3498db;
            }
        """)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)

        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        return header

    def _create_scrollable_content_area(self) -> QWidget:
        """创建可滚动的主要内容区域"""
        from PyQt6.QtWidgets import QScrollArea

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 优化滚动体验
        scroll_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        scroll_area.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

        # 设置现代化滚动条样式
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f8f9fa;
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #dee2e6;
                border-radius: 5px;
                min-height: 15px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #adb5bd;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #6c757d;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        # 创建滚动内容容器
        scroll_content = self._create_scroll_content()
        scroll_area.setWidget(scroll_content)

        # 保存滚动区域引用
        self.scroll_area = scroll_area

        return scroll_area

    def _create_scroll_content(self) -> QWidget:
        """创建滚动区域内的内容"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(12)

        # 快速操作面板
        quick_actions = self._create_quick_actions_panel()
        layout.addWidget(quick_actions)

        # 输入输出区域
        io_area = self._create_compact_io_area()
        layout.addWidget(io_area)

        # 添加底部间距
        layout.addStretch()

        return content

    def _create_footer_section(self) -> QWidget:
        """创建底部状态区"""
        footer = QWidget()
        footer.setFixedHeight(40)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(12, 8, 12, 8)

        # 状态指示器
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-size: 11px;
                padding: 3px 8px;
                background-color: #d5f4e6;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 文档ID显示（调试用）
        doc_id_label = QLabel(f"ID: {self.document_id[:8]}...")
        doc_id_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 10px;
            }
        """)
        layout.addWidget(doc_id_label)

        return footer

    def _create_quick_actions_panel(self) -> QWidget:
        """创建快速操作面板"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 标题
        title = QLabel("⚡ 快速操作")
        title.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(title)

        # 操作按钮网格
        actions_grid = QGridLayout()
        actions_grid.setSpacing(6)

        # 定义快速操作按钮 - 全智能化小说写作功能
        actions = [
            {"text": "✍️ 续写", "tooltip": "智能分析文档末尾，自动续写", "callback": self._quick_continue},
            {"text": "✨ 优化", "tooltip": "智能优化选中文字或输入内容", "callback": self._quick_improve},
            {"text": "🔍 分析", "tooltip": "智能分析选中文字或整个文档", "callback": self._quick_analyze},
            {"text": "💡 灵感", "tooltip": "智能分析文档内容，自动生成写作灵感", "callback": self._quick_inspire},
            {"text": "📝 总结", "tooltip": "智能总结选中文字或整个文档", "callback": self._quick_summary},
            {"text": "🌐 翻译", "tooltip": "智能检测语言并翻译选中文字", "callback": self._quick_translate},
        ]

        for i, action in enumerate(actions):
            btn = QPushButton(action["text"])
            btn.setFixedHeight(28)
            btn.setToolTip(action["tooltip"])
            btn.clicked.connect(action["callback"])
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                    border-color: #3498db;
                }
                QPushButton:pressed {
                    background-color: #dee2e6;
                }
            """)

            row = i // 2
            col = i % 2
            actions_grid.addWidget(btn, row, col)

        layout.addLayout(actions_grid)

        return panel

    def _create_compact_io_area(self) -> QWidget:
        """创建紧凑的输入输出区域"""
        area = QWidget()
        area.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(area)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 输入区域
        input_section = self._create_compact_input_section()
        layout.addWidget(input_section)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #e1e8ed; }")
        layout.addWidget(separator)

        # 输出区域
        output_section = self._create_compact_output_section()
        layout.addWidget(output_section)

        return area

    def _create_compact_input_section(self) -> QWidget:
        """创建紧凑的输入区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 输入标题和按钮行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        input_title = QLabel("📝 输入")
        input_title.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title_row.addWidget(input_title)

        title_row.addStretch()

        # 使用选中文本按钮
        use_selection_btn = QPushButton("📋 使用选中")
        use_selection_btn.setFixedHeight(24)
        use_selection_btn.clicked.connect(self._use_selected_text)
        use_selection_btn.setStyleSheet(self._get_small_button_style())
        title_row.addWidget(use_selection_btn)

        # 清空按钮
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setFixedHeight(24)
        clear_btn.clicked.connect(lambda: self.input_text.clear())
        clear_btn.setStyleSheet(self._get_small_button_style())
        title_row.addWidget(clear_btn)

        layout.addLayout(title_row)

        # 输入文本框
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(100)  # 紧凑高度
        self.input_text.setPlaceholderText("输入要处理的内容，或使用快速操作...")
        self.input_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                line-height: 1.4;
                background-color: #fafbfc;
            }
            QTextEdit:focus {
                border-color: #3498db;
                background-color: white;
            }
        """)
        layout.addWidget(self.input_text)

        # 处理按钮
        process_btn = QPushButton("🚀 处理")
        process_btn.setFixedHeight(32)
        process_btn.clicked.connect(self._process_input)
        process_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        layout.addWidget(process_btn)

        return section

    def _create_compact_output_section(self) -> QWidget:
        """创建紧凑的输出区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 输出标题和按钮行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        output_title = QLabel("🤖 输出")
        output_title.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title_row.addWidget(output_title)

        title_row.addStretch()

        # 复制按钮
        copy_btn = QPushButton("📄 复制")
        copy_btn.setFixedHeight(24)
        copy_btn.clicked.connect(self._copy_output)
        copy_btn.setStyleSheet(self._get_small_button_style())
        title_row.addWidget(copy_btn)

        # 插入按钮
        insert_btn = QPushButton("📝 插入")
        insert_btn.setFixedHeight(24)
        insert_btn.clicked.connect(self._insert_to_document)
        insert_btn.setStyleSheet(self._get_small_button_style())
        title_row.addWidget(insert_btn)

        # 替换按钮
        replace_btn = QPushButton("🔄 替换")
        replace_btn.setFixedHeight(24)
        replace_btn.clicked.connect(self._replace_in_document)
        replace_btn.setStyleSheet(self._get_small_button_style())
        title_row.addWidget(replace_btn)

        layout.addLayout(title_row)

        # 输出文本框
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(120)  # 设置最小高度
        self.output_text.setPlaceholderText("AI处理结果将显示在这里...")
        self.output_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                line-height: 1.5;
                background-color: #fafbfc;
            }
        """)
        layout.addWidget(self.output_text)

        return section

    def _get_small_button_style(self) -> str:
        """获取小按钮样式"""
        return """
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 10px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """

    # 滚动辅助方法

    def scroll_to_top(self):
        """滚动到顶部"""
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self):
        """滚动到底部"""
        if hasattr(self, 'scroll_area'):
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def scroll_to_input_area(self):
        """滚动到输入区域"""
        if hasattr(self, 'scroll_area'):
            scrollbar = self.scroll_area.verticalScrollBar()
            # 滚动到大约50%的位置
            target_value = int(scrollbar.maximum() * 0.5)
            scrollbar.setValue(target_value)

    def scroll_to_output_area(self):
        """滚动到输出区域"""
        if hasattr(self, 'scroll_area'):
            scrollbar = self.scroll_area.verticalScrollBar()
            # 滚动到大约80%的位置
            target_value = int(scrollbar.maximum() * 0.8)
            scrollbar.setValue(target_value)

    # 缺失的方法实现

    def _copy_output(self):
        """复制输出内容"""
        try:
            from PyQt6.QtWidgets import QApplication
            text = self.output_text.toPlainText()
            if text:
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                self._show_status("已复制到剪贴板", "info")
            else:
                self._show_status("没有内容可复制", "warning")
        except Exception as e:
            logger.error(f"复制失败: {e}")

    def _insert_to_document(self):
        """插入内容到文档"""
        try:
            text = self.output_text.toPlainText().strip()
            if text:
                # 在当前光标位置插入
                self.text_insert_requested.emit(text, self.cursor_position)
                self._show_status(f"已插入 {len(text)} 字符到文档", "success")
            else:
                self._show_status("没有内容可插入", "warning")
        except Exception as e:
            logger.error(f"插入失败: {e}")
            self._show_status(f"插入失败: {str(e)}", "error")

    def _replace_in_document(self):
        """替换文档中的选中内容"""
        try:
            text = self.output_text.toPlainText().strip()
            if text:
                if self.selected_text:
                    # 替换选中的文字
                    self.text_replace_requested.emit(
                        text,
                        self.last_selection_start,
                        self.last_selection_end
                    )
                    self._show_status(f"已替换选中内容 ({len(self.selected_text)} → {len(text)} 字符)", "success")
                else:
                    # 没有选中文字，在当前位置插入
                    self.text_insert_requested.emit(text, self.cursor_position)
                    self._show_status(f"无选中文字，已插入 {len(text)} 字符", "info")
            else:
                self._show_status("没有内容可替换", "warning")
        except Exception as e:
            logger.error(f"替换失败: {e}")
            self._show_status(f"替换失败: {str(e)}", "error")

    def _show_status(self, message: str, status_type: str = "info"):
        """显示状态信息"""
        try:
            if not hasattr(self, 'status_label'):
                return

            # 根据状态类型设置样式
            styles = {
                "info": {"color": "#3498db", "bg": "#e3f2fd"},
                "success": {"color": "#27ae60", "bg": "#d5f4e6"},
                "warning": {"color": "#f39c12", "bg": "#fef9e7"},
                "error": {"color": "#e74c3c", "bg": "#fdeaea"}
            }

            style = styles.get(status_type, styles["info"])

            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {style["color"]};
                    background-color: {style["bg"]};
                    font-size: 11px;
                    padding: 3px 8px;
                    border-radius: 10px;
                }}
            """)

            # 自动清除状态（3秒后）
            if hasattr(self, '_status_timer'):
                self._status_timer.stop()

            self._status_timer = QTimer()
            self._status_timer.singleShot(3000, lambda: self._show_status("就绪", "success"))

        except Exception as e:
            logger.error(f"显示状态失败: {e}")

    def _process_input(self):
        """处理输入内容"""
        text = self.input_text.toPlainText().strip()
        if not text:
            self._show_status("请输入要处理的内容", "warning")
            return

        # 滚动到输出区域
        QTimer.singleShot(200, self.scroll_to_output_area)

        # 根据当前模式选择处理方式
        if self.current_mode == DocumentAIMode.CONTEXT_AWARE:
            self._quick_suggest()
        elif self.current_mode == DocumentAIMode.SELECTION_BASED:
            self._quick_improve()
        elif self.current_mode == DocumentAIMode.DOCUMENT_ANALYSIS:
            self._quick_analyze()
        elif self.current_mode == DocumentAIMode.SMART_WRITING:
            self._quick_continue()

    def _use_selected_text(self):
        """使用选中文本"""
        if self.selected_text:
            self.input_text.setPlainText(self.selected_text)
            self._show_status("已使用选中文本", "info")
            # 滚动到输入区域
            QTimer.singleShot(100, self.scroll_to_input_area)
        else:
            self._show_status("没有选中的文本", "warning")

    def _execute_module_with_text(self, module: AIFunctionModule, text: str):
        """使用指定文本执行模块"""
        try:
            # 使用增强的上下文信息
            context = getattr(self, 'enhanced_context', '') or self.document_context
            request = module.build_request(text, context, {
                "document_id": self.document_id,
                "document_type": getattr(self, 'document_type', 'chapter'),
                "metadata": getattr(self, 'document_metadata', {})
            })
            self._show_status(f"正在执行 {module.metadata.name}...", "info")
            # 使用安全的异步调用方式
            self._schedule_ai_request(request)
        except Exception as e:
            logger.error(f"执行模块失败: {e}")
            self._show_status(f"执行失败: {str(e)}", "error")

    def _execute_module_with_context(self, module: AIFunctionModule, context: str):
        """使用文档上下文执行模块"""
        try:
            # 使用增强的上下文信息
            enhanced_context = getattr(self, 'enhanced_context', '') or context
            request = module.build_request("", enhanced_context, {
                "document_id": self.document_id,
                "document_type": getattr(self, 'document_type', 'chapter'),
                "metadata": getattr(self, 'document_metadata', {})
            })
            self._show_status(f"正在执行 {module.metadata.name}...", "info")
            # 使用安全的异步调用方式
            self._schedule_ai_request(request)
        except Exception as e:
            logger.error(f"执行模块失败: {e}")
            self._show_status(f"执行失败: {str(e)}", "error")

    def _schedule_ai_request(self, request):
        """安全地调度AI请求"""
        try:
            # 检查是否有运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果有事件循环，直接创建任务
                asyncio.create_task(self.process_ai_request(request))
            except RuntimeError:
                # 没有事件循环，使用QTimer延迟执行
                QTimer.singleShot(100, lambda: self._execute_ai_request_sync(request))
        except Exception as e:
            logger.error(f"调度AI请求失败: {e}")
            self._show_status(f"请求调度失败: {str(e)}", "error")

    def _execute_ai_request_sync(self, request):
        """同步执行AI请求（在主线程中）"""
        try:
            # 创建新的事件循环来执行异步请求
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.process_ai_request(request))
                logger.debug(f"AI请求执行完成: {result}")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"同步执行AI请求失败: {e}")
            self._show_status(f"AI请求执行失败: {str(e)}", "error")

    # 文档特定方法

    def set_selected_text(self, text: str):
        """设置选中文本"""
        self.selected_text = text
        if text:
            self._show_status(f"已获取选中文本 ({len(text)} 字符)", "info")

    def set_document_context(self, context: str, document_type: str = "chapter", metadata: dict = None):
        """设置文档上下文 - 增强版本"""
        self.document_context = context
        self.document_type = document_type
        self.document_metadata = metadata or {}

        if context:
            # 构建丰富的上下文信息
            context_info = self._build_enhanced_context()
            self.enhanced_context = context_info
            self._show_status(f"已更新文档上下文 ({len(context)} 字符, 类型: {document_type})", "info")
        else:
            self.enhanced_context = ""

    def _build_enhanced_context(self) -> str:
        """构建增强的上下文信息"""
        if not self.document_context:
            return ""

        context_parts = []

        # 文档类型信息
        doc_type_map = {
            "chapter": "章节",
            "character": "角色档案",
            "setting": "设定文档",
            "outline": "大纲",
            "note": "笔记",
            "research": "资料"
        }
        doc_type_name = doc_type_map.get(self.document_type, self.document_type)
        context_parts.append(f"【文档类型】{doc_type_name}")

        # 文档元数据
        if self.document_metadata:
            if "title" in self.document_metadata:
                context_parts.append(f"【文档标题】{self.document_metadata['title']}")
            if "tags" in self.document_metadata and self.document_metadata["tags"]:
                tags = ", ".join(self.document_metadata["tags"])
                context_parts.append(f"【标签】{tags}")

        # 文档统计信息
        word_count = len(self.document_context)
        context_parts.append(f"【字数】{word_count} 字符")

        # 文档内容
        context_parts.append(f"【文档内容】\n{self.document_context}")

        return "\n".join(context_parts)

    def update_cursor_position(self, position: int):
        """更新光标位置"""
        self.cursor_position = position

    def set_selected_text(self, selected_text: str, start_pos: int = -1, end_pos: int = -1):
        """设置选中文字"""
        self.selected_text = selected_text
        if start_pos >= 0:
            self.last_selection_start = start_pos
        if end_pos >= 0:
            self.last_selection_end = end_pos

        # 发出选中文字更新信号
        self.selection_updated.emit(selected_text)

        # 更新状态显示
        if selected_text:
            self._show_status(f"已选中 {len(selected_text)} 字符", "info")
            # 如果有选中文字，自动填充到输入框
            if hasattr(self, 'input_text') and self.input_text:
                current_input = self.input_text.toPlainText().strip()
                if not current_input:  # 只在输入框为空时自动填充
                    self.input_text.setPlainText(selected_text)
        else:
            self._show_status("无选中文字", "info")

    def get_current_selection_info(self) -> dict:
        """获取当前选中信息"""
        return {
            "text": self.selected_text,
            "start": self.last_selection_start,
            "end": self.last_selection_end,
            "length": len(self.selected_text),
            "cursor_position": self.cursor_position
        }

    def insert_ai_result_to_editor(self, text: str, replace_selection: bool = False):
        """将AI结果插入到编辑器"""
        try:
            if replace_selection and self.selected_text:
                # 替换选中的文字
                self.text_replace_requested.emit(
                    text,
                    self.last_selection_start,
                    self.last_selection_end
                )
                self._show_status(f"已替换选中文字 ({len(self.selected_text)} → {len(text)} 字符)", "success")
            else:
                # 在当前光标位置插入
                self.text_insert_requested.emit(text, self.cursor_position)
                self._show_status(f"已插入 {len(text)} 字符到编辑器", "success")

        except Exception as e:
            logger.error(f"插入AI结果失败: {e}")
            self._show_status(f"插入失败: {str(e)}", "error")

    def _execute_smart_module(self, module):
        """执行智能化AI模块"""
        try:
            # 构建智能化请求
            request = module.build_auto_request(
                context=self.document_context,
                selected_text=self.selected_text,
                parameters={
                    "document_id": self.document_id,
                    "document_type": getattr(self, 'document_type', 'chapter'),
                    "metadata": getattr(self, 'document_metadata', {})
                }
            )

            if request:
                # 执行AI请求
                self._execute_ai_request(request, module.metadata.name)
            else:
                self._show_status("无法构建智能化请求", "error")

        except Exception as e:
            logger.error(f"执行智能化模块失败: {e}")
            self._show_status(f"执行失败: {str(e)}", "error")

    def _execute_ai_request(self, request, function_name: str = "AI功能"):
        """执行AI请求"""
        try:
            self._show_status(f"正在执行 {function_name}...", "info")

            # 调度AI请求到主线程执行
            QTimer.singleShot(0, lambda: self._execute_ai_request_sync(request))

        except Exception as e:
            logger.error(f"调度AI请求失败: {e}")
            self._show_status(f"请求调度失败: {str(e)}", "error")

    # 旧的_create_top_panel方法已被_create_header_section替代
    
    # 旧的UI创建方法已被新的滚动版本替代

    def _create_quick_actions_old(self) -> QWidget:
        """创建快速操作面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(4)
        
        # 第一行：写作辅助
        row1 = QHBoxLayout()
        
        continue_btn = self._create_action_button(
            "➡️ 续写", 
            tooltip="基于当前内容智能续写",
            min_height=32
        )
        continue_btn.clicked.connect(self._quick_continue)
        row1.addWidget(continue_btn)
        
        improve_btn = self._create_action_button(
            "✨ 优化", 
            tooltip="优化选中或输入的文本",
            min_height=32
        )
        improve_btn.clicked.connect(self._quick_improve)
        row1.addWidget(improve_btn)
        
        layout.addLayout(row1)
        
        # 第二行：分析功能
        row2 = QHBoxLayout()
        
        analyze_btn = self._create_action_button(
            "🔍 分析", 
            tooltip="分析文档或选中内容",
            min_height=32
        )
        analyze_btn.clicked.connect(self._quick_analyze)
        row2.addWidget(analyze_btn)
        
        suggest_btn = self._create_action_button(
            "💡 灵感",
            tooltip="智能分析文档内容，自动生成写作灵感",
            min_height=32
        )
        suggest_btn.clicked.connect(self._quick_inspire)
        row2.addWidget(suggest_btn)
        
        layout.addLayout(row2)
        
        return panel
    
    def _create_io_panel_old(self) -> QWidget:
        """创建输入输出面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 标签页组织
        tab_widget = QTabWidget()
        
        # 输入标签页
        input_tab = self._create_input_tab()
        tab_widget.addTab(input_tab, "📝 输入")
        
        # 输出标签页
        output_tab = self._create_output_tab()
        tab_widget.addTab(output_tab, "🤖 输出")
        
        # 上下文标签页
        context_tab = self._create_context_tab()
        tab_widget.addTab(context_tab, "📄 上下文")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    def _create_input_tab_old(self) -> QWidget:
        """创建输入标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 输入区域
        self.input_text = self._create_text_area(
            placeholder="输入要处理的内容，或使用快速操作...",
            max_height=120
        )
        layout.addWidget(self.input_text)
        
        # 输入选项
        options_layout = QHBoxLayout()
        
        # 使用选中文本按钮
        use_selection_btn = self._create_action_button(
            "📋 使用选中", 
            tooltip="使用当前选中的文本",
            min_height=28
        )
        use_selection_btn.clicked.connect(self._use_selected_text)
        options_layout.addWidget(use_selection_btn)
        
        # 使用上下文按钮
        use_context_btn = self._create_action_button(
            "📄 使用上下文", 
            tooltip="使用文档上下文",
            min_height=28
        )
        use_context_btn.clicked.connect(self._use_document_context)
        options_layout.addWidget(use_context_btn)
        
        options_layout.addStretch()
        
        # 处理按钮
        process_btn = self._create_action_button(
            "🚀 处理", 
            tooltip="开始AI处理",
            color=self.theme.PRIMARY_COLOR,
            min_height=28
        )
        process_btn.clicked.connect(self._process_input)
        options_layout.addWidget(process_btn)
        
        layout.addLayout(options_layout)
        
        return tab
    
    def _create_output_tab_old(self) -> QWidget:
        """创建输出标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 输出区域
        self.output_text = self._create_text_area(
            placeholder="AI响应将显示在这里...",
            read_only=True,
            max_height=150
        )
        layout.addWidget(self.output_text)
        
        # 输出操作
        actions_layout = QHBoxLayout()
        
        # 插入按钮
        insert_btn = self._create_action_button(
            "📝 插入", 
            tooltip="在光标位置插入",
            color=self.theme.SUCCESS_COLOR,
            min_height=28
        )
        insert_btn.clicked.connect(self._insert_result)
        actions_layout.addWidget(insert_btn)
        
        # 替换按钮
        replace_btn = self._create_action_button(
            "🔄 替换", 
            tooltip="替换选中内容",
            color=self.theme.PRIMARY_COLOR,
            min_height=28
        )
        replace_btn.clicked.connect(self._replace_result)
        actions_layout.addWidget(replace_btn)
        
        # 复制按钮
        copy_btn = self._create_action_button(
            "📋 复制", 
            tooltip="复制到剪贴板",
            min_height=28
        )
        copy_btn.clicked.connect(self._copy_result)
        actions_layout.addWidget(copy_btn)
        
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        return tab
    
    def _create_context_tab_old(self) -> QWidget:
        """创建上下文标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 上下文显示
        self.context_text = self._create_text_area(
            placeholder="文档上下文将显示在这里...",
            read_only=True,
            max_height=120
        )
        layout.addWidget(self.context_text)
        
        # 上下文信息
        info_layout = QHBoxLayout()
        
        self.context_info_label = QLabel("上下文: 0 字符")
        self.context_info_label.setStyleSheet(f"color: {self.theme.SECONDARY_TEXT_COLOR};")
        info_layout.addWidget(self.context_info_label)
        
        info_layout.addStretch()
        
        # 刷新上下文按钮
        refresh_btn = self._create_action_button(
            "🔄 刷新", 
            tooltip="刷新文档上下文",
            min_height=28
        )
        refresh_btn.clicked.connect(self._refresh_context)
        info_layout.addWidget(refresh_btn)
        
        layout.addLayout(info_layout)
        
        return tab
    
    # 事件处理
    
    def _on_mode_changed(self, text: str):
        """模式变化处理"""
        mode_map = {
            "📄 上下文感知": DocumentAIMode.CONTEXT_AWARE,
            "✂️ 选择处理": DocumentAIMode.SELECTION_BASED,
            "🔍 文档分析": DocumentAIMode.DOCUMENT_ANALYSIS,
            "✍️ 智能写作": DocumentAIMode.SMART_WRITING
        }
        self.current_mode = mode_map.get(text, DocumentAIMode.CONTEXT_AWARE)
        self._show_status(f"切换到{text}模式", "info")
    
    # 快速操作
    
    def _quick_continue(self):
        """智能续写 - 自动基于文档内容续写"""
        module = ai_function_registry.get_module("continue_writing")
        if not module:
            self._show_status("续写功能不可用", "error")
            return

        # 检查是否可以自动执行
        if module.can_auto_execute(self.document_context, self.selected_text):
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化续写
            self._execute_smart_module(module)
            self._show_status("正在智能分析文档内容并续写...", "info")
        else:
            self._show_status("文档内容不足，无法进行智能续写", "warning")

    def _quick_inspire(self):
        """智能灵感 - 自动基于文档内容生成写作灵感"""
        module = ai_function_registry.get_module("writing_inspiration")
        if not module:
            self._show_status("写作灵感功能不可用", "error")
            return

        # 检查是否可以自动执行
        if module.can_auto_execute(self.document_context, self.selected_text):
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化灵感生成
            self._execute_smart_module(module)
            self._show_status("正在智能分析文档内容并生成写作灵感...", "info")
        else:
            self._show_status("文档内容不足，无法生成智能灵感", "warning")

    def _quick_improve(self):
        """智能优化 - 优先优化选中文字"""
        module = ai_function_registry.get_module("text_optimization")
        if not module:
            self._show_status("文本优化功能不可用", "error")
            return

        # 检查是否可以智能执行
        if module.can_auto_execute(self.document_context, self.selected_text):
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化优化
            self._execute_smart_module(module)

            if self.selected_text:
                self._show_status(f"正在智能优化选中的 {len(self.selected_text)} 字符...", "info")
            else:
                self._show_status("正在智能优化文档内容...", "info")
        else:
            # 回退到手动输入模式
            text = self.input_text.toPlainText().strip()
            if text:
                QTimer.singleShot(100, self.scroll_to_output_area)
                self._execute_module_with_text(module, text)
                self._show_status(f"正在优化输入的 {len(text)} 字符...", "info")
            else:
                self._show_status("请选择文字或在输入框中输入要优化的内容", "warning")
    
    def _quick_analyze(self):
        """快速分析"""
        text = self.selected_text or self.document_context
        if not text:
            self._show_status("需要文本内容进行分析", "warning")
            return

        # 滚动到输出区域
        QTimer.singleShot(100, self.scroll_to_output_area)

        # 使用分析模块
        module = ai_function_registry.get_module("content_analysis")
        if module:
            self._execute_module_with_text(module, text)
        else:
            self._show_status("内容分析功能不可用", "error")
    
    def _quick_suggest(self):
        """快速建议"""
        text = self.input_text.toPlainText().strip() or self.document_context
        if not text:
            self._show_status("需要内容获取写作建议", "warning")
            return

        # 滚动到输出区域
        QTimer.singleShot(100, self.scroll_to_output_area)

        # 使用灵感模块
        module = ai_function_registry.get_module("writing_inspiration")
        if module:
            self._execute_module_with_text(module, text)
        else:
            self._show_status("写作建议功能不可用", "error")

    def _quick_dialogue(self):
        """智能对话优化 - 自动优化选中的对话文字"""
        module = ai_function_registry.get_module("dialogue_optimization")
        if not module:
            self._show_status("对话优化功能不可用", "error")
            return

        # 检查是否有选中文字
        if self.selected_text:
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化对话优化
            self._execute_smart_module(module)
            self._show_status(f"正在智能优化选中的对话 ({len(self.selected_text)} 字符)...", "info")
        else:
            # 回退到手动输入模式
            text = self.input_text.toPlainText().strip()
            if text:
                QTimer.singleShot(100, self.scroll_to_output_area)
                self._execute_module_with_text(module, text)
                self._show_status(f"正在优化输入的对话 ({len(text)} 字符)...", "info")
            else:
                self._show_status("请选择对话文字或在输入框中输入对话内容", "warning")

    def _quick_scene(self):
        """智能场景扩展 - 自动扩展选中的场景描写"""
        module = ai_function_registry.get_module("scene_expansion")
        if not module:
            self._show_status("场景扩展功能不可用", "error")
            return

        # 检查是否有选中文字
        if self.selected_text:
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化场景扩展
            self._execute_smart_module(module)
            self._show_status(f"正在智能扩展选中的场景 ({len(self.selected_text)} 字符)...", "info")
        else:
            # 回退到手动输入模式
            text = self.input_text.toPlainText().strip()
            if text:
                QTimer.singleShot(100, self.scroll_to_output_area)
                self._execute_module_with_text(module, text)
                self._show_status(f"正在扩展输入的场景 ({len(text)} 字符)...", "info")
            else:
                self._show_status("请选择场景文字或在输入框中输入场景描述", "warning")

    def _quick_summary(self):
        """智能内容总结 - 自动总结选中文字或整个文档"""
        module = ai_function_registry.get_module("content_summary")
        if not module:
            self._show_status("内容总结功能不可用", "error")
            return

        # 检查是否可以智能化执行
        if module.can_auto_execute(self.document_context, self.selected_text):
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化总结
            self._execute_smart_module(module)
            content_type = "选中内容" if self.selected_text else "整个文档"
            content_length = len(self.selected_text) if self.selected_text else len(self.document_context)
            self._show_status(f"正在智能总结{content_type} ({content_length} 字符)...", "info")
        else:
            # 回退到手动输入模式
            text = self.input_text.toPlainText().strip()
            if text:
                QTimer.singleShot(100, self.scroll_to_output_area)
                self._execute_module_with_text(module, text)
                self._show_status(f"正在总结输入内容 ({len(text)} 字符)...", "info")
            else:
                self._show_status("文档内容不足，请在输入框中输入要总结的内容", "warning")

    def _quick_translate(self):
        """智能翻译 - 自动检测语言并翻译选中文字"""
        module = ai_function_registry.get_module("translation")
        if not module:
            self._show_status("智能翻译功能不可用", "error")
            return

        # 检查是否有选中文字
        if self.selected_text:
            # 滚动到输出区域
            QTimer.singleShot(100, self.scroll_to_output_area)

            # 使用智能化翻译
            self._execute_smart_module(module)
            self._show_status(f"正在智能翻译选中文字 ({len(self.selected_text)} 字符)...", "info")
        else:
            # 回退到手动输入模式
            text = self.input_text.toPlainText().strip()
            if text:
                QTimer.singleShot(100, self.scroll_to_output_area)
                self._execute_module_with_text(module, text)
                self._show_status(f"正在翻译输入内容 ({len(text)} 字符)...", "info")
            else:
                self._show_status("请选择要翻译的文字或在输入框中输入内容", "warning")

    # 工具方法（重复的方法定义已删除，使用上面的版本）

    # 重复的_process_input方法已删除，使用上面的版本
    
    def _use_selected_text(self):
        """使用选中文本"""
        if self.selected_text:
            self.input_text.setPlainText(self.selected_text)
            self._show_status("已使用选中文本", "info")
        else:
            self._show_status("没有选中的文本", "warning")
    
    def _use_document_context(self):
        """使用文档上下文"""
        if self.document_context:
            self.input_text.setPlainText(self.document_context)
            self._show_status("已使用文档上下文", "info")
        else:
            self._show_status("没有文档上下文", "warning")
    
    def _insert_result(self):
        """插入结果"""
        text = self.output_text.toPlainText()
        if text:
            self.text_insert_requested.emit(text)
            self._show_status("已请求插入文本", "success")
        else:
            self._show_status("没有可插入的内容", "warning")
    
    def _replace_result(self):
        """替换结果"""
        text = self.output_text.toPlainText()
        if text:
            self.text_replace_requested.emit(text)
            self._show_status("已请求替换文本", "success")
        else:
            self._show_status("没有可替换的内容", "warning")
    
    def _copy_result(self):
        """复制结果"""
        text = self.output_text.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self._show_status("结果已复制到剪贴板", "success")
        else:
            self._show_status("没有可复制的内容", "warning")
    
    def _refresh_context(self):
        """刷新上下文"""
        if self.document_context:
            self.context_text.setPlainText(self.document_context)
            count = len(self.document_context)
            self.context_info_label.setText(f"上下文: {count} 字符")
            self._show_status("上下文已刷新", "info")
        else:
            self._show_status("没有可用的上下文", "warning")
    
    # 公共接口
    
    def set_selected_text(self, text: str):
        """设置选中文本"""
        self.selected_text = text
        if self.current_mode == DocumentAIMode.SELECTION_BASED:
            self.input_text.setPlainText(text)
    
    # 重复的set_document_context方法已删除，使用上面的版本
    
    def set_cursor_position(self, position: int):
        """设置光标位置"""
        self.cursor_position = position
    
    def get_current_mode(self) -> DocumentAIMode:
        """获取当前模式"""
        return self.current_mode

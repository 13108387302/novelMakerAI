#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局AI面板 - 重构版本

提供统一的全局AI助手功能，支持模块化AI功能和智能建议
"""

import asyncio
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QGroupBox, QComboBox, QScrollArea, QFrame, QGridLayout,
    QSplitter, QTabWidget, QCheckBox, QSpinBox, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from .ai_widget_base import BaseAIWidget, AIWidgetConfig, AIWidgetTheme, AIOutputMode
from .ai_function_modules import ai_function_registry, AIFunctionCategory, AIFunctionModule
from src.application.services.unified_ai_service import UnifiedAIService
from src.application.services.ai.core_abstractions import AIRequestBuilder, AIRequestType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class GlobalAIPanel(BaseAIWidget):
    """
    全局AI面板 - 重构版本
    
    特性：
    - 模块化AI功能
    - 智能功能建议
    - 统一的输入输出界面
    - 支持流式响应
    - 配置和主题支持
    """
    
    # 额外信号
    function_executed = pyqtSignal(str, str)  # function_id, result
    output_mode_changed = pyqtSignal(str)  # mode
    text_insert_requested = pyqtSignal(str)  # 请求插入文本到编辑器
    
    def __init__(
        self,
        ai_service: UnifiedAIService,
        parent: Optional[QWidget] = None,
        config: Optional[AIWidgetConfig] = None
    ):
        # 初始化配置
        if config is None:
            config = AIWidgetConfig()
            config.enable_streaming = True
            config.show_token_count = True
            config.enable_context_awareness = True

        # 🔧 关键修复：在super().__init__()之前设置function_registry
        # 因为BaseAIWidget的初始化会调用_create_ui()，而_create_ui()需要访问function_registry
        try:
            self.function_registry = ai_function_registry
            logger.debug(f"功能注册表已设置，包含 {len(ai_function_registry.get_all_functions())} 个功能")
        except Exception as e:
            logger.error(f"功能注册表设置失败: {e}")
            # 创建空的注册表作为fallback
            try:
                from .ai_function_modules import AIFunctionRegistry
                self.function_registry = AIFunctionRegistry()
                logger.debug("使用空的功能注册表作为fallback")
            except Exception as e2:
                logger.error(f"创建fallback注册表失败: {e2}")
                # 最后的fallback - 创建一个简单的对象
                class EmptyRegistry:
                    def get_all_functions(self):
                        return []
                    def get_modules_by_category(self, category):
                        return []
                self.function_registry = EmptyRegistry()

        self.current_function: Optional[AIFunctionModule] = None

        # 🔧 关键修复：在UI创建之前初始化所有UI组件属性
        # 因为UI创建过程中会访问这些属性
        self.input_text: Optional[QTextEdit] = None
        self.output_text: Optional[QTextEdit] = None
        self.function_buttons: Dict[str, QPushButton] = {}
        self.output_mode_combo: Optional[QComboBox] = None
        self.settings_panel: Optional[QWidget] = None

        # 现在可以安全地调用父类初始化
        try:
            super().__init__(ai_service, "global_ai_panel", parent, config)
            logger.debug("BaseAIWidget初始化完成")
        except Exception as e:
            logger.error(f"BaseAIWidget初始化失败: {e}")
            # 如果父类初始化失败，至少要初始化基本的QWidget
            QWidget.__init__(self, parent)
            # 手动设置必要的属性
            self.ai_service = ai_service
            self.widget_id = "global_ai_panel"
            self.config = config
            self.theme = AIWidgetTheme()
            # 创建基本布局
            self.main_layout = QVBoxLayout(self)
            # 手动调用UI创建
            try:
                self._create_ui()
            except Exception as ui_error:
                logger.error(f"手动UI创建失败: {ui_error}")
                # 创建最简单的UI
                self._create_fallback_ui()
        
        # 状态
        self.current_output_mode = AIOutputMode.REPLACE
        self._accumulated_response = ""
        
        logger.info("全局AI面板初始化完成")

    def _create_fallback_ui(self):
        """创建fallback UI（当正常UI创建失败时使用）"""
        try:
            # 清理现有布局
            if self.main_layout:
                while self.main_layout.count():
                    child = self.main_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

            # 创建简单的UI
            label = QLabel("AI助手正在初始化...")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    padding: 20px;
                    font-size: 14px;
                    color: #666;
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                }
            """)
            self.main_layout.addWidget(label)

            # 添加重试按钮
            retry_btn = QPushButton("🔄 重新初始化")
            retry_btn.clicked.connect(self._retry_initialization)
            retry_btn.setMinimumHeight(35)
            self.main_layout.addWidget(retry_btn)

            logger.debug("Fallback UI创建完成")
        except Exception as e:
            logger.error(f"Fallback UI创建失败: {e}")

    def _retry_initialization(self):
        """重试初始化"""
        try:
            # 重新创建UI
            self._create_ui()
            logger.info("UI重新初始化成功")
        except Exception as e:
            logger.error(f"UI重新初始化失败: {e}")
    
    def _create_ui(self):
        """创建现代化的AI助手界面（带滚动支持）"""
        try:
            logger.debug("开始创建现代化GlobalAIPanel UI（带滚动支持）...")

            # 🎨 新设计：垂直布局，支持滚动
            main_container = QWidget()
            main_layout = QVBoxLayout(main_container)
            main_layout.setContentsMargins(0, 0, 0, 0)  # 移除外边距，由内部组件控制
            main_layout.setSpacing(0)

            # 顶部：标题和快速操作区（固定不滚动）
            header = self._create_header_section()
            main_layout.addWidget(header)

            # 中间：可滚动的主要内容区
            scroll_area = self._create_scrollable_content_area()
            main_layout.addWidget(scroll_area, 1)  # 占据剩余空间

            # 底部：状态和设置区（固定不滚动）
            footer = self._create_footer_section()
            main_layout.addWidget(footer)

            self.main_layout.addWidget(main_container)

            logger.info("✅ 现代化GlobalAIPanel UI创建完成（带滚动支持）")
        except Exception as e:
            logger.error(f"❌ GlobalAIPanel UI创建失败: {e}")
            raise

    def _create_header_section(self) -> QWidget:
        """创建顶部标题和快速操作区"""
        header = QWidget()
        header.setFixedHeight(80)  # 增加高度以容纳边距
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 16, 16, 8)  # 添加适当的边距

        # 左侧：标题和描述
        title_area = QWidget()
        title_layout = QVBoxLayout(title_area)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        # 主标题
        title_label = QLabel("🤖 AI写作助手")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin: 0;
            }
        """)
        title_layout.addWidget(title_label)

        # 副标题
        subtitle_label = QLabel("智能辅助创作，提升写作效率")
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                margin: 0;
            }
        """)
        title_layout.addWidget(subtitle_label)

        layout.addWidget(title_area)
        layout.addStretch()

        # 右侧：快速设置按钮
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setToolTip("AI设置")
        settings_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 16px;
                background-color: #ecf0f1;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d5dbdb;
            }
            QPushButton:pressed {
                background-color: #bdc3c7;
            }
        """)
        layout.addWidget(settings_btn)

        return header

    def _create_scrollable_content_area(self) -> QWidget:
        """创建可滚动的主要内容区域"""
        from PyQt6.QtWidgets import QScrollArea

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许内容自动调整大小
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 禁用水平滚动条
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 需要时显示垂直滚动条

        # 优化滚动体验
        scroll_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 允许键盘焦点
        scroll_area.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)  # 支持触摸滚动

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
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #dee2e6;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
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

        # 保存滚动区域引用，用于后续操作
        self.scroll_area = scroll_area

        return scroll_area

    def _create_scroll_content(self) -> QWidget:
        """创建滚动区域内的内容"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)  # 恢复内边距
        layout.setSpacing(16)

        # 功能选择卡片
        function_card = self._create_function_selection_card()
        layout.addWidget(function_card)

        # 输入输出区域
        io_card = self._create_io_card()
        layout.addWidget(io_card)

        # 添加底部间距，确保内容不会紧贴底部
        layout.addStretch()

        return content

    # 旧的_create_content_area方法已被_create_scrollable_content_area替代

    def _create_footer_section(self) -> QWidget:
        """创建底部状态和设置区"""
        footer = QWidget()
        footer.setFixedHeight(56)  # 增加高度以容纳边距
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 8, 16, 16)  # 添加适当的边距

        # 状态指示器
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #d5f4e6;
                border-radius: 12px;
            }
        """)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 字数统计
        self.word_count_label = QLabel("0 字符")
        self.word_count_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.word_count_label)

        return footer

    def _create_function_selection_card(self) -> QWidget:
        """创建功能选择卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 12px;
                padding: 0;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 卡片标题
        title = QLabel("🎯 选择AI功能")
        title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title)

        # 功能按钮网格
        functions_grid = self._create_functions_grid()
        layout.addWidget(functions_grid)

        return card

    def _create_functions_grid(self) -> QWidget:
        """创建功能按钮网格"""
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        # 定义功能按钮配置（重新组织，更清晰的分类）
        functions = [
            # 第一行：创作辅助
            {"id": "writing_inspiration", "icon": "💡", "title": "写作灵感", "desc": "获取创作建议", "color": "#3498db"},
            {"id": "intelligent_continuation", "icon": "✍️", "title": "智能续写", "desc": "自动续写内容", "color": "#9b59b6"},
            {"id": "content_generation", "icon": "📝", "title": "内容生成", "desc": "生成新内容", "color": "#e67e22"},

            # 第二行：内容优化
            {"id": "text_optimization", "icon": "✨", "title": "文本优化", "desc": "改进表达质量", "color": "#27ae60"},
            {"id": "content_analysis", "icon": "🔍", "title": "内容分析", "desc": "深度分析文本", "color": "#f39c12"},
            {"id": "content_summary", "icon": "📋", "title": "内容总结", "desc": "提取核心要点", "color": "#e74c3c"},
        ]

        # 创建功能按钮
        for i, func in enumerate(functions):
            row = i // 3
            col = i % 3

            btn = self._create_modern_function_button(
                func["icon"],
                func["title"],
                func["desc"],
                func["color"]
            )

            # 绑定点击事件
            btn.clicked.connect(lambda checked, f_id=func["id"]: self._on_function_selected(f_id))

            grid.addWidget(btn, row, col)

        return grid_widget

    def _create_modern_function_button(self, icon: str, title: str, desc: str, color: str) -> QPushButton:
        """创建现代化的功能按钮"""
        btn = QPushButton()
        btn.setFixedSize(140, 80)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # 设置按钮文本（多行）
        btn.setText(f"{icon}\n{title}\n{desc}")

        # 现代化样式（移除Qt不支持的CSS属性）
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: 2px solid #e1e8ed;
                border-radius: 12px;
                font-size: 11px;
                color: #2c3e50;
                text-align: center;
                padding: 8px;
            }}
            QPushButton:hover {{
                border-color: {color};
                background-color: #f0f8ff;
            }}
            QPushButton:pressed {{
                background-color: #e6f3ff;
                border-color: {color};
            }}
            QPushButton:focus {{
                border-color: {color};
            }}
        """)

        return btn

    def _create_io_card(self) -> QWidget:
        """创建输入输出卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 输入区域
        input_section = self._create_input_section()
        layout.addWidget(input_section)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #e1e8ed; }")
        layout.addWidget(separator)

        # 输出区域
        output_section = self._create_output_section()
        layout.addWidget(output_section, 1)

        return card

    def _create_input_section(self) -> QWidget:
        """创建输入区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 输入标题
        input_title = QLabel("📝 输入内容")
        input_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        layout.addWidget(input_title)

        # 输入文本框
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(120)
        self.input_text.setPlaceholderText("请输入需要处理的内容...")
        self.input_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e1e8ed;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
                background-color: #fafbfc;
            }
            QTextEdit:focus {
                border-color: #3498db;
                background-color: white;
            }
        """)
        layout.addWidget(self.input_text)

        # 操作按钮行
        actions_row = self._create_input_actions()
        layout.addWidget(actions_row)

        return section

    def _create_input_actions(self) -> QWidget:
        """创建输入操作按钮行"""
        actions = QWidget()
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 清空按钮
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setFixedHeight(32)
        clear_btn.clicked.connect(lambda: self.input_text.clear())
        clear_btn.setStyleSheet(self._get_secondary_button_style())
        layout.addWidget(clear_btn)

        # 粘贴按钮
        paste_btn = QPushButton("📋 粘贴")
        paste_btn.setFixedHeight(32)
        paste_btn.clicked.connect(self._paste_from_clipboard)
        paste_btn.setStyleSheet(self._get_secondary_button_style())
        layout.addWidget(paste_btn)

        layout.addStretch()

        # 主要执行按钮
        self.execute_btn = QPushButton("🚀 开始处理")
        self.execute_btn.setFixedHeight(36)
        self.execute_btn.setFixedWidth(120)
        self.execute_btn.clicked.connect(self._execute_current_function)
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
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
        layout.addWidget(self.execute_btn)

        return actions

    def _create_output_section(self) -> QWidget:
        """创建输出区域"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 输出标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        output_title = QLabel("🤖 AI响应")
        output_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title_row.addWidget(output_title)

        title_row.addStretch()

        # 复制按钮
        copy_btn = QPushButton("📄 复制")
        copy_btn.setFixedHeight(28)
        copy_btn.clicked.connect(self._copy_output)
        copy_btn.setStyleSheet(self._get_secondary_button_style())
        title_row.addWidget(copy_btn)

        # 插入按钮
        insert_btn = QPushButton("📝 插入")
        insert_btn.setFixedHeight(28)
        insert_btn.clicked.connect(self._insert_to_editor)
        insert_btn.setStyleSheet(self._get_secondary_button_style())
        title_row.addWidget(insert_btn)

        layout.addLayout(title_row)

        # 输出文本框
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(200)  # 设置最小高度，确保有足够的显示空间
        self.output_text.setPlaceholderText("AI处理结果将显示在这里...")
        self.output_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e1e8ed;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
                background-color: #fafbfc;
            }
        """)
        layout.addWidget(self.output_text)

        return section

    def _get_secondary_button_style(self) -> str:
        """获取次要按钮样式"""
        return """
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 12px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """

    def _on_function_selected(self, function_id: str):
        """处理功能选择"""
        try:
            # 更新当前选中的功能
            self.current_function = function_id

            # 更新执行按钮文本
            function_names = {
                "writing_inspiration": "获取灵感",
                "intelligent_continuation": "智能续写",
                "content_generation": "生成内容",
                "text_optimization": "优化文本",
                "content_analysis": "分析内容",
                "content_summary": "总结内容"
            }

            action_name = function_names.get(function_id, "处理")
            self.execute_btn.setText(f"🚀 {action_name}")

            # 更新状态
            self._show_status(f"已选择：{function_names.get(function_id, '未知功能')}", "info")

            # 自动滚动到输入区域，方便用户输入内容
            QTimer.singleShot(100, self.scroll_to_input_area)  # 延迟100ms执行滚动

            logger.debug(f"用户选择AI功能: {function_id}")

        except Exception as e:
            logger.error(f"处理功能选择失败: {e}")

    def _execute_current_function(self):
        """执行当前选中的功能"""
        try:
            if not hasattr(self, 'current_function'):
                self._show_status("请先选择一个AI功能", "warning")
                return

            content = self.input_text.toPlainText().strip()
            if not content:
                self._show_status("请输入需要处理的内容", "warning")
                return

            # 执行选中的功能
            self._execute_ai_function(self.current_function, content)

        except Exception as e:
            logger.error(f"执行AI功能失败: {e}")
            self._show_status(f"执行失败: {str(e)}", "error")

    def _paste_from_clipboard(self):
        """从剪贴板粘贴内容"""
        try:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                self.input_text.setPlainText(text)
                self._show_status("已粘贴剪贴板内容", "info")
            else:
                self._show_status("剪贴板为空", "warning")
        except Exception as e:
            logger.error(f"粘贴失败: {e}")

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

    def _insert_to_editor(self):
        """插入内容到编辑器"""
        try:
            text = self.output_text.toPlainText()
            if text:
                # 发射信号，让主窗口处理插入
                self.text_insert_requested.emit(text)
                self._show_status("已插入到编辑器", "info")
            else:
                self._show_status("没有内容可插入", "warning")
        except Exception as e:
            logger.error(f"插入失败: {e}")

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
                    font-size: 12px;
                    padding: 4px 8px;
                    border-radius: 12px;
                }}
            """)

            # 自动清除状态（5秒后）
            if hasattr(self, '_status_timer'):
                self._status_timer.stop()

            self._status_timer = QTimer()
            self._status_timer.singleShot(5000, lambda: self._show_status("就绪", "success"))

        except Exception as e:
            logger.error(f"显示状态失败: {e}")

    def _execute_ai_function(self, function_id: str, content: str):
        """执行AI功能"""
        try:
            # 映射功能ID到模块名
            function_mapping = {
                "writing_inspiration": "writing_inspiration",
                "intelligent_continuation": "intelligent_continuation",
                "content_generation": "content_generation",
                "text_optimization": "text_optimization",
                "content_analysis": "content_analysis",
                "content_summary": "content_summary"
            }

            module_name = function_mapping.get(function_id)
            if not module_name:
                self._show_status(f"未知功能: {function_id}", "error")
                return

            # 获取功能模块
            module = self.function_registry.get_module(module_name)
            if not module:
                self._show_status(f"功能模块未找到: {module_name}", "error")
                return

            # 构建请求
            request = module.build_request(content, "", {})

            # 更新UI状态
            self._show_status("正在处理中...", "info")
            self.execute_btn.setEnabled(False)
            self.execute_btn.setText("⏳ 处理中...")

            # 滚动到输出区域，让用户看到处理结果
            QTimer.singleShot(200, self.scroll_to_output_area)  # 延迟200ms执行滚动

            # 异步执行请求
            import asyncio
            asyncio.create_task(self._process_ai_request_async(request))

        except Exception as e:
            logger.error(f"执行AI功能失败: {e}")
            self._show_status(f"执行失败: {str(e)}", "error")
            self._reset_execute_button()

    async def _process_ai_request_async(self, request):
        """异步处理AI请求"""
        try:
            # 调用基类的处理方法
            await self.process_ai_request(request)

        except Exception as e:
            logger.error(f"AI请求处理失败: {e}")
            self._show_status(f"处理失败: {str(e)}", "error")
        finally:
            # 恢复按钮状态
            self._reset_execute_button()

    def _reset_execute_button(self):
        """重置执行按钮状态"""
        try:
            self.execute_btn.setEnabled(True)
            if hasattr(self, 'current_function'):
                function_names = {
                    "writing_inspiration": "获取灵感",
                    "intelligent_continuation": "智能续写",
                    "content_generation": "生成内容",
                    "text_optimization": "优化文本",
                    "content_analysis": "分析内容",
                    "content_summary": "总结内容"
                }
                action_name = function_names.get(self.current_function, "处理")
                self.execute_btn.setText(f"🚀 {action_name}")
            else:
                self.execute_btn.setText("🚀 开始处理")
        except Exception as e:
            logger.error(f"重置按钮状态失败: {e}")

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
        if hasattr(self, 'scroll_area') and hasattr(self, 'input_text'):
            # 计算输入区域的大概位置（功能按钮区域之后）
            scrollbar = self.scroll_area.verticalScrollBar()
            # 滚动到大约40%的位置，这通常是输入区域的位置
            target_value = int(scrollbar.maximum() * 0.4)
            scrollbar.setValue(target_value)

    def scroll_to_output_area(self):
        """滚动到输出区域"""
        if hasattr(self, 'scroll_area') and hasattr(self, 'output_text'):
            # 滚动到大约70%的位置，这通常是输出区域的位置
            scrollbar = self.scroll_area.verticalScrollBar()
            target_value = int(scrollbar.maximum() * 0.7)
            scrollbar.setValue(target_value)
    
    # 旧的UI方法已被新设计替代
    
    def _create_category_tab(self, category: AIFunctionCategory, modules: List[AIFunctionModule]) -> QWidget:
        """创建分类标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 功能按钮容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(4)
        
        # 创建功能按钮
        for module in modules:
            if module.is_enabled():
                button = self._create_function_button(module)
                container_layout.addWidget(button)
                self.function_buttons[module.metadata.id] = button
        
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        return tab
    
    def _create_function_button(self, module: AIFunctionModule) -> QPushButton:
        """创建功能按钮"""
        button = QPushButton(f"{module.metadata.icon} {module.metadata.name}")
        button.setToolTip(module.metadata.tooltip)
        button.setMinimumHeight(40)
        button.clicked.connect(lambda: self._execute_function(module))
        
        # 设置按钮样式
        button.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 8px 12px;
                border: 1px solid {self.theme.BORDER_COLOR};
                border-radius: 6px;
                background-color: white;
                color: {self.theme.TEXT_COLOR};
            }}
            QPushButton:hover {{
                background-color: {self.theme.PRIMARY_COLOR}22;
                border-color: {self.theme.PRIMARY_COLOR};
            }}
            QPushButton:pressed {{
                background-color: {self.theme.PRIMARY_COLOR}44;
            }}
        """)
        
        return button
    
    def _create_io_panel(self) -> QWidget:
        """创建输入输出面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 输入区域
        input_group = QGroupBox("📝 输入内容")
        input_layout = QVBoxLayout(input_group)
        
        self.input_text = self._create_text_area(
            placeholder="请输入需要处理的内容...",
            max_height=150
        )
        input_layout.addWidget(self.input_text)
        
        # 输入工具栏
        input_toolbar = QHBoxLayout()
        
        clear_input_btn = self._create_action_button(
            "🗑️ 清空", 
            tooltip="清空输入内容",
            color=self.theme.WARNING_COLOR,
            min_height=28
        )
        clear_input_btn.clicked.connect(self._clear_input)
        input_toolbar.addWidget(clear_input_btn)
        
        paste_btn = self._create_action_button(
            "📋 粘贴", 
            tooltip="粘贴剪贴板内容",
            min_height=28
        )
        paste_btn.clicked.connect(self._paste_from_clipboard)
        input_toolbar.addWidget(paste_btn)
        
        input_toolbar.addStretch()
        
        # 字数统计
        self.input_count_label = QLabel("0 字符")
        self.input_count_label.setStyleSheet(f"color: {self.theme.SECONDARY_TEXT_COLOR};")
        input_toolbar.addWidget(self.input_count_label)
        
        input_layout.addLayout(input_toolbar)
        layout.addWidget(input_group)
        
        # 输出区域
        output_group = QGroupBox("🤖 AI响应")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = self._create_text_area(
            placeholder="AI响应将显示在这里...",
            read_only=True,
            max_height=200
        )
        output_layout.addWidget(self.output_text)
        
        # 输出工具栏
        output_toolbar = QHBoxLayout()
        
        copy_btn = self._create_action_button(
            "📋 复制", 
            tooltip="复制结果到剪贴板",
            color=self.theme.SUCCESS_COLOR,
            min_height=28
        )
        copy_btn.clicked.connect(self._copy_result)
        output_toolbar.addWidget(copy_btn)
        
        apply_btn = self._create_action_button(
            "✅ 应用", 
            tooltip="应用结果到文档",
            color=self.theme.PRIMARY_COLOR,
            min_height=28
        )
        apply_btn.clicked.connect(self._apply_result)
        output_toolbar.addWidget(apply_btn)
        
        clear_output_btn = self._create_action_button(
            "🗑️ 清空", 
            tooltip="清空输出内容",
            color=self.theme.WARNING_COLOR,
            min_height=28
        )
        clear_output_btn.clicked.connect(self._clear_output)
        output_toolbar.addWidget(clear_output_btn)
        
        output_toolbar.addStretch()
        
        # 输出字数统计
        self.output_count_label = QLabel("0 字符")
        self.output_count_label.setStyleSheet(f"color: {self.theme.SECONDARY_TEXT_COLOR};")
        output_toolbar.addWidget(self.output_count_label)
        
        output_layout.addLayout(output_toolbar)
        layout.addWidget(output_group)
        
        # 连接输入文本变化信号
        self.input_text.textChanged.connect(self._update_input_count)
        
        return panel
    
    def _get_category_display_name(self, category: AIFunctionCategory) -> str:
        """获取分类显示名称"""
        names = {
            AIFunctionCategory.WRITING: "✍️ 写作",
            AIFunctionCategory.ANALYSIS: "🔍 分析", 
            AIFunctionCategory.OPTIMIZATION: "✨ 优化",
            AIFunctionCategory.TRANSLATION: "🌐 翻译",
            AIFunctionCategory.CREATIVE: "💡 创意",
            AIFunctionCategory.UTILITY: "🔧 工具"
        }
        return names.get(category, category.value)
    
    # 事件处理
    
    def _execute_function(self, module: AIFunctionModule):
        """执行AI功能"""
        if self.is_busy():
            self._show_status("AI正在处理中，请稍候", "warning")
            return
        
        # 获取输入内容
        input_text = self.input_text.toPlainText().strip()
        
        # 验证输入
        is_valid, error_msg = module.validate_input(input_text)
        if not is_valid:
            self._show_status(error_msg, "warning")
            return
        
        # 设置当前功能
        self.current_function = module
        
        # 构建请求
        try:
            request = module.build_request(input_text, "", {})
            
            # 清空输出（如果配置允许）
            if self.config.auto_clear_on_new_request:
                self._clear_output()
            
            # 执行请求
            self._show_status(f"正在执行 {module.metadata.name}...", "info")
            asyncio.create_task(self._process_function_request(request, module))
            
        except Exception as e:
            logger.error(f"执行AI功能失败: {e}")
            self._show_status(f"执行失败: {str(e)}", "error")
    
    async def _process_function_request(self, request, module: AIFunctionModule):
        """处理功能请求"""
        try:
            # 重置累积响应
            self._accumulated_response = ""
            
            # 处理请求
            stream = self.config.enable_streaming and module.metadata.supports_streaming
            await self.process_ai_request(request, stream)
            
        except Exception as e:
            logger.error(f"处理功能请求失败: {e}")
            self._show_status(f"处理失败: {str(e)}", "error")
    
    def _on_ai_response_received(self, content: str):
        """AI响应接收完成"""
        self.output_text.setPlainText(content)
        self._update_output_count()
        
        if self.current_function:
            self.function_executed.emit(self.current_function.metadata.id, content)
            self._show_status(f"{self.current_function.metadata.name} 完成", "success")
        else:
            self._show_status("AI处理完成", "success")
    
    def _on_ai_stream_chunk(self, chunk: str):
        """AI流式数据块"""
        self._accumulated_response += chunk
        self.output_text.setPlainText(self._accumulated_response)
        
        # 滚动到底部
        cursor = self.output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        
        self._update_output_count()
    
    def _on_ai_stream_completed(self):
        """AI流式响应完成"""
        if self.current_function:
            self.function_executed.emit(self.current_function.metadata.id, self._accumulated_response)
            self._show_status(f"{self.current_function.metadata.name} 完成", "success")
        else:
            self._show_status("AI处理完成", "success")
    
    # 工具方法
    
    def _update_input_count(self):
        """更新输入字数统计"""
        text = self.input_text.toPlainText()
        count = len(text)
        self.input_count_label.setText(f"{count} 字符")
    
    def _update_output_count(self):
        """更新输出字数统计"""
        text = self.output_text.toPlainText()
        count = len(text)
        self.output_count_label.setText(f"{count} 字符")
    
    def _clear_input(self):
        """清空输入"""
        self.input_text.clear()
        self._show_status("输入已清空", "info")
    
    def _clear_output(self):
        """清空输出"""
        self.output_text.clear()
        self._accumulated_response = ""
        self._update_output_count()
        self._show_status("输出已清空", "info")
    
    def _paste_from_clipboard(self):
        """从剪贴板粘贴"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.input_text.setPlainText(text)
            self._show_status("已粘贴剪贴板内容", "info")
        else:
            self._show_status("剪贴板为空", "warning")
    
    def _copy_result(self):
        """复制结果"""
        text = self.output_text.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self._show_status("结果已复制到剪贴板", "success")
        else:
            self._show_status("没有可复制的内容", "warning")
    
    def _apply_result(self):
        """应用结果"""
        text = self.output_text.toPlainText()
        if text:
            self.content_ready.emit(text, self.current_output_mode.value)
            self._show_status("结果已应用", "success")
        else:
            self._show_status("没有可应用的内容", "warning")
    
    def _on_output_mode_changed(self, text: str):
        """输出模式变化"""
        mode_map = {
            "替换内容": AIOutputMode.REPLACE,
            "插入到光标": AIOutputMode.INSERT,
            "追加到末尾": AIOutputMode.APPEND,
            "新建文档": AIOutputMode.NEW_DOCUMENT
        }
        self.current_output_mode = mode_map.get(text, AIOutputMode.REPLACE)
        self.output_mode_changed.emit(self.current_output_mode.value)
    
    def _on_stream_toggle(self, enabled: bool):
        """流式输出开关"""
        self.config.enable_streaming = enabled
        self._show_status(f"流式输出已{'启用' if enabled else '禁用'}", "info")
    
    # 公共接口
    
    def set_input_text(self, text: str):
        """设置输入文本"""
        self.input_text.setPlainText(text)
    
    def get_output_text(self) -> str:
        """获取输出文本"""
        return self.output_text.toPlainText()
    
    def clear_all(self):
        """清空所有内容"""
        self._clear_input()
        self._clear_output()
    
    def get_current_output_mode(self) -> AIOutputMode:
        """获取当前输出模式"""
        return self.current_output_mode

    def set_context_text(self, context: str):
        """设置上下文文本（用于文档级AI功能）"""
        # 全局面板通常不需要上下文，但保留接口兼容性
        pass

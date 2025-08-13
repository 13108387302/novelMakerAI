#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化AI组件

提供现代化设计的AI界面组件
"""

import logging
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QPushButton, QFrame, QScrollArea, QGroupBox, QGraphicsDropShadowEffect,
    QProgressBar, QSizePolicy, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QGuiApplication

from src.presentation.styles.ai_panel_styles import (
    get_complete_ai_style, SPECIAL_BUTTON_STYLES, COLORS
)
from ..utils.ai_config_validator import AIConfigValidator

logger = logging.getLogger(__name__)


class ModernAIWidget(QWidget):
    """现代化AI组件基类"""

    # 信号定义
    ai_request = pyqtSignal(str, dict)  # AI请求信号
    status_changed = pyqtSignal(str, str)  # 状态变化信号
    # 应用到编辑器（兼容旧连接）
    text_applied = pyqtSignal(str)
    # 更精细的写回信号
    text_insert_requested = pyqtSignal(str, int)  # 文本、插入位置（-1=当前光标）
    text_replace_requested = pyqtSignal(str, int, int)  # 文本、起止位置

    # 线程安全的UI更新信号
    ui_update_signal = pyqtSignal(str)  # 用于线程安全的UI更新
    # 上下文来源提示
    context_source_changed = pyqtSignal(str)

    def __init__(self, parent=None, settings_service=None):
        super().__init__(parent)
        self.selected_text = ""
        self.document_context = ""
        self.document_type = "chapter"
        self.document_metadata = {}
        self._cursor_position: Optional[int] = None  # 用于局部上下文提取

        # AI服务引用
        self.ai_orchestration_service = None
        self.ai_intelligence_service = None

        # 设置服务
        self.settings_service = settings_service

        # 设置基础属性
        self._setup_widget_properties()

        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建滚动区域
        self._create_scroll_area()

        # 应用样式
        self._apply_modern_styles()

        # 密度/间距设置
        self._density = self._get_setting('ai.density', 'comfortable')
        self._apply_density_from_settings()

        # 尝试获取AI服务
        self._initialize_ai_services()

        # 连接线程安全的UI更新信号
        self.ui_update_signal.connect(self._handle_ui_update)

        # 初始化文档上下文管理器
        self._initialize_context_manager()

        # 兼容旧版上下文更新接口
        self._current_document_id: Optional[str] = None

        logger.debug("现代化AI组件初始化完成")

    def _setup_widget_properties(self):
        """设置组件属性"""
        self.setObjectName("ModernAIWidget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def _create_scroll_area(self):
        """创建滚动区域"""
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # 创建滚动内容容器
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(16, 16, 16, 16)
        self.scroll_layout.setSpacing(16)

        # 设置滚动内容
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

    def _apply_modern_styles(self):
        """交由 ThemeManager 的全局样式控制，避免面板覆盖主题"""
        return

    def _get_setting(self, key: str, default=None):
        try:
            if self.settings_service:
                return self.settings_service.get(key, default)
        except Exception:
            pass
        return default

    def _apply_density_from_settings(self):
        try:
            density = (self._density or 'comfortable').lower()
            if density not in ('comfortable', 'compact'):
                density = 'comfortable'
            if density == 'compact':
                margins = (8, 8, 8, 8)
                spacing = 8
            else:
                margins = (16, 16, 16, 16)
                spacing = 16
            if hasattr(self, 'scroll_layout') and self.scroll_layout:
                self.scroll_layout.setContentsMargins(*margins)
                self.scroll_layout.setSpacing(spacing)
        except Exception:
            pass

    def _initialize_ai_services(self):
        """初始化AI服务"""
        try:
            # 尝试从全局容器获取AI服务
            from src.presentation.widgets.ai.refactored import get_ai_widget_factory
            factory = get_ai_widget_factory()

            if factory:
                self.ai_orchestration_service = factory.ai_orchestration_service
                self.ai_intelligence_service = factory.ai_intelligence_service
                logger.debug("✅ AI服务连接成功")
            else:
                logger.warning("⚠️ AI组件工厂未找到")

        except Exception as e:
            logger.warning(f"⚠️ AI服务初始化失败: {e}")

    def set_ai_services(self, ai_orchestration_service, ai_intelligence_service):
        """设置AI服务（外部调用）"""
        self.ai_orchestration_service = ai_orchestration_service
        self.ai_intelligence_service = ai_intelligence_service
        logger.debug("✅ AI服务已设置")

    def _initialize_context_manager(self):
        """初始化文档上下文管理器"""
        try:
            from src.application.services.ai.intelligence.document_context_manager import DocumentContextManager

            self.context_manager = DocumentContextManager()

            # 注册当前组件
            component_id = f"ai_widget_{id(self)}"
            self.context_manager.register_ai_component(component_id, self)

            # 添加上下文更新回调
            self.context_manager.add_update_callback(self._on_context_updated_callback)

            logger.debug("文档上下文管理器初始化成功")

        except Exception as e:
            logger.warning(f"文档上下文管理器初始化失败: {e}")
            self.context_manager = None

    def create_modern_button(self, text: str, icon: str = "", style_type: str = "default",
                           tooltip: str = "", callback=None) -> QPushButton:
        """
        创建现代化按钮

        Args:
            text: 按钮文本
            icon: 图标（emoji或图标字符）
            style_type: 样式类型 (default, writing, inspiration, optimization, analysis)
            tooltip: 工具提示
            callback: 点击回调函数
        """
        button = QPushButton(f"{icon} {text}" if icon else text)
        button.setToolTip(tooltip or text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        # 使用主题强调样式，移除内联QSS
        if style_type and style_type != "default":
            button.setProperty("accent", True)
            button.setStyleSheet("")

        # 连接回调
        if callback:
            button.clicked.connect(callback)

        # 添加悬停动画效果
        self._add_button_animation(button)
        return button

    def create_quick_actions_bar(self) -> QGroupBox:
        """创建统一的快捷执行区（根据可用槽函数自动装配）"""
        box = QGroupBox("⚡ 快捷操作")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 读取配置以过滤展示项（逗号分隔），为空表示全部
        cfg = str(self._get_setting('ai.quick_actions', '') or '').strip()
        allow: Optional[set] = None
        if cfg:
            allow = {n.strip() for n in cfg.split(',') if n.strip()}

        def maybe_add_btn(title, icon, slot_name, style="writing"):
            if allow is not None and title not in allow:
                return
            slot = getattr(self, slot_name, None)
            if callable(slot):
                btn = self.create_modern_button(title, icon, style, title, slot)
                btn.setMinimumHeight(28)
                layout.addWidget(btn)

        # 文档常用
        maybe_add_btn("智能续写", "📝", "_on_smart_continue")
        maybe_add_btn("内容扩展", "📖", "_on_content_expand")
        maybe_add_btn("对话生成", "💬", "_on_dialogue_generation")
        maybe_add_btn("场景描写", "🎭", "_on_scene_description")
        maybe_add_btn("语言润色", "✨", "_on_language_polish")
        # 全局常用（若存在）
        maybe_add_btn("大纲生成", "🧭", "_on_outline_generation")
        maybe_add_btn("人物设定", "👤", "_on_character_creation")
        maybe_add_btn("世界观", "🌍", "_on_worldbuilding")
        maybe_add_btn("智能命名", "🏷️", "_on_smart_naming")

        layout.addStretch()
        return box

    def create_context_source_badge(self) -> QLabel:
        """创建上下文来源提示徽章"""
        label = QLabel("上下文来源: 未知")
        # 颜色与背景交由主题
        # 连接信号
        try:
            self.context_source_changed.connect(lambda src: label.setText(f"上下文来源: {src}"))
        except Exception:
            pass
        return label

    def _add_button_animation(self, button: QPushButton):
        """为按钮添加动画效果"""
        # 这里可以添加更复杂的动画效果
        # 目前通过CSS的hover效果实现
        pass

    def create_modern_group(self, title: str, icon: str = "") -> QGroupBox:
        """
        创建现代化组框

        Args:
            title: 组框标题
            icon: 图标
        """
        group = QGroupBox(f"{icon} {title}" if icon else title)
        group.setObjectName("ModernGroup")

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 1)
        group.setGraphicsEffect(shadow)

        return group

    def create_status_indicator(self, text: str = "就绪", status: str = "info") -> QLabel:
        """
        创建状态指示器

        Args:
            text: 状态文本
            status: 状态类型 (success, warning, error, info)
        """
        indicator = QLabel(text)
        indicator.setProperty("status", status)
        indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        indicator.setObjectName("StatusIndicator")

        return indicator

    def create_output_area(self, placeholder: str = "AI响应将显示在这里...") -> QScrollArea:
        """创建带滚动条的输出区域"""
        from PyQt6.QtWidgets import QScrollArea

        density = (self._density or 'comfortable').lower() if hasattr(self, '_density') else 'comfortable'
        if density not in ('comfortable', 'compact'):
            density = 'comfortable'
        # 不同密度的高度建议
        if density == 'compact':
            text_min = 120
            area_min, area_max = 160, 320
        else:
            text_min = 150
            area_min, area_max = 200, 400

        # 创建文本编辑器
        output_text = QTextEdit()
        output_text.setPlaceholderText(placeholder)
        output_text.setReadOnly(True)
        output_text.setMinimumHeight(text_min)
        output_text.setObjectName("OutputText")

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(output_text)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(area_min)
        scroll_area.setMaximumHeight(area_max)
        scroll_area.setObjectName("OutputArea")

        # 保存文本编辑器的引用，用于更新内容
        scroll_area.output_text = output_text
        return scroll_area
    def create_output_toolbar(self) -> QHBoxLayout:
        """创建输出区上方的写回方式工具条"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.apply_insert_btn = QPushButton("插入到光标处")
        self.apply_replace_btn = QPushButton("替换选中内容")
        self.apply_append_btn = QPushButton("追加到文尾")
        for b in (self.apply_insert_btn, self.apply_replace_btn, self.apply_append_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            # 按钮样式交由主题
        layout.addWidget(self.apply_insert_btn)
        layout.addWidget(self.apply_replace_btn)
        layout.addWidget(self.apply_append_btn)
        layout.addStretch()

        # 常用操作
        self.copy_output_btn = QPushButton("复制结果")
        self.copy_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_output_btn = QPushButton("清空结果")
        self.clear_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.copy_output_btn)
        layout.addWidget(self.clear_output_btn)

        # 视图控制
        self.toggle_collapse_btn = QPushButton("折叠输出")
        self.toggle_collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_maximize_btn = QPushButton("最大化")
        self.toggle_maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.toggle_collapse_btn)
        layout.addWidget(self.toggle_maximize_btn)

        # 撤销提示标签（临时显示）
        self.undo_hint = QLabel("")
        # 文字样式交由主题
        layout.addWidget(self.undo_hint)

        # 连接点击行为 -> 发出写回信号
        def _get_output_text() -> str:
            try:
                if hasattr(self, 'output_area') and hasattr(self.output_area, 'output_text'):
                    return self.output_area.output_text.toPlainText()
            except Exception:
                return ""
            return ""

        self.apply_insert_btn.clicked.connect(lambda: self._emit_apply_insert(_get_output_text()))
        self.apply_replace_btn.clicked.connect(lambda: self._emit_apply_replace(_get_output_text()))
        self.apply_append_btn.clicked.connect(lambda: self._emit_apply_append(_get_output_text()))
        self.copy_output_btn.clicked.connect(self._copy_output_text)
        self.clear_output_btn.clicked.connect(self._clear_output_text)
        self.toggle_collapse_btn.clicked.connect(self._toggle_output_collapsed)
        self.toggle_maximize_btn.clicked.connect(self._open_output_max_view)
        return layout

    def _emit_apply_insert(self, text: str):
        if text.strip():
            self.text_insert_requested.emit(text, -1)
            self._show_undo_hint("已插入，可按Ctrl+Z撤销")

    def _emit_apply_replace(self, text: str):
        if text.strip():
            # 用 (-1,-1) 让 MainWindow 使用当前选择范围
            self.text_replace_requested.emit(text, -1, -1)
            self._show_undo_hint("已替换，可按Ctrl+Z撤销")

    def _emit_apply_append(self, text: str):
        if text.strip():
            # 约定 position=-2 表示追加到文尾，由 MainWindow 侧处理
            self.text_insert_requested.emit(text + "\n", -2)
            self._show_undo_hint("已追加到文尾，可按Ctrl+Z撤销")

    def _show_undo_hint(self, msg: str):
        try:
            self.undo_hint.setText(msg)
            QTimer.singleShot(3000, lambda: self.undo_hint.setText(""))
        except Exception:
            pass

    def _toggle_output_collapsed(self):
        try:
            if not hasattr(self, '_output_collapsed'):
                self._output_collapsed = False
            self._output_collapsed = not self._output_collapsed
            if hasattr(self, 'output_area') and self.output_area:
                self.output_area.setVisible(not self._output_collapsed)
            self.toggle_collapse_btn.setText("展开输出" if self._output_collapsed else "折叠输出")
        except Exception as e:
            logger.warning(f"切换输出折叠失败: {e}")

    def _open_output_max_view(self):
        try:
            # 快速只读查看对话框
            dlg = QDialog(self)
            dlg.setWindowTitle("AI输出 - 最大化查看")
            v = QVBoxLayout(dlg)
            view = QTextEdit()
            view.setReadOnly(True)
            text = ""
            try:
                if hasattr(self, 'output_area') and hasattr(self.output_area, 'output_text'):
                    text = self.output_area.output_text.toPlainText()
            except Exception:
                pass
            view.setPlainText(text)
            v.addWidget(view)
            btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            btns.rejected.connect(dlg.reject)
            btns.accepted.connect(dlg.accept)
            v.addWidget(btns)
            dlg.resize(900, 650)
            dlg.exec()
        except Exception as e:
            logger.warning(f"打开最大化查看失败: {e}")

    def _copy_output_text(self):
        try:
            if hasattr(self, 'output_area') and hasattr(self.output_area, 'output_text'):
                text = self.output_area.output_text.toPlainText()
                if text:
                    QGuiApplication.clipboard().setText(text)
                    self._show_undo_hint("已复制结果到剪贴板")
        except Exception as e:
            logger.warning(f"复制结果失败: {e}")

    def _clear_output_text(self):
        try:
            self._clear_output()
            self._show_undo_hint("已清空结果")
        except Exception as e:
            logger.warning(f"清空结果失败: {e}")


    def create_chat_interface(self) -> QWidget:
        """创建聊天界面"""
        # 创建聊天容器
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(8)

        # 创建聊天历史显示区域
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(250)
        self.chat_history.setPlaceholderText("对话历史将显示在这里...")

        # 设置聊天历史样式
        font = QFont("Microsoft YaHei UI", 10)
        self.chat_history.setFont(font)
        # 外观交由主题

        chat_layout.addWidget(self.chat_history)

        # 创建输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        # 创建输入文本框
        self.chat_input = QTextEdit()
        self.chat_input.setMaximumHeight(80)
        self.chat_input.setPlaceholderText("在这里输入您的问题...")
        self.chat_input.setFont(font)
        # 外观交由主题

        # 创建发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.setMinimumSize(80, 40)
        self.send_button.setProperty("accent", True)
        self.send_button.setStyleSheet("")

        # 创建清空按钮
        self.clear_chat_button = QPushButton("清空")
        self.clear_chat_button.setMinimumSize(60, 40)
        # 外观由主题控制
        self.clear_chat_button.setStyleSheet("")

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.clear_chat_button)

        chat_layout.addLayout(input_layout)

        # 连接信号
        self.send_button.clicked.connect(self._on_send_chat_message)
        self.clear_chat_button.clicked.connect(self._on_clear_chat)
        self.chat_input.textChanged.connect(self._on_chat_input_changed)

        # 支持回车发送
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeySequence, QShortcut
        send_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.chat_input)
        send_shortcut.activated.connect(self._on_send_chat_message)

        # 初始化聊天历史
        self.conversation_history = []

        return chat_container

    def create_button_row(self, buttons: List[QPushButton]) -> QHBoxLayout:
        """创建按钮行布局"""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        for button in buttons:
            layout.addWidget(button)

        layout.addStretch()  # 添加弹性空间
        return layout

    def create_card_frame(self) -> QFrame:
        """创建卡片框架"""
        frame = QFrame()
        frame.setObjectName("CardFrame")
        frame.setFrameShape(QFrame.Shape.Box)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 2)
        frame.setGraphicsEffect(shadow)

        return frame

    def show_status(self, message: str, status_type: str = "info"):
        """
        显示状态信息

        Args:
            message: 状态消息
            status_type: 状态类型 (success, warning, error, info)
        """
        # 发射状态变化信号
        self.status_changed.emit(message, status_type)

        # 如果有状态指示器，更新它
        if hasattr(self, 'status_indicator'):
            self.status_indicator.setText(message)
            self.status_indicator.setProperty("status", status_type)
            # 强制刷新样式
            self.status_indicator.style().unpolish(self.status_indicator)
            self.status_indicator.style().polish(self.status_indicator)

        logger.info(f"状态更新: {message} ({status_type})")

    def add_to_layout(self, widget: QWidget):
        """添加组件到滚动布局"""
        self.scroll_layout.addWidget(widget)

    def add_stretch(self):
        """添加弹性空间"""
        self.scroll_layout.addStretch()

    def add_layout(self, layout: QHBoxLayout):
        """添加布局到滚动内容区域"""
        try:
            self.scroll_layout.addLayout(layout)
        except Exception as e:
            logger.warning(f"添加布局失败: {e}")

    def set_selected_text(self, text: str):
        """设置选中文本"""
        self.selected_text = text
        logger.debug(f"设置选中文本: {len(text)} 字符")

    # ===== 兼容旧版/外部调用的上下文接口 =====
    def set_context(self, document_context: str = "", selected_text: str = "", document_id: Optional[str] = None, document_type: str = "chapter"):
        self.document_context = document_context or ""
        self.selected_text = selected_text or ""
        self._current_document_id = document_id
        self.document_type = document_type or "chapter"

    def update_document_context_external(self, document_id: Optional[str], content: str, selected_text: str = "", document_type: Optional[str] = None) -> None:
        try:
            if document_type is None:
                document_type = self.document_type or "chapter"
            self.set_context(
                document_context=content or "",
                selected_text=selected_text or "",
                document_id=document_id,
                document_type=document_type,
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"更新AI上下文失败: {e}")


    def set_document_context(self, content: str, doc_type: str = "chapter", metadata: dict = None):
        """设置文档上下文"""
        if metadata is None:
            metadata = {}

        self.document_context = content
        self.document_type = doc_type
        self.document_metadata = metadata

        logger.debug(f"设置文档上下文: {len(content)} 字符, 类型: {doc_type}")

        # 如果有AI面板，更新其上下文
        if hasattr(self, 'ai_panel') and self.ai_panel:
            try:
                if hasattr(self.ai_panel, 'set_document_info'):
                    # 对于文档AI面板，设置文档信息
                    document_id = metadata.get('id', 'unknown')
                    self.ai_panel.set_document_info(document_id, doc_type)
                elif hasattr(self.ai_panel, 'set_document_context'):
                    # 对于其他AI面板，设置上下文
                    self.ai_panel.set_document_context(content)
            except Exception as e:
                logger.debug(f"更新AI面板上下文失败: {e}")

    def execute_ai_request(self, function_name: str, prompt: str, options: dict = None):
        """
        执行AI请求

        Args:
            function_name: 功能名称
            prompt: 提示词
            options: 选项参数
        """
        if options is None:
            options = {}

        # 添加基础信息
        options.update({
            'function_name': function_name,
            'selected_text': self.selected_text,
            'document_context': self.document_context
        })

        # 发射AI请求信号
        self.ai_request.emit(prompt, options)

        # 显示处理状态
        self.show_status(f"正在执行 {function_name}...", "info")

        # 使用QTimer延迟执行异步请求，避免事件循环问题
        QTimer.singleShot(10, lambda: self._schedule_ai_request(function_name, prompt, options))

        logger.info(f"执行AI请求: {function_name}")

    def _schedule_ai_request(self, function_name: str, prompt: str, options: dict):
        """调度AI请求执行 - 线程安全版本"""
        try:
            # 使用异步管理器执行AI请求
            from src.shared.utils.async_manager import get_async_manager
            async_manager = get_async_manager()

            # 定义成功回调
            def on_success(result):
                # 在主线程中更新UI
                self.show_status(f"{function_name} 完成", "success")
                if result:
                    self._display_ai_response(result)

            # 定义错误回调
            def on_error(error):
                # 在主线程中更新UI
                self.show_status(f"{function_name} 失败", "error")
                self._display_ai_response(f"❌ 执行失败: {str(error)}")

            # 执行异步任务
            async_manager.execute_async(
                self._process_ai_request_async(function_name, prompt, options),
                success_callback=on_success,
                error_callback=on_error
            )

        except Exception as e:
            logger.error(f"调度AI请求失败: {e}")
            self.show_status(f"{function_name} 调度失败", "error")
            self._display_ai_response(f"❌ 调度失败: {str(e)}")

    async def _process_ai_request_async(self, function_name: str, prompt: str, options: dict):
        """异步处理AI请求"""
        try:
            # 检查AI服务状态
            service_status = self._check_ai_service_status()
            if not service_status['available']:
                self.show_status("AI服务不可用", "error")
                self._display_ai_response(f"❌ {service_status['message']}")
                return

            # 构建完整的提示词
            full_prompt = self._build_full_prompt(function_name, prompt, options)

            # 检查是否启用流式输出
            use_streaming = self._get_streaming_preference()

            # 创建AI请求
            from src.domain.ai.entities.ai_request import AIRequest
            from src.domain.ai.value_objects.ai_priority import AIPriority
            from src.domain.ai.value_objects.ai_request_type import AIRequestType
            request = AIRequest(
                prompt=full_prompt,
                context=self.document_context,
                request_type=AIRequestType.TEXT_GENERATION,
                priority=AIPriority.NORMAL,
                parameters=options,
                metadata={'function_name': function_name},
                is_streaming=use_streaming
            )

            # 处理请求
            if use_streaming:
                await self._process_streaming_request(request, function_name, options)
            else:
                response = await self.ai_orchestration_service.process_request(request)
                self._handle_ai_response(response, function_name, options)

        except Exception as e:
            logger.error(f"AI请求处理失败: {e}")
            # 在主线程中更新UI
            error_msg = f"❌ 处理失败: {str(e)}"
            QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 失败", "error"))
            QTimer.singleShot(0, lambda: self._display_ai_response(error_msg))

    def _build_full_prompt(self, function_name: str, prompt: str, options: dict) -> str:
        """构建完整的提示词"""
        # 基础提示词
        full_prompt = f"任务: {function_name}\n\n"

        # 根据功能类型选择上下文拼接策略
        func_type = (options or {}).get('type', '').lower()

        def _extract_local_context(before: int = 400, after: int = 120) -> str:
            text = self.document_context or ""
            if not text:
                return ""
            pos = self._cursor_position
            if pos is None or pos < 0 or pos > len(text):
                return text[-(before + after):]
            start = max(0, pos - before)
            end = min(len(text), pos + after)
            return text[start:end]

        source = None
        if self.selected_text:
            full_prompt += f"选中文本:\n{self.selected_text}\n\n"
            source = "选中内容"
        elif func_type in {"continue", "dialogue", "scene"}:
            local_ctx = _extract_local_context()
            if local_ctx:
                full_prompt += f"附近上下文片段:\n{local_ctx}\n\n"
                source = "光标附近"
            elif self.document_context:
                full_prompt += f"文档上下文:\n{self.document_context[:1000]}...\n\n"
                source = "文档摘要"
        else:
            if self.document_context:
                full_prompt += f"文档上下文:\n{self.document_context[:1000]}...\n\n"
                source = "文档摘要"

        # 发射上下文来源提示
        try:
            if source:
                self.context_source_changed.emit(source)
        except Exception:
            pass

        # 添加具体指令
        full_prompt += f"指令:\n{prompt}\n\n"

        # 添加功能特定的指导
        function_guides = {
            "ai_chat": "请以友好、专业的方式回答用户的问题。",
            "translate": "请将文本翻译成中文，保持原意和语调。",
            "summary": "请生成简洁明了的摘要，突出要点。",
            "smart_continue": "请基于上下文智能续写，保持风格一致。",
            "content_expand": "请扩展内容，增加细节描述，使文本更生动。",
            "dialogue_generation": "请生成符合角色性格的对话。",
            "scene_description": "请生成生动的场景描写。",
            "language_polish": "请优化文字表达，提升文学性。",
            "outline_generation": "请生成详细的小说大纲。",
            "character_creation": "请创建详细的角色设定。"
        }

        guide = function_guides.get(function_name, "请根据指令完成任务。")
        full_prompt += f"要求: {guide}"

        return full_prompt

    def update_cursor_position(self, position: int) -> None:
        """由编辑器通知光标位置，便于提取局部上下文"""
        try:
            self._cursor_position = int(position)
        except Exception:
            self._cursor_position = None

    def _display_ai_response(self, content: str):
        """显示AI响应 - 统一使用流式输出方法"""
        logger.debug(f"🎯 _display_ai_response 被调用，内容长度: {len(content)}")

        # 如果是聊天模式且有聊天历史组件，添加到聊天历史
        if hasattr(self, 'chat_history') and hasattr(self, 'conversation_history'):
            self._add_message_to_history("AI助手", content)
            self.show_status("回复完成", "success")
        else:
            # 否则使用常规输出方式
            self._update_streaming_output(content)

    def _debug_output_area_status(self):
        """调试输出区域状态"""
        logger.info("🔍 调试输出区域状态:")
        logger.info(f"   - hasattr(self, 'output_area'): {hasattr(self, 'output_area')}")
        if hasattr(self, 'output_area'):
            logger.info(f"   - self.output_area: {self.output_area}")
            logger.info(f"   - type(self.output_area): {type(self.output_area)}")
            if self.output_area:
                logger.info(f"   - hasattr(output_area, 'output_text'): {hasattr(self.output_area, 'output_text')}")
                if hasattr(self.output_area, 'output_text'):
                    logger.info(f"   - output_text: {self.output_area.output_text}")
                    logger.info(f"   - type(output_text): {type(self.output_area.output_text)}")
        else:
            logger.error("   - output_area 属性不存在！")

    def _test_ui_component_directly(self):
        """直接测试UI组件是否能显示内容"""
        logger.info("🧪 开始直接测试UI组件...")
        try:
            if hasattr(self, 'output_area') and self.output_area:
                if hasattr(self.output_area, 'output_text'):
                    test_text = "🧪 这是一个测试文本，用于验证UI组件是否正常工作！"
                    logger.info(f"🧪 设置测试文本: {test_text}")
                    self.output_area.output_text.setPlainText(test_text)

                    # 验证设置结果
                    result_text = self.output_area.output_text.toPlainText()
                    logger.info(f"🧪 验证结果: {result_text}")

                    if result_text == test_text:
                        logger.info("✅ UI组件测试成功！")
                        return True
                    else:
                        logger.error("❌ UI组件测试失败！")
                        return False
                else:
                    logger.error("❌ output_text 不存在")
                    return False
            else:
                logger.error("❌ output_area 不存在")
                return False
        except Exception as e:
            logger.error(f"❌ UI组件测试异常: {e}", exc_info=True)
            return False

    def _check_ai_service_status(self) -> Dict[str, Any]:
        """检查AI服务状态"""
        logger.debug(f"检查AI服务状态: ai_orchestration_service={self.ai_orchestration_service}")

        if not self.ai_orchestration_service:
            return {
                'available': False,
                'message': 'AI编排服务未连接，请检查服务配置'
            }

        is_initialized = self.ai_orchestration_service.is_initialized
        logger.debug(f"AI服务初始化状态: {is_initialized}")

        if not is_initialized:
            return {
                'available': False,
                'message': 'AI服务未初始化，请等待服务启动完成'
            }

        # 检查是否有可用的客户端
        if hasattr(self.ai_orchestration_service, 'clients'):
            available_clients = [
                provider for provider, client in self.ai_orchestration_service.clients.items()
                if client and client.is_connected
            ]

            if not available_clients:
                return {
                    'available': False,
                    'message': 'AI客户端未连接，请检查API密钥和网络连接'
                }

        return {
            'available': True,
            'message': 'AI服务正常'
        }

    def get_ai_service_diagnosis(self) -> str:
        """获取AI服务诊断信息"""
        diagnosis = AIConfigValidator.diagnose_ai_service(self.ai_orchestration_service)
        return AIConfigValidator.format_diagnosis_report(diagnosis)

    def _get_streaming_preference(self) -> bool:
        """获取流式输出偏好设置"""
        try:
            if self.settings_service:
                return self.settings_service.get('ai.enable_streaming', True)
            else:
                # 回退到全局容器获取
                from src.shared.ioc.container import get_container
                from src.application.services.settings_service import SettingsService
                container = get_container()
                if container:
                    settings_service = container.get(SettingsService)
                    return settings_service.get('ai.enable_streaming', True)
                else:
                    logger.debug("全局容器未初始化，使用默认流式输出设置")
                    return True
        except Exception as e:
            logger.warning(f"获取流式输出设置失败: {e}")
            return True  # 默认启用流式输出

    async def _process_streaming_request(self, request, function_name: str, options: dict):
        """处理流式AI请求 - 增强调试版本"""
        logger.info(f"🚀 开始流式处理请求: {function_name}")

        # 调试输出区域状态
        self._debug_output_area_status()

        try:
            # 在主线程中清空输出区域并显示开始状态
            logger.debug("📝 清空输出区域并设置状态")
            self._safe_ui_update(lambda: self._clear_output())
            self._safe_ui_update(lambda: self.show_status(f"正在{function_name}...", "info"))

            # 累积响应内容
            accumulated_content = ""
            chunk_count = 0

            logger.info(f"🔄 开始接收流式响应...")
            # 处理流式响应
            async for chunk in self.ai_orchestration_service.process_request_stream(request):
                if chunk:  # 确保chunk不为空
                    accumulated_content += chunk
                    chunk_count += 1
                    logger.debug(f"📦 收到chunk {chunk_count}: '{chunk[:50]}...' (长度: {len(chunk)})")
                    logger.debug(f"📊 累积内容长度: {len(accumulated_content)}")

                    # 每5个chunk或每100个字符更新一次UI，避免过于频繁的更新
                    should_update = chunk_count % 5 == 0 or len(accumulated_content) % 100 < len(chunk)
                    if should_update:
                        # 使用信号进行线程安全的UI更新
                        content_to_display = str(accumulated_content)
                        logger.debug(f"🖥️ 更新UI显示，内容长度: {len(content_to_display)}")
                        self.ui_update_signal.emit(content_to_display)

            # 最终更新 - 确保显示完整内容
            logger.info(f"✅ 流式接收完成，总共 {chunk_count} 个chunk，总长度 {len(accumulated_content)}")
            if accumulated_content:
                final_content = str(accumulated_content)
                logger.info(f"🎯 最终更新UI，内容: '{final_content[:100]}...'")
                # 最终一次支持Markdown渲染（强制主线程执行）
                try:
                    if self.settings_service and self.settings_service.get('ai.render_markdown', True):
                        self._safe_ui_update(lambda fc=final_content: self._render_to_output(fc))
                    else:
                        # 通过信号进入主线程
                        self.ui_update_signal.emit(final_content)
                except Exception:
                    self.ui_update_signal.emit(final_content)
            else:
                logger.warning("⚠️ 没有接收到任何内容！")

            # 流式完成
            self._safe_ui_update(lambda: self.show_status(f"{function_name} 完成", "success"))
            logger.info(f"🎉 流式处理完成，共处理 {chunk_count} 个块，总长度 {len(accumulated_content)} 字符")

            # 智能续写默认自动插入（支持 options 覆盖设置）
            try:
                # 优先读取 options 中的配置，其次读取 settings_service
                auto_apply = (options or {}).get('auto_apply_continue', None)
                if auto_apply is None:
                    auto_apply = self.settings_service.get('ai.auto_apply_continue', True) if self.settings_service else True
                if (options or {}).get('type') == 'continue' and auto_apply and accumulated_content.strip():
                    self.text_insert_requested.emit(accumulated_content, -1)
                    self.text_applied.emit(accumulated_content)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"❌ 流式处理失败: {e}", exc_info=True)
            error_msg = f"❌ 流式处理失败: {str(e)}"
            self._safe_ui_update(lambda: self.show_status(f"{function_name} 失败", "error"))
            self._safe_ui_update(lambda msg=error_msg: self._display_ai_response(msg))

    def _handle_ai_response(self, response, function_name: str, options: dict):
        """处理AI响应（非流式）"""
        if response.is_successful:
            # 在主线程中更新UI
            QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 完成", "success"))
            # 非流式最终渲染（支持Markdown）
            try:
                if self.settings_service and self.settings_service.get('ai.render_markdown', True):
                    QTimer.singleShot(0, lambda: self._render_to_output(response.content))
                else:
                    QTimer.singleShot(0, lambda: self._display_ai_response(response.content))
            except Exception:
                QTimer.singleShot(0, lambda: self._display_ai_response(response.content))
            # 非流式也支持自动插入（支持 options 覆盖设置）
            try:
                auto_apply = (options or {}).get('auto_apply_continue', None)
                if auto_apply is None:
                    auto_apply = self.settings_service.get('ai.auto_apply_continue', True) if self.settings_service else True
                if (options or {}).get('type') == 'continue' and auto_apply and response.content.strip():
                    self.text_insert_requested.emit(response.content, -1)
                    self.text_applied.emit(response.content)
            except Exception:
                pass
        else:
            # 在主线程中更新UI
            error_msg = f"❌ {response.error_message or '处理失败'}"
            QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 失败", "error"))
            QTimer.singleShot(0, lambda: self._display_ai_response(error_msg))

    def _clear_output(self):
        """清空输出区域"""
        try:
            if hasattr(self, 'output_area') and self.output_area:
                if hasattr(self.output_area, 'output_text'):
                    self.output_area.output_text.clear()
                else:
                    # 兼容旧版本
                    self.output_area.clear()
        except Exception as e:
            logger.warning(f"清空输出区域失败: {e}")

    def _safe_ui_update(self, update_func):
        """安全的UI更新方法 - 简化版本"""
        try:
            logger.debug("🔄 调度UI更新任务")
            QTimer.singleShot(0, update_func)
        except Exception as e:
            logger.error(f"❌ UI更新调度失败: {e}", exc_info=True)

    def _handle_ui_update(self, content: str):
        """处理线程安全的UI更新信号 - 在主线程中执行"""
        from PyQt6.QtCore import QThread
        current_thread = QThread.currentThread()
        main_thread = self.thread()

        logger.info(f"🎯 收到UI更新信号，内容长度: {len(content)}")
        logger.info(f"🧵 信号处理线程: {current_thread}, 主线程: {main_thread}")

        try:
            self._update_streaming_output(content)
            logger.info("✅ 信号驱动的UI更新成功")
        except Exception as e:
            logger.error(f"❌ 信号驱动的UI更新失败: {e}", exc_info=True)

    # === 聊天功能处理方法 ===

    def _on_send_chat_message(self):
        """发送聊天消息"""
        message = self.chat_input.toPlainText().strip()
        if not message:
            return

        # 添加用户消息到历史
        self._add_message_to_history("用户", message)

        # 清空输入框
        self.chat_input.clear()

        # 显示状态
        self.show_status("正在处理您的问题...", "info")

        # 构建聊天请求
        chat_prompt = self._build_chat_prompt(message)

        # 执行AI请求
        options = {
            'function_id': 'interactive_chat',
            'execution_mode': 'INTERACTIVE',
            'context': self.document_context,
            'selected_text': self.selected_text,
            'conversation_history': self.conversation_history
        }

        self.execute_ai_request("ai_chat", chat_prompt, options)

    def _on_clear_chat(self):
        """清空聊天历史"""
        self.chat_history.clear()
        self.conversation_history = []
        self.show_status("聊天历史已清空", "info")

    def _on_chat_input_changed(self):
        """聊天输入变化处理"""
        has_text = bool(self.chat_input.toPlainText().strip())
        self.send_button.setEnabled(has_text)

    def _add_message_to_history(self, sender: str, message: str):
        """添加消息到聊天历史"""
        from datetime import datetime

        # 添加到对话历史数据
        self.conversation_history.append({
            'sender': sender,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

        # 显示在UI中
        timestamp = datetime.now().strftime("%H:%M:%S")

        if sender == "用户":
            formatted_message = f"""
            <div style="margin: 8px 0; padding: 8px; background-color: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;">
                <strong style="color: #1976d2;">👤 {sender}</strong> <span style="color: #666; font-size: 12px;">{timestamp}</span><br>
                <span style="color: #333;">{message}</span>
            </div>
            """
        else:
            formatted_message = f"""
            <div style="margin: 8px 0; padding: 8px; background-color: #f1f8e9; border-radius: 8px; border-left: 4px solid #4caf50;">
                <strong style="color: #388e3c;">🤖 {sender}</strong> <span style="color: #666; font-size: 12px;">{timestamp}</span><br>
                <span style="color: #333;">{message}</span>
            </div>
            """

        # 添加到聊天历史显示
        cursor = self.chat_history.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(formatted_message)

        # 滚动到底部
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _build_chat_prompt(self, user_message: str) -> str:
        """构建聊天提示词"""
        # 基础系统提示
        system_prompt = """你是一个专业的AI写作助手，专门帮助用户进行小说创作。你的特点是：
1. 友好、专业、有耐心
2. 对小说创作有深入理解
3. 能够提供具体、实用的建议
4. 善于分析文本和提供创意灵感

请根据用户的问题提供有帮助的回答。"""

        # 添加文档上下文（如果有）
        context_info = ""
        if self.document_context:
            context_info = f"\n\n当前文档内容（供参考）：\n{self.document_context[:1000]}..."

        # 添加对话历史（最近5轮）
        history_info = ""
        if len(self.conversation_history) > 1:
            recent_history = self.conversation_history[-10:]  # 最近5轮对话
            history_info = "\n\n对话历史：\n"
            for item in recent_history:
                if item['sender'] != "用户":  # 排除当前用户消息
                    history_info += f"{item['sender']}: {item['message']}\n"

        # 构建完整提示
        full_prompt = f"""{system_prompt}{context_info}{history_info}

用户问题: {user_message}

请提供有帮助的回答："""

        return full_prompt

    def _on_context_updated_callback(self, document_id: str, context_info) -> None:
        """文档上下文更新回调"""
        try:
            # 更新当前组件的上下文
            self.document_context = context_info.content
            self.selected_text = context_info.selected_text

            # 如果有建议，可以显示给用户
            if context_info.suggestions:
                suggestions_text = "💡 写作建议：\n" + "\n".join(context_info.suggestions)
                logger.info(f"收到写作建议: {len(context_info.suggestions)} 条")

            logger.debug(f"上下文已更新: {document_id}, 内容长度: {len(context_info.content)}")

        except Exception as e:
            logger.error(f"上下文更新回调失败: {e}")

    def update_document_context_external(self, document_id: str, content: str, selected_text: str = "") -> None:
        """外部调用更新文档上下文"""
        if hasattr(self, 'context_manager') and self.context_manager:
            self.context_manager.update_document_context(
                document_id=document_id,
                content=content,
                selected_text=selected_text
            )

    def _update_streaming_output(self, content: str):
        """更新流式输出内容 - 简化版本（应该在主线程中调用）"""
        logger.info(f"🚀 _update_streaming_output 执行，内容长度: {len(content)}")

        try:
            # 检查output_area是否存在
            if not hasattr(self, 'output_area') or not self.output_area:
                logger.error("❌ output_area 不存在！")
                return

            # 检查output_text是否存在
            if hasattr(self.output_area, 'output_text'):
                text_widget = self.output_area.output_text
                logger.info(f"✅ 找到 output_text: {type(text_widget)}")

                # 设置文本内容（流式阶段保持纯文本，避免渲染抖动）
                text_widget.setPlainText(content)
                logger.info(f"📝 文本内容已设置，长度: {len(content)}")

                # 自动滚动到底部
                cursor = text_widget.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                text_widget.setTextCursor(cursor)

                # 确保滚动条滚动到底部
                scrollbar = text_widget.verticalScrollBar()
                if scrollbar:
                    scrollbar.setValue(scrollbar.maximum())

                logger.info("✅ UI内容更新完成")
            else:
                logger.error("❌ output_area.output_text 不存在")

        except Exception as e:
            logger.error(f"❌ 更新流式输出失败: {e}", exc_info=True)

    def _render_to_output(self, markdown_text: str):
        """将Markdown渲染成HTML并显示到输出区（最终完成时调用）"""
        try:
            if not hasattr(self, 'output_area') or not self.output_area or not hasattr(self.output_area, 'output_text'):
                return
            # 简易Markdown渲染：标题、粗体、代码块和列表（不引入依赖）
            html = self._simple_markdown_to_html(markdown_text)
            # 确保在主线程更新 QTextDocument（安全起见）
            from src.shared.utils.thread_safety import is_main_thread
            if is_main_thread():
                self.output_area.output_text.setHtml(html)
            else:
                from src.shared.utils.thread_safety import safe_qt_call
                safe_qt_call(self.output_area.output_text.setHtml, html)
        except Exception as e:
            logger.warning(f"Markdown渲染失败: {e}")
            # 回退纯文本
            try:
                self.output_area.output_text.setPlainText(markdown_text)
            except Exception:
                pass

    def _simple_markdown_to_html(self, text: str) -> str:
        """非常轻量的Markdown->HTML（足够用于可读性增强）"""
        import html
        t = html.escape(text)
        # 粗体 **bold**
        t = t.replace("**", "\u0000")  # 暂存
        parts = t.split("\u0000")
        t = ''.join([f"<b>{p}</b>" if i % 2 == 1 else p for i, p in enumerate(parts)])
        # 标题 #, ##
        lines = []
        for line in t.split('\n'):
            s = line.lstrip()
            if s.startswith('### '):
                lines.append(f"<h3>{s[4:]}</h3>")
            elif s.startswith('## '):
                lines.append(f"<h2>{s[3:]}</h2>")
            elif s.startswith('# '):
                lines.append(f"<h1>{s[2:]}</h1>")
            elif s.startswith('- '):
                lines.append(f"<li>{s[2:]}</li>")
            else:
                lines.append(f"<p>{line}</p>")
        # 列表包裹
        html_lines = []
        in_list = False
        for line in lines:
            if line.startswith('<li>') and not in_list:
                html_lines.append('<ul>')
                in_list = True
            if not line.startswith('<li>') and in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(line)
        if in_list:
            html_lines.append('</ul>')
        return '\n'.join(html_lines)

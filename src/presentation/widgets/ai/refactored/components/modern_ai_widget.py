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
    QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPalette

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

    # 线程安全的UI更新信号
    ui_update_signal = pyqtSignal(str)  # 用于线程安全的UI更新
    
    def __init__(self, parent=None, settings_service=None):
        super().__init__(parent)
        self.selected_text = ""
        self.document_context = ""
        self.document_type = "chapter"
        self.document_metadata = {}

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

        # 尝试获取AI服务
        self._initialize_ai_services()

        # 连接线程安全的UI更新信号
        self.ui_update_signal.connect(self._handle_ui_update)

        # 初始化文档上下文管理器
        self._initialize_context_manager()

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
        """应用现代化样式"""
        self.setStyleSheet(get_complete_ai_style())

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
        
        # 设置按钮样式
        if style_type in SPECIAL_BUTTON_STYLES:
            button.setStyleSheet(SPECIAL_BUTTON_STYLES[style_type])
        
        # 连接回调
        if callback:
            button.clicked.connect(callback)
        
        # 添加悬停动画效果
        self._add_button_animation(button)
        
        return button
    
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

        # 创建文本编辑器
        output_text = QTextEdit()
        output_text.setPlaceholderText(placeholder)
        output_text.setReadOnly(True)
        output_text.setMinimumHeight(150)
        output_text.setObjectName("OutputText")

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(output_text)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(400)
        scroll_area.setObjectName("OutputArea")

        # 保存文本编辑器的引用，用于更新内容
        scroll_area.output_text = output_text

        return scroll_area

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
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        chat_layout.addWidget(self.chat_history)

        # 创建输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        # 创建输入文本框
        self.chat_input = QTextEdit()
        self.chat_input.setMaximumHeight(80)
        self.chat_input.setPlaceholderText("在这里输入您的问题...")
        self.chat_input.setFont(font)
        self.chat_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
                background-color: white;
            }
            QTextEdit:focus {
                border-color: #007bff;
            }
        """)

        # 创建发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.setMinimumSize(80, 40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        # 创建清空按钮
        self.clear_chat_button = QPushButton("清空")
        self.clear_chat_button.setMinimumSize(60, 40)
        self.clear_chat_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)

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
    
    def set_selected_text(self, text: str):
        """设置选中文本"""
        self.selected_text = text
        logger.debug(f"设置选中文本: {len(text)} 字符")

    def set_context(self, content: str, selected_text: str = ""):
        """设置上下文（兼容性方法）"""
        self.document_context = content
        self.selected_text = selected_text
        logger.debug(f"设置上下文: {len(content)} 字符内容, {len(selected_text)} 字符选中文本")
    
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
            request = AIRequest(
                prompt=full_prompt,
                context=self.document_context,
                request_type=function_name,
                priority=AIPriority.NORMAL,
                parameters=options,
                is_streaming=use_streaming
            )

            # 处理请求
            if use_streaming:
                await self._process_streaming_request(request, function_name)
            else:
                response = await self.ai_orchestration_service.process_request(request)
                self._handle_ai_response(response, function_name)

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

        # 添加上下文信息
        if self.document_context:
            full_prompt += f"文档上下文:\n{self.document_context[:1000]}...\n\n"

        if self.selected_text:
            full_prompt += f"选中文本:\n{self.selected_text}\n\n"

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

    async def _process_streaming_request(self, request, function_name: str):
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
                self.ui_update_signal.emit(final_content)
            else:
                logger.warning("⚠️ 没有接收到任何内容！")

            # 流式完成
            self._safe_ui_update(lambda: self.show_status(f"{function_name} 完成", "success"))
            logger.info(f"🎉 流式处理完成，共处理 {chunk_count} 个块，总长度 {len(accumulated_content)} 字符")

        except Exception as e:
            logger.error(f"❌ 流式处理失败: {e}", exc_info=True)
            error_msg = f"❌ 流式处理失败: {str(e)}"
            self._safe_ui_update(lambda: self.show_status(f"{function_name} 失败", "error"))
            self._safe_ui_update(lambda msg=error_msg: self._display_ai_response(msg))

    def _handle_ai_response(self, response, function_name: str):
        """处理AI响应（非流式）"""
        if response.is_successful:
            # 在主线程中更新UI
            QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 完成", "success"))
            QTimer.singleShot(0, lambda: self._display_ai_response(response.content))
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

                # 设置文本内容
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

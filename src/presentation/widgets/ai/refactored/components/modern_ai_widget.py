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
    
    def __init__(self, parent=None, settings_service=None):
        super().__init__(parent)
        self.selected_text = ""
        self.document_context = ""

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
    
    def set_document_context(self, context: str):
        """设置文档上下文"""
        self.document_context = context
        logger.debug(f"设置文档上下文: {len(context)} 字符")
    
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
        """调度AI请求执行"""
        try:
            # 直接在主线程中执行，避免线程问题
            import asyncio

            # 使用QTimer在主线程中执行异步任务
            def run_async_task():
                try:
                    # 创建新的事件循环在当前线程中运行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # 运行异步任务
                    result = loop.run_until_complete(
                        self._process_ai_request_async(function_name, prompt, options)
                    )

                    # 清理事件循环
                    loop.close()

                except Exception as e:
                    logger.error(f"异步任务执行失败: {e}")
                    # 在主线程中更新UI
                    QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 失败", "error"))
                    QTimer.singleShot(0, lambda: self._display_ai_response(f"❌ 执行失败: {str(e)}"))

            # 使用线程池执行异步任务，避免阻塞主线程
            import threading
            thread = threading.Thread(target=run_async_task, daemon=True)
            thread.start()

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
        """显示AI响应"""
        if hasattr(self, 'output_area') and self.output_area:
            # 获取实际的文本编辑器
            if hasattr(self.output_area, 'output_text'):
                self.output_area.output_text.setPlainText(content)
                # 自动滚动到底部
                cursor = self.output_area.output_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.output_area.output_text.setTextCursor(cursor)
            else:
                # 兼容旧版本
                self.output_area.setPlainText(content)
        else:
            logger.info(f"AI响应: {content[:100]}...")

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
        """处理流式AI请求"""
        try:
            # 清空输出区域并显示开始状态
            QTimer.singleShot(0, lambda: self._clear_output())
            QTimer.singleShot(0, lambda: self.show_status(f"正在{function_name}...", "info"))

            # 累积响应内容
            accumulated_content = ""

            # 处理流式响应
            async for chunk in self.ai_orchestration_service.process_request_stream(request):
                accumulated_content += chunk
                # 在主线程中更新UI
                content_copy = accumulated_content  # 避免闭包问题
                QTimer.singleShot(0, lambda c=content_copy: self._update_streaming_output(c))

            # 流式完成
            QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 完成", "success"))

        except Exception as e:
            logger.error(f"流式处理失败: {e}")
            error_msg = f"❌ 流式处理失败: {str(e)}"
            QTimer.singleShot(0, lambda: self.show_status(f"{function_name} 失败", "error"))
            QTimer.singleShot(0, lambda: self._display_ai_response(error_msg))

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
        if hasattr(self, 'output_area') and self.output_area:
            if hasattr(self.output_area, 'output_text'):
                self.output_area.output_text.clear()
            else:
                # 兼容旧版本
                self.output_area.clear()

    def _update_streaming_output(self, content: str):
        """更新流式输出内容"""
        if hasattr(self, 'output_area') and self.output_area:
            if hasattr(self.output_area, 'output_text'):
                self.output_area.output_text.setPlainText(content)
                # 自动滚动到底部
                cursor = self.output_area.output_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.output_area.output_text.setTextCursor(cursor)
            else:
                # 兼容旧版本
                self.output_area.setPlainText(content)

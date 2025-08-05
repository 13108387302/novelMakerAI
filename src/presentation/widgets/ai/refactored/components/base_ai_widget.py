#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础AI组件

提供AI组件的基础功能和通用接口
"""

import logging
from typing import Dict, Any, Optional, Callable
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont

from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
from src.application.services.ai.intelligence.ai_intelligence_service import AIIntelligentFunction
from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse

logger = logging.getLogger(__name__)


class AIWidgetSignals(QObject):
    """AI组件信号"""
    
    # 请求相关信号
    request_started = pyqtSignal(str)  # 请求开始，参数：请求ID
    request_completed = pyqtSignal(str, str)  # 请求完成，参数：请求ID, 响应内容
    request_failed = pyqtSignal(str, str)  # 请求失败，参数：请求ID, 错误信息
    request_cancelled = pyqtSignal(str)  # 请求取消，参数：请求ID
    
    # 状态相关信号
    status_changed = pyqtSignal(str, str)  # 状态改变，参数：状态文本, 状态类型
    progress_updated = pyqtSignal(int)  # 进度更新，参数：进度百分比
    
    # 智能化相关信号
    intelligence_mode_changed = pyqtSignal(bool)  # 智能化模式改变，参数：是否启用
    auto_execution_triggered = pyqtSignal(str)  # 自动执行触发，参数：功能ID


class BaseAIWidget(QWidget):
    """
    基础AI组件
    
    提供AI组件的基础功能和通用接口
    """
    
    def __init__(self, parent=None):
        """
        初始化基础AI组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 信号管理
        self.signals = AIWidgetSignals()
        
        # 服务依赖
        self.ai_orchestration_service: Optional[AIOrchestrationService] = None
        
        # 组件状态
        self.is_initialized = False
        self.is_processing = False
        self.current_request_id: Optional[str] = None
        
        # 智能化配置
        self.intelligence_enabled = True
        self.auto_execution_enabled = True
        
        # 上下文信息
        self.document_context = ""
        self.selected_text = ""
        self.document_id: Optional[str] = None
        self.document_type = "chapter"
        
        # UI配置
        self.setup_ui_config()
        
        # 初始化UI
        self.setup_ui()
        
        # 连接信号
        self.connect_signals()
    
    def setup_ui_config(self) -> None:
        """设置UI配置"""
        # 字体配置
        self.default_font = QFont("Microsoft YaHei", 10)
        self.title_font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        self.code_font = QFont("Consolas", 9)
        
        # 颜色配置
        self.colors = {
            'primary': '#0078D4',
            'success': '#107C10',
            'warning': '#FF8C00',
            'error': '#D13438',
            'info': '#0078D4',
            'background': '#FFFFFF',
            'border': '#E1E1E1',
            'text': '#323130',
            'text_secondary': '#605E5C'
        }
        
        # 样式配置
        self.styles = {
            'button': f"""
                QPushButton {{
                    background-color: {self.colors['primary']};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #106EBE;
                }}
                QPushButton:pressed {{
                    background-color: #005A9E;
                }}
                QPushButton:disabled {{
                    background-color: #F3F2F1;
                    color: #A19F9D;
                }}
            """,
            'input': f"""
                QTextEdit, QLineEdit {{
                    border: 2px solid {self.colors['border']};
                    border-radius: 4px;
                    padding: 8px;
                    background-color: {self.colors['background']};
                    color: {self.colors['text']};
                }}
                QTextEdit:focus, QLineEdit:focus {{
                    border-color: {self.colors['primary']};
                }}
            """,
            'status': f"""
                QLabel {{
                    color: {self.colors['text_secondary']};
                    font-size: 12px;
                }}
                QLabel[status="info"] {{
                    color: {self.colors['info']};
                }}
                QLabel[status="success"] {{
                    color: {self.colors['success']};
                }}
                QLabel[status="warning"] {{
                    color: {self.colors['warning']};
                }}
                QLabel[status="error"] {{
                    color: {self.colors['error']};
                }}
            """
        }
    
    def setup_ui(self) -> None:
        """设置用户界面（子类应重写）"""
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)
        
        # 设置默认字体
        self.setFont(self.default_font)
    
    def connect_signals(self) -> None:
        """连接信号（子类可重写）"""
        # 连接基础信号
        self.signals.request_started.connect(self._on_request_started)
        self.signals.request_completed.connect(self._on_request_completed)
        self.signals.request_failed.connect(self._on_request_failed)
        self.signals.request_cancelled.connect(self._on_request_cancelled)
        self.signals.status_changed.connect(self._on_status_changed)
    
    def initialize(self, ai_orchestration_service: AIOrchestrationService) -> bool:
        """
        初始化组件
        
        Args:
            ai_orchestration_service: AI编排服务
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.ai_orchestration_service = ai_orchestration_service
            
            # 执行子类特定的初始化
            if not self._initialize_specific():
                return False
            
            self.is_initialized = True
            logger.info(f"{self.__class__.__name__} 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} 初始化失败: {e}")
            return False
    
    def _initialize_specific(self) -> bool:
        """子类特定的初始化逻辑（子类可重写）"""
        return True
    
    def set_context(
        self,
        document_context: str = "",
        selected_text: str = "",
        document_id: Optional[str] = None,
        document_type: str = "chapter"
    ) -> None:
        """
        设置上下文信息
        
        Args:
            document_context: 文档上下文
            selected_text: 选中文字
            document_id: 文档ID
            document_type: 文档类型
        """
        self.document_context = document_context
        self.selected_text = selected_text
        self.document_id = document_id
        self.document_type = document_type
        
        # 通知子类上下文已更新
        self._on_context_updated()
    
    def _on_context_updated(self) -> None:
        """上下文更新回调（子类可重写）"""
        pass
    
    def set_intelligence_enabled(self, enabled: bool) -> None:
        """
        设置智能化是否启用
        
        Args:
            enabled: 是否启用智能化
        """
        self.intelligence_enabled = enabled
        self.signals.intelligence_mode_changed.emit(enabled)
        self._on_intelligence_mode_changed(enabled)
    
    def _on_intelligence_mode_changed(self, enabled: bool) -> None:
        """智能化模式改变回调（子类可重写）"""
        pass
    
    def execute_intelligent_function(
        self,
        function: AIIntelligentFunction,
        callback: Optional[Callable[[AIResponse], None]] = None
    ) -> bool:
        """
        执行智能化功能
        
        Args:
            function: 智能化功能
            callback: 完成回调
            
        Returns:
            bool: 是否成功启动执行
        """
        if not self.is_initialized or not self.ai_orchestration_service:
            logger.error("组件未初始化或服务不可用")
            return False
        
        if self.is_processing:
            logger.warning("正在处理其他请求，无法执行新请求")
            return False
        
        try:
            # 构建智能化请求
            request = function.build_auto_request(
                context=self.document_context,
                selected_text=self.selected_text,
                parameters={
                    'document_id': self.document_id,
                    'document_type': self.document_type
                }
            )
            
            if not request:
                logger.warning(f"无法构建智能化请求: {function.metadata.name}")
                return False
            
            # 异步执行请求
            self._execute_request_async(request, callback)
            
            return True
            
        except Exception as e:
            logger.error(f"执行智能化功能失败: {e}")
            return False
    
    def _execute_request_async(
        self,
        request: AIRequest,
        callback: Optional[Callable[[AIResponse], None]] = None
    ) -> None:
        """
        异步执行AI请求
        
        Args:
            request: AI请求
            callback: 完成回调
        """
        # 使用QTimer在下一个事件循环中执行
        QTimer.singleShot(0, lambda: self._execute_request_sync(request, callback))
    
    def _execute_request_sync(
        self,
        request: AIRequest,
        callback: Optional[Callable[[AIResponse], None]] = None
    ) -> None:
        """
        同步执行AI请求

        Args:
            request: AI请求
            callback: 完成回调
        """
        # 发出请求开始信号
        self.signals.request_started.emit(request.id)

        # 这里应该调用异步的AI服务，但由于Qt的限制，我们需要特殊处理
        # 实际实现中，应该使用QThread或其他异步机制
        # 暂时使用模拟响应
        QTimer.singleShot(1000, lambda: self._simulate_response(request, callback))

    def _simulate_response(
        self,
        request: AIRequest,
        callback: Optional[Callable[[AIResponse], None]] = None
    ) -> None:
        """模拟AI响应（临时实现）"""
        try:
            # 创建模拟响应
            response = AIResponse(
                request_id=request.id,
                content="这是一个模拟的AI响应内容。",
                provider="mock",
                model="mock-model"
            )
            response.complete()

            # 发出完成信号
            self.signals.request_completed.emit(request.id, response.content)

            # 调用回调
            if callback:
                callback(response)

        except Exception as e:
            self.signals.request_failed.emit(request.id, str(e))
    
    def cancel_current_request(self) -> bool:
        """
        取消当前请求
        
        Returns:
            bool: 是否成功取消
        """
        if not self.current_request_id:
            return False
        
        # 这里应该调用AI服务的取消方法
        # 实际实现中需要与AI编排服务集成
        
        self.signals.request_cancelled.emit(self.current_request_id)
        return True
    
    def show_status(self, message: str, status_type: str = "info") -> None:
        """
        显示状态信息
        
        Args:
            message: 状态消息
            status_type: 状态类型 (info, success, warning, error)
        """
        self.signals.status_changed.emit(message, status_type)
    
    # 信号处理方法
    def _on_request_started(self, request_id: str) -> None:
        """请求开始处理"""
        self.is_processing = True
        self.current_request_id = request_id
        logger.debug(f"AI请求开始: {request_id}")
    
    def _on_request_completed(self, request_id: str, content: str) -> None:
        """请求完成处理"""
        self.is_processing = False
        self.current_request_id = None
        logger.debug(f"AI请求完成: {request_id}")
    
    def _on_request_failed(self, request_id: str, error: str) -> None:
        """请求失败处理"""
        self.is_processing = False
        self.current_request_id = None
        logger.error(f"AI请求失败: {request_id}, 错误: {error}")
    
    def _on_request_cancelled(self, request_id: str) -> None:
        """请求取消处理"""
        self.is_processing = False
        self.current_request_id = None
        logger.info(f"AI请求已取消: {request_id}")
    
    def _on_status_changed(self, message: str, status_type: str) -> None:
        """状态改变处理（子类可重写）"""
        logger.info(f"状态更新: {message} ({status_type})")
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.current_request_id:
            self.cancel_current_request()
        
        self.ai_orchestration_service = None
        self.is_initialized = False

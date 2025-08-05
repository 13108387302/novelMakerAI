#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI组件基础类 - 重构版本

提供所有AI组件的统一基础架构，确保架构一致性和代码复用
"""

from abc import ABC, abstractmethod, ABCMeta
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QProgressBar, QGroupBox, QComboBox, QFrame
)
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QTextCursor

# 处理不同PyQt6版本的sip导入
try:
    import sip
except ImportError:
    try:
        from PyQt6 import sip
    except ImportError:
        # 如果都导入失败，使用type()作为fallback
        sip = None

from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger
from src.application.services.ai.core_abstractions import AIRequest, AIResponse, AIRequestType
from src.application.services.unified_ai_service import UnifiedAIService

logger = get_logger(__name__)


class QWidgetABCMeta(type(QWidget), ABCMeta):
    """
    解决QWidget和ABC的metaclass冲突的自定义metaclass

    这个metaclass继承了QWidget的metaclass和ABCMeta，
    使得类可以同时继承QWidget和ABC而不会产生metaclass冲突。
    """
    pass


class AIWidgetState(Enum):
    """AI组件状态 - 扩展版本"""
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    DISABLED = "disabled"
    CANCELLED = "cancelled"


class AIOutputMode(Enum):
    """AI输出模式 - 扩展版本"""
    REPLACE = "replace"
    INSERT = "insert"
    APPEND = "append"
    NEW_DOCUMENT = "new_document"
    PREVIEW = "preview"
    CLIPBOARD = "clipboard"


class AIWidgetPriority(Enum):
    """AI组件优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AIWidgetTheme:
    """AI组件主题配置 - 增强版本"""
    # 主要颜色
    PRIMARY_COLOR: str = "#2196F3"
    SECONDARY_COLOR: str = "#1976D2"
    ACCENT_COLOR: str = "#03DAC6"

    # 状态颜色
    SUCCESS_COLOR: str = "#4CAF50"
    WARNING_COLOR: str = "#FF9800"
    ERROR_COLOR: str = "#F44336"
    INFO_COLOR: str = "#2196F3"

    # 背景颜色
    BACKGROUND_COLOR: str = "#FAFAFA"
    SURFACE_COLOR: str = "#FFFFFF"
    CARD_COLOR: str = "#F5F5F5"

    # 边框和分割线
    BORDER_COLOR: str = "#E0E0E0"
    DIVIDER_COLOR: str = "#BDBDBD"

    # 文本颜色
    TEXT_COLOR: str = "#212121"
    SECONDARY_TEXT_COLOR: str = "#757575"
    DISABLED_TEXT_COLOR: str = "#BDBDBD"

    # 按钮样式
    BUTTON_RADIUS: int = 4
    CARD_RADIUS: int = 8

    # 字体设置
    FONT_FAMILY: str = "Segoe UI, Arial, sans-serif"
    FONT_SIZE: int = 12
    TITLE_FONT_SIZE: int = 14


class AIWidgetConfig:
    """AI组件配置 - 增强版本"""

    def __init__(self):
        # 基础功能
        self.enable_streaming = True
        self.auto_clear_on_new_request = False
        self.show_token_count = True
        self.show_performance_stats = False

        # 输入输出限制
        self.max_input_length = 10000
        self.max_output_length = 20000
        self.input_placeholder = "请输入您的问题或需求..."

        # AI参数
        self.default_temperature = 0.7
        self.default_max_tokens = 2000
        self.default_provider = "auto"

        # 高级功能
        self.enable_context_awareness = True
        self.auto_save_history = True
        self.enable_suggestions = True
        self.enable_shortcuts = True

        # UI设置
        self.compact_mode = False
        self.show_advanced_options = False
        self.auto_resize = True

        # 性能设置
        self.debounce_delay = 300  # 毫秒
        self.max_concurrent_requests = 1
        self.request_timeout = 30  # 秒


class BaseAIWidget(QWidget, ABC, metaclass=QWidgetABCMeta):
    """
    AI组件基础类 - 优化版本

    提供所有AI组件的统一基础功能，包括：
    - 统一的UI布局和样式
    - 标准化的AI请求处理
    - 事件总线集成
    - 状态管理和错误处理
    - 主题和配置支持
    - 性能监控和优化
    - 用户体验增强
    """

    # 统一信号定义 - 扩展版本
    request_started = pyqtSignal(str)  # request_id
    request_completed = pyqtSignal(str, str)  # request_id, content
    request_failed = pyqtSignal(str, str)  # request_id, error
    request_cancelled = pyqtSignal(str)  # request_id

    content_ready = pyqtSignal(str, str)  # content, mode
    content_preview = pyqtSignal(str)  # preview_content

    status_changed = pyqtSignal(str, str)  # message, level
    state_changed = pyqtSignal(str)  # new_state
    progress_updated = pyqtSignal(int)  # progress_percentage

    # 流式响应信号
    stream_started = pyqtSignal(str)  # request_id
    stream_chunk_received = pyqtSignal(str, str)  # request_id, chunk
    stream_completed = pyqtSignal(str)  # request_id

    # 用户交互信号
    suggestion_clicked = pyqtSignal(str)  # suggestion_text
    shortcut_triggered = pyqtSignal(str)  # shortcut_name
    
    def __init__(
        self,
        ai_service: UnifiedAIService,
        widget_id: str,
        parent: Optional[QWidget] = None,
        config: Optional[AIWidgetConfig] = None,
        theme: Optional[AIWidgetTheme] = None
    ):
        super().__init__(parent)

        # 核心属性
        self.ai_service = ai_service
        self.widget_id = widget_id
        self.config = config or AIWidgetConfig()
        self.theme = theme or AIWidgetTheme()

        # 状态管理
        self._state = AIWidgetState.IDLE
        self._current_request_id: Optional[str] = None
        self._request_history: List[Dict[str, Any]] = []
        self._is_busy = False

        # 性能监控
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        self._start_time = None

        # UI组件（子类可以重写）
        self.main_layout: Optional[QVBoxLayout] = None
        self.status_label: Optional[QLabel] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.input_widget: Optional[QTextEdit] = None
        self.output_widget: Optional[QTextEdit] = None

        # 防抖定时器
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_debounce_timeout)

        # 性能监控定时器
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_performance_stats)
        if self.config.show_performance_stats:
            self._stats_timer.start(5000)  # 每5秒更新一次

        # 初始化
        self._setup_base_ui()
        self._connect_ai_service()
        self._apply_theme()
        self._setup_shortcuts()

        logger.debug(f"AI组件基础类初始化完成: {widget_id}")
    
    def _setup_base_ui(self):
        """设置基础UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)
        
        # 状态栏
        self._create_status_bar()
        
        # 子类实现具体UI
        self._create_ui()
        
        # 进度条（默认隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(4, 2, 4, 2)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"color: {self.theme.SECONDARY_TEXT_COLOR};")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        self.main_layout.addWidget(status_frame)
    
    @abstractmethod
    def _create_ui(self):
        """创建具体UI - 子类实现"""
        pass
    
    def _connect_ai_service(self):
        """连接AI服务信号"""
        if self.ai_service:
            # 连接统一AI服务的信号
            self.ai_service.request_started.connect(self._on_request_started)
            self.ai_service.request_completed.connect(self._on_request_completed)
            self.ai_service.request_failed.connect(self._on_request_failed)
            self.ai_service.stream_chunk_received.connect(self._on_stream_chunk)
            self.ai_service.stream_completed.connect(self._on_stream_completed)
    
    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme.BACKGROUND_COLOR};
                color: {self.theme.TEXT_COLOR};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.theme.BORDER_COLOR};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }}
            QPushButton {{
                background-color: {self.theme.PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.PRIMARY_COLOR}dd;
            }}
            QPushButton:pressed {{
                background-color: {self.theme.PRIMARY_COLOR}bb;
            }}
            QPushButton:disabled {{
                background-color: {self.theme.BORDER_COLOR};
                color: {self.theme.SECONDARY_TEXT_COLOR};
            }}
            QTextEdit {{
                border: 1px solid {self.theme.BORDER_COLOR};
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }}
            QComboBox {{
                border: 1px solid {self.theme.BORDER_COLOR};
                border-radius: 4px;
                padding: 4px 8px;
                background-color: white;
            }}
        """)
    
    # 状态管理
    
    def get_state(self) -> AIWidgetState:
        """获取当前状态"""
        return self._state
    
    def set_state(self, state: AIWidgetState):
        """设置状态"""
        if self._state != state:
            old_state = self._state
            self._state = state
            self._on_state_changed(old_state, state)
            self.state_changed.emit(state.value)
    
    def is_busy(self) -> bool:
        """检查是否忙碌"""
        return self._state in [AIWidgetState.PROCESSING, AIWidgetState.STREAMING]
    
    def _on_state_changed(self, old_state: AIWidgetState, new_state: AIWidgetState):
        """状态变化处理"""
        # 更新UI状态
        if new_state == AIWidgetState.PROCESSING:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self._show_status("AI处理中...", "info")
        elif new_state == AIWidgetState.STREAMING:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self._show_status("接收AI响应中...", "info")
        elif new_state == AIWidgetState.IDLE:
            self.progress_bar.setVisible(False)
            self._show_status("就绪", "info")
        elif new_state == AIWidgetState.ERROR:
            self.progress_bar.setVisible(False)
            self._show_status("发生错误", "error")
        elif new_state == AIWidgetState.DISABLED:
            self.progress_bar.setVisible(False)
            self._show_status("AI服务不可用", "warning")
    
    # 状态显示
    
    def _show_status(self, message: str, level: str = "info"):
        """显示状态消息"""
        if self.status_label:
            color_map = {
                "info": self.theme.SECONDARY_TEXT_COLOR,
                "success": self.theme.SUCCESS_COLOR,
                "warning": self.theme.WARNING_COLOR,
                "error": self.theme.ERROR_COLOR
            }
            color = color_map.get(level, self.theme.SECONDARY_TEXT_COLOR)
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"color: {color};")
        
        self.status_changed.emit(message, level)
        logger.debug(f"[{self.widget_id}] {level.upper()}: {message}")
    
    # AI请求处理
    
    async def process_ai_request(
        self, 
        request: AIRequest,
        stream: bool = None
    ) -> Optional[AIResponse]:
        """处理AI请求"""
        if self.is_busy():
            self._show_status("AI正在处理中，请稍候", "warning")
            return None
        
        if not self.ai_service:
            self._show_status("AI服务不可用", "error")
            self.set_state(AIWidgetState.DISABLED)
            return None
        
        try:
            self.set_state(AIWidgetState.PROCESSING)
            self._current_request_id = request.id
            
            # 记录请求历史
            self._request_history.append({
                "request_id": request.id,
                "prompt": request.prompt,
                "timestamp": request.created_at,
                "request_type": request.type.value
            })
            
            # 发送请求
            if stream or (stream is None and self.config.enable_streaming):
                self.set_state(AIWidgetState.STREAMING)
                # 流式处理在信号回调中处理
                async for chunk in self.ai_service.process_request_stream(request):
                    pass  # 实际处理在 _on_stream_chunk 中
                return None
            else:
                response = await self.ai_service.process_request(request)
                return response
                
        except Exception as e:
            logger.error(f"AI请求处理失败: {e}")
            self.set_state(AIWidgetState.ERROR)
            self._show_status(f"请求失败: {str(e)}", "error")
            return None
    
    # AI服务信号处理
    
    def _on_request_started(self, request_id: str):
        """请求开始"""
        if request_id == self._current_request_id:
            self.request_started.emit(request_id)
    
    def _on_request_completed(self, request_id: str, content: str):
        """请求完成"""
        if request_id == self._current_request_id:
            self.set_state(AIWidgetState.IDLE)
            self._current_request_id = None
            self.request_completed.emit(request_id, content)
            self._on_ai_response_received(content)
    
    def _on_request_failed(self, request_id: str, error: str):
        """请求失败"""
        if request_id == self._current_request_id:
            self.set_state(AIWidgetState.ERROR)
            self._current_request_id = None
            self.request_failed.emit(request_id, error)
            self._show_status(f"AI请求失败: {error}", "error")
    
    def _on_stream_chunk(self, request_id: str, chunk: str):
        """接收流式数据块"""
        if request_id == self._current_request_id:
            self._on_ai_stream_chunk(chunk)
    
    def _on_stream_completed(self, request_id: str):
        """流式响应完成"""
        if request_id == self._current_request_id:
            self.set_state(AIWidgetState.IDLE)
            self._current_request_id = None
            self._on_ai_stream_completed()
    
    # 子类可重写的方法
    
    def _on_ai_response_received(self, content: str):
        """AI响应接收完成 - 子类可重写"""
        pass
    
    def _on_ai_stream_chunk(self, chunk: str):
        """AI流式数据块 - 子类可重写"""
        pass
    
    def _on_ai_stream_completed(self):
        """AI流式响应完成 - 子类可重写"""
        pass
    
    # 工具方法
    
    def _create_action_button(
        self, 
        text: str, 
        tooltip: str = "", 
        color: str = None,
        min_height: int = 32
    ) -> QPushButton:
        """创建操作按钮"""
        button = QPushButton(text)
        if tooltip:
            button.setToolTip(tooltip)
        if color:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-height: {min_height}px;
                }}
                QPushButton:hover {{
                    background-color: {color}dd;
                }}
                QPushButton:pressed {{
                    background-color: {color}bb;
                }}
                QPushButton:disabled {{
                    background-color: {self.theme.BORDER_COLOR};
                    color: {self.theme.SECONDARY_TEXT_COLOR};
                }}
            """)
        else:
            button.setMinimumHeight(min_height)
        return button
    
    def _create_text_area(
        self, 
        placeholder: str = "", 
        read_only: bool = False,
        max_height: int = None
    ) -> QTextEdit:
        """创建文本区域"""
        text_edit = QTextEdit()
        if placeholder:
            text_edit.setPlaceholderText(placeholder)
        text_edit.setReadOnly(read_only)
        if max_height:
            text_edit.setMaximumHeight(max_height)
        
        # 设置字体
        font = QFont("Consolas", 10)
        text_edit.setFont(font)

        return text_edit

    # 新增优化方法

    def _setup_shortcuts(self):
        """设置快捷键"""
        if not self.config.enable_shortcuts:
            return

        from PyQt6.QtGui import QShortcut, QKeySequence

        # Ctrl+Enter: 提交请求
        submit_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        submit_shortcut.activated.connect(self._on_submit_shortcut)

        # Escape: 取消请求
        cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        cancel_shortcut.activated.connect(self._on_cancel_shortcut)

        # Ctrl+L: 清空输入
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self._on_clear_shortcut)

    def _on_submit_shortcut(self):
        """提交快捷键处理"""
        self.shortcut_triggered.emit("submit")

    def _on_cancel_shortcut(self):
        """取消快捷键处理"""
        if self._current_request_id:
            self.cancel_current_request()
        self.shortcut_triggered.emit("cancel")

    def _on_clear_shortcut(self):
        """清空快捷键处理"""
        if self.input_widget:
            self.input_widget.clear()
        self.shortcut_triggered.emit("clear")

    def _on_debounce_timeout(self):
        """防抖超时处理"""
        # 子类可以重写此方法实现防抖逻辑
        pass

    def _update_performance_stats(self):
        """更新性能统计"""
        if not self.config.show_performance_stats:
            return

        stats = self.get_performance_stats()
        # 可以在状态栏显示统计信息
        if hasattr(self, 'status_label') and self.status_label:
            success_rate = stats.get('success_rate', 0) * 100
            self.status_label.setText(
                f"请求: {stats.get('total_requests', 0)} | "
                f"成功率: {success_rate:.1f}%"
            )

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            'total_requests': self._request_count,
            'success_count': self._success_count,
            'error_count': self._error_count,
            'success_rate': self._success_count / max(self._request_count, 1),
            'current_state': self._state.value,
            'is_busy': self._is_busy
        }

    def reset_performance_stats(self):
        """重置性能统计"""
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        logger.info(f"AI组件 {self.widget_id} 性能统计已重置")

    def set_priority(self, priority: AIWidgetPriority):
        """设置组件优先级"""
        self.priority = priority
        logger.debug(f"AI组件 {self.widget_id} 优先级设置为: {priority.name}")

    def enable_compact_mode(self, enabled: bool = True):
        """启用/禁用紧凑模式"""
        self.config.compact_mode = enabled
        self._apply_theme()  # 重新应用主题
        logger.debug(f"AI组件 {self.widget_id} 紧凑模式: {'启用' if enabled else '禁用'}")

    def show_suggestions(self, suggestions: List[str]):
        """显示建议"""
        if not self.config.enable_suggestions:
            return

        # 子类可以重写此方法实现建议显示
        for suggestion in suggestions:
            logger.debug(f"建议: {suggestion}")

    def cancel_current_request(self) -> bool:
        """取消当前请求"""
        if self._current_request_id and self.ai_service:
            try:
                # 尝试取消请求
                success = self.ai_service.cancel_request(self._current_request_id)
                if success:
                    self.set_state(AIWidgetState.CANCELLED)
                    self._current_request_id = None
                    self._is_busy = False
                    self.request_cancelled.emit(self._current_request_id or "")
                    self._show_status("请求已取消", "info")
                    return True
            except Exception as e:
                logger.error(f"取消请求失败: {e}")

        return False

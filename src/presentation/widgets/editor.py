#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编辑器组件

富文本编辑器，支持多种编辑功能
"""

import time
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QTabWidget,
    QLabel, QToolBar, QFrame, QSplitter, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QTextDocument, QAction

from src.domain.entities.document import Document, DocumentType
from src.presentation.widgets.syntax_highlighter import NovelSyntaxHighlighter, MarkdownSyntaxHighlighter
from src.presentation.widgets.virtual_text_editor import VirtualTextEditor, get_virtual_editor_manager
from src.application.services.document_preloader import get_document_preloader
from src.shared.monitoring.performance_monitor import get_performance_monitor, monitor_performance
from src.shared.utils.logger import get_logger
from src.shared.utils.thread_safety import ensure_main_thread

logger = get_logger(__name__)


class DocumentTab(QWidget):
    """
    文档标签页

    单个文档的编辑界面，包含文本编辑器和AI助手面板。
    提供语法高亮、自动保存和AI辅助功能。

    实现方式：
    - 使用QTextEdit作为主要编辑器
    - 集成语法高亮器提供代码着色
    - 支持AI助手面板的动态加载
    - 提供自动保存和手动保存功能
    - 实时统计字数和内容变化

    Attributes:
        document: 关联的文档实例
        ai_assistant: AI助手实例（可选）
        ai_panel: AI助手面板
        syntax_highlighter: 语法高亮器
        auto_save_timer: 自动保存定时器

    Signals:
        content_changed: 内容变化信号(document_id, content)
        word_count_changed: 字数变化信号
        save_requested: 保存请求信号
    """

    content_changed = pyqtSignal(str, str)  # document_id, content
    word_count_changed = pyqtSignal(int)
    save_requested = pyqtSignal(object)  # document
    selection_changed = pyqtSignal(str, str)  # document_id, selected_text
    cursor_position_changed = pyqtSignal(str, int)  # document_id, position

    def __init__(self, document: Document, ai_assistant: Optional['DocumentAIAssistant'] = None):
        """
        初始化文档标签页

        Args:
            document: 要编辑的文档实例
            ai_assistant: AI助手实例（可选）
        """
        super().__init__()
        self.document = document
        self.ai_assistant = ai_assistant
        self.ai_panel = None
        self.syntax_highlighter = None

        # 虚拟化编辑器支持
        self.use_virtual_editor = self._should_use_virtual_editor()
        self.virtual_editor = None

        self._setup_ui()
        self._setup_connections()
        self._setup_syntax_highlighting()

        # 🔧 修复：直接创建AI面板，不依赖ai_assistant
        # 使用新的统一AI服务架构
        self._setup_ai_panel_async()

        # 自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.setSingleShot(True)

        logger.debug(f"文档标签页创建: {document.title} (虚拟化: {self.use_virtual_editor})")

    def _should_use_virtual_editor(self) -> bool:
        """判断是否应该使用虚拟化编辑器"""
        try:
            # 基于文档大小决定
            content_length = len(self.document.content) if self.document.content else 0
            line_count = self.document.content.count('\n') + 1 if self.document.content else 1

            # 超过50K字符或2000行使用虚拟化编辑器
            should_use_virtual = content_length > 50000 or line_count > 2000

            logger.debug(f"文档大小评估: {content_length} 字符, {line_count} 行, 使用虚拟化: {should_use_virtual}")
            return should_use_virtual

        except Exception as e:
            logger.error(f"判断虚拟化编辑器使用失败: {e}")
            return False

    def _load_content_async(self):
        """异步加载文档内容（优化版本）"""
        try:
            from PyQt6.QtCore import QTimer
            import time

            # 开始性能监控
            monitor = get_performance_monitor()
            operation_id = monitor.start_operation(
                f"document_load_{self.document.id}",
                "document_load",
                {
                    'document_id': self.document.id,
                    'document_title': self.document.title,
                    'use_virtual_editor': self.use_virtual_editor
                }
            )

            start_time = time.time()
            content_length = len(self.document.content) if self.document.content else 0
            line_count = self.document.content.count('\n') + 1 if self.document.content else 1

            logger.info(f"📝 开始优化异步加载: {self.document.title} ({content_length} 字符, {line_count} 行)")

            # 使用统一的性能阈值决定加载策略
            from src.shared.constants import SMALL_DOCUMENT_THRESHOLD, LARGE_DOCUMENT_THRESHOLD

            if self.use_virtual_editor or content_length > LARGE_DOCUMENT_THRESHOLD:
                # 使用虚拟化编辑器加载大文档
                self._load_with_virtual_editor(operation_id)
            elif content_length < SMALL_DOCUMENT_THRESHOLD:
                # 小文档直接同步加载
                self._load_small_document_direct(start_time, operation_id)
            else:
                # 中等文档使用优化的分块加载
                self._load_medium_document_chunked(start_time, operation_id)

        except Exception as e:
            logger.error(f"❌ 异步内容加载失败: {e}")
            # 结束性能监控（失败）
            monitor.end_operation(operation_id, "document_load", False, {'error': str(e)})
            # 回退到同步加载
            self._fallback_sync_load()

    def _load_with_virtual_editor(self, operation_id: str):
        """使用虚拟化编辑器加载"""
        try:
            logger.info(f"🚀 使用虚拟化编辑器加载大文档: {self.document.title}")

            # 创建虚拟化编辑器
            manager = get_virtual_editor_manager()
            self.virtual_editor = manager.create_editor(self.document.id, self)

            # 连接虚拟化编辑器信号
            self.virtual_editor.loading_completed.connect(
                lambda load_time: self._on_virtual_load_completed(load_time, operation_id)
            )
            self.virtual_editor.viewport_changed.connect(self._on_viewport_changed)

            # 替换原有的text_edit
            self._replace_text_editor_with_virtual()

            # 开始虚拟化加载
            self.virtual_editor.load_document_virtual(self.document)

            # 触发预加载相邻文档
            self._trigger_adjacent_preload()

        except Exception as e:
            logger.error(f"虚拟化编辑器加载失败: {e}")
            # 结束性能监控（失败）
            monitor = get_performance_monitor()
            monitor.end_operation(operation_id, "document_load", False, {'error': str(e)})
            # 回退到普通加载
            self._fallback_sync_load()

    def _load_small_document_direct(self, start_time: float, operation_id: str):
        """直接加载小文档"""
        try:
            self.text_edit.setPlainText(self.document.content)
            self._update_word_count()

            load_time = time.time() - start_time

            # 结束性能监控（成功）
            monitor = get_performance_monitor()
            monitor.end_operation(operation_id, "document_load", True, {
                'load_time': load_time,
                'content_length': len(self.document.content) if self.document.content else 0,
                'load_strategy': 'direct'
            })

            logger.info(f"⚡ 小文档同步加载完成: {load_time:.3f}秒")

        except Exception as e:
            logger.error(f"小文档加载失败: {e}")
            # 结束性能监控（失败）
            monitor = get_performance_monitor()
            monitor.end_operation(operation_id, "document_load", False, {'error': str(e)})
            self._fallback_sync_load()

    def _load_medium_document_chunked(self, start_time: float, operation_id: str):
        """分块加载中等文档"""
        try:
            def load_in_chunks():
                try:
                    # 先显示加载提示
                    self.text_edit.setPlainText("正在加载文档内容...")

                    def actual_load():
                        try:
                            # 优化的分块设置内容
                            self.text_edit.setPlainText(self.document.content)
                            self._update_word_count()

                            load_time = time.time() - start_time

                            # 结束性能监控（成功）
                            monitor = get_performance_monitor()
                            monitor.end_operation(operation_id, "document_load", True, {
                                'load_time': load_time,
                                'content_length': len(self.document.content) if self.document.content else 0,
                                'load_strategy': 'chunked'
                            })

                            logger.info(f"⚡ 中等文档分块加载完成: {load_time:.3f}秒")

                            # 触发预加载
                            self._trigger_adjacent_preload()

                        except Exception as e:
                            logger.error(f"❌ 文档内容加载失败: {e}")
                            # 结束性能监控（失败）
                            monitor = get_performance_monitor()
                            monitor.end_operation(operation_id, "document_load", False, {'error': str(e)})
                            self.text_edit.setPlainText(f"加载失败: {e}")

                    # 延迟加载实际内容
                    QTimer.singleShot(100, actual_load)  # 100ms延迟

                except Exception as e:
                    logger.error(f"❌ 分块加载失败: {e}")
                    self._fallback_sync_load()

            # 立即开始分块加载
            QTimer.singleShot(0, load_in_chunks)

        except Exception as e:
            logger.error(f"中等文档分块加载失败: {e}")
            self._fallback_sync_load()







    def _fallback_sync_load(self):
        """回退到同步加载"""
        try:
            self.text_edit.setPlainText(self.document.content or "")
            self._update_word_count()
            logger.info("回退到同步加载完成")
        except Exception as e:
            logger.error(f"同步加载也失败: {e}")
            self.text_edit.setPlainText("文档加载失败")

    def _replace_text_editor_with_virtual(self):
        """将普通编辑器替换为虚拟化编辑器"""
        try:
            if not self.virtual_editor:
                return

            # 获取当前布局
            layout = self.main_splitter.widget(0).parent().layout()
            if layout:
                # 移除原有的text_edit
                old_text_edit = self.text_edit
                layout.removeWidget(old_text_edit)
                old_text_edit.setParent(None)

                # 添加虚拟化编辑器
                self.text_edit = self.virtual_editor
                self.main_splitter.insertWidget(0, self.virtual_editor)

                # 重新连接信号
                self._setup_connections()

                logger.debug("已替换为虚拟化编辑器")

        except Exception as e:
            logger.error(f"替换虚拟化编辑器失败: {e}")

    def _trigger_adjacent_preload(self):
        """触发相邻文档预加载"""
        try:
            if not self.document.project_id:
                return

            # 获取预加载器
            preloader = get_document_preloader()
            if preloader:
                # 记录文档访问
                preloader.record_document_access(self.document.id)

                # 异步预加载相邻文档
                QTimer.singleShot(1000, lambda: asyncio.create_task(
                    preloader.preload_adjacent_documents(self.document.id, self.document.project_id)
                ))

                logger.debug(f"已触发相邻文档预加载: {self.document.id}")

        except Exception as e:
            logger.error(f"触发预加载失败: {e}")

    def _on_virtual_load_completed(self, load_time: float, operation_id: str):
        """虚拟化加载完成处理"""
        try:
            self._update_word_count()

            # 结束性能监控（成功）
            monitor = get_performance_monitor()
            monitor.end_operation(operation_id, "document_load", True, {
                'load_time': load_time,
                'content_length': len(self.document.content) if self.document.content else 0,
                'line_count': self.document.content.count('\n') + 1 if self.document.content else 1
            })

            logger.info(f"✅ 虚拟化加载完成: {self.document.title}, 耗时: {load_time:.3f}秒")

        except Exception as e:
            logger.error(f"虚拟化加载完成处理失败: {e}")

    def _on_viewport_changed(self, start_line: int, end_line: int):
        """视口变化处理"""
        try:
            logger.debug(f"视口变化: 行{start_line}-{end_line}")
            # 可以在这里添加额外的视口变化处理逻辑

        except Exception as e:
            logger.error(f"视口变化处理失败: {e}")

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 文档信息栏
        info_frame = QFrame()
        info_frame.setMaximumHeight(30)
        info_frame.setStyleSheet("")  # 使用主题样式
        
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 5, 10, 5)
        
        # 文档标题
        self.title_label = QLabel(self.document.title)
        self.title_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.title_label)
        
        info_layout.addStretch()
        
        # 字数统计
        self.word_count_label = QLabel("0 字")
        self.word_count_label.setStyleSheet("font-size: 10pt;")
        info_layout.addWidget(self.word_count_label)

        # AI状态指示器（如果有AI助手）
        if self.ai_assistant:
            self.ai_status_label = QLabel("🤖 AI就绪")
            self.ai_status_label.setStyleSheet("font-size: 10pt; color: #4CAF50;")
            info_layout.addWidget(self.ai_status_label)

        layout.addWidget(info_frame)

        # 始终使用分割器布局（为后续AI面板做准备）
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 文本编辑器 - 根据文档大小选择编辑器类型
        if self.use_virtual_editor:
            # 创建虚拟化编辑器（稍后在_load_content_async中初始化）
            self.text_edit = QTextEdit()  # 临时占位符
            self._setup_text_edit()
            self.main_splitter.addWidget(self.text_edit)
            logger.debug(f"将使用虚拟化编辑器: {self.document.title}")
        else:
            # 创建普通编辑器
            self.text_edit = QTextEdit()
            self._setup_text_edit()
            self.main_splitter.addWidget(self.text_edit)
            logger.debug(f"使用普通编辑器: {self.document.title}")

        # AI面板将在_setup_ai_panel中添加（如果有AI助手）
        layout.addWidget(self.main_splitter)

        # 如果有AI助手，立即设置AI面板
        if self.ai_assistant:
            self._setup_ai_panel()
        
        # 异步加载文档内容以提高响应性
        self._load_content_async()

    def _setup_ai_panel(self):
        """设置AI面板（已废弃：统一由 MainWindow 的 AI Studio 页面承载）"""
        try:
            logger.info("Editor 不再创建或嵌入文档 AI 面板，所有 AI 交互集中到 AI Studio 页面。")
        except Exception:
            pass
        # 直接返回，避免旧逻辑
        return

    def _setup_ai_panel_async(self):
        """异步设置AI面板"""
        try:
            from PyQt6.QtCore import QTimer

            logger.info(f"🤖 开始异步设置AI面板: {self.document.title}")

            def setup_ai_panel():
                try:
                    # 🔧 新逻辑：直接使用统一AI服务创建AI面板
                    self._create_ai_panel_with_unified_service()
                    logger.info(f"✅ AI面板异步设置完成: {self.document.title}")
                except Exception as e:
                    logger.error(f"❌ AI面板异步设置失败: {e}")
                    # 如果失败，创建占位符
                    self._prepare_ai_panel_space()

            # 延迟设置AI面板，让主要UI先显示
            QTimer.singleShot(200, setup_ai_panel)  # 200ms延迟

        except Exception as e:
            logger.error(f"❌ 异步AI面板设置失败: {e}")
            # 回退到创建占位符
            self._prepare_ai_panel_space()

    def _prepare_ai_panel_space(self):
        """预留AI面板空间"""
        try:
            # 创建一个占位符标签，表示AI面板将在此处显示
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt

            placeholder = QLabel("🤖 AI助手正在初始化...")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    background-color: #f5f5f5;
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                    color: #666;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
            placeholder.setMinimumWidth(250)

            # 添加到分割器
            if hasattr(self, 'main_splitter'):
                self.main_splitter.addWidget(placeholder)
                # 设置分割器比例（编辑器:占位符 = 3:1）
                self.main_splitter.setSizes([600, 200])
                self.main_splitter.setCollapsible(1, True)  # 占位符可折叠

                # 保存占位符引用，以便后续替换
                self._ai_panel_placeholder = placeholder

            logger.debug("AI面板占位符已创建")

        except Exception as e:
            logger.error(f"创建AI面板占位符失败: {e}")

    def _create_ai_panel_with_unified_service(self):
        """使用统一AI服务创建AI面板"""
        try:
            # 移除占位符（如果存在）
            if hasattr(self, '_ai_panel_placeholder') and self._ai_panel_placeholder:
                self._ai_panel_placeholder.setParent(None)
                self._ai_panel_placeholder.deleteLater()
                self._ai_panel_placeholder = None
                logger.debug("AI面板占位符已移除")

            # 尝试获取AI服务（使用新架构）
            ai_service = None

            # 方法1：尝试使用兼容性AI服务
            try:
                from src.application.services.ai import get_ai_service
                # 创建基本配置用于兼容性接口
                config = {
                    'providers': {
                        'deepseek': {
                            'api_key': '',
                            'base_url': 'https://api.deepseek.com/v1',
                            'default_model': 'deepseek-chat'
                        }
                    },
                    'default_provider': 'deepseek'
                }
                ai_service = get_ai_service(config)
                logger.debug("从兼容性接口获取AI服务成功")
            except Exception as e:
                logger.debug(f"从兼容性接口获取AI服务失败: {e}")

            # 方法2：尝试直接创建AI编排服务（如果可用）
            if not ai_service:
                try:
                    from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
                    # 创建基本配置
                    config = {
                        'providers': {
                            'deepseek': {
                                'api_key': '',
                                'base_url': 'https://api.deepseek.com/v1',
                                'default_model': 'deepseek-chat'
                            }
                        },
                        'default_provider': 'deepseek'
                    }
                    ai_service = AIOrchestrationService(config)
                    logger.debug("创建AI编排服务成功")
                except Exception as e:
                    logger.debug(f"创建AI编排服务失败: {e}")

            # 为了兼容性，将ai_service赋值给unified_ai_service
            unified_ai_service = ai_service

            if unified_ai_service:
                # Editor 不再嵌入文档 AI 面板，统一在 MainWindow 的 AI Studio 页面操作
                logger.info("统一AI服务可用：由 AI Studio 页面统一承载文档相关功能，不再在 Editor 内嵌面板")
                return True
            else:
                logger.warning("无法获取统一AI服务")
                return False

        except Exception as e:
            logger.error(f"使用统一AI服务创建AI面板失败: {e}")
            return False

    def set_ai_assistant(self, ai_assistant):
        """
        设置AI助手（用于后续设置）

        Args:
            ai_assistant: AI助手实例
        """
        try:
            self.ai_assistant = ai_assistant

            # 如果已经有AI面板，不需要重新创建
            if hasattr(self, 'ai_panel') and self.ai_panel:
                logger.debug("AI面板已存在，无需重新创建")
                return

            # 移除占位符（如果存在）
            if hasattr(self, '_ai_panel_placeholder') and self._ai_panel_placeholder:
                self._ai_panel_placeholder.setParent(None)
                self._ai_panel_placeholder.deleteLater()
                self._ai_panel_placeholder = None

            # 创建AI面板
            self._setup_ai_panel()

            logger.info(f"AI助手已设置并创建AI面板: {self.document.title}")

        except Exception as e:
            logger.error(f"设置AI助手失败: {e}")

    @ensure_main_thread
    def _insert_ai_text(self, text: str, position: int = -1):
        """插入AI生成的文本（强制主线程）"""
        try:
            cursor = self.text_edit.textCursor()

            if position >= 0:
                # 移动到指定位置
                cursor.setPosition(position)
                self.text_edit.setTextCursor(cursor)

            cursor.insertText(text)
            self.text_edit.setTextCursor(cursor)
            logger.debug(f"插入AI文本: {len(text)} 字符 (位置: {position})")
        except Exception as e:
            logger.error(f"插入AI文本失败: {e}")

    @ensure_main_thread
    def _replace_ai_text(self, text: str, start_pos: int = -1, end_pos: int = -1):
        """替换指定范围或选中的文本为AI生成的文本（强制主线程）"""
        try:
            cursor = self.text_edit.textCursor()

            if start_pos >= 0 and end_pos >= 0:
                # 替换指定范围的文本
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, cursor.MoveMode.KeepAnchor)
                cursor.insertText(text)
                self.text_edit.setTextCursor(cursor)
                logger.debug(f"替换AI文本: {len(text)} 字符 (范围: {start_pos}-{end_pos})")
            elif cursor.hasSelection():
                # 替换选中的文本
                cursor.insertText(text)
                self.text_edit.setTextCursor(cursor)
                logger.debug(f"替换选中AI文本: {len(text)} 字符")
            else:
                # 如果没有选择，则插入
                self._insert_ai_text(text)
        except Exception as e:
            logger.error(f"替换AI文本失败: {e}")

    @ensure_main_thread
    def _setup_syntax_highlighting(self):
        """设置语法高亮（强制主线程执行）"""
        try:
            # 根据文档类型选择合适的语法高亮器
            if self.document.type in [DocumentType.CHAPTER, DocumentType.NOTE]:
                self.syntax_highlighter = NovelSyntaxHighlighter(self.text_edit.document())
            elif self.document.type in [DocumentType.OUTLINE, DocumentType.CHARACTER, DocumentType.SETTING]:
                self.syntax_highlighter = MarkdownSyntaxHighlighter(self.text_edit.document())

            logger.debug(f"语法高亮设置完成: {self.document.type}")

        except Exception as e:
            logger.error(f"设置语法高亮失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def toggle_syntax_highlighting(self, enabled: bool):
        """切换语法高亮"""
        try:
            if self.syntax_highlighter:
                self.syntax_highlighter.set_enabled(enabled)

        except Exception as e:
            logger.error(f"切换语法高亮失败: {e}")

    def update_syntax_theme(self, is_dark_theme: bool):
        """更新语法高亮主题"""
        try:
            if self.syntax_highlighter:
                self.syntax_highlighter.update_theme(is_dark_theme)

        except Exception as e:
            logger.error(f"更新语法高亮主题失败: {e}")
    
    def _setup_text_edit(self):
        """设置文本编辑器"""
        # 设置字体
        font = QFont("Microsoft YaHei UI", 12)
        self.text_edit.setFont(font)

        # 设置行间距（通过文档格式）
        from PyQt6.QtGui import QTextBlockFormat
        block_format = QTextBlockFormat()
        # 使用整数值：0=SingleHeight, 1=ProportionalHeight, 2=FixedHeight
        block_format.setLineHeight(150, 1)  # 150% 行高，类型1表示比例高度
        cursor = self.text_edit.textCursor()
        cursor.select(cursor.SelectionType.Document)
        cursor.mergeBlockFormat(block_format)
        
        # 设置样式 - 使用主题颜色
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: none;
                padding: 20px;
                line-height: 1.8;
            }

            QTextEdit:focus {
                outline: none;
            }
        """)
        
        # 设置占位符
        self.text_edit.setPlaceholderText("开始你的创作...")
        
        # 启用拼写检查（如果可用）
        self.text_edit.setAcceptRichText(False)  # 纯文本模式
    
    def _setup_connections(self):
        """设置信号连接"""
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.cursorPositionChanged.connect(self._on_cursor_position_changed)
        self.text_edit.selectionChanged.connect(self._on_selection_changed)
    
    def _on_text_changed(self):
        """文本变更处理"""
        try:
            logger.debug(f"文本变更检测到: {self.document.title}")

            # 更新字数统计
            self._update_word_count()

            # 发出内容变更信号
            content = self.text_edit.toPlainText()
            self.content_changed.emit(self.document.id, content)

            # 更新AI面板上下文
            if self.ai_panel:
                selected_text = self.text_edit.textCursor().selectedText()
                cursor_position = self.text_edit.textCursor().position()

                # 使用新的上下文管理方法
                if hasattr(self.ai_panel, 'update_document_context_external'):
                    self.ai_panel.update_document_context_external(
                        document_id=self.document.id,
                        content=content,
                        selected_text=selected_text
                    )
                else:
                    # 回退到原有方法
                    self.ai_panel.set_context(content, selected_text)

            # 启动自动保存定时器
            self.auto_save_timer.start(2000)  # 2秒后自动保存
            logger.debug(f"自动保存定时器已启动: {self.document.title}")

        except Exception as e:
            logger.error(f"处理文本变更失败: {e}")

    def _on_selection_changed(self):
        """选中文字变化处理"""
        try:
            selected_text = self.text_edit.textCursor().selectedText()
            self.selection_changed.emit(self.document.id, selected_text)

            # 更新AI面板选中文字和上下文
            if self.ai_panel:
                if hasattr(self.ai_panel, 'update_document_context_external'):
                    # 使用增强的上下文更新方法
                    content = self.text_edit.toPlainText()
                    self.ai_panel.update_document_context_external(
                        document_id=self.document.id,
                        content=content,
                        selected_text=selected_text
                    )
                elif hasattr(self.ai_panel, 'set_selected_text'):
                    # 回退到原有方法
                    self.ai_panel.set_selected_text(selected_text)

        except Exception as e:
            logger.error(f"处理选中文字变化失败: {e}")

    def _on_cursor_position_changed(self):
        """光标位置变化处理"""
        try:
            cursor = self.text_edit.textCursor()
            position = cursor.position()
            self.cursor_position_changed.emit(self.document.id, position)

            # 更新AI面板光标位置
            if self.ai_panel and hasattr(self.ai_panel, 'update_cursor_position'):
                self.ai_panel.update_cursor_position(position)

        except Exception as e:
            logger.error(f"处理光标位置变化失败: {e}")

    def _update_word_count(self):
        """更新字数统计"""
        try:
            content = self.text_edit.toPlainText()
            
            # 计算字数（中文字符 + 英文单词）
            chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
            english_words = len([w for w in content.split() if w.strip() and any(c.isalpha() for c in w)])
            
            total_words = chinese_chars + english_words
            
            # 更新显示
            self.word_count_label.setText(f"{total_words} 字")
            
            # 发出字数变更信号
            self.word_count_changed.emit(total_words)
            
        except Exception as e:
            logger.error(f"更新字数统计失败: {e}")
    
    def _auto_save(self):
        """自动保存"""
        try:
            # 检查内容是否有变化
            current_content = self.text_edit.toPlainText()
            if current_content != self.document.content:
                # 更新文档内容
                self.document.content = current_content

                # 更新文档统计信息
                self.document.statistics.update_from_content(current_content)

                # 更新修改时间
                from datetime import datetime
                self.document.updated_at = datetime.now()

                # 发出保存请求信号
                self.save_requested.emit(self.document)

                logger.debug(f"自动保存文档: {self.document.title}, 字数: {self.document.statistics.word_count}")

        except Exception as e:
            logger.error(f"自动保存失败: {e}")

    def save_document(self):
        """手动保存文档"""
        try:
            # 停止自动保存定时器
            self.auto_save_timer.stop()

            # 更新文档内容
            current_content = self.text_edit.toPlainText()
            self.document.content = current_content

            # 更新文档统计信息
            self.document.statistics.update_from_content(current_content)

            # 更新修改时间
            from datetime import datetime
            self.document.updated_at = datetime.now()

            # 发出保存请求信号
            self.save_requested.emit(self.document)

            logger.info(f"手动保存文档: {self.document.title}, 字数: {self.document.statistics.word_count}")

        except Exception as e:
            logger.error(f"手动保存失败: {e}")

    def is_modified(self) -> bool:
        """检查文档是否已修改"""
        try:
            current_content = self.text_edit.toPlainText()
            return current_content != self.document.content
        except Exception as e:
            logger.error(f"检查修改状态失败: {e}")
            return False
    
    def get_content(self) -> str:
        """获取内容"""
        return self.text_edit.toPlainText()
    
    @ensure_main_thread
    def set_content(self, content: str):
        """设置内容（强制主线程）"""
        self.text_edit.setPlainText(content)
        self._update_word_count()

    @ensure_main_thread
    def insert_text(self, text: str):
        """插入文本（强制主线程）"""
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)

    def get_selected_text(self) -> str:
        """获取选中的文本"""
        return self.text_edit.textCursor().selectedText()
    
    @ensure_main_thread
    def replace_selected_text(self, text: str):
        """替换选中的文本（强制主线程）"""
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)

    def undo(self):
        """撤销"""
        self.text_edit.undo()
    
    def redo(self):
        """重做"""
        self.text_edit.redo()
    
    def copy(self):
        """复制"""
        self.text_edit.copy()
    
    def cut(self):
        """剪切"""
        self.text_edit.cut()
    
    def paste(self):
        """粘贴"""
        self.text_edit.paste()
    
    def select_all(self):
        """全选"""
        self.text_edit.selectAll()
    
    def find_text(self, text: str, case_sensitive: bool = False, whole_word: bool = False, backward: bool = False) -> bool:
        """查找文本"""
        # PyQt6 使用 QTextDocument.FindFlag
        from PyQt6.QtGui import QTextDocument
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_word:
            flags |= QTextDocument.FindFlag.FindWholeWords
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward

        return self.text_edit.find(text, flags)

    def replace_text(self, find_text: str, replace_text: str, case_sensitive: bool = False, whole_word: bool = False) -> int:
        """替换当前选中的文本"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == find_text:
            cursor.insertText(replace_text)
            return 1
        return 0

    def replace_all_text(self, find_text: str, replace_text: str, case_sensitive: bool = False, whole_word: bool = False) -> int:
        """替换所有匹配的文本"""
        count = 0
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.text_edit.setTextCursor(cursor)

        # PyQt6 使用 QTextDocument.FindFlag
        from PyQt6.QtGui import QTextDocument
        flags = QTextDocument.FindFlag(0)
        if case_sensitive:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_word:
            flags |= QTextDocument.FindFlag.FindWholeWords

        while self.text_edit.find(find_text, flags):
            cursor = self.text_edit.textCursor()
            cursor.insertText(replace_text)
            count += 1

        return count

    def find_next(self, text: str, case_sensitive: bool = False, whole_word: bool = False) -> bool:
        """查找下一个"""
        return self.find_text(text, case_sensitive, whole_word, False)

    def find_previous(self, text: str, case_sensitive: bool = False, whole_word: bool = False) -> bool:
        """查找上一个"""
        return self.find_text(text, case_sensitive, whole_word, True)

    def highlight_all_matches(self, text: str, case_sensitive: bool = False, whole_word: bool = False):
        """高亮所有匹配项"""
        # 这个功能需要更复杂的实现，暂时留空
        pass

    def clear_highlights(self):
        """清除所有高亮"""
        # 这个功能需要更复杂的实现，暂时留空
        pass


class EditorWidget(QWidget):
    """
    编辑器组件

    多文档编辑器的主要组件，使用标签页管理多个文档。
    提供文档的创建、打开、编辑和保存功能。

    实现方式：
    - 使用QTabWidget管理多个文档标签页
    - 为每个文档创建独立的DocumentTab
    - 提供统一的信号接口
    - 支持文档的动态添加和移除
    - 集成AI助手功能

    Attributes:
        tab_widget: 标签页组件
        ai_assistant_manager: AI助手管理器

    Signals:
        content_changed: 内容变化信号(document_id, content)
        word_count_changed: 字数变化信号
        save_requested: 保存请求信号
        document_closed: 文档关闭信号
    """

    # 信号定义
    content_changed = pyqtSignal(str, str)  # document_id, content
    word_count_changed = pyqtSignal(int)
    document_switched = pyqtSignal(str)  # document_id
    save_requested = pyqtSignal(object)  # document
    selection_changed = pyqtSignal(str, str)  # document_id, selected_text
    cursor_position_changed = pyqtSignal(str, int)  # document_id, position

    def __init__(self, ai_assistant_manager=None):
        super().__init__()
        self.ai_assistant_manager = ai_assistant_manager
        self._setup_ui()
        self._setup_connections()
        self._document_tabs: dict[str, DocumentTab] = {}

        logger.debug("编辑器组件初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        self.toolbar = QToolBar()
        # 工具栏使用主题样式
        self.toolbar.setStyleSheet("")
        
        # 添加工具栏按钮
        self._create_toolbar_actions()
        layout.addWidget(self.toolbar)
        
        # 标签页组件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        # 标签页使用主题样式
        self.tab_widget.setStyleSheet("")
        
        layout.addWidget(self.tab_widget)
        
        # 欢迎页面
        self._create_welcome_page()
    
    def _create_toolbar_actions(self):
        """创建工具栏动作"""
        # 撤销
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        self.toolbar.addAction(undo_action)
        
        # 重做
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        self.toolbar.addAction(redo_action)
        
        self.toolbar.addSeparator()
        
        # 复制
        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)
        self.toolbar.addAction(copy_action)
        
        # 剪切
        cut_action = QAction("剪切", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut)
        self.toolbar.addAction(cut_action)
        
        # 粘贴
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste)
        self.toolbar.addAction(paste_action)
        
        self.toolbar.addSeparator()
        
        # 查找
        find_action = QAction("查找", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_dialog)
        self.toolbar.addAction(find_action)
    
    def _create_welcome_page(self):
        """创建欢迎页面"""
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.setSpacing(30)

        # 检查是否有当前项目
        current_project = self._get_current_project()

        if current_project:
            # 项目已打开，显示项目相关的欢迎信息
            self._create_project_welcome_content(welcome_layout, current_project)
        else:
            # 没有项目，显示通用欢迎信息
            self._create_general_welcome_content(welcome_layout)

        self.tab_widget.addTab(welcome_widget, "欢迎")

    def _get_current_project(self):
        """获取当前项目"""
        try:
            # 尝试从全局容器获取项目服务
            from src.shared.ioc.container import get_global_container
            container = get_global_container()
            if container:
                from src.application.services.project_service import ProjectService
                project_service = container.get(ProjectService)
                if project_service and project_service.has_current_project:
                    return project_service.current_project
        except Exception as e:
            logger.debug(f"获取当前项目失败: {e}")
        return None

    def _create_project_welcome_content(self, layout, project):
        """创建项目相关的欢迎内容"""
        # 项目信息
        project_info = QLabel(f"""
        <div style="text-align: center;">
            <h2>📚 {project.title}</h2>
            <p style="font-size: 12pt; color: #666; margin: 10px 0;">项目已打开</p>
        </div>
        """)
        project_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(project_info)

        # 提示文本（简化，无快速按钮）
        hint_label = QLabel("""
        <div style="text-align: center;">
            <p style="color: #888; font-size: 11pt;">
                从左侧项目树选择文档开始编辑
            </p>
        </div>
        """)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

    def _create_general_welcome_content(self, layout):
        """创建通用欢迎内容"""
        # 欢迎文本
        welcome_label = QLabel("""
        <div style="text-align: center;">
            <h2>🎨 AI小说编辑器 2.0</h2>
            <p style="font-size: 14pt; margin: 20px 0;">欢迎使用全新的创作工具</p>
            <p>从左侧项目树选择文档开始创作</p>
            <p>或者创建一个新项目开始你的写作之旅</p>
        </div>
        """)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)



    def _setup_connections(self):
        """设置信号连接"""
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def load_document(self, document: Document):
        """加载文档（优化版本）"""
        try:
            import time
            start_time = time.time()

            logger.info(f"📝 开始加载文档到编辑器: {document.title}")

            # 如果文档已经打开，快速切换到该标签页
            if document.id in self._document_tabs:
                tab = self._document_tabs[document.id]
                index = self.tab_widget.indexOf(tab)
                self.tab_widget.setCurrentIndex(index)
                logger.info(f"⚡ 快速切换到已打开文档: {document.title}")
                return

            # 立即创建标签页（最小化UI）
            tab = DocumentTab(document, None)  # 先不创建AI助手

            # 连接信号
            tab.content_changed.connect(self.content_changed)
            tab.word_count_changed.connect(self.word_count_changed)
            tab.save_requested.connect(self.save_requested)
            tab.selection_changed.connect(self.selection_changed)
            tab.cursor_position_changed.connect(self.cursor_position_changed)

            # 立即添加到标签页组件
            index = self.tab_widget.addTab(tab, document.title)
            self.tab_widget.setCurrentIndex(index)

            # 记录标签页
            self._document_tabs[document.id] = tab

            # 如果这是第一个文档，移除欢迎页面
            if len(self._document_tabs) == 1 and self.tab_widget.count() > 1:
                self.tab_widget.removeTab(0)  # 移除欢迎页面

            ui_time = time.time() - start_time
            logger.info(f"⚡ 文档UI创建完成: {document.title} - 耗时: {ui_time:.3f}s")

            # 🔧 修复：不再依赖ai_assistant_manager，AI面板已在DocumentTab中创建

        except Exception as e:
            logger.error(f"❌ 加载文档失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _create_ai_assistant_async(self, document_id: str, tab: 'DocumentTab'):
        """异步创建AI助手"""
        try:
            from PyQt6.QtCore import QTimer

            def create_assistant():
                try:
                    logger.info(f"🤖 开始创建AI助手: {document_id}")
                    ai_assistant = self.ai_assistant_manager.create_assistant(document_id)

                    # 使用新的设置方法
                    if hasattr(tab, 'set_ai_assistant'):
                        tab.set_ai_assistant(ai_assistant)
                    else:
                        # 回退到直接设置
                        tab.ai_assistant = ai_assistant
                        if hasattr(tab, '_setup_ai_panel'):
                            tab._setup_ai_panel()

                    logger.info(f"✅ AI助手创建完成: {document_id}")
                except Exception as e:
                    logger.error(f"❌ AI助手创建失败: {e}")

            # 延迟创建AI助手
            QTimer.singleShot(300, create_assistant)  # 300ms延迟

        except Exception as e:
            logger.error(f"❌ 异步AI助手创建失败: {e}")
    
    def _close_tab(self, index: int):
        """关闭标签页"""
        try:
            widget = self.tab_widget.widget(index)
            if isinstance(widget, DocumentTab):
                # 从记录中移除
                document_id = widget.document.id
                if document_id in self._document_tabs:
                    del self._document_tabs[document_id]

                # 清理AI助手
                if self.ai_assistant_manager:
                    self.ai_assistant_manager.remove_assistant(document_id)
                    logger.info(f"移除文档 {document_id} 的AI助手")

                logger.info(f"文档标签页已关闭: {widget.document.title}")
            
            # 移除标签页
            self.tab_widget.removeTab(index)
            
            # 如果没有文档了，显示欢迎页面
            if len(self._document_tabs) == 0:
                self._create_welcome_page()

        except Exception as e:
            logger.error(f"关闭标签页失败: {e}")

    def close_document(self, document_id: str):
        """通过文档ID关闭文档"""
        try:
            if document_id in self._document_tabs:
                tab = self._document_tabs[document_id]
                index = self.tab_widget.indexOf(tab)
                if index >= 0:
                    self._close_tab(index)
                    logger.info(f"文档已关闭: {document_id}")
        except Exception as e:
            logger.error(f"关闭文档失败: {e}")

    def close_all_documents(self):
        """关闭所有打开的文档"""
        try:
            logger.info(f"🗂️ 开始关闭所有文档，当前打开: {len(self._document_tabs)} 个")

            # 获取所有文档ID的副本，避免在迭代时修改字典
            document_ids = list(self._document_tabs.keys())

            for document_id in document_ids:
                self.close_document(document_id)

            # 确保所有标签页都被移除（除了欢迎页面）
            while self.tab_widget.count() > 0:
                widget = self.tab_widget.widget(0)
                if isinstance(widget, DocumentTab):
                    self.tab_widget.removeTab(0)
                else:
                    break  # 遇到非文档标签页（如欢迎页面）就停止

            # 清空文档标签页记录
            self._document_tabs.clear()

            # 显示欢迎页面（会根据当前项目状态显示不同内容）
            if self.tab_widget.count() == 0:
                self._create_welcome_page()

            logger.info("✅ 所有文档已关闭，欢迎页面已刷新")

        except Exception as e:
            logger.error(f"❌ 关闭所有文档失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def refresh_welcome_page(self):
        """刷新欢迎页面（在项目状态改变时调用）"""
        try:
            # 如果当前只有欢迎页面，则刷新它
            if self.tab_widget.count() == 1 and self.tab_widget.tabText(0) == "欢迎":
                self.tab_widget.clear()
                self._create_welcome_page()
                logger.info("欢迎页面已刷新")
        except Exception as e:
            logger.error(f"刷新欢迎页面失败: {e}")

    def _on_tab_changed(self, index: int):
        """标签页切换"""
        try:
            widget = self.tab_widget.widget(index)
            if isinstance(widget, DocumentTab):
                self.document_switched.emit(widget.document.id)
                
        except Exception as e:
            logger.error(f"处理标签页切换失败: {e}")
    
    def get_current_tab(self) -> Optional[DocumentTab]:
        """获取当前标签页"""
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, DocumentTab):
            return current_widget
        return None

    def get_current_document(self) -> Optional['Document']:
        """获取当前文档"""
        tab = self.get_current_tab()
        if tab:
            return tab.document
        return None

    @ensure_main_thread
    def save_current_document(self):
        """保存当前文档（强制主线程）"""
        tab = self.get_current_tab()
        if tab:
            tab.save_document()
        else:
            logger.warning("没有当前文档可以保存")

    def undo(self):
        """撤销"""
        tab = self.get_current_tab()
        if tab:
            tab.undo()
    
    def redo(self):
        """重做"""
        tab = self.get_current_tab()
        if tab:
            tab.redo()
    
    def copy(self):
        """复制"""
        tab = self.get_current_tab()
        if tab:
            tab.copy()
    
    def cut(self):
        """剪切"""
        tab = self.get_current_tab()
        if tab:
            tab.cut()
    
    def paste(self):
        """粘贴"""
        tab = self.get_current_tab()
        if tab:
            tab.paste()
    
    def show_find_dialog(self):
        """显示查找对话框"""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox, QLabel
            from PyQt6.QtCore import Qt

            # 创建查找对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("查找和替换")
            dialog.setModal(False)
            dialog.resize(400, 200)

            layout = QVBoxLayout(dialog)

            # 查找输入
            find_layout = QHBoxLayout()
            find_layout.addWidget(QLabel("查找:"))
            find_input = QLineEdit()
            find_layout.addWidget(find_input)
            layout.addLayout(find_layout)

            # 替换输入
            replace_layout = QHBoxLayout()
            replace_layout.addWidget(QLabel("替换:"))
            replace_input = QLineEdit()
            replace_layout.addWidget(replace_input)
            layout.addLayout(replace_layout)

            # 选项
            options_layout = QHBoxLayout()
            case_sensitive = QCheckBox("区分大小写")
            whole_word = QCheckBox("全字匹配")
            options_layout.addWidget(case_sensitive)
            options_layout.addWidget(whole_word)
            layout.addLayout(options_layout)

            # 按钮
            button_layout = QHBoxLayout()
            find_next_btn = QPushButton("查找下一个")
            find_prev_btn = QPushButton("查找上一个")
            replace_btn = QPushButton("替换")
            replace_all_btn = QPushButton("全部替换")
            close_btn = QPushButton("关闭")

            button_layout.addWidget(find_next_btn)
            button_layout.addWidget(find_prev_btn)
            button_layout.addWidget(replace_btn)
            button_layout.addWidget(replace_all_btn)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)

            # 连接信号
            def find_next():
                text = find_input.text()
                if text:
                    tab = self.get_current_tab()
                    if tab and hasattr(tab, 'find_text'):
                        tab.find_text(text, case_sensitive.isChecked(), whole_word.isChecked())

            def find_previous():
                text = find_input.text()
                if text:
                    tab = self.get_current_tab()
                    if tab and hasattr(tab, 'find_text'):
                        tab.find_text(text, case_sensitive.isChecked(), whole_word.isChecked(), backward=True)

            def replace_current():
                find_text = find_input.text()
                replace_text = replace_input.text()
                if find_text:
                    tab = self.get_current_tab()
                    if tab and hasattr(tab, 'replace_text'):
                        tab.replace_text(find_text, replace_text, case_sensitive.isChecked(), whole_word.isChecked())

            def replace_all():
                find_text = find_input.text()
                replace_text = replace_input.text()
                if find_text:
                    tab = self.get_current_tab()
                    if tab and hasattr(tab, 'replace_all_text'):
                        count = tab.replace_all_text(find_text, replace_text, case_sensitive.isChecked(), whole_word.isChecked())
                        logger.info(f"替换了 {count} 处文本")

            find_next_btn.clicked.connect(find_next)
            find_prev_btn.clicked.connect(find_previous)
            replace_btn.clicked.connect(replace_current)
            replace_all_btn.clicked.connect(replace_all)
            close_btn.clicked.connect(dialog.close)

            # 显示对话框
            dialog.show()
            find_input.setFocus()

            logger.info("查找对话框已显示")

        except Exception as e:
            logger.error(f"显示查找对话框失败: {e}")
    
    def insert_text(self, text: str):
        """插入文本到当前文档"""
        tab = self.get_current_tab()
        if tab:
            tab.insert_text(text)
    
    def get_selected_text(self) -> str:
        """获取当前选中的文本"""
        tab = self.get_current_tab()
        if tab:
            return tab.get_selected_text()
        return ""
    
    def replace_selected_text(self, text: str):
        """替换当前选中的文本"""
        tab = self.get_current_tab()
        if tab:
            tab.replace_selected_text(text)

    def toggle_syntax_highlighting(self):
        """切换语法高亮"""
        tab = self.get_current_tab()
        if tab:
            # 获取当前语法高亮状态
            current_enabled = tab.syntax_highlighter is not None and tab.syntax_highlighter.enabled if hasattr(tab.syntax_highlighter, 'enabled') else True
            # 切换状态
            tab.toggle_syntax_highlighting(not current_enabled)

    def get_content(self) -> str:
        """获取当前文档内容"""
        tab = self.get_current_tab()
        if tab:
            return tab.get_content()
        return ""

    def set_content(self, content: str):
        """设置当前文档内容"""
        tab = self.get_current_tab()
        if tab:
            tab.set_content(content)

    def get_cursor_position(self) -> tuple:
        """获取光标位置 (行, 列)"""
        tab = self.get_current_tab()
        if tab and hasattr(tab, 'text_edit'):
            cursor = tab.text_edit.textCursor()
            block = cursor.block()
            line = block.blockNumber() + 1
            column = cursor.positionInBlock() + 1
            return (line, column)
        return (1, 1)

    def get_word_count(self) -> int:
        """获取当前文档字数"""
        content = self.get_content()
        return len(content.split()) if content.strip() else 0

    def get_character_count(self) -> int:
        """获取当前文档字符数"""
        content = self.get_content()
        return len(content)

    def can_undo(self) -> bool:
        """是否可以撤销"""
        tab = self.get_current_tab()
        if tab and hasattr(tab, 'text_edit'):
            return tab.text_edit.document().isUndoAvailable()
        return False

    def can_redo(self) -> bool:
        """是否可以重做"""
        tab = self.get_current_tab()
        if tab and hasattr(tab, 'text_edit'):
            return tab.text_edit.document().isRedoAvailable()
        return False

    def has_selection(self) -> bool:
        """是否有选中的文本"""
        tab = self.get_current_tab()
        if tab and hasattr(tab, 'text_edit'):
            return tab.text_edit.textCursor().hasSelection()
        return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档专属AI面板

为每个文档标签页提供独立的AI助手界面
"""

import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QGroupBox, QProgressBar, QComboBox, QSplitter,
    QTabWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from src.application.services.ai_assistant_manager import DocumentAIAssistant
from src.application.services.specialized_ai_assistants import SpecializedAIManager, DocumentType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentAIPanel(QWidget):
    """文档专属AI面板 - 专注于特定文档类型的功能"""

    # 信号定义
    text_insert_requested = pyqtSignal(str)  # 请求插入文本
    text_replace_requested = pyqtSignal(str)  # 请求替换文本

    def __init__(self, document_id: str, document_type: str, ai_assistant: DocumentAIAssistant, parent=None):
        super().__init__(parent)
        self.document_id = document_id
        self.document_type = document_type
        self.ai_assistant = ai_assistant
        self._current_context = ""
        self._selected_text = ""
        self._is_busy = False

        # 初始化专属AI管理器
        self.specialized_ai_manager = SpecializedAIManager(ai_assistant.ai_service)
        self.current_streaming_assistant = None

        self._setup_ui()
        self._setup_connections()

        logger.info(f"为{document_type}文档 {document_id} 创建专属AI面板")
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # 标题 - 根据文档类型显示不同图标和名称
        type_icons = {
            'chapter': '📖',
            'character': '👤',
            'setting': '🏛️',
            'outline': '📋',
            'note': '📝'
        }
        type_names = {
            'chapter': '章节AI',
            'character': '角色AI',
            'setting': '设定AI',
            'outline': '大纲AI',
            'note': '笔记AI'
        }

        icon = type_icons.get(self.document_type.lower(), '🤖')
        name = type_names.get(self.document_type.lower(), 'AI助手')

        title_label = QLabel(f"{icon} {name}")
        title_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2196F3; padding: 4px;")
        layout.addWidget(title_label)

        # 创建滚动区域包装主要内容
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # 主要内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(3, 3, 3, 3)
        content_layout.setSpacing(8)

        # 状态指示器
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Shape.Box)
        self.status_frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; padding: 4px; }")
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(6)
        status_layout.addWidget(self.progress_bar)

        content_layout.addWidget(self.status_frame)
        
        # 快速操作按钮 - 根据文档类型显示不同功能
        quick_actions_group = QGroupBox(f"{name}专属功能")
        quick_actions_layout = QVBoxLayout(quick_actions_group)

        # 智能AI助手按钮（置顶）
        smart_layout = QHBoxLayout()

        self.smart_ai_btn = QPushButton("🧠 智能AI助手")
        self.smart_ai_btn.setToolTip("根据当前内容自动选择最合适的AI功能")
        self.smart_ai_btn.clicked.connect(self.smart_ai_assist)
        self.smart_ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        smart_layout.addWidget(self.smart_ai_btn)

        self.refresh_suggestions_btn = QPushButton("🔄")
        self.refresh_suggestions_btn.setToolTip("刷新写作建议")
        self.refresh_suggestions_btn.clicked.connect(self._refresh_suggestions)
        self.refresh_suggestions_btn.setMaximumWidth(30)
        smart_layout.addWidget(self.refresh_suggestions_btn)

        quick_actions_layout.addLayout(smart_layout)

        # 写作建议区域
        self.suggestions_label = QLabel("💡 写作建议:")
        self.suggestions_label.setFont(QFont("Microsoft YaHei UI", 8))
        quick_actions_layout.addWidget(self.suggestions_label)

        self.suggestions_text = QLabel("正在分析内容...")
        self.suggestions_text.setWordWrap(True)
        self.suggestions_text.setFont(QFont("Microsoft YaHei UI", 8))
        self.suggestions_text.setStyleSheet("""
            QLabel {
                background-color: #f0f8ff;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                margin: 2px;
            }
        """)
        self.suggestions_text.setMaximumHeight(60)
        quick_actions_layout.addWidget(self.suggestions_text)

        # 根据文档类型创建不同的按钮
        self._create_type_specific_buttons(quick_actions_layout)

        # 通用控制按钮
        control_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.setToolTip("取消当前AI请求")
        self.cancel_btn.clicked.connect(self._cancel_request)
        self.cancel_btn.setEnabled(False)
        control_layout.addWidget(self.cancel_btn)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setToolTip("停止流式响应")
        self.stop_btn.clicked.connect(self._stop_streaming)
        self.stop_btn.setVisible(False)
        control_layout.addWidget(self.stop_btn)

        quick_actions_layout.addLayout(control_layout)

        content_layout.addWidget(quick_actions_group)

        # AI响应区域
        response_group = QGroupBox("AI响应")
        response_layout = QVBoxLayout(response_group)
        
        # 响应类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("响应类型:"))
        
        self.response_type_combo = QComboBox()
        self.response_type_combo.addItems(["续写", "优化", "对话", "场景", "分析"])
        self.response_type_combo.setEnabled(False)
        type_layout.addWidget(self.response_type_combo)
        
        type_layout.addStretch()
        response_layout.addLayout(type_layout)
        
        # 响应文本
        self.response_text = QTextEdit()
        self.response_text.setPlaceholderText("AI响应将显示在这里...")
        self.response_text.setMaximumHeight(200)
        self.response_text.setFont(QFont("Microsoft YaHei UI", 9))
        response_layout.addWidget(self.response_text)
        
        # 响应操作按钮
        response_actions_layout = QHBoxLayout()
        
        self.insert_btn = QPushButton("📝 插入")
        self.insert_btn.setToolTip("将AI响应插入到文档中")
        self.insert_btn.clicked.connect(self._insert_response)
        self.insert_btn.setEnabled(False)
        response_actions_layout.addWidget(self.insert_btn)
        
        self.replace_btn = QPushButton("🔄 替换")
        self.replace_btn.setToolTip("用AI响应替换选中的文本")
        self.replace_btn.clicked.connect(self._replace_response)
        self.replace_btn.setEnabled(False)
        response_actions_layout.addWidget(self.replace_btn)
        
        self.copy_btn = QPushButton("📋 复制")
        self.copy_btn.setToolTip("复制AI响应到剪贴板")
        self.copy_btn.clicked.connect(self._copy_response)
        self.copy_btn.setEnabled(False)
        response_actions_layout.addWidget(self.copy_btn)
        
        response_layout.addLayout(response_actions_layout)

        content_layout.addWidget(response_group)

        # 添加弹性空间
        content_layout.addStretch()

        # 将内容容器设置到滚动区域
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def _create_type_specific_buttons(self, layout):
        """根据文档类型创建特定功能按钮"""
        doc_type = self.document_type.lower()

        if doc_type == 'chapter':
            self._create_chapter_buttons(layout)
        elif doc_type == 'character':
            self._create_character_buttons(layout)
        elif doc_type == 'setting':
            self._create_setting_buttons(layout)
        elif doc_type == 'outline':
            self._create_outline_buttons(layout)
        elif doc_type == 'note':
            self._create_note_buttons(layout)
        else:
            self._create_default_buttons(layout)

    def _create_chapter_buttons(self, layout):
        """创建章节专属按钮"""
        # 第一行：内容创作
        row1_layout = QHBoxLayout()

        self.continue_btn = QPushButton("✨ 智能续写")
        self.continue_btn.setToolTip("基于当前情节智能续写")
        self.continue_btn.clicked.connect(self._request_continuation)
        row1_layout.addWidget(self.continue_btn)

        self.dialogue_btn = QPushButton("💬 对话优化")
        self.dialogue_btn.setToolTip("优化对话的自然度和表现力")
        self.dialogue_btn.clicked.connect(self._improve_dialogue)
        row1_layout.addWidget(self.dialogue_btn)

        layout.addLayout(row1_layout)

        # 第二行：场景和描写
        row2_layout = QHBoxLayout()

        self.scene_btn = QPushButton("🎬 场景扩展")
        self.scene_btn.setToolTip("扩展和丰富场景描述")
        self.scene_btn.clicked.connect(self._expand_scene)
        row2_layout.addWidget(self.scene_btn)

        self.emotion_btn = QPushButton("💭 情感描写")
        self.emotion_btn.setToolTip("增强角色情感表达")
        self.emotion_btn.clicked.connect(self._enhance_emotion)
        row2_layout.addWidget(self.emotion_btn)

        layout.addLayout(row2_layout)

        # 第三行：结构和节奏
        row3_layout = QHBoxLayout()

        self.pacing_btn = QPushButton("⏱️ 节奏调整")
        self.pacing_btn.setToolTip("分析和调整章节节奏")
        self.pacing_btn.clicked.connect(self._adjust_pacing)
        row3_layout.addWidget(self.pacing_btn)

        self.transition_btn = QPushButton("🔄 过渡优化")
        self.transition_btn.setToolTip("优化段落间的过渡")
        self.transition_btn.clicked.connect(self._improve_transitions)
        row3_layout.addWidget(self.transition_btn)

        layout.addLayout(row3_layout)

    def _create_character_buttons(self, layout):
        """创建角色专属按钮"""
        # 第一行：角色塑造
        row1_layout = QHBoxLayout()

        self.personality_btn = QPushButton("🎭 性格分析")
        self.personality_btn.setToolTip("分析和完善角色性格")
        self.personality_btn.clicked.connect(self._analyze_personality)
        row1_layout.addWidget(self.personality_btn)

        self.background_btn = QPushButton("📚 背景扩展")
        self.background_btn.setToolTip("扩展角色背景故事")
        self.background_btn.clicked.connect(self._expand_background)
        row1_layout.addWidget(self.background_btn)

        layout.addLayout(row1_layout)

        # 第二行：关系和发展
        row2_layout = QHBoxLayout()

        self.relationship_btn = QPushButton("🤝 关系分析")
        self.relationship_btn.setToolTip("分析角色关系网络")
        self.relationship_btn.clicked.connect(self._analyze_relationships)
        row2_layout.addWidget(self.relationship_btn)

        self.development_btn = QPushButton("📈 成长轨迹")
        self.development_btn.setToolTip("规划角色发展轨迹")
        self.development_btn.clicked.connect(self._plan_development)
        row2_layout.addWidget(self.development_btn)

        layout.addLayout(row2_layout)

    def _create_setting_buttons(self, layout):
        """创建设定专属按钮"""
        # 第一行：世界构建
        row1_layout = QHBoxLayout()

        self.worldbuild_btn = QPushButton("🌍 世界扩展")
        self.worldbuild_btn.setToolTip("扩展世界观设定")
        self.worldbuild_btn.clicked.connect(self._expand_worldbuilding)
        row1_layout.addWidget(self.worldbuild_btn)

        self.consistency_btn = QPushButton("🔍 一致性检查")
        self.consistency_btn.setToolTip("检查设定的一致性")
        self.consistency_btn.clicked.connect(self._check_consistency)
        row1_layout.addWidget(self.consistency_btn)

        layout.addLayout(row1_layout)

        # 第二行：细节完善
        row2_layout = QHBoxLayout()

        self.detail_btn = QPushButton("🔬 细节补充")
        self.detail_btn.setToolTip("补充设定细节")
        self.detail_btn.clicked.connect(self._add_details)
        row2_layout.addWidget(self.detail_btn)

        self.logic_btn = QPushButton("⚖️ 逻辑验证")
        self.logic_btn.setToolTip("验证设定的逻辑性")
        self.logic_btn.clicked.connect(self._verify_logic)
        row2_layout.addWidget(self.logic_btn)

        layout.addLayout(row2_layout)

    def _create_outline_buttons(self, layout):
        """创建大纲专属按钮"""
        # 第一行：结构分析
        row1_layout = QHBoxLayout()

        self.structure_btn = QPushButton("🏗️ 结构分析")
        self.structure_btn.setToolTip("分析大纲结构")
        self.structure_btn.clicked.connect(self._analyze_structure)
        row1_layout.addWidget(self.structure_btn)

        self.expand_btn = QPushButton("📈 内容扩展")
        self.expand_btn.setToolTip("扩展大纲内容")
        self.expand_btn.clicked.connect(self._expand_outline)
        row1_layout.addWidget(self.expand_btn)

        layout.addLayout(row1_layout)

        # 第二行：优化建议
        row2_layout = QHBoxLayout()

        self.balance_btn = QPushButton("⚖️ 平衡调整")
        self.balance_btn.setToolTip("调整章节平衡")
        self.balance_btn.clicked.connect(self._balance_chapters)
        row2_layout.addWidget(self.balance_btn)

        self.conflict_btn = QPushButton("⚔️ 冲突设计")
        self.conflict_btn.setToolTip("设计冲突点")
        self.conflict_btn.clicked.connect(self._design_conflicts)
        row2_layout.addWidget(self.conflict_btn)

        layout.addLayout(row2_layout)

    def _create_note_buttons(self, layout):
        """创建笔记专属按钮"""
        # 第一行：内容整理
        row1_layout = QHBoxLayout()

        self.organize_btn = QPushButton("📋 内容整理")
        self.organize_btn.setToolTip("整理笔记内容")
        self.organize_btn.clicked.connect(self._organize_notes)
        row1_layout.addWidget(self.organize_btn)

        self.summarize_btn = QPushButton("📝 内容总结")
        self.summarize_btn.setToolTip("总结笔记要点")
        self.summarize_btn.clicked.connect(self._summarize_notes)
        row1_layout.addWidget(self.summarize_btn)

        layout.addLayout(row1_layout)

        # 第二行：关联分析
        row2_layout = QHBoxLayout()

        self.connect_btn = QPushButton("🔗 关联分析")
        self.connect_btn.setToolTip("分析与其他内容的关联")
        self.connect_btn.clicked.connect(self._analyze_connections)
        row2_layout.addWidget(self.connect_btn)

        self.insight_btn = QPushButton("💡 洞察提取")
        self.insight_btn.setToolTip("提取关键洞察")
        self.insight_btn.clicked.connect(self._extract_insights)
        row2_layout.addWidget(self.insight_btn)

        layout.addLayout(row2_layout)

    def _create_default_buttons(self, layout):
        """创建默认按钮"""
        # 通用功能按钮
        row1_layout = QHBoxLayout()

        self.improve_btn = QPushButton("🔧 文本优化")
        self.improve_btn.setToolTip("优化选中的文本")
        self.improve_btn.clicked.connect(self._improve_text)
        row1_layout.addWidget(self.improve_btn)

        self.analyze_btn = QPushButton("📊 内容分析")
        self.analyze_btn.setToolTip("分析文档内容")
        self.analyze_btn.clicked.connect(self._analyze_content)
        row1_layout.addWidget(self.analyze_btn)

        layout.addLayout(row1_layout)

    def _setup_connections(self):
        """设置信号连接"""
        self.ai_assistant.response_ready.connect(self._on_response_ready)
        self.ai_assistant.error_occurred.connect(self._on_error_occurred)
        self.ai_assistant.progress_updated.connect(self._on_progress_updated)

        # 初始化写作建议
        QTimer.singleShot(500, self._refresh_suggestions)  # 延迟500ms刷新建议
    
    def set_context(self, context: str, selected_text: str = ""):
        """设置上下文"""
        self._current_context = context
        self._selected_text = selected_text

        # 更新按钮状态（安全地检查按钮是否存在）
        has_selection = bool(selected_text.strip())

        # 通用按钮
        if hasattr(self, 'improve_btn'):
            self.improve_btn.setEnabled(has_selection)
        if hasattr(self, 'analyze_btn'):
            self.analyze_btn.setEnabled(has_selection)

        # 章节专属按钮
        if hasattr(self, 'dialogue_btn'):
            self.dialogue_btn.setEnabled(has_selection)
        if hasattr(self, 'scene_btn'):
            self.scene_btn.setEnabled(has_selection)
        if hasattr(self, 'emotion_btn'):
            self.emotion_btn.setEnabled(has_selection)

        # 其他类型的按钮也可以在这里添加检查
    
    def _request_continuation(self):
        """请求续写"""
        if not self._current_context.strip():
            self._show_status("请先在编辑器中输入一些内容", "error")
            return

        # 使用流式响应，提供默认字数参数
        self._start_streaming_task("continue_writing", word_count=500)
    
    def _improve_text(self):
        """改进文本"""
        if not self._selected_text.strip():
            self._show_status("请先选择要改进的文本", "error")
            return

        # 使用流式响应
        self._start_streaming_task("improve_dialogue")
    
    def _improve_dialogue(self):
        """改进对话"""
        if not self._selected_text.strip():
            self._show_status("请先选择要优化的对话", "error")
            return

        # 使用流式响应
        self._start_streaming_task("improve_dialogue")
    
    def _expand_scene(self):
        """扩展场景"""
        if not self._selected_text.strip():
            self._show_status("请先选择要扩展的场景", "error")
            return

        # 使用流式响应
        self._start_streaming_task("expand_scene")
    
    def _analyze_style(self):
        """分析风格"""
        text_to_analyze = self._selected_text if self._selected_text.strip() else self._current_context
        if not text_to_analyze.strip():
            self._show_status("请先选择要分析的文本", "error")
            return

        # 使用流式响应
        self._start_streaming_task("analyze_structure")
    
    def _cancel_request(self):
        """取消请求"""
        self.ai_assistant.cancel_current_request()
        self._end_ai_request()
        self._show_status("请求已取消", "warning")
    
    def _start_ai_request(self, request_type: str):
        """开始AI请求"""
        self.status_label.setText("处理中...")
        self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        
        # 禁用操作按钮（安全地检查按钮是否存在）
        if hasattr(self, 'continue_btn'):
            self.continue_btn.setEnabled(False)
        if hasattr(self, 'improve_btn'):
            self.improve_btn.setEnabled(False)
        if hasattr(self, 'dialogue_btn'):
            self.dialogue_btn.setEnabled(False)
        if hasattr(self, 'scene_btn'):
            self.scene_btn.setEnabled(False)
        if hasattr(self, 'analyze_btn'):
            self.analyze_btn.setEnabled(False)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setEnabled(True)
        
        # 设置响应类型
        self.response_type_combo.setCurrentText(request_type)
        self.response_type_combo.setEnabled(False)
    
    def _end_ai_request(self):
        """结束AI请求"""
        self.status_label.setText("就绪")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.progress_bar.setVisible(False)
        
        # 恢复按钮状态（安全地检查按钮是否存在）
        if hasattr(self, 'continue_btn'):
            self.continue_btn.setEnabled(True)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setEnabled(False)

        # 根据选择状态恢复其他按钮
        has_selection = bool(self._selected_text.strip())
        if hasattr(self, 'improve_btn'):
            self.improve_btn.setEnabled(has_selection)
        if hasattr(self, 'dialogue_btn'):
            self.dialogue_btn.setEnabled(has_selection)
        if hasattr(self, 'scene_btn'):
            self.scene_btn.setEnabled(has_selection)
        if hasattr(self, 'analyze_btn'):
            self.analyze_btn.setEnabled(has_selection)
    
    def _show_status(self, message: str, status_type: str = "info"):
        """显示状态消息"""
        colors = {
            "info": "#2196F3",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336"
        }
        
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {colors.get(status_type, colors['info'])}; font-weight: bold;")
        
        # 3秒后恢复默认状态
        if status_type != "info":
            QTimer.singleShot(3000, lambda: self._show_status("就绪"))
    
    def _on_response_ready(self, request_type: str, response: str):
        """AI响应就绪"""
        self._end_ai_request()
        self.response_text.setPlainText(response)
        
        # 启用响应操作按钮
        self.insert_btn.setEnabled(True)
        self.replace_btn.setEnabled(bool(self._selected_text.strip()))
        self.copy_btn.setEnabled(True)
        
        self._show_status(f"{request_type}完成", "success")
    
    def _on_error_occurred(self, request_type: str, error: str):
        """AI请求出错"""
        self._end_ai_request()
        self.response_text.setPlainText(f"错误: {error}")
        self._show_status(f"{request_type}失败", "error")
    
    def _on_progress_updated(self, request_type: str, progress: int):
        """进度更新"""
        if progress > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)
    
    def _insert_response(self):
        """插入响应"""
        response = self.response_text.toPlainText()
        if response.strip():
            self.text_insert_requested.emit(response)
    
    def _replace_response(self):
        """替换响应"""
        response = self.response_text.toPlainText()
        if response.strip():
            self.text_replace_requested.emit(response)
    
    def _copy_response(self):
        """复制响应"""
        response = self.response_text.toPlainText()
        if response.strip():
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(response)
            self._show_status("已复制到剪贴板", "success")

    # ========== 流式AI处理方法 ==========

    def _start_streaming_task(self, task_name: str, content: str = None, **kwargs):
        """开始流式AI任务"""
        try:
            # 获取专属AI助手
            assistant = self.specialized_ai_manager.get_assistant(self.document_type)
            if not assistant:
                self._show_status(f"不支持的文档类型: {self.document_type}", "error")
                return

            # 准备内容
            if content is None:
                content = self._selected_text if self._selected_text.strip() else self._current_context

            if not content.strip():
                self._show_status("请先选择文本或确保文档有内容", "error")
                return

            # 停止当前任务
            if self.current_streaming_assistant:
                self.current_streaming_assistant.stop_streaming()

            # 设置UI状态
            self._set_streaming_ui_state(True)
            self.response_text.clear()

            # 连接信号
            assistant.chunk_received.connect(self._on_chunk_received)
            assistant.response_completed.connect(self._on_response_completed)
            assistant.error_occurred.connect(self._on_error_occurred)
            assistant.progress_updated.connect(self._on_progress_updated)
            assistant.status_updated.connect(self._on_status_updated)

            # 开始流式任务
            assistant.start_streaming_task(task_name, content, self._current_context, **kwargs)
            self.current_streaming_assistant = assistant

            logger.info(f"开始流式AI任务: {task_name}")

        except Exception as e:
            logger.error(f"启动流式AI任务失败: {e}")
            self._show_status(f"启动任务失败: {str(e)}", "error")

    def _stop_streaming(self):
        """停止流式响应"""
        if self.current_streaming_assistant:
            self.current_streaming_assistant.stop_streaming()
            self._set_streaming_ui_state(False)
            self._show_status("任务已停止", "warning")

    def _set_streaming_ui_state(self, is_streaming: bool):
        """设置流式响应UI状态"""
        self.progress_bar.setVisible(is_streaming)
        self.stop_btn.setVisible(is_streaming)
        self.cancel_btn.setEnabled(is_streaming)

        # 禁用/启用功能按钮
        for button in self.findChildren(QPushButton):
            if button not in [self.stop_btn, self.cancel_btn, self.insert_btn, self.replace_btn, self.copy_btn]:
                button.setEnabled(not is_streaming)

    def _on_chunk_received(self, chunk: str):
        """处理接收到的文本块"""
        cursor = self.response_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.response_text.setTextCursor(cursor)

        # 自动滚动到底部
        scrollbar = self.response_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_response_completed(self, response: str):
        """处理响应完成"""
        self._set_streaming_ui_state(False)
        self._show_status("任务完成", "success")

        # 启用响应操作按钮
        self.insert_btn.setEnabled(True)
        self.replace_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)

        # 断开信号连接
        if self.current_streaming_assistant:
            self.current_streaming_assistant.chunk_received.disconnect()
            self.current_streaming_assistant.response_completed.disconnect()
            self.current_streaming_assistant.error_occurred.disconnect()
            self.current_streaming_assistant.progress_updated.disconnect()
            self.current_streaming_assistant.status_updated.disconnect()
            self.current_streaming_assistant = None

    def _on_error_occurred(self, error: str):
        """处理错误"""
        self._set_streaming_ui_state(False)
        self._show_status(f"任务失败: {error}", "error")

        # 断开信号连接
        if self.current_streaming_assistant:
            self.current_streaming_assistant.chunk_received.disconnect()
            self.current_streaming_assistant.response_completed.disconnect()
            self.current_streaming_assistant.error_occurred.disconnect()
            self.current_streaming_assistant.progress_updated.disconnect()
            self.current_streaming_assistant.status_updated.disconnect()
            self.current_streaming_assistant = None

    def _on_progress_updated(self, progress: int):
        """处理进度更新"""
        self.progress_bar.setValue(progress)

    def _on_status_updated(self, status: str):
        """处理状态更新"""
        self.status_label.setText(status)

    # ========== 章节专属功能方法 ==========

    def _enhance_emotion(self):
        """增强情感描写"""
        self._start_streaming_task("enhance_emotion")

    def _adjust_pacing(self):
        """调整节奏"""
        self._start_streaming_task("adjust_pacing", pacing_target="平衡")

    def _improve_transitions(self):
        """改进过渡"""
        self._start_streaming_task("improve_transitions")

    # ========== 角色专属功能方法 ==========

    def _analyze_personality(self):
        """分析性格"""
        self._start_streaming_task("analyze_personality")

    def _expand_background(self):
        """扩展背景"""
        self._start_streaming_task("expand_background")

    def _analyze_relationships(self):
        """分析关系"""
        self._start_streaming_task("analyze_relationships")

    def _plan_development(self):
        """规划发展"""
        self._start_streaming_task("plan_development")

    # ========== 设定专属功能方法 ==========

    def _expand_worldbuilding(self):
        """扩展世界观"""
        self._start_streaming_task("expand_worldbuilding")

    def _check_consistency(self):
        """检查一致性"""
        self._start_streaming_task("check_consistency")

    def _add_details(self):
        """添加细节"""
        self._start_streaming_task("add_details")

    def _verify_logic(self):
        """验证逻辑"""
        self._start_streaming_task("verify_logic")

    # ========== 大纲专属功能方法 ==========

    def _analyze_structure(self):
        """分析结构"""
        self._start_streaming_task("analyze_structure")

    def _expand_outline(self):
        """扩展大纲"""
        self._start_streaming_task("expand_outline")

    def _balance_chapters(self):
        """平衡章节"""
        self._start_streaming_task("balance_chapters")

    def _design_conflicts(self):
        """设计冲突"""
        self._start_streaming_task("design_conflicts")

    # ========== 笔记专属功能方法 ==========

    def _organize_notes(self):
        """整理笔记"""
        self._start_streaming_task("organize_notes")

    def _summarize_notes(self):
        """总结笔记"""
        self._start_streaming_task("summarize_notes")

    def _analyze_connections(self):
        """分析关联"""
        self._start_streaming_task("analyze_connections")

    def _extract_insights(self):
        """提取洞察"""
        self._start_streaming_task("extract_insights")

    # ========== 通用功能方法 ==========

    def _improve_text(self):
        """改进文本"""
        # 通用文本改进，使用章节AI的improve_dialogue作为示例
        self._start_streaming_task("improve_dialogue")

    def _analyze_content(self):
        """分析内容"""
        # 通用内容分析，使用章节AI的analyze_structure作为示例
        self._start_streaming_task("analyze_structure")

    # ========== 上下文管理和智能功能 ==========

    def update_context(self, content: str):
        """
        更新文档上下文

        当文档内容发生变化时，更新AI助手的上下文信息。
        这样AI可以基于最新的文档内容提供更准确的建议。

        Args:
            content: 当前文档的完整内容
        """
        self._current_context = content
        logger.debug(f"文档 {self.document_id} 上下文已更新，长度: {len(content)}")

        # 如果内容较长，只保留最近的部分作为上下文
        max_context_length = 5000  # 最大上下文长度
        if len(content) > max_context_length:
            # 保留最后的内容，因为通常用户在文档末尾工作
            self._current_context = "..." + content[-max_context_length:]
            logger.debug(f"上下文已截断到 {max_context_length} 字符")

    def set_selected_text(self, selected_text: str):
        """
        设置当前选中的文本

        当用户在编辑器中选中文本时，更新AI助手的选中文本信息。
        这样AI可以针对选中的文本进行特定的处理。

        Args:
            selected_text: 用户选中的文本内容
        """
        self._selected_text = selected_text
        logger.debug(f"文档 {self.document_id} 选中文本已更新，长度: {len(selected_text)}")

        # 更新替换按钮的状态
        if hasattr(self, 'replace_btn'):
            self.replace_btn.setEnabled(bool(selected_text.strip()) and hasattr(self, 'response_text') and bool(self.response_text.toPlainText().strip()))

    def set_context(self, content: str, selected_text: str = ""):
        """
        设置AI面板的上下文（兼容编辑器调用）

        这是编辑器调用的接口，用于同时更新文档内容和选中文本。

        Args:
            content: 文档的完整内容
            selected_text: 当前选中的文本
        """
        self.update_context(content)
        self.set_selected_text(selected_text)

        # 如果内容发生了显著变化，刷新建议
        if hasattr(self, '_last_content_length'):
            content_change = abs(len(content) - self._last_content_length)
            if content_change > 50:  # 内容变化超过50字符时刷新建议
                self._refresh_suggestions()

        self._last_content_length = len(content)

    def get_context_for_ai(self) -> str:
        """
        获取用于AI请求的上下文信息

        构建包含文档类型、当前内容和选中文本的完整上下文。

        Returns:
            str: 格式化的上下文字符串
        """
        context_parts = []

        # 添加文档类型信息
        context_parts.append(f"文档类型: {self.document_type}")

        # 添加当前文档内容
        if self._current_context:
            context_parts.append(f"当前文档内容:\n{self._current_context}")

        # 添加选中文本（如果有）
        if self._selected_text:
            context_parts.append(f"选中文本:\n{self._selected_text}")

        return "\n\n".join(context_parts)

    def get_smart_prompt(self, task_type: str) -> str:
        """
        根据任务类型和上下文生成智能提示词

        Args:
            task_type: 任务类型（如 'continue_writing', 'improve_dialogue' 等）

        Returns:
            str: 智能生成的提示词
        """
        base_context = self.get_context_for_ai()

        # 根据任务类型生成特定的提示词
        task_prompts = {
            'continue_writing': f"请基于以下内容进行自然流畅的续写:\n\n{base_context}\n\n续写内容:",
            'improve_dialogue': f"请优化以下对话，使其更加自然生动:\n\n{base_context}\n\n优化后的对话:",
            'expand_scene': f"请扩展以下场景描述，增加细节和氛围:\n\n{base_context}\n\n扩展后的场景:",
            'enhance_emotion': f"请增强以下内容的情感表达:\n\n{base_context}\n\n增强后的内容:",
            'analyze_character': f"请分析以下角色的特征和发展:\n\n{base_context}\n\n角色分析:",
            'check_consistency': f"请检查以下设定的一致性:\n\n{base_context}\n\n一致性分析:",
            'organize_content': f"请整理以下内容的结构:\n\n{base_context}\n\n整理后的内容:",
        }

        return task_prompts.get(task_type, f"请处理以下内容:\n\n{base_context}\n\n处理结果:")

    def auto_detect_task_type(self) -> str:
        """
        根据选中文本和文档类型自动检测最适合的任务类型

        Returns:
            str: 推荐的任务类型
        """
        if not self._selected_text:
            # 没有选中文本，根据文档类型推荐默认任务
            default_tasks = {
                'chapter': 'continue_writing',
                'character': 'analyze_character',
                'setting': 'check_consistency',
                'outline': 'organize_content',
                'note': 'organize_content'
            }
            return default_tasks.get(self.document_type, 'continue_writing')

        # 有选中文本，根据内容特征推荐任务
        selected_lower = self._selected_text.lower()

        # 检测对话内容
        if '"' in self._selected_text or '"' in self._selected_text or '：' in self._selected_text:
            return 'improve_dialogue'

        # 检测场景描述
        if any(word in selected_lower for word in ['房间', '街道', '森林', '山', '海', '天空', '阳光', '月亮']):
            return 'expand_scene'

        # 检测情感内容
        if any(word in selected_lower for word in ['感到', '心情', '情绪', '高兴', '悲伤', '愤怒', '恐惧']):
            return 'enhance_emotion'

        # 默认返回续写
        return 'continue_writing'

    def smart_ai_assist(self):
        """
        智能AI辅助功能

        根据当前上下文和选中文本，自动选择最合适的AI功能。
        """
        if self._is_busy:
            self._show_status("AI正在处理中，请稍候", "warning")
            return

        # 自动检测任务类型
        task_type = self.auto_detect_task_type()

        # 显示检测到的任务类型
        task_names = {
            'continue_writing': '智能续写',
            'improve_dialogue': '对话优化',
            'expand_scene': '场景扩展',
            'enhance_emotion': '情感增强',
            'analyze_character': '角色分析',
            'check_consistency': '一致性检查',
            'organize_content': '内容整理'
        }

        task_name = task_names.get(task_type, '智能处理')
        self._show_status(f"检测到: {task_name}", "info")

        # 执行对应的任务
        if hasattr(self, f'_{task_type}'):
            getattr(self, f'_{task_type}')()
        else:
            # 使用通用的流式任务处理
            self._start_streaming_task(task_type)

    def get_writing_suggestions(self) -> list:
        """
        根据当前内容获取写作建议

        Returns:
            list: 写作建议列表
        """
        suggestions = []

        if not self._current_context:
            suggestions.append("💡 开始写作，AI将根据内容提供智能建议")
            return suggestions

        content_length = len(self._current_context)

        # 根据内容长度提供建议
        if content_length < 100:
            suggestions.append("📝 内容较短，可以尝试扩展场景描述")
        elif content_length > 2000:
            suggestions.append("📊 内容较长，可以考虑分段或总结要点")

        # 根据文档类型提供建议
        if self.document_type == 'chapter':
            if '对话' in self._current_context or '"' in self._current_context:
                suggestions.append("💬 检测到对话内容，可以优化对话的自然度")
            if '场景' in self._current_context or '环境' in self._current_context:
                suggestions.append("🎬 检测到场景描述，可以扩展场景细节")

        elif self.document_type == 'character':
            if '性格' not in self._current_context:
                suggestions.append("👤 建议添加角色性格描述")
            if '背景' not in self._current_context:
                suggestions.append("📚 建议添加角色背景信息")

        elif self.document_type == 'setting':
            if '世界观' in self._current_context:
                suggestions.append("🌍 可以检查世界观设定的一致性")

        if not suggestions:
            suggestions.append("✨ 内容看起来不错，可以尝试智能续写")

        return suggestions

    def _refresh_suggestions(self):
        """刷新写作建议"""
        try:
            suggestions = self.get_writing_suggestions()

            if suggestions:
                # 只显示前2个建议，避免界面过于拥挤
                display_suggestions = suggestions[:2]
                suggestion_text = " | ".join(display_suggestions)
                self.suggestions_text.setText(suggestion_text)
            else:
                self.suggestions_text.setText("💡 暂无建议")

        except Exception as e:
            logger.error(f"刷新写作建议失败: {e}")
            self.suggestions_text.setText("💡 建议加载失败")

    def get_ai_status_info(self) -> dict:
        """
        获取AI助手状态信息

        Returns:
            dict: 包含AI助手状态的字典
        """
        return {
            'document_id': self.document_id,
            'document_type': self.document_type,
            'is_busy': self._is_busy,
            'context_length': len(self._current_context),
            'selected_length': len(self._selected_text),
            'has_response': bool(hasattr(self, 'response_text') and self.response_text.toPlainText().strip())
        }

    def export_ai_session(self) -> dict:
        """
        导出AI会话信息

        Returns:
            dict: AI会话的完整信息
        """
        return {
            'document_info': {
                'id': self.document_id,
                'type': self.document_type
            },
            'context': self._current_context,
            'selected_text': self._selected_text,
            'last_response': self.response_text.toPlainText() if hasattr(self, 'response_text') else "",
            'suggestions': self.get_writing_suggestions(),
            'timestamp': QTimer().remainingTime()  # 简单的时间戳
        }

    def import_ai_session(self, session_data: dict):
        """
        导入AI会话信息

        Args:
            session_data: 之前导出的会话数据
        """
        try:
            if 'context' in session_data:
                self.update_context(session_data['context'])

            if 'selected_text' in session_data:
                self.set_selected_text(session_data['selected_text'])

            if 'last_response' in session_data and hasattr(self, 'response_text'):
                self.response_text.setPlainText(session_data['last_response'])

            # 刷新建议
            self._refresh_suggestions()

            logger.info(f"AI会话导入成功: {self.document_id}")

        except Exception as e:
            logger.error(f"AI会话导入失败: {e}")

    def cleanup(self):
        """
        清理资源

        在文档关闭或AI面板销毁时调用，确保资源正确释放。
        """
        try:
            # 取消当前请求
            if self._is_busy:
                self._cancel_request()

            # 停止流式响应
            if self.current_streaming_assistant:
                self.current_streaming_assistant.stop_task()
                self.current_streaming_assistant = None

            # 清理AI助手
            if self.ai_assistant:
                self.ai_assistant.cancel_current_request()

            logger.info(f"文档AI面板清理完成: {self.document_id}")

        except Exception as e:
            logger.error(f"文档AI面板清理失败: {e}")

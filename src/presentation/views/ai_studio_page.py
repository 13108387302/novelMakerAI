#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Studio 页面

以“页面”为中心的全新 AI 交互：左侧导航，右侧功能页面 + 统一输出区与工具条。
- 每个功能拥有独立页面（续写/对话/场景/润色/大纲/角色等）
- 复用 ModernAIWidget 的上下文、写回、流式与渲染能力
- 统一样式与快捷操作，保持项目整洁、低耦合
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt

from src.presentation.widgets.ai.refactored.components.modern_ai_widget import ModernAIWidget


class AIStudioPage(ModernAIWidget):
    """AI Studio 主页面：左侧导航 + 右侧分页面 + 统一输出"""

    def __init__(self, parent=None, settings_service=None):
        super().__init__(parent, settings_service)
        self._setup_studio_ui()

    # ---- 公共上下文接口（供主窗调用） ----
    def set_document_context(self, text: str):
        self.document_context = text or ""

    def set_selected_text(self, text: str):
        self.selected_text = text or ""

    # ModernAIWidget 已有 update_cursor_position

    # ---- UI ----
    def _setup_studio_ui(self):
        # 清空滚动内容，改为页面布局：导航 + 页面 + 输出
        container = QFrame()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 左侧导航
        self.nav = QListWidget()
        self.nav.setFixedWidth(140)
        for name in ["写作助手", "对话", "场景", "文本优化", "大纲", "角色", "世界观", "命名"]:
            QListWidgetItem(name, self.nav)
        self.nav.setCurrentRow(0)

        # 右侧堆叠页面
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_writing_page())
        self.pages.addWidget(self._build_dialogue_page())
        self.pages.addWidget(self._build_scene_page())
        self.pages.addWidget(self._build_optimization_page())
        self.pages.addWidget(self._build_outline_page())
        self.pages.addWidget(self._build_character_page())
        self.pages.addWidget(self._build_world_page())
        self.pages.addWidget(self._build_naming_page())

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        container_layout.addWidget(self.nav)
        container_layout.addWidget(self.pages, 1)

        # 页面顶部：上下文来源徽章
        header = QHBoxLayout()
        header.setContentsMargins(16, 8, 16, 8)
        header.addWidget(self.create_context_source_badge())
        header.addStretch()

        # 结果工具条 + 输出区（复用基类）
        output_box = QVBoxLayout()
        output_box.setContentsMargins(16, 0, 16, 16)
        output_box.setSpacing(8)
        output_box.addLayout(self.create_output_toolbar())
        self.output_area = self.create_output_area("AI输出将在这里显示…")
        output_box.addWidget(self.output_area)

        # 用滚动布局容器替换为页面布局
        # 清空原有滚动布局内容
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.scroll_layout.addLayout(header)
        self.scroll_layout.addWidget(container)
        self.scroll_layout.addLayout(output_box)
        self.add_stretch()

    def _add_feature_buttons(self, titles_and_handlers):
        row = QHBoxLayout()
        row.setSpacing(10)
        for title, handler in titles_and_handlers:
            btn = self.create_modern_button(title, "", "writing", title, handler)
            btn.setMinimumHeight(36)
            row.addWidget(btn)
        row.addStretch()
        return row

    # ---- 各功能页面 ----
    def _build_writing_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("写作助手：针对当前上下文进行智能创作"))
        v.addLayout(self._add_feature_buttons([
            ("智能续写", lambda: self.execute_ai_request("smart_continue", "智能续写", {"type": "continue"})),
            ("内容扩展", lambda: self.execute_ai_request("content_expand", "扩展选中内容", {"type": "expand"})),
        ]))
        v.addLayout(self._add_feature_buttons([
            ("情节建议", lambda: self.execute_ai_request("plot_suggestion", "情节建议", {"type": "plot"})),
            ("剧情转折", lambda: self.execute_ai_request("plot_twist", "剧情转折", {"type": "twist"})),
        ]))
        return w

    def _build_dialogue_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("对话生成：为角色生成符合性格的对话"))
        v.addLayout(self._add_feature_buttons([
            ("对话生成", lambda: self.execute_ai_request("dialogue_generation", "生成角色对话", {"type": "dialogue"})),
            ("争吵场景", lambda: self.execute_ai_request("argue_dialogue", "激烈对话", {"type": "dialogue"})),
        ]))
        return w

    def _build_scene_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("场景描写：营造氛围与细节"))
        v.addLayout(self._add_feature_buttons([
            ("场景描写", lambda: self.execute_ai_request("scene_description", "生成场景描写", {"type": "scene"})),
            ("氛围强化", lambda: self.execute_ai_request("mood_enhance", "强化氛围", {"type": "scene"})),
        ]))
        return w

    def _build_optimization_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("文本优化：润色、风格与结构"))
        v.addLayout(self._add_feature_buttons([
            ("语言润色", lambda: self.execute_ai_request("language_polish", "润色文字表达", {"type": "polish"})),
            ("风格调整", lambda: self.execute_ai_request("style_adjustment", "调整文本风格", {"type": "style"})),
        ]))
        v.addLayout(self._add_feature_buttons([
            ("结构优化", lambda: self.execute_ai_request("structure_optimization", "优化段落结构", {"type": "structure"})),
            ("逻辑检查", lambda: self.execute_ai_request("logic_check", "检查情节逻辑", {"type": "logic"})),
        ]))
        return w

    def _build_outline_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("大纲与结构"))
        v.addLayout(self._add_feature_buttons([
            ("大纲生成", lambda: self.execute_ai_request("outline_generation", "生成章节大纲", {"type": "outline"})),
        ]))
        return w

    def _build_character_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("人物设定"))
        v.addLayout(self._add_feature_buttons([
            ("人物设定", lambda: self.execute_ai_request("character_creation", "创建人物设定", {"type": "character"})),
        ]))
        return w

    def _build_world_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("世界观构建"))
        v.addLayout(self._add_feature_buttons([
            ("世界观", lambda: self.execute_ai_request("worldbuilding", "构建世界观", {"type": "world"})),
        ]))
        return w

    def _build_naming_page(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)
        v.addWidget(QLabel("智能命名"))
        v.addLayout(self._add_feature_buttons([
            ("智能命名", lambda: self.execute_ai_request("smart_naming", "为变量/人名/地名命名", {"type": "naming"})),
        ]))
        return w


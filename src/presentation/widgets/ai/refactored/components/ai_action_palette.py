#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 动作面板（基础版）

- Alt+Enter 呼出，列出与上下文匹配的常用动作
- 先支持文档 AI 高频动作；后续可扩展全局 AI 动作
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt


class AIAction:
    def __init__(self, id: str, title: str, handler: Callable[[], None], require_selection: bool = False):
        self.id = id
        self.title = title
        self.handler = handler
        self.require_selection = require_selection


class AIActionPalette(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 动作")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setModal(True)
        self.setFixedWidth(420)
        self._actions: List[AIAction] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索动作…")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)
        self.list = QListWidget()
        layout.addWidget(self.list)
        self.list.itemActivated.connect(self._on_activated)

    def set_actions(self, actions: List[AIAction]):
        self._actions = actions
        self._render(actions)

    def _render(self, actions: List[AIAction]):
        self.list.clear()
        for a in actions:
            item = QListWidgetItem(a.title)
            item.setData(Qt.ItemDataRole.UserRole, a)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _filter(self, text: str):
        t = (text or "").strip().lower()
        if not t:
            self._render(self._actions)
            return
        filt = [a for a in self._actions if t in a.title.lower()]
        self._render(filt)

    def _on_activated(self, item: QListWidgetItem):
        a: AIAction = item.data(Qt.ItemDataRole.UserRole)
        if a and callable(a.handler):
            self.accept()
            a.handler()

    # 便捷构造：从文档 AI 面板生成动作
    @staticmethod
    def from_document_ai_panel(panel, selected_text: str) -> 'AIActionPalette':
        dlg = AIActionPalette(panel)
        actions: List[AIAction] = []
        # 将常用动作映射到面板的槽函数，如果不存在则跳过
        mapping = [
            ("智能续写", getattr(panel, "_on_smart_continue", None), False),
            ("内容扩展", getattr(panel, "_on_content_expand", None), True),
            ("对话生成", getattr(panel, "_on_dialogue_generation", None), False),
            ("场景描写", getattr(panel, "_on_scene_description", None), False),
            ("语言润色", getattr(panel, "_on_language_polish", None), True),
            ("风格调整", getattr(panel, "_on_style_adjustment", None), True),
            ("结构优化", getattr(panel, "_on_structure_optimization", None), False),
            ("逻辑检查", getattr(panel, "_on_logic_check", None), False),
        ]
        for title, handler, need_sel in mapping:
            if handler is None:
                continue
            # 若需要选区且当前无选区，则禁用（但仍展示给予提示）
            if need_sel and not selected_text:
                def disabled_handler():
                    # 利用面板的状态提示
                    if hasattr(panel, 'show_status'):
                        panel.show_status("请先选择文本", "warning")
                actions.append(AIAction(id=title, title=f"{title}（需选区）", handler=disabled_handler, require_selection=True))
            else:
                actions.append(AIAction(id=title, title=title, handler=handler, require_selection=need_sel))
        dlg.set_actions(actions)
        return dlg


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
                    if hasattr(panel, 'show_status'):
                        panel.show_status("请先选择文本", "warning")
                actions.append(AIAction(id=title, title=f"{title}（需选区）", handler=disabled_handler, require_selection=True))
            else:
                actions.append(AIAction(id=title, title=title, handler=handler, require_selection=need_sel))

        # 智能排序（可配置）：有选区优先“润色/扩写/改写”；无选区且光标在行尾优先“续写/对话”
        try:
            use_smart = True
            try:
                from src.presentation.widgets.ai.refactored import get_ai_widget_factory
                factory = get_ai_widget_factory()
                if factory and getattr(factory, 'settings_service', None):
                    use_smart = bool(factory.settings_service.get('ai.smart_action_sorting', True))
            except Exception:
                pass

            if use_smart:
                is_selection = bool(selected_text and selected_text.strip())
                # 尝试从 panel 获取是否在行尾（可选能力）
                at_line_end = False
                if hasattr(panel, 'document_context') and hasattr(panel, '_cursor_position') and isinstance(panel._cursor_position, int):
                    ctx = panel.document_context or ""
                    pos = panel._cursor_position if 0 <= panel._cursor_position <= len(ctx) else len(ctx)
                    # 行尾：后续到换行/结尾无字符
                    at_line_end = pos >= len(ctx) or ctx[pos:pos+1] in ('\n', '\r')

                priority = []
                if is_selection:
                    priority = ["语言润色", "内容扩展", "风格调整", "结构优化"]
                elif at_line_end:
                    priority = ["智能续写", "对话生成", "场景描写"]

                if priority:
                    order = {name: i for i, name in enumerate(priority)}
                    def key(a: AIAction):
                        # 去掉“（需选区）”后比较
                        name = a.title.split('（')[0]
                        return order.get(name, 999), a.title
                    actions.sort(key=key)
        except Exception:
            pass

        dlg.set_actions(actions)
        return dlg

    # 便捷构造：从通用 AI 组件生成动作（AI Studio/ModernAIWidget）
    @staticmethod
    def from_ai_widget(ai_widget, selected_text: str) -> 'AIActionPalette':
        dlg = AIActionPalette(ai_widget)
        actions: List[AIAction] = []

        def make(fn_id: str, title: str, type_: str, need_sel: bool = False):
            def handler():
                ai_widget.execute_ai_request(fn_id, title, {"type": type_})
            return AIAction(id=fn_id, title=title, handler=handler, require_selection=need_sel)

        actions.extend([
            make("smart_continue", "智能续写", "continue", False),
            make("content_expand", "内容扩展", "expand", True),
            make("dialogue_generation", "对话生成", "dialogue", False),
            make("scene_description", "场景描写", "scene", False),
            make("language_polish", "语言润色", "polish", True),
            make("style_adjustment", "风格调整", "style", True),
            make("structure_optimization", "结构优化", "structure", False),
            make("logic_check", "逻辑检查", "logic", False),
        ])

        # 根据是否有选区/行尾进行智能排序（沿用现有逻辑）
        try:
            use_smart = True
            try:
                from src.presentation.widgets.ai.refactored import get_ai_widget_factory
                factory = get_ai_widget_factory()
                if factory and getattr(factory, 'settings_service', None):
                    use_smart = bool(factory.settings_service.get('ai.smart_action_sorting', True))
            except Exception:
                pass

            if use_smart:
                is_selection = bool(selected_text and selected_text.strip())
                at_line_end = False
                if hasattr(ai_widget, 'document_context') and hasattr(ai_widget, '_cursor_position') and isinstance(ai_widget._cursor_position, int):
                    ctx = ai_widget.document_context or ""
                    pos = ai_widget._cursor_position if 0 <= ai_widget._cursor_position <= len(ctx) else len(ctx)
                    at_line_end = pos >= len(ctx) or ctx[pos:pos+1] in ('\n', '\r')
                priority = []
                if is_selection:
                    priority = ["语言润色", "内容扩展", "风格调整", "结构优化"]
                elif at_line_end:
                    priority = ["智能续写", "对话生成", "场景描写"]
                if priority:
                    order = {name: i for i, name in enumerate(priority)}
                    def key(a: AIAction):
                        name = a.title.split('（')[0]
                        return order.get(name, 999), a.title
                    actions.sort(key=key)
        except Exception:
            pass

        # 需要选区但没有选区的，附带禁用提示
        final_actions: List[AIAction] = []
        for a in actions:
            if a.require_selection and not selected_text:
                def disabled_handler():
                    if hasattr(ai_widget, 'show_status'):
                        ai_widget.show_status("请先选择文本", "warning")
                final_actions.append(AIAction(id=a.id, title=f"{a.title}（需选区）", handler=disabled_handler, require_selection=True))
            else:
                final_actions.append(a)

        dlg.set_actions(final_actions)
        return dlg


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EditorService

向插件暴露统一的编辑器API，避免插件直接依赖具体的 EditorWidget。
优先通过 EditorBridge 访问，退化到 MainWindow.editor_widget。
"""
from typing import Callable, Optional, Any

class EditorService:
    def __init__(self, editor_bridge_getter: Callable[[], Any], main_window_getter: Callable[[], Any]):
        self._get_bridge = editor_bridge_getter
        self._get_main_window = main_window_getter

    # 基础获取
    def _bridge(self):
        try:
            return self._get_bridge() if self._get_bridge else None
        except Exception:
            return None

    def _editor(self):
        try:
            mw = self._get_main_window() if self._get_main_window else None
            return getattr(mw, 'editor_widget', None) if mw else None
        except Exception:
            return None

    # API
    def get_current_document(self):
        b = self._bridge()
        if b and hasattr(b, 'get_current_document'):
            return b.get_current_document()
        ed = self._editor()
        return ed.get_current_document() if ed and hasattr(ed, 'get_current_document') else None

    def get_content(self) -> str:
        b = self._bridge()
        if b and hasattr(b, 'get_content'):
            return b.get_content()
        ed = self._editor()
        return ed.get_content() if ed and hasattr(ed, 'get_content') else ""

    def set_content(self, text: str) -> None:
        ed = self._editor()
        if ed and hasattr(ed, 'set_content'):
            ed.set_content(text)

    def get_selected_text(self) -> str:
        b = self._bridge()
        if b and hasattr(b, 'get_selected_text'):
            return b.get_selected_text()
        ed = self._editor()
        return ed.get_selected_text() if ed and hasattr(ed, 'get_selected_text') else ""

    def insert_text(self, text: str) -> None:
        ed = self._editor()
        if ed and hasattr(ed, 'insert_text'):
            ed.insert_text(text)

    def replace_selected_text(self, text: str) -> None:
        ed = self._editor()
        # 优先使用 Editor 的 replace_selected_text
        if ed and hasattr(ed, 'replace_selected_text'):
            ed.replace_selected_text(text)
        else:
            # 退化：直接插入（可能丢失选区替换语义）
            if ed and hasattr(ed, 'insert_text'):
                ed.insert_text(text)


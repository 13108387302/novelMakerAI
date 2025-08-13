#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Expanded EditorBridge

逐步收纳 MainController 对 editor_widget 的常见交互点，降低耦合。
先覆盖读取当前文档/内容、当前标签与选区等接口。
"""
from typing import Optional, Any

class EditorBridge:
    def __init__(self, main_window_getter):
        self._get_main_window = main_window_getter

    # -------- 基础获取 --------
    def get_editor(self):
        mw = self._get_main_window()
        return getattr(mw, 'editor_widget', None) if mw else None

    def get_current_document(self):
        ed = self.get_editor()
        return ed.get_current_document() if ed and hasattr(ed, 'get_current_document') else None

    def get_content(self) -> str:
        ed = self.get_editor()
        return ed.get_content() if ed and hasattr(ed, 'get_content') else ""

    def get_current_tab(self):
        ed = self.get_editor()
        return ed.get_current_tab() if ed and hasattr(ed, 'get_current_tab') else None

    def get_selected_text(self) -> str:
        ed = self.get_editor()
        if not ed:
            return ""
        if hasattr(ed, 'get_selected_text'):
            return ed.get_selected_text()
        tab = self.get_current_tab()
        if tab and hasattr(tab, 'get_selected_text'):
            return tab.get_selected_text()
        return ""

    # -------- 编辑行为 --------
    def rename_document_tab(self, document_id: str, new_title: str) -> None:
        ed = self.get_editor()
        if ed and hasattr(ed, 'rename_document_tab'):
            ed.rename_document_tab(document_id, new_title)

    def load_document(self, doc) -> None:
        ed = self.get_editor()
        if ed and hasattr(ed, 'load_document'):
            ed.load_document(doc)

    def toggle_syntax_highlighting(self) -> None:
        ed = self.get_editor()
        if ed and hasattr(ed, 'toggle_syntax_highlighting'):
            ed.toggle_syntax_highlighting()

    # 文本查找替换相关：返回 current_tab 给调用者使用，避免复制具体操作细节
    def find_current_tab(self):
        return self.get_current_tab()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EditorBridge

将与 MainWindow.editor_widget 的交互集中封装，降低 MainController 的 UI 耦合。
目前仅包含重命名标签的封装，后续可逐步迁移更多编辑器相关交互。
"""
from typing import Optional

class EditorBridge:
    def __init__(self, main_window_getter):
        """main_window_getter: 一个返回 MainWindow 的可调用，避免硬绑定引用。"""
        self._get_main_window = main_window_getter

    def rename_document_tab(self, document_id: str, new_title: str) -> None:
        mw = self._get_main_window()
        if not mw:
            return
        editor = getattr(mw, 'editor_widget', None)
        if editor and hasattr(editor, 'rename_document_tab'):
            editor.rename_document_tab(document_id, new_title)


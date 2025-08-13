#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DialogsFacade

将 MainController 中的对话框/消息框相关逻辑逐步迁移，
降低主控制器体量与 UI 耦合度。
当前提供最常用的几个对话框入口：
- show_warning / show_info / show_error
- 查找替换入口的选区传递和对话框打开
可根据需要扩展更多专用对话框（设置、模板、插件、角色管理、备份等）。
"""
from typing import Optional, Callable

from PyQt6.QtWidgets import QMessageBox
from src.shared.utils.thread_safety import is_main_thread

class DialogsFacade:
    def __init__(self, main_window_getter: Callable[[], object], async_manager_getter: Callable[[], object]):
        self._get_main_window = main_window_getter
        self._get_async_manager = async_manager_getter

    # 统一的线程安全弹窗
    def show_warning(self, title: str, message: str) -> None:
        if not is_main_thread():
            am = self._get_async_manager()
            am.execute_delayed(self.show_warning, 0, title, message)
            return
        mw = self._get_main_window()
        if mw:
            QMessageBox.warning(mw, title, message)

    def show_info(self, title: str, message: str) -> None:
        if not is_main_thread():
            am = self._get_async_manager()
            am.execute_delayed(self.show_info, 0, title, message)
            return
        mw = self._get_main_window()
        if mw:
            QMessageBox.information(mw, title, message)

    def show_error(self, title: str, message: str) -> None:
        if not is_main_thread():
            am = self._get_async_manager()
            am.execute_delayed(self.show_error, 0, title, message)
            return
        mw = self._get_main_window()
        if mw:
            QMessageBox.critical(mw, title, message)

    # 示例：调用查找替换对话框，传递选中内容
    def open_find_replace(self, dialog_getter: Callable[[], object], selected_text: str = "") -> None:
        dlg = dialog_getter()
        if not dlg:
            return
        if selected_text and hasattr(dlg, 'set_search_text'):
            dlg.set_search_text(selected_text)
        if hasattr(dlg, 'show'):
            dlg.show()
        if hasattr(dlg, 'raise_'):
            dlg.raise_()
        if hasattr(dlg, 'activateWindow'):
            dlg.activateWindow()


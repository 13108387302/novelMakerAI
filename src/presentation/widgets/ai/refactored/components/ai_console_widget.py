#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 控制台组件（基础版）

- 用于承载 AI 的流式输出、多轮对话记录与错误提示
- 提供统一的信号接线方法以便与 BaseAIWidget 兼容
"""

from __future__ import annotations

from typing import Optional, Dict
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import Qt


class AIConsoleWidget(QWidget):
    """AI 控制台（底部 Dock 的主部件）"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._last_stream_content: Dict[int, str] = {}
        self._streaming_active: Dict[int, bool] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 顶部工具栏（清空、停止占位）
        toolbar = QHBoxLayout()
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear)
        self.title_label = QLabel("AI 控制台")
        self.title_label.setStyleSheet("color:#666;")
        toolbar.addWidget(self.title_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.clear_btn)
        layout.addLayout(toolbar)

        # 输出区域
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setAcceptRichText(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.output.setFont(font)
        self.output.setPlaceholderText("AI 输出将显示在这里…\n可在面板中触发动作或对话，长响应会流式显示。")
        layout.addWidget(self.output, 1)

    # 基础输出 API
    def clear(self) -> None:
        self.output.clear()

    def append_html(self, html: str) -> None:
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertHtml(html)
        self.output.insertPlainText("\n")
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def append_text(self, text: str) -> None:
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(text + "\n")
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    # 与 AI 面板信号对接的便捷方法
    def connect_ai_widget(self, ai_widget: object) -> None:
        """将 BaseAIWidget/ModernAIWidget 的信号接入控制台（聚合流式输出）"""
        wid = id(ai_widget)
        self._last_stream_content.pop(wid, None)
        self._streaming_active[wid] = False

        # 兼容 BaseAIWidget 风格
        signals = getattr(ai_widget, 'signals', None)
        if signals:
            if hasattr(signals, 'request_started'):
                signals.request_started.connect(lambda req_id: self.on_request_started(req_id, wid))
            if hasattr(signals, 'request_completed'):
                signals.request_completed.connect(lambda req_id, content: self.on_request_completed(req_id, content, wid))
            if hasattr(signals, 'request_failed'):
                signals.request_failed.connect(lambda req_id, err: self.on_request_failed(req_id, err))
        # 兼容 ModernAIWidget 风格
        if hasattr(ai_widget, 'status_changed'):
            ai_widget.status_changed.connect(lambda msg, typ: self.append_html(f"<div style='color:#999'>ℹ {msg} ({typ})</div>"))
        if hasattr(ai_widget, 'ui_update_signal'):
            ai_widget.ui_update_signal.connect(lambda content: self._on_stream_update(wid, content))

    # 槽函数：与 BaseAIWidget.signals 对齐
    def on_request_started(self, request_id: str, wid: Optional[int] = None) -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        self.append_html(f"<div style='color:#999'>[{ts}] ▶ 开始请求: <b>{request_id}</b></div>")
        if wid is not None:
            self._last_stream_content[wid] = ""
            self._streaming_active[wid] = True

    def on_request_completed(self, request_id: str, content: str, wid: Optional[int] = None) -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        self.append_html(f"<div style='color:#999'>[{ts}] ✅ 完成请求: <b>{request_id}</b></div>")
        if wid is not None:
            # 如果有剩余未显示部分，补齐（通常 ui_update_signal 已完整覆盖）
            prev = self._last_stream_content.get(wid, "")
            if content and len(content) > len(prev):
                delta = content[len(prev):]
                if delta:
                    self.append_text(delta)
            self._streaming_active[wid] = False
            self._last_stream_content.pop(wid, None)

    def on_request_failed(self, request_id: str, error_message: str) -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        safe = error_message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.append_html(f"<div style='color:#c00'>[{ts}] ❌ 失败: <b>{request_id}</b> — {safe}</div>")

    def _on_stream_update(self, wid: int, content: str) -> None:
        """聚合同一请求的流式输出，只追加新增部分，避免全量重复"""
        prev = self._last_stream_content.get(wid, "")
        if not self._streaming_active.get(wid, False) and not prev:
            # 未显式收到开始信号，也尝试开启聚合
            self._streaming_active[wid] = True
            self._last_stream_content[wid] = ""
        # 仅追加新增的增量
        delta = content[len(prev):] if content.startswith(prev) else content
        if delta:
            self.append_text(delta)
            self._last_stream_content[wid] = content


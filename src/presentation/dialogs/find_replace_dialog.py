#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找替换对话框

提供文本查找和替换功能
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QCheckBox, QLabel, QGroupBox, QTabWidget,
    QWidget, QTextEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class FindReplaceDialog(QDialog):
    """查找替换对话框"""
    
    # 信号定义
    find_requested = pyqtSignal(str, dict)  # search_text, options
    replace_requested = pyqtSignal(str, str, dict)  # find_text, replace_text, options
    replace_all_requested = pyqtSignal(str, str, dict)  # find_text, replace_text, options
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        self._search_history = []
        self._replace_history = []
        
        logger.debug("查找替换对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("查找和替换")
        self.setModal(False)
        self.resize(450, 350)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 查找标签页
        self._create_find_tab()
        
        # 替换标签页
        self._create_replace_tab()
        
        # 高级搜索标签页
        self._create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 按钮区域
        self._create_buttons()
        layout.addLayout(self.buttons_layout)
        
        # 应用样式
        self._apply_styles()
    
    def _create_find_tab(self):
        """创建查找标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 查找输入
        find_group = QGroupBox("查找")
        find_layout = QGridLayout(find_group)
        
        find_layout.addWidget(QLabel("查找内容:"), 0, 0)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("输入要查找的文本...")
        find_layout.addWidget(self.find_edit, 0, 1)
        
        layout.addWidget(find_group)
        
        # 查找选项
        options_group = QGroupBox("选项")
        options_layout = QVBoxLayout(options_group)
        
        self.case_sensitive_check = QCheckBox("区分大小写")
        options_layout.addWidget(self.case_sensitive_check)
        
        self.whole_words_check = QCheckBox("全字匹配")
        options_layout.addWidget(self.whole_words_check)
        
        self.regex_check = QCheckBox("使用正则表达式")
        options_layout.addWidget(self.regex_check)
        
        self.wrap_search_check = QCheckBox("循环搜索")
        self.wrap_search_check.setChecked(True)
        options_layout.addWidget(self.wrap_search_check)
        
        layout.addWidget(options_group)
        
        # 搜索历史
        history_group = QGroupBox("搜索历史")
        history_layout = QVBoxLayout(history_group)
        
        self.search_history_list = QListWidget()
        self.search_history_list.setMaximumHeight(100)
        self.search_history_list.itemClicked.connect(self._on_history_clicked)
        history_layout.addWidget(self.search_history_list)
        
        layout.addWidget(history_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "🔍 查找")
    
    def _create_replace_tab(self):
        """创建替换标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 查找和替换输入
        replace_group = QGroupBox("查找和替换")
        replace_layout = QGridLayout(replace_group)
        
        replace_layout.addWidget(QLabel("查找内容:"), 0, 0)
        self.replace_find_edit = QLineEdit()
        self.replace_find_edit.setPlaceholderText("输入要查找的文本...")
        replace_layout.addWidget(self.replace_find_edit, 0, 1)
        
        replace_layout.addWidget(QLabel("替换为:"), 1, 0)
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("输入替换文本...")
        replace_layout.addWidget(self.replace_edit, 1, 1)
        
        layout.addWidget(replace_group)
        
        # 替换选项
        replace_options_group = QGroupBox("替换选项")
        replace_options_layout = QVBoxLayout(replace_options_group)
        
        self.replace_case_sensitive_check = QCheckBox("区分大小写")
        replace_options_layout.addWidget(self.replace_case_sensitive_check)
        
        self.replace_whole_words_check = QCheckBox("全字匹配")
        replace_options_layout.addWidget(self.replace_whole_words_check)
        
        self.replace_regex_check = QCheckBox("使用正则表达式")
        replace_options_layout.addWidget(self.replace_regex_check)
        
        self.confirm_replace_check = QCheckBox("替换前确认")
        self.confirm_replace_check.setChecked(True)
        replace_options_layout.addWidget(self.confirm_replace_check)
        
        layout.addWidget(replace_options_group)
        
        # 替换历史
        replace_history_group = QGroupBox("替换历史")
        replace_history_layout = QVBoxLayout(replace_history_group)
        
        self.replace_history_list = QListWidget()
        self.replace_history_list.setMaximumHeight(80)
        self.replace_history_list.itemClicked.connect(self._on_replace_history_clicked)
        replace_history_layout.addWidget(self.replace_history_list)
        
        layout.addWidget(replace_history_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "🔄 替换")
    
    def _create_advanced_tab(self):
        """创建高级搜索标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 搜索范围
        scope_group = QGroupBox("搜索范围")
        scope_layout = QVBoxLayout(scope_group)
        
        self.current_document_radio = QCheckBox("当前文档")
        self.current_document_radio.setChecked(True)
        scope_layout.addWidget(self.current_document_radio)
        
        self.all_documents_radio = QCheckBox("所有文档")
        scope_layout.addWidget(self.all_documents_radio)
        
        self.selected_text_radio = QCheckBox("选中文本")
        scope_layout.addWidget(self.selected_text_radio)
        
        layout.addWidget(scope_group)
        
        # 文件类型过滤
        filter_group = QGroupBox("文件类型")
        filter_layout = QVBoxLayout(filter_group)
        
        self.chapters_check = QCheckBox("章节文档")
        self.chapters_check.setChecked(True)
        filter_layout.addWidget(self.chapters_check)
        
        self.characters_check = QCheckBox("角色档案")
        filter_layout.addWidget(self.characters_check)
        
        self.notes_check = QCheckBox("笔记文档")
        filter_layout.addWidget(self.notes_check)
        
        layout.addWidget(filter_group)
        
        # 搜索结果预览
        preview_group = QGroupBox("搜索结果预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.results_preview = QTextEdit()
        self.results_preview.setMaximumHeight(120)
        self.results_preview.setReadOnly(True)
        self.results_preview.setPlaceholderText("搜索结果将在这里显示...")
        preview_layout.addWidget(self.results_preview)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "⚙️ 高级")
    
    def _create_buttons(self):
        """创建按钮"""
        self.buttons_layout = QHBoxLayout()
        
        # 查找按钮
        self.find_next_btn = QPushButton("查找下一个")
        self.find_next_btn.setDefault(True)
        self.find_next_btn.clicked.connect(self.find_next)
        self.buttons_layout.addWidget(self.find_next_btn)
        
        self.find_prev_btn = QPushButton("查找上一个")
        self.find_prev_btn.clicked.connect(self.find_previous)
        self.buttons_layout.addWidget(self.find_prev_btn)
        
        # 替换按钮
        self.replace_btn = QPushButton("替换")
        self.replace_btn.clicked.connect(self.replace_current)
        self.buttons_layout.addWidget(self.replace_btn)
        
        self.replace_all_btn = QPushButton("全部替换")
        self.replace_all_btn.clicked.connect(self.replace_all)
        self.buttons_layout.addWidget(self.replace_all_btn)
        
        self.buttons_layout.addStretch()
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.close_btn)
    
    def _setup_connections(self):
        """设置信号连接"""
        # 同步查找输入框
        self.find_edit.textChanged.connect(self.replace_find_edit.setText)
        self.replace_find_edit.textChanged.connect(self.find_edit.setText)
        
        # 同步选项
        self.case_sensitive_check.toggled.connect(self.replace_case_sensitive_check.setChecked)
        self.replace_case_sensitive_check.toggled.connect(self.case_sensitive_check.setChecked)
        
        self.whole_words_check.toggled.connect(self.replace_whole_words_check.setChecked)
        self.replace_whole_words_check.toggled.connect(self.whole_words_check.setChecked)
        
        self.regex_check.toggled.connect(self.replace_regex_check.setChecked)
        self.replace_regex_check.toggled.connect(self.regex_check.setChecked)
        
        # 回车键查找
        self.find_edit.returnPressed.connect(self.find_next)
        self.replace_find_edit.returnPressed.connect(self.find_next)
        self.replace_edit.returnPressed.connect(self.replace_current)
    
    def _apply_styles(self):
        """应用样式 - 使用主题管理器"""
        try:
            from src.presentation.styles.theme_manager import ThemeManager
            theme_manager = ThemeManager()

            # 应用对话框样式
            dialog_style = """
            QDialog {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
            }

            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background-color: white;
            }

            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }

            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }

            QLineEdit {
                padding: 6px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: white;
                color: #333;
                selection-background-color: #0078d4;
                selection-color: white;
            }

            QLineEdit:focus {
                border-color: #0078d4;
                color: #111;
            }

            QLineEdit::placeholder {
                color: #999;
            }

            QPushButton {
                padding: 6px 12px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background-color: #f0f0f0;
                min-width: 80px;
            }

            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #b0b0b0;
            }

            QPushButton:pressed {
                background-color: #d0d0d0;
            }

            QPushButton:default {
                background-color: #0078d4;
                color: white;
                border-color: #0078d4;
            }

            QPushButton:default:hover {
                background-color: #106ebe;
            }

            QCheckBox {
                spacing: 8px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #d0d0d0;
                border-radius: 2px;
                background-color: white;
            }

            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }

            QLabel {
                color: #333333;
            }
            """

            self.setStyleSheet(dialog_style)

        except Exception as e:
            # 如果主题管理器不可用，使用基本样式
            basic_style = """
            QDialog {
                background-color: #f5f5f5;
            }
            QPushButton {
                padding: 6px 12px;
                min-width: 80px;
            }
            QLineEdit {
                padding: 6px;
            }
            """
            self.setStyleSheet(basic_style)

    
    def _get_search_options(self) -> dict:
        """获取搜索选项"""
        return {
            "case_sensitive": self.case_sensitive_check.isChecked(),
            "whole_words": self.whole_words_check.isChecked(),
            "use_regex": self.regex_check.isChecked(),
            "wrap_search": self.wrap_search_check.isChecked(),
            "current_document": self.current_document_radio.isChecked(),
            "all_documents": self.all_documents_radio.isChecked(),
            "selected_text": self.selected_text_radio.isChecked(),
            "include_chapters": self.chapters_check.isChecked(),
            "include_characters": self.characters_check.isChecked(),
            "include_notes": self.notes_check.isChecked()
        }
    
    def _add_to_search_history(self, text: str):
        """添加到搜索历史"""
        if text and text not in self._search_history:
            self._search_history.insert(0, text)
            if len(self._search_history) > 10:
                self._search_history = self._search_history[:10]
            
            self._update_search_history_list()
    
    def _add_to_replace_history(self, find_text: str, replace_text: str):
        """添加到替换历史"""
        entry = f"{find_text} → {replace_text}"
        if entry not in self._replace_history:
            self._replace_history.insert(0, entry)
            if len(self._replace_history) > 10:
                self._replace_history = self._replace_history[:10]
            
            self._update_replace_history_list()
    
    def _update_search_history_list(self):
        """更新搜索历史列表"""
        self.search_history_list.clear()
        for item in self._search_history:
            self.search_history_list.addItem(QListWidgetItem(item))
    
    def _update_replace_history_list(self):
        """更新替换历史列表"""
        self.replace_history_list.clear()
        for item in self._replace_history:
            self.replace_history_list.addItem(QListWidgetItem(item))
    
    def _on_history_clicked(self, item: QListWidgetItem):
        """搜索历史点击"""
        self.find_edit.setText(item.text())
    
    def _on_replace_history_clicked(self, item: QListWidgetItem):
        """替换历史点击"""
        text = item.text()
        if " → " in text:
            find_text, replace_text = text.split(" → ", 1)
            self.replace_find_edit.setText(find_text)
            self.replace_edit.setText(replace_text)
    
    def find_next(self):
        """查找下一个"""
        search_text = self.find_edit.text()
        if not search_text:
            return
        
        self._add_to_search_history(search_text)
        options = self._get_search_options()
        self.find_requested.emit(search_text, options)
    
    def find_previous(self):
        """查找上一个"""
        search_text = self.find_edit.text()
        if not search_text:
            return
        
        self._add_to_search_history(search_text)
        options = self._get_search_options()
        options["backward"] = True
        self.find_requested.emit(search_text, options)
    
    def replace_current(self):
        """替换当前"""
        find_text = self.replace_find_edit.text()
        replace_text = self.replace_edit.text()
        
        if not find_text:
            return
        
        if self.confirm_replace_check.isChecked():
            reply = QMessageBox.question(
                self,
                "确认替换",
                f"确定要将 '{find_text}' 替换为 '{replace_text}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self._add_to_replace_history(find_text, replace_text)
        options = self._get_search_options()
        self.replace_requested.emit(find_text, replace_text, options)
    
    def replace_all(self):
        """全部替换"""
        find_text = self.replace_find_edit.text()
        replace_text = self.replace_edit.text()
        
        if not find_text:
            return
        
        reply = QMessageBox.question(
            self,
            "确认全部替换",
            f"确定要将所有 '{find_text}' 替换为 '{replace_text}' 吗？\n\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self._add_to_replace_history(find_text, replace_text)
        options = self._get_search_options()
        self.replace_all_requested.emit(find_text, replace_text, options)
    
    def set_search_text(self, text: str):
        """设置搜索文本"""
        self.find_edit.setText(text)
        self.replace_find_edit.setText(text)
    
    def show_results_preview(self, results: list):
        """显示搜索结果预览"""
        if not results:
            self.results_preview.setText("未找到匹配项")
            return
        
        preview_text = f"找到 {len(results)} 个匹配项:\n\n"
        
        for i, result in enumerate(results[:10]):  # 最多显示10个结果
            preview_text += f"{i+1}. {result.get('context', '')}\n"
        
        if len(results) > 10:
            preview_text += f"\n... 还有 {len(results) - 10} 个结果"
        
        self.results_preview.setText(preview_text)

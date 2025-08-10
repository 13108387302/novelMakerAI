#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具栏构建器

负责创建和配置主窗口的工具栏
"""

from PyQt6.QtWidgets import QToolBar, QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QObject, pyqtSignal, QSize

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ToolBarBuilder(QObject):
    """工具栏构建器"""
    
    # 信号定义
    action_triggered = pyqtSignal(str, object)  # 动作名称, 动作对象
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.actions = {}
        self.toolbars = {}
        
    def build_main_toolbar(self, main_window) -> QToolBar:
        """构建主工具栏"""
        toolbar = main_window.addToolBar("主工具栏")
        toolbar.setObjectName("main_toolbar")
        toolbar.setIconSize(QSize(24, 24))
        
        # 文件操作
        self._add_file_actions(toolbar, main_window)
        
        toolbar.addSeparator()
        
        # 编辑操作
        self._add_edit_actions(toolbar, main_window)

        toolbar.addSeparator()

        # 视图操作（简化版）
        self._add_view_actions(toolbar, main_window)
        
        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # 状态信息
        self._add_status_widgets(toolbar, main_window)
        
        self.toolbars["main"] = toolbar
        return toolbar
        
    def _add_file_actions(self, toolbar: QToolBar, main_window):
        """添加文件操作"""
        # 新建项目
        new_action = QAction("新建", main_window)
        new_action.setToolTip("新建项目 (Ctrl+N)")
        new_action.triggered.connect(lambda: self._emit_action("new_project", new_action))
        toolbar.addAction(new_action)
        self.actions["new_project"] = new_action
        
        # 打开项目
        open_action = QAction("打开", main_window)
        open_action.setToolTip("打开项目 (Ctrl+O)")
        open_action.triggered.connect(lambda: self._emit_action("open_project", open_action))
        toolbar.addAction(open_action)
        self.actions["open_project"] = open_action
        
        # 保存
        save_action = QAction("保存", main_window)
        save_action.setToolTip("保存当前文档 (Ctrl+S)")
        save_action.triggered.connect(lambda: self._emit_action("save", save_action))
        toolbar.addAction(save_action)
        self.actions["save"] = save_action
        
    def _add_edit_actions(self, toolbar: QToolBar, main_window):
        """添加编辑操作"""
        # 撤销
        undo_action = QAction("撤销", main_window)
        undo_action.setToolTip("撤销 (Ctrl+Z)")
        undo_action.triggered.connect(lambda: self._emit_action("undo", undo_action))
        toolbar.addAction(undo_action)
        self.actions["undo"] = undo_action
        
        # 重做
        redo_action = QAction("重做", main_window)
        redo_action.setToolTip("重做 (Ctrl+Y)")
        redo_action.triggered.connect(lambda: self._emit_action("redo", redo_action))
        toolbar.addAction(redo_action)
        self.actions["redo"] = redo_action
        
        # 查找
        find_action = QAction("查找", main_window)
        find_action.setToolTip("查找 (Ctrl+F)")
        find_action.triggered.connect(lambda: self._emit_action("find", find_action))
        toolbar.addAction(find_action)
        self.actions["find"] = find_action
        

        
    def _add_view_actions(self, toolbar: QToolBar, main_window):
        """添加视图操作（简化版）"""
        # AI Studio 显示/隐藏
        ai_assistant_action = QAction("AI Studio", main_window)
        ai_assistant_action.setCheckable(True)
        ai_assistant_action.setChecked(True)
        ai_assistant_action.setToolTip("显示/隐藏 AI Studio 页面")
        ai_assistant_action.triggered.connect(lambda: self._emit_action("toggle_ai_panel", ai_assistant_action))
        toolbar.addAction(ai_assistant_action)
        self.actions["toggle_ai_panel"] = ai_assistant_action

    def _add_status_widgets(self, toolbar: QToolBar, main_window):
        """添加状态组件"""
        # 创建状态容器
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 0, 5, 0)
        
        # AI状态标签
        ai_status_label = QLabel("AI: 就绪")
        ai_status_label.setObjectName("ai_status_label")
        ai_status_label.setStyleSheet("color: #2e8b57; font-weight: bold;")
        status_layout.addWidget(ai_status_label)
        
        # 分隔符
        separator = QLabel("|")
        separator.setStyleSheet("color: #ccc; margin: 0 5px;")
        status_layout.addWidget(separator)
        
        # 字数标签
        word_count_label = QLabel("字数: 0")
        word_count_label.setObjectName("word_count_label")
        word_count_label.setStyleSheet("color: #666;")
        status_layout.addWidget(word_count_label)
        
        toolbar.addWidget(status_widget)
        
        # 保存引用以便外部访问
        main_window.ai_status_label = ai_status_label
        main_window.word_count_label = word_count_label
        

        
    def _emit_action(self, action_name: str, action_data):
        """发出动作信号"""
        self.action_triggered.emit(action_name, action_data)
        
    def get_action(self, action_name: str) -> QAction:
        """获取动作"""
        return self.actions.get(action_name)
        
    def get_toolbar(self, toolbar_name: str) -> QToolBar:
        """获取工具栏"""
        return self.toolbars.get(toolbar_name)
        
    def enable_action(self, action_name: str, enabled: bool = True):
        """启用/禁用动作"""
        action = self.get_action(action_name)
        if action:
            action.setEnabled(enabled)
            
    def check_action(self, action_name: str, checked: bool = True):
        """选中/取消选中动作"""
        action = self.get_action(action_name)
        if action and action.isCheckable():
            action.setChecked(checked)
            
    def set_ai_mode(self, mode: str):
        """设置AI模式"""
        # 取消所有AI模式的选中状态
        for action_name in self.actions:
            if action_name.startswith("ai_mode_"):
                self.check_action(action_name, False)
                
        # 选中指定模式
        mode_action = f"ai_mode_{mode}"
        if mode_action in self.actions:
            self.check_action(mode_action, True)
            
    def update_ai_status(self, status: str):
        """更新AI状态显示"""
        # 这个方法可以通过主窗口的ai_status_label来更新
        pass
        
    def update_word_count(self, count: int):
        """更新字数显示"""
        # 这个方法可以通过主窗口的word_count_label来更新
        pass

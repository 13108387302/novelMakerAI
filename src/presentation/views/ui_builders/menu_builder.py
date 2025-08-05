#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
菜单构建器

负责创建和配置主窗口的菜单栏
"""

from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import QObject, pyqtSignal

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class MenuBuilder(QObject):
    """菜单构建器"""
    
    # 信号定义
    action_triggered = pyqtSignal(str, object)  # 动作名称, 动作对象
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.actions = {}
        
    def build_menu_bar(self, main_window) -> QMenuBar:
        """构建菜单栏"""
        menubar = main_window.menuBar()
        
        # 文件菜单
        self._create_file_menu(menubar, main_window)
        
        # 编辑菜单
        self._create_edit_menu(menubar, main_window)
        
        # 视图菜单
        self._create_view_menu(menubar, main_window)
        
        # AI菜单
        self._create_ai_menu(menubar, main_window)
        
        # 工具菜单
        self._create_tools_menu(menubar, main_window)
        
        # 帮助菜单
        self._create_help_menu(menubar, main_window)
        
        return menubar
        
    def _create_file_menu(self, menubar: QMenuBar, main_window):
        """创建文件菜单"""
        file_menu = menubar.addMenu("文件(&F)")
        
        # 新建项目
        new_project_action = QAction("新建项目(&N)", main_window)
        new_project_action.setShortcut(QKeySequence.StandardKey.New)
        new_project_action.triggered.connect(lambda: self._emit_action("new_project", new_project_action))
        file_menu.addAction(new_project_action)
        self.actions["new_project"] = new_project_action
        
        # 打开项目
        open_project_action = QAction("打开项目(&O)", main_window)
        open_project_action.setShortcut(QKeySequence.StandardKey.Open)
        open_project_action.triggered.connect(lambda: self._emit_action("open_project", open_project_action))
        file_menu.addAction(open_project_action)
        self.actions["open_project"] = open_project_action
        
        # 最近项目
        recent_menu = file_menu.addMenu("最近项目(&R)")
        self.actions["recent_menu"] = recent_menu
        
        file_menu.addSeparator()
        
        # 保存
        save_action = QAction("保存(&S)", main_window)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(lambda: self._emit_action("save", save_action))
        file_menu.addAction(save_action)
        self.actions["save"] = save_action
        
        # 另存为
        save_as_action = QAction("另存为(&A)", main_window)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(lambda: self._emit_action("save_as", save_as_action))
        file_menu.addAction(save_as_action)
        self.actions["save_as"] = save_as_action
        
        file_menu.addSeparator()
        
        # 导入
        import_action = QAction("导入项目(&I)", main_window)
        import_action.triggered.connect(lambda: self._emit_action("import_project", import_action))
        file_menu.addAction(import_action)
        self.actions["import_project"] = import_action
        
        # 导出
        export_action = QAction("导出项目(&E)", main_window)
        export_action.triggered.connect(lambda: self._emit_action("export_project", export_action))
        file_menu.addAction(export_action)
        self.actions["export_project"] = export_action
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", main_window)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(lambda: self._emit_action("exit", exit_action))
        file_menu.addAction(exit_action)
        self.actions["exit"] = exit_action
        
    def _create_edit_menu(self, menubar: QMenuBar, main_window):
        """创建编辑菜单"""
        edit_menu = menubar.addMenu("编辑(&E)")
        
        # 撤销
        undo_action = QAction("撤销(&U)", main_window)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(lambda: self._emit_action("undo", undo_action))
        edit_menu.addAction(undo_action)
        self.actions["undo"] = undo_action
        
        # 重做
        redo_action = QAction("重做(&R)", main_window)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(lambda: self._emit_action("redo", redo_action))
        edit_menu.addAction(redo_action)
        self.actions["redo"] = redo_action
        
        edit_menu.addSeparator()
        
        # 剪切
        cut_action = QAction("剪切(&T)", main_window)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(lambda: self._emit_action("cut", cut_action))
        edit_menu.addAction(cut_action)
        self.actions["cut"] = cut_action
        
        # 复制
        copy_action = QAction("复制(&C)", main_window)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(lambda: self._emit_action("copy", copy_action))
        edit_menu.addAction(copy_action)
        self.actions["copy"] = copy_action
        
        # 粘贴
        paste_action = QAction("粘贴(&P)", main_window)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(lambda: self._emit_action("paste", paste_action))
        edit_menu.addAction(paste_action)
        self.actions["paste"] = paste_action
        
        edit_menu.addSeparator()
        
        # 查找
        find_action = QAction("查找(&F)", main_window)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(lambda: self._emit_action("find", find_action))
        edit_menu.addAction(find_action)
        self.actions["find"] = find_action
        
        # 替换
        replace_action = QAction("替换(&H)", main_window)
        replace_action.setShortcut(QKeySequence.StandardKey.Replace)
        replace_action.triggered.connect(lambda: self._emit_action("replace", replace_action))
        edit_menu.addAction(replace_action)
        self.actions["replace"] = replace_action
        
    def _create_view_menu(self, menubar: QMenuBar, main_window):
        """创建视图菜单"""
        view_menu = menubar.addMenu("视图(&V)")
        
        # 项目树
        project_tree_action = QAction("项目树(&P)", main_window)
        project_tree_action.setCheckable(True)
        project_tree_action.setChecked(True)
        project_tree_action.triggered.connect(lambda: self._emit_action("toggle_project_tree", project_tree_action))
        view_menu.addAction(project_tree_action)
        self.actions["toggle_project_tree"] = project_tree_action
        
        # AI面板
        ai_panel_action = QAction("AI面板(&A)", main_window)
        ai_panel_action.setCheckable(True)
        ai_panel_action.setChecked(True)
        ai_panel_action.triggered.connect(lambda: self._emit_action("toggle_ai_panel", ai_panel_action))
        view_menu.addAction(ai_panel_action)
        self.actions["toggle_ai_panel"] = ai_panel_action

        # 状态面板
        status_panel_action = QAction("状态面板(&S)", main_window)
        status_panel_action.setCheckable(True)
        status_panel_action.setChecked(True)
        status_panel_action.triggered.connect(lambda: self._emit_action("toggle_status_panel", status_panel_action))
        view_menu.addAction(status_panel_action)
        self.actions["toggle_status_panel"] = status_panel_action

        view_menu.addSeparator()
        
        # 语法高亮
        syntax_highlight_action = QAction("语法高亮(&S)", main_window)
        syntax_highlight_action.setCheckable(True)
        syntax_highlight_action.setChecked(True)
        syntax_highlight_action.triggered.connect(lambda: self._emit_action("toggle_syntax_highlighting", syntax_highlight_action))
        view_menu.addAction(syntax_highlight_action)
        self.actions["toggle_syntax_highlighting"] = syntax_highlight_action
        
        view_menu.addSeparator()
        
        # 全屏
        fullscreen_action = QAction("全屏(&F)", main_window)
        fullscreen_action.setShortcut(QKeySequence("F11"))
        fullscreen_action.triggered.connect(lambda: self._emit_action("toggle_fullscreen", fullscreen_action))
        view_menu.addAction(fullscreen_action)
        self.actions["toggle_fullscreen"] = fullscreen_action
        
    def _create_ai_menu(self, menubar: QMenuBar, main_window):
        """创建AI菜单（简化版）"""
        ai_menu = menubar.addMenu("AI助手(&A)")

        # 显示AI面板（主要入口）
        show_ai_panel_action = QAction("显示AI助手面板(&S)", main_window)
        show_ai_panel_action.setShortcut(QKeySequence("F4"))
        show_ai_panel_action.triggered.connect(lambda: self._emit_action("show_ai_panel", show_ai_panel_action))
        ai_menu.addAction(show_ai_panel_action)
        self.actions["show_ai_panel"] = show_ai_panel_action

        ai_menu.addSeparator()

        # AI服务设置
        ai_setup_action = QAction("🔧 AI服务设置(&S)", main_window)
        ai_setup_action.triggered.connect(lambda: self._emit_action("ai_setup", ai_setup_action))
        ai_menu.addAction(ai_setup_action)
        self.actions["ai_setup"] = ai_setup_action
        
    def _create_tools_menu(self, menubar: QMenuBar, main_window):
        """创建工具菜单"""
        tools_menu = menubar.addMenu("工具(&T)")
        
        # 字数统计
        word_count_action = QAction("字数统计(&W)", main_window)
        word_count_action.triggered.connect(lambda: self._emit_action("word_count", word_count_action))
        tools_menu.addAction(word_count_action)
        self.actions["word_count"] = word_count_action
        
        # 备份管理
        backup_action = QAction("备份管理(&B)", main_window)
        backup_action.triggered.connect(lambda: self._emit_action("backup_management", backup_action))
        tools_menu.addAction(backup_action)
        self.actions["backup_management"] = backup_action
        
        tools_menu.addSeparator()
        
        # 设置
        settings_action = QAction("设置(&S)", main_window)
        settings_action.triggered.connect(lambda: self._emit_action("settings", settings_action))
        tools_menu.addAction(settings_action)
        self.actions["settings"] = settings_action
        
    def _create_help_menu(self, menubar: QMenuBar, main_window):
        """创建帮助菜单"""
        help_menu = menubar.addMenu("帮助(&H)")
        
        # 快捷键帮助
        shortcuts_action = QAction("快捷键(&K)", main_window)
        shortcuts_action.setShortcut(QKeySequence("F1"))
        shortcuts_action.triggered.connect(lambda: self._emit_action("show_shortcuts", shortcuts_action))
        help_menu.addAction(shortcuts_action)
        self.actions["show_shortcuts"] = shortcuts_action
        
        help_menu.addSeparator()
        
        # 关于
        about_action = QAction("关于(&A)", main_window)
        about_action.triggered.connect(lambda: self._emit_action("about", about_action))
        help_menu.addAction(about_action)
        self.actions["about"] = about_action
        
    def _emit_action(self, action_name: str, action: QAction):
        """发出动作信号"""
        self.action_triggered.emit(action_name, action)
        
    def get_action(self, action_name: str) -> QAction:
        """获取动作"""
        return self.actions.get(action_name)
        
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

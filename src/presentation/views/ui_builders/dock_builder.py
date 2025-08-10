#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
停靠窗口构建器

负责创建和配置主窗口的停靠窗口
"""

from PyQt6.QtWidgets import QDockWidget
from PyQt6.QtCore import QObject, pyqtSignal, Qt

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class DockBuilder(QObject):
    """停靠窗口构建器"""
    
    # 信号定义
    dock_visibility_changed = pyqtSignal(str, bool)  # 停靠窗口名称, 是否可见
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.docks = {}
        
    def create_project_dock(self, main_window, project_tree_widget) -> QDockWidget:
        """创建项目停靠窗口"""
        project_dock = QDockWidget("项目", main_window)
        project_dock.setObjectName("project_dock")
        project_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # 设置项目树组件
        project_dock.setWidget(project_tree_widget)
        
        # 连接可见性变化信号
        project_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("project", visible)
        )
        
        # 添加到主窗口
        main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, project_dock)
        
        # 保存引用
        self.docks["project"] = project_dock
        main_window.project_dock = project_dock
        # 注册到主窗口的注册表
        if hasattr(main_window, 'dock_registry'):
            main_window.dock_registry["project"] = project_dock
            main_window.view_registry["project_tree"] = project_tree_widget

        return project_dock

    # 旧的 AI Dock 已废弃，改为中心区域 AI Studio 页面
    def create_status_dock(self, main_window, status_panel_widget) -> QDockWidget:
        """创建状态停靠窗口"""
        status_dock = QDockWidget("状态", main_window)
        status_dock.setObjectName("status_dock")
        status_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # 设置状态面板组件
        status_dock.setWidget(status_panel_widget)

        # 连接可见性变化信号
        status_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("status", visible)
        )

        # 添加到主窗口（右侧，与AI面板并列）
        main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, status_dock)

        # 确保状态面板默认可见
        status_dock.setVisible(True)

        # 保存引用
        self.docks["status"] = status_dock
        main_window.status_dock = status_dock
        # 注册到主窗口的注册表
        if hasattr(main_window, 'dock_registry'):
            main_window.dock_registry["status"] = status_dock
            main_window.view_registry["status_panel"] = status_panel_widget

        return status_dock

    # 旧的右侧标签页 Dock 已废弃（全局AI/文档AI），改用 AI Studio 页面
    def create_output_dock(self, main_window) -> QDockWidget:
        """创建输出停靠窗口（系统输出）"""
        from PyQt6.QtWidgets import QTextEdit

        output_text = QTextEdit()
        output_text.setObjectName("output_text")
        output_text.setReadOnly(True)
        output_text.setPlaceholderText("系统输出信息将显示在这里...")

        output_dock = QDockWidget("输出", main_window)
        output_dock.setObjectName("output_dock")
        output_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        output_dock.setWidget(output_text)

        output_dock.setVisible(False)
        output_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("output", visible)
        )
        main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, output_dock)

        self.docks["output"] = output_dock
        main_window.output_dock = output_dock
        main_window.output_text = output_text
        # 注册到主窗口的注册表
        if hasattr(main_window, 'dock_registry'):
            main_window.dock_registry["output"] = output_dock
            main_window.view_registry["output_text"] = output_text

        return output_dock

    def create_ai_console_dock(self, main_window) -> QDockWidget:
        """创建 AI 控制台停靠窗口（底部，默认隐藏）"""
        from src.presentation.widgets.ai.refactored.components.ai_console_widget import AIConsoleWidget
        ai_console = AIConsoleWidget()
        ai_console_dock = QDockWidget("AI 控制台", main_window)
        ai_console_dock.setObjectName("ai_console_dock")
        ai_console_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        ai_console_dock.setWidget(ai_console)
        ai_console_dock.setVisible(False)
        ai_console_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("ai_console", visible)
        )
        main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, ai_console_dock)
        self.docks["ai_console"] = ai_console_dock
        main_window.ai_console_dock = ai_console_dock
        main_window.ai_console = ai_console
        # 注册到主窗口的注册表
        if hasattr(main_window, 'dock_registry'):
            main_window.dock_registry["ai_console"] = ai_console_dock
            main_window.view_registry["ai_console"] = ai_console
        return ai_console_dock

    def get_dock(self, dock_name: str) -> QDockWidget:
        """获取停靠窗口"""
        return self.docks.get(dock_name)
        
    def show_dock(self, dock_name: str):
        """显示停靠窗口"""
        dock = self.get_dock(dock_name)
        if dock:
            dock.setVisible(True)
            dock.raise_()
            
    def hide_dock(self, dock_name: str):
        """隐藏停靠窗口"""
        dock = self.get_dock(dock_name)
        if dock:
            dock.setVisible(False)
            
    def toggle_dock(self, dock_name: str):
        """切换停靠窗口显示状态"""
        dock = self.get_dock(dock_name)
        if dock:
            dock.setVisible(not dock.isVisible())
            
    def is_dock_visible(self, dock_name: str) -> bool:
        """检查停靠窗口是否可见"""
        dock = self.get_dock(dock_name)
        return dock.isVisible() if dock else False
        
    def set_dock_sizes(self, main_window):
        """设置停靠窗口大小"""
        try:
            # 设置左右停靠窗口的宽度比例
            # 旧的 right_tabs 尺寸管理已移除，AI Studio 在中央区域
            return

        except Exception as e:
            logger.warning(f"设置停靠窗口大小失败: {e}")
            
    def save_dock_state(self, main_window) -> bytes:
        """保存停靠窗口状态"""
        try:
            return main_window.saveState()
        except Exception as e:
            logger.error(f"保存停靠窗口状态失败: {e}")
            return b""
            
    def restore_dock_state(self, main_window, state: bytes) -> bool:
        """恢复停靠窗口状态"""
        try:
            if state:
                return main_window.restoreState(state)
            return False
        except Exception as e:
            logger.error(f"恢复停靠窗口状态失败: {e}")
            return False
            
    def reset_dock_layout(self, main_window):
        """重置停靠窗口布局"""
        try:
            # 重新排列所有停靠窗口
            for dock_name, dock in self.docks.items():
                if dock_name == "project":
                    main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
                elif dock_name in ["ai", "right_tabs", "status"]:
                    main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                elif dock_name in ["output"]:
                    main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
                    
            # 重新设置大小
            self.set_dock_sizes(main_window)
            
        except Exception as e:
            logger.error(f"重置停靠窗口布局失败: {e}")
            
    def get_all_dock_names(self) -> list:
        """获取所有停靠窗口名称"""
        return list(self.docks.keys())
        
    def get_visible_docks(self) -> list:
        """获取所有可见的停靠窗口"""
        visible_docks = []
        for dock_name, dock in self.docks.items():
            if dock.isVisible():
                visible_docks.append(dock_name)
        return visible_docks

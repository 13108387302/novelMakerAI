#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
停靠窗口构建器

负责创建和配置主窗口的停靠窗口
"""

from PyQt6.QtWidgets import QDockWidget, QTabWidget
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
        
        return project_dock
        
    def create_ai_dock(self, main_window, ai_panel_widget) -> QDockWidget:
        """创建AI停靠窗口"""
        ai_dock = QDockWidget("AI助手", main_window)
        ai_dock.setObjectName("ai_dock")
        ai_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # 设置AI面板组件
        ai_dock.setWidget(ai_panel_widget)
        
        # 连接可见性变化信号
        ai_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("ai", visible)
        )
        
        # 添加到主窗口
        main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ai_dock)
        
        # 保存引用
        self.docks["ai"] = ai_dock
        main_window.ai_dock = ai_dock
        
        return ai_dock
        
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

        return status_dock
        
    def create_tabbed_right_dock(self, main_window, ai_panel_widget, document_ai_panel_widget) -> QTabWidget:
        """创建右侧标签页停靠窗口"""
        # 创建标签页容器
        right_tabs = QTabWidget()
        right_tabs.setObjectName("right_tabs")

        # 添加AI面板标签页
        right_tabs.addTab(ai_panel_widget, "🤖 全局AI")

        # 添加文档AI面板标签页
        right_tabs.addTab(document_ai_panel_widget, "📝 文档AI")
        
        # 创建停靠窗口
        right_dock = QDockWidget("AI助手", main_window)
        right_dock.setObjectName("right_dock")
        right_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # 设置标签页容器为停靠窗口的组件
        right_dock.setWidget(right_tabs)
        
        # 连接可见性变化信号
        right_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("right_tabs", visible)
        )
        
        # 添加到主窗口
        main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right_dock)
        
        # 保存引用
        self.docks["right_tabs"] = right_dock
        main_window.right_dock = right_dock
        main_window.right_tabs = right_tabs
        
        return right_tabs
        
    def create_output_dock(self, main_window) -> QDockWidget:
        """创建输出停靠窗口"""
        from PyQt6.QtWidgets import QTextEdit
        
        # 创建输出文本框
        output_text = QTextEdit()
        output_text.setObjectName("output_text")
        output_text.setReadOnly(True)
        output_text.setPlaceholderText("系统输出信息将显示在这里...")
        
        # 创建停靠窗口
        output_dock = QDockWidget("输出", main_window)
        output_dock.setObjectName("output_dock")
        output_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        output_dock.setWidget(output_text)
        
        # 默认隐藏
        output_dock.setVisible(False)
        
        # 连接可见性变化信号
        output_dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit("output", visible)
        )
        
        # 添加到主窗口
        main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, output_dock)
        
        # 保存引用
        self.docks["output"] = output_dock
        main_window.output_dock = output_dock
        main_window.output_text = output_text
        
        return output_dock
        
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
            if "project" in self.docks and "right_tabs" in self.docks:
                # 获取主窗口宽度
                main_width = main_window.width()
                
                # 设置项目树宽度为主窗口的20%
                project_width = int(main_width * 0.2)
                
                # 设置AI面板宽度为主窗口的25%
                ai_width = int(main_width * 0.25)
                
                # 应用大小
                main_window.resizeDocks(
                    [self.docks["project"], self.docks["right_tabs"]],
                    [project_width, ai_width],
                    Qt.Orientation.Horizontal
                )
                
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

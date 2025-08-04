#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态栏构建器

负责创建和配置主窗口的状态栏
"""

from PyQt6.QtWidgets import QStatusBar, QLabel, QProgressBar, QWidget, QHBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class StatusBarBuilder(QObject):
    """状态栏构建器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widgets = {}
        
    def build_status_bar(self, main_window) -> QStatusBar:
        """构建状态栏"""
        status_bar = QStatusBar()
        main_window.setStatusBar(status_bar)
        
        # 主状态消息
        self._create_main_status(status_bar, main_window)
        
        # 进度条
        self._create_progress_bar(status_bar, main_window)
        
        # 右侧信息区域
        self._create_info_area(status_bar, main_window)
        
        return status_bar
        
    def _create_main_status(self, status_bar: QStatusBar, main_window):
        """创建主状态消息区域"""
        # 主状态标签
        status_label = QLabel("就绪")
        status_label.setObjectName("status_label")
        status_label.setStyleSheet("color: #333; padding: 2px 5px;")
        
        status_bar.addWidget(status_label, 1)  # 占用剩余空间
        
        # 保存引用
        main_window.status_label = status_label
        self.widgets["status_label"] = status_label
        
    def _create_progress_bar(self, status_bar: QStatusBar, main_window):
        """创建进度条"""
        progress_bar = QProgressBar()
        progress_bar.setObjectName("progress_bar")
        progress_bar.setVisible(False)  # 默认隐藏
        progress_bar.setMaximumWidth(200)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        
        status_bar.addPermanentWidget(progress_bar)
        
        # 保存引用
        main_window.progress_bar = progress_bar
        self.widgets["progress_bar"] = progress_bar
        
    def _create_info_area(self, status_bar: QStatusBar, main_window):
        """创建信息区域"""
        # 创建信息容器
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(5, 0, 5, 0)
        info_layout.setSpacing(10)
        
        # 项目信息
        project_label = QLabel("项目: 未加载")
        project_label.setObjectName("project_label")
        project_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(project_label)
        
        # 分隔符
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #ccc;")
        info_layout.addWidget(separator1)
        
        # 文档信息
        document_label = QLabel("文档: 无")
        document_label.setObjectName("document_label")
        document_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(document_label)
        
        # 分隔符
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #ccc;")
        info_layout.addWidget(separator2)
        
        # 光标位置
        cursor_label = QLabel("行: 1, 列: 1")
        cursor_label.setObjectName("cursor_label")
        cursor_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(cursor_label)
        
        # 分隔符
        separator3 = QLabel("|")
        separator3.setStyleSheet("color: #ccc;")
        info_layout.addWidget(separator3)
        
        # 编码信息
        encoding_label = QLabel("UTF-8")
        encoding_label.setObjectName("encoding_label")
        encoding_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(encoding_label)
        
        # 分隔符
        separator4 = QLabel("|")
        separator4.setStyleSheet("color: #ccc;")
        info_layout.addWidget(separator4)
        
        # 时间显示
        time_label = QLabel()
        time_label.setObjectName("time_label")
        time_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(time_label)
        
        # 更新时间显示
        self._setup_time_update(time_label)
        
        status_bar.addPermanentWidget(info_widget)
        
        # 保存引用
        main_window.project_label = project_label
        main_window.document_label = document_label
        main_window.cursor_label = cursor_label
        main_window.encoding_label = encoding_label
        main_window.time_label = time_label
        
        self.widgets.update({
            "project_label": project_label,
            "document_label": document_label,
            "cursor_label": cursor_label,
            "encoding_label": encoding_label,
            "time_label": time_label
        })
        
    def _setup_time_update(self, time_label: QLabel):
        """设置时间更新"""
        from datetime import datetime
        
        def update_time():
            current_time = datetime.now().strftime("%H:%M:%S")
            time_label.setText(current_time)
            
        # 创建定时器
        timer = QTimer()
        timer.timeout.connect(update_time)
        timer.start(1000)  # 每秒更新
        
        # 立即更新一次
        update_time()
        
        # 保存定时器引用防止被垃圾回收
        self.widgets["time_timer"] = timer
        
    def show_message(self, message: str, timeout: int = 3000):
        """显示临时消息"""
        if "status_label" in self.widgets:
            status_label = self.widgets["status_label"]
            original_text = status_label.text()
            
            # 显示消息
            status_label.setText(message)
            status_label.setStyleSheet("color: #2e8b57; padding: 2px 5px; font-weight: bold;")
            
            # 设置定时器恢复原始文本
            def restore_text():
                status_label.setText(original_text)
                status_label.setStyleSheet("color: #333; padding: 2px 5px;")
                
            QTimer.singleShot(timeout, restore_text)
            
    def show_error(self, message: str, timeout: int = 5000):
        """显示错误消息"""
        if "status_label" in self.widgets:
            status_label = self.widgets["status_label"]
            original_text = status_label.text()
            
            # 显示错误消息
            status_label.setText(f"错误: {message}")
            status_label.setStyleSheet("color: #d32f2f; padding: 2px 5px; font-weight: bold;")
            
            # 设置定时器恢复原始文本
            def restore_text():
                status_label.setText(original_text)
                status_label.setStyleSheet("color: #333; padding: 2px 5px;")
                
            QTimer.singleShot(timeout, restore_text)
            
    def show_progress(self, value: int, maximum: int = 100, text: str = ""):
        """显示进度"""
        if "progress_bar" in self.widgets:
            progress_bar = self.widgets["progress_bar"]
            progress_bar.setVisible(True)
            progress_bar.setMaximum(maximum)
            progress_bar.setValue(value)
            
            if text:
                progress_bar.setFormat(text)
            else:
                progress_bar.setFormat(f"{value}/{maximum}")
                
    def hide_progress(self):
        """隐藏进度条"""
        if "progress_bar" in self.widgets:
            self.widgets["progress_bar"].setVisible(False)
            
    def update_project_info(self, project_name: str = ""):
        """更新项目信息"""
        if "project_label" in self.widgets:
            if project_name:
                self.widgets["project_label"].setText(f"项目: {project_name}")
            else:
                self.widgets["project_label"].setText("项目: 未加载")
                
    def update_document_info(self, document_name: str = ""):
        """更新文档信息"""
        if "document_label" in self.widgets:
            if document_name:
                self.widgets["document_label"].setText(f"文档: {document_name}")
            else:
                self.widgets["document_label"].setText("文档: 无")
                
    def update_cursor_position(self, line: int, column: int):
        """更新光标位置"""
        if "cursor_label" in self.widgets:
            self.widgets["cursor_label"].setText(f"行: {line}, 列: {column}")
            
    def update_encoding(self, encoding: str):
        """更新编码信息"""
        if "encoding_label" in self.widgets:
            self.widgets["encoding_label"].setText(encoding)
            
    def get_widget(self, widget_name: str):
        """获取组件"""
        return self.widgets.get(widget_name)
        
    def set_permanent_message(self, message: str):
        """设置永久状态消息"""
        if "status_label" in self.widgets:
            self.widgets["status_label"].setText(message)
            self.widgets["status_label"].setStyleSheet("color: #333; padding: 2px 5px;")

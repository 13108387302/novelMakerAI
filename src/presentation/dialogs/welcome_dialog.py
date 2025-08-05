#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
欢迎对话框

显示应用程序启动时的欢迎信息，包含新特性介绍和"下次不再提醒"选项。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class WelcomeDialog(QDialog):
    """欢迎对话框"""
    
    # 信号
    dont_show_again_changed = pyqtSignal(bool)  # 不再提醒状态变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎉 欢迎使用AI小说编辑器 2.0")
        self.setModal(True)
        self.setFixedSize(600, 700)
        
        # 设置窗口图标
        self.setWindowIcon(QIcon("📖"))
        
        self._setup_ui()
        self._apply_styles()
        
        logger.debug("欢迎对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(30, 30, 30, 20)
        
        # 标题区域
        self._create_header(content_layout)
        
        # 特性介绍区域
        self._create_features_section(content_layout)
        
        # 开始创作区域
        self._create_getting_started_section(content_layout)
        
        # 版本信息
        self._create_version_info(content_layout)
        
        # 设置滚动内容
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # 底部按钮区域
        self._create_bottom_section(layout)
    
    def _create_header(self, layout):
        """创建标题区域"""
        # 主标题
        title_label = QLabel("欢迎使用AI小说编辑器 2.0！")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("全新架构，智能创作，开启您的写作新体验")
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)
    
    def _create_features_section(self, layout):
        """创建特性介绍区域"""
        # 特性标题
        features_title = QLabel("🏗️ 全新架构特性：")
        features_title.setObjectName("section_title")
        layout.addWidget(features_title)
        
        # 特性列表
        features = [
            ("🔧", "现代化分层架构设计", "采用领域驱动设计，代码结构更清晰"),
            ("💉", "依赖注入容器管理", "松耦合设计，组件更易测试和维护"),
            ("📡", "事件驱动通信机制", "响应式架构，实时状态同步"),
            ("🗄️", "仓储模式数据访问", "统一的数据访问接口，支持多种存储"),
            ("🎨", "响应式主题系统", "美观的界面设计，支持主题切换"),
            ("🤖", "多AI服务集成", "支持多种AI模型，智能写作助手")
        ]
        
        for icon, title, description in features:
            feature_widget = self._create_feature_item(icon, title, description)
            layout.addWidget(feature_widget)
    
    def _create_feature_item(self, icon, title, description):
        """创建特性项目"""
        container = QFrame()
        container.setObjectName("feature_item")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setObjectName("feature_icon")
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 文本区域
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("feature_title")
        text_layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(description)
        desc_label.setObjectName("feature_description")
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        
        return container
    
    def _create_getting_started_section(self, layout):
        """创建开始创作区域"""
        # 开始创作标题
        start_title = QLabel("🚀 开始创作：")
        start_title.setObjectName("section_title")
        layout.addWidget(start_title)
        
        # 步骤列表
        steps = [
            "点击'文件 - 新建项目'创建项目",
            "使用右侧AI助手提升创作效率",
            "体验全新的写作体验！"
        ]
        
        for step in steps:
            step_label = QLabel(f"• {step}")
            step_label.setObjectName("step_item")
            step_label.setContentsMargins(20, 5, 20, 5)
            layout.addWidget(step_label)
    
    def _create_version_info(self, layout):
        """创建版本信息"""
        version_label = QLabel("版本 2.0.0 | 基于现代化架构重构")
        version_label.setObjectName("version_info")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
    
    def _create_bottom_section(self, layout):
        """创建底部区域"""
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottom_frame")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(20, 15, 20, 15)
        bottom_layout.setSpacing(15)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setObjectName("separator")
        bottom_layout.addWidget(separator)
        
        # 复选框和按钮区域
        controls_layout = QHBoxLayout()
        
        # 不再提醒复选框
        self.dont_show_checkbox = QCheckBox("下次启动时不再显示此对话框")
        self.dont_show_checkbox.setObjectName("dont_show_checkbox")
        self.dont_show_checkbox.stateChanged.connect(self._on_dont_show_changed)
        controls_layout.addWidget(self.dont_show_checkbox)
        
        controls_layout.addStretch()
        
        # 确定按钮
        ok_button = QPushButton("开始使用")
        ok_button.setObjectName("ok_button")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        controls_layout.addWidget(ok_button)
        
        bottom_layout.addLayout(controls_layout)
        layout.addWidget(bottom_frame)
    
    def _on_dont_show_changed(self, state):
        """处理不再提醒状态变化"""
        dont_show = state == Qt.CheckState.Checked.value
        self.dont_show_again_changed.emit(dont_show)
        logger.debug(f"不再提醒设置变更: {dont_show}")
    
    def set_dont_show_again(self, dont_show: bool):
        """设置不再提醒状态"""
        self.dont_show_checkbox.setChecked(dont_show)
    
    def get_dont_show_again(self) -> bool:
        """获取不再提醒状态"""
        return self.dont_show_checkbox.isChecked()
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            
            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: #2196F3;
                margin: 10px 0;
            }
            
            QLabel#subtitle {
                font-size: 14px;
                color: #666666;
                margin-bottom: 20px;
            }
            
            QLabel#section_title {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                margin: 15px 0 10px 0;
            }
            
            QFrame#feature_item {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin: 2px 0;
            }
            
            QFrame#feature_item:hover {
                background-color: #e3f2fd;
                border-color: #2196F3;
            }
            
            QLabel#feature_icon {
                font-size: 18px;
            }
            
            QLabel#feature_title {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
            
            QLabel#feature_description {
                font-size: 12px;
                color: #666666;
            }
            
            QLabel#step_item {
                font-size: 14px;
                color: #333333;
                margin: 3px 0;
            }
            
            QLabel#version_info {
                font-size: 12px;
                color: #999999;
                margin-top: 20px;
            }
            
            QFrame#bottom_frame {
                background-color: #f8f9fa;
            }
            
            QFrame#separator {
                color: #dee2e6;
            }
            
            QCheckBox#dont_show_checkbox {
                font-size: 12px;
                color: #666666;
            }
            
            QPushButton#ok_button {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            
            QPushButton#ok_button:hover {
                background-color: #1976D2;
            }
            
            QPushButton#ok_button:pressed {
                background-color: #1565C0;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
        """)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框

应用程序设置和偏好配置
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QSpinBox, QSlider, QGroupBox, QColorDialog, QFontDialog,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
    QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from src.application.services.settings_service import SettingsService
from src.presentation.styles.theme_manager import ThemeManager, ThemeType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """
    设置对话框

    提供应用程序设置和偏好配置的用户界面。
    使用标签页组织不同类别的设置选项。

    实现方式：
    - 使用QTabWidget组织设置分类
    - 提供实时预览和应用功能
    - 支持设置的导入导出
    - 包含设置验证和错误处理
    - 提供设置重置功能

    Attributes:
        settings_service: 设置服务实例
        theme_manager: 主题管理器实例

    Signals:
        settings_changed: 设置变更信号(setting_key, value)
        theme_changed: 主题变更信号(theme_name)
    """

    # 信号定义
    settings_changed = pyqtSignal(str, object)  # setting_key, value
    theme_changed = pyqtSignal(str)  # theme_name

    def __init__(self, settings_service: SettingsService, theme_manager: ThemeManager, parent=None):
        """
        初始化设置对话框

        Args:
            settings_service: 设置服务实例
            theme_manager: 主题管理器实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.settings_service = settings_service
        self.theme_manager = theme_manager
        self._setup_ui()
        self._load_settings()
        self._setup_connections()

        logger.debug("设置对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(600, 500)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 创建各个设置页面
        self._create_general_tab()
        self._create_editor_tab()
        self._create_appearance_tab()
        self._create_shortcuts_tab()
        self._create_backup_tab()
        self._create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 按钮区域
        self._create_buttons()
        layout.addLayout(self.buttons_layout)
        
        # 应用样式
        self._apply_styles()
    
    def _create_general_tab(self):
        """创建常规设置标签页"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 用户信息
        user_group = QGroupBox("用户信息")
        user_layout = QGridLayout(user_group)
        
        user_layout.addWidget(QLabel("默认作者:"), 0, 0)
        self.default_author_edit = QLineEdit()
        user_layout.addWidget(self.default_author_edit, 0, 1)
        
        user_layout.addWidget(QLabel("默认类型:"), 1, 0)
        self.default_genre_combo = QComboBox()
        self.default_genre_combo.addItems(["小说", "散文", "诗歌", "剧本", "其他"])
        user_layout.addWidget(self.default_genre_combo, 1, 1)
        
        layout.addWidget(user_group)
        
        # 项目设置
        project_group = QGroupBox("项目设置")
        project_layout = QGridLayout(project_group)
        
        project_layout.addWidget(QLabel("默认目标字数:"), 0, 0)
        self.target_word_count_spin = QSpinBox()
        self.target_word_count_spin.setRange(1000, 1000000)
        self.target_word_count_spin.setValue(80000)
        self.target_word_count_spin.setSuffix(" 字")
        project_layout.addWidget(self.target_word_count_spin, 0, 1)
        
        project_layout.addWidget(QLabel("自动备份间隔:"), 1, 0)
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setRange(5, 120)
        self.backup_interval_spin.setValue(30)
        self.backup_interval_spin.setSuffix(" 分钟")
        project_layout.addWidget(self.backup_interval_spin, 1, 1)
        
        self.auto_backup_check = QCheckBox("启用自动备份")
        project_layout.addWidget(self.auto_backup_check, 2, 0, 1, 2)
        
        self.version_control_check = QCheckBox("启用版本控制")
        project_layout.addWidget(self.version_control_check, 3, 0, 1, 2)

        self.auto_open_last_project_check = QCheckBox("启动时自动打开上次项目")
        project_layout.addWidget(self.auto_open_last_project_check, 4, 0, 1, 2)

        layout.addWidget(project_group)
        
        # 语言和地区
        locale_group = QGroupBox("语言和地区")
        locale_layout = QGridLayout(locale_group)
        
        locale_layout.addWidget(QLabel("界面语言:"), 0, 0)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["简体中文", "繁体中文", "English"])
        locale_layout.addWidget(self.language_combo, 0, 1)
        
        layout.addWidget(locale_group)

        # AI设置快捷入口
        ai_group = QGroupBox("AI助手设置")
        ai_layout = QVBoxLayout(ai_group)

        ai_info = QLabel("AI助手功能需要单独配置API密钥和服务参数")
        ai_info.setStyleSheet("color: #666; font-style: italic;")
        ai_layout.addWidget(ai_info)

        self.ai_setup_btn = QPushButton("🔧 打开AI服务设置")
        self.ai_setup_btn.setToolTip("配置OpenAI、DeepSeek等AI服务的API密钥和参数")
        self.ai_setup_btn.clicked.connect(self._open_ai_setup)
        ai_layout.addWidget(self.ai_setup_btn)

        layout.addWidget(ai_group)

        layout.addStretch()

        # 将内容设置到滚动区域
        scroll_area.setWidget(tab)
        self.tab_widget.addTab(scroll_area, "🏠 常规")
    
    def _create_editor_tab(self):
        """创建编辑器设置标签页"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 编辑器外观
        appearance_group = QGroupBox("编辑器外观")
        appearance_layout = QGridLayout(appearance_group)
        
        appearance_layout.addWidget(QLabel("字体:"), 0, 0)
        self.font_btn = QPushButton("选择字体...")
        self.font_btn.clicked.connect(self._choose_font)
        appearance_layout.addWidget(self.font_btn, 0, 1)
        
        appearance_layout.addWidget(QLabel("字体大小:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        appearance_layout.addWidget(self.font_size_spin, 1, 1)
        
        appearance_layout.addWidget(QLabel("行间距:"), 2, 0)
        self.line_spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_spacing_slider.setRange(100, 300)
        self.line_spacing_slider.setValue(150)
        self.line_spacing_label = QLabel("1.5")
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(self.line_spacing_slider)
        spacing_layout.addWidget(self.line_spacing_label)
        appearance_layout.addLayout(spacing_layout, 2, 1)
        
        layout.addWidget(appearance_group)
        
        # 编辑器行为（仅保留已实现的功能）
        behavior_group = QGroupBox("编辑器行为")
        behavior_layout = QVBoxLayout(behavior_group)

        # 添加说明
        behavior_info = QLabel("注意：部分编辑器功能正在开发中，当前版本支持语法高亮和基本编辑功能")
        behavior_info.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        behavior_layout.addWidget(behavior_info)

        # 仅保留已实现的设置
        self.syntax_highlighting_check = QCheckBox("启用语法高亮")
        self.syntax_highlighting_check.setChecked(True)
        self.syntax_highlighting_check.setToolTip("为小说文本提供对话、标题等元素的高亮显示")
        behavior_layout.addWidget(self.syntax_highlighting_check)

        layout.addWidget(behavior_group)
        
        # 自动保存
        autosave_group = QGroupBox("自动保存")
        autosave_layout = QGridLayout(autosave_group)
        
        autosave_layout.addWidget(QLabel("自动保存间隔:"), 0, 0)
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(10, 300)
        self.autosave_interval_spin.setValue(30)
        self.autosave_interval_spin.setSuffix(" 秒")
        autosave_layout.addWidget(self.autosave_interval_spin, 0, 1)
        
        layout.addWidget(autosave_group)

        layout.addStretch()

        # 将内容设置到滚动区域
        scroll_area.setWidget(tab)
        self.tab_widget.addTab(scroll_area, "✏️ 编辑器")
    

    
    def _create_appearance_tab(self):
        """创建外观设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QGridLayout(theme_group)
        
        theme_layout.addWidget(QLabel("主题:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "自动"])
        theme_layout.addWidget(self.theme_combo, 0, 1)
        
        self.preview_btn = QPushButton("预览主题")
        self.preview_btn.clicked.connect(self._preview_theme)
        theme_layout.addWidget(self.preview_btn, 0, 2)
        
        layout.addWidget(theme_group)
        
        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QVBoxLayout(ui_group)
        
        self.show_word_count_check = QCheckBox("显示字数统计")
        ui_layout.addWidget(self.show_word_count_check)
        
        self.show_character_count_check = QCheckBox("显示字符统计")
        ui_layout.addWidget(self.show_character_count_check)
        
        self.show_reading_time_check = QCheckBox("显示阅读时间")
        ui_layout.addWidget(self.show_reading_time_check)
        
        layout.addWidget(ui_group)
        
        # 窗口设置
        window_group = QGroupBox("窗口设置")
        window_layout = QGridLayout(window_group)
        
        window_layout.addWidget(QLabel("最近项目数量:"), 0, 0)
        self.recent_projects_spin = QSpinBox()
        self.recent_projects_spin.setRange(5, 20)
        self.recent_projects_spin.setValue(10)
        window_layout.addWidget(self.recent_projects_spin, 0, 1)
        
        self.remember_window_state_check = QCheckBox("记住窗口状态")
        window_layout.addWidget(self.remember_window_state_check, 1, 0, 1, 2)
        
        layout.addWidget(window_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "🎨 外观")
    
    def _create_advanced_tab(self):
        """创建高级设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 性能设置（仅保留已实现的功能）
        performance_group = QGroupBox("性能设置")
        performance_layout = QVBoxLayout(performance_group)

        performance_info = QLabel("性能优化功能正在开发中，当前版本已内置基本的性能优化")
        performance_info.setStyleSheet("color: #666; font-style: italic;")
        performance_layout.addWidget(performance_info)

        layout.addWidget(performance_group)
        
        # 调试设置
        debug_group = QGroupBox("调试设置")
        debug_layout = QGridLayout(debug_group)
        
        self.debug_mode_check = QCheckBox("调试模式")
        debug_layout.addWidget(self.debug_mode_check, 0, 0)
        
        debug_layout.addWidget(QLabel("日志级别:"), 1, 0)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        debug_layout.addWidget(self.log_level_combo, 1, 1)
        
        layout.addWidget(debug_group)
        
        # 应用程序设置
        app_group = QGroupBox("应用程序设置")
        app_layout = QVBoxLayout(app_group)

        self.check_updates_check = QCheckBox("启动时检查更新")
        self.check_updates_check.setChecked(True)
        app_layout.addWidget(self.check_updates_check)

        app_info = QLabel("其他隐私和实验性功能正在开发中")
        app_info.setStyleSheet("color: #666; font-style: italic;")
        app_layout.addWidget(app_info)

        layout.addWidget(app_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "⚙️ 高级")
    
    def _create_buttons(self):
        """创建按钮"""
        self.buttons_layout = QHBoxLayout()
        
        # 重置按钮
        self.reset_btn = QPushButton("重置为默认")
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        self.buttons_layout.addWidget(self.reset_btn)
        
        # 导入导出按钮
        self.export_btn = QPushButton("导出设置")
        self.export_btn.clicked.connect(self._export_settings)
        self.buttons_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("导入设置")
        self.import_btn.clicked.connect(self._import_settings)
        self.buttons_layout.addWidget(self.import_btn)
        
        self.buttons_layout.addStretch()
        
        # 确定取消按钮
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self._save_and_close)
        self.buttons_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        self.buttons_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton("应用")
        self.apply_btn.clicked.connect(self._apply_settings)
        self.buttons_layout.addWidget(self.apply_btn)
    
    def _setup_connections(self):
        """设置信号连接"""
        # 滑块值变化
        self.line_spacing_slider.valueChanged.connect(
            lambda v: self.line_spacing_label.setText(f"{v/100:.1f}")
        )

        # 主题变化
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
    
    def _apply_styles(self):
        """应用样式 - 使用主题管理器"""
        # 移除硬编码样式，使用主题管理器
        pass

    def _create_shortcuts_tab(self):
        """创建快捷键设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 快捷键列表
        shortcuts_group = QGroupBox("⌨️ 快捷键设置")
        shortcuts_layout = QVBoxLayout(shortcuts_group)

        # 快捷键说明
        info_label = QLabel("双击快捷键可以修改，按ESC取消修改")
        info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        shortcuts_layout.addWidget(info_label)

        # 快捷键表格（这里用简单的标签代替）
        shortcuts_info = [
            ("新建项目", "Ctrl+N"),
            ("打开项目", "Ctrl+O"),
            ("保存文档", "Ctrl+S"),
            ("查找替换", "Ctrl+F"),
            ("AI助手", "Ctrl+Shift+A"),
            ("字数统计", "Ctrl+Shift+W"),
            ("全屏模式", "F11"),
            ("专注模式", "Ctrl+Shift+F"),
        ]

        for action, shortcut in shortcuts_info:
            shortcut_layout = QHBoxLayout()
            action_label = QLabel(action)
            action_label.setMinimumWidth(150)
            shortcut_layout.addWidget(action_label)

            shortcut_label = QLabel(shortcut)
            shortcut_label.setStyleSheet("background: #f0f0f0; padding: 4px 8px; border-radius: 3px; font-family: monospace;")
            shortcut_layout.addWidget(shortcut_label)

            shortcut_layout.addStretch()
            shortcuts_layout.addLayout(shortcut_layout)

        layout.addWidget(shortcuts_group)

        # 重置快捷键按钮
        reset_shortcuts_btn = QPushButton("🔄 重置为默认快捷键")
        reset_shortcuts_btn.clicked.connect(self._reset_shortcuts)
        layout.addWidget(reset_shortcuts_btn)

        layout.addStretch()
        self.tab_widget.addTab(tab, "⌨️ 快捷键")

    def _create_backup_tab(self):
        """创建备份设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 自动备份设置
        auto_backup_group = QGroupBox("🔄 自动备份")
        auto_backup_layout = QVBoxLayout(auto_backup_group)

        # 启用自动备份
        self.auto_backup_enabled = QCheckBox("启用自动备份")
        auto_backup_layout.addWidget(self.auto_backup_enabled)

        # 备份间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("备份间隔:"))
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(5, 120)
        self.backup_interval.setValue(30)
        self.backup_interval.setSuffix(" 分钟")
        interval_layout.addWidget(self.backup_interval)
        interval_layout.addStretch()
        auto_backup_layout.addLayout(interval_layout)

        # 最大备份数量
        max_backups_layout = QHBoxLayout()
        max_backups_layout.addWidget(QLabel("最大备份数量:"))
        self.max_backups = QSpinBox()
        self.max_backups.setRange(5, 100)
        self.max_backups.setValue(20)
        max_backups_layout.addWidget(self.max_backups)
        max_backups_layout.addStretch()
        auto_backup_layout.addLayout(max_backups_layout)

        layout.addWidget(auto_backup_group)

        # 版本控制设置
        version_group = QGroupBox("📚 版本控制")
        version_layout = QVBoxLayout(version_group)

        # 启用版本控制
        self.version_control_enabled = QCheckBox("启用文档版本控制")
        version_layout.addWidget(self.version_control_enabled)

        # 最大版本数
        max_versions_layout = QHBoxLayout()
        max_versions_layout.addWidget(QLabel("每个文档最大版本数:"))
        self.max_versions = QSpinBox()
        self.max_versions.setRange(5, 50)
        self.max_versions.setValue(10)
        max_versions_layout.addWidget(self.max_versions)
        max_versions_layout.addStretch()
        version_layout.addLayout(max_versions_layout)

        layout.addWidget(version_group)

        # 备份位置设置
        location_group = QGroupBox("📁 备份位置")
        location_layout = QVBoxLayout(location_group)

        location_path_layout = QHBoxLayout()
        self.backup_path = QLineEdit()
        self.backup_path.setPlaceholderText("选择备份文件夹...")
        location_path_layout.addWidget(self.backup_path)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_backup_folder)
        location_path_layout.addWidget(browse_btn)

        location_layout.addLayout(location_path_layout)
        layout.addWidget(location_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "💾 备份")

    def _reset_shortcuts(self):
        """重置快捷键"""
        QMessageBox.information(self, "提示", "快捷键重置功能开发中...")

    def _browse_backup_folder(self):
        """浏览备份文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择备份文件夹")
        if folder:
            self.backup_path.setText(folder)
    
    def _load_settings(self):
        """加载设置"""
        try:
            # 加载常规设置
            self.default_author_edit.setText(
                self.settings_service.get_setting("project.default_author", "")
            )
            self.target_word_count_spin.setValue(
                self.settings_service.get_setting("project.default_target_word_count", 80000)
            )
            # 加载默认项目类型
            try:
                type_code = str(self.settings_service.get_setting("project.default_project_type", "novel")).lower()
                code_to_label = {"novel": "小说", "essay": "散文", "poetry": "诗歌", "script": "剧本", "other": "其他"}
                self.default_genre_combo.setCurrentText(code_to_label.get(type_code, "小说"))
            except Exception:
                pass
            self.auto_open_last_project_check.setChecked(
                self.settings_service.get_auto_open_last_project()
            )

            # 加载编辑器设置
            self.font_size_spin.setValue(
                self.settings_service.get_setting("ui.font_size", 12)
            )
            self.syntax_highlighting_check.setChecked(
                self.settings_service.get_setting("editor.syntax_highlighting", True)
            )
            
            # 加载主题设置
            theme = self.settings_service.get_setting("ui.theme", "light")
            theme_map = {"light": "浅色主题", "dark": "深色主题", "auto": "自动"}
            self.theme_combo.setCurrentText(theme_map.get(theme, "浅色主题"))
            
            logger.info("设置加载完成")
            
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
    
    def _save_settings(self):
        """保存设置"""
        try:
            # 保存常规设置
            self.settings_service.set_setting(
                "project.default_author",
                self.default_author_edit.text()
            )
            # 保存默认项目类型（中文到代码映射）
            try:
                label = self.default_genre_combo.currentText()
                label_to_code = {"小说": "novel", "散文": "essay", "诗歌": "poetry", "剧本": "script", "其他": "other"}
                self.settings_service.set_setting("project.default_project_type", label_to_code.get(label, "novel"))
            except Exception:
                pass
            self.settings_service.set_setting(
                "project.default_target_word_count",
                self.target_word_count_spin.value()
            )
            self.settings_service.set_auto_open_last_project(
                self.auto_open_last_project_check.isChecked()
            )

            # 保存编辑器设置
            self.settings_service.set_setting(
                "ui.font_size",
                self.font_size_spin.value()
            )
            self.settings_service.set_setting(
                "editor.syntax_highlighting",
                self.syntax_highlighting_check.isChecked()
            )
            
            # 保存主题设置
            theme_map = {"浅色主题": "light", "深色主题": "dark", "自动": "auto"}
            theme = theme_map.get(self.theme_combo.currentText(), "light")
            self.settings_service.set_setting("ui.theme", theme)
            
            logger.info("设置保存完成")
            
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
    
    def _choose_font(self):
        """选择字体"""
        current_font = QFont("Microsoft YaHei UI", 12)
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            self.font_btn.setText(f"{font.family()} {font.pointSize()}pt")
    
    def _preview_theme(self):
        """预览主题"""
        theme_map = {"浅色主题": ThemeType.LIGHT, "深色主题": ThemeType.DARK, "自动": ThemeType.AUTO}
        theme = theme_map.get(self.theme_combo.currentText(), ThemeType.LIGHT)
        self.theme_manager.set_theme(theme)
    
    def _on_theme_changed(self, theme_name: str):
        """主题变化处理"""
        self.theme_changed.emit(theme_name)

    def _open_ai_setup(self):
        """打开AI设置对话框"""
        try:
            from src.presentation.dialogs.ai_setup_dialog import AISetupDialog

            # 获取设置服务
            settings_service = self.settings_service
            settings = getattr(settings_service, 'settings', None) if settings_service else None

            dialog = AISetupDialog(self, settings=settings, settings_service=settings_service)
            dialog.settings_updated.connect(self._on_ai_settings_updated)
            dialog.exec()

        except Exception as e:
            logger.error(f"打开AI设置对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"无法打开AI设置对话框: {e}")

    def _on_ai_settings_updated(self):
        """AI设置更新处理"""
        logger.info("AI设置已更新")
        # 可以在这里添加其他需要的处理逻辑
    
    def _reset_to_defaults(self):
        """重置为默认设置"""
        reply = QMessageBox.question(
            self,
            "重置设置",
            "确定要重置所有设置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_service.reset_to_defaults()
            self._load_settings()
    
    def _export_settings(self):
        """导出设置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出设置",
            "settings.json",
            "JSON文件 (*.json)"
        )
        
        if file_path:
            from pathlib import Path
            success = self.settings_service.export_settings(Path(file_path))
            if success:
                QMessageBox.information(self, "导出成功", "设置已成功导出")
            else:
                QMessageBox.warning(self, "导出失败", "设置导出失败")
    
    def _import_settings(self):
        """导入设置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入设置",
            "",
            "JSON文件 (*.json)"
        )
        
        if file_path:
            from pathlib import Path
            success = self.settings_service.import_settings(Path(file_path))
            if success:
                self._load_settings()
                QMessageBox.information(self, "导入成功", "设置已成功导入")
            else:
                QMessageBox.warning(self, "导入失败", "设置导入失败")
    
    def _apply_settings(self):
        """应用设置"""
        self._save_settings()
    
    def _save_and_close(self):
        """保存并关闭"""
        self._save_settings()
        self.accept()

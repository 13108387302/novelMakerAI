#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理对话框

管理插件的启用、禁用、安装、卸载等操作
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QWidget, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QSplitter, QTextEdit, QCheckBox, QProgressBar,
    QMessageBox, QFileDialog, QFormLayout, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon, QPixmap

from src.shared.plugins.plugin_manager import PluginManager
from src.shared.plugins.plugin_interface import PluginStatus, PluginType
from src.shared.utils.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)


class PluginInstallWorker(QThread):
    """插件安装工作线程"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    installation_completed = pyqtSignal(bool, str)
    
    def __init__(self, plugin_manager: PluginManager, plugin_path: Path):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.plugin_path = plugin_path
    
    def run(self):
        """运行安装"""
        try:
            self.status_updated.emit("正在安装插件...")
            self.progress_updated.emit(25)
            
            # 安装插件
            success = self.plugin_manager.install_plugin(self.plugin_path)
            self.progress_updated.emit(75)
            
            if success:
                self.status_updated.emit("安装完成")
                self.progress_updated.emit(100)
                self.installation_completed.emit(True, "插件安装成功")
            else:
                self.installation_completed.emit(False, "插件安装失败")
                
        except Exception as e:
            self.installation_completed.emit(False, f"安装异常: {e}")


class PluginManagerDialog(QDialog):
    """插件管理对话框"""
    
    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.current_plugin_id = None
        self._setup_ui()
        self._load_plugins()
        
        logger.debug("插件管理对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("🔌 插件管理器")
        self.setModal(True)
        self.resize(800, 600)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：插件列表
        left_widget = self._create_plugin_list()
        splitter.addWidget(left_widget)
        
        # 右侧：插件详情
        right_widget = self._create_plugin_details()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # 按钮区域
        self._create_buttons()
        layout.addLayout(self.buttons_layout)
        
        # 应用样式
        self._apply_styles()
    
    def _create_plugin_list(self) -> QWidget:
        """创建插件列表"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("🔌 已安装插件")
        title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 插件列表
        self.plugin_list = QListWidget()
        self.plugin_list.currentItemChanged.connect(self._on_plugin_selected)
        layout.addWidget(self.plugin_list)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("📥 安装")
        self.install_btn.clicked.connect(self._install_plugin)
        action_layout.addWidget(self.install_btn)
        
        self.uninstall_btn = QPushButton("🗑️ 卸载")
        self.uninstall_btn.clicked.connect(self._uninstall_plugin)
        self.uninstall_btn.setEnabled(False)
        action_layout.addWidget(self.uninstall_btn)
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._load_plugins)
        action_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(action_layout)
        
        return widget
    
    def _create_plugin_details(self) -> QWidget:
        """创建插件详情"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标签页
        self.detail_tabs = QTabWidget()
        
        # 基本信息标签页
        info_tab = self._create_info_tab()
        self.detail_tabs.addTab(info_tab, "ℹ️ 基本信息")
        
        # 设置标签页
        settings_tab = self._create_settings_tab()
        self.detail_tabs.addTab(settings_tab, "⚙️ 设置")
        
        # 日志标签页
        log_tab = self._create_log_tab()
        self.detail_tabs.addTab(log_tab, "📋 日志")
        
        layout.addWidget(self.detail_tabs)
        
        return widget
    
    def _create_info_tab(self) -> QWidget:
        """创建信息标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 插件信息
        info_group = QGroupBox("插件信息")
        info_layout = QFormLayout(info_group)
        
        self.plugin_name_label = QLabel("-")
        self.plugin_name_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        info_layout.addRow("名称:", self.plugin_name_label)
        
        self.plugin_version_label = QLabel("-")
        info_layout.addRow("版本:", self.plugin_version_label)
        
        self.plugin_author_label = QLabel("-")
        info_layout.addRow("作者:", self.plugin_author_label)
        
        self.plugin_type_label = QLabel("-")
        info_layout.addRow("类型:", self.plugin_type_label)
        
        self.plugin_status_label = QLabel("-")
        info_layout.addRow("状态:", self.plugin_status_label)
        
        layout.addWidget(info_group)
        
        # 插件描述
        desc_group = QGroupBox("描述")
        desc_layout = QVBoxLayout(desc_group)
        
        self.plugin_description_text = QTextEdit()
        self.plugin_description_text.setReadOnly(True)
        self.plugin_description_text.setMaximumHeight(100)
        desc_layout.addWidget(self.plugin_description_text)
        
        layout.addWidget(desc_group)
        
        # 控制区域
        control_group = QGroupBox("控制")
        control_layout = QHBoxLayout(control_group)
        
        self.enable_checkbox = QCheckBox("启用插件")
        self.enable_checkbox.stateChanged.connect(self._toggle_plugin)
        control_layout.addWidget(self.enable_checkbox)
        
        control_layout.addStretch()
        
        self.configure_btn = QPushButton("⚙️ 配置")
        self.configure_btn.clicked.connect(self._configure_plugin)
        self.configure_btn.setEnabled(False)
        control_layout.addWidget(self.configure_btn)
        
        layout.addWidget(control_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_settings_tab(self) -> QWidget:
        """创建设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 设置说明
        help_label = QLabel("💡 插件设置将在这里显示")
        help_label.setStyleSheet("font-style: italic; padding: 8px;")
        layout.addWidget(help_label)
        
        # 设置区域
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        layout.addWidget(self.settings_widget)
        
        layout.addStretch()
        
        return tab
    
    def _create_log_tab(self) -> QWidget:
        """创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("插件日志将在这里显示...")
        layout.addWidget(self.log_text)
        
        # 日志控制
        log_control_layout = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("🗑️ 清空日志")
        self.clear_log_btn.clicked.connect(self._clear_log)
        log_control_layout.addWidget(self.clear_log_btn)
        
        log_control_layout.addStretch()
        
        self.export_log_btn = QPushButton("📤 导出日志")
        self.export_log_btn.clicked.connect(self._export_log)
        log_control_layout.addWidget(self.export_log_btn)
        
        layout.addLayout(log_control_layout)
        
        return tab
    
    def _create_buttons(self):
        """创建按钮"""
        self.buttons_layout = QHBoxLayout()
        
        # 全局操作
        self.reload_all_btn = QPushButton("🔄 重新加载所有")
        self.reload_all_btn.clicked.connect(self._reload_all_plugins)
        self.buttons_layout.addWidget(self.reload_all_btn)
        
        self.buttons_layout.addStretch()
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.close_btn)
    
    def _apply_styles(self):
        """应用样式 - 使用主题管理器"""
        try:
            from src.presentation.styles.theme_manager import ThemeManager
            theme_manager = ThemeManager()

            # 应用插件管理器对话框样式
            dialog_style = """
            QDialog {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
            }

            QTreeWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                selection-background-color: #e3f2fd;
                alternate-background-color: #f8f9fa;
            }

            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }

            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }

            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }

            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }

            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }

            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }

            QPushButton:pressed {
                background-color: #e9ecef;
            }

            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border-color: #dee2e6;
            }

            /* 特殊按钮样式 */
            QPushButton[class="primary"] {
                background-color: #007bff;
                color: white;
                border-color: #007bff;
            }

            QPushButton[class="primary"]:hover {
                background-color: #0056b3;
                border-color: #0056b3;
            }

            QPushButton[class="success"] {
                background-color: #28a745;
                color: white;
                border-color: #28a745;
            }

            QPushButton[class="success"]:hover {
                background-color: #1e7e34;
                border-color: #1e7e34;
            }

            QPushButton[class="danger"] {
                background-color: #dc3545;
                color: white;
                border-color: #dc3545;
            }

            QPushButton[class="danger"]:hover {
                background-color: #c82333;
                border-color: #c82333;
            }

            QPushButton[class="warning"] {
                background-color: #ffc107;
                color: #212529;
                border-color: #ffc107;
            }

            QPushButton[class="warning"]:hover {
                background-color: #e0a800;
                border-color: #e0a800;
            }

            QLabel {
                color: #495057;
            }

            QLabel[class="title"] {
                font-size: 14px;
                font-weight: bold;
                color: #212529;
            }

            QLabel[class="subtitle"] {
                font-size: 12px;
                color: #6c757d;
            }

            QSplitter::handle {
                background-color: #dee2e6;
                width: 2px;
                height: 2px;
            }

            QSplitter::handle:hover {
                background-color: #adb5bd;
            }
            """

            self.setStyleSheet(dialog_style)

            # 为特定按钮设置类属性
            if hasattr(self, 'reload_all_btn'):
                self.reload_all_btn.setProperty("class", "primary")

        except Exception as e:
            # 如果主题管理器不可用，使用基本样式
            basic_style = """
            QDialog {
                background-color: #f8f9fa;
            }
            QPushButton {
                padding: 8px 16px;
                min-width: 80px;
            }
            QTreeWidget {
                background-color: white;
                border: 1px solid #ccc;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                padding: 8px;
            }
            """
            self.setStyleSheet(basic_style)

    
    def _load_plugins(self):
        """加载插件列表"""
        try:
            self.plugin_list.clear()
            
            # 获取所有插件
            plugins = self.plugin_manager.get_plugins()
            discovered = self.plugin_manager.discover_plugins()
            
            # 添加已加载的插件
            for plugin_id, plugin in plugins.items():
                self._add_plugin_item(plugin_id, plugin.info, plugin.status)
            
            # 添加未加载的插件
            for plugin_id in discovered:
                if plugin_id not in plugins:
                    status = self.plugin_manager.get_plugin_status(plugin_id)
                    self._add_plugin_item(plugin_id, None, status)
            
            logger.info(f"插件列表加载完成，共 {self.plugin_list.count()} 个插件")
            
        except Exception as e:
            logger.error(f"加载插件列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载插件列表失败: {e}")
    
    def _add_plugin_item(self, plugin_id: str, plugin_info, status: PluginStatus):
        """添加插件项"""
        item = QListWidgetItem()
        
        # 设置显示文本
        if plugin_info:
            display_text = f"{plugin_info.name} ({plugin_info.version})"
        else:
            display_text = plugin_id
        
        # 添加状态图标
        status_icons = {
            PluginStatus.ENABLED: "✅",
            PluginStatus.DISABLED: "⏸️",
            PluginStatus.ERROR: "❌",
            PluginStatus.LOADING: "🔄"
        }
        
        icon = status_icons.get(status, "❓")
        item.setText(f"{icon} {display_text}")
        item.setData(Qt.ItemDataRole.UserRole, plugin_id)
        
        # 设置工具提示
        if plugin_info:
            item.setToolTip(f"{plugin_info.description}\n状态: {status.value}")
        else:
            item.setToolTip(f"插件ID: {plugin_id}\n状态: {status.value}")
        
        self.plugin_list.addItem(item)
    
    def _on_plugin_selected(self, current, previous):
        """插件选择变化"""
        try:
            if not current:
                self._clear_plugin_details()
                return
            
            plugin_id = current.data(Qt.ItemDataRole.UserRole)
            self.current_plugin_id = plugin_id
            
            self._update_plugin_details(plugin_id)
            self.uninstall_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"处理插件选择失败: {e}")
    
    def _update_plugin_details(self, plugin_id: str):
        """更新插件详情"""
        try:
            plugin = self.plugin_manager.get_plugin(plugin_id)
            status = self.plugin_manager.get_plugin_status(plugin_id)
            
            if plugin and plugin.info:
                info = plugin.info
                self.plugin_name_label.setText(info.name)
                self.plugin_version_label.setText(info.version)
                self.plugin_author_label.setText(info.author)
                
                type_names = {
                    PluginType.EDITOR: "编辑器",
                    PluginType.AI_ASSISTANT: "AI助手",
                    PluginType.EXPORT: "导出",
                    PluginType.IMPORT: "导入",
                    PluginType.THEME: "主题",
                    PluginType.TOOL: "工具",
                    PluginType.WIDGET: "组件",
                    PluginType.SERVICE: "服务"
                }
                self.plugin_type_label.setText(type_names.get(info.plugin_type, info.plugin_type.value))
                
                self.plugin_description_text.setPlainText(info.description)
            else:
                self.plugin_name_label.setText(plugin_id)
                self.plugin_version_label.setText("未知")
                self.plugin_author_label.setText("未知")
                self.plugin_type_label.setText("未知")
                self.plugin_description_text.setPlainText("插件信息不可用")
            
            # 更新状态
            status_names = {
                PluginStatus.ENABLED: "✅ 已启用",
                PluginStatus.DISABLED: "⏸️ 已禁用",
                PluginStatus.ERROR: "❌ 错误",
                PluginStatus.LOADING: "🔄 加载中"
            }
            self.plugin_status_label.setText(status_names.get(status, status.value))
            
            # 更新启用复选框
            self.enable_checkbox.blockSignals(True)
            self.enable_checkbox.setChecked(status == PluginStatus.ENABLED)
            self.enable_checkbox.blockSignals(False)
            
            # 更新配置按钮
            self.configure_btn.setEnabled(plugin is not None and status == PluginStatus.ENABLED)
            
        except Exception as e:
            logger.error(f"更新插件详情失败: {e}")
    
    def _clear_plugin_details(self):
        """清空插件详情"""
        self.plugin_name_label.setText("-")
        self.plugin_version_label.setText("-")
        self.plugin_author_label.setText("-")
        self.plugin_type_label.setText("-")
        self.plugin_status_label.setText("-")
        self.plugin_description_text.clear()
        
        self.enable_checkbox.blockSignals(True)
        self.enable_checkbox.setChecked(False)
        self.enable_checkbox.blockSignals(False)
        
        self.configure_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)
    
    def _toggle_plugin(self, state):
        """切换插件状态"""
        try:
            if not self.current_plugin_id:
                return
            
            if state == Qt.CheckState.Checked.value:
                success = self.plugin_manager.enable_plugin(self.current_plugin_id)
                if success:
                    QMessageBox.information(self, "成功", f"插件 {self.current_plugin_id} 已启用")
                else:
                    QMessageBox.warning(self, "失败", f"启用插件 {self.current_plugin_id} 失败")
                    self.enable_checkbox.blockSignals(True)
                    self.enable_checkbox.setChecked(False)
                    self.enable_checkbox.blockSignals(False)
            else:
                success = self.plugin_manager.disable_plugin(self.current_plugin_id)
                if success:
                    QMessageBox.information(self, "成功", f"插件 {self.current_plugin_id} 已禁用")
                else:
                    QMessageBox.warning(self, "失败", f"禁用插件 {self.current_plugin_id} 失败")
                    self.enable_checkbox.blockSignals(True)
                    self.enable_checkbox.setChecked(True)
                    self.enable_checkbox.blockSignals(False)
            
            # 刷新插件列表和详情
            self._load_plugins()
            if self.current_plugin_id:
                self._update_plugin_details(self.current_plugin_id)
            
        except Exception as e:
            logger.error(f"切换插件状态失败: {e}")
            QMessageBox.critical(self, "错误", f"操作失败: {e}")
    
    def _install_plugin(self):
        """安装插件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择插件文件",
                "",
                "插件文件 (*.zip);;所有文件 (*)"
            )
            
            if file_path:
                plugin_path = Path(file_path)
                
                # 创建进度对话框
                progress_dialog = QDialog(self)
                progress_dialog.setWindowTitle("安装插件")
                progress_dialog.setModal(True)
                progress_dialog.resize(300, 100)
                
                layout = QVBoxLayout(progress_dialog)
                
                status_label = QLabel("准备安装...")
                layout.addWidget(status_label)
                
                progress_bar = QProgressBar()
                layout.addWidget(progress_bar)
                
                # 启动安装工作线程
                self.install_worker = PluginInstallWorker(self.plugin_manager, plugin_path)
                self.install_worker.progress_updated.connect(progress_bar.setValue)
                self.install_worker.status_updated.connect(status_label.setText)
                self.install_worker.installation_completed.connect(
                    lambda success, message: self._on_installation_completed(
                        progress_dialog, success, message
                    )
                )
                
                self.install_worker.start()
                progress_dialog.exec()
            
        except Exception as e:
            logger.error(f"安装插件失败: {e}")
            QMessageBox.critical(self, "错误", f"安装插件失败: {e}")
    
    def _on_installation_completed(self, progress_dialog, success: bool, message: str):
        """安装完成处理"""
        progress_dialog.close()
        
        if success:
            QMessageBox.information(self, "安装成功", message)
            self._load_plugins()
        else:
            QMessageBox.critical(self, "安装失败", message)
    
    def _uninstall_plugin(self):
        """卸载插件"""
        try:
            if not self.current_plugin_id:
                return
            
            reply = QMessageBox.question(
                self,
                "确认卸载",
                f"确定要卸载插件 '{self.current_plugin_id}' 吗？\n此操作不可撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.plugin_manager.uninstall_plugin(self.current_plugin_id)
                if success:
                    QMessageBox.information(self, "卸载成功", f"插件 {self.current_plugin_id} 已卸载")
                    self._load_plugins()
                    self._clear_plugin_details()
                else:
                    QMessageBox.warning(self, "卸载失败", f"卸载插件 {self.current_plugin_id} 失败")
            
        except Exception as e:
            logger.error(f"卸载插件失败: {e}")
            QMessageBox.critical(self, "错误", f"卸载插件失败: {e}")
    
    def _configure_plugin(self):
        """配置插件"""
        QMessageBox.information(self, "功能开发中", "插件配置功能正在开发中")
    
    def _reload_all_plugins(self):
        """重新加载所有插件"""
        try:
            reply = QMessageBox.question(
                self,
                "确认重新加载",
                "确定要重新加载所有插件吗？\n这将重启所有插件。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 重新加载插件
                self.plugin_manager.load_all_plugins()
                self._load_plugins()
                QMessageBox.information(self, "完成", "所有插件已重新加载")
            
        except Exception as e:
            logger.error(f"重新加载插件失败: {e}")
            QMessageBox.critical(self, "错误", f"重新加载插件失败: {e}")
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.clear()
    
    def _export_log(self):
        """导出日志"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出插件日志",
                f"plugin_log_{self.current_plugin_id or 'all'}.txt",
                "文本文件 (*.txt)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                
                QMessageBox.information(self, "导出成功", f"日志已导出到: {file_path}")
            
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
            QMessageBox.critical(self, "错误", f"导出日志失败: {e}")

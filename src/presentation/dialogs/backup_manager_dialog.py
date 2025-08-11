#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理对话框

提供项目备份和版本控制的用户界面
"""

from typing import Optional, List
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton,
    QLabel, QGroupBox, QTabWidget, QWidget, QMessageBox, QInputDialog,
    QFileDialog, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from src.application.services.backup_service import BackupService, BackupInfo, VersionInfo
from src.shared.utils.logger import get_logger

from PyQt6.QtCore import QThreadPool, QRunnable, QObject

class _BackupSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

class _BackupTask(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _BackupSignals()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.failed.emit(str(e))

logger = get_logger(__name__)


class BackupManagerDialog(QDialog):
    """备份管理对话框"""

    # 信号定义
    backup_created = pyqtSignal(str)  # backup_id
    backup_restored = pyqtSignal(str)  # project_id
    version_created = pyqtSignal(str)  # version_id

    def __init__(self, backup_service: BackupService, project_id: str = None, parent=None):
        super().__init__(parent)
        self.backup_service = backup_service
        self.project_id = project_id
        self.current_backup: Optional[BackupInfo] = None
        self.current_version: Optional[VersionInfo] = None

        self._setup_ui()
        self._setup_connections()

        # 线程池与防重入控制
        self._thread_pool = QThreadPool.globalInstance()
        self._pending_task = None

        # 加载数据
        self._load_data()

        logger.debug("备份管理对话框初始化完成")

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("备份管理")
        self.setModal(False)
        self.resize(1000, 700)

        # 主布局
        layout = QVBoxLayout(self)

        # 标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 创建标签页
        self._create_backups_tab()
        self._create_versions_tab()
        self._create_settings_tab()

        # 底部按钮
        self._create_buttons()
        layout.addLayout(self.buttons_layout)

    def _create_backups_tab(self):
        """创建备份标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 左侧：备份列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 标题、目录与操作
        header_layout = QVBoxLayout()
        title_row = QHBoxLayout()
        title_label = QLabel("💾 项目备份")
        title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        title_row.addWidget(title_label)
        title_row.addStretch()
        # 创建备份按钮
        self.create_backup_btn = QPushButton("➕ 创建备份")
        self.create_backup_btn.clicked.connect(self._create_backup)
        title_row.addWidget(self.create_backup_btn)
        header_layout.addLayout(title_row)

        # 备份目录展示与打开
        dir_row = QHBoxLayout()
        self.backup_dir_label = QLabel("")
        self.backup_dir_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        open_dir_btn = QPushButton("📂 打开目录")
        open_dir_btn.clicked.connect(self._open_backup_dir)
        dir_row.addWidget(QLabel("目录:"))
        dir_row.addWidget(self.backup_dir_label, 1)
        dir_row.addWidget(open_dir_btn)
        header_layout.addLayout(dir_row)

        left_layout.addLayout(header_layout)

        # 备份列表
        self.backups_list = QListWidget()
        self.backups_list.currentItemChanged.connect(self._on_backup_selected)
        left_layout.addWidget(self.backups_list)

        # 列表操作按钮
        list_buttons_layout = QHBoxLayout()

        self.restore_backup_btn = QPushButton("🔄 恢复备份")
        self.restore_backup_btn.clicked.connect(self._restore_backup)
        self.restore_backup_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.restore_backup_btn)

        self.delete_backup_btn = QPushButton("🗑️ 删除备份")
        self.delete_backup_btn.clicked.connect(self._delete_backup)
        self.delete_backup_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.delete_backup_btn)

        list_buttons_layout.addStretch()

        self.refresh_backups_btn = QPushButton("🔄 刷新")
        self.refresh_backups_btn.clicked.connect(self._load_backups)
        list_buttons_layout.addWidget(self.refresh_backups_btn)

        left_layout.addLayout(list_buttons_layout)

        splitter.addWidget(left_widget)

        # 右侧：备份详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 备份信息
        info_group = QGroupBox("备份信息")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("备份ID:"), 0, 0)
        self.backup_id_label = QLabel("未选择")
        info_layout.addWidget(self.backup_id_label, 0, 1)

        info_layout.addWidget(QLabel("创建时间:"), 1, 0)
        self.backup_time_label = QLabel("未选择")
        info_layout.addWidget(self.backup_time_label, 1, 1)

        info_layout.addWidget(QLabel("备份大小:"), 2, 0)
        self.backup_size_label = QLabel("未选择")
        info_layout.addWidget(self.backup_size_label, 2, 1)

        info_layout.addWidget(QLabel("备份类型:"), 3, 0)
        self.backup_type_label = QLabel("未选择")
        info_layout.addWidget(self.backup_type_label, 3, 1)

        right_layout.addWidget(info_group)

        # 备份描述
        desc_group = QGroupBox("备份描述")
        desc_layout = QVBoxLayout(desc_group)

        self.backup_description = QTextEdit()
        self.backup_description.setMaximumHeight(100)
        self.backup_description.setReadOnly(True)
        desc_layout.addWidget(self.backup_description)

        right_layout.addWidget(desc_group)

        # 备份内容预览
        preview_group = QGroupBox("备份内容")
        preview_layout = QVBoxLayout(preview_group)

        self.backup_content = QTextEdit()
        self.backup_content.setReadOnly(True)
        self.backup_content.setText("选择备份以查看内容...")
        preview_layout.addWidget(self.backup_content)

        right_layout.addWidget(preview_group)

        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([400, 600])

        self.tab_widget.addTab(tab, "💾 项目备份")

    def _create_versions_tab(self):
        """创建版本标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 文档选择
        doc_selection_layout = QHBoxLayout()
        doc_selection_layout.addWidget(QLabel("选择文档:"))

        self.document_combo = QComboBox()
        self.document_combo.currentTextChanged.connect(self._load_document_versions)
        doc_selection_layout.addWidget(self.document_combo)

        doc_selection_layout.addStretch()

        # 创建版本按钮
        self.create_version_btn = QPushButton("📚 创建版本")
        self.create_version_btn.clicked.connect(self._create_version)
        doc_selection_layout.addWidget(self.create_version_btn)

        layout.addLayout(doc_selection_layout)

        # 版本列表
        versions_group = QGroupBox("文档版本")
        versions_layout = QVBoxLayout(versions_group)

        self.versions_list = QListWidget()
        self.versions_list.currentItemChanged.connect(self._on_version_selected)
        versions_layout.addWidget(self.versions_list)

        # 版本操作按钮
        version_buttons_layout = QHBoxLayout()

        self.restore_version_btn = QPushButton("🔄 恢复版本")
        self.restore_version_btn.clicked.connect(self._restore_version)
        self.restore_version_btn.setEnabled(False)
        version_buttons_layout.addWidget(self.restore_version_btn)

        self.compare_version_btn = QPushButton("🔍 版本对比")
        self.compare_version_btn.clicked.connect(self._compare_versions)
        self.compare_version_btn.setEnabled(False)
        version_buttons_layout.addWidget(self.compare_version_btn)

        version_buttons_layout.addStretch()

        versions_layout.addLayout(version_buttons_layout)
        layout.addWidget(versions_group)

        # 版本内容预览
        version_preview_group = QGroupBox("版本内容")
        version_preview_layout = QVBoxLayout(version_preview_group)

        self.version_content = QTextEdit()
        self.version_content.setReadOnly(True)
        self.version_content.setText("选择版本以查看内容...")
        version_preview_layout.addWidget(self.version_content)

        layout.addWidget(version_preview_group)

        self.tab_widget.addTab(tab, "📚 文档版本")

    def _create_settings_tab(self):
        """创建设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 自动备份设置
        auto_backup_group = QGroupBox("自动备份设置")
        auto_backup_layout = QGridLayout(auto_backup_group)

        auto_backup_layout.addWidget(QLabel("备份间隔:"), 0, 0)
        self.backup_interval_label = QLabel("30 分钟")
        auto_backup_layout.addWidget(self.backup_interval_label, 0, 1)

        auto_backup_layout.addWidget(QLabel("最大备份数:"), 1, 0)
        self.max_backups_label = QLabel("50 个")
        auto_backup_layout.addWidget(self.max_backups_label, 1, 1)

        auto_backup_layout.addWidget(QLabel("备份位置:"), 2, 0)
        self.backup_location_label = QLabel("默认位置")
        auto_backup_layout.addWidget(self.backup_location_label, 2, 1)

        layout.addWidget(auto_backup_group)

        # 版本控制设置
        version_control_group = QGroupBox("版本控制设置")
        version_control_layout = QGridLayout(version_control_group)

        version_control_layout.addWidget(QLabel("每文档最大版本数:"), 0, 0)
        self.max_versions_label = QLabel("20 个")
        version_control_layout.addWidget(self.max_versions_label, 0, 1)

        version_control_layout.addWidget(QLabel("版本存储位置:"), 1, 0)
        self.versions_location_label = QLabel("默认位置")
        version_control_layout.addWidget(self.versions_location_label, 1, 1)

        layout.addWidget(version_control_group)

        # 清理操作
        cleanup_group = QGroupBox("清理操作")
        cleanup_layout = QVBoxLayout(cleanup_group)

        cleanup_buttons_layout = QHBoxLayout()

        self.cleanup_old_backups_btn = QPushButton("🧹 清理旧备份")
        self.cleanup_old_backups_btn.clicked.connect(self._cleanup_old_backups)
        cleanup_buttons_layout.addWidget(self.cleanup_old_backups_btn)

        self.cleanup_old_versions_btn = QPushButton("🧹 清理旧版本")
        self.cleanup_old_versions_btn.clicked.connect(self._cleanup_old_versions)
        cleanup_buttons_layout.addWidget(self.cleanup_old_versions_btn)

        cleanup_buttons_layout.addStretch()

        cleanup_layout.addLayout(cleanup_buttons_layout)
        layout.addWidget(cleanup_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "⚙️ 设置")

    def _create_buttons(self):
        """创建按钮"""
        self.buttons_layout = QHBoxLayout()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.buttons_layout.addWidget(self.progress_bar)

        self.buttons_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.close_btn)

    def _setup_connections(self):
        """设置信号连接"""
        pass

    def _open_backup_dir(self):
        try:
            path = str(self.backup_service.backup_dir)
            import os
            os.startfile(path)
        except Exception as e:
            logger.warning(f"打开备份目录失败: {e}")

    def _load_data(self):
        """加载数据"""
        try:
            # 显示备份目录
            self.backup_dir_label.setText(str(self.backup_service.backup_dir))
        except Exception:
            self.backup_dir_label.setText("<unknown>")
        self._load_backups()
        self._load_documents()
        self.progress_bar.setVisible(False)


    def _run_task(self, fn, on_finished, on_failed, *args, **kwargs):
        """在全局线程池中执行耗时任务，完成后在主线程回调。"""
        if getattr(self, "_pending_task", None) is not None:
            return
        task = _BackupTask(fn, *args, **kwargs)
        self._pending_task = task
        task.signals.finished.connect(on_finished)
        task.signals.failed.connect(on_failed)
        def _clear(*_):
            self._pending_task = None
        task.signals.finished.connect(_clear)
        task.signals.failed.connect(_clear)
        self._thread_pool.start(task)

    def _load_backups(self):
        """加载备份列表"""
        try:
            self.backups_list.clear()
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)

            def on_ok(backups):
                try:
                    self.progress_bar.setVisible(False)
                    for backup in backups or []:
                        try:
                            item_text = f"💾 {backup.created_at.strftime('%Y-%m-%d %H:%M')} - {backup.description or '无描述'}"
                            item = QListWidgetItem(item_text)
                            item.setData(Qt.ItemDataRole.UserRole, backup)
                            self.backups_list.addItem(item)
                        except Exception:
                            continue
                except Exception as e:
                    logger.error(f"渲染备份列表失败: {e}")
            def on_fail(msg):
                self.progress_bar.setVisible(False)
                logger.error(f"加载备份列表失败: {msg}")
                QMessageBox.warning(self, "错误", f"加载备份列表失败: {msg}")
            # 在线程池中执行
            self._run_task(lambda: __import__('asyncio').run(self.backup_service.list_backups(self.project_id)), on_ok, on_fail)

        except Exception as e:
            logger.error(f"加载备份列表失败: {e}")
            QMessageBox.warning(self, "错误", f"加载备份列表失败: {str(e)}")

    def _load_documents(self):
        """加载文档列表"""
        try:
            self.document_combo.clear()
            # 这里需要从文档服务获取文档列表
            # documents = await self.document_service.list_by_project(self.project_id)
            # 暂时使用示例数据
            documents = ["第一章", "第二章", "第三章"]

            for doc in documents:
                self.document_combo.addItem(doc)

        except Exception as e:
            logger.error(f"加载文档列表失败: {e}")

    def _load_document_versions(self):
        """加载文档版本"""
        try:
            self.versions_list.clear()
            current_doc = self.document_combo.currentText()
            if not current_doc:
                return

            # 这里需要从备份服务获取文档版本
            # versions = await self.backup_service.list_document_versions(document_id)
            # 暂时使用空列表
            versions = []

            for version in versions:
                item_text = f"📚 v{version.version_number} - {version.created_at.strftime('%Y-%m-%d %H:%M')}"
                if version.description:
                    item_text += f" - {version.description}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, version)
                self.versions_list.addItem(item)

        except Exception as e:
            logger.error(f"加载文档版本失败: {e}")

    def _on_backup_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """备份选择变化"""
        if current:
            backup = current.data(Qt.ItemDataRole.UserRole)
            self.current_backup = backup
            self._update_backup_details(backup)
            self.restore_backup_btn.setEnabled(True)
            self.delete_backup_btn.setEnabled(True)
        else:
            self.current_backup = None
            self._clear_backup_details()
            self.restore_backup_btn.setEnabled(False)
            self.delete_backup_btn.setEnabled(False)

    def _on_version_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """版本选择变化"""
        if current:
            version = current.data(Qt.ItemDataRole.UserRole)
            self.current_version = version
            self._update_version_details(version)
            self.restore_version_btn.setEnabled(True)
            self.compare_version_btn.setEnabled(True)
        else:
            self.current_version = None
            self._clear_version_details()
            self.restore_version_btn.setEnabled(False)
            self.compare_version_btn.setEnabled(False)

    def _update_backup_details(self, backup: BackupInfo):
        """更新备份详情"""
        self.backup_id_label.setText(backup.id)
        self.backup_time_label.setText(backup.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        self.backup_size_label.setText(f"{backup.size / 1024:.1f} KB")
        self.backup_type_label.setText(backup.backup_type)
        self.backup_description.setText(backup.description)
        self.backup_content.setText("备份内容预览功能开发中...")

    def _update_version_details(self, version: VersionInfo):
        """更新版本详情"""
        self.version_content.setText(version.content[:1000] + "..." if len(version.content) > 1000 else version.content)

    def _clear_backup_details(self):
        """清空备份详情"""
        self.backup_id_label.setText("未选择")
        self.backup_time_label.setText("未选择")
        self.backup_size_label.setText("未选择")
        self.backup_type_label.setText("未选择")
        self.backup_description.clear()
        self.backup_content.setText("选择备份以查看内容...")

    def _clear_version_details(self):
        """清空版本详情"""
        self.version_content.setText("选择版本以查看内容...")

    def _create_backup(self):
        """创建备份"""
        description, ok = QInputDialog.getText(self, "创建备份", "备份描述:")
        if ok:
            try:
                # 显示进度
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # 不确定进度

                # 在线程池中执行创建备份
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)
                def on_ok(info):
                    try:
                        self.progress_bar.setVisible(False)
                        # 恢复UI按钮
                        self.restore_backup_btn.setEnabled(True)
                        self.delete_backup_btn.setEnabled(True)
                        self.create_backup_btn.setEnabled(True)
                        if not info:
                            QMessageBox.warning(self, "错误", "创建备份失败（返回空结果）")
                            return
                        # 弹窗提示并刷新列表
                        self._load_backups()
                        QMessageBox.information(self, "成功", f"备份 '{description}' 创建成功！\nID: {getattr(info, 'id', '')}\n目录: {self.backup_service.backup_dir}")
                        # 发出信号（带真实ID）
                        self.backup_created.emit(getattr(info, 'id', ''))
                    except Exception as e:
                        logger.error(f"处理备份创建结果失败: {e}")
                def on_fail(msg):
                    logger.error(f"创建备份失败: {msg}")
                    QMessageBox.warning(self, "错误", f"创建备份失败: {msg}")
                    self.progress_bar.setVisible(False)
                    # 恢复UI按钮
                    self.restore_backup_btn.setEnabled(True)
                    self.delete_backup_btn.setEnabled(True)
                    self.create_backup_btn.setEnabled(True)
                # 执行期间禁用按钮防止并发
                self.restore_backup_btn.setEnabled(False)
                self.delete_backup_btn.setEnabled(False)
                self.create_backup_btn.setEnabled(False)
                self._run_task(lambda: __import__('asyncio').run(self.backup_service.create_backup(self.project_id, description, "manual")), on_ok, on_fail)

            except Exception as e:
                logger.error(f"创建备份失败: {e}")
                QMessageBox.warning(self, "错误", f"创建备份失败: {str(e)}")
                self.progress_bar.setVisible(False)

    def _backup_created_success(self, description: str):
        """备份创建成功"""
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "成功", f"备份 '{description}' 创建成功！")
        self._load_backups()
        self.backup_created.emit("backup_id")

    def _restore_backup(self):
        """恢复备份"""
        if not self.current_backup:
            return

        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要恢复备份 '{self.current_backup.id}' 吗？\n\n当前项目数据将被覆盖！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 在线程池中执行恢复
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)
                def on_ok(project_id):
                    self.progress_bar.setVisible(False)
                    # 恢复UI按钮
                    self.restore_backup_btn.setEnabled(True)
                    self.delete_backup_btn.setEnabled(True)
                    self.create_backup_btn.setEnabled(True)
                    if not project_id:
                        QMessageBox.warning(self, "错误", "备份恢复失败")
                        return
                    # 恢复后刷新列表，提示目录，便于核查
                    self._load_backups()
                    QMessageBox.information(self, "成功", f"备份恢复成功！\n目录: {self.backup_service.backup_dir}")
                    self.backup_restored.emit(project_id)
                def on_fail(msg):
                    self.progress_bar.setVisible(False)
                    # 恢复UI按钮
                    self.restore_backup_btn.setEnabled(True)
                    self.delete_backup_btn.setEnabled(True)
                    self.create_backup_btn.setEnabled(True)
                    logger.error(f"恢复备份失败: {msg}")
                    QMessageBox.warning(self, "错误", f"恢复备份失败: {msg}")
                # 传入目标root_path，确保覆盖当前项目目录
                from src.shared.project_context import ProjectPaths
                from src.shared.ioc.container import get_global_container
                container = get_global_container()
                project_paths = container.try_get(ProjectPaths) if container else None
                target_root = project_paths.root if project_paths else None
                if target_root is None and container:
                    try:
                        from src.application.services.project_service import ProjectService
                        ps = container.try_get(ProjectService)
                        if ps and getattr(ps, 'has_current_project', False) and getattr(ps.current_project, 'root_path', None):
                            target_root = ps.current_project.root_path
                    except Exception:
                        pass
                # 执行期间禁用按钮防止并发
                self.restore_backup_btn.setEnabled(False)
                self.delete_backup_btn.setEnabled(False)
                self.create_backup_btn.setEnabled(False)
                self._run_task(lambda: __import__('asyncio').run(self.backup_service.restore_backup(self.current_backup.backup_path, target_root)), on_ok, on_fail)

            except Exception as e:
                logger.error(f"恢复备份失败: {e}")
                QMessageBox.warning(self, "错误", f"恢复备份失败: {str(e)}")

    def _delete_backup(self):
        """删除备份"""
        if not self.current_backup:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除备份 '{self.current_backup.id}' 吗？\n\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 在线程池中执行删除
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)
                def on_ok(success):
                    self.progress_bar.setVisible(False)
                    # 恢复UI按钮
                    self.restore_backup_btn.setEnabled(True)
                    self.delete_backup_btn.setEnabled(True)
                    self.create_backup_btn.setEnabled(True)
                    if not success:
                        QMessageBox.warning(self, "错误", "删除备份失败")
                        return
                    QMessageBox.information(self, "成功", "备份删除成功！")
                    self._load_backups()
                def on_fail(msg):
                    self.progress_bar.setVisible(False)
                    # 恢复UI按钮
                    self.restore_backup_btn.setEnabled(True)
                    self.delete_backup_btn.setEnabled(True)
                    self.create_backup_btn.setEnabled(True)
                    logger.error(f"删除备份失败: {msg}")
                    QMessageBox.warning(self, "错误", f"删除备份失败: {msg}")
                # 执行期间禁用按钮防止并发
                self.restore_backup_btn.setEnabled(False)
                self.delete_backup_btn.setEnabled(False)
                self.create_backup_btn.setEnabled(False)

                # 删除后刷新列表并校验文件系统是否确实不存在
                def wrapped_delete():
                    import asyncio, os
                    ok = asyncio.run(self.backup_service.delete_backup(self.current_backup.id))
                    try:
                        p = self.current_backup.backup_path
                        still_exists = os.path.exists(str(p))
                        return ok and (not still_exists)
                    except Exception:
                        return ok

                self._run_task(wrapped_delete, on_ok, on_fail)

            except Exception as e:
                logger.error(f"删除备份失败: {e}")
                QMessageBox.warning(self, "错误", f"删除备份失败: {str(e)}")

    def _create_version(self):
        """创建版本"""
        current_doc = self.document_combo.currentText()
        if not current_doc:
            QMessageBox.warning(self, "提示", "请先选择文档")
            return

        description, ok = QInputDialog.getText(self, "创建版本", "版本描述:")
        if ok:
            try:
                # 这里需要调用备份服务创建版本
                # version_info = await self.backup_service.create_document_version(
                #     document_id, content, description
                # )

                QMessageBox.information(self, "成功", f"文档版本创建成功！")
                self._load_document_versions()
                self.version_created.emit("version_id")

            except Exception as e:
                logger.error(f"创建版本失败: {e}")
                QMessageBox.warning(self, "错误", f"创建版本失败: {str(e)}")

    def _restore_version(self):
        """恢复版本"""
        QMessageBox.information(self, "提示", "版本恢复功能开发中...")

    def _compare_versions(self):
        """版本对比"""
        QMessageBox.information(self, "提示", "版本对比功能开发中...")

    def _cleanup_old_backups(self):
        """清理旧备份"""
        QMessageBox.information(self, "提示", "清理旧备份功能开发中...")

    def _cleanup_old_versions(self):
        """清理旧版本"""
        QMessageBox.information(self, "提示", "清理旧版本功能开发中...")

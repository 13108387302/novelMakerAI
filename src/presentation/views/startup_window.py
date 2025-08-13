#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动页面窗口

类似 Visual Studio 的启动页面，提供项目选择和最近项目功能。
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QSizePolicy, QSpacerItem,
    QWidget, QScrollArea, QGridLayout, QMenu, QMessageBox, QLineEdit,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QAction, QDesktopServices, QColor

from src.shared.utils.logger import get_logger
from src.presentation.styles.theme_manager import ThemeManager, ThemeType

logger = get_logger(__name__)


class RecentProjectItem(QWidget):
    """最近项目条目组件"""

    clicked = pyqtSignal(str)  # 发送项目路径
    remove_requested = pyqtSignal(str)  # 请求移除项目
    show_in_explorer_requested = pyqtSignal(str)  # 请求在文件管理器中显示

    def __init__(self, project_path: str, project_name: str, last_opened: str, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.project_name = project_name
        self.last_opened = last_opened

        self._setup_ui()
        self._setup_style()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        # 项目名称
        name_label = QLabel(self.project_name)
        name_font = QFont()
        name_font.setPointSize(12)
        name_font.setBold(True)
        name_font.setFamily("Microsoft YaHei UI")
        name_label.setFont(name_font)
        # 色彩交由全局主题
        layout.addWidget(name_label)

        # 项目路径
        path_label = QLabel(self.project_path)
        path_font = QFont()
        path_font.setPointSize(10)
        path_font.setFamily("Microsoft YaHei UI")
        path_label.setFont(path_font)
        # 色彩交由全局主题
        layout.addWidget(path_label)

        # 最后打开时间
        time_label = QLabel(f"🕒 {self.last_opened}")
        time_font = QFont()
        time_font.setPointSize(9)
        time_font.setFamily("Microsoft YaHei UI")
        time_label.setFont(time_font)
        # 色彩交由全局主题
        layout.addWidget(time_label)

    def _setup_style(self):
        """设置样式"""
        # 移除硬编码样式，使用全局主题 QSS；保留圆角通过属性标记由主题表接管
        self.setProperty("card", True)
        # 设置 objectName 便于主题表精准选择，并启用 hover 反馈
        self.setObjectName("RecentProjectCard")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        except Exception:
            pass

        # 设置固定高度和阴影
        self.setFixedHeight(92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 添加更好的阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_path)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def _show_context_menu(self, position: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)

        # 在文件管理器中显示
        show_action = QAction("📁 在文件管理器中显示", self)
        show_action.triggered.connect(lambda: self.show_in_explorer_requested.emit(self.project_path))
        menu.addAction(show_action)

        menu.addSeparator()

        # 从列表中移除
        remove_action = QAction("🗑️ 从列表中移除", self)
        remove_action.triggered.connect(lambda: self._confirm_remove())
        menu.addAction(remove_action)

        menu.exec(position)

    def _confirm_remove(self):
        """确认移除项目"""
        reply = QMessageBox.question(
            self,
            "确认移除",
            f"确定要从最近项目列表中移除以下项目吗？\n\n{self.project_name}\n{self.project_path}\n\n注意：这不会删除项目文件，只是从列表中移除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.remove_requested.emit(self.project_path)


class StartupWindow(QDialog):
    """启动页面窗口"""

    project_selected = pyqtSignal(str)  # 发送选中的项目路径
    create_new_project = pyqtSignal(dict)  # 请求创建新项目，传递项目信息
    remove_requested = pyqtSignal(str)  # 请求移除项目

    def __init__(self, recent_projects: List[Dict[str, Any]] = None, parent=None, theme_manager: Optional[ThemeManager] = None):
        super().__init__(parent)
        # 复用主程序注入的 ThemeManager，避免不一致
        if theme_manager is not None:
            self.theme_manager = theme_manager
        self.recent_projects = recent_projects or []
        self.selected_project_path: Optional[str] = None
        self.created_project_path: Optional[str] = None
        self._max_recent_to_show: int = 10

        # 尝试从设置读取最近项目显示数量
        try:
            from src.shared.ioc.container import get_global_container
            container = get_global_container()
            if container is not None:
                try:
                    from src.application.services.settings_service import SettingsService
                    ss = container.try_get(SettingsService)
                    if ss is not None:
                        self._max_recent_to_show = int(ss.get_setting("ui.recent_projects_count", 10))
                except Exception:
                    pass
        except Exception:
            pass

        self._setup_ui()
        self._setup_connections()
        self._load_recent_projects()
        self._apply_global_styles()
        # 应用全局主题（与主程序一致）：仅复用主程序注入的 ThemeManager，不再自行解析
        try:
            tm = None
            if hasattr(self, 'theme_manager') and getattr(self, 'theme_manager'):
                tm = getattr(self, 'theme_manager')
            elif parent is not None and hasattr(parent, 'theme_manager'):
                tm = getattr(parent, 'theme_manager')
            if tm is not None:
                # 使用主应用的 ThemeManager，记录有效主题供调试
                current = tm.get_current_theme()
                effective = current
                try:
                    if hasattr(tm, 'get_effective_theme'):
                        effective = tm.get_effective_theme()
                except Exception:
                    pass
                logger.warning(f"[Theme][Startup] Using injected ThemeManager current -> {current}; effective -> {effective}; no reapply")
            else:
                logger.warning("[Theme][Startup] No injected ThemeManager; skip applying theme")
        except Exception as e:
            logger.warning(f"[Theme][Startup] Apply failed: {e}")

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("AI小说编辑器 2.0")
        self.setFixedSize(1000, 680)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 标题区域
        self._create_header_section(main_layout)

        # 内容区域
        self._create_content_section(main_layout)

        # 底部按钮区域
        self._create_footer_section(main_layout)

    def _create_header_section(self, parent_layout):
        """创建标题区域"""
        header_frame = QFrame()
        # 背景由主题 QSS 提供，标记为 hero 区域
        header_frame.setProperty("hero", True)
        header_frame.setFixedHeight(140)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(40, 30, 40, 30)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 应用程序图标和标题的水平布局
        title_container = QHBoxLayout()
        title_container.setSpacing(16)
        title_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 应用程序图标
        icon_label = QLabel("✨")
        icon_font = QFont()
        icon_font.setPointSize(32)
        icon_label.setFont(icon_font)
        # 颜色跟随主题
        title_container.addWidget(icon_label)

        # 标题和版本的垂直布局
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        # 应用程序标题
        title_label = QLabel("AI小说编辑器")
        title_label.setProperty("title", True)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_font.setFamily("Microsoft YaHei UI")
        title_label.setFont(title_font)
        # 颜色跟随主题
        text_layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel("版本 2.0.0 · 现代化架构")
        version_label.setProperty("version", True)
        version_font = QFont()
        version_font.setPointSize(12)
        version_font.setFamily("Microsoft YaHei UI")
        version_label.setFont(version_font)
        # 次要说明文字，颜色由 [hero][secondary] 规则控制
        version_label.setProperty("secondary", True)
        text_layout.addWidget(version_label)

        title_container.addLayout(text_layout)
        header_layout.addLayout(title_container)

        parent_layout.addWidget(header_frame)

    def _create_content_section(self, parent_layout):
        """创建内容区域"""
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 32, 32, 24)
        content_layout.setSpacing(32)

        # 左侧：最近项目
        self._create_recent_projects_section(content_layout)

        # 右侧：快速操作
        self._create_actions_section(content_layout)

        parent_layout.addWidget(content_widget)

    def _create_recent_projects_section(self, parent_layout):
        """创建最近项目区域"""
        recent_frame = QFrame()
        recent_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        # 由主题提供卡片样式
        recent_frame.setProperty("card", True)
        # 更深的卡片阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 12)
        recent_frame.setGraphicsEffect(shadow)

        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(24, 20, 24, 16)

        # 标题区域
        title_container = QHBoxLayout()
        title_container.setSpacing(12)

        # 标题图标
        title_icon = QLabel("📚")
        title_icon_font = QFont()
        title_icon_font.setPointSize(16)
        title_icon.setFont(title_icon_font)
        title_container.addWidget(title_icon)

        # 标题
        recent_title = QLabel("最近的项目")
        recent_title_font = QFont()
        recent_title_font.setPointSize(16)
        recent_title_font.setBold(True)
        recent_title_font.setFamily("Microsoft YaHei UI")
        recent_title.setFont(recent_title_font)
        # 颜色跟随主题
        title_container.addWidget(recent_title)

        title_container.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        recent_layout.addLayout(title_container)

        # 搜索框
        search_box = QLineEdit()
        search_box.setPlaceholderText("🔍 搜索项目名称或路径...")
        search_box.setClearButtonEnabled(True)
        # 输入框样式由主题统一控制
        search_box.textChanged.connect(self._on_search_changed)
        recent_layout.addWidget(search_box)

        # 项目列表滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 滚动区域样式由主题统一控制

        # 项目列表容器
        self.projects_container = QWidget()
        # 背景由主题控制
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setContentsMargins(0, 12, 0, 12)
        self.projects_layout.setSpacing(8)

        scroll_area.setWidget(self.projects_container)
        recent_layout.addWidget(scroll_area)

        # 设置大小
        recent_frame.setMinimumWidth(520)
        parent_layout.addWidget(recent_frame, 2)

    def _create_actions_section(self, parent_layout):
        """创建操作区域"""
        actions_frame = QFrame()
        actions_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        # 由主题提供卡片样式
        actions_frame.setProperty("card", True)
        shadow2 = QGraphicsDropShadowEffect(self)
        shadow2.setColor(QColor(0, 0, 0, 60))
        shadow2.setBlurRadius(32)
        shadow2.setOffset(0, 12)
        actions_frame.setGraphicsEffect(shadow2)

        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(24, 20, 24, 20)
        actions_layout.setSpacing(24)

        # 标题区域
        title_container = QHBoxLayout()
        title_container.setSpacing(12)

        # 标题图标
        title_icon = QLabel("🚀")
        title_icon_font = QFont()
        title_icon_font.setPointSize(16)
        title_icon.setFont(title_icon_font)
        title_container.addWidget(title_icon)

        # 标题
        actions_title = QLabel("开始创作")
        actions_title_font = QFont()
        actions_title_font.setPointSize(16)
        actions_title_font.setBold(True)
        actions_title_font.setFamily("Microsoft YaHei UI")
        actions_title.setFont(actions_title_font)
        # 颜色跟随主题
        title_container.addWidget(actions_title)

        title_container.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        actions_layout.addLayout(title_container)

        # 打开项目文件夹按钮
        self.open_folder_btn = QPushButton("📁  打开项目文件夹")
        self.open_folder_btn.setMinimumHeight(56)
        # 使用强调按钮样式+炫酷胶囊+fancy
        self.open_folder_btn.setProperty("accent", True)
        self.open_folder_btn.setProperty("fancy", True)
        self.open_folder_btn.setStyleSheet("")
        actions_layout.addWidget(self.open_folder_btn)

        # 创建新项目按钮
        self.create_project_btn = QPushButton("✨  创建新项目")
        self.create_project_btn.setMinimumHeight(56)
        self.create_project_btn.setProperty("accent", True)
        self.create_project_btn.setProperty("fancy", True)
        self.create_project_btn.setStyleSheet("")
        actions_layout.addWidget(self.create_project_btn)

        # 添加弹性空间
        actions_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # 设置大小
        actions_frame.setMinimumWidth(280)
        actions_frame.setMaximumWidth(320)
        parent_layout.addWidget(actions_frame, 1)

    def _create_footer_section(self, parent_layout):
        """创建底部区域"""
        footer_frame = QFrame()
        # 由主题提供页脚背景
        footer_frame.setFixedHeight(72)

        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(40, 20, 40, 20)

        # 左侧信息
        info_label = QLabel("💡 选择一个项目文件夹开始创作，或创建全新的小说项目")
        # 文本颜色交给主题
        footer_layout.addWidget(info_label)

        # 右侧退出按钮
        footer_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        exit_btn = QPushButton("退出")
        exit_btn.setMinimumHeight(32)
        exit_btn.setMinimumWidth(80)
        # 按钮样式交给主题
        exit_btn.clicked.connect(self.reject)
        footer_layout.addWidget(exit_btn)

        parent_layout.addWidget(footer_frame)

    def _apply_global_styles(self):
        """交由 ThemeManager 统一样式，移除本地硬编码样式"""
        # 旧版在此叠加浅色渐变背景，导致深色/自动主题不一致
        # 这里改为不做任何操作，具体样式由 ThemeManager 的全局 QSS 控制
        return

    def _on_search_changed(self, text: str):
        """根据搜索关键字过滤最近项目"""
        keyword = (text or "").strip().lower()
        # 清空并重建最近项目列表（包括空白项）
        self._clear_projects_layout()
        matched = []
        if keyword:
            for project in self.recent_projects:
                if keyword in project['name'].lower() or keyword in project['path'].lower():
                    matched.append(project)
        else:
            matched = self.recent_projects
        if not matched:
            # 搜索无结果的空状态
            empty_container = QWidget()
            # 外观由主题控制
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(16)
            empty_layout.setContentsMargins(40, 40, 40, 40)

            # 搜索无结果图标
            empty_icon = QLabel("🔍")
            empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_icon_font = QFont()
            empty_icon_font.setPointSize(48)
            empty_icon.setFont(empty_icon_font)
            # 颜色交由主题
            empty_layout.addWidget(empty_icon)

            # 无结果文字
            empty_label = QLabel("未找到匹配的项目")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 文本外观由主题控制
            empty_layout.addWidget(empty_label)

            # 搜索提示
            hint_label = QLabel("尝试使用不同的关键词搜索")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 文本外观由主题控制
            empty_layout.addWidget(hint_label)

            self.projects_layout.addWidget(empty_container)
        else:
            for project in matched:
                item = RecentProjectItem(project['path'], project['name'], project['last_opened'])
                item.clicked.connect(self._on_project_selected)
                item.remove_requested.connect(self._on_remove_project)
                item.show_in_explorer_requested.connect(self._on_show_in_explorer)
                self.projects_layout.addWidget(item)
        self.projects_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def _setup_connections(self):
        """设置信号连接"""
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        self.create_project_btn.clicked.connect(self._on_create_project)

    def _clear_projects_layout(self):
        """彻底清空项目列表布局（移除所有小部件和弹性空白项）"""
        try:
            if not hasattr(self, 'projects_layout') or self.projects_layout is None:
                return
            layout = self.projects_layout
            # 逐个取出并删除，确保QSpacerItem也被移除
            while layout.count():
                item = layout.takeAt(0)
                if item is None:
                    continue
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
                # 非widget项（如QSpacerItem）由GC处理
        except Exception as e:
            logger.warning(f"清空项目列表布局失败: {e}")

    def _load_recent_projects(self):
        """加载最近项目列表"""
        # 清空现有项目（包括空白项）
        self._clear_projects_layout()

        if not self.recent_projects:
            # 显示空状态
            empty_container = QWidget()
            # 外观由主题控制
            empty_layout = QVBoxLayout(empty_container)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(20)
            empty_layout.setContentsMargins(40, 60, 40, 60)

            # 空状态图标
            empty_icon = QLabel("📚")
            empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_icon_font = QFont()
            empty_icon_font.setPointSize(64)
            empty_icon.setFont(empty_icon_font)
            # 颜色交由主题
            empty_layout.addWidget(empty_icon)

            # 空状态文字
            empty_label = QLabel("暂无最近项目")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 文本外观由主题控制
            empty_layout.addWidget(empty_label)

            # 提示文字
            hint_label = QLabel("创建新项目或打开现有项目文件夹开始使用")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # 文本外观由主题控制
            empty_layout.addWidget(hint_label)

            self.projects_layout.addWidget(empty_container)
        else:
            # 添加最近项目
            # 仅显示部分最近项目
            to_show = self.recent_projects[: max(0, int(self._max_recent_to_show))]
            for project in to_show:
                item = RecentProjectItem(
                    project['path'],
                    project['name'],
                    project['last_opened']
                )
                item.clicked.connect(self._on_project_selected)
                item.remove_requested.connect(self._on_remove_project)
                item.show_in_explorer_requested.connect(self._on_show_in_explorer)
                self.projects_layout.addWidget(item)

        # 添加弹性空间
        self.projects_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def _on_open_folder(self):
        """打开文件夹按钮点击"""
        from PyQt6.QtWidgets import QFileDialog

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择项目文件夹",
            str(Path.cwd()),
            QFileDialog.Option.ShowDirsOnly
        )

        if folder_path:
            self.selected_project_path = folder_path
            self.project_selected.emit(folder_path)
            self.accept()

    def _on_create_project(self):
        """创建新项目按钮点击"""
        try:
            from src.presentation.dialogs.project_wizard import ProjectWizard

            # 创建项目向导
            wizard = ProjectWizard(self)
            wizard.project_created.connect(self._on_project_wizard_completed)

            # 显示向导
            result = wizard.exec()
            if result == wizard.DialogCode.Accepted:
                logger.info("项目创建向导完成")
            else:
                logger.info("用户取消项目创建")

        except Exception as e:
            logger.error(f"显示项目创建向导失败: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "创建项目失败",
                f"无法显示项目创建向导：\n{e}\n\n请使用'打开项目文件夹'功能选择一个空文件夹来创建项目。"
            )

    def _on_project_wizard_completed(self, project_info: dict):
        """项目向导完成回调（不在此处创建项目，交由外层统一处理）"""
        try:
            # 交由外层（main_app 或 主控制器）统一通过服务创建
            self.create_new_project.emit(project_info)
            # 不要立即关闭启动页面，等待项目创建完成后由回调关闭
            logger.info(f"项目创建请求已提交: {project_info.get('name', '未知')}")
        except Exception as e:
            logger.error(f"处理项目向导完成失败: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "项目创建失败",
                f"处理项目创建结果时出错：\n{e}"
            )

    def _create_project_from_wizard(self, project_info: dict) -> Optional[Path]:
        """已废弃：不再在此处创建项目，统一交由外层服务处理"""
        logger.warning("_create_project_from_wizard 已废弃，使用 create_new_project 信号交由外层处理")
        return None

    def _on_project_selected(self, project_path: str):
        """项目被选中"""
        # 验证项目路径是否仍然存在
        if not Path(project_path).exists():
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "项目不存在",
                f"项目文件夹不存在：\n{project_path}\n\n是否从最近项目列表中移除？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 发送移除请求
                self.remove_requested.emit(project_path)
                # 重新加载项目列表
                self._load_recent_projects()
            return

        self.selected_project_path = project_path
        self.project_selected.emit(project_path)
        self.accept()

    def _on_remove_project(self, project_path: str):
        """移除项目"""
        # 从本地列表中移除
        self.recent_projects = [p for p in self.recent_projects if p['path'] != project_path]
        # 重新加载UI
        self._load_recent_projects()
        # 通知外部移除
        self.remove_requested.emit(project_path)

    def _on_show_in_explorer(self, project_path: str):
        """在文件管理器中显示项目"""
        try:
            from PyQt6.QtCore import QUrl
            project_url = QUrl.fromLocalFile(project_path)
            QDesktopServices.openUrl(project_url)
        except Exception as e:
            logger.error(f"打开文件管理器失败: {e}")
            QMessageBox.warning(
                self,
                "打开失败",
                f"无法在文件管理器中显示项目：\n{project_path}\n\n错误：{e}"
            )

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # 如果有最近项目，选择第一个
            if self.recent_projects:
                first_project = self.recent_projects[0]
                self._on_project_selected(first_project['path'])
        super().keyPressEvent(event)

    def update_recent_projects(self, projects: List[Dict[str, Any]]):
        """更新最近项目列表"""
        self.recent_projects = projects
        self._load_recent_projects()

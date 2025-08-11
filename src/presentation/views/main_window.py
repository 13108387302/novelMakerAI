#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 - 重构版本

应用程序的主界面框架，使用模块化的UI构建器
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMessageBox, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QByteArray
from PyQt6.QtGui import QKeySequence, QFont

from src.presentation.controllers.main_controller import MainController
from src.presentation.widgets.project_tree import ProjectTreeWidget
from src.presentation.widgets.editor import EditorWidget
# 使用新的AI组件架构
from PyQt6.QtWidgets import QLabel

class EnhancedDocumentAIPanel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__("文档AI面板 - 重构中")
from src.presentation.widgets.status_panel import StatusPanelWidget
from src.application.services.status_service import StatusService
from src.presentation.shortcuts.shortcut_manager import ShortcutManager

# UI构建器
from .ui_builders import MenuBuilder, ToolBarBuilder, StatusBarBuilder, DockBuilder

from src.shared.utils.logger import get_logger
from src.shared.constants import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    DEFAULT_STATUS_TIMEOUT, UI_UPDATE_DELAY_MS, DOCUMENT_LOAD_DELAY_MS
)

logger = get_logger(__name__)

# 主窗口常量
WINDOW_TITLE = "AI小说编辑器 2.0"
DEFAULT_THEME = "light"
EDITOR_PLACEHOLDER = "编辑器暂不可用"
AI_PANEL_HINT = "📝 文档AI助手"
AI_PANEL_INFO = "请先打开一个文档\n文档AI助手将为您提供：\n\n🧠 智能续写建议\n💡 写作指导\n🎨 内容优化\n📊 文档分析"
AI_PANEL_UNAVAILABLE = "AI面板创建失败"
DOCUMENT_AI_UNAVAILABLE = "文档AI面板不可用"

# 样式常量
HINT_LABEL_STYLE = "color: #2196F3; padding: 10px;"
INFO_LABEL_STYLE = """
    QLabel {
        color: #666;
        font-size: 14px;
        line-height: 1.5;
        padding: 20px;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        margin: 10px;
    }
"""

# 快捷键映射
SHORTCUT_MAPPINGS = {
    "Ctrl+N": "new_project",
    "Ctrl+O": "open_project",
    "Ctrl+S": "save",
    "Ctrl+Q": "exit",
    "F1": "show_shortcuts",
    "F11": "toggle_fullscreen",
    "F4": "show_ai_panel",
}


class MainWindow(QMainWindow):
    """
    主窗口 - 重构版本

    应用程序的主界面框架，使用模块化的UI构建器架构。
    提供完整的用户界面，包括菜单、工具栏、编辑器和各种面板。

    实现方式：
    - 使用模块化的UI构建器分离界面构建逻辑
    - 采用停靠窗口提供灵活的界面布局
    - 集成快捷键管理器提供键盘操作
    - 使用信号槽机制处理用户交互
    - 提供完整的窗口状态管理

    Attributes:
        controller: 主控制器实例
        menu_builder: 菜单构建器
        toolbar_builder: 工具栏构建器
        statusbar_builder: 状态栏构建器
        dock_builder: 停靠窗口构建器
        shortcut_manager: 快捷键管理器

    Signals:
        window_closing: 窗口关闭信号
        project_requested: 请求打开项目信号
        document_requested: 请求打开文档信号
    """

    # 信号定义
    window_closing = pyqtSignal()
    project_requested = pyqtSignal(str)  # 请求打开项目
    document_requested = pyqtSignal(str)  # 请求打开文档

    def __init__(self, controller: MainController):
        """
        初始化主窗口

        Args:
            controller: 主控制器实例
        """
        super().__init__()
        self.controller = controller

        # UI构建器
        self.menu_builder = MenuBuilder(self)
        self.toolbar_builder = ToolBarBuilder(self)
        self.statusbar_builder = StatusBarBuilder(self)
        self.dock_builder = DockBuilder(self)

        # 快捷键管理器
        self.shortcut_manager = ShortcutManager(self)

        # UI组件
        self.project_tree = None
        self.editor_widget = None
        # 旧的全局 AI 面板已废弃，使用 AI Studio 页面
        self.status_panel = None
        self.document_ai_panel = None

        # 视图注册表
        self.view_registry = {}
        self.dock_registry = {}

        # 初始化
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        self._restore_window_state()

        logger.info("主窗口初始化完成")

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        # 创建UI组件
        self._create_widgets()
        self._create_central_widget()
        self._create_menu_bar()
        self._create_toolbars()
        self._create_status_bar()
        self._create_dock_widgets()

        # 应用样式
        self._apply_styles()

    def _create_widgets(self):
        """创建UI组件"""
        # 项目树
        self.project_tree = ProjectTreeWidget()

        # 编辑器
        if self.controller:
            # 获取AI助手管理器
            ai_assistant_manager = getattr(self.controller, 'ai_assistant_manager', None)
            self.editor_widget = EditorWidget(ai_assistant_manager)
        else:
            from PyQt6.QtWidgets import QTextEdit
            self.editor_widget = QTextEdit()
            self.editor_widget.setPlaceholderText(EDITOR_PLACEHOLDER)

        # 使用全新的 AI Studio 页面替换旧面板
        from src.presentation.views.ai_studio_page import AIStudioPage
        self.ai_studio = AIStudioPage(self, settings_service=getattr(self.controller, 'settings_service', None))

        # 状态服务和状态面板
        self.status_service = StatusService()
        self.status_panel = StatusPanelWidget(self.status_service)

    # 旧的文档AI面板容器已废弃
    def _create_central_widget(self):
        """创建中央组件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 主分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # 添加编辑器到中央区域
        main_splitter.addWidget(self.editor_widget)

        # 添加 AI Studio 到右侧
        try:
            if not hasattr(self, 'ai_studio'):
                from src.presentation.views.ai_studio_page import AIStudioPage
                self.ai_studio = AIStudioPage(self, settings_service=getattr(self.controller, 'settings_service', None))
            main_splitter.addWidget(self.ai_studio)
            # 设置分割器比例：编辑器:AI=3:2
            main_splitter.setStretchFactor(0, 3)
            main_splitter.setStretchFactor(1, 2)
        except Exception as e:
            logger.error(f"加载 AI Studio 失败: {e}")

        # 保存引用
        self.main_splitter = main_splitter

    def _create_menu_bar(self):
        """创建菜单栏"""
        self.menu_builder.build_menu_bar(self)

    def _create_toolbars(self):
        """创建工具栏"""
        # 主工具栏（简化版，AI功能通过AI面板访问）
        self.toolbar_builder.build_main_toolbar(self)

    def _create_status_bar(self):
        """创建状态栏"""
        self.statusbar_builder.build_status_bar(self)

    def _create_dock_widgets(self):
        """创建停靠窗口"""
        # 项目停靠窗口
        self.dock_builder.create_project_dock(self, self.project_tree)

        # 右侧标签页 Dock 已移除：AI Studio 位于中央主分割器右侧
        # 状态停靠窗口（独立，但在右侧）
        self.dock_builder.create_status_dock(self, self.status_panel)

        # 输出停靠窗口
        self.dock_builder.create_output_dock(self)

        # AI 控制台（底部，默认隐藏）
        self.dock_builder.create_ai_console_dock(self)

        # 设置停靠窗口大小
        QTimer.singleShot(100, lambda: self.dock_builder.set_dock_sizes(self))

    def _apply_styles(self):
        """应用样式"""
        try:
            from src.presentation.styles.theme_manager import ThemeManager
            theme_manager = ThemeManager()
            theme_manager.apply_theme(DEFAULT_THEME)
        except Exception as e:
            logger.warning(f"应用主题失败: {e}")

    def _setup_connections(self):
        """设置信号连接"""
        # 菜单动作连接
        self.menu_builder.action_triggered.connect(self._handle_menu_action)

        # 工具栏动作连接
        self.toolbar_builder.action_triggered.connect(self._handle_toolbar_action)

        # 停靠窗口可见性变化
        self.dock_builder.dock_visibility_changed.connect(self._handle_dock_visibility_changed)
        # 将 AI Studio 信号接入 AI 控制台（若存在）
        try:
            if hasattr(self, 'ai_studio') and hasattr(self, 'ai_console') and self.ai_studio and self.ai_console:
                self.ai_console.connect_ai_widget(self.ai_studio)
        except Exception as e:
            logger.warning(f"连接 AI 控制台失败: {e}")


        # 项目树信号
        if self.controller and hasattr(self.project_tree, 'document_selected'):
            self.project_tree.document_selected.connect(self.controller.open_document)
        if self.controller and hasattr(self.project_tree, 'project_selected'):
            self.project_tree.project_selected.connect(self.controller.open_project)
        if self.controller and hasattr(self.project_tree, 'document_create_requested'):
            self.project_tree.document_create_requested.connect(self.controller.create_document_from_tree)
        if self.controller and hasattr(self.project_tree, 'document_delete_requested'):
            self.project_tree.document_delete_requested.connect(self.controller.delete_document)
        if self.controller and hasattr(self.project_tree, 'document_rename_requested'):
            self.project_tree.document_rename_requested.connect(self.controller.rename_document)
        if self.controller and hasattr(self.project_tree, 'document_copy_requested'):
            self.project_tree.document_copy_requested.connect(self.controller.copy_document)

        # 编辑器信号
        if hasattr(self.editor_widget, 'content_changed'):
            self.editor_widget.content_changed.connect(self._update_word_count)
            self.editor_widget.content_changed.connect(self._on_content_changed)
        if hasattr(self.editor_widget, 'cursor_position_changed'):
            self.editor_widget.cursor_position_changed.connect(self._update_cursor_position)
        if hasattr(self.editor_widget, 'selection_changed'):
            self.editor_widget.selection_changed.connect(self._on_selection_changed)
        if hasattr(self.editor_widget, 'document_switched'):
            self.editor_widget.document_switched.connect(self._on_document_switched)
        if hasattr(self.editor_widget, 'save_requested'):
            self.editor_widget.save_requested.connect(self.controller.save_document)

        # AI Studio 信号
        if hasattr(self, 'ai_studio'):
            if hasattr(self.ai_studio, 'text_applied'):
                self.ai_studio.text_applied.connect(self._on_ai_text_applied)
            if hasattr(self.ai_studio, 'status_changed'):
                self.ai_studio.status_changed.connect(lambda msg, typ: self._on_ai_status_updated(msg))
            if hasattr(self.ai_studio, 'text_insert_requested'):
                self.ai_studio.text_insert_requested.connect(self._on_ai_text_insert)
            if hasattr(self.ai_studio, 'text_replace_requested'):
                self.ai_studio.text_replace_requested.connect(self._on_ai_text_replace)

        # 控制器信号
        if self.controller:
            if hasattr(self.controller, 'project_opened'):
                self.controller.project_opened.connect(self._on_project_opened)
            if hasattr(self.controller, 'document_opened'):
                self.controller.document_opened.connect(self._on_document_opened_event)
            if hasattr(self.controller, 'status_message'):
                self.controller.status_message.connect(self._on_status_message)
            if hasattr(self.controller, 'project_tree_refresh_requested'):
                self.controller.project_tree_refresh_requested.connect(self._refresh_project_tree)

    def _setup_shortcuts(self):
        """设置快捷键"""
        try:
            # 基本快捷键
            shortcuts = {
                sequence: lambda action=action: self._handle_menu_action(action, None)
                for sequence, action in SHORTCUT_MAPPINGS.items()
            }

            # 导入快捷键类别
            from src.presentation.shortcuts.shortcut_manager import ShortcutCategory

            for sequence, callback in shortcuts.items():
                # 生成快捷键名称
                key = sequence.replace("+", "_").replace("Ctrl", "ctrl").replace("Shift", "shift").lower()
                description = f"快捷键 {sequence}"
                self.shortcut_manager.register_shortcut(
                    key=key,
                    sequence=sequence,
                    description=description,
                    category=ShortcutCategory.GENERAL,
                    action=callback
                )

            # AI 控制台与动作面板快捷键
            try:
                from src.presentation.shortcuts.shortcut_manager import ShortcutCategory
                self.shortcut_manager.register_shortcut(
                    key="toggle_ai_console",
                    sequence="F6",
                    description="切换 AI 控制台",
                    category=ShortcutCategory.GENERAL,
                    action=lambda: self.dock_builder.toggle_dock("ai_console")
                )
                self.shortcut_manager.register_shortcut(
                    key="ai_action_palette",
                    sequence="Alt+Enter",
                    description="打开 AI 动作面板",
                    category=ShortcutCategory.GENERAL,
                    action=self._open_ai_action_palette
                )
            except Exception as e:
                logger.warning(f"注册 AI 快捷键失败: {e}")

        except Exception as e:
            logger.error(f"设置快捷键失败: {e}")

    def _restore_window_state(self):
        """恢复窗口状态"""
        try:
            # 从设置服务恢复窗口状态
            settings = self.controller.settings_service

            # 恢复窗口几何
            geometry = settings.get_window_geometry()
            if geometry:
                try:
                    # 尝试从base64字符串恢复
                    if isinstance(geometry, str):
                        geometry_bytes = QByteArray.fromBase64(geometry.encode())
                    else:
                        geometry_bytes = QByteArray(geometry)
                    self.restoreGeometry(geometry_bytes)
                except Exception as e:
                    logger.warning(f"恢复窗口几何失败: {e}")

            # 恢复停靠窗口状态
            dock_state = settings.get_dock_state()
            if dock_state:
                try:
                    if isinstance(dock_state, str):
                        state_bytes = QByteArray.fromBase64(dock_state.encode())
                    else:
                        state_bytes = QByteArray(dock_state)
                    self.dock_builder.restore_dock_state(self, state_bytes)
                except Exception as e:
                    logger.warning(f"恢复停靠窗口状态失败: {e}")

        except Exception as e:
            logger.warning(f"恢复窗口状态失败: {e}")

    def _handle_menu_action(self, action_name: str, action):
        """处理菜单动作"""
        try:
            logger.debug(f"🎯 处理菜单动作: {action_name}")

            # 文件菜单
            if action_name == "new_project":
                self.controller.new_project()
            elif action_name == "open_project":
                self.controller.open_project()
            elif action_name == "close_project":
                self.controller.close_current_project()
            elif action_name == "save":
                logger.info("💾 Ctrl+S 快捷键触发保存动作")
                self.controller.save_current_document()
            elif action_name == "save_as":
                self.controller.save_as()
            elif action_name == "import_project":
                self.controller.import_project()
            elif action_name == "export_project":
                self.controller.export_project()
            elif action_name == "exit":
                self.close()

            # 编辑菜单
            elif action_name == "undo":
                self.controller.undo()
            elif action_name == "redo":
                self.controller.redo()
            elif action_name == "cut":
                self.controller.cut()
            elif action_name == "copy":
                self.controller.copy()
            elif action_name == "paste":
                self.controller.paste()
            elif action_name == "find":
                self.controller.find()
            elif action_name == "replace":
                self.controller.replace()

            # 视图菜单
            elif action_name == "toggle_syntax_highlighting":
                self.controller.toggle_syntax_highlighting()
            elif action_name == "toggle_fullscreen":
                self._toggle_fullscreen()
            elif action_name == "toggle_project_tree":
                self.dock_builder.toggle_dock("project")
            elif action_name == "toggle_ai_panel":
                self._toggle_ai_studio()
            elif action_name == "toggle_status_panel":
                self.dock_builder.toggle_dock("status")

            # AI菜单（简化版）
            elif action_name == "show_ai_panel":
                self._show_ai_panel()
            elif action_name == "ai_setup":
                self._show_ai_setup()
            elif action_name == "toggle_ai_console":
                # 切换 AI 控制台
                self.dock_builder.toggle_dock("ai_console")
            elif action_name == "toggle_output_panel":
                # 切换 输出面板
                self.dock_builder.toggle_dock("output")

            # 工具菜单
            elif action_name == "word_count":
                self.controller.show_word_count()
            elif action_name == "backup_management":
                self.controller.backup_management()
            elif action_name == "settings":
                self.controller.settings()
            elif action_name == "new_document":
                logger.info("🔧 触发新建文档动作")
                self.controller.new_document()

            # 帮助菜单
            elif action_name == "show_shortcuts":
                self._show_shortcuts_help()
            elif action_name == "about":
                self.controller.about()

            else:
                logger.warning(f"未处理的菜单动作: {action_name}")

        except Exception as e:
            logger.error(f"处理菜单动作失败 {action_name}: {e}")

    def _toggle_ai_studio(self):
        try:
            if not hasattr(self, 'ai_studio') or not self.ai_studio:
                return
            visible = self.ai_studio.isVisible()
            self.ai_studio.setVisible(not visible)
            # 调整分割比例
            if not visible:
                if hasattr(self, 'main_splitter'):
                    self.main_splitter.setStretchFactor(0, 3)
                    self.main_splitter.setStretchFactor(1, 2)
            else:
                if hasattr(self, 'main_splitter'):
                    self.main_splitter.setStretchFactor(0, 1)
                    self.main_splitter.setStretchFactor(1, 0)
        except Exception as e:
            logger.warning(f"切换 AI Studio 可见性失败: {e}")

    def _handle_toolbar_action(self, action_name: str, action_data):
        """处理工具栏动作"""
        # 大部分工具栏动作与菜单动作相同
        self._handle_menu_action(action_name, action_data)

    def _handle_dock_visibility_changed(self, dock_name: str, visible: bool):
        """处理停靠窗口可见性变化"""
        # 更新菜单和工具栏的选中状态
        if dock_name == "project":
            self.menu_builder.check_action("toggle_project_tree", visible)
            self.toolbar_builder.check_action("toggle_project_tree", visible)
        # 右侧 AI 标签页已废弃，改用中心区域 AI Studio
        elif dock_name == "status":
            self.menu_builder.check_action("toggle_status_panel", visible)
        elif dock_name == "ai_console":
            self.menu_builder.check_action("toggle_ai_console", visible)
        elif dock_name == "output":
            self.menu_builder.check_action("toggle_output_panel", visible)

    def _update_word_count(self, count: int):
        """更新字数显示"""
        if hasattr(self, 'word_count_label'):
            self.word_count_label.setText(f"字数: {count}")

    def _update_cursor_position(self, line: int, column: int):
        """更新光标位置"""
        self.statusbar_builder.update_cursor_position(line, column)

    def _on_ai_text_applied(self, text: str):
        """AI文本应用到编辑器，并触发更新与自动保存（可控）"""
        try:
            # 将文本插入编辑器
            if self.editor_widget and hasattr(self.editor_widget, 'insert_text'):
                self.editor_widget.insert_text(text)

            # 触发内容更新到服务
            try:
                if self.controller and hasattr(self.editor_widget, 'get_current_document'):
                    doc = self.editor_widget.get_current_document()
                    if doc and hasattr(self.controller, 'document_content_changed'):
                        content = self.editor_widget.get_content()
                        self.controller.document_content_changed(doc.id, content)
                        # 自动保存当前文档（走控制器统一保存）
                        if hasattr(self.controller, 'save_current_document'):
                            self.controller.save_current_document()
            except Exception as e:
                logger.warning(f"AI写回触发更新/保存失败（用户手动保存兜底）: {e}")

            self.statusbar_builder.show_message("AI文本已应用、更新并保存")
        except Exception as e:
            logger.error(f"应用AI文本失败: {e}")
            self.statusbar_builder.show_error(f"应用AI文本失败: {e}")

    def _on_ai_status_updated(self, status: str):
        """AI状态更新"""
        if hasattr(self, 'ai_status_label'):
            self.ai_status_label.setText(f"AI: {status}")
        self.statusbar_builder.show_message(status)

    def _on_project_opened(self, project):
        """处理项目打开事件（性能优化版本）"""
        try:
            import time
            start_time = time.time()

            logger.info(f"🎯 主窗口收到项目打开事件: {project.title if project else 'None'}")

            # 关闭所有当前打开的文档（新项目时清理旧文档）
            if hasattr(self, 'editor_widget') and self.editor_widget:
                logger.info("🗂️ 关闭原项目的所有文档")
                self.editor_widget.close_all_documents()

                # 刷新欢迎页面以显示新项目的信息
                from PyQt6.QtCore import QTimer
                def refresh_welcome():
                    try:
                        if hasattr(self.editor_widget, 'refresh_welcome_page'):
                            self.editor_widget.refresh_welcome_page()
                            logger.info("📄 编辑器欢迎页面已刷新")
                    except Exception as e:
                        logger.error(f"刷新编辑器欢迎页面失败: {e}")

                # 延迟刷新，确保项目状态已完全更新
                QTimer.singleShot(100, refresh_welcome)

            # 立即更新状态栏（轻量级操作）
            self.statusbar_builder.update_project_info(project.name if project else "")
            logger.debug("✅ 状态栏项目信息已更新")

            # 更新状态服务
            if self.status_service:
                self.status_service.set_current_project(project)
                logger.info("📊 状态服务已更新当前项目")

            # 立即显示项目基本结构
            if hasattr(self.project_tree, 'load_project') and project:
                logger.info(f"🌳 立即显示项目基本结构: {project.title}")
                self._load_project_documents_async(project)
            else:
                if not hasattr(self.project_tree, 'load_project'):
                    logger.error("项目树没有 load_project 方法")
                if not project:
                    logger.error("项目对象为空")

            # 延迟更新 AI Studio（重量级操作）
            try:
                from PyQt6.QtCore import QTimer
                def update_ai_studio():
                    try:
                        if hasattr(self, 'ai_studio') and hasattr(self.ai_studio, 'show_status'):
                            self.ai_studio.show_status("项目已更新", "success")
                    except Exception as e:
                        logger.error(f"❌ 更新 AI Studio 失败: {e}")
                QTimer.singleShot(UI_UPDATE_DELAY_MS, update_ai_studio)
            except Exception:
                pass

            ui_time = time.time() - start_time
            logger.info(f"⚡ 项目打开事件处理完成，UI响应时间: {ui_time:.3f}s")

        except Exception as e:
            logger.error(f"处理项目打开事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _load_project_documents_async(self, project):
        """异步加载项目文档（优化版本）"""
        try:
            import time
            start_time = time.time()

            logger.info(f"🔄 开始异步加载项目文档: {project.title}")

            # 立即显示项目基本结构，不等待文档加载
            self.project_tree.load_project(project, [])

            ui_time = time.time() - start_time
            logger.info(f"⚡ 项目基本结构显示完成，耗时: {ui_time:.3f}s")

            # 异步加载文档数据
            from PyQt6.QtCore import QTimer

            async def load_documents():
                try:
                    doc_start_time = time.time()
                    logger.info(f"📄 开始获取文档数据: {project.title}")

                    # 获取文档服务
                    if hasattr(self.controller, 'document_service'):
                        # 清理文档缓存确保获取最新数据
                        if hasattr(self.controller.document_service, 'document_repository'):
                            repo = self.controller.document_service.document_repository
                            if hasattr(repo, 'clear_all_cache'):
                                repo.clear_all_cache()
                                logger.debug("🧹 已清理文档缓存")

                        documents = await self.controller.document_service.list_documents_by_project(project.id)

                        doc_load_time = time.time() - doc_start_time
                        logger.info(f"📋 文档数据获取完成: {len(documents)} 个文档, 耗时: {doc_load_time:.3f}s")
                        logger.info(f"🔍 准备更新项目树，文档列表: {[doc.title for doc in documents[:3]]}")  # 显示前3个文档标题

                        # 使用控制器的安全回调机制更新项目树
                        logger.info(f"⏰ 调度项目树更新任务，文档数量: {len(documents)}")

                        def update_project_tree_with_docs():
                            try:
                                update_start_time = time.time()
                                logger.info(f"🌳 开始更新项目树文档: {project.title}")

                                # 重新加载项目树，这次传入完整的文档列表
                                self.project_tree.load_project(project, documents)

                                update_time = time.time() - update_start_time
                                logger.info(f"✅ 项目树文档更新完成: {project.title}, 文档数量: {len(documents)}, 耗时: {update_time:.3f}s")
                            except Exception as e:
                                logger.error(f"❌ 更新项目树文档失败: {e}")
                                import traceback
                                logger.error(traceback.format_exc())

                        # 使用控制器的安全回调机制确保在主线程中执行
                        if hasattr(self.controller, '_safe_callback'):
                            self.controller._safe_callback(update_project_tree_with_docs)
                        else:
                            # 回退到QTimer
                            QTimer.singleShot(0, update_project_tree_with_docs)

                    else:
                        logger.warning("⚠️ 文档服务不可用")

                except Exception as e:
                    logger.error(f"❌ 加载项目文档失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # 运行异步任务
            if hasattr(self.controller, '_run_async_task'):
                logger.info("🚀 使用控制器的异步任务运行器")
                self.controller._run_async_task(
                    load_documents(),
                    success_callback=lambda _: logger.info("✅ 项目文档异步加载完成"),
                    error_callback=lambda e: logger.error(f"❌ 项目文档异步加载失败: {e}")
                )
            else:
                logger.warning("⚠️ 控制器没有异步任务运行器")

        except Exception as e:
            logger.error(f"❌ 异步加载项目文档失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 确保项目树至少能显示项目
            try:
                self.project_tree.load_project(project, [])
            except Exception as e2:
                logger.error(f"❌ 加载空项目树也失败: {e2}")

    def _on_document_opened_event(self, event):
        """处理文档打开事件（领域事件版本）"""
        try:
            import time
            start_time = time.time()

            title = getattr(event, 'document_title', '')
            doc_id = getattr(event, 'document_id', '')
            logger.info(f"🎯 开始处理文档打开事件: {title} ({doc_id})")

            # 立即更新状态栏（轻量级操作）
            self.statusbar_builder.update_document_info(title)
            logger.debug("✅ 状态栏更新完成")

            # 异步加载文档到编辑器（重量级操作）：由控制器层负责获取实体并调度
            # UI 层无需直接加载实体，降低耦合

            # 更新文档AI面板（这里仍需实体，延后由控制器传递或事件触发）
            # 先仅更新标题相关轻量状态

            ui_time = time.time() - start_time
            logger.info(f"⚡ 文档打开事件处理完成（领域事件），UI响应时间: {ui_time:.3f}s")

        except Exception as e:
            logger.error(f"处理文档打开事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _load_document_to_editor_async(self, document):
        """异步加载文档到编辑器"""
        try:
            from PyQt6.QtCore import QTimer

            def load_in_chunks():
                """分块加载文档内容"""
                try:
                    logger.info(f"📝 开始分块加载文档: {document.title}")

                    # 先显示加载状态
                    self.statusbar_builder.show_message(f"正在加载文档: {document.title}...")

                    # 延迟加载编辑器内容，让UI先响应
                    def actual_load():
                        try:
                            logger.info(f"🔄 执行实际文档加载: {document.title}")
                            self.editor_widget.load_document(document)
                            self.statusbar_builder.show_message(f"文档已打开: {document.title}")
                            logger.info(f"✅ 文档加载到编辑器完成: {document.title}")
                        except Exception as e:
                            logger.error(f"❌ 实际文档加载失败: {e}")
                            self.statusbar_builder.show_message(f"文档加载失败: {document.title}")

                    # 使用QTimer延迟执行，让UI先更新
                    QTimer.singleShot(DOCUMENT_LOAD_DELAY_MS, actual_load)

                except Exception as e:
                    logger.error(f"❌ 分块加载失败: {e}")

            # 立即开始分块加载
            load_in_chunks()

        except Exception as e:
            logger.error(f"❌ 异步文档加载失败: {e}")
            # 回退到同步加载
            try:
                self.editor_widget.load_document(document)
            except Exception as e2:
                logger.error(f"❌ 回退同步加载也失败: {e2}")

    def update_document_ai_panel(self, document=None):
        """更新 AI Studio 上下文（最终版）"""
        try:
            if not document:
                return
            content = getattr(document, 'content', '') if hasattr(document, 'content') else ''
            if hasattr(self, 'ai_studio'):
                if hasattr(self.ai_studio, 'set_document_context'):
                    self.ai_studio.set_document_context(content)
                # 同步当前选区
                sel = ""
                try:
                    current_tab = self.editor_widget.get_current_tab()
                    if current_tab and hasattr(current_tab, 'text_edit'):
                        sel = current_tab.text_edit.textCursor().selectedText() or ""
                except Exception:
                    sel = ""
                if hasattr(self.ai_studio, 'set_selected_text'):
                    self.ai_studio.set_selected_text(sel)
        except Exception as e:
            logger.error(f"更新 AI Studio 上下文失败: {e}")

    def _on_status_message(self, message: str):
        """处理状态消息"""
        self.statusbar_builder.show_message(message)

    def _refresh_project_tree(self):
        """刷新项目树"""
        try:
            if self.project_tree and hasattr(self.project_tree, 'refresh'):
                self.project_tree.refresh()
            elif self.controller and hasattr(self.controller, 'refresh_project_tree'):
                self.controller.refresh_project_tree()
        except Exception as e:
            logger.error(f"刷新项目树失败: {e}")

    def _show_shortcuts_help(self):
        """显示快捷键帮助"""
        try:
            shortcuts_text = """
            快捷键帮助：

            文件操作：
            Ctrl+N - 新建项目
            Ctrl+O - 打开项目
            Ctrl+S - 保存文档
            Ctrl+Q - 退出程序

            AI功能：
            F4 - 打开右侧AI面板
            F6 - 切换底部AI控制台
            Alt+Enter - 打开AI动作面板

            视图：
            F11 - 切换全屏模式

            """
            QMessageBox.information(self, "快捷键帮助", shortcuts_text)
        except Exception as e:
            logger.error(f"显示快捷键帮助失败: {e}")



    def _open_ai_action_palette(self):
        """Open AI Action Palette (based on current document AI panel and selection)"""
        try:
            from src.presentation.widgets.ai.refactored.components.ai_action_palette import AIActionPalette
            selected_text = ""
            try:
                if hasattr(self, 'editor_widget') and hasattr(self.editor_widget, 'get_selected_text'):
                    selected_text = self.editor_widget.get_selected_text() or ""
            except Exception:
                selected_text = ""

            # 直接使用 AI Studio
            ai_widget = getattr(self, 'ai_studio', None)
            if ai_widget is None:
                try:
                    self.statusbar_builder.update_status("AI Studio 未就绪", "warning")
                except Exception:
                    pass
                return

            dlg = AIActionPalette.from_ai_widget(ai_widget, selected_text)

            # Center the dialog relative to main window
            geo = self.geometry()
            dlg.move(geo.center().x() - dlg.width() // 2, geo.top() + 120)
            dlg.exec()
        except Exception as e:
            logger.error(f"打开 AI 动作面板失败: {e}")

    def _toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _show_ai_panel(self):
        """显示AI助手面板"""
        try:
            # 聚焦到 AI Studio 页面
            if hasattr(self, 'ai_studio'):
                self.ai_studio.setFocus()
            logger.info("AI Studio 已显示")

        except Exception as e:
            logger.error(f"显示AI助手面板失败: {e}")

    def _switch_to_ai_mode(self, mode: str):
        """切换AI模式（保留用于兼容性）"""
        try:
            # 切换到 AI Studio 指定页面
            try:
                if hasattr(self, 'ai_studio') and hasattr(self.ai_studio, 'nav'):
                    mapping = {
                        'writing': 0,
                        'chat': 1,
                        'scene': 2,
                        'optimize': 3,
                        'outline': 4,
                        'character': 5,
                        'world': 6,
                        'naming': 7,
                    }
                    idx = mapping.get(mode, 0)
                    self.ai_studio.nav.setCurrentRow(idx)
                    # 确保可见并聚焦
                    self.ai_studio.setVisible(True)
                    if hasattr(self, 'main_splitter'):
                        self.main_splitter.setStretchFactor(0, 3)
                        self.main_splitter.setStretchFactor(1, 2)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"切换AI模式失败: {e}")

    def _show_ai_setup(self):
        """显示AI服务设置"""
        try:
            from src.presentation.dialogs.ai_setup_dialog import AISetupDialog

            settings_to_inject = None
            service_to_inject = None
            try:
                if hasattr(self, 'controller') and hasattr(self.controller, 'settings_service') and self.controller.settings_service:
                    service_to_inject = self.controller.settings_service
                    # 可选注入 Settings 对象（用于显示默认值，不作写入）
                    if hasattr(self.controller.settings_service, 'settings'):
                        settings_to_inject = self.controller.settings_service.settings
            except Exception:
                settings_to_inject = None
                service_to_inject = None

            dialog = AISetupDialog(self, settings=settings_to_inject, settings_service=service_to_inject)
            dialog.settings_updated.connect(self._on_ai_settings_updated)
            dialog.exec()

        except Exception as e:
            logger.error(f"显示AI设置对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"无法打开AI设置对话框：{str(e)}")



    def _on_ai_settings_updated(self):
        """AI设置更新后的处理"""
        try:
            # 重新同步设置服务（保证缓存在 user_settings.json 的值进入运行态）
            if hasattr(self.controller, 'settings_service'):
                settings_service = self.controller.settings_service
                settings_service.sync_from_main_config()

            # 通知AI编排服务立即应用新配置
            if hasattr(self.controller, 'ai_service') and hasattr(self.controller.ai_service, 'reload_settings'):
                # 组装最小必要配置传入（默认提供商/基础URL/模型/密钥）
                ss = getattr(self, 'settings_service', None) or getattr(self.controller, 'settings_service', None)
                new_conf = None
                if ss is not None:
                    new_conf = {
                        'providers': {
                            'openai': {
                                'api_key': ss.get('ai.openai_api_key'),
                                'base_url': ss.get('ai.openai_base_url', 'https://api.openai.com/v1'),
                                'default_model': ss.get('ai.openai_model', 'gpt-3.5-turbo')
                            },
                            'deepseek': {
                                'api_key': ss.get('ai.deepseek_api_key'),
                                'base_url': ss.get('ai.deepseek_base_url', 'https://api.deepseek.com/v1'),
                                'default_model': ss.get('ai.deepseek_model', 'deepseek-chat')
                            },
                        },
                        'default_provider': ss.get('ai.default_provider', 'deepseek'),
                    }
                self.controller.ai_service.reload_settings(new_conf)

            logger.info("AI设置已更新并立即应用")

        except Exception as e:
            logger.error(f"处理AI设置更新失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 保存当前项目信息（如果有打开的项目）
            self._save_current_project_info()

            # 发出关闭信号
            self.window_closing.emit()

            # 保存窗口状态
            self._save_window_state()

            # 接受关闭事件
            event.accept()

        except Exception as e:
            logger.error(f"关闭窗口失败: {e}")
            event.accept()

    def _save_current_project_info(self):
        """保存当前项目信息"""
        try:
            if self.controller and hasattr(self.controller, 'project_service'):
                current_project = self.controller.project_service.get_current_project()
                if current_project:
                    # 获取项目路径
                    project_path = self.controller.project_service.get_current_project_path()
                    if project_path:
                        # 保存项目信息，下次启动时自动打开
                        self.controller.settings_service.set_last_project_info(
                            current_project.id,
                            str(project_path)
                        )
                        logger.info(f"已保存当前项目信息: {current_project.title}")
                    else:
                        logger.debug(f"项目 '{current_project.title}' 没有设置根路径，跳过路径保存")
                else:
                    logger.info("没有打开的项目需要保存")
        except Exception as e:
            logger.error(f"保存当前项目信息失败: {e}")

    def _save_window_state(self):
        """保存窗口状态"""
        try:
            settings = self.controller.settings_service

            # 保存窗口几何
            settings.set_window_geometry(self.saveGeometry().data())

            # 保存停靠窗口状态
            dock_state = self.dock_builder.save_dock_state(self)
            settings.set_dock_state(dock_state)

        except Exception as e:
            logger.error(f"保存窗口状态失败: {e}")

    def show_message(self, message: str, timeout: int = DEFAULT_STATUS_TIMEOUT):
        """显示状态消息"""
        self.statusbar_builder.show_message(message, timeout)

    # ==================== AI集成信号处理 ====================

    def _on_content_changed(self, document_id: str, content: str):
        """处理文档内容变化"""
        try:
            # 更新全局AI面板的上下文
            document = self.controller.get_document_by_id(document_id) if self.controller else None
            doc_type = "chapter"
            metadata = {}

            if document:
                doc_type = str(document.type).split('.')[-1].lower()
                metadata = {
                    "title": getattr(document, 'title', ''),
                    "tags": getattr(document, 'tags', []),
                    "author": getattr(document, 'author', '')
                }

            try:
                # 将上下文推送到 AI Studio
                try:
                    if hasattr(self, 'ai_studio'):
                        sel = ""
                        try:
                            current_tab = self.editor_widget.get_current_tab()
                            if current_tab and hasattr(current_tab, 'text_edit'):
                                sel = current_tab.text_edit.textCursor().selectedText() or ""
                        except Exception:
                            sel = ""
                        if hasattr(self.ai_studio, 'set_document_context'):
                            self.ai_studio.set_document_context(content)
                        if hasattr(self.ai_studio, 'set_selected_text'):
                            self.ai_studio.set_selected_text(sel)
                except Exception as e:
                    logger.debug(f"更新 AI Studio 上下文失败: {e}")
            except Exception as e:
                logger.debug(f"更新全局AI面板上下文失败: {e}")

            # 更新当前编辑标签内的文档AI面板上下文
            current_tab = self.editor_widget.get_current_tab()
            if current_tab and hasattr(current_tab, 'ai_panel') and current_tab.ai_panel:
                try:
                    if hasattr(current_tab.ai_panel, 'set_document_context'):
                        current_tab.ai_panel.set_document_context(content, doc_type, metadata)
                except Exception as e:
                    logger.debug(f"更新编辑标签文档AI面板上下文失败: {e}")

            # AI Studio 已取代右侧文档AI面板，此同步逻辑删除
        except Exception as e:
            logger.error(f"处理文档内容变化失败: {e}")

    def _on_selection_changed(self, document_id: str, selected_text: str):
        """处理选中文字变化"""
        try:
            # 更新 AI Studio 的选中文字
            if hasattr(self, 'ai_studio') and hasattr(self.ai_studio, 'set_selected_text'):
                self.ai_studio.set_selected_text(selected_text)

            # 兼容：更新当前文档选区写回逻辑
            current_tab = self.editor_widget.get_current_tab()
            if current_tab and hasattr(current_tab, 'ai_panel') and current_tab.ai_panel:
                if hasattr(current_tab.ai_panel, 'set_selected_text'):
                    current_tab.ai_panel.set_selected_text(selected_text)

        except Exception as e:
            logger.error(f"处理选中文字变化失败: {e}")

    def _on_document_switched(self, document_id: str):
        """处理文档切换"""
        try:
            # 获取新文档的内容和信息
            current_tab = self.editor_widget.get_current_tab()
            if current_tab:
                content = current_tab.text_edit.toPlainText()
                selected_text = current_tab.text_edit.textCursor().selectedText()

                # 触发内容和选中文字更新
                self._on_content_changed(document_id, content)
                self._on_selection_changed(document_id, selected_text)

        except Exception as e:
            logger.error(f"处理文档切换失败: {e}")

    def _on_ai_text_insert(self, text: str, position: int = -1):
        """处理AI文本插入请求（强制主线程）"""
        try:
            from src.shared.utils.thread_safety import ensure_main_thread

            @ensure_main_thread
            def do_insert():
                current_tab = self.editor_widget.get_current_tab()
                if current_tab:
                    cursor = current_tab.text_edit.textCursor()
                    if position == -2:
                        cursor.movePosition(cursor.MoveOperation.End)
                    elif position >= 0:
                        cursor.setPosition(position)
                    current_tab.text_edit.setTextCursor(cursor)
                    cursor.insertText(text)
                    current_tab.text_edit.setTextCursor(cursor)
                    logger.info(f"AI文本已插入: {len(text)} 字符")

            do_insert()
        except Exception as e:
            logger.error(f"AI文本插入失败: {e}")

    def _on_ai_text_replace(self, text: str, start_pos: int = -1, end_pos: int = -1):
        """处理AI文本替换请求（强制主线程）"""
        try:
            from src.shared.utils.thread_safety import ensure_main_thread

            @ensure_main_thread
            def do_replace():
                current_tab = self.editor_widget.get_current_tab()
                if current_tab:
                    cursor = current_tab.text_edit.textCursor()
                    if start_pos >= 0 and end_pos >= 0:
                        cursor.setPosition(start_pos)
                        cursor.setPosition(end_pos, cursor.MoveMode.KeepAnchor)
                    elif cursor.hasSelection():
                        pass
                    else:
                        cursor.insertText(text)
                        current_tab.text_edit.setTextCursor(cursor)
                        return
                    cursor.insertText(text)
                    current_tab.text_edit.setTextCursor(cursor)
                    logger.info(f"AI文本已替换: {len(text)} 字符")

            do_replace()
        except Exception as e:
            logger.error(f"AI文本替换失败: {e}")

    def show_progress(self, value: int, maximum: int = 100):
        """显示进度"""
        self.statusbar_builder.show_progress(value, maximum)

    def hide_progress(self):
        """隐藏进度条"""
        self.statusbar_builder.hide_progress()

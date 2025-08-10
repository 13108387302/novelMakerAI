#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主控制器

协调各个组件之间的交互
"""

import asyncio
from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from src.domain.entities.document import Document

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QDialog
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread


class ThreadSafeCallbackEmitter(QObject):
    """
    线程安全的回调发射器

    用于在多线程环境中安全地执行UI回调函数。
    确保回调函数在主线程中执行，避免线程安全问题。

    实现方式：
    - 使用Qt信号槽机制确保线程安全
    - 将回调函数和参数封装为信号数据
    - 在主线程中执行实际的回调逻辑
    - 提供完整的错误处理和日志记录

    Signals:
        callback_signal: 回调信号，传递回调函数和参数
    """
    callback_signal = pyqtSignal(object)  # 传递回调函数

    def __init__(self):
        """
        初始化线程安全回调发射器

        连接回调信号到执行方法。
        """
        super().__init__()
        self.callback_signal.connect(self._execute_callback)

    def _execute_callback(self, callback_data):
        """
        在主线程中执行回调函数

        Args:
            callback_data: 包含回调函数和参数的元组
        """
        try:
            callback, args = callback_data
            logger.info("在主线程中执行回调")
            if args:
                callback(*args)
            else:
                callback()
            logger.info("主线程回调执行完成")
        except Exception as e:
            logger.error(f"主线程回调执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def emit_callback(self, callback, *args):
        """
        发射回调信号

        将回调函数和参数封装为信号数据并发射。

        Args:
            callback: 要执行的回调函数
            *args: 回调函数的参数
        """
        logger.info("发射回调信号")
        self.callback_signal.emit((callback, args))
        logger.info("回调信号已发射")

from src.presentation.dialogs.find_replace_dialog import FindReplaceDialog
from src.presentation.dialogs.settings_dialog import SettingsDialog
from src.presentation.dialogs.project_wizard import ProjectWizard
from src.presentation.dialogs.word_count_dialog import WordCountDialog
from src.presentation.dialogs.template_manager_dialog import TemplateManagerDialog
from src.presentation.dialogs.plugin_manager_dialog import PluginManagerDialog



from src.application.services.application_service import ApplicationService
from src.application.services.project_service import ProjectService
from src.application.services.document_service import DocumentService
# 使用新的AI服务架构
try:
    from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService as AIService
except ImportError:
    # 向后兼容：如果新架构不可用，使用兼容性包装器
    from src.application.services.ai import get_ai_service
    AIService = get_ai_service

# 新控制器（分层委派）
from src.presentation.controllers.project_controller import ProjectController
from src.presentation.controllers.document_controller import DocumentController
from src.presentation.controllers.ai_controller import AIController
from src.application.services.settings_service import SettingsService
from src.application.services.search import SearchService
from src.application.services.import_export_service import ImportExportService
from src.application.services.import_export.base import ImportOptions, ExportOptions
from src.domain.entities.project import ProjectType, Project
from src.domain.entities.document import DocumentType
from src.domain.events.document_events import DocumentCreatedEvent, DocumentSavedEvent
from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import controller_error_handler, async_controller_error_handler
from src.shared.utils.async_manager import get_async_manager, async_task
from src.shared.constants import (
    UI_IMMEDIATE_DELAY, UI_SHORT_DELAY, UI_MEDIUM_DELAY, UI_LONG_DELAY,
    ASYNC_SHORT_TIMEOUT, ASYNC_MEDIUM_TIMEOUT, ASYNC_LONG_TIMEOUT,
    ERROR_MESSAGE_MAX_LENGTH
)

logger = get_logger(__name__)


class MainController(QObject):
    """
    主控制器

    协调各个组件之间的交互，管理应用程序的核心业务逻辑。
    作为表示层和应用层之间的桥梁，处理用户操作和业务逻辑。

    实现方式：
    - 继承QObject提供信号槽机制
    - 协调项目、文档、AI服务等各个组件
    - 处理用户界面事件和业务逻辑
    - 管理对话框和窗口的显示
    - 提供完整的错误处理和用户反馈

    Attributes:
        main_window: 主窗口实例
        project_service: 项目服务
        document_service: 文档服务
        ai_service: AI服务
        settings_service: 设置服务

    Signals:
        project_opened: 项目打开信号
        document_opened: 文档打开信号
        status_message: 状态消息信号
        progress_updated: 进度更新信号
    """

    # 信号定义
    project_opened = pyqtSignal(object)  # 项目打开
    project_closed = pyqtSignal()  # 项目关闭
    document_opened = pyqtSignal(object)  # 文档打开
    status_message = pyqtSignal(str)  # 状态消息
    progress_updated = pyqtSignal(int, int)  # 进度更新
    project_tree_refresh_requested = pyqtSignal()  # 项目树刷新请求

    def __init__(
        self,
        app_service: ApplicationService,
        project_service: ProjectService,
        document_service: DocumentService,
        ai_service: AIService,
        settings_service: SettingsService,
        search_service: SearchService,
        import_export_service: ImportExportService,
        ai_assistant_manager: Optional['AIAssistantManager'] = None,
        status_service: Optional['StatusService'] = None
    ):
        """
        初始化主控制器

        注入所有必要的服务依赖，初始化控制器状态和对话框管理。

        Args:
            app_service: 应用程序服务
            project_service: 项目服务
            document_service: 文档服务
            ai_service: AI服务
            settings_service: 设置服务
            search_service: 搜索服务
            import_export_service: 导入导出服务
        """
        super().__init__()

        # 服务依赖
        self.app_service = app_service
        self.project_service = project_service
        self.document_service = document_service
        self.ai_service = ai_service

        # 先保存依赖，再初始化分层控制器
        self.settings_service = settings_service
        self.search_service = search_service
        self.import_export_service = import_export_service
        self.ai_assistant_manager = ai_assistant_manager
        self._status_service = status_service

        # 新控制器实例（最小接入，不破坏现有流程）
        self.project_controller = ProjectController(project_service=self.project_service, settings_service=self.settings_service)
        self.document_controller = DocumentController(document_service=self.document_service)
        self.ai_controller = AIController(ai_service=self.ai_service)

        # 连接控制器状态/事件到主控制器信号
        self.project_controller.project_opened.connect(self.project_opened)
        self.project_controller.project_closed.connect(self.project_closed)
        self.project_controller.status_message.connect(self.status_message)

        # 统一：文档控制器发出领域事件对象，由主控制器做桥接，向UI层继续发文档对象/简单参数
        self.document_controller.document_opened.connect(self._on_document_opened_event)
        self.document_controller.document_saved.connect(self._on_document_saved)
        self.document_controller.document_closed.connect(self._on_document_closed_event)
        self.document_controller.document_created.connect(self._on_document_created)
        self.document_controller.document_deleted.connect(self._on_document_deleted_event)
        self.document_controller.document_renamed.connect(self._on_document_renamed_event)


        self.document_controller.status_message.connect(self.status_message)
        self.ai_controller.status_message.connect(self.status_message)

        # 状态
        self._main_window: Optional['MainWindow'] = None

        # 创建线程安全的回调发射器
        self.callback_emitter = ThreadSafeCallbackEmitter()

        # 使用统一的异步任务管理器
        self.async_manager = get_async_manager()

        # 任务状态管理
        self._creating_documents = set()  # 正在创建的文档标题集合（防重复创建）
        self._opening_documents = set()  # 正在打开的文档ID集合（防重复打开）
        self._last_open_time = {}  # 最后打开时间记录

        # 对话框
        self._find_replace_dialog: Optional[FindReplaceDialog] = None
        self._settings_dialog: Optional[SettingsDialog] = None
        self._project_wizard: Optional[ProjectWizard] = None
        self._word_count_dialog: Optional[WordCountDialog] = None
        self._template_manager_dialog: Optional[TemplateManagerDialog] = None
        self._plugin_manager_dialog: Optional[PluginManagerDialog] = None
        self._character_manager_dialog = None
        self._backup_manager_dialog = None

        # 项目树刷新节流
        self._refresh_timer: Optional[QTimer] = None
        self._pending_refresh = False

        # 设置事件监听
        self._setup_event_listeners()

        logger.info("主控制器初始化完成")

    def _setup_event_listeners(self) -> None:
        """设置事件监听"""
        try:
            # 获取事件总线
            from src.shared.events.event_bus import get_event_bus
            event_bus = get_event_bus()

            # 监听文档创建事件
            event_bus.subscribe(
                DocumentCreatedEvent,
                self._on_document_created,
                subscriber=self
            )

            # 监听文档保存事件
            event_bus.subscribe(
                DocumentSavedEvent,
                self._on_document_saved,
                subscriber=self
            )

            # 监听AI配置变化事件
            try:
                from src.domain.events.ai_events import AIConfigurationChangedEvent
                event_bus.subscribe(
                    AIConfigurationChangedEvent,
                    self._on_ai_configuration_changed,
                    subscriber=self
                )
                logger.debug("✅ AI配置变化事件监听已设置")
            except ImportError:
                logger.debug("⚠️ AI事件模块不可用，跳过AI配置事件监听")

            logger.info("✅ 事件监听设置完成")

        except Exception as e:
            logger.error(f"❌ 设置事件监听失败: {e}")

    @controller_error_handler("清理资源", show_user_error=False)
    def cleanup(self):
        """清理资源"""
        # 取消所有活跃的异步任务
        if hasattr(self, 'async_manager'):
            cancelled_count = self.async_manager.cancel_all_tasks()
            logger.info(f"已取消 {cancelled_count} 个异步任务")

        logger.info("控制器资源清理完成")

    def set_main_window(self, main_window: 'MainWindow') -> None:
        """设置主窗口引用"""
        self._main_window = main_window

        # 如果没有注入的状态服务，则使用主窗口的状态服务
        if not self._status_service and hasattr(main_window, 'status_service'):
            self._status_service = main_window.status_service
            logger.info("状态服务引用已设置")

    def _run_async_task(self, coro, success_callback=None, error_callback=None, timeout=None):
        """通用的异步任务执行器（使用统一的异步管理器）"""
        try:
            # 使用统一的异步管理器执行任务
            task_id = self.async_manager.execute_async(
                coro=coro,
                success_callback=success_callback,
                error_callback=error_callback,
                timeout=timeout or ASYNC_MEDIUM_TIMEOUT
            )
            logger.debug(f"异步任务已提交: {task_id}")
            return task_id

        except Exception as e:
            logger.error(f"启动异步任务失败: {e}")
            if error_callback:
                error_callback(e)
            else:
                self._show_error("操作失败", str(e))

    def _safe_callback(self, callback):
        """线程安全的回调执行"""
        try:
            # 使用异步管理器的回调信号确保线程安全
            self.async_manager.callback_signal.emit(callback)
        except Exception as e:
            logger.error(f"安全回调执行失败: {e}")
            # 尝试直接执行作为备用
            try:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, callback)
            except Exception as e2:
                logger.error(f"备用回调执行也失败: {e2}")

    def _connect_signals(self, main_window):
        """连接信号"""
        # 连接窗口信号
        main_window.window_closing.connect(self._on_window_closing)

        # 连接控制器信号到窗口
        self.status_message.connect(main_window.show_message)
        self.progress_updated.connect(main_window.show_progress)

    # 移除重复的cleanup方法定义

    # ========================================================================
    # 项目管理
    # ========================================================================

    @controller_error_handler("新建项目")
    def new_project(self) -> None:
        """新建项目"""
        # 创建项目向导
        if not self._project_wizard:
            from src.presentation.dialogs.project_wizard import ProjectWizard
            self._project_wizard = ProjectWizard(self._main_window)
            self._project_wizard.project_created.connect(self._on_project_wizard_completed)

        # 显示向导
        result = self._project_wizard.exec()
        if result == self._project_wizard.DialogCode.Accepted:
            logger.info("项目创建向导完成")

    @controller_error_handler("新建文档")
    def new_document(self) -> None:
        """新建文档"""
        logger.info("🔧 new_document() 方法被调用")

        if not self.project_service.has_current_project:
            self._show_warning("新建文档", "请先打开一个项目")
            return

        # 使用输入对话框获取文档标题
        from PyQt6.QtWidgets import QInputDialog
        title, ok = QInputDialog.getText(
            self._main_window,
            "新建文档",
            "请输入文档标题:",
            text="新文档"
        )

        if ok and title.strip():
            logger.info(f"📝 用户确认创建新文档: {title.strip()}")
            self.async_manager.execute_delayed(
                self._run_async_new_document,
                UI_IMMEDIATE_DELAY,
                title.strip()
            )
        else:
            logger.info("❌ 用户取消创建新文档")





    @async_controller_error_handler("新建文档", log_traceback=True)
    async def _new_document_async(self, title: str) -> None:
        """异步新建文档"""
        # 检查是否正在创建同名文档
        if title in self._creating_documents:
            logger.warning(f"文档 '{title}' 正在创建中，跳过重复创建")
            return

        # 添加到创建中列表
        self._creating_documents.add(title)

        try:
            current_project = self.project_service.current_project
            if not current_project:
                return

            # 创建新文档
            document = await self.document_service.create_document(
                title=title,
                content="",
                project_id=current_project.id,
                document_type=DocumentType.CHAPTER
            )

            if document:
                logger.info(f"文档创建成功: {document.title}")
                # 状态消息由 DocumentController 发送，避免重复

                # 延迟打开新创建的文档
                self.async_manager.execute_delayed(
                    self._safe_open_document,
                    UI_MEDIUM_DELAY,
                    document.id
                )
            else:
                self._show_error("新建文档失败", "无法创建文档")

        finally:
            # 从创建中列表移除
            self._creating_documents.discard(title)

    @controller_error_handler("删除文档", show_user_error=False)
    def delete_document(self, document_id: str) -> None:
        """删除文档"""
        self.async_manager.execute_delayed(
            self._run_async_delete_document,
            UI_IMMEDIATE_DELAY,
            document_id
        )

    @controller_error_handler("重命名文档")
    def rename_document(self, document_id: str, new_title: str) -> None:
        """重命名文档"""
        def delayed_rename():
            self._run_async_task(
                self.document_controller.rename_document(document_id, new_title),
                success_callback=lambda result: self._show_info("成功", f"文档重命名为: {new_title}"),
                error_callback=lambda e: self._show_error("重命名失败", f"重命名文档失败: {e}")
            )
        self.async_manager.execute_delayed(delayed_rename, UI_IMMEDIATE_DELAY)

    @controller_error_handler("复制文档")
    def copy_document(self, document_id: str, new_title: str) -> None:
        """复制文档"""
        def delayed_copy():
            self._run_async_task(
                self.document_controller.copy_document(document_id, new_title),
                success_callback=lambda result: self._show_info("成功", f"文档复制为: {new_title}"),
                error_callback=lambda e: self._show_error("复制失败", f"复制文档失败: {e}")
            )
        self.async_manager.execute_delayed(delayed_copy, UI_IMMEDIATE_DELAY)

    def _run_async_delete_document(self, document_id: str):
        """运行异步删除文档操作"""
        self._run_async_task(
            self._delete_document_async(document_id),
            success_callback=lambda _: logger.info(f"文档删除成功: {document_id}"),
            error_callback=lambda e: self._show_error("删除文档失败", str(e))
        )

    async def _delete_document_async(self, document_id: str) -> None:
        """异步删除文档（委派到 DocumentController.delete_document）"""
        try:
            success = await self.document_controller.delete_document(document_id)
            if success:
                logger.info(f"文档删除成功: {document_id}")
                # 状态消息由 DocumentController 发送，避免重复
                self.schedule_refresh_project_tree()
            else:
                self._show_error("删除文档失败", "无法删除文档")
        except Exception as e:
            logger.error(f"异步删除文档失败: {e}")
            self._show_error("删除文档失败", str(e))

    def create_document_from_tree(self, document_type: str, project_id: str) -> None:
        """从项目树创建文档"""
        try:
            logger.info(f"🌳 从项目树创建文档请求: 类型={document_type}, 项目={project_id}")

            if not self.project_service.has_current_project:
                self._show_warning("创建文档", "请先打开一个项目")
                return

            # 检查是否有相同类型的文档正在创建
            creation_check_key = f"creating_{document_type}_{project_id}"
            if hasattr(self, '_ui_creation_locks') and creation_check_key in self._ui_creation_locks:
                logger.warning(f"相同类型的文档正在创建中，跳过: {document_type}")
                self._show_warning("创建文档", f"正在创建{document_type}，请稍候...")
                return

            # 添加UI级别的创建锁
            if not hasattr(self, '_ui_creation_locks'):
                self._ui_creation_locks = set()
            self._ui_creation_locks.add(creation_check_key)

            try:
                # 根据文档类型确定默认标题
                type_names = {
                    "chapter": "新章节",
                    "character": "新角色",
                    "setting": "新设定",
                    "outline": "新大纲",
                    "note": "新笔记"
                }
                default_title = type_names.get(document_type, "新文档")

                # 使用输入对话框获取文档标题
                from PyQt6.QtWidgets import QInputDialog
                title, ok = QInputDialog.getText(
                    self._main_window,
                    f"创建{default_title}",
                    "请输入文档标题:",
                    text=default_title
                )

                if ok and title.strip():
                    logger.info(f"📝 用户确认创建文档: {title.strip()}")
                    # 直接调用同步方法，避免嵌套的QTimer调用
                    self._create_document_from_tree_sync(title.strip(), document_type, project_id)
                else:
                    logger.info("❌ 用户取消创建文档")

            finally:
                # 清理UI级别的创建锁
                self._ui_creation_locks.discard(creation_check_key)

        except Exception as e:
            logger.error(f"从项目树创建文档失败: {e}")
            self._show_error("创建文档失败", str(e))

    # 已删除 _run_async_create_document_from_tree 方法，避免嵌套QTimer调用

    def _create_document_from_tree_sync(self, title: str, document_type: str, project_id: str):
        """非阻塞的文档创建"""
        try:
            self.status_message.emit(f"正在创建{document_type}: {title}")

            # 使用非阻塞的异步执行器
            self._run_async_task(
                self._create_document_from_tree_async(title, document_type, project_id),
                success_callback=lambda result: self._on_document_created_success(title, document_type),
                error_callback=lambda e: self._show_error("创建文档失败", str(e))
            )

        except Exception as e:
            logger.error(f"启动文档创建失败: {e}")
            self._show_error("创建文档失败", str(e))

    def _on_document_created_success(self, title: str, document_type: str):
        """文档创建成功回调"""
        # 状态消息由 DocumentController 发送，避免重复
        logger.info(f"从项目树创建文档成功: {title}")
        # 延迟刷新项目树，确保文档已完全保存
        from PyQt6.QtCore import QTimer
        self.schedule_refresh_project_tree(1000)  # 1秒后刷新

    def _safe_open_document(self, document_id: str):
        """安全的文档打开方法"""
        try:
            # 使用非阻塞方式打开文档
            self._run_async_task(
                self._open_document_async(document_id),
                success_callback=lambda document: self._on_document_opened_success(document, document_id),
                error_callback=lambda e: logger.warning(f"文档打开失败: {document_id}, {e}")
            )
        except Exception as e:
            logger.error(f"安全打开文档失败: {e}")

    def _simple_refresh_project_tree(self):
        """简化的项目树刷新"""
        try:
            if hasattr(self, 'project_service') and self.project_service.has_current_project:
                current_project = self.project_service.current_project
                if current_project:
                    # 使用非阻塞方式获取文档并刷新
                    self._run_async_task(
                        self.document_service.list_documents_by_project(current_project.id),
                        success_callback=lambda docs: self._update_project_tree_with_documents(current_project, docs),
                        error_callback=lambda e: self._update_project_tree_with_documents(current_project, [])
                    )
        except Exception as e:
            logger.error(f"简化项目树刷新失败: {e}")

    def _force_refresh_project_tree(self):
        """强制刷新项目树（确保新文档显示）"""
        try:
            if hasattr(self, 'project_service') and self.project_service.has_current_project:
                current_project = self.project_service.current_project
                if current_project:
                    logger.info(f"强制刷新项目树: {current_project.title}")
                    # 使用非阻塞方式获取文档并刷新
                    self._run_async_task(
                        self.document_service.list_documents_by_project(current_project.id),
                        success_callback=lambda docs: self._force_update_project_tree(current_project, docs),
                        error_callback=lambda e: logger.error(f"强制刷新项目树失败: {e}")
                    )
        except Exception as e:
            logger.error(f"强制刷新项目树失败: {e}")

    def _force_update_project_tree(self, project, documents):
        """强制更新项目树"""
        try:
            if hasattr(self, '_main_window') and self._main_window:
                # 强制重新加载项目树
                self._main_window.project_tree.load_project(project, documents)
                logger.info(f"项目树强制更新完成: {project.title}, {len(documents)} 个文档")

                # 展开项目节点，确保新文档可见
                self._main_window.project_tree.expandAll()

        except Exception as e:
            logger.error(f"强制更新项目树失败: {e}")

    def _update_project_tree_with_documents(self, project, documents):
        """使用文档更新项目树"""
        try:
            if hasattr(self, '_main_window') and self._main_window:
                self._main_window.project_tree.load_project(project, documents)
                logger.debug(f"项目树更新完成: {project.title}, {len(documents)} 个文档")
        except Exception as e:
            logger.error(f"更新项目树失败: {e}")

    async def _create_document_from_tree_async(self, title: str, document_type: str, project_id: str) -> str:
        """异步从项目树创建文档"""
        try:
            # 生成精确的创建键（标题+类型+项目ID的哈希）
            import hashlib
            import time

            # 使用标题、类型、项目ID的组合生成唯一键
            content_hash = hashlib.md5(f"{title}_{document_type}_{project_id}".encode()).hexdigest()[:8]
            timestamp = int(time.time() * 1000)  # 毫秒级时间戳
            creation_key = f"doc_{content_hash}_{timestamp}"

            logger.info(f"🔑 生成创建键: {creation_key} (标题: {title})")

            # 更严格的重复检查：检查相同标题+类型+项目的文档
            base_pattern = f"doc_{content_hash}_"
            active_keys = [key for key in self._creating_documents if key.startswith(base_pattern)]

            if active_keys:
                logger.warning(f"文档 '{title}' ({document_type}) 正在创建中，活跃键: {active_keys}")
                logger.warning(f"跳过重复创建")
                return None

            # 检查是否已存在相同标题的文档（仅警告，不阻止创建）
            try:
                existing_docs = await self.document_service.list_documents_by_project(project_id)
                for doc in existing_docs:
                    if doc.title == title and doc.document_type.value == document_type:
                        logger.warning(f"已存在相同标题的文档: '{title}' ({document_type})")
                        # 在主线程中显示警告，但不阻止创建
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self._show_warning("创建文档", f"已存在标题为 '{title}' 的{document_type}，将创建新的文档"))
                        break  # 只显示一次警告
            except Exception as e:
                logger.warning(f"检查现有文档失败: {e}")

            # 添加到创建中列表
            logger.info(f"📝 添加创建键到活跃列表: {creation_key}")
            self._creating_documents.add(creation_key)

            try:
                # 映射文档类型
                from src.domain.entities.document import DocumentType
                type_map = {
                    "chapter": DocumentType.CHAPTER,
                    "character": DocumentType.CHARACTER,
                    "setting": DocumentType.SETTING,
                    "outline": DocumentType.OUTLINE,
                    "note": DocumentType.NOTE
                }
                doc_type = type_map.get(document_type, DocumentType.CHAPTER)

                # 根据文档类型生成默认内容
                default_content = self._get_default_content_for_type(doc_type)

                # 获取当前项目ID（确保使用正确的项目ID）
                current_project = self.project_service.get_current_project()
                if current_project:
                    actual_project_id = current_project.id
                    logger.info(f"使用当前项目ID: {actual_project_id} (传入的ID: {project_id})")
                else:
                    actual_project_id = project_id
                    logger.warning(f"无法获取当前项目，使用传入的项目ID: {project_id}")

                # 创建新文档
                document = await self.document_controller.create_document(
                    title=title,
                    content=default_content,
                    project_id=actual_project_id,
                    document_type=doc_type
                )

                if document:
                    logger.info(f"文档创建成功: {document.title}")
                    # 状态消息由 DocumentController 发送，避免重复

                    # 立即触发项目树刷新信号
                    self.schedule_refresh_project_tree()

                    # 延迟打开新创建的文档，确保文档已完全保存
                    # 使用线程安全的方式调度文档打开
                    self.callback_emitter.emit_callback(
                        lambda: self._schedule_document_open(document.id)
                    )

                    # 返回文档ID
                    return document.id
                else:
                    self._show_error("创建文档失败", "无法创建文档")
                    return None

            finally:
                # 从创建中列表移除
                logger.info(f"🧹 从活跃列表移除创建键: {creation_key}")
                self._creating_documents.discard(creation_key)

        except Exception as e:
            logger.error(f"异步从项目树创建文档失败: {e}")
            self._show_error("创建文档失败", str(e))
            # 确保从创建中列表移除
            if 'creation_key' in locals():
                logger.info(f"🧹 异常处理中移除创建键: {creation_key}")
                self._creating_documents.discard(creation_key)
            return None

    def _schedule_document_open(self, document_id: str):
        """在主线程中调度文档打开"""
        try:
            logger.info(f"在主线程中调度文档打开: {document_id}")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._safe_open_document(document_id))
        except Exception as e:
            logger.error(f"调度文档打开失败: {e}")
            # 如果QTimer失败，直接打开
            self._safe_open_document(document_id)

    def _get_default_content_for_type(self, doc_type: DocumentType) -> str:
        """根据文档类型获取默认内容"""
        templates = {
            DocumentType.CHAPTER: "# 章节标题\n\n在这里开始写作...\n",
            DocumentType.CHARACTER: "# 角色名称\n\n## 基本信息\n- 姓名：\n- 年龄：\n- 性别：\n- 职业：\n\n## 外貌特征\n\n## 性格特点\n\n## 背景故事\n\n## 人际关系\n",
            DocumentType.SETTING: "# 设定标题\n\n## 基本信息\n\n## 详细描述\n\n## 相关要素\n",
            DocumentType.OUTLINE: "# 大纲标题\n\n## 主要情节\n\n### 开端\n\n### 发展\n\n### 高潮\n\n### 结局\n",
            DocumentType.NOTE: "# 笔记标题\n\n记录你的想法和灵感...\n"
        }
        return templates.get(doc_type, "")

    # 统一删除实现：保留上方实现，移除重复定义
    # （此处原有的重复 _run_async_delete_document/_delete_document_async 已移除）






    def create_new_project(self) -> None:
        """创建新项目（统一入口）"""
        try:
            from PyQt6.QtWidgets import QInputDialog, QFileDialog
            import os

            # 获取项目名称
            name, ok = QInputDialog.getText(
                self._main_window,
                "新建项目",
                "请输入项目名称:",
                text="新项目"
            )
            if not ok or not name.strip():
                return

            # 选择保存位置
            default_location = os.path.join(os.getcwd(), "projects")
            try:
                os.makedirs(default_location, exist_ok=True)
            except Exception:
                default_location = os.path.join(os.path.expanduser("~"), "Documents", "AI小说编辑器")
                try:
                    os.makedirs(default_location, exist_ok=True)
                except Exception:
                    default_location = os.getcwd()

            project_location = QFileDialog.getExistingDirectory(
                self._main_window,
                "选择项目保存位置",
                default_location
            )
            if not project_location:
                return

            # 走统一服务入口
            project_info = {
                "name": name.strip(),
                "location": project_location,
                "description": "",
                "author": self.settings_service.get_setting("project.default_author", ""),
                "word_count": self.settings_service.get_setting("project.default_target_word_count", 80000),
                "type": "novel",
                "template": "空白项目",
            }
            self.create_project_via_service(project_info)
        except Exception as e:
            logger.error(f"创建新项目失败: {e}")
            self._show_error("错误", f"创建新项目失败: {e}")

    @controller_error_handler("保存当前文档", log_traceback=True)
    def save_current_document(self) -> None:
        """保存当前文档"""
        logger.info("🔄 Ctrl+S 保存功能被调用")

        # 检查编辑器是否可用
        if not (hasattr(self.main_window, 'editor_widget') and self.main_window.editor_widget):
            self._show_warning("提示", "编辑器未初始化")
            logger.warning("❌ 尝试保存文档，但编辑器未初始化")
            return

        logger.debug("✅ 编辑器组件存在")

        # 获取当前文档
        current_document = self.main_window.editor_widget.get_current_document()
        if not current_document:
            self._show_warning("提示", "没有打开的文档")
            logger.warning("❌ 尝试保存文档，但没有打开的文档")
            return

        logger.info(f"✅ 找到当前文档: {current_document.title} (ID: {current_document.id})")

        # 准备文档数据
        content = self.main_window.editor_widget.get_content()
        old_content = current_document.content

        # 更新文档
        self._update_document_for_save(current_document, content)

        logger.info(f"📝 准备保存文档: {current_document.title}")
        logger.info(f"   - 字数: {current_document.statistics.word_count}")
        logger.info(f"   - 内容变化: {len(old_content)} -> {len(content)} 字符")

        # 异步保存
        document_title = current_document.title  # 捕获标题，避免闭包问题
        self.async_manager.execute_async(
            self._save_document_async(current_document),
            success_callback=lambda result: self._on_save_success(document_title),
            error_callback=lambda e: self._on_save_error(document_title, e),
            timeout=ASYNC_MEDIUM_TIMEOUT
        )

    def _update_document_for_save(self, document, content: str) -> None:
        """更新文档以准备保存"""
        document.content = content
        document.statistics.update_from_content(content)

        from datetime import datetime
        document.updated_at = datetime.now()

    def _on_save_success(self, document_title: str):
        """保存成功回调"""
        logger.info(f"✅ 文档保存成功: {document_title}")
        self._show_info("成功", f"文档 '{document_title}' 保存成功")
        # 状态消息由 DocumentController 发送，避免重复

    def _on_save_error(self, document_title: str, error):
        """保存失败回调"""
        logger.error(f"❌ 文档保存失败: {document_title}, 错误: {error}")
        self._show_error("错误", f"保存文档 '{document_title}' 失败: {error}")
        self.status_message.emit(f"保存失败: {error}")

    def open_project_directory(self, project_dir: Path) -> None:
        """直接打开指定的项目目录（供应用入口调用）"""
        try:
            if not isinstance(project_dir, Path):
                project_dir = Path(project_dir)
            QTimer.singleShot(0, lambda: self._run_async_open_project_dir(project_dir))
        except Exception as e:
            logger.error(f"通过主控制器打开项目失败: {e}")
            self._show_error("打开项目失败", str(e))

    def open_project_dialog(self) -> None:
        """打开项目对话框"""
        self.open_project()

    def open_project(self) -> None:
        """打开项目"""
        try:
            # 获取上次打开的目录或默认目录
            last_dir = self.settings_service.get_last_opened_directory()
            if last_dir and Path(last_dir).exists():
                default_path = Path(last_dir)
            else:
                # 使用当前工作目录作为默认路径，因为现在需要项目上下文
                default_path = Path.cwd()

            # 提供两种打开方式：选择目录或选择文件
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self._main_window,
                "打开项目",
                "请选择打开方式：\n\n"
                "• 选择「是」：选择项目目录（推荐）\n"
                "• 选择「否」：选择项目文件",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 选择项目目录
                from PyQt6.QtWidgets import QFileDialog
                project_dir = QFileDialog.getExistingDirectory(
                    self._main_window,
                    "选择项目目录",
                    str(default_path)
                )

                if project_dir:
                    QTimer.singleShot(0, lambda: self._run_async_open_project_dir(Path(project_dir)))

            elif reply == QMessageBox.StandardButton.No:
                # 选择项目文件
                file_path, _ = QFileDialog.getOpenFileName(
                    self._main_window,
                    "打开项目文件",
                    str(default_path),
                    "项目文件 (*.json *.zip);;所有文件 (*)"
                )

                if file_path:
                    QTimer.singleShot(0, lambda: self._run_async_open_project(Path(file_path)))

        except Exception as e:
            logger.error(f"打开项目失败: {e}")
            self._show_error("打开项目失败", str(e))

    def auto_open_last_project(self) -> None:
        """自动打开上次项目"""
        try:
            # 检查是否启用自动打开
            if not self.settings_service.get_auto_open_last_project():
                logger.info("自动打开上次项目功能已禁用")
                return

            # 获取上次项目信息
            project_id, project_path = self.settings_service.get_last_project_info()

            # 添加详细的调试信息
            logger.info(f"🔍 自动打开项目 - 从设置获取的信息:")
            logger.info(f"   项目ID: {project_id}")
            logger.info(f"   项目路径: {project_path}")

            if not project_id or not project_path:
                logger.info("没有上次项目信息，跳过自动打开")
                return

            # 处理项目路径（支持相对路径和绝对路径）
            path = Path(project_path)
            if not path.is_absolute():
                # 如果是相对路径，相对于应用程序根目录
                from pathlib import Path as PathLib
                app_root = PathLib(__file__).parent.parent.parent.parent
                path = app_root / path

            # 规范化路径
            path = path.resolve()

            if not path.exists():
                logger.warning(f"上次项目路径不存在: {path}")
                # 尝试在projects目录下查找项目
                projects_dir = Path(__file__).parent.parent.parent.parent / "projects"
                if projects_dir.exists():
                    # 查找匹配的项目目录
                    for project_dir in projects_dir.iterdir():
                        if project_dir.is_dir():
                            project_config = project_dir / "project.json"
                            if project_config.exists():
                                try:
                                    import json
                                    with open(project_config, 'r', encoding='utf-8') as f:
                                        config = json.load(f)
                                    if config.get('id') == project_id:
                                        logger.info(f"在projects目录找到匹配的项目: {project_dir}")
                                        path = project_dir
                                        # 更新配置中的路径
                                        self.settings_service.set_last_project_info(project_id, str(path))
                                        break
                                except Exception as e:
                                    logger.debug(f"读取项目配置失败: {e}")
                                    continue

                # 如果还是找不到，清空无效的项目信息
                if not path.exists():
                    logger.warning("无法找到上次项目，清空项目信息")
                    self.settings_service.clear_last_project_info()
                    return

            # 检查项目配置文件是否存在
            project_config = path / "project.json"
            if not project_config.exists():
                logger.warning(f"上次项目配置文件不存在: {project_config}")
                # 清空无效的项目信息
                self.settings_service.clear_last_project_info()
                return

            # 验证项目ID是否匹配
            try:
                import json
                with open(project_config, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                actual_project_id = config.get('id')

                logger.info(f"🔍 项目ID验证:")
                logger.info(f"   设置中的ID: {project_id}")
                logger.info(f"   文件中的ID: {actual_project_id}")

                if actual_project_id != project_id:
                    logger.warning(f"项目ID不匹配！更新设置中的项目ID")
                    logger.warning(f"   旧ID: {project_id}")
                    logger.warning(f"   新ID: {actual_project_id}")

                    # 更新设置中的项目ID
                    self.settings_service.set_last_project_info(actual_project_id, str(path))
                    project_id = actual_project_id

            except Exception as e:
                logger.error(f"验证项目ID失败: {e}")
                # 清空无效的项目信息
                self.settings_service.clear_last_project_info()
                return

            logger.info(f"自动打开上次项目: {path} (ID: {project_id})")

            # 延迟打开项目，确保界面已完全加载
            QTimer.singleShot(1000, lambda: self._run_async_open_project_dir(path))

        except Exception as e:
            logger.error(f"自动打开上次项目失败: {e}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")

    def close_current_project(self) -> None:
        """关闭当前项目"""
        try:
            current_project = self.project_service.get_current_project()
            if current_project:
                logger.info(f"关闭当前项目: {current_project.title}")

                # 保存所有未保存的文档
                self._save_all_documents()

                # 关闭项目
                self.project_service.close_project()

                # 清空上次项目信息（用户主动关闭，下次不自动打开）
                self.settings_service.clear_last_project_info()

                # 发送项目关闭信号
                self.project_closed.emit()
                self.status_message.emit("项目已关闭")

                logger.info("项目关闭完成")
            else:
                logger.info("没有打开的项目需要关闭")

        except Exception as e:
            logger.error(f"关闭项目失败: {e}")
            self._show_error("关闭项目失败", str(e))

    def _save_all_documents(self) -> None:
        """保存所有未保存的文档"""
        try:
            # 这里可以添加保存所有文档的逻辑
            # 目前先记录日志
            logger.info("保存所有未保存的文档")
        except Exception as e:
            logger.error(f"保存文档失败: {e}")

    async def _open_project_async(self, file_path: Path) -> None:
        """异步打开项目"""
        try:
            self.status_message.emit("正在打开项目...")
            logger.info(f"尝试打开项目文件: {file_path}")

            if file_path.suffix.lower() == '.json' and file_path.name == 'project.json':
                # 将打开项目统一委派到 ProjectController
                await self.project_controller.open_project_by_path(file_path.parent)
            else:
                # 导入项目（导入成功后也走 ProjectController 打开路径）
                result = await self.import_export_service.import_project(
                    file_path, "", ImportOptions()
                )
                if result.success:
                    # 假设导入时返回了项目目录或已创建项目，尝试使用返回路径或父目录
                    project_dir = Path(result.success.root_path) if hasattr(result.success, 'root_path') and result.success.root_path else file_path.parent
                    await self.project_controller.open_project_by_path(project_dir)
                else:
                    self._show_error("打开项目失败", f"无法导入项目文件: {file_path}")

        except Exception as e:
            logger.error(f"异步打开项目失败: {e}")
            self._show_error("打开项目失败", str(e))

    async def _open_project_dir_async(self, project_dir: Path) -> None:
        """异步打开项目目录"""
        try:
            self.status_message.emit("正在打开项目目录...")
            logger.info(f"尝试打开项目目录: {project_dir}")

            # 检查目录是否存在
            if not project_dir.exists():
                error_msg = f"选择的目录不存在：\n{project_dir}"
                logger.warning(error_msg)
                self._show_error("打开项目失败", error_msg)
                return

            # 检查目录中是否有project.json文件
            project_config = project_dir / "project.json"
            if not project_config.exists():
                error_msg = f"选择的目录不是有效的项目目录：\n{project_dir}\n\n缺少project.json文件"
                logger.warning(error_msg)
                self._show_error("打开项目失败", error_msg)
                return

            # 检查project.json文件是否可读
            try:
                with open(project_config, 'r', encoding='utf-8') as f:
                    import json
                    project_data = json.load(f)

                    # 如果缺少项目ID，自动修复
                    if not project_data.get('id'):
                        logger.warning(f"项目配置文件缺少ID，自动修复: {project_config}")
                        # 使用项目文件夹名称作为ID
                        project_data['id'] = project_dir.name

                        # 保存修复后的配置文件
                        with open(project_config, 'w', encoding='utf-8') as f_write:
                            json.dump(project_data, f_write, ensure_ascii=False, indent=2)

                        logger.info(f"项目配置文件已修复，添加ID: {project_data['id']}")

            except Exception as e:
                error_msg = f"无法读取项目配置文件：\n{project_config}\n\n错误: {e}"
                logger.warning(error_msg)
                self._show_error("打开项目失败", error_msg)
                return

            # 直接委派 ProjectController 负责打开与信号
            await self.project_controller.open_project_by_path(project_dir)

        except Exception as e:
            error_msg = f"打开项目目录时发生错误：\n{project_dir}\n\n错误: {e}"
            logger.error(f"异步打开项目目录失败: {e}")
            self._show_error("打开项目失败", error_msg)

    def save_current(self) -> None:
        """保存当前项目/文档"""
        try:
            # 使用QTimer在下一个事件循环中执行异步操作
            QTimer.singleShot(0, lambda: self._run_async_save())
        except Exception as e:
            logger.error(f"保存失败: {e}")
            self._show_error("保存失败", str(e))

    def save_document(self, document) -> None:
        """保存指定文档"""
        try:
            logger.info(f"开始保存文档: {document.title}")
            # 捕获文档对象，避免闭包问题
            doc = document
            # 使用文档控制器委派保存
            self._run_async_task(
                self.document_controller.save_document(document.id),
                success_callback=lambda result, d=doc: self._on_document_save_success(d),
                error_callback=lambda e, d=doc: self._on_document_save_error(d, e)
            )
        except Exception as e:
            logger.error(f"保存文档失败: {e}")
            self._show_error("保存失败", str(e))

    def _run_async_save(self):
        """运行异步保存操作"""
        try:
            # 使用统一的异步执行器
            self._run_async_task(
                self._save_current_async(),
                success_callback=lambda result: self._on_save_success_general(),
                error_callback=lambda error: self._on_save_error_general(error)
            )
        except Exception as e:
            logger.error(f"启动保存操作失败: {e}")
            self._show_error("保存失败", str(e))

    def _on_save_success_general(self):
        """通用保存成功回调"""
        self.status_message.emit("保存成功")
        logger.info("保存成功")

    def _on_save_error_general(self, error):
        """通用保存错误回调"""
        logger.error(f"保存失败: {error}")
        self._show_error("保存失败", str(error))

    async def _save_document_async(self, document) -> None:
        """异步保存指定文档"""
        try:
            logger.info(f"异步保存文档: {document.title}")
            # 使用文档对象保存方法
            success = await self.document_service.save_document_object(document)
            if success:
                logger.info(f"文档保存成功: {document.title}")
            else:
                raise Exception(f"文档保存失败: {document.title}")
        except Exception as e:
            logger.error(f"异步保存文档失败: {e}")
            raise

    async def _update_current_document_content(self) -> None:
        """更新当前文档内容"""
        try:
            if hasattr(self.main_window, 'editor_widget') and self.main_window.editor_widget:
                current_document = self.main_window.editor_widget.get_current_document()
                if current_document:
                    # 获取编辑器中的最新内容
                    content = self.main_window.editor_widget.get_content()

                    # 更新文档内容
                    current_document.content = content

                    # 更新统计信息
                    current_document.statistics.update_from_content(content)

                    # 更新修改时间
                    from datetime import datetime
                    current_document.updated_at = datetime.now()

                    logger.debug(f"更新文档内容: {current_document.title}, 字数: {current_document.statistics.word_count}")

                    # 确保文档服务中的文档对象也是最新的
                    if current_document.id in self.document_service._open_documents:
                        self.document_service._open_documents[current_document.id] = current_document
                        logger.debug(f"同步文档到文档服务: {current_document.title}")
                else:
                    logger.debug("没有当前文档需要更新")
            else:
                logger.debug("编辑器未初始化，跳过文档内容更新")
        except Exception as e:
            logger.error(f"更新当前文档内容失败: {e}")

    def _on_document_save_success(self, document):
        """文档保存成功回调"""
        logger.info(f"文档保存成功: {document.title}")
        # 状态消息由 DocumentController 发送，避免重复

    def _on_document_save_error(self, document, error):
        """文档保存错误回调"""
        logger.error(f"文档保存失败: {document.title}, {error}")
        self._show_error("保存失败", f"文档 '{document.title}' 保存失败: {str(error)}")



    async def _save_current_async(self) -> None:
        """异步保存当前内容"""
        try:
            self.status_message.emit("正在保存...")

            # 首先更新当前编辑器中的文档内容
            await self._update_current_document_content()

            # 保存当前文档
            if self.document_service.has_open_documents:
                success = await self.document_service.save_all_documents()
                if success:
                    # 状态消息由 DocumentController 发送，避免重复
                    logger.info("所有文档保存成功")
                else:
                    self._show_error("保存失败", "无法保存文档")
                    logger.error("文档保存失败")

            # 保存当前项目
            if self.project_service.has_current_project:
                success = await self.project_service.save_current_project()
                if success:
                    # 状态消息由 ProjectController 发送，避免重复
                    logger.info("项目保存成功")
                else:
                    self._show_error("保存失败", "无法保存项目")
                    logger.error("项目保存失败")

        except Exception as e:
            logger.error(f"异步保存失败: {e}")
            self._show_error("保存失败", str(e))

    def save_as(self) -> None:
        """另存为"""
        try:
            if not self.project_service.has_current_project:
                self._show_warning("另存为", "请先打开一个项目")
                return

            # 获取当前项目
            current_project = self.project_service.current_project
            if not current_project:
                self._show_warning("另存为", "当前没有打开的项目")
                return

            # 选择保存位置
            # 使用当前工作目录作为默认路径
            default_path = Path.cwd()

            file_path, _ = QFileDialog.getSaveFileName(
                self._main_window,
                "另存为项目",
                str(default_path / f"{current_project.title}_副本.json"),
                "项目文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                QTimer.singleShot(0, lambda: self._run_async_save_as(Path(file_path)))

        except Exception as e:
            logger.error(f"另存为失败: {e}")
            self._show_error("另存为失败", str(e))

    def _run_async_save_as(self, file_path: Path):
        """运行异步另存为操作"""
        self._run_async_task(
            self._save_as_async(file_path),
            success_callback=lambda _: logger.info(f"另存为成功: {file_path}"),
            error_callback=lambda e: self._show_error("另存为失败", str(e))
        )

    async def _save_as_async(self, file_path: Path) -> None:
        """异步另存为"""
        try:
            current_project = self.project_service.current_project
            if not current_project:
                return

            # 创建项目副本
            new_project = Project(
                title=current_project.title + "_副本",
                description=current_project.description,
                project_type=current_project.project_type,
                status=current_project.status,
                metadata=current_project.metadata
            )

            # 保存新项目
            success = await self.project_service.save_project_as(new_project, file_path)
            if success:
                self._show_info("另存为成功", f"项目已另存为: {file_path.name}")

                # 询问是否切换到新项目
                reply = QMessageBox.question(
                    self._main_window,
                    "切换项目",
                    "是否切换到新保存的项目？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    await self.project_service.open_project(file_path)
                    self.project_opened.emit(new_project.id)
            else:
                self._show_error("另存为失败", "无法保存项目副本")

        except Exception as e:
            logger.error(f"异步另存为失败: {e}")
            self._show_error("另存为失败", str(e))

    def import_project(self) -> None:
        """导入项目"""
        try:
            # 使用当前工作目录作为默认路径
            default_path = Path.cwd()

            file_path, _ = QFileDialog.getOpenFileName(
                self._main_window,
                "导入项目",
                str(default_path),
                "支持的格式 (*.json *.zip *.txt *.docx);;所有文件 (*)"
            )

            if file_path:
                QTimer.singleShot(0, lambda: self._run_async_task(
                    self._import_project_async(Path(file_path)),
                    success_callback=lambda _: logger.info(f"项目导入成功: {file_path}"),
                    error_callback=lambda e: self._show_error("导入项目失败", str(e))
                ))

        except Exception as e:
            logger.error(f"导入项目失败: {e}")
            self._show_error("导入项目失败", str(e))

    async def _import_project_async(self, file_path: Path) -> None:
        """异步导入项目"""
        try:
            self.status_message.emit("正在导入项目...")

            result = await self.import_export_service.import_project(
                file_path, "", ImportOptions()
            )

            if result.success:
                # 从导入结果中获取项目信息
                if hasattr(result, 'project') and result.project:
                    # 统一由 ProjectController 处理打开与信号
                    await self.project_controller.open_project_by_path(Path(result.project.root_path))
                    return
                    # 已由 ProjectController 打开，无需重复发信号
                    logger.info(f"项目导入成功: {result.project.name}")
                    self.callback_emitter.emit_callback(self._refresh_project_ui)

                elif hasattr(result, 'imported_items') and result.imported_items:
                    # 如果没有完整项目，但有导入的项目ID
                    project_id = result.imported_items[0] if result.imported_items else None
                    if project_id:
                        # 尝试加载项目
                        project = await self.project_service.load_project(project_id)
                        if project:
                            await self.project_service.set_current_project(project)
                            self.project_opened.emit(project)
                            # 状态消息由 ProjectController 发送，避免重复
                        else:
                            self.status_message.emit("项目导入成功，但无法加载项目详情")
                    else:
                        self.status_message.emit("项目导入成功")
                else:
                    self.status_message.emit("项目导入成功")
            else:
                self._show_error("导入失败", "无法导入项目文件")

        except Exception as e:
            logger.error(f"异步导入项目失败: {e}")
            self._show_error("导入失败", str(e))

    def _refresh_project_ui(self):
        """
        刷新项目相关的UI组件

        在项目导入或切换后更新界面显示。
        """
        try:
            if self._main_window:
                # 刷新项目树
                if hasattr(self._main_window, 'project_tree'):
                    self._main_window.project_tree.refresh()

                # 更新窗口标题
                current_project = self.project_service.current_project
                if current_project:
                    title = f"AI小说编辑器 - {current_project.name}"
                    self._main_window.setWindowTitle(title)

                # 刷新状态栏
                if hasattr(self._main_window, 'status_bar'):
                    self._main_window.status_bar.update_project_info()

                logger.debug("项目UI刷新完成")

        except Exception as e:
            logger.error(f"刷新项目UI失败: {e}")

    def export_project(self) -> None:
        """导出项目"""
        try:
            if not self.project_service.has_current_project:
                self._show_warning("导出失败", "没有打开的项目")
                return

            # 使用当前工作目录作为默认路径
            default_path = Path.cwd()

            file_path, _ = QFileDialog.getSaveFileName(
                self._main_window,
                "导出项目",
                str(default_path / f"{self.project_service.current_project.title}.zip"),
                "ZIP文件 (*.zip);;JSON文件 (*.json);;文本文件 (*.txt)"
            )

            if file_path:
                QTimer.singleShot(0, lambda: self._run_async_task(
                    self._export_project_async(Path(file_path)),
                    success_callback=lambda _: logger.info(f"项目导出成功: {file_path}"),
                    error_callback=lambda e: self._show_error("导出项目失败", str(e))
                ))

        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            self._show_error("导出项目失败", str(e))

    async def _export_project_async(self, file_path: Path) -> None:
        """异步导出项目"""
        try:
            self.status_message.emit("正在导出项目...")

            project = self.project_service.current_project
            export_format = file_path.suffix.lower().lstrip('.')

            result = await self.import_export_service.export_project(
                project.id,
                file_path,
                export_format,
                ExportOptions()
            )

            if result.success:
                # 状态消息由 ProjectController 发送，避免重复
                pass
            else:
                error_msg = "; ".join(result.errors) if result.errors else "未知错误"
                self._show_error("导出失败", error_msg)

        except Exception as e:
            logger.error(f"异步导出项目失败: {e}")
            self._show_error("导出失败", str(e))

    # ========================================================================
    # 文档管理
    # ========================================================================

    def open_document(self, document_id: str) -> None:
        """打开文档"""
        try:
            # 直接委派给 DocumentController，由其处理防抖和去重
            QTimer.singleShot(0, lambda: self._run_async_task(
                self.document_controller.open_document(document_id),
                success_callback=lambda doc: self._on_document_opened_success(doc, document_id) if doc else None,
                error_callback=lambda e: self._show_error("打开文档失败", str(e))
            ))
        except Exception as e:
            logger.error(f"打开文档失败: {e}")
            self._show_error("打开文档失败", str(e))

    async def _open_document_async(self, document_id: str) -> None:
        """异步打开文档"""
        try:
            document = await self.document_service.open_document(document_id)

            if document:
                # 发送“领域事件”到UI层（彻底事件化）
                try:
                    from src.domain.events.document_events import DocumentOpenedEvent
                    event = DocumentOpenedEvent(
                        document_id=getattr(document, 'id', ''),
                        document_title=getattr(document, 'title', '')
                    )
                    self.document_opened.emit(event)
                except Exception:
                    # 退化为不带标题的事件
                    from src.domain.events.document_events import DocumentOpenedEvent
                    self.document_opened.emit(DocumentOpenedEvent(document_id=document_id, document_title=''))

                # 返回文档对象，让调用者在主线程中处理UI更新
                return document
            else:
                self._show_error("打开文档失败", "无法加载文档")
                return None

        except Exception as e:
            logger.error(f"异步打开文档失败: {e}")
            self._show_error("打开文档失败", str(e))
            return None

    def document_content_changed(self, document_id: str, content: str) -> None:
        """文档内容变更"""
        try:
            # 使用文档控制器委派内容更新
            QTimer.singleShot(0, lambda: self._run_async_task(
                self.document_controller.update_document_content(document_id, content),
                success_callback=lambda _: logger.debug(f"文档内容更新成功: {document_id}"),
                error_callback=lambda e: logger.error(f"异步更新文档内容失败: {e}")
            ))
        except Exception as e:
            logger.error(f"更新文档内容失败: {e}")

    def get_document_by_id(self, document_id: str) -> Optional['Document']:
        """根据ID获取文档"""
        try:
            # 首先检查已打开的文档
            open_documents = self.document_service.get_open_documents()
            for doc in open_documents:
                if doc.id == document_id:
                    return doc

            # 如果没有在打开的文档中找到，返回None
            # 注意：这里不进行异步加载，因为这个方法是同步的
            logger.debug(f"文档未在已打开列表中找到: {document_id}")
            return None

        except Exception as e:
            logger.error(f"获取文档失败: {document_id}, {e}")
            return None

    def _run_async_update_document_content(self, document_id: str, content: str):
        """运行异步更新文档内容操作"""
        self._run_async_task(
            self._update_document_content_async(document_id, content),
            success_callback=lambda _: logger.debug(f"文档内容更新成功: {document_id}"),
            error_callback=lambda e: logger.error(f"异步更新文档内容失败: {e}")
        )

    async def _update_document_content_async(self, document_id: str, content: str) -> None:
        """异步更新文档内容"""
        try:
            await self.document_service.update_document_content(document_id, content)
        except Exception as e:
            logger.error(f"异步更新文档内容失败: {e}")

    def select_project(self, project_id: str) -> None:
        """选择项目"""
        try:
            # 使用异步方式打开项目
            self._run_async_task(
                self.project_service.open_project(project_id),
                success_callback=lambda project: self._on_project_selected_success(project),
                error_callback=lambda e: logger.error(f"选择项目失败: {e}")
            )
        except Exception as e:
            logger.error(f"选择项目失败: {e}")

    def _on_project_selected_success(self, project):
        """项目选择成功回调"""
        if project:
            # 更新最近项目
            try:
                from src.shared.managers.recent_projects_manager import get_recent_projects_manager
                recent_manager = get_recent_projects_manager()
                if project.root_path:
                    recent_manager.add_project(Path(project.root_path), project.title)
            except Exception as e:
                logger.warning(f"更新最近项目失败: {e}")

            self.project_opened.emit(project)
            logger.info(f"项目选择成功: {project.title}")

    @controller_error_handler("创建项目")
    def create_project_via_service(self, project_info: dict, completion_callback=None) -> Optional[Path]:
        """通过服务创建项目并打开，统一入口供 StartupWindow/其他UI 调用"""
        try:
            name = project_info.get("name", "新项目")
            description = project_info.get("description", "")
            author = project_info.get("author", "")
            target_word_count = project_info.get("word_count", 80000)
            proj_type = project_info.get("type", "novel")
            location = project_info.get("location")
            if not location:
                raise ValueError("项目位置不能为空")
            from src.domain.entities.project import ProjectType
            type_enum = getattr(ProjectType, proj_type.upper(), ProjectType.NOVEL)

            # 组合路径
            project_dir = Path(location) / name

            async def do_create():
                project = await self.project_service.create_project(
                    name=name,
                    project_type=type_enum,
                    description=description,
                    author=author,
                    target_word_count=target_word_count,
                    project_path=str(project_dir)
                )
                if not project:
                    raise RuntimeError("项目创建失败")
                # 打开项目（统一委派 ProjectController 以避免重复实现与重复信号）
                await self.project_controller.open_project_by_path(project_dir)
                return project_dir

            def on_success(path):
                logger.info(f"项目创建异步任务成功，路径: {path}")
                if completion_callback:
                    logger.info("调用项目创建完成回调")
                    completion_callback(path)
                else:
                    logger.warning("没有设置项目创建完成回调")

            def on_error(e):
                logger.error(f"项目创建异步任务失败: {e}")
                self._show_error("创建项目失败", str(e))
                if completion_callback:
                    logger.info("调用项目创建失败回调")
                    completion_callback(None)

            self._run_async_task(
                do_create(),
                success_callback=lambda _: on_success(project_dir),
                error_callback=on_error
            )
            return project_dir  # 立即返回预期路径
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            if completion_callback:
                completion_callback(None)
            raise


    # ========================================================================
    # 搜索功能
    # ========================================================================

    def _ensure_find_replace_dialog(self) -> None:
        """确保查找替换对话框已创建并连接信号"""
        if not self._find_replace_dialog:
            self._find_replace_dialog = FindReplaceDialog(self._main_window)
            self._find_replace_dialog.find_requested.connect(self._on_find_requested)
            self._find_replace_dialog.replace_requested.connect(self._on_replace_requested)
            self._find_replace_dialog.replace_all_requested.connect(self._on_replace_all_requested)

    def _show_find_replace_dialog(self, tab_index: int = 0) -> None:
        """显示查找替换对话框的通用方法"""
        try:
            self._ensure_find_replace_dialog()

            # 切换到指定标签页
            if hasattr(self._find_replace_dialog, 'tab_widget'):
                self._find_replace_dialog.tab_widget.setCurrentIndex(tab_index)

            # 设置当前选中的文本
            if self._main_window and self._main_window.editor_widget:
                selected_text = self._main_window.editor_widget.get_selected_text()
                if selected_text:
                    self._find_replace_dialog.set_search_text(selected_text)

            self._find_replace_dialog.show()
            self._find_replace_dialog.raise_()
            self._find_replace_dialog.activateWindow()

        except Exception as e:
            operation = "替换对话框" if tab_index == 1 else "查找对话框"
            logger.error(f"显示{operation}失败: {e}")
            self._show_error(operation, f"无法显示{operation}: {e}")

    def show_find_dialog(self) -> None:
        """显示查找对话框"""
        self._show_find_replace_dialog(tab_index=0)

    def show_replace_dialog(self) -> None:
        """显示替换对话框"""
        self._show_find_replace_dialog(tab_index=1)

    # ========================================================================
    # 工具功能
    # ========================================================================

    def show_word_count(self) -> None:
        """显示字数统计"""
        try:
            if not self.project_service.has_current_project:
                self._show_warning("字数统计", "请先打开一个项目")
                return

            if not self._word_count_dialog:
                self._word_count_dialog = WordCountDialog(
                    self.project_service,
                    self.document_service,
                    self._main_window
                )

            self._word_count_dialog.show()
            self._word_count_dialog.raise_()
            self._word_count_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示字数统计对话框失败: {e}")
            self._show_error("字数统计", f"无法显示字数统计: {e}")

    def show_settings(self) -> None:
        """显示设置对话框"""
        try:
            if not self._settings_dialog:
                from src.presentation.styles.theme_manager import ThemeManager
                theme_manager = self._main_window.theme_manager if hasattr(self._main_window, 'theme_manager') else None

                self._settings_dialog = SettingsDialog(
                    self.settings_service,
                    theme_manager,
                    self._main_window
                )
                self._settings_dialog.settings_changed.connect(self._on_settings_changed)
                self._settings_dialog.theme_changed.connect(self._on_theme_changed)

            result = self._settings_dialog.exec()
            if result == QMessageBox.StandardButton.Accepted:
                self.status_message.emit("设置已保存")

        except Exception as e:
            logger.error(f"显示设置对话框失败: {e}")
            self._show_error("设置对话框", f"无法显示设置对话框: {e}")

    def show_about(self) -> None:
        """显示关于对话框"""
        QMessageBox.about(
            self._main_window,
            "关于 AI小说编辑器 2.0",
            """
            <h3>AI小说编辑器 2.0</h3>
            <p>版本: 2.0.0</p>
            <p>一个现代化的AI辅助小说创作工具</p>
            <p>采用分层架构设计，支持多种AI服务</p>
            <br>
            <p><b>主要特性:</b></p>
            <ul>
            <li>智能AI续写</li>
            <li>对话优化</li>
            <li>场景扩展</li>
            <li>风格分析</li>
            <li>项目管理</li>
            <li>多格式导入导出</li>
            </ul>
            <br>
            <p>© 2024 AI小说编辑器团队</p>
            """
        )

    # ========================================================================
    # 事件处理
    # ========================================================================

    def _on_window_closing(self) -> None:
        """窗口关闭处理"""
        try:
            # 保存所有未保存的内容
            QTimer.singleShot(0, lambda: self._run_async_save_before_exit())
        except Exception as e:
            logger.error(f"关闭前保存失败: {e}")

    async def _save_before_exit(self) -> None:
        """退出前保存"""
        try:
            # 保存文档
            if self.document_service.has_open_documents:
                await self.document_service.save_all_documents()

            # 保存项目
            if self.project_service.has_current_project:
                await self.project_service.save_current_project()

            # 关闭应用服务
            self.app_service.shutdown()

        except Exception as e:
            logger.error(f"退出前保存失败: {e}")

    # ========================================================================
    # 辅助方法
    # ========================================================================

    # 移除重复的_show_error方法定义，使用后面的线程安全版本

    def _show_warning(self, title: str, message: str) -> None:
        """显示警告消息"""
        if self._main_window:
            QMessageBox.warning(self._main_window, title, message)

    def _show_info(self, title: str, message: str) -> None:
        """显示信息消息"""
        if self._main_window:
            QMessageBox.information(self._main_window, title, message)

    # ========================================================================
    # 查找替换处理
    # ========================================================================

    def _on_find_requested(self, search_text: str, options: dict):
        """处理查找请求"""
        try:
            if self._main_window and self._main_window.editor_widget:
                current_tab = self._main_window.editor_widget.get_current_tab()
                if current_tab:
                    found = current_tab.find_text(
                        search_text,
                        options.get("case_sensitive", False)
                    )

                    if not found and options.get("wrap_search", True):
                        # 从头开始搜索
                        cursor = current_tab.text_edit.textCursor()
                        cursor.movePosition(cursor.MoveOperation.Start)
                        current_tab.text_edit.setTextCursor(cursor)
                        found = current_tab.find_text(search_text, options.get("case_sensitive", False))

                    if not found:
                        self.status_message.emit(f"未找到 '{search_text}'")
                    else:
                        self.status_message.emit(f"找到 '{search_text}'")

        except Exception as e:
            logger.error(f"查找失败: {e}")
            self._show_error("查找失败", str(e))

    def _on_replace_requested(self, find_text: str, replace_text: str, options: dict):
        """处理替换请求"""
        try:
            if self._main_window and self._main_window.editor_widget:
                current_tab = self._main_window.editor_widget.get_current_tab()
                if current_tab:
                    selected_text = current_tab.get_selected_text()

                    # 检查选中的文本是否匹配
                    if selected_text == find_text or (
                        not options.get("case_sensitive", False) and
                        selected_text.lower() == find_text.lower()
                    ):
                        current_tab.replace_selected_text(replace_text)
                        self.status_message.emit(f"已替换 '{find_text}' 为 '{replace_text}'")

                        # 查找下一个
                        self._on_find_requested(find_text, options)
                    else:
                        # 先查找
                        self._on_find_requested(find_text, options)

        except Exception as e:
            logger.error(f"替换失败: {e}")
            self._show_error("替换失败", str(e))

    def _on_replace_all_requested(self, find_text: str, replace_text: str, options: dict):
        """处理全部替换请求"""
        try:
            if self._main_window and self._main_window.editor_widget:
                current_tab = self._main_window.editor_widget.get_current_tab()
                if current_tab:
                    count = current_tab.replace_text(
                        find_text,
                        replace_text,
                        options.get("case_sensitive", False)
                    )

                    if count > 0:
                        self.status_message.emit(f"已替换 {count} 处 '{find_text}' 为 '{replace_text}'")
                    else:
                        self.status_message.emit(f"未找到 '{find_text}'")

        except Exception as e:
            logger.error(f"全部替换失败: {e}")
            self._show_error("全部替换失败", str(e))

    def _on_settings_changed(self, setting_key: str, value):
        """设置变更处理"""
        try:
            logger.info(f"设置已变更: {setting_key} = {value}")
            # 这里可以根据具体设置进行相应的处理

        except Exception as e:
            logger.error(f"处理设置变更失败: {e}")

    def _on_theme_changed(self, theme_name: str):
        """主题变更处理"""
        try:
            logger.info(f"主题已变更: {theme_name}")
            # 应用主题变更
            if hasattr(self._main_window, 'theme_manager'):
                from src.presentation.styles.theme_manager import ThemeType
                theme_map = {"浅色主题": ThemeType.LIGHT, "深色主题": ThemeType.DARK, "自动": ThemeType.AUTO}
                theme_type = theme_map.get(theme_name, ThemeType.LIGHT)
                self._main_window.theme_manager.set_theme(theme_type)

        except Exception as e:
            logger.error(f"处理主题变更失败: {e}")

    def show_template_manager(self) -> None:
        """显示模板管理器"""
        try:
            if not self._template_manager_dialog:
                from src.application.services.template_service import TemplateService
                template_service = TemplateService()

                self._template_manager_dialog = TemplateManagerDialog(
                    template_service,
                    self._main_window
                )
                self._template_manager_dialog.template_applied.connect(self._on_template_applied)

            self._template_manager_dialog.show()
            self._template_manager_dialog.raise_()
            self._template_manager_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示模板管理器失败: {e}")
            self._show_error("模板管理器", f"无法显示模板管理器: {e}")

    def _on_template_applied(self, content: str):
        """模板应用处理"""
        try:
            if self._main_window and self._main_window.editor_widget:
                current_tab = self._main_window.editor_widget.get_current_tab()
                if current_tab:
                    # 在当前光标位置插入模板内容
                    cursor = current_tab.text_edit.textCursor()
                    cursor.insertText(content)

                    self.status_message.emit("模板已应用到编辑器")
                else:
                    self._show_warning("应用模板", "请先打开一个文档")

        except Exception as e:
            logger.error(f"应用模板失败: {e}")
            self._show_error("应用模板失败", str(e))

    def show_plugin_manager(self) -> None:
        """显示插件管理器"""
        try:
            if not self._plugin_manager_dialog:
                # 获取插件管理器
                plugin_manager = None
                if hasattr(self, 'container') and self.container:
                    from src.shared.plugins.plugin_manager import PluginManager
                    plugin_manager = self.container.get(PluginManager)

                if not plugin_manager:
                    self._show_warning("插件管理器", "插件管理器不可用")
                    return

                self._plugin_manager_dialog = PluginManagerDialog(
                    plugin_manager,
                    self._main_window
                )

            self._plugin_manager_dialog.show()
            self._plugin_manager_dialog.raise_()
            self._plugin_manager_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示插件管理器失败: {e}")
            self._show_error("插件管理器", f"无法显示插件管理器: {e}")

    def show_character_manager(self) -> None:
        """显示角色管理器"""
        try:
            if not self.project_service.has_current_project:
                self._show_warning("角色管理器", "请先打开一个项目")
                return

            if not self._character_manager_dialog:
                from src.presentation.dialogs.character_manager_dialog import CharacterManagerDialog
                self._character_manager_dialog = CharacterManagerDialog(
                    project_id=self.project_service.current_project.id,
                    parent=self._main_window
                )

                # 连接信号
                self._character_manager_dialog.character_created.connect(self._on_character_created)
                self._character_manager_dialog.character_updated.connect(self._on_character_updated)
                self._character_manager_dialog.character_deleted.connect(self._on_character_deleted)

            self._character_manager_dialog.show()
            self._character_manager_dialog.raise_()
            self._character_manager_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示角色管理器失败: {e}")
            self._show_error("角色管理器", f"无法显示角色管理器: {e}")

    def _on_character_created(self, character_id: str):
        """角色创建事件处理"""
        try:
            logger.info(f"角色创建成功: {character_id}")
            self.status_message.emit("角色创建成功")

        except Exception as e:
            logger.error(f"处理角色创建事件失败: {e}")

    def _on_character_updated(self, character_id: str):
        """角色更新事件处理"""
        try:
            logger.info(f"角色更新成功: {character_id}")
            self.status_message.emit("角色更新成功")

        except Exception as e:
            logger.error(f"处理角色更新事件失败: {e}")

    def _on_character_deleted(self, character_id: str):
        """角色删除事件处理"""
        try:
            logger.info(f"角色删除成功: {character_id}")
            self.status_message.emit("角色删除成功")

        except Exception as e:
            logger.error(f"处理角色删除事件失败: {e}")

    def show_backup_manager(self) -> None:
        """显示备份管理器"""
        try:
            if not self.project_service.has_current_project:
                self._show_warning("备份管理器", "请先打开一个项目")
                return

            if not self._backup_manager_dialog:
                from src.presentation.dialogs.backup_manager_dialog import BackupManagerDialog
                from src.application.services.backup_service import BackupService

                # 创建备份服务
                backup_service = BackupService(
                    project_repository=self.project_repository,
                    document_repository=self.document_repository,
                    backup_dir=Path.home() / "AI小说编辑器" / "backups"
                )

                self._backup_manager_dialog = BackupManagerDialog(
                    backup_service=backup_service,
                    project_id=self.project_service.current_project.id,
                    parent=self._main_window
                )

                # 连接信号
                self._backup_manager_dialog.backup_created.connect(self._on_backup_created)
                self._backup_manager_dialog.backup_restored.connect(self._on_backup_restored)
                self._backup_manager_dialog.version_created.connect(self._on_version_created)

            self._backup_manager_dialog.show()
            self._backup_manager_dialog.raise_()
            self._backup_manager_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示备份管理器失败: {e}")
            self._show_error("备份管理器", f"无法显示备份管理器: {e}")

    def _on_backup_created(self, backup_id: str):
        """备份创建事件处理"""
        try:
            logger.info(f"备份创建成功: {backup_id}")
            self.status_message.emit("备份创建成功")

        except Exception as e:
            logger.error(f"处理备份创建事件失败: {e}")

    def _on_backup_restored(self, project_id: str):
        """备份恢复事件处理"""
        try:
            logger.info(f"备份恢复成功: {project_id}")
            self.status_message.emit("备份恢复成功")

            # 重新加载项目
            self.project_opened.emit(project_id)

        except Exception as e:
            logger.error(f"处理备份恢复事件失败: {e}")

    def _on_version_created(self, version_id: str):
        """版本创建事件处理"""
        try:
            logger.info(f"版本创建成功: {version_id}")
            self.status_message.emit("版本创建成功")

        except Exception as e:
            logger.error(f"处理版本创建事件失败: {e}")

    def show_find_replace(self) -> None:
        """显示查找替换对话框"""
        self._show_find_replace_dialog(tab_index=0)



    def _on_project_wizard_completed(self, project_info: dict):
        """项目向导完成处理"""
        try:
            logger.info(f"项目向导完成，创建项目: {project_info['name']}")

            # 映射项目类型
            type_map = {
                "小说": ProjectType.NOVEL,
                "散文": ProjectType.ESSAY,
                "诗歌": ProjectType.POETRY,
                "剧本": ProjectType.SCRIPT,
                "其他": ProjectType.OTHER
            }
            project_type = type_map.get(project_info.get("type", "小说"), ProjectType.NOVEL)

            # 统一走集中入口，避免多套实现造成不一致
            self.create_project_via_service(project_info)

        except Exception as e:
            logger.error(f"处理项目向导完成失败: {e}")
            self._show_error("创建项目失败", str(e))






    def _on_project_creation_complete(self, project, project_info: dict):
        """项目创建完成回调"""
        try:
            logger.info(f"项目创建完成回调被调用，项目: {project}")

            if project:
                # 项目创建成功，立即发送信号（在主线程中）
                logger.info(f"🎯 立即发送项目打开信号: {project.title}")
                self.project_opened.emit(project)
                logger.info(f"项目打开信号已发送: {project.title}")

                # 状态消息由 ProjectController 发送，避免重复
                logger.info(f"新建项目已自动打开: {project.title} ({project.id})")

                # 显示成功消息
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._show_project_creation_success(project_info))
            else:
                logger.error("项目创建返回空值")
                self._show_error("创建项目失败", "项目创建过程中出现未知错误")

        except Exception as e:
            logger.error(f"项目创建完成回调失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._show_error("创建项目失败", str(e))

    def _on_project_creation_error_simple(self, project_info: dict, error: Exception):
        """项目创建失败回调"""
        try:
            logger.error(f"项目创建失败: {project_info.get('name', 'Unknown')}, {error}")
            self._show_error("创建项目失败", str(error))

        except Exception as e:
            logger.error(f"项目创建失败回调失败: {e}")






    def _emit_project_opened_signal(self, project):
        """发送项目打开信号"""
        try:
            logger.info(f"🎯 发送项目打开信号: {project.title}")
            self.project_opened.emit(project)
            # 状态消息由 ProjectController 发送，避免重复
            logger.info(f"项目打开信号已发送: {project.title}")

        except Exception as e:
            logger.error(f"发送项目打开信号失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _show_project_creation_success(self, project_info: dict):
        """线程安全的项目创建成功消息显示"""
        try:
            # 确保在主线程中执行
            from src.shared.utils.thread_safety import is_main_thread
            if not is_main_thread():
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(10, lambda: self._show_project_creation_success(project_info))
                return

            # 在主线程中显示消息框
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self._main_window,
                "项目创建成功",
                f"项目 '{project_info['name']}' 已成功创建！\n\n"
                f"你可以开始在左侧项目树中创建文档，\n"
                f"或使用右侧的AI助手来辅助创作。"
            )

        except Exception as e:
            logger.error(f"显示项目创建成功消息失败: {e}")

    async def _create_template_documents(self, project, template_name: str):
        """根据模板创建初始文档"""
        try:
            from src.domain.entities.document import DocumentType

            if template_name == "长篇小说":
                # 创建人物设定
                await self.document_service.create_document(
                    title="人物设定",
                    project_id=project.id,
                    document_type=DocumentType.CHARACTER,
                    content="# 主要人物\n\n## 主角\n姓名：\n年龄：\n性格：\n背景：\n\n## 配角\n..."
                )

                # 创建大纲
                await self.document_service.create_document(
                    title="故事大纲",
                    project_id=project.id,
                    document_type=DocumentType.OUTLINE,
                    content="# 故事大纲\n\n## 主线情节\n\n## 支线情节\n\n## 章节安排\n..."
                )

                # 创建第一章
                await self.document_service.create_document(
                    title="第一章",
                    project_id=project.id,
                    document_type=DocumentType.CHAPTER,
                    content="# 第一章\n\n故事从这里开始..."
                )

            elif template_name == "短篇小说":
                # 创建大纲
                await self.document_service.create_document(
                    title="故事大纲",
                    project_id=project.id,
                    document_type=DocumentType.OUTLINE,
                    content="# 故事大纲\n\n## 故事梗概\n\n## 人物关系\n\n## 情节发展\n..."
                )

                # 创建正文
                await self.document_service.create_document(
                    title="正文",
                    project_id=project.id,
                    document_type=DocumentType.CHAPTER,
                    content="故事开始..."
                )

            elif template_name == "剧本":
                # 创建人物表
                await self.document_service.create_document(
                    title="人物表",
                    project_id=project.id,
                    document_type=DocumentType.CHARACTER,
                    content="# 人物表\n\n## 主要人物\n\n## 次要人物\n..."
                )

                # 创建第一幕
                await self.document_service.create_document(
                    title="第一幕",
                    project_id=project.id,
                    document_type=DocumentType.CHAPTER,
                    content="# 第一幕\n\n时间：\n地点：\n\n[幕启]\n\n..."
                )

            # 其他模板可以继续添加...

            logger.info(f"模板文档创建完成: {template_name}")

        except Exception as e:
            logger.error(f"创建模板文档失败: {e}")

    # ========================================================================
    # 异步操作包装方法
    # ========================================================================

    def _run_async_open_project(self, file_path: Path):
        """运行异步打开项目操作（委派至项目控制器）"""
        self._run_async_task(
            self.project_controller.open_project_by_path(file_path),
            success_callback=lambda _: logger.info(f"项目打开成功: {file_path}"),
            error_callback=lambda e: self._show_error("打开项目失败", str(e))
        )

    def _run_async_open_project_dir(self, project_dir: Path):
        """运行异步打开项目目录操作"""
        try:
            # 添加超时保护，防止卡死
            import asyncio

            async def open_with_timeout():
                try:
                    # 设置10秒超时
                    await asyncio.wait_for(
                        self._open_project_dir_async(project_dir),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    error_msg = f"打开项目目录超时：\n{project_dir}\n\n操作已取消"
                    logger.warning(error_msg)
                    self._show_error("打开项目超时", error_msg)
                    raise

            # 使用统一的异步执行器
            self._run_async_task(
                open_with_timeout(),
                success_callback=lambda _: logger.info(f"项目目录打开完成: {project_dir}"),
                error_callback=lambda e: self._handle_project_open_error(project_dir, e)
            )

        except Exception as e:
            logger.error(f"启动打开项目目录失败: {e}")
            self._show_error("打开项目失败", str(e))

    def _handle_project_open_error(self, project_dir: Path, error: Exception):
        """处理项目打开错误"""
        try:
            if "TimeoutError" in str(type(error)):
                # 超时错误已经在上面处理了
                return

            error_msg = f"打开项目目录失败：\n{project_dir}\n\n错误: {error}"
            logger.error(error_msg)
            self._show_error("打开项目失败", error_msg)

        except Exception as e:
            logger.error(f"处理项目打开错误失败: {e}")

    def _run_async_refresh_project_tree(self, project, project_tree_widget):
        """运行异步项目树刷新操作（修复版）"""
        try:
            # 使用统一的异步任务执行器，避免直接创建任务
            self._run_async_task(
                self._refresh_project_tree_async(project, project_tree_widget),
                success_callback=lambda _: logger.debug(f"项目树异步刷新完成: {project.title}"),
                error_callback=lambda e: self._handle_refresh_error(e, project, project_tree_widget)
            )

        except Exception as e:
            logger.error(f"启动异步刷新项目树失败: {e}")
            # 备用方案：同步刷新
            self._fallback_refresh_project_tree(project, project_tree_widget)

    def _handle_refresh_error(self, error, project, project_tree_widget):
        """处理项目树刷新错误"""
        logger.error(f"异步刷新项目树失败: {error}")
        # 备用方案：同步刷新
        self._fallback_refresh_project_tree(project, project_tree_widget)

    def _fallback_refresh_project_tree(self, project, project_tree_widget):
        """备用的项目树刷新方案"""
        try:
            project_tree_widget.load_project(project, [])
            logger.debug(f"项目树备用刷新完成: {project.title}")
        except Exception as e:
            logger.error(f"项目树备用刷新也失败: {e}")

    async def _refresh_project_tree_async(self, project, project_tree_widget):
        """异步刷新项目树"""
        try:
            # 获取项目的所有文档
            documents = await self.document_service.list_documents_by_project(project.id)

            # 在主线程中刷新项目树
            project_tree_widget.load_project(project, documents)
            logger.debug(f"项目树异步刷新完成: {project.title}, {len(documents)} 个文档")
        except Exception as e:
            logger.error(f"异步刷新项目树失败: {e}")
            # 备用方案
            project_tree_widget.load_project(project, [])


    def _run_async_open_document(self, document_id: str):
        """运行异步打开文档操作"""
        def success_callback(document):
            try:
                self._on_document_opened_success(document, document_id)
            finally:
                # 清理打开状态
                self._opening_documents.discard(document_id)

        def error_callback(e):
            try:
                self._show_error("打开文档失败", str(e))
            finally:
                # 清理打开状态
                self._opening_documents.discard(document_id)

        # 委派至文档控制器
        self._run_async_task(
            self.document_controller.open_document(document_id),
            success_callback=success_callback,
            error_callback=error_callback
        )

    def _on_document_opened_success(self, document, document_id: str):
        """文档打开成功回调（在主线程中执行）"""
        try:
            # 检查是否在主线程中
            from src.shared.utils.thread_safety import is_main_thread
            if not is_main_thread():
                logger.warning("文档打开回调不在主线程中，重新调度到主线程")
                # 使用QTimer确保在主线程中执行
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._on_document_opened_success(document, document_id))
                return

            if document and self._main_window:
                logger.info(f"在主线程中加载文档到编辑器: {document.title}")
                # 在主线程中安全地加载文档到编辑器
                self._main_window.editor_widget.load_document(document)
                logger.info(f"文档打开成功: {document_id}")
            elif document:
                logger.warning(f"文档打开成功但主窗口不可用: {document_id}")
            else:
                # 文档为None，说明文档不存在，但不需要重复警告
                # 因为document_service已经记录了警告
                logger.debug(f"文档打开失败，文档不存在: {document_id}")
        except Exception as e:
            logger.error(f"文档打开成功回调失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # 移除重复的_run_async_save_before_exit方法定义

    def _show_error(self, title: str, message: str):
        """显示错误消息（线程安全）"""
        try:
            # 限制错误消息长度
            if len(message) > ERROR_MESSAGE_MAX_LENGTH:
                message = message[:ERROR_MESSAGE_MAX_LENGTH] + "..."

            # 确保在主线程中显示错误消息
            from src.shared.utils.thread_safety import is_main_thread
            if not is_main_thread():
                self.async_manager.execute_delayed(
                    self._show_error,
                    UI_IMMEDIATE_DELAY,
                    title,
                    message
                )
                return

            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self._main_window if hasattr(self, '_main_window') else None, title, message)

        except Exception as e:
            logger.error(f"显示错误消息失败: {e}")
            # 备用方案：直接记录到日志
            logger.error(f"错误消息 - {title}: {message}")

    def _show_success_message(self, title: str, message: str):
        """显示成功消息（线程安全）"""
        try:
            # 确保在主线程中显示成功消息
            from src.shared.utils.thread_safety import is_main_thread
            if not is_main_thread():
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._show_success_message(title, message))
                return

            from PyQt6.QtWidgets import QMessageBox
            msg_box = QMessageBox(self._main_window if hasattr(self, '_main_window') else None)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        except Exception as e:
            logger.error(f"显示成功消息失败: {e}")
            # 备用方案：直接记录到日志
            logger.info(f"成功消息 - {title}: {message}")

    # ========================================================================
    # 编辑操作方法
    # ========================================================================

    @controller_error_handler("撤销操作", show_user_error=False)
    def undo(self) -> None:
        """撤销操作"""
        self._execute_editor_operation('undo', "撤销")

    @controller_error_handler("重做操作", show_user_error=False)
    def redo(self) -> None:
        """重做操作"""
        self._execute_editor_operation('redo', "重做")

    @controller_error_handler("剪切操作", show_user_error=False)
    def cut(self) -> None:
        """剪切操作"""
        self._execute_editor_operation('cut', "剪切")

    @controller_error_handler("复制操作", show_user_error=False)
    def copy(self) -> None:
        """复制操作"""
        self._execute_editor_operation('copy', "复制")

    @controller_error_handler("粘贴操作", show_user_error=False)
    def paste(self) -> None:
        """粘贴操作"""
        self._execute_editor_operation('paste', "粘贴")

    @controller_error_handler("查找操作")
    def find(self) -> None:
        """查找操作"""
        self.show_find_dialog()

    @controller_error_handler("替换操作")
    def replace(self) -> None:
        """替换操作"""
        self.show_replace_dialog()

    def _execute_editor_operation(self, operation: str, operation_name: str) -> None:
        """执行编辑器操作的通用方法"""
        if not (hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget):
            logger.warning(f"编辑器不可用，无法执行{operation_name}操作")
            return

        if hasattr(self._main_window.editor_widget, operation):
            getattr(self._main_window.editor_widget, operation)()
        else:
            logger.warning(f"编辑器不支持{operation_name}操作")

    # ========================================================================
    # 视图操作方法
    # ========================================================================

    def toggle_syntax_highlighting(self) -> None:
        """切换语法高亮"""
        try:
            if hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget:
                if hasattr(self._main_window.editor_widget, 'toggle_syntax_highlighting'):
                    self._main_window.editor_widget.toggle_syntax_highlighting()
                else:
                    logger.warning("编辑器不支持语法高亮切换")
        except Exception as e:
            logger.error(f"切换语法高亮失败: {e}")

    # ========================================================================
    # AI功能方法
    # ========================================================================

    def ai_analyze_characters(self) -> None:
        """AI角色分析"""
        try:
            # 获取当前项目
            if not self.project_service.has_current_project:
                self._show_warning("提示", "请先打开一个项目")
                return

            # 切换到AI面板的角色分析模式
            if hasattr(self._main_window, 'global_ai_panel'):
                if hasattr(self._main_window.global_ai_panel, 'switch_to_character_analysis'):
                    self._main_window.global_ai_panel.switch_to_character_analysis()

                    # 确保AI面板可见
                    if hasattr(self._main_window, 'dock_builder'):
                        self._main_window.dock_builder.show_dock("right_tabs")
                else:
                    self._show_warning("提示", "AI角色分析功能暂未实现")
            else:
                self._show_warning("提示", "AI面板未初始化")

        except Exception as e:
            logger.error(f"AI角色分析失败: {e}")
            self._show_error("错误", f"AI角色分析失败: {e}")

    # ========================================================================
    # 工具功能方法
    # ========================================================================



    def backup_management(self) -> None:
        """备份管理"""
        try:
            self.show_backup_manager()
        except Exception as e:
            logger.error(f"打开备份管理失败: {e}")
            self._show_error("错误", f"打开备份管理失败: {e}")

    def settings(self) -> None:
        """打开设置对话框"""
        try:
            self.show_settings()
        except Exception as e:
            logger.error(f"打开设置对话框失败: {e}")
            self._show_error("错误", f"打开设置对话框失败: {e}")

    def about(self) -> None:
        """显示关于对话框"""
        try:
            self.show_about()
        except Exception as e:
            logger.error(f"显示关于对话框失败: {e}")
            self._show_error("错误", f"显示关于对话框失败: {e}")

    @property
    def main_window(self):
        """获取主窗口引用"""
        return self._main_window

    @property
    def current_project(self):
        """获取当前项目"""
        return self.project_service.current_project if self.project_service.has_current_project else None

    # ========================================================================
    # 缺失的辅助方法
    # ========================================================================






    def _run_async_save_before_exit(self):
        """运行异步退出前保存操作"""
        self._run_async_task(
            self._save_before_exit(),
            success_callback=lambda _: logger.info("退出前保存完成"),
            error_callback=lambda e: logger.error(f"异步退出前保存失败: {e}")
        )

    def _run_async_new_document(self, title: str):
        """运行异步新建文档操作"""
        self._run_async_task(
            self._new_document_async(title),
            success_callback=lambda _: logger.info(f"新建文档成功: {title}"),
            error_callback=lambda e: self._show_error("新建文档失败", str(e))
        )

    # 重复的方法已删除，使用第一个更完整的版本

    def _on_project_creation_finished(self, project):
        """项目创建完成回调"""
        if project:
            self.project_opened.emit(project)
            logger.info(f"项目创建完成: {project.title}")

    def _on_settings_changed(self, settings_dict):
        """设置变更回调"""
        logger.info("设置已更新")
        self.status_message.emit("设置已保存")

    def _on_theme_changed(self, theme_name):
        """主题变更回调"""
        logger.info(f"主题已切换到: {theme_name}")
        self.status_message.emit(f"主题已切换: {theme_name}")

    def settings(self) -> None:
        """打开设置对话框"""
        try:
            from src.presentation.dialogs.settings_dialog import SettingsDialog

            dialog = SettingsDialog(self.settings_service, self._main_window)
            dialog.settings_changed.connect(self._on_settings_changed)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                logger.info("设置对话框已确认")
                self.status_message.emit("设置已保存")
            else:
                logger.info("设置对话框已取消")

        except Exception as e:
            logger.error(f"打开设置对话框失败: {e}")
            self._show_error("设置错误", f"无法打开设置对话框: {e}")

    # ========================================================================
    # 事件处理方法
    # ========================================================================

    def _on_document_created(self, event: DocumentCreatedEvent) -> None:
        """处理文档创建事件
        兼容两种来源：
        - 事件总线发送的 DocumentCreatedEvent
        - DocumentController.document_created 信号发送的 Document 实体
        """
        try:
            from src.domain.events.document_events import DocumentCreatedEvent as DCEvent
            # 归一化为 DocumentCreatedEvent
            if hasattr(event, 'document_title') and hasattr(event, 'document_id'):
                normalized = event
            else:
                # 认为是 Document 实体或 dict
                title = getattr(event, 'title', None)
                if title is None and isinstance(event, dict):
                    title = event.get('title')
                doc_id = getattr(event, 'document_id', None) or getattr(event, 'id', None)
                doc_type = getattr(event, 'document_type', None) or getattr(event, 'type', None)
                # 规范化类型
                from src.domain.entities.document import DocumentType
                if isinstance(doc_type, str):
                    try:
                        type_enum = DocumentType[doc_type.upper()]
                    except Exception:
                        try:
                            type_enum = DocumentType(doc_type)
                        except Exception:
                            type_enum = DocumentType.CHAPTER
                elif isinstance(doc_type, DocumentType):
                    type_enum = doc_type
                else:
                    type_enum = DocumentType.CHAPTER
                # 项目ID尽量从当前项目读取
                project_id = getattr(event, 'project_id', None)
                if project_id is None and hasattr(self, 'project_service') and getattr(self.project_service, 'has_current_project', False):
                    project_id = self.project_service.current_project.id
                normalized = DCEvent(
                    document_id=str(doc_id or ""),
                    document_title=str(title or ""),
                    document_type=type_enum,
                    project_id=project_id
                )

            logger.info(f"🎯 收到文档创建事件: {normalized.document_title} ({normalized.document_type.value}) - 文档ID: {normalized.document_id}")

            # 检查是否是重复事件
            if hasattr(self, '_processed_document_events'):
                if normalized.document_id in self._processed_document_events:
                    logger.warning(f"⚠️ 重复的文档创建事件，跳过处理: {normalized.document_title} ({normalized.document_id})")
                    return
                self._processed_document_events.add(normalized.document_id)
            else:
                self._processed_document_events = {normalized.document_id}

            # 立即刷新项目树以显示新文档
            self._refresh_project_tree_for_new_document(normalized)

            # 清除文档列表缓存
            self._clear_document_cache()

            logger.info(f"✅ 文档创建事件处理完成: {normalized.document_title}")

        except Exception as e:
            logger.error(f"❌ 处理文档创建事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _on_document_saved(self, event: DocumentSavedEvent | str) -> None:
        """处理文档保存事件（兼容旧签名）"""
        try:
            if isinstance(event, str):
                logger.debug(f"📝 收到文档保存事件: {event}")
            else:
                logger.debug(f"📝 收到文档保存事件: {event.document_title}")
        except Exception as e:
            logger.error(f"❌ 处理文档保存事件失败: {e}")

    def _on_document_closed(self, document_id: str) -> None:
        try:
            logger.info(f"📕 文档已关闭: {document_id}")
        except Exception:
            pass

    def _on_document_deleted(self, document_id: str) -> None:
        try:
            logger.info(f"🗑️ 文档已删除: {document_id}")
            # 刷新项目树
            self.schedule_refresh_project_tree()
            # 若编辑器可用，关闭对应标签
            if hasattr(self, '_main_window') and self._main_window and hasattr(self._main_window, 'editor_widget'):
                editor = self._main_window.editor_widget
                if hasattr(editor, 'close_document'):
                    editor.close_document(document_id)
        except Exception as e:
            logger.warning(f"处理文档删除信号时出现问题: {e}")

    def _on_document_opened_event(self, event):
        """从 DocumentController 接收 DocumentOpenedEvent，桥接到 UI 仍用文档对象"""
        try:
            # 从服务获取文档对象
            doc_id = getattr(event, 'document_id', None) or getattr(event, 'id', None)
            document = None
            if doc_id:
                try:
                    # 在主线程调度 UI 更新
                    self._run_async_task(
                        self.document_service.open_document(doc_id),
                        success_callback=lambda doc: self._on_document_opened_success(doc, doc_id)
                    )
                    return
                except Exception:
                    document = None
            # 若无法获取，直接转发事件对象
            self.document_opened.emit(event)
        except Exception as e:
            logger.error(f"处理 DocumentOpenedEvent 失败: {e}")

    def _on_document_closed_event(self, event):
        try:
            doc_id = getattr(event, 'document_id', None) or getattr(event, 'id', None)
            if doc_id:
                self._on_document_closed(doc_id)
            else:
                logger.debug("DocumentClosedEvent 缺少 document_id")
        except Exception as e:
            logger.error(f"处理 DocumentClosedEvent 失败: {e}")

    def _on_document_deleted_event(self, event):
        try:
            doc_id = getattr(event, 'document_id', None) or getattr(event, 'id', None)
            if doc_id:
                self._on_document_deleted(doc_id)
            else:
                logger.debug("DocumentDeletedEvent 缺少 document_id")
        except Exception as e:
            logger.error(f"处理 DocumentDeletedEvent 失败: {e}")

    def _on_document_renamed_event(self, event):
        try:
            doc_id = getattr(event, 'document_id', None) or getattr(event, 'id', None)
            new_title = getattr(event, 'new_title', None)
            if doc_id and new_title is not None:
                self._on_document_renamed(doc_id, new_title)
            else:
                logger.debug("DocumentTitleChangedEvent 缺少字段")
        except Exception as e:
            logger.error(f"处理 DocumentTitleChangedEvent 失败: {e}")

            logger.error(f"❌ 处理文档保存事件失败: {e}")

    def _refresh_project_tree_for_new_document(self, event: DocumentCreatedEvent) -> None:
        """为新文档刷新项目树"""
        try:
            if not self._main_window or not hasattr(self._main_window, 'project_tree'):
                logger.warning("主窗口或项目树不可用")
                return

            # 检查是否是当前项目的文档
            if (hasattr(self, 'project_service') and
                self.project_service.has_current_project and
                event.project_id == self.project_service.current_project.id):

                logger.info(f"🔄 刷新项目树以显示新文档: {event.document_title}")

                # 使用延迟刷新，确保文档已完全保存
                self.schedule_refresh_project_tree(100)

            else:
                logger.debug(f"文档不属于当前项目，跳过刷新: {event.project_id}")

        except Exception as e:
            logger.error(f"❌ 为新文档刷新项目树失败: {e}")

    def schedule_refresh_project_tree(self, delay_ms: int = 200) -> None:
        """统一的项目树刷新调度入口（带节流，确保在主线程）"""
        try:
            # 若不在主线程，转到主线程后再调度
            try:
                from src.shared.utils.thread_safety import is_main_thread
                if not is_main_thread():
                    from src.shared.utils.async_manager import get_async_manager
                    get_async_manager().callback_signal.emit(lambda: self.schedule_refresh_project_tree(delay_ms))
                    return
            except Exception:
                pass

            # 如果已有定时器在运行，取消它
            if self._refresh_timer and self._refresh_timer.isActive():
                self._refresh_timer.stop()

            # 标记有待刷新
            self._pending_refresh = True

            # 创建新的定时器（绑定到主控制器线程）
            if not self._refresh_timer:
                self._refresh_timer = QTimer(self)
                self._refresh_timer.setSingleShot(True)
                self._refresh_timer.timeout.connect(self._execute_pending_refresh)

            # 启动定时器
            self._refresh_timer.start(delay_ms)
            logger.debug(f"项目树刷新已调度，延迟 {delay_ms}ms")

        except Exception as e:
            logger.error(f"调度项目树刷新失败: {e}")
            # 备用方案：立即刷新
            self._immediate_refresh_project_tree()

    def _execute_pending_refresh(self) -> None:
        """执行待处理的项目树刷新"""
        try:
            if self._pending_refresh:
                self._pending_refresh = False
                self._immediate_refresh_project_tree()
                logger.debug("执行了节流的项目树刷新")
        except Exception as e:
            logger.error(f"执行项目树刷新失败: {e}")

    def refresh_project_tree(self) -> None:
        """供外部触发的项目树刷新入口（MainWindow回调使用）"""
        try:
            self._immediate_refresh_project_tree()
        except Exception as e:
            logger.error(f"刷新项目树失败: {e}")
    def _on_document_renamed(self, document_id: str, new_title: str) -> None:
        try:
            logger.info(f"✏️ 文档重命名事件: {document_id} -> {new_title}")
            # 刷新项目树
            self.schedule_refresh_project_tree()
            # 更新编辑器页签标题
            if hasattr(self, '_main_window') and self._main_window and hasattr(self._main_window, 'editor_widget'):
                editor = self._main_window.editor_widget
                if hasattr(editor, 'rename_document_tab'):
                    editor.rename_document_tab(document_id, new_title)
        except Exception as e:
            logger.warning(f"处理文档重命名信号时出现问题: {e}")


    def _immediate_refresh_project_tree(self) -> None:
        """立即刷新项目树"""
        try:
            if (hasattr(self, 'project_service') and
                self.project_service.has_current_project):

                current_project = self.project_service.current_project
                logger.info(f"🌳 立即刷新项目树: {current_project.title}")

                # 使用异步方式获取最新的文档列表并刷新
                self._run_async_task(
                    self.document_service.list_documents_by_project(current_project.id),
                    success_callback=lambda docs: self._update_project_tree_with_new_documents(current_project, docs),
                    error_callback=lambda e: logger.error(f"获取文档列表失败: {e}")
                )

        except Exception as e:
            logger.error(f"❌ 立即刷新项目树失败: {e}")

    def _update_project_tree_with_new_documents(self, project, documents) -> None:
        """使用新文档更新项目树"""
        try:
            if self._main_window and hasattr(self._main_window, 'project_tree'):
                logger.info(f"📋 更新项目树文档: {len(documents)} 个文档")

                # 重新加载项目树
                self._main_window.project_tree.load_project(project, documents)

                logger.info(f"✅ 项目树已更新显示新文档")

        except Exception as e:
            logger.error(f"❌ 更新项目树文档失败: {e}")

    def _clear_document_cache(self) -> None:
        """清除文档缓存"""
        try:
            # 清除文档仓储中的缓存
            if hasattr(self.document_service, 'document_repository'):
                repo = self.document_service.document_repository

                # 清除旧的缓存（向后兼容）
                if hasattr(repo, '_project_docs_cache'):
                    repo._project_docs_cache.clear()
                    logger.debug("✅ 旧版文档缓存已清除")

                # 清除新的统一缓存管理器
                if hasattr(repo, '_cache_manager'):
                    # 清除所有项目文档缓存
                    cache_manager = repo._cache_manager
                    cache_prefix = getattr(repo, '_cache_prefix', 'file_document_repo')

                    # 清除所有以项目文档前缀开头的缓存
                    if hasattr(cache_manager, 'clear_by_pattern'):
                        cache_manager.clear_by_pattern(f"{cache_prefix}:project_docs:*")
                        logger.debug("✅ 统一缓存管理器中的项目文档缓存已清除")
                    elif hasattr(cache_manager, 'clear'):
                        cache_manager.clear()
                        logger.debug("✅ 统一缓存管理器已完全清除")

        except Exception as e:
            logger.debug(f"清除文档缓存失败: {e}")

    def _on_ai_configuration_changed(self, event):
        """处理AI配置变化事件"""
        try:
            logger.info(f"🔄 主控制器收到AI配置变化: {event.setting_key}")

            # 更新状态栏显示
            if hasattr(self, '_main_window') and self._main_window:
                status_message = f"AI配置已更新: {event.setting_key}"
                self.status_message.emit(status_message)

            # 如果有AI相关的UI组件，可以在这里通知它们更新
            # 例如：更新AI面板的状态、刷新AI服务列表等

        except Exception as e:
            logger.error(f"❌ 处理AI配置变化事件失败: {e}")

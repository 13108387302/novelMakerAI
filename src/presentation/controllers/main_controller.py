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
from src.application.services.settings_service import SettingsService
from src.application.services.search import SearchService
from src.application.services.import_export_service import ImportExportService
from src.application.services.import_export.base import ImportOptions, ExportOptions
from src.domain.entities.project import ProjectType, Project
from src.domain.entities.document import DocumentType
from src.domain.events.document_events import DocumentCreatedEvent, DocumentSavedEvent
from src.shared.utils.logger import get_logger

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
        self.settings_service = settings_service
        self.search_service = search_service
        self.import_export_service = import_export_service
        self.ai_assistant_manager = ai_assistant_manager
        self._status_service = status_service

        # 状态
        self._main_window: Optional['MainWindow'] = None

        # 创建线程安全的回调发射器
        self.callback_emitter = ThreadSafeCallbackEmitter()

        # 异步任务管理
        self._active_tasks = set()  # 跟踪活跃的异步任务

        # 初始化线程池以提高性能
        import concurrent.futures
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="AsyncTask"
        )

        # 对话框
        self._find_replace_dialog: Optional[FindReplaceDialog] = None
        self._settings_dialog: Optional[SettingsDialog] = None
        self._project_wizard: Optional[ProjectWizard] = None
        self._word_count_dialog: Optional[WordCountDialog] = None
        self._template_manager_dialog: Optional[TemplateManagerDialog] = None
        self._plugin_manager_dialog: Optional[PluginManagerDialog] = None
        self._character_manager_dialog = None
        self._backup_manager_dialog = None

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

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=False)
                logger.info("线程池已关闭")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

    def set_main_window(self, main_window: 'MainWindow') -> None:
        """设置主窗口引用"""
        self._main_window = main_window

        # 如果没有注入的状态服务，则使用主窗口的状态服务
        if not self._status_service and hasattr(main_window, 'status_service'):
            self._status_service = main_window.status_service
            logger.info("状态服务引用已设置")

    def _run_async_task(self, coro, success_callback=None, error_callback=None):
        """通用的异步任务执行器（优化版本，使用线程池）"""
        try:
            import asyncio
            import time

            start_time = time.time()

            def run_in_thread():
                loop = None
                try:
                    # 在线程池线程中创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    logger.debug("⚡ 开始执行异步协程")
                    result = loop.run_until_complete(coro)
                    execution_time = time.time() - start_time
                    logger.debug(f"⚡ 异步协程执行完成，耗时: {execution_time:.3f}s")

                    # 使用线程安全的方式执行回调
                    if success_callback:
                        logger.debug("准备执行成功回调")
                        self._safe_callback(lambda res=result: success_callback(res))
                        logger.debug("成功回调已调度")
                    else:
                        logger.debug("没有成功回调")

                except Exception as e:
                    logger.error(f"异步协程执行失败: {e}")
                    # 使用线程安全的方式执行错误回调
                    if error_callback:
                        self._safe_callback(lambda error=e: error_callback(error))
                    else:
                        self._safe_callback(lambda error=e: logger.error(f"异步任务执行失败: {error}"))
                finally:
                    # 确保事件循环正确关闭
                    if loop and not loop.is_closed():
                        try:
                            # 取消所有未完成的任务
                            pending = asyncio.all_tasks(loop)
                            for task in pending:
                                task.cancel()

                            # 等待任务取消完成
                            if pending:
                                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception as cleanup_error:
                            logger.warning(f"清理异步任务时出错: {cleanup_error}")
                        finally:
                            loop.close()

            # 使用线程池执行，减少线程创建开销
            future = self._thread_pool.submit(run_in_thread)
            # 不等待完成，让任务在后台运行

        except Exception as e:
            logger.error(f"启动异步任务失败: {e}")
            if error_callback:
                error_callback(e)
            else:
                self._show_error("操作失败", str(e))

    def _safe_callback(self, callback):
        """线程安全的回调执行"""
        try:
            logger.info("开始执行安全回调")
            # 检查是否在主线程中
            from src.shared.utils.thread_safety import is_main_thread
            if is_main_thread():
                logger.info("在主线程中，直接执行回调")
                # 直接执行
                callback()
            else:
                logger.info("不在主线程中，使用信号槽机制切换到主线程")
                # 使用信号槽机制切换到主线程
                self.callback_emitter.emit_callback(callback)

        except Exception as e:
            logger.error(f"安全回调执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 尝试直接执行
            try:
                callback()
            except Exception as e2:
                logger.error(f"直接回调执行也失败: {e2}")

    def _connect_signals(self, main_window):
        """连接信号"""
        # 连接窗口信号
        main_window.window_closing.connect(self._on_window_closing)

        # 连接控制器信号到窗口
        self.status_message.connect(main_window.show_message)
        self.progress_updated.connect(main_window.show_progress)

    def cleanup(self):
        """清理资源"""
        try:
            # 取消所有活跃的异步任务
            for task in self._active_tasks.copy():
                if not task.done():
                    task.cancel()
                    logger.debug(f"取消异步任务: {task}")

            self._active_tasks.clear()
            logger.info("控制器资源清理完成")

        except Exception as e:
            logger.error(f"控制器资源清理失败: {e}")
    
    # ========================================================================
    # 项目管理
    # ========================================================================
    
    def new_project(self) -> None:
        """新建项目"""
        try:
            # 创建项目向导
            if not self._project_wizard:
                from src.presentation.dialogs.project_wizard import ProjectWizard
                self._project_wizard = ProjectWizard(self._main_window)
                self._project_wizard.project_created.connect(self._on_project_wizard_completed)

            # 显示向导
            result = self._project_wizard.exec()
            if result == self._project_wizard.DialogCode.Accepted:
                logger.info("项目创建向导完成")

        except Exception as e:
            logger.error(f"新建项目失败: {e}")
            self._show_error("新建项目失败", str(e))

    def new_document(self) -> None:
        """新建文档"""
        try:
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
                QTimer.singleShot(0, lambda: self._run_async_new_document(title.strip()))

        except Exception as e:
            logger.error(f"新建文档失败: {e}")
            self._show_error("新建文档失败", str(e))



    def _new_document_sync(self, title: str):
        """同步新建文档"""
        try:
            self.status_message.emit(f"正在创建文档: {title}")

            # 使用同步方式创建文档
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self._new_document_async(title))
                self.status_message.emit(f"文档创建成功: {title}")
                logger.info(f"新建文档成功: {title}")
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"同步新建文档失败: {e}")
            self._show_error("新建文档失败", str(e))

    async def _new_document_async(self, title: str) -> None:
        """异步新建文档"""
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
                self.status_message.emit(f"文档 '{document.title}' 创建成功")

                # 项目树刷新将通过信号处理，这里不重复刷新

                # 延迟打开新创建的文档
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self._safe_open_document(document.id))
            else:
                self._show_error("新建文档失败", "无法创建文档")

        except Exception as e:
            logger.error(f"异步新建文档失败: {e}")
            self._show_error("新建文档失败", str(e))

    def delete_document(self, document_id: str) -> None:
        """删除文档"""
        try:
            QTimer.singleShot(0, lambda: self._run_async_delete_document(document_id))
        except Exception as e:
            logger.error(f"删除文档失败: {e}")

    def rename_document(self, document_id: str, new_title: str) -> None:
        """重命名文档"""
        try:
            QTimer.singleShot(0, lambda: self._run_async_rename_document(document_id, new_title))
        except Exception as e:
            logger.error(f"重命名文档失败: {e}")
            self._show_error("重命名文档失败", str(e))

    def copy_document(self, document_id: str, new_title: str) -> None:
        """复制文档"""
        try:
            QTimer.singleShot(0, lambda: self._run_async_copy_document(document_id, new_title))
        except Exception as e:
            logger.error(f"复制文档失败: {e}")
            self._show_error("复制文档失败", str(e))
            self._show_error("删除文档失败", str(e))

    def _run_async_delete_document(self, document_id: str):
        """运行异步删除文档操作"""
        self._run_async_task(
            self._delete_document_async(document_id),
            success_callback=lambda _: logger.info(f"文档删除成功: {document_id}"),
            error_callback=lambda e: self._show_error("删除文档失败", str(e))
        )

    async def _delete_document_async(self, document_id: str) -> None:
        """异步删除文档"""
        try:
            # 删除文档
            success = await self.document_service.delete_document(document_id)

            if success:
                logger.info(f"文档删除成功: {document_id}")
                self.status_message.emit("文档删除成功")

                # 刷新项目树
                self.project_tree_refresh_requested.emit()

                # 如果当前编辑器中打开的是被删除的文档，关闭它
                if hasattr(self, '_main_window') and self._main_window:
                    editor = self._main_window.editor_widget
                    if hasattr(editor, 'close_document'):
                        editor.close_document(document_id)
            else:
                self._show_error("删除文档失败", "无法删除文档")

        except Exception as e:
            logger.error(f"异步删除文档失败: {e}")
            self._show_error("删除文档失败", str(e))

    def create_document_from_tree(self, document_type: str, project_id: str) -> None:
        """从项目树创建文档"""
        try:
            if not self.project_service.has_current_project:
                self._show_warning("创建文档", "请先打开一个项目")
                return

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
                QTimer.singleShot(0, lambda: self._run_async_create_document_from_tree(
                    title.strip(), document_type, project_id
                ))

        except Exception as e:
            logger.error(f"从项目树创建文档失败: {e}")
            self._show_error("创建文档失败", str(e))

    def _run_async_create_document_from_tree(self, title: str, document_type: str, project_id: str):
        """运行异步从项目树创建文档操作"""
        try:
            # 使用QTimer延迟执行，避免阻塞UI
            QTimer.singleShot(0, lambda: self._create_document_from_tree_sync(title, document_type, project_id))
        except Exception as e:
            logger.error(f"启动从项目树创建文档失败: {e}")
            self._show_error("创建文档失败", str(e))

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
        self.status_message.emit(f"{document_type}创建成功: {title}")
        logger.info(f"从项目树创建文档成功: {title}")
        # 延迟刷新项目树，确保文档已完全保存
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self._force_refresh_project_tree)  # 1秒后强制刷新

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

            # 创建新文档
            document = await self.document_service.create_document(
                title=title,
                content=default_content,
                project_id=project_id,
                document_type=doc_type
            )

            if document:
                logger.info(f"文档创建成功: {document.title}")
                self.status_message.emit(f"文档 '{document.title}' 创建成功")

                # 立即触发项目树刷新信号
                self.project_tree_refresh_requested.emit()

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

        except Exception as e:
            logger.error(f"异步从项目树创建文档失败: {e}")
            self._show_error("创建文档失败", str(e))
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

    def _run_async_delete_document(self, document_id: str):
        """运行异步删除文档任务"""
        self._run_async_task(
            self._delete_document_async(document_id),
            success_callback=lambda result: self._show_info("成功", "文档删除成功"),
            error_callback=lambda e: self._show_error("删除失败", f"删除文档失败: {e}")
        )

    async def _delete_document_async(self, document_id: str) -> bool:
        """异步删除文档"""
        try:
            # 确认删除
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self._main_window,
                "确认删除",
                "确定要删除这个文档吗？此操作无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return False

            # 删除文档
            success = await self.document_service.delete_document(document_id)
            if success:
                logger.info(f"文档删除成功: {document_id}")
                self.status_message.emit("文档删除成功")

                # 刷新项目树
                self.project_tree_refresh_requested.emit()
                return True
            else:
                self._show_error("删除失败", "无法删除文档")
                return False

        except Exception as e:
            logger.error(f"异步删除文档失败: {e}")
            self._show_error("删除失败", str(e))
            return False

    def _run_async_rename_document(self, document_id: str, new_title: str):
        """运行异步重命名文档任务"""
        self._run_async_task(
            self._rename_document_async(document_id, new_title),
            success_callback=lambda result: self._show_info("成功", f"文档重命名为: {new_title}"),
            error_callback=lambda e: self._show_error("重命名失败", f"重命名文档失败: {e}")
        )

    async def _rename_document_async(self, document_id: str, new_title: str) -> bool:
        """异步重命名文档"""
        try:
            # 重命名文档
            success = await self.document_service.update_document_title(document_id, new_title)
            if success:
                logger.info(f"文档重命名成功: {document_id} -> {new_title}")
                self.status_message.emit(f"文档重命名为: {new_title}")

                # 刷新项目树
                self.project_tree_refresh_requested.emit()
                return True
            else:
                self._show_error("重命名失败", "无法重命名文档")
                return False

        except Exception as e:
            logger.error(f"异步重命名文档失败: {e}")
            self._show_error("重命名失败", str(e))
            return False

    def _run_async_copy_document(self, document_id: str, new_title: str):
        """运行异步复制文档任务"""
        self._run_async_task(
            self._copy_document_async(document_id, new_title),
            success_callback=lambda result: self._show_info("成功", f"文档复制为: {new_title}"),
            error_callback=lambda e: self._show_error("复制失败", f"复制文档失败: {e}")
        )

    async def _copy_document_async(self, document_id: str, new_title: str) -> bool:
        """异步复制文档"""
        try:
            # 获取原文档
            original_doc = await self.document_service.get_document(document_id)
            if not original_doc:
                self._show_error("复制失败", "找不到原文档")
                return False

            # 创建新文档
            new_document = await self.document_service.create_document(
                title=new_title,
                content=original_doc.content,
                project_id=original_doc.project_id,
                document_type=original_doc.document_type
            )

            if new_document:
                logger.info(f"文档复制成功: {document_id} -> {new_document.id}")
                self.status_message.emit(f"文档复制为: {new_title}")

                # 刷新项目树
                self.project_tree_refresh_requested.emit()
                return True
            else:
                self._show_error("复制失败", "无法创建新文档")
                return False

        except Exception as e:
            logger.error(f"异步复制文档失败: {e}")
            self._show_error("复制失败", str(e))
            return False

    async def _create_project_async(self, name: str) -> None:
        """异步创建项目"""
        try:
            self.status_message.emit("正在创建项目...")
            
            project = await self.project_service.create_project(
                name=name,
                project_type=ProjectType.NOVEL,
                description="",
                author=self.settings_service.get_setting("project.default_author", ""),
                target_word_count=self.settings_service.get_setting("project.default_target_word_count", 80000)
            )
            
            if project:
                self.project_opened.emit(project)
                self.status_message.emit(f"项目创建成功并已打开: {name}")
                logger.info(f"新建项目已自动打开: {name} ({project.id})")

                # 可选：显示成功提示
                self._show_success_message("项目创建成功", f"项目 '{name}' 已创建并自动打开")
            else:
                self._show_error("创建项目失败", "无法创建项目，请检查设置")
                
        except Exception as e:
            logger.error(f"异步创建项目失败: {e}")
            self._show_error("创建项目失败", str(e))
    
    def create_new_project(self) -> None:
        """创建新项目"""
        try:
            from PyQt6.QtWidgets import QInputDialog, QMessageBox

            # 获取项目名称
            name, ok = QInputDialog.getText(
                None,
                "新建项目",
                "请输入项目名称:",
                text="新项目"
            )

            if ok and name.strip():
                # 异步创建项目
                self._run_async_task(
                    self._create_project_async(name.strip()),
                    success_callback=lambda result: self._show_info("成功", f"项目 '{name}' 创建成功"),
                    error_callback=lambda e: self._show_error("错误", f"创建项目失败: {e}")
                )

        except Exception as e:
            logger.error(f"创建新项目失败: {e}")
            self._show_error("错误", f"创建项目失败: {e}")

    def save_current_document(self) -> None:
        """保存当前文档"""
        try:
            # 获取当前编辑器中的文档
            if hasattr(self.main_window, 'editor_widget') and self.main_window.editor_widget:
                current_document = getattr(self.main_window.editor_widget, 'current_document', None)
                if current_document:
                    # 获取编辑器内容
                    content = getattr(self.main_window.editor_widget, 'get_content', lambda: "")()

                    # 更新文档内容
                    current_document.content = content
                    current_document.touch()  # 更新修改时间

                    # 异步保存
                    self._run_async_task(
                        self._save_document_async(current_document),
                        success_callback=lambda result: self._show_info("成功", "文档保存成功"),
                        error_callback=lambda e: self._show_error("错误", f"保存文档失败: {e}")
                    )
                else:
                    self._show_warning("提示", "没有打开的文档")
            else:
                self._show_warning("提示", "编辑器未初始化")

        except Exception as e:
            logger.error(f"保存当前文档失败: {e}")
            self._show_error("错误", f"保存文档失败: {e}")

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
                from config.settings import get_settings
                settings = get_settings()
                default_path = settings.data_dir / "projects"

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

            if not project_id or not project_path:
                logger.info("没有上次项目信息，跳过自动打开")
                return

            # 检查项目路径是否存在
            path = Path(project_path)
            if not path.exists():
                logger.warning(f"上次项目路径不存在: {project_path}")
                # 清空无效的项目信息
                self.settings_service.clear_last_project_info()
                return

            # 检查项目配置文件是否存在
            project_config = path / "project.json"
            if not project_config.exists():
                logger.warning(f"上次项目配置文件不存在: {project_config}")
                # 清空无效的项目信息
                self.settings_service.clear_last_project_info()
                return

            logger.info(f"自动打开上次项目: {project_path}")

            # 延迟打开项目，确保界面已完全加载
            QTimer.singleShot(1000, lambda: self._run_async_open_project_dir(path))

        except Exception as e:
            logger.error(f"自动打开上次项目失败: {e}")

    async def _open_project_async(self, file_path: Path) -> None:
        """异步打开项目"""
        try:
            self.status_message.emit("正在打开项目...")
            logger.info(f"尝试打开项目文件: {file_path}")

            if file_path.suffix.lower() == '.json':
                # 检查是否是项目配置文件
                if file_path.name == 'project.json':
                    # 直接加载项目文件
                    project = await self.project_service.open_project_by_path(file_path.parent)
                else:
                    # 可能是导出的项目文件
                    result = await self.import_export_service.import_project(
                        file_path, "", ImportOptions()
                    )
                    project = result.success
            else:
                # 导入项目
                result = await self.import_export_service.import_project(
                    file_path, "", ImportOptions()
                )
                project = result.success

            if project:
                # 保存最近打开的目录（文件的父目录）
                self.settings_service.set_last_opened_directory(str(file_path.parent))

                self.project_opened.emit(project)
                self.status_message.emit(f"项目打开成功: {project.title}")
                logger.info(f"项目打开成功: {project.title} ({project.id})")
            else:
                logger.warning(f"项目打开失败: {file_path}")
                self._show_error("打开项目失败", f"无法打开项目文件: {file_path}")

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
                    if not project_data.get('id'):
                        error_msg = f"项目配置文件损坏：\n{project_config}\n\n缺少项目ID"
                        logger.warning(error_msg)
                        self._show_error("打开项目失败", error_msg)
                        return
            except Exception as e:
                error_msg = f"无法读取项目配置文件：\n{project_config}\n\n错误: {e}"
                logger.warning(error_msg)
                self._show_error("打开项目失败", error_msg)
                return

            # 直接通过路径打开项目
            project = await self.project_service.open_project_by_path(project_dir)

            if project:
                # 保存最近打开的目录
                self.settings_service.set_last_opened_directory(str(project_dir))

                # 保存上次打开的项目信息
                self.settings_service.set_last_project_info(project.id, str(project_dir))

                self.project_opened.emit(project)
                self.status_message.emit(f"项目打开成功: {project.title}")
                logger.info(f"项目目录打开成功: {project.title} ({project.id})")
            else:
                error_msg = f"无法打开项目目录：\n{project_dir}\n\n项目文件可能已损坏"
                logger.warning(error_msg)
                self._show_error("打开项目失败", error_msg)

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
            # 使用异步方式保存文档
            self._run_async_task(
                self._save_document_async(document),
                success_callback=lambda _: self._on_document_save_success(document),
                error_callback=lambda e: self._on_document_save_error(document, e)
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
                success_callback=lambda result: self._on_save_success(),
                error_callback=lambda error: self._on_save_error(error)
            )
        except Exception as e:
            logger.error(f"启动保存操作失败: {e}")
            self._show_error("保存失败", str(e))

    def _on_save_success(self):
        """保存成功回调"""
        self.status_message.emit("保存成功")
        logger.info("保存成功")

    def _on_save_error(self, error):
        """保存错误回调"""
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

    def _on_document_save_success(self, document):
        """文档保存成功回调"""
        logger.info(f"文档保存成功: {document.title}")
        self.status_message.emit(f"文档 '{document.title}' 保存成功")

    def _on_document_save_error(self, document, error):
        """文档保存错误回调"""
        logger.error(f"文档保存失败: {document.title}, {error}")
        self._show_error("保存失败", f"文档 '{document.title}' 保存失败: {str(error)}")

    def _save_current_sync(self):
        """同步保存当前文档"""
        try:
            self.status_message.emit("正在保存...")

            # 使用同步方式保存
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self._save_current_async())
                self.status_message.emit("保存成功")
                logger.info("保存成功")
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"同步保存失败: {e}")
            self._show_error("保存失败", str(e))
    
    async def _save_current_async(self) -> None:
        """异步保存当前内容"""
        try:
            self.status_message.emit("正在保存...")
            
            # 保存当前文档
            if self.document_service.has_open_documents:
                success = await self.document_service.save_all_documents()
                if success:
                    self.status_message.emit("文档保存成功")
                else:
                    self._show_error("保存失败", "无法保存文档")
            
            # 保存当前项目
            if self.project_service.has_current_project:
                success = await self.project_service.save_current_project()
                if success:
                    self.status_message.emit("项目保存成功")
                else:
                    self._show_error("保存失败", "无法保存项目")
                    
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
            from config.settings import get_settings
            settings = get_settings()
            default_path = settings.data_dir / "projects"

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
            from config.settings import get_settings
            settings = get_settings()
            default_path = settings.data_dir

            file_path, _ = QFileDialog.getOpenFileName(
                self._main_window,
                "导入项目",
                str(default_path),
                "支持的格式 (*.json *.zip *.txt *.docx);;所有文件 (*)"
            )
            
            if file_path:
                QTimer.singleShot(0, lambda: self._run_async_import_project(Path(file_path)))
                
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
                    # 设置为当前项目
                    await self.project_service.set_current_project(result.project)

                    # 发出项目打开信号
                    self.project_opened.emit(result.project)

                    self.status_message.emit(f"项目 '{result.project.name}' 导入成功")
                    logger.info(f"项目导入成功: {result.project.name}")

                    # 刷新UI
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
                            self.status_message.emit(f"项目 '{project.name}' 导入成功")
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
            
            from config.settings import get_settings
            settings = get_settings()
            default_path = settings.data_dir

            file_path, _ = QFileDialog.getSaveFileName(
                self._main_window,
                "导出项目",
                str(default_path / f"{self.project_service.current_project.title}.zip"),
                "ZIP文件 (*.zip);;JSON文件 (*.json);;文本文件 (*.txt)"
            )
            
            if file_path:
                QTimer.singleShot(0, lambda: self._run_async_export_project(Path(file_path)))
                
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
                self.status_message.emit(f"项目导出成功: {file_path.name}")
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
            QTimer.singleShot(0, lambda: self._run_async_open_document(document_id))
        except Exception as e:
            logger.error(f"打开文档失败: {e}")
            self._show_error("打开文档失败", str(e))
    
    async def _open_document_async(self, document_id: str) -> None:
        """异步打开文档"""
        try:
            document = await self.document_service.open_document(document_id)

            if document:
                # 发送文档打开信号（这个信号会在主线程中处理UI更新）
                self.document_opened.emit(document)

                # 状态消息也通过信号发送，确保在主线程中更新
                self.status_message.emit(f"文档已打开: {document.title}")

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
            QTimer.singleShot(0, lambda: self._run_async_update_document_content(document_id, content))
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
            self.project_opened.emit(project)
            logger.info(f"项目选择成功: {project.title}")


    # ========================================================================
    # 搜索功能
    # ========================================================================
    
    def show_find_dialog(self) -> None:
        """显示查找对话框"""
        try:
            if not self._find_replace_dialog:
                self._find_replace_dialog = FindReplaceDialog(self._main_window)
                self._find_replace_dialog.find_requested.connect(self._on_find_requested)
                self._find_replace_dialog.replace_requested.connect(self._on_replace_requested)
                self._find_replace_dialog.replace_all_requested.connect(self._on_replace_all_requested)

            # 设置当前选中的文本
            if self._main_window and self._main_window.editor_widget:
                selected_text = self._main_window.editor_widget.get_selected_text()
                if selected_text:
                    self._find_replace_dialog.set_search_text(selected_text)

            self._find_replace_dialog.show()
            self._find_replace_dialog.raise_()
            self._find_replace_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示查找对话框失败: {e}")
            self._show_error("查找对话框", f"无法显示查找对话框: {e}")

    def show_replace_dialog(self) -> None:
        """显示替换对话框"""
        try:
            if not self._find_replace_dialog:
                self._find_replace_dialog = FindReplaceDialog(self._main_window)
                self._find_replace_dialog.find_requested.connect(self._on_find_requested)
                self._find_replace_dialog.replace_requested.connect(self._on_replace_requested)
                self._find_replace_dialog.replace_all_requested.connect(self._on_replace_all_requested)

            # 切换到替换标签页
            self._find_replace_dialog.tab_widget.setCurrentIndex(1)

            # 设置当前选中的文本
            if self._main_window and self._main_window.editor_widget:
                selected_text = self._main_window.editor_widget.get_selected_text()
                if selected_text:
                    self._find_replace_dialog.set_search_text(selected_text)

            self._find_replace_dialog.show()
            self._find_replace_dialog.raise_()
            self._find_replace_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示替换对话框失败: {e}")
            self._show_error("替换对话框", f"无法显示替换对话框: {e}")
    
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
    
    def _show_error(self, title: str, message: str) -> None:
        """显示错误消息"""
        if self._main_window:
            QMessageBox.critical(self._main_window, title, message)
    
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
        try:
            if not self._find_replace_dialog:
                self._find_replace_dialog = FindReplaceDialog(self._main_window)

                # 连接信号
                self._find_replace_dialog.find_requested.connect(self._on_find_requested)
                self._find_replace_dialog.replace_requested.connect(self._on_replace_requested)
                self._find_replace_dialog.replace_all_requested.connect(self._on_replace_all_requested)

            self._find_replace_dialog.show()
            self._find_replace_dialog.raise_()
            self._find_replace_dialog.activateWindow()

        except Exception as e:
            logger.error(f"显示查找替换对话框失败: {e}")
            self._show_error("查找替换", f"无法显示查找替换对话框: {e}")



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

            # 使用同步方式创建项目，避免线程问题
            self._create_project_sync(project_info, project_type)

        except Exception as e:
            logger.error(f"处理项目向导完成失败: {e}")
            self._show_error("创建项目失败", str(e))





    def _create_project_sync(self, project_info: dict, project_type: ProjectType):
        """非阻塞的项目创建"""
        try:
            # 显示状态消息
            self.status_message.emit("正在创建项目...")

            # 使用非阻塞的异步任务执行器
            logger.info("准备启动异步项目创建任务")
            self._run_async_task(
                self._create_project_from_wizard_async(project_info, project_type),
                success_callback=lambda project: self._on_project_creation_complete(project, project_info),
                error_callback=lambda e: self._on_project_creation_error_simple(project_info, e)
            )
            logger.info("异步项目创建任务已启动")

        except Exception as e:
            logger.error(f"启动项目创建失败: {e}")
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

                self.status_message.emit(f"项目创建成功并已打开: {project.title}")
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





    async def _create_project_from_wizard_async(self, project_info: dict, project_type: ProjectType):
        """从向导信息异步创建项目"""
        try:
            self.status_message.emit("正在创建项目...")

            # 验证项目位置
            project_location = project_info.get("location")
            if not project_location:
                raise ValueError("项目位置不能为空")

            # 创建项目
            project = await self.project_service.create_project(
                name=project_info["name"],
                project_type=project_type,
                description=project_info.get("description", ""),
                author=project_info.get("author", ""),
                target_word_count=project_info.get("word_count", 80000),
                project_path=project_location
            )

            if project:
                # 根据模板创建初始文档
                await self._create_template_documents(project, project_info.get("template", "空白项目"))

                logger.info(f"项目创建完成: {project.title} -> {project.root_path}")
                return project
            else:
                raise ValueError("项目创建返回空值")

        except Exception as e:
            logger.error(f"从向导异步创建项目失败: {e}")
            raise  # 重新抛出异常，让调用者处理

    def _emit_project_opened_signal(self, project):
        """发送项目打开信号"""
        try:
            logger.info(f"🎯 发送项目打开信号: {project.title}")
            self.project_opened.emit(project)
            self.status_message.emit(f"项目创建成功: {project.title}")
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
        """运行异步打开项目操作"""
        self._run_async_task(
            self._open_project_async(file_path),
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

    def _run_async_import_project(self, file_path: Path):
        """运行异步导入项目操作"""
        self._run_async_task(
            self._import_project_async(file_path),
            success_callback=lambda _: logger.info(f"项目导入成功: {file_path}"),
            error_callback=lambda e: self._show_error("导入项目失败", str(e))
        )

    def _run_async_export_project(self, file_path: Path):
        """运行异步导出项目操作"""
        self._run_async_task(
            self._export_project_async(file_path),
            success_callback=lambda _: logger.info(f"项目导出成功: {file_path}"),
            error_callback=lambda e: self._show_error("导出项目失败", str(e))
        )

    def _run_async_open_document(self, document_id: str):
        """运行异步打开文档操作"""
        self._run_async_task(
            self._open_document_async(document_id),
            success_callback=lambda document: self._on_document_opened_success(document, document_id),
            error_callback=lambda e: self._show_error("打开文档失败", str(e))
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
            else:
                logger.warning(f"文档打开成功但无法加载到编辑器: {document_id}")
        except Exception as e:
            logger.error(f"文档打开成功回调失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _run_async_save_before_exit(self):
        """运行异步退出前保存操作"""
        self._run_async_task(
            self._save_before_exit(),
            success_callback=lambda _: logger.info("退出前保存完成"),
            error_callback=lambda e: logger.error(f"异步退出前保存失败: {e}")
        )

    def _show_error(self, title: str, message: str):
        """显示错误消息（线程安全）"""
        try:
            # 确保在主线程中显示错误消息
            from src.shared.utils.thread_safety import is_main_thread
            if not is_main_thread():
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._show_error(title, message))
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

    def undo(self) -> None:
        """撤销操作"""
        try:
            if hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget:
                if hasattr(self._main_window.editor_widget, 'undo'):
                    self._main_window.editor_widget.undo()
                else:
                    logger.warning("编辑器不支持撤销操作")
        except Exception as e:
            logger.error(f"撤销操作失败: {e}")

    def redo(self) -> None:
        """重做操作"""
        try:
            if hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget:
                if hasattr(self._main_window.editor_widget, 'redo'):
                    self._main_window.editor_widget.redo()
                else:
                    logger.warning("编辑器不支持重做操作")
        except Exception as e:
            logger.error(f"重做操作失败: {e}")

    def cut(self) -> None:
        """剪切操作"""
        try:
            if hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget:
                if hasattr(self._main_window.editor_widget, 'cut'):
                    self._main_window.editor_widget.cut()
                else:
                    logger.warning("编辑器不支持剪切操作")
        except Exception as e:
            logger.error(f"剪切操作失败: {e}")

    def copy(self) -> None:
        """复制操作"""
        try:
            if hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget:
                if hasattr(self._main_window.editor_widget, 'copy'):
                    self._main_window.editor_widget.copy()
                else:
                    logger.warning("编辑器不支持复制操作")
        except Exception as e:
            logger.error(f"复制操作失败: {e}")

    def paste(self) -> None:
        """粘贴操作"""
        try:
            if hasattr(self._main_window, 'editor_widget') and self._main_window.editor_widget:
                if hasattr(self._main_window.editor_widget, 'paste'):
                    self._main_window.editor_widget.paste()
                else:
                    logger.warning("编辑器不支持粘贴操作")
        except Exception as e:
            logger.error(f"粘贴操作失败: {e}")

    def find(self) -> None:
        """查找操作"""
        try:
            self.show_find_dialog()
        except Exception as e:
            logger.error(f"查找操作失败: {e}")

    def replace(self) -> None:
        """替换操作"""
        try:
            self.show_replace_dialog()
        except Exception as e:
            logger.error(f"替换操作失败: {e}")

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

    def word_count(self) -> None:
        """字数统计"""
        try:
            # 使用专门的字数统计对话框
            if not hasattr(self, '_word_count_dialog') or not self._word_count_dialog:
                from src.presentation.dialogs.word_count_dialog import WordCountDialog
                self._word_count_dialog = WordCountDialog(
                    self.project_service,
                    self.document_service,
                    self._main_window
                )

            self._word_count_dialog.show()
            self._word_count_dialog.raise_()
            self._word_count_dialog.activateWindow()

        except Exception as e:
            logger.error(f"字数统计失败: {e}")
            self._show_error("错误", f"字数统计失败: {e}")

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



    def _run_async_open_project(self, file_path: Path):
        """运行异步打开项目操作"""
        self._run_async_task(
            self._open_project_async(file_path),
            success_callback=lambda _: logger.info(f"项目打开成功: {file_path}"),
            error_callback=lambda e: self._show_error("打开项目失败", str(e))
        )

    def _run_async_open_project_dir(self, project_dir: Path):
        """运行异步打开项目目录操作"""
        self._run_async_task(
            self._open_project_dir_async(project_dir),
            success_callback=lambda _: logger.info(f"项目目录打开成功: {project_dir}"),
            error_callback=lambda e: self._show_error("打开项目目录失败", str(e))
        )

    def _run_async_import_project(self, file_path: Path):
        """运行异步导入项目操作"""
        self._run_async_task(
            self._import_project_async(file_path),
            success_callback=lambda _: logger.info(f"项目导入成功: {file_path}"),
            error_callback=lambda e: self._show_error("导入项目失败", str(e))
        )

    def _run_async_export_project(self, file_path: Path):
        """运行异步导出项目操作"""
        self._run_async_task(
            self._export_project_async(file_path),
            success_callback=lambda _: logger.info(f"项目导出成功: {file_path}"),
            error_callback=lambda e: self._show_error("导出项目失败", str(e))
        )

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

    def _on_document_opened_success(self, document, document_id: str):
        """文档打开成功回调"""
        if document:
            logger.info(f"文档打开成功: {document.title}")
        else:
            logger.warning(f"文档打开失败: {document_id}")

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
        """处理文档创建事件"""
        try:
            logger.info(f"🎯 收到文档创建事件: {event.document_title} ({event.document_type.value})")

            # 立即刷新项目树以显示新文档
            self._refresh_project_tree_for_new_document(event)

            # 清除文档列表缓存
            self._clear_document_cache()

            logger.info(f"✅ 文档创建事件处理完成: {event.document_title}")

        except Exception as e:
            logger.error(f"❌ 处理文档创建事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _on_document_saved(self, event: DocumentSavedEvent) -> None:
        """处理文档保存事件"""
        try:
            logger.debug(f"📝 收到文档保存事件: {event.document_title}")

            # 可以在这里添加保存后的处理逻辑
            # 比如更新项目树中的文档统计信息

        except Exception as e:
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
                QTimer.singleShot(100, self._immediate_refresh_project_tree)

            else:
                logger.debug(f"文档不属于当前项目，跳过刷新: {event.project_id}")

        except Exception as e:
            logger.error(f"❌ 为新文档刷新项目树失败: {e}")

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
                if hasattr(repo, '_project_docs_cache'):
                    repo._project_docs_cache.clear()
                    logger.debug("✅ 文档缓存已清除")

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

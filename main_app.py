#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说编辑器 2.0 - 主应用程序

完整的重构版本，展示现代化架构设计
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Any

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 使用标准asyncio，不依赖qasync

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

# 导入重构后的组件
from src.shared.ioc.container import Container
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import setup_logging, get_logger
from src.presentation.views.main_window import MainWindow
from src.presentation.controllers.main_controller import MainController
from src.presentation.styles.theme_manager import ThemeManager, ThemeType

# 导入服务层
from src.application.services.application_service import ApplicationService
from src.application.services.project_service import ProjectService
from src.application.services.document_service import DocumentService
# 导入重构后的AI服务
try:
    from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
    from src.application.services.ai.intelligence.ai_intelligence_service import AIIntelligenceService
    _new_ai_available = True
    print("✅ 新架构AI服务导入成功")
except ImportError as e:
    print(f"⚠️ 新架构AI服务导入失败: {e}")
    import traceback
    print(f"详细错误: {traceback.format_exc()}")

    # 创建一个占位符AI服务类
    class AIService:
        def __init__(self, *args, **kwargs):
            # 忽略参数，创建一个基本的占位符服务
            del args, kwargs  # 避免未使用参数警告

        def process_request(self, *args, **kwargs):
            del args, kwargs  # 避免未使用参数警告
            raise RuntimeError("AI服务不可用，请检查AI模块安装")

    _new_ai_available = False
# 保留控制器需要的服务类型导入
from src.application.services.settings_service import SettingsService
from src.application.services.search import SearchService
from src.application.services.import_export_service import ImportExportService
from src.application.services.status_service import StatusService

# 配置现在在需要时局部导入

# 导入线程安全工具
from src.shared.utils.thread_safety import is_main_thread
from src.shared.utils.error_handler import handle_errors
from src.shared.constants import (
    ASYNC_MEDIUM_TIMEOUT,
    APP_NAME, APP_VERSION, APP_ORGANIZATION
)
from src.shared.utils.service_registry import ServiceRegistryFactory
from src.shared.utils.splash_factory import create_splash_and_execute_steps

logger = get_logger(__name__)


# 使用统一的错误处理装饰器，移除重复的装饰器定义


class AINovelEditorApp:
    """
    AI小说编辑器应用程序主类

    这是应用程序的核心类，负责整个应用程序的生命周期管理，包括：
    - 初始化Qt应用程序和核心组件
    - 配置依赖注入容器
    - 创建和管理用户界面
    - 处理应用程序启动和关闭流程
    - 管理主题和插件系统

    实现方式：
    - 使用依赖注入模式管理组件依赖关系
    - 采用事件驱动架构处理组件间通信
    - 支持插件系统的动态加载
    - 提供完整的错误处理和资源清理机制

    Attributes:
        app: Qt应用程序实例
        container: 依赖注入容器
        event_bus: 事件总线
        theme_manager: 主题管理器
        main_window: 主窗口实例
        main_controller: 主控制器
        settings: 应用程序设置
        app_service: 应用程序服务
    """

    def __init__(self):
        """
        初始化AI小说编辑器应用程序

        创建应用程序实例并初始化所有核心组件的引用。
        所有组件都设置为None，将在initialize()方法中进行实际初始化。
        """
        self.app: Optional[QApplication] = None
        self.container: Optional[Container] = None
        self.event_bus: Optional[EventBus] = None
        self.theme_manager: Optional[ThemeManager] = None
        self.main_window: Optional[MainWindow] = None
        self.main_controller: Optional[MainController] = None
        self.settings: Optional[Any] = None

        # 服务引用
        self.app_service: Optional[ApplicationService] = None

        # AI服务初始化标志
        self._ai_services_need_initialization: bool = False

        # 事件循环管理
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_shutting_down: bool = False

        logger.info("AI小说编辑器应用程序初始化")

    def _ensure_main_thread(self):
        """
        确保当前操作在主线程中执行

        Qt应用程序的UI操作必须在主线程中执行，此方法用于验证当前线程。
        如果不在主线程中，将抛出RuntimeError异常。

        实现方式：
        - 使用thread_safety工具检查当前线程
        - 获取当前线程信息用于错误报告
        - 抛出包含线程ID的详细错误信息

        Raises:
            RuntimeError: 当不在主线程中执行时抛出
        """
        if not is_main_thread():
            import threading
            current_thread = threading.current_thread()
            raise RuntimeError(f"必须在主线程中执行此操作。当前线程: {current_thread.ident}")
    
    def initialize(self) -> bool:
        """
        初始化应用程序的所有组件

        按照特定顺序初始化应用程序的各个组件，包括Qt应用程序、
        核心组件、依赖注入、服务层和用户界面。

        实现方式：
        - 分步骤初始化，每步都有错误检查
        - 显示启动画面提供用户反馈
        - 使用try-catch确保错误处理
        - 返回布尔值表示初始化是否成功

        Returns:
            bool: 初始化成功返回True，失败返回False

        Note:
            初始化失败时会显示错误对话框并记录详细日志
        """
        try:
            logger.info("🚀 启动AI小说编辑器 2.0")

            # 设置日志（包含AI模块调试）
            setup_logging()

            # 创建Qt应用
            self.app = QApplication(sys.argv)
            self.app.setApplicationName(APP_NAME)
            self.app.setApplicationVersion(APP_VERSION)
            self.app.setOrganizationName(APP_ORGANIZATION)

            # 使用启动画面工厂执行初始化
            success = create_splash_and_execute_steps(self.app, self)
            if not success:
                return False

            logger.info("✅ 应用程序初始化完成")
            return True

        except Exception as e:
            import traceback
            logger.error(f"❌ 应用程序初始化失败: {e}")
            traceback.print_exc()  # 打印详细错误追踪
            self._show_error("初始化失败", f"应用程序初始化失败：{e}")
            return False

    @handle_errors("核心组件初始化", show_dialog=False)
    def _initialize_core_components(self) -> bool:
        """
        初始化应用程序的核心组件

        按照依赖关系顺序初始化核心组件，包括设置、依赖注入容器、
        事件总线、主题管理器和插件管理器。这些组件是应用程序运行的基础。

        实现方式：
        - 使用get_settings()获取应用程序配置
        - 创建依赖注入容器管理对象生命周期
        - 初始化事件总线用于组件间通信
        - 创建主题管理器处理UI主题切换
        - 延迟创建插件管理器，避免过早初始化
        - 每个步骤都有异常处理确保稳定性

        Returns:
            bool: 初始化成功返回True，失败返回False

        Note:
            核心组件初始化失败会导致整个应用程序无法启动
        """
        # 设置和项目上下文将在项目打开后初始化
        self.settings = None
        self.project_paths = None

        # 创建依赖注入容器
        self.container = Container()

        # 如果稍后有项目上下文，注册 ProjectPaths 到容器以影响 ServiceRegistry 的 data_dir
        try:
            from src.shared.project_context import ProjectPaths
            # 暂不注册，待“打开项目”后再注册具体实例
            pass
        except Exception:
            pass

        # 设置全局容器实例
        from src.shared.ioc.container import set_global_container
        set_global_container(self.container)

        # 创建事件总线
        self.event_bus = EventBus()

        # 创建主题管理器
        self.theme_manager = ThemeManager()

        # 插件管理器将在UI创建时初始化，避免过早创建
        self.plugin_manager = None

        return True
    
    @handle_errors("依赖注册", show_dialog=False)
    def _register_dependencies(self) -> bool:
        """
        注册依赖注入容器中的所有依赖关系

        使用服务注册工厂统一管理依赖注册，减少重复代码。

        Returns:
            bool: 注册成功返回True，失败返回False
        """
        # 创建服务注册工厂
        registry = ServiceRegistryFactory(self.container, self.settings, self.event_bus)

        # 注册核心单例组件
        self._register_core_singletons()

        # 使用工厂批量注册服务
        registry.register_repositories_batch()
        registry.register_core_services_batch()
        registry.register_additional_services_batch()

        # 注册AI服务并检查是否需要初始化
        self._ai_services_need_initialization = registry.register_ai_services_batch(_new_ai_available)

        # 注册控制器
        self._register_controllers()

        # 初始化AI服务（如果需要）
        if self._ai_services_need_initialization:
            logger.info("依赖注册完成，开始初始化AI服务...")
            self._initialize_ai_services_sync()
            self._ai_services_need_initialization = False

        return True

    def _register_core_singletons(self) -> None:
        """注册核心单例组件"""
        from config.settings import Settings
        self.container.register_singleton(Settings, lambda: self.settings)
        self.container.register_singleton(EventBus, lambda: self.event_bus)
        self.container.register_singleton(ThemeManager, lambda: self.theme_manager)

    # 移除重复的服务注册方法，已由ServiceRegistryFactory统一处理

    def _register_controllers(self) -> None:
        """注册控制器层组件"""
        def create_main_controller():
            # 根据可用的AI架构选择服务
            ai_service = (self.container.get(AIOrchestrationService)
                         if _new_ai_available
                         else self.container.get('AIService'))

            return MainController(
                app_service=self.container.get(ApplicationService),
                project_service=self.container.get(ProjectService),
                document_service=self.container.get(DocumentService),
                ai_service=ai_service,
                settings_service=self.container.get(SettingsService),
                search_service=self.container.get(SearchService),
                import_export_service=self.container.get(ImportExportService),
                status_service=self.container.get(StatusService)
            )

        self.container.register_singleton(MainController, create_main_controller)
    
    @handle_errors("应用服务初始化", show_dialog=False)
    def _initialize_services(self) -> bool:
        """初始化服务"""
        # 获取应用服务
        self.app_service = self.container.get(ApplicationService)

        # 初始化应用服务
        if not self.app_service.initialize():
            logger.error("应用服务初始化失败")
            return False

        return True


    @handle_errors("用户界面创建", show_dialog=False)
    def _create_ui(self) -> bool:
        """创建用户界面"""
        # 确保在主线程中执行
        self._ensure_main_thread()

        # 创建插件管理器（在UI创建时初始化，确保依赖关系正确）
        from src.shared.plugins.plugin_manager import PluginManager
        self.plugin_manager = PluginManager(self)

        # 注册插件管理器到容器
        self.container.register_singleton(PluginManager, lambda: self.plugin_manager)

        # 获取主控制器（如果还没有创建的话）
        if not self.main_controller:
            self.main_controller = self.container.get(MainController)

        # 初始化AI组件工厂
        try:
            if _new_ai_available:
                # 使用新的重构架构
                from src.presentation.widgets.ai.refactored import initialize_ai_component_factory
                ai_orchestration_service = self.container.get(AIOrchestrationService)
                ai_intelligence_service = self.container.get(AIIntelligenceService)

                if ai_orchestration_service and ai_intelligence_service:
                    settings_service = self.container.get(SettingsService)
                    initialize_ai_component_factory(
                        ai_orchestration_service,
                        ai_intelligence_service,
                        self.event_bus,
                        settings_service
                    )
                    logger.info("✅ 新架构AI组件工厂初始化完成")
                else:
                    logger.warning("⚠️ 新架构AI服务不可用")
            else:
                # 使用旧版本架构
                from src.presentation.widgets.ai import initialize_ai_component_factory
                ai_service = self.container.get(AIService)
                if ai_service and hasattr(ai_service, 'unified_ai_service'):
                    initialize_ai_component_factory(
                        ai_service.unified_ai_service,
                        self.event_bus
                    )
                    logger.info("✅ 旧版本AI组件工厂初始化完成")
                else:
                    logger.warning("⚠️ 旧版本AI服务不可用，跳过AI组件工厂初始化")
        except Exception as e:
            logger.warning(f"AI组件工厂初始化失败: {e}")

        # 创建主窗口
        self.main_window = MainWindow(self.main_controller)

        # 设置控制器的主窗口引用
        self.main_controller.set_main_window(self.main_window)

        # AI助手管理器已通过主控制器传递给编辑器

        # 设置主题管理器到主窗口
        self.main_window.theme_manager = self.theme_manager

        # 连接信号
        self._connect_signals()

        # 加载插件
        self._load_plugins()

        return True
    
    def _connect_signals(self):
        """连接信号"""
        try:
            # 连接主题变更信号
            self.theme_manager.theme_changed.connect(self._on_theme_changed)
            
            logger.debug("信号连接完成")
            
        except Exception as e:
            logger.error(f"信号连接失败: {e}")

    def _load_plugins(self):
        """加载插件"""
        try:
            logger.info("正在加载插件...")

            # 加载所有插件
            self.plugin_manager.load_all_plugins()

            # 执行应用启动钩子
            from src.shared.plugins.plugin_interface import PluginHooks
            self.plugin_manager.execute_hook(PluginHooks.APP_STARTUP, self)

            logger.info("插件加载完成")

        except Exception as e:
            logger.error(f"加载插件失败: {e}")

    def _apply_theme(self):
        """应用主题"""
        try:
            # 从设置中获取主题（如果设置可用）
            if self.settings:
                theme_name = self.settings.ui.theme
            else:
                # 使用默认主题
                theme_name = "light"

            if theme_name == "dark":
                theme_type = ThemeType.DARK
            elif theme_name == "auto":
                theme_type = ThemeType.AUTO
            else:
                theme_type = ThemeType.LIGHT

            # 应用主题
            self.theme_manager.set_theme(theme_type)

            logger.info(f"主题应用完成: {theme_name}")

        except Exception as e:
            logger.error(f"应用主题失败: {e}")
    
    def _setup_async_loop(self):
        """设置异步事件循环"""
        if self._is_shutting_down:
            return

        try:
            # 检查是否已有事件循环
            try:
                existing_loop = asyncio.get_event_loop()
                if existing_loop and not existing_loop.is_closed():
                    self._event_loop = existing_loop
                    logger.debug("使用现有的异步事件循环")
                    return
            except RuntimeError:
                # 没有现有循环，创建新的
                pass

            # 创建基础事件循环
            if self._event_loop is None or self._event_loop.is_closed():
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
                logger.debug("创建新的异步事件循环")

            logger.debug("异步事件循环设置完成")

        except Exception as e:
            logger.error(f"设置异步事件循环失败: {e}")
            self._event_loop = None

    def _initialize_ai_services_sync(self):
        """同步初始化AI服务"""
        try:
            logger.info("🚀 开始同步初始化AI服务...")

            # 先检查容器状态
            logger.debug(f"容器状态: {self.container}")

            ai_orchestration = self.container.get(AIOrchestrationService)
            logger.info(f"🔧 AI编排服务获取结果: {ai_orchestration}")

            if ai_orchestration:
                logger.info("🔧 AI编排服务获取成功，开始初始化...")

                # 检查配置
                try:
                    config = ai_orchestration.config
                    logger.info(f"🔧 AI服务配置: {config}")
                except Exception as e:
                    logger.error(f"❌ 获取AI服务配置失败: {e}")
                    return

                try:
                    # AI编排服务现在委托给统一客户端管理器
                    logger.info(f"🔧 AI编排服务已重构，使用统一客户端管理器")
                except Exception as e:
                    logger.error(f"❌ 获取提供商配置失败: {e}")
                    return

                # 使用独立事件循环进行初始化
                self._run_ai_initialization_with_timeout(ai_orchestration)

            else:
                logger.warning("⚠️ AI编排服务未找到")

        except Exception as e:
            logger.error(f"❌ AI服务同步初始化失败: {e}")
            import traceback
            logger.error(f"❌ 异常详情: {traceback.format_exc()}")

    def _run_ai_initialization_with_timeout(self, ai_orchestration):
        """在独立事件循环中运行AI初始化"""
        if self._is_shutting_down:
            return

        temp_loop = None
        try:
            # 使用临时事件循环避免干扰主循环
            temp_loop = asyncio.new_event_loop()

            logger.info("🔧 开始异步初始化...")
            # 统一超时时间为30秒
            result = temp_loop.run_until_complete(
                asyncio.wait_for(ai_orchestration.initialize(), timeout=ASYNC_MEDIUM_TIMEOUT)
            )

            if result:
                logger.info("✅ AI编排服务同步初始化完成")
            else:
                logger.error("❌ AI编排服务初始化返回False")

        except asyncio.TimeoutError:
            logger.error(f"❌ AI服务初始化超时（{ASYNC_MEDIUM_TIMEOUT}秒）")
        except Exception as e:
            logger.error(f"❌ AI服务异步初始化失败: {e}")
        finally:
            if temp_loop:
                try:
                    # 清理临时循环
                    pending = asyncio.all_tasks(temp_loop)
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    temp_loop.close()
                    logger.debug("🔧 临时事件循环已关闭")
                except Exception as e:
                    logger.warning(f"关闭临时事件循环失败: {e}")

    # 移除重复的异步初始化方法，统一使用同步初始化



    def _on_theme_changed(self, theme_name: str):
        """主题变更处理"""
        logger.info(f"主题已变更: {theme_name}")
        
        # 保存主题设置
        if self.app_service:
            settings_service = self.container.get(SettingsService)
            settings_service.set_setting("ui.theme", theme_name)
    
    def run(self) -> int:
        """
        运行AI小说编辑器应用程序

        这是应用程序的主入口点，负责完整的应用程序生命周期管理。
        包括初始化、显示界面、运行事件循环和清理资源。

        实现方式：
        - 调用initialize()方法完成应用程序初始化
        - 显示主窗口并展示欢迎消息
        - 启动Qt事件循环处理用户交互
        - 使用try-finally确保资源正确清理
        - 返回适当的退出代码

        Returns:
            int: 应用程序退出代码，0表示成功，1表示失败

        Note:
            此方法会阻塞直到用户关闭应用程序
        """
        try:
            if not self.initialize():
                return 1

            # 显示启动页面选择项目
            project_path = self._show_startup_page()
            if not project_path:
                logger.info("用户取消选择项目，退出应用程序")
                return 0

            # 初始化项目上下文
            if not self._initialize_project_context(project_path):
                return 1

            # 注册依赖（现在有了项目上下文）
            if not self._register_dependencies():
                return 1

            # 创建用户界面
            if not self._create_ui():
                return 1

            # 打开选择的项目
            if not self._open_selected_project(project_path):
                logger.warning("项目打开失败，但继续显示主界面")

            # 显示主窗口
            self.main_window.show()

            # 使用标准Qt事件循环
            return self.app.exec()

        except Exception as e:
            logger.error(f"运行应用程序失败: {e}")
            self._show_error("运行错误", f"应用程序运行失败：{e}")
            return 1
        finally:
            self._cleanup()

    def _show_startup_page(self) -> Optional[Path]:
        """显示启动页面选择项目"""
        try:
            from PyQt6.QtWidgets import QDialog
            from src.presentation.views.startup_window import StartupWindow
            from src.shared.managers.recent_projects_manager import get_recent_projects_manager

            # 获取最近项目管理器
            recent_manager = get_recent_projects_manager()
            recent_projects = recent_manager.get_recent_projects()

            # 创建启动页面（无论是否有最近项目都显示）
            startup_window = StartupWindow(recent_projects)

            # 连接信号
            startup_window.remove_requested.connect(recent_manager.remove_project)

            # 项目创建逻辑：统一委托主控制器与服务层，避免重复实现
            def on_create_project(info: dict):
                try:
                    logger.info(f"收到项目创建请求: {info.get('name', '未知')}")

                    def completion_callback(path):
                        try:
                            if path:
                                startup_window.selected_project_path = str(path)
                                startup_window.accept()
                            else:
                                from PyQt6.QtWidgets import QMessageBox
                                QMessageBox.warning(
                                    startup_window,
                                    "创建项目失败",
                                    "项目创建失败"
                                )
                        except Exception as e:
                            logger.error(f"处理项目创建回调失败: {e}")

                    # 统一入口：优先通过主控制器 -> ProjectService -> Repository
                    if not self.main_controller:
                        # 在主控制器尚未初始化时，仍然使用项目服务层完成创建，保持与编辑器一致的实现路径
                        try:
                            from src.shared.utils.service_registry import ServiceRegistryFactory
                            from src.infrastructure.repositories.file_project_repository import FileProjectRepository
                            from src.application.services.project_service import ProjectService
                            reg = ServiceRegistryFactory(self.container, self.settings, self.event_bus)
                            repo = FileProjectRepository(reg.data_dir / "projects")
                            svc = ProjectService(repo, self.event_bus)

                            # 与编辑器一致：在选定目录(location)下创建“给定名称”的子目录
                            location = info.get('location') or info.get('path') or info.get('directory') or info.get('dir')
                            name = (info.get('name') or '新项目').strip() or '新项目'
                            if not location:
                                from pathlib import Path
                                base = Path.home() / 'Documents' / 'AI_Novel_Editor' / 'Projects'
                                location = str(base)
                            from pathlib import Path
                            target_path = Path(location) / name

                            # 调用异步服务在独立线程中执行，避免事件循环冲突
                            import asyncio, threading
                            result = {}
                            def runner():
                                try:
                                    proj = asyncio.run(svc.create_project(name=name, project_path=str(target_path)))
                                    result['proj'] = proj
                                except Exception as e:
                                    result['error'] = e
                            t = threading.Thread(target=runner, daemon=True)
                            t.start(); t.join()
                            if 'error' in result:
                                raise result['error']
                            proj = result.get('proj')
                            # 回调通知成功并关闭启动窗口
                            project_root = getattr(proj, 'root_path', None) or target_path
                            completion_callback(project_root)
                        except Exception as ce:
                            logger.error(f"项目服务层创建失败: {ce}")
                            raise
                    else:
                        self.main_controller.create_project_via_service(info, completion_callback=completion_callback)

                except Exception as e:
                    logger.error(f"创建项目失败: {e}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        startup_window,
                        "创建项目失败",
                        f"无法创建项目：\n{e}"
                    )

            startup_window.create_new_project.connect(on_create_project)

            # 显示启动页面
            result = startup_window.exec()

            if result == QDialog.DialogCode.Accepted and startup_window.selected_project_path:
                selected_path = Path(startup_window.selected_project_path)
                return selected_path

            return None

        except Exception as e:
            logger.error(f"显示启动页面失败: {e}")
            # 回退到简单的文件夹选择对话框
            return self._fallback_folder_selection()

    # 项目创建逻辑已移到启动页面中处理

    def _fallback_folder_selection(self) -> Optional[Path]:
        """回退的文件夹选择对话框"""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox

            reply = QMessageBox.question(
                None,
                "选择项目文件夹",
                "AI小说编辑器需要一个项目文件夹来存储所有数据。\n\n"
                "请选择一个现有的项目文件夹，或选择一个空文件夹来创建新项目。",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Ok
            )

            if reply != QMessageBox.StandardButton.Ok:
                return None

            folder_path = QFileDialog.getExistingDirectory(
                None,
                "选择项目文件夹",
                str(Path.cwd()),
                QFileDialog.Option.ShowDirsOnly
            )

            if folder_path:
                return Path(folder_path)
            return None

        except Exception as e:
            logger.error(f"回退文件夹选择失败: {e}")
            return None

    def _initialize_project_context(self, project_path: Path) -> bool:
        """初始化项目上下文"""
        try:
            from src.shared.project_context import ProjectPaths, ensure_project_dirs
            from config.settings import get_settings_for_project, Settings
            from src.shared.managers.recent_projects_manager import get_recent_projects_manager

            # 创建项目路径对象
            self.project_paths = ProjectPaths(project_path)

            # 确保项目目录结构存在
            ensure_project_dirs(self.project_paths)

            # 加载项目设置
            self.settings = get_settings_for_project(project_path)

            # 注册项目上下文到容器
            self.container.register_instance(ProjectPaths, self.project_paths)
            self.container.register_instance(Settings, self.settings)

            # 更新最近项目的访问时间
            recent_manager = get_recent_projects_manager()
            recent_manager.update_project_access_time(str(project_path))

            logger.info(f"项目上下文初始化完成: {project_path}")
            return True

        except Exception as e:
            logger.error(f"初始化项目上下文失败: {e}")
            return False

    def _open_selected_project(self, project_path: Path) -> bool:
        """打开选择的项目（统一入口到主控制器）"""
        try:
            if not self.main_controller:
                logger.error("主控制器不可用")
                return False

            from PyQt6.QtCore import QTimer

            def delayed():
                try:
                    logger.info(f"通过主控制器打开项目: {project_path}")
                    self.main_controller.open_project_directory(project_path)  # 统一入口
                except Exception as e:
                    logger.error(f"通过主控制器打开项目失败: {e}")

            # 延迟 500ms，确保主窗口加载完毕
            QTimer.singleShot(500, delayed)
            return True
        except Exception as e:
            logger.error(f"打开选择的项目失败: {e}")
            return False



    # 欢迎消息相关方法已移除，现在直接进入项目选择流程
    
    def _show_error(self, title: str, message: str):
        """显示错误消息"""
        if self.app:
            QMessageBox.critical(None, title, message)
        else:
            print(f"错误: {title} - {message}")
    
    def _cleanup(self):
        """清理资源"""
        if self._is_shutting_down:
            return

        self._is_shutting_down = True

        try:
            logger.info("清理应用程序资源...")

            # 按照依赖关系逆序清理资源

            # 1. 首先清理控制器资源
            if hasattr(self, 'main_controller') and self.main_controller:
                try:
                    self.main_controller.cleanup()
                except Exception as e:
                    logger.error(f"清理控制器失败: {e}")

            # 2. 关闭插件管理器
            if hasattr(self, 'plugin_manager') and self.plugin_manager:
                try:
                    self.plugin_manager.shutdown()
                except Exception as e:
                    logger.error(f"关闭插件管理器失败: {e}")

            # 3. 关闭AI编排服务
            if hasattr(self, 'ai_service') and self.ai_service:
                try:
                    # 获取AI编排服务
                    ai_orchestration = getattr(self.ai_service, 'ai_orchestration_service', None)
                    if ai_orchestration:
                        logger.info("关闭AI编排服务...")
                        # 创建临时事件循环来关闭AI服务
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            loop.run_until_complete(ai_orchestration.shutdown())
                        except Exception as e:
                            logger.error(f"关闭AI编排服务失败: {e}")
                except Exception as e:
                    logger.error(f"关闭AI服务失败: {e}")

            # 4. 关闭事件总线
            try:
                from src.shared.events.event_bus import get_event_bus
                event_bus = get_event_bus()
                if event_bus:
                    logger.info("关闭事件总线...")
                    # 优先使用 asyncio.run，在无事件循环时优雅关闭；若当前线程已有事件循环，则退回同步关闭
                    try:
                        asyncio.run(event_bus.shutdown_async())
                    except RuntimeError:
                        # 可能是“Cannot be called from a running event loop”
                        try:
                            loop = asyncio.get_running_loop()
                            # 尝试在线程安全地提交到该循环
                            future = asyncio.run_coroutine_threadsafe(event_bus.shutdown_async(), loop)
                            future.result(timeout=2)
                        except Exception as e:
                            logger.warning(f"异步关闭事件总线失败，使用同步方法: {e}")
                            event_bus.shutdown()
                    except Exception as e:
                        logger.warning(f"异步关闭事件总线失败，使用同步方法: {e}")
                        event_bus.shutdown()
            except Exception as e:
                logger.error(f"关闭事件总线失败: {e}")

            # 5. 关闭应用服务
            if self.app_service:
                try:
                    self.app_service.shutdown()
                except Exception as e:
                    logger.error(f"关闭应用服务失败: {e}")

            # 6. 最后关闭事件循环（确保其他组件已经停止使用）
            self._cleanup_event_loop()

            logger.info("资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")

    def _cleanup_event_loop(self):
        """清理事件循环"""
        try:
            # 优先清理我们管理的事件循环
            if self._event_loop and not self._event_loop.is_closed():
                self._cancel_pending_tasks(self._event_loop)
                self._event_loop.close()
                self._event_loop = None
                logger.debug("已清理管理的事件循环")
                return

            # 如果没有管理的循环，尝试清理当前循环
            try:
                current_loop = asyncio.get_event_loop()
                if current_loop and not current_loop.is_closed():
                    self._cancel_pending_tasks(current_loop)
                    current_loop.close()
                    logger.debug("已清理当前事件循环")
            except RuntimeError as e:
                # 可能没有事件循环或已经关闭
                if "no current event loop" not in str(e).lower():
                    logger.warning(f"获取当前事件循环失败: {e}")

        except Exception as e:
            logger.error(f"清理事件循环失败: {e}")

    def _cancel_pending_tasks(self, loop):
        """取消事件循环中的待处理任务"""
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.debug(f"取消 {len(pending)} 个待处理任务")
                for task in pending:
                    if not task.done():
                        task.cancel()

                # 等待任务取消完成，设置超时避免无限等待
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=5.0
                        )
                    )
                except asyncio.TimeoutError:
                    logger.warning("等待异步任务取消超时")
                except Exception as e:
                    logger.warning(f"等待任务取消失败: {e}")
        except Exception as e:
            logger.warning(f"取消待处理任务失败: {e}")


def main() -> int:
    """
    AI小说编辑器应用程序主入口函数

    这是整个应用程序的启动入口点，负责创建应用程序实例并启动运行。
    提供最外层的异常处理确保应用程序能够优雅地处理启动错误。

    实现方式：
    - 创建AINovelEditorApp实例
    - 调用run()方法启动应用程序
    - 捕获并处理任何启动异常
    - 返回适当的退出代码供系统使用

    Returns:
        int: 应用程序退出代码，0表示成功，1表示失败

    Note:
        此函数通常由if __name__ == "__main__"块调用
    """
    try:
        # 创建应用程序实例
        app = AINovelEditorApp()

        # 运行应用程序
        return app.run()

    except Exception as e:
        print(f"启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

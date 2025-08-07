#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说编辑器 2.0 - 主应用程序

完整的重构版本，展示现代化架构设计
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional
from functools import wraps

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 使用标准asyncio，不依赖qasync

from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont

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
from src.application.services.settings_service import SettingsService
from src.application.services.search import SearchService
from src.application.services.import_export_service import ImportExportService
from src.application.services.backup_service import BackupService
from src.application.services.template_service import TemplateService
# 注意：AIAssistantManager 和 SpecializedAIManager 已被新的统一AI服务替代
from src.application.services.status_service import StatusService

# 导入仓储层
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.document_repository import IDocumentRepository
from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.infrastructure.repositories.file_project_repository import FileProjectRepository
from src.infrastructure.repositories.file_document_repository import FileDocumentRepository
from src.infrastructure.repositories.ai_service_repository import AIServiceRepository

# 导入配置
from config.settings import Settings

# 导入线程安全工具
from src.shared.utils.thread_safety import is_main_thread

logger = get_logger(__name__)


def handle_initialization_error(operation_name: str):
    """
    初始化操作异常处理装饰器

    用于统一处理初始化过程中的异常，减少重复的异常处理代码。

    Args:
        operation_name: 操作名称，用于日志记录
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logger.info(f"{operation_name}完成")
                return result
            except Exception as e:
                logger.error(f"{operation_name}失败: {e}")
                return False
        return wrapper
    return decorator


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

        实现方式：
        - 使用Optional类型注解确保类型安全
        - 延迟初始化模式，避免构造函数中的复杂逻辑
        - 记录初始化日志便于调试
        """
        self.app: Optional[QApplication] = None
        self.container: Optional[Container] = None
        self.event_bus: Optional[EventBus] = None
        self.theme_manager: Optional[ThemeManager] = None
        self.main_window: Optional[MainWindow] = None
        self.main_controller: Optional[MainController] = None
        self.settings: Optional[Settings] = None

        # 服务引用
        self.app_service: Optional[ApplicationService] = None

        # AI服务初始化标志
        self._ai_services_need_initialization: bool = False

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
        splash = None
        try:
            logger.info("🚀 启动AI小说编辑器 2.0")

            # 设置日志（包含AI模块调试）
            setup_logging()

            # 创建Qt应用
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AI小说编辑器 2.0")
            self.app.setApplicationVersion("2.0.0")
            self.app.setOrganizationName("AI小说编辑器团队")

            # 显示启动画面
            splash = self._create_splash_screen()
            splash.show()
            self.app.processEvents()

            # 初始化核心组件
            splash.showMessage("初始化核心组件...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            if not self._initialize_core_components():
                return False

            # 注册依赖
            splash.showMessage("注册服务依赖...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            if not self._register_dependencies():
                return False

            # 初始化服务
            splash.showMessage("初始化应用服务...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            if not self._initialize_services():
                return False

            # 创建UI
            splash.showMessage("创建用户界面...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            if not self._create_ui():
                return False

            # 应用主题
            splash.showMessage("应用主题样式...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            self._apply_theme()

            # 设置事件循环
            splash.showMessage("设置异步事件循环...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            self._setup_async_loop()

            # 完成初始化
            splash.showMessage("启动完成！", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
            self.app.processEvents()

            # 延迟关闭启动画面
            QTimer.singleShot(1000, splash.close)

            logger.info("✅ 应用程序初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 应用程序初始化失败: {e}")
            # 确保启动画面被关闭
            if splash:
                try:
                    splash.close()
                except Exception:
                    pass
            self._show_error("初始化失败", f"应用程序初始化失败：{e}")
            return False
    
    def _create_splash_screen(self) -> QSplashScreen:
        """
        创建应用程序启动画面

        创建一个简单的启动画面，在应用程序初始化过程中向用户显示进度信息。
        启动画面会保持在最顶层，无边框设计，提供现代化的用户体验。

        实现方式：
        - 创建400x300像素的白色背景图像
        - 设置窗口标志保持在最顶层且无边框
        - 使用Microsoft YaHei UI字体提供良好的中文显示效果
        - 居中显示应用程序名称和启动状态

        Returns:
            QSplashScreen: 配置好的启动画面实例

        Note:
            启动画面会在初始化完成后通过定时器自动关闭
        """
        # 确保在主线程中创建UI组件
        self._ensure_main_thread()

        # 创建简单的启动画面
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.GlobalColor.white)

        splash = QSplashScreen(pixmap)
        splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)

        # 设置字体
        font = QFont("Microsoft YaHei UI", 12)
        splash.setFont(font)

        splash.showMessage(
            "🤖 AI小说编辑器 2.0\n\n正在启动...",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.black
        )

        return splash

    @handle_initialization_error("核心组件初始化")
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
        # 创建设置（使用默认配置）
        from config.settings import get_settings
        self.settings = get_settings()

        # 创建依赖注入容器
        self.container = Container()

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
    
    @handle_initialization_error("依赖注册")
    def _register_dependencies(self) -> bool:
        """
        注册依赖注入容器中的所有依赖关系

        配置依赖注入容器，注册所有服务、仓储和组件的依赖关系。
        使用单例模式确保核心组件的唯一性，使用工厂函数创建复杂对象。

        实现方式：
        - 注册核心组件为单例（Settings、EventBus、ThemeManager等）
        - 注册仓储接口与具体实现的映射关系
        - 注册应用服务及其依赖关系
        - 使用lambda表达式延迟创建对象
        - 确保依赖关系的正确注入顺序

        Returns:
            bool: 注册成功返回True，失败返回False

        Note:
            依赖注册失败会导致后续服务无法正常创建和使用
        """
        # 注册单例
        self.container.register_singleton(Settings, lambda: self.settings)
        self.container.register_singleton(EventBus, lambda: self.event_bus)
        self.container.register_singleton(ThemeManager, lambda: self.theme_manager)

        # 注册仓储
        self.container.register_singleton(
            IProjectRepository,
            lambda: FileProjectRepository(self.settings.data_dir / "projects")
        )
        self.container.register_singleton(
            IDocumentRepository,
            lambda: FileDocumentRepository(self.settings.data_dir / "documents")
        )
        self.container.register_singleton(
            IAIServiceRepository,
            lambda: AIServiceRepository(self.settings)
        )

        # 注册应用服务
        self.container.register_singleton(
            ApplicationService,
            lambda: ApplicationService(self.container, self.event_bus, self.settings)
        )
        self.container.register_singleton(
            ProjectService,
            lambda: ProjectService(
                project_repository=self.container.get(IProjectRepository),
                event_bus=self.event_bus
            )
        )

        # 先注册SearchService，因为DocumentService依赖它
        self.container.register_singleton(
            SearchService,
            lambda: SearchService(
                project_repository=self.container.get(IProjectRepository),
                document_repository=self.container.get(IDocumentRepository),
                event_bus=self.event_bus,
                index_path=self.settings.data_dir / "search_index.db"
            )
        )

        self.container.register_singleton(
            DocumentService,
            lambda: DocumentService(
                document_repository=self.container.get(IDocumentRepository),
                event_bus=self.event_bus,
                search_service=self.container.get(SearchService)
            )
        )
        # 注册AI服务（支持新旧架构）
        if _new_ai_available:
            # 使用新的重构架构
            def create_ai_orchestration_service():
                # 获取设置服务
                settings_service = self.container.get(SettingsService)

                # 配置AI编排服务
                config = {
                    'providers': {
                        'openai': {
                            'api_key': settings_service.get_setting('ai.openai_api_key', ''),
                            'base_url': settings_service.get_setting('ai.openai_base_url', 'https://api.openai.com/v1'),
                            'default_model': settings_service.get_setting('ai.openai_model', 'gpt-3.5-turbo')
                        },
                        'deepseek': {
                            'api_key': settings_service.get_setting('ai.deepseek_api_key', ''),
                            'base_url': settings_service.get_setting('ai.deepseek_base_url', 'https://api.deepseek.com/v1'),
                            'default_model': settings_service.get_setting('ai.deepseek_model', 'deepseek-chat')
                        }
                    },
                    'default_provider': settings_service.get_setting('ai.default_provider', 'deepseek'),
                    'max_concurrent_requests': settings_service.get_setting('ai.max_concurrent_requests', 10),
                    'request_timeout': settings_service.get_setting('ai.request_timeout', 30.0)
                }
                return AIOrchestrationService(config)

            def create_ai_intelligence_service():
                service = AIIntelligenceService()
                service.initialize()
                return service

            # 注册新架构服务
            self.container.register_singleton(AIOrchestrationService, create_ai_orchestration_service)
            self.container.register_singleton(AIIntelligenceService, create_ai_intelligence_service)

            # 为向后兼容，也注册一个AIService别名
            self.container.register_singleton('AIService', create_ai_orchestration_service)

            # 标记需要初始化AI服务
            self._ai_services_need_initialization = True
        else:
            # 使用占位符AI服务
            def create_ai_service():
                return AIService()
            self.container.register_singleton(AIService, create_ai_service)
        self.container.register_singleton(
            SettingsService,
            lambda: SettingsService(self.settings, self.event_bus)
        )
        self.container.register_singleton(
            ImportExportService,
            lambda: ImportExportService(
                project_repository=self.container.get(IProjectRepository),
                document_repository=self.container.get(IDocumentRepository),
                event_bus=self.event_bus
            )
        )

        # 注册备份服务
        self.container.register_singleton(
            BackupService,
            lambda: BackupService(
                project_repository=self.container.get(IProjectRepository),
                document_repository=self.container.get(IDocumentRepository),
                backup_dir=self.settings.data_dir / "backups"
            )
        )

        # 注册模板服务
        self.container.register_singleton(
            TemplateService,
            lambda: TemplateService(
                templates_dir=self.settings.data_dir / "templates"
            )
        )

        # 注意：专属AI管理器已被统一AI服务替代

        # 注册状态服务
        self.container.register_singleton(
            StatusService,
            lambda: StatusService()
        )

        # 注册控制器（手动解析依赖）
        def create_main_controller():
            # 根据可用的AI架构选择服务
            if _new_ai_available:
                ai_service = self.container.get(AIOrchestrationService)
            else:
                ai_service = self.container.get(AIService)

            return MainController(
                app_service=self.container.get(ApplicationService),
                project_service=self.container.get(ProjectService),
                document_service=self.container.get(DocumentService),
                ai_service=ai_service,
                settings_service=self.container.get(SettingsService),
                search_service=self.container.get(SearchService),
                import_export_service=self.container.get(ImportExportService),
                # ai_assistant_manager 已被统一AI服务替代
                status_service=self.container.get(StatusService)
            )

        self.container.register_singleton(MainController, create_main_controller)

        # 在依赖注册完成后初始化AI服务
        if self._ai_services_need_initialization:
            logger.info("依赖注册完成，开始初始化AI服务...")
            self._initialize_ai_services_sync()
            self._ai_services_need_initialization = False

        return True
    
    @handle_initialization_error("应用服务初始化")
    def _initialize_services(self) -> bool:
        """初始化服务"""
        # 获取应用服务
        self.app_service = self.container.get(ApplicationService)

        # 初始化应用服务
        if not self.app_service.initialize():
            logger.error("应用服务初始化失败")
            return False

        return True
    
    @handle_initialization_error("用户界面创建")
    def _create_ui(self) -> bool:
        """创建用户界面"""
        # 确保在主线程中执行
        self._ensure_main_thread()

        # 创建插件管理器（在UI创建时初始化，确保依赖关系正确）
        from src.shared.plugins.plugin_manager import PluginManager
        self.plugin_manager = PluginManager(self)

        # 注册插件管理器到容器
        self.container.register_singleton(PluginManager, lambda: self.plugin_manager)

        # 获取主控制器
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
            # 从设置中获取主题
            theme_name = self.settings.ui.theme
            
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
        try:
            # 检查是否已有事件循环
            try:
                existing_loop = asyncio.get_event_loop()
                if existing_loop and not existing_loop.is_closed():
                    logger.debug("使用现有的异步事件循环")
                    return
            except RuntimeError:
                # 没有现有循环，创建新的
                pass

            # 创建基础事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            logger.debug("异步事件循环设置完成")

        except Exception as e:
            logger.error(f"设置异步事件循环失败: {e}")

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
                    providers_config = ai_orchestration.providers_config
                    logger.info(f"🔧 提供商配置: {list(providers_config.keys())}")
                except Exception as e:
                    logger.error(f"❌ 获取提供商配置失败: {e}")
                    return

                # 使用同步方式初始化，添加超时
                import asyncio

                # 创建新的事件循环来运行异步初始化
                logger.info("🔧 创建事件循环...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    logger.info("🔧 开始异步初始化...")
                    # 添加超时，避免卡死（增加到30秒）
                    result = loop.run_until_complete(
                        asyncio.wait_for(ai_orchestration.initialize(), timeout=30.0)
                    )
                    if result:
                        logger.info("✅ AI编排服务同步初始化完成")
                    else:
                        logger.error("❌ AI编排服务初始化返回False")
                except asyncio.TimeoutError:
                    logger.error("❌ AI服务初始化超时（5秒）")
                except Exception as e:
                    logger.error(f"❌ AI服务异步初始化失败: {e}")
                finally:
                    logger.info("🔧 关闭事件循环...")
                    loop.close()

            else:
                logger.warning("⚠️ AI编排服务未找到")

        except Exception as e:
            logger.error(f"❌ AI服务同步初始化失败: {e}")
            import traceback
            logger.error(f"❌ 异常详情: {traceback.format_exc()}")

    def _initialize_ai_services_async(self):
        """异步初始化AI服务"""
        logger.debug(f"检查AI服务初始化标志: {hasattr(self, '_ai_services_need_initialization')}")
        if hasattr(self, '_ai_services_need_initialization'):
            logger.debug(f"AI服务初始化标志值: {self._ai_services_need_initialization}")

        if not hasattr(self, '_ai_services_need_initialization') or not self._ai_services_need_initialization:
            logger.debug("跳过AI服务初始化：标志未设置或为False")
            return

        try:
            logger.info("🔄 调度AI服务异步初始化...")
            # 使用QTimer延迟执行，确保事件循环已经运行
            QTimer.singleShot(100, self._do_ai_services_initialization)
        except Exception as e:
            logger.error(f"调度AI服务初始化失败: {e}")

    def _do_ai_services_initialization(self):
        """执行AI服务初始化"""
        logger.info("🚀 开始执行AI服务初始化...")
        try:
            import asyncio

            async def initialize_ai_services():
                try:
                    logger.info("🔍 获取AI编排服务...")
                    ai_orchestration = self.container.get(AIOrchestrationService)
                    if ai_orchestration:
                        logger.info("🔧 开始初始化AI编排服务...")
                        logger.info(f"🔧 AI服务配置: {ai_orchestration.config}")
                        logger.info(f"🔧 提供商配置: {list(ai_orchestration.providers_config.keys())}")

                        result = await ai_orchestration.initialize()
                        if result:
                            logger.info("✅ AI编排服务异步初始化完成")
                        else:
                            logger.error("❌ AI编排服务初始化返回False")
                    else:
                        logger.warning("⚠️ AI编排服务未找到")
                except Exception as e:
                    logger.error(f"❌ AI服务异步初始化失败: {e}")
                    import traceback
                    logger.error(f"❌ 异常详情: {traceback.format_exc()}")

            # 创建任务
            try:
                loop = asyncio.get_event_loop()
                logger.debug(f"获取到事件循环: {loop}, 是否关闭: {loop.is_closed()}")
            except RuntimeError as e:
                logger.warning(f"获取事件循环失败: {e}")
                loop = None

            if loop and not loop.is_closed():
                logger.info("📋 创建AI服务初始化任务...")
                task = loop.create_task(initialize_ai_services())
                self._ai_services_need_initialization = False
                logger.info("✅ AI服务初始化任务已创建")

                # 添加任务完成回调
                def on_task_complete(task):
                    if task.exception():
                        logger.error(f"❌ AI服务初始化任务失败: {task.exception()}")
                    else:
                        logger.info("✅ AI服务初始化任务完成")

                task.add_done_callback(on_task_complete)
            else:
                logger.warning("⚠️ 事件循环不可用，跳过AI服务初始化")

        except Exception as e:
            logger.error(f"AI服务初始化执行失败: {e}")

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

            # 显示主窗口
            self.main_window.show()

            # 显示欢迎消息
            self._show_welcome_message()

            # 自动打开上次项目
            self._auto_open_last_project()

            # 使用标准Qt事件循环
            return self.app.exec()

        except Exception as e:
            logger.error(f"运行应用程序失败: {e}")
            self._show_error("运行错误", f"应用程序运行失败：{e}")
            return 1
        finally:
            self._cleanup()

    def _auto_open_last_project(self):
        """自动打开上次项目"""
        try:
            if not hasattr(self, 'main_controller') or not self.main_controller:
                logger.warning("主控制器未初始化，无法自动打开上次项目")
                return

            if not hasattr(self.main_controller, 'auto_open_last_project'):
                logger.warning("主控制器缺少auto_open_last_project方法")
                return

            # 延迟调用，确保界面完全加载
            QTimer.singleShot(500, self.main_controller.auto_open_last_project)
        except Exception as e:
            logger.error(f"自动打开上次项目失败: {e}")

    def _show_welcome_message(self):
        """显示欢迎消息"""
        try:
            # 检查用户偏好设置
            from src.shared.config.user_preferences import get_user_preferences
            user_prefs = get_user_preferences()

            # 如果用户选择不再显示，则跳过
            if not user_prefs.should_show_welcome_dialog():
                logger.debug("用户选择不再显示欢迎对话框，跳过显示")
                return

            # 延迟显示欢迎对话框
            QTimer.singleShot(2000, self._display_welcome_dialog)

        except Exception as e:
            logger.error(f"显示欢迎消息失败: {e}")

    def _display_welcome_dialog(self):
        """显示欢迎对话框"""
        try:
            from src.presentation.dialogs.welcome_dialog import WelcomeDialog
            from src.shared.config.user_preferences import get_user_preferences

            user_prefs = get_user_preferences()

            # 创建欢迎对话框
            welcome_dialog = WelcomeDialog(self.main_window)

            # 连接信号
            welcome_dialog.dont_show_again_changed.connect(
                lambda dont_show: user_prefs.set_show_welcome_dialog(not dont_show)
            )

            # 显示对话框
            welcome_dialog.exec()

            logger.debug("欢迎对话框显示完成")

        except Exception as e:
            logger.error(f"显示欢迎对话框失败: {e}")
            # 如果自定义对话框失败，回退到简单消息框
            self._show_fallback_welcome_message()

    def _show_fallback_welcome_message(self):
        """显示回退的欢迎消息（简单消息框）"""
        try:
            QMessageBox.information(
                self.main_window,
                "🎉 欢迎使用AI小说编辑器 2.0",
                """
                <h3>欢迎使用AI小说编辑器 2.0！</h3>

                <p><b>🏗️ 全新架构特性：</b></p>
                <ul>
                <li>🔧 现代化分层架构设计</li>
                <li>💉 依赖注入容器管理</li>
                <li>📡 事件驱动通信机制</li>
                <li>🗄️ 仓储模式数据访问</li>
                <li>🎨 响应式主题系统</li>
                <li>🤖 多AI服务集成</li>
                </ul>

                <p><b>🚀 开始创作：</b></p>
                <p>• 点击"文件 → 新建项目"创建项目</p>
                <p>• 使用右侧AI助手提升创作效率</p>
                <p>• 体验全新的写作体验！</p>

                <p style="color: #666; font-size: 10pt;">
                版本 2.0.0 | 基于现代化架构重构
                </p>
                """
            )
        except Exception as e:
            logger.error(f"显示回退欢迎消息失败: {e}")
    
    def _show_error(self, title: str, message: str):
        """显示错误消息"""
        if self.app:
            QMessageBox.critical(None, title, message)
        else:
            print(f"错误: {title} - {message}")
    
    def _cleanup(self):
        """清理资源"""
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
                    # 使用异步关闭方法
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        loop.run_until_complete(event_bus.shutdown_async())
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
            try:
                loop = asyncio.get_event_loop()
                if loop and not loop.is_closed():
                    # 取消所有待处理的任务
                    pending = asyncio.all_tasks(loop)
                    if pending:
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
                    loop.close()
            except RuntimeError as e:
                # 可能没有事件循环或已经关闭
                if "no current event loop" not in str(e).lower():
                    logger.error(f"关闭事件循环失败: {e}")
            except Exception as e:
                logger.error(f"关闭事件循环失败: {e}")

            logger.info("资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")


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

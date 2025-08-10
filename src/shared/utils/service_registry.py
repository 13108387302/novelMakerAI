#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务注册工厂

提供统一的服务注册模式，减少重复的依赖注入代码。
"""

from typing import Type, Callable, Any, Dict, List, Optional
from pathlib import Path

from src.shared.utils.logger import get_logger
from src.shared.constants import (
    DIR_PROJECTS, DIR_DOCUMENTS, DIR_CHARACTERS, DIR_WORLDBUILDING,
    DIR_PLOTS, DIR_VERSIONS, DIR_BACKUPS, DIR_TEMPLATES, DIR_SEARCH_INDEX
)

logger = get_logger(__name__)


class ServiceRegistryFactory:
    """
    服务注册工厂
    
    提供统一的服务注册模式，减少重复代码。
    """
    
    def __init__(self, container, settings, event_bus):
        """
        初始化服务注册工厂
        
        Args:
            container: 依赖注入容器
            settings: 应用程序设置
            event_bus: 事件总线
        """
        self.container = container
        self.settings = settings
        self.event_bus = event_bus
        # 尝试使用项目作用域数据目录，如果没有则使用默认目录
        try:
            from src.shared.project_context import ProjectPaths
            project_paths: ProjectPaths = self.container.get(ProjectPaths)
            self.data_dir = project_paths.data_dir
        except ValueError:
            # 项目路径还没有注册，使用默认数据目录
            from pathlib import Path
            import os
            default_data_dir = Path(os.path.expanduser("~")) / "AppData" / "Local" / "AI_Novel_Editor"
            default_data_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir = default_data_dir
            logger.debug("使用默认数据目录（项目路径未注册）")

        logger.debug("服务注册工厂初始化完成")
    
    def register_singleton(self, interface: Type, factory: Callable[[], Any]) -> None:
        """
        注册单例服务

        Args:
            interface: 服务接口类型
            factory: 服务工厂函数
        """
        self.container.register_singleton(interface, factory)
        interface_name = interface.__name__ if hasattr(interface, '__name__') else str(interface)
        logger.debug(f"注册单例服务: {interface_name}")
    
    def register_repository(self, interface: Type, implementation: Type, 
                          directory: str, *args, **kwargs) -> None:
        """
        注册仓储服务
        
        Args:
            interface: 仓储接口类型
            implementation: 仓储实现类型
            directory: 数据目录名称
            *args: 额外的构造参数
            **kwargs: 额外的关键字参数
        """
        def factory():
            path = self.data_dir / directory
            return implementation(path, *args, **kwargs)
        
        self.register_singleton(interface, factory)
    

    
    def register_repositories_batch(self) -> None:
        """批量注册仓储服务（使用项目内路径）"""
        from src.infrastructure.repositories.file_project_repository import FileProjectRepository
        from src.infrastructure.repositories.file_document_repository import FileDocumentRepository
        from src.domain.repositories.project_repository import IProjectRepository
        from src.domain.repositories.document_repository import IDocumentRepository
        from src.domain.repositories.ai_service_repository import IAIServiceRepository
        from src.shared.project_context import ProjectPaths

        project_paths: ProjectPaths = self.container.get(ProjectPaths)

        # 注册项目仓储（使用项目内data目录）
        self.container.register_singleton(
            IProjectRepository,
            lambda: FileProjectRepository(project_paths.data_dir / "projects")
        )

        # 注册文档仓储（使用项目内documents目录）
        self.container.register_singleton(
            IDocumentRepository,
            lambda: FileDocumentRepository(project_paths.documents_dir)
        )

        # 注册AI仓储接口适配到新编排服务（替代直接绑定客户端管理器）
        from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
        from src.infrastructure.ai.adapters.ai_service_repository_adapter import AIServiceRepositoryAdapter
        def _create_ai_repository_adapter():
            orchestration: AIOrchestrationService = self.container.get(AIOrchestrationService)
            return AIServiceRepositoryAdapter(orchestration)
        self.register_singleton(
            IAIServiceRepository,
            _create_ai_repository_adapter
        )

        logger.info("批量注册仓储服务完成")
    
    def register_core_services_batch(self) -> None:
        """批量注册核心应用服务"""
        from src.application.services.application_service import ApplicationService
        from src.application.services.project_service import ProjectService
        from src.application.services.document_service import DocumentService
        from src.application.services.search import SearchService
        from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
        from src.domain.repositories.project_repository import IProjectRepository
        from src.domain.repositories.document_repository import IDocumentRepository
        
        # 注册应用服务
        self.register_singleton(
            ApplicationService,
            lambda: ApplicationService(self.container, self.event_bus, self.settings)
        )
        
        # 注册项目服务
        self.register_singleton(
            ProjectService,
            lambda: ProjectService(self.container.get(IProjectRepository), self.event_bus)
        )
        
        # 注册搜索服务
        def create_search_service():
            return SearchService(
                project_repository=self.container.get(IProjectRepository),
                document_repository=self.container.get(IDocumentRepository),
                event_bus=self.event_bus,
                index_path=self.data_dir / DIR_SEARCH_INDEX
            )
        
        self.register_singleton(SearchService, create_search_service)
        
        # 注册文档服务
        def create_document_service():
            return DocumentService(
                document_repository=self.container.get(IDocumentRepository),
                event_bus=self.event_bus,
                search_service=self.container.get(SearchService)
            )
        
        self.register_singleton(DocumentService, create_document_service)
        
        logger.info("批量注册核心服务完成")
    
    def register_additional_services_batch(self) -> None:
        """批量注册其他应用服务"""
        from src.application.services.settings_service import SettingsService
        from src.application.services.import_export_service import ImportExportService
        from src.application.services.backup_service import BackupService
        from src.application.services.template_service import TemplateService
        from src.application.services.status_service import StatusService
        from src.domain.repositories.project_repository import IProjectRepository
        from src.domain.repositories.document_repository import IDocumentRepository
        
        # 服务配置列表
        services_config = [
            # (接口类型, 实现类型, 构造参数)
            (SettingsService, SettingsService, 
             lambda: SettingsService(self.settings, self.event_bus)),
            
            (ImportExportService, ImportExportService,
             lambda: ImportExportService(
                 project_repository=self.container.get(IProjectRepository),
                 document_repository=self.container.get(IDocumentRepository),
                 event_bus=self.event_bus
             )),
            
            (BackupService, BackupService,
             lambda: BackupService(
                 project_repository=self.container.get(IProjectRepository),
                 document_repository=self.container.get(IDocumentRepository),
                 backup_dir=self.data_dir / DIR_BACKUPS
             )),
            
            (TemplateService, TemplateService,
             lambda: TemplateService(templates_dir=self.data_dir / DIR_TEMPLATES)),
            
            (StatusService, StatusService,
             lambda: StatusService())
        ]
        
        # 批量注册服务
        for interface, implementation, factory in services_config:
            self.register_singleton(interface, factory)
        
        logger.info("批量注册其他服务完成")
    
    def register_ai_services_batch(self, new_ai_available: bool) -> bool:
        """
        批量注册AI服务
        
        Args:
            new_ai_available: 是否有新的AI架构可用
            
        Returns:
            bool: 是否需要初始化AI服务
        """
        if new_ai_available:
            return self._register_new_ai_architecture()
        else:
            self._register_fallback_ai_service()
            return False
    
    def _register_new_ai_architecture(self) -> bool:
        """注册新的AI架构服务"""
        from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
        from src.application.services.ai.intelligence.ai_intelligence_service import AIIntelligenceService
        from src.application.services.settings_service import SettingsService
        
        def create_ai_orchestration_service():
            settings_service = self.container.get(SettingsService)
            config = self._build_ai_config(settings_service)
            return AIOrchestrationService(config)

        def create_ai_intelligence_service():
            service = AIIntelligenceService()
            service.initialize()
            return service

        # 注册新架构服务
        self.register_singleton(AIOrchestrationService, create_ai_orchestration_service)
        self.register_singleton(AIIntelligenceService, create_ai_intelligence_service)

        # 为向后兼容，也注册一个AIService别名（供插件/旧代码获取）
        self.register_singleton('ai_service', create_ai_orchestration_service)
        self.register_singleton('AIService', create_ai_orchestration_service)

        logger.info("注册新AI架构服务完成")
        return True  # 需要初始化AI服务
    
    def _register_fallback_ai_service(self) -> None:
        """注册备用AI服务"""
        # 这里应该导入备用的AI服务类
        # 由于代码中有占位符实现，我们使用它
        def create_ai_service():
            # 返回占位符AI服务
            class AIService:
                def process_request(self, *args, **kwargs):
                    raise RuntimeError("AI服务不可用，请检查AI模块安装")
            return AIService()
        
        self.register_singleton('AIService', create_ai_service)
        logger.info("注册备用AI服务完成")
    
    def _build_ai_config(self, settings_service) -> dict:
        """构建AI服务配置"""
        from src.shared.constants import ASYNC_MEDIUM_TIMEOUT

        def _sanitize_api_key(raw):
            try:
                if not raw or not isinstance(raw, str):
                    return ''
                s = raw.strip()
                # 过滤明显的日志串/中文提示等异常值
                if 'WARNING' in s or 'AI设置不可用' in s or '错误' in s or '|' in s:
                    return ''
                # 若包含非ASCII字符，视为无效，避免客户端底层编码异常
                try:
                    s.encode('ascii')
                except UnicodeEncodeError:
                    return ''
                return s
            except Exception:
                return ''

        return {
            'providers': {
                'openai': {
                    'api_key': _sanitize_api_key(settings_service.get_setting('ai.openai_api_key', '')),
                    'base_url': settings_service.get_setting('ai.openai_base_url', 'https://api.openai.com/v1'),
                    'default_model': settings_service.get_setting('ai.openai_model', 'gpt-3.5-turbo')
                },
                'deepseek': {
                    'api_key': _sanitize_api_key(settings_service.get_setting('ai.deepseek_api_key', '')),
                    'base_url': settings_service.get_setting('ai.deepseek_base_url', 'https://api.deepseek.com/v1'),
                    'default_model': settings_service.get_setting('ai.deepseek_model', 'deepseek-chat')
                }
            },
            'default_provider': settings_service.get_setting('ai.default_provider', 'deepseek'),
            'max_concurrent_requests': settings_service.get_setting('ai.max_concurrent_requests', 10),
            'request_timeout': settings_service.get_setting('ai.request_timeout', ASYNC_MEDIUM_TIMEOUT)
        }

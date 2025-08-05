#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI组件工厂 - 优化统一版本

提供统一的AI组件创建和管理功能，确保架构一致性和高性能
"""

from typing import Optional, Dict, Any, Type, Union, List
from enum import Enum
from PyQt6.QtWidgets import QWidget
import time

from .ai_widget_base import BaseAIWidget, AIWidgetConfig, AIWidgetTheme, AIWidgetPriority
from .global_ai_panel_v2 import GlobalAIPanel
from .document_ai_panel_v2 import DocumentAIPanel
from .conversation_widget import ConversationWidget
from .content_generation_widget import ContentGenerationWidget
from src.application.services.unified_ai_service import UnifiedAIService
from src.shared.utils.logger import get_logger
from src.shared.events.event_bus import EventBus

logger = get_logger(__name__)


class AIComponentType(Enum):
    """AI组件类型 - 扩展版本"""
    # 主要面板
    GLOBAL_PANEL = "global_panel"
    DOCUMENT_PANEL = "document_panel"

    # 功能组件
    CONVERSATION = "conversation"
    CONTENT_GENERATION = "content_generation"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    WRITING_ASSISTANT = "writing_assistant"

    # 专业组件
    CHAT_PANEL = "chat_panel"
    ANALYSIS_PANEL = "analysis_panel"
    PROJECT_ANALYZER = "project_analyzer"
    CHARACTER_GENERATOR = "character_generator"
    PLOT_GENERATOR = "plot_generator"


class AIComponentPreset(Enum):
    """AI组件预设配置"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    ADVANCED = "advanced"
    PROFESSIONAL = "professional"


class AIComponentFactory:
    """
    AI组件工厂
    
    负责创建和配置各种AI组件，确保：
    - 统一的配置管理
    - 一致的主题应用
    - 正确的依赖注入
    - 标准化的事件连接
    """
    
    def __init__(
        self,
        ai_service: UnifiedAIService,
        event_bus: EventBus,
        default_config: Optional[AIWidgetConfig] = None,
        default_theme: Optional[AIWidgetTheme] = None
    ):
        """初始化AI组件工厂"""
        logger.debug("开始初始化AI组件工厂...")

        self.ai_service = ai_service
        self.event_bus = event_bus
        logger.debug("基础服务设置完成")

        # 预设配置必须在_create_default_config之前初始化
        self._presets: Dict[AIComponentPreset, AIWidgetConfig] = {}
        logger.debug("预设配置字典初始化完成")

        self.default_config = default_config or self._create_default_config()
        self.default_theme = default_theme or self._create_default_theme()
        logger.debug("默认配置和主题设置完成")

        # 组件注册表
        self._component_registry: Dict[AIComponentType, Type[BaseAIWidget]] = {}
        self._component_configs: Dict[AIComponentType, Dict[str, Any]] = {}
        logger.debug("组件注册表初始化完成")

        # 活跃组件跟踪
        self._active_components: Dict[str, BaseAIWidget] = {}
        logger.debug("活跃组件跟踪初始化完成")

        # 性能监控
        self._creation_count = 0
        self._creation_times: List[float] = []
        logger.debug("性能监控初始化完成")

        # 注册默认组件和预设
        try:
            self._register_default_components()
            logger.debug("默认组件注册完成")
        except Exception as e:
            logger.error(f"默认组件注册失败: {e}")

        try:
            self._register_default_presets()
            logger.debug("默认预设注册完成")
        except Exception as e:
            logger.error(f"默认预设注册失败: {e}")
            # 确保_presets属性存在
            if not hasattr(self, '_presets'):
                self._presets = {}

        logger.info("AI组件工厂初始化完成（优化版本）")
    
    def _register_default_components(self):
        """注册默认组件"""
        # 主要面板
        self._component_registry[AIComponentType.GLOBAL_PANEL] = GlobalAIPanel
        self._component_registry[AIComponentType.DOCUMENT_PANEL] = DocumentAIPanel

        # 功能组件
        try:
            self._component_registry[AIComponentType.CONVERSATION] = ConversationWidget
            self._component_registry[AIComponentType.CONTENT_GENERATION] = ContentGenerationWidget
        except ImportError:
            logger.warning("部分AI组件类未找到，将跳过注册")

        logger.debug(f"已注册 {len(self._component_registry)} 个AI组件类型")

    def _register_default_presets(self):
        """注册默认预设配置"""
        try:
            # 确保_presets属性存在
            if not hasattr(self, '_presets'):
                self._presets = {}

            # 最小配置
            minimal_config = AIWidgetConfig()
            minimal_config.enable_streaming = False
            minimal_config.show_token_count = False
            minimal_config.show_performance_stats = False
            if hasattr(minimal_config, 'compact_mode'):
                minimal_config.compact_mode = True
            self._presets[AIComponentPreset.MINIMAL] = minimal_config

            # 标准配置
            standard_config = AIWidgetConfig()
            standard_config.enable_streaming = True
            standard_config.show_token_count = True
            if hasattr(standard_config, 'enable_context_awareness'):
                standard_config.enable_context_awareness = True
            self._presets[AIComponentPreset.STANDARD] = standard_config

            # 高级配置
            advanced_config = AIWidgetConfig()
            advanced_config.enable_streaming = True
            advanced_config.show_token_count = True
            advanced_config.show_performance_stats = True
            if hasattr(advanced_config, 'enable_context_awareness'):
                advanced_config.enable_context_awareness = True
            if hasattr(advanced_config, 'enable_suggestions'):
                advanced_config.enable_suggestions = True
            if hasattr(advanced_config, 'enable_shortcuts'):
                advanced_config.enable_shortcuts = True
            self._presets[AIComponentPreset.ADVANCED] = advanced_config

            # 专业配置
            professional_config = AIWidgetConfig()
            professional_config.enable_streaming = True
            professional_config.show_token_count = True
            professional_config.show_performance_stats = True
            if hasattr(professional_config, 'enable_context_awareness'):
                professional_config.enable_context_awareness = True
            if hasattr(professional_config, 'enable_suggestions'):
                professional_config.enable_suggestions = True
            if hasattr(professional_config, 'enable_shortcuts'):
                professional_config.enable_shortcuts = True
            if hasattr(professional_config, 'show_advanced_options'):
                professional_config.show_advanced_options = True
            if hasattr(professional_config, 'max_concurrent_requests'):
                professional_config.max_concurrent_requests = 3
            self._presets[AIComponentPreset.PROFESSIONAL] = professional_config

            logger.debug(f"已注册 {len(self._presets)} 个预设配置")

        except Exception as e:
            logger.error(f"注册默认预设失败: {e}")
            # 确保_presets属性存在，即使注册失败
            if not hasattr(self, '_presets'):
                self._presets = {}

    def _create_default_config(self) -> AIWidgetConfig:
        """创建默认配置"""
        # 如果_presets还没有初始化或为空，直接返回新的AIWidgetConfig
        if not hasattr(self, '_presets') or not self._presets:
            return AIWidgetConfig()
        return self._presets.get(AIComponentPreset.STANDARD, AIWidgetConfig())

    def _create_default_theme(self) -> AIWidgetTheme:
        """创建默认主题"""
        return AIWidgetTheme()
    
    def create_global_panel(
        self, 
        parent: Optional[QWidget] = None,
        config: Optional[AIWidgetConfig] = None,
        theme: Optional[AIWidgetTheme] = None
    ) -> GlobalAIPanel:
        """创建全局AI面板"""
        try:
            # 使用提供的配置或默认配置
            final_config = config or self.default_config
            final_theme = theme or self.default_theme
            
            # 创建组件
            panel = GlobalAIPanel(
                ai_service=self.ai_service,
                parent=parent,
                config=final_config
            )
            
            # 应用主题
            panel.theme = final_theme
            panel._apply_theme()
            
            # 连接事件
            self._connect_component_events(panel)
            
            # 注册组件
            component_id = f"global_panel_{id(panel)}"
            self._active_components[component_id] = panel
            
            logger.info(f"创建全局AI面板: {component_id}")
            return panel
            
        except Exception as e:
            logger.error(f"创建全局AI面板失败: {e}")
            raise
    
    def create_document_panel(
        self,
        document_id: str,
        document_type: str = "chapter",
        parent: Optional[QWidget] = None,
        config: Optional[AIWidgetConfig] = None,
        theme: Optional[AIWidgetTheme] = None
    ) -> DocumentAIPanel:
        """创建文档AI面板"""
        try:
            # 使用提供的配置或默认配置
            final_config = config or self.default_config
            final_theme = theme or self.default_theme
            
            # 为文档面板优化配置
            doc_config = AIWidgetConfig()
            doc_config.__dict__.update(final_config.__dict__)
            doc_config.enable_context_awareness = True  # 文档面板必须启用上下文感知
            
            # 创建组件
            panel = DocumentAIPanel(
                ai_service=self.ai_service,
                document_id=document_id,
                document_type=document_type,
                parent=parent,
                config=doc_config
            )
            
            # 应用主题
            panel.theme = final_theme
            panel._apply_theme()
            
            # 连接事件
            self._connect_component_events(panel)
            self._connect_document_panel_events(panel)
            
            # 注册组件
            component_id = f"doc_panel_{document_id}"
            self._active_components[component_id] = panel
            
            logger.info(f"创建文档AI面板: {component_id}")
            return panel
            
        except Exception as e:
            logger.error(f"创建文档AI面板失败: {e}")
            raise
    
    def _connect_component_events(self, component: BaseAIWidget):
        """连接组件通用事件"""
        # 连接到事件总线
        component.request_started.connect(
            lambda req_id: self.event_bus.publish(AIRequestStartedEvent(req_id, component.widget_id))
        )
        component.request_completed.connect(
            lambda req_id, content: self.event_bus.publish(AIRequestCompletedEvent(req_id, component.widget_id, content))
        )
        component.request_failed.connect(
            lambda req_id, error: self.event_bus.publish(AIRequestFailedEvent(req_id, component.widget_id, error))
        )
        component.status_changed.connect(
            lambda msg, level: logger.debug(f"[{component.widget_id}] {level}: {msg}")
        )
    
    def _connect_document_panel_events(self, panel: DocumentAIPanel):
        """连接文档面板特定事件"""
        # 文档操作事件
        panel.text_insert_requested.connect(
            lambda text: self.event_bus.publish(TextInsertRequestedEvent(panel.document_id, text))
        )
        panel.text_replace_requested.connect(
            lambda text: self.event_bus.publish(TextReplaceRequestedEvent(panel.document_id, text))
        )
    
    def get_component(self, component_id: str) -> Optional[BaseAIWidget]:
        """获取组件"""
        return self._active_components.get(component_id)
    
    def remove_component(self, component_id: str) -> bool:
        """移除组件"""
        if component_id in self._active_components:
            component = self._active_components[component_id]
            
            # 断开连接
            try:
                component.deleteLater()
            except:
                pass
            
            # 从注册表移除
            del self._active_components[component_id]
            
            logger.info(f"移除AI组件: {component_id}")
            return True
        
        return False
    
    def get_active_components(self) -> Dict[str, BaseAIWidget]:
        """获取所有活跃组件"""
        return self._active_components.copy()
    
    def cleanup_all_components(self):
        """清理所有组件"""
        for component_id in list(self._active_components.keys()):
            self.remove_component(component_id)
        
        logger.info("所有AI组件已清理")
    
    def register_component_type(self, component_type: AIComponentType, component_class: Type[BaseAIWidget]):
        """注册新的组件类型"""
        self._component_registry[component_type] = component_class
        logger.info(f"注册AI组件类型: {component_type.value}")
    
    def create_component(
        self,
        component_type: AIComponentType,
        **kwargs
    ) -> Optional[BaseAIWidget]:
        """通用组件创建方法"""
        component_class = self._component_registry.get(component_type)
        if not component_class:
            logger.error(f"未知的组件类型: {component_type.value}")
            return None
        
        try:
            # 根据组件类型调用相应的创建方法
            if component_type == AIComponentType.GLOBAL_PANEL:
                return self.create_global_panel(**kwargs)
            elif component_type == AIComponentType.DOCUMENT_PANEL:
                return self.create_document_panel(**kwargs)
            else:
                # 通用创建逻辑
                config = kwargs.pop('config', self.default_config)
                theme = kwargs.pop('theme', self.default_theme)
                parent = kwargs.pop('parent', None)
                widget_id = kwargs.pop('widget_id', f"{component_type.value}_{int(time.time() * 1000)}")

                component = component_class(
                    ai_service=self.ai_service,
                    widget_id=widget_id,
                    parent=parent,
                    config=config,
                    theme=theme,
                    **kwargs
                )

                self._connect_component_events(component)

                component_id = widget_id
                self._active_components[component_id] = component

                return component
                
        except Exception as e:
            logger.error(f"创建组件失败 {component_type.value}: {e}")
            return None

    # 新增组件管理方法

    def create_component_with_preset(
        self,
        component_type: AIComponentType,
        preset: AIComponentPreset,
        component_id: Optional[str] = None,
        parent: Optional[QWidget] = None,
        **kwargs
    ) -> Optional[BaseAIWidget]:
        """使用预设创建组件"""
        preset_config = self._presets.get(preset)
        if not preset_config:
            logger.warning(f"未找到预设配置: {preset}")
            preset_config = self.default_config

        return self.create_component(
            component_type=component_type,
            config=preset_config,
            parent=parent,
            **kwargs
        )



    def get_factory_statistics(self) -> Dict[str, Any]:
        """获取工厂统计信息"""
        avg_creation_time = (
            sum(self._creation_times) / len(self._creation_times)
            if self._creation_times else 0
        )

        return {
            'total_created': self._creation_count,
            'active_components': len(self._active_components),
            'avg_creation_time': avg_creation_time,
            'registered_types': len(self._component_registry),
            'available_presets': len(self._presets)
        }


# AI事件定义（用于事件总线）

from dataclasses import dataclass
from src.shared.events.event_bus import Event

@dataclass
class AIRequestStartedEvent(Event):
    """AI请求开始事件"""
    request_id: str = ""
    component_id: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_component"

@dataclass
class AIRequestCompletedEvent(Event):
    """AI请求完成事件"""
    request_id: str = ""
    component_id: str = ""
    content: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_component"

@dataclass
class AIRequestFailedEvent(Event):
    """AI请求失败事件"""
    request_id: str = ""
    component_id: str = ""
    error: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_component"

@dataclass
class TextInsertRequestedEvent(Event):
    """文本插入请求事件"""
    document_id: str = ""
    text: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_ai_panel"

@dataclass
class TextReplaceRequestedEvent(Event):
    """文本替换请求事件"""
    document_id: str = ""
    text: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_ai_panel"


# 全局工厂实例（延迟初始化）
_global_factory: Optional[AIComponentFactory] = None

def get_ai_component_factory() -> Optional[AIComponentFactory]:
    """获取全局AI组件工厂"""
    return _global_factory

def initialize_ai_component_factory(
    ai_service: UnifiedAIService,
    event_bus: EventBus,
    config: Optional[AIWidgetConfig] = None,
    theme: Optional[AIWidgetTheme] = None
) -> AIComponentFactory:
    """初始化全局AI组件工厂"""
    global _global_factory
    _global_factory = AIComponentFactory(ai_service, event_bus, config, theme)
    logger.info("全局AI组件工厂已初始化")
    return _global_factory

def cleanup_ai_component_factory():
    """清理全局AI组件工厂"""
    global _global_factory
    if _global_factory:
        _global_factory.cleanup_all_components()
        _global_factory = None
        logger.info("全局AI组件工厂已清理")

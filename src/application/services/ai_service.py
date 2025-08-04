#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助手服务 - 重构版本

管理AI功能的调用和处理，使用组件化架构
"""

from typing import Optional, Dict, Any, AsyncGenerator, List
from datetime import datetime
from abc import ABCMeta

from PyQt6.QtCore import QObject, pyqtSignal


from .ai.base_ai_service import BaseAIService, IAIService, QABCMeta
from .ai.streaming_ai_service import StreamingAIService
from .ai.content_generation_service import ContentGenerationService
from .ai.analysis_service import AnalysisService

from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class AIService(QObject, IAIService, metaclass=QABCMeta):
    """
    AI助手服务 - 重构版本

    作为各个AI服务组件的协调者和统一接口，提供完整的AI功能管理。
    整合流式生成、内容生成和分析服务，提供统一的API接口。

    实现方式：
    - 使用组合模式整合多个AI服务组件
    - 继承QObject提供信号槽机制
    - 实现IAIService接口确保API一致性
    - 提供统一的错误处理和状态管理
    - 支持异步操作和流式响应

    Attributes:
        streaming_service: 流式AI服务组件
        content_service: 内容生成服务组件
        analysis_service: 分析服务组件
        ai_repository: AI服务仓储
        event_bus: 事件总线

    Signals:
        request_started: 请求开始信号
        request_completed: 请求完成信号
        request_failed: 请求失败信号
        streaming_started: 流式生成开始信号
        streaming_stopped: 流式生成停止信号
        chunk_received: 接收到数据块信号
        streaming_completed: 流式生成完成信号
        streaming_error: 流式生成错误信号
        streaming_progress: 流式生成进度信号
    """

    # 统一信号
    request_started = pyqtSignal(str)  # 请求ID
    request_completed = pyqtSignal(str, str)  # 请求ID, 响应内容
    request_failed = pyqtSignal(str, str)  # 请求ID, 错误信息

    # 流式生成信号
    streaming_started = pyqtSignal()
    streaming_stopped = pyqtSignal()
    chunk_received = pyqtSignal(str)
    streaming_completed = pyqtSignal(str)
    streaming_error = pyqtSignal(str)
    streaming_progress = pyqtSignal(int)
    
    def __init__(
        self,
        ai_repository: IAIServiceRepository,
        event_bus: EventBus
    ):
        """
        初始化AI服务

        创建AI服务实例并初始化所有子服务组件。
        设置依赖注入和信号连接。

        实现方式：
        - 调用QObject的初始化方法
        - 保存依赖注入的仓储和事件总线
        - 初始化流式服务、内容生成服务和分析服务
        - 连接各组件的信号到统一接口

        Args:
            ai_repository: AI服务仓储接口
            event_bus: 事件总线用于组件间通信
        """
        super().__init__()
        self.ai_repository = ai_repository
        self.event_bus = event_bus

        # 初始化各个AI服务组件
        self._init_services()

        # 连接信号
        self._connect_signals()

    def _init_services(self):
        """
        初始化AI服务组件

        创建并配置所有AI服务子组件，包括流式服务、内容生成服务和分析服务。
        每个组件都使用相同的仓储和事件总线确保一致性。

        实现方式：
        - 创建StreamingAIService处理流式AI响应
        - 创建ContentGenerationService处理内容生成
        - 创建AnalysisService处理文本分析
        - 传递共享的依赖确保组件协调工作
        - 验证所有服务是否成功初始化
        """
        try:
            # 流式AI服务
            self.streaming_service = StreamingAIService(
                self.ai_repository, self.event_bus
            )

            # 内容生成服务
            self.content_service = ContentGenerationService(
                self.ai_repository, self.event_bus
            )

            # 分析服务
            self.analysis_service = AnalysisService(
                self.ai_repository, self.event_bus
            )

            # 验证服务初始化
            services = [
                ("streaming_service", self.streaming_service),
                ("content_service", self.content_service),
                ("analysis_service", self.analysis_service)
            ]

            for name, service in services:
                if service is None:
                    raise RuntimeError(f"AI服务组件初始化失败: {name}")

            logger.info("AI服务组件初始化完成")

        except Exception as e:
            logger.error(f"AI服务组件初始化失败: {e}")
            raise
        
    def _connect_signals(self):
        """连接各个服务的信号"""
        # 流式服务信号
        self.streaming_service.streaming_started.connect(self.streaming_started)
        self.streaming_service.streaming_stopped.connect(self.streaming_stopped)
        self.streaming_service.chunk_received.connect(self.chunk_received)
        self.streaming_service.streaming_completed.connect(self.streaming_completed)
        self.streaming_service.streaming_error.connect(self.streaming_error)
        self.streaming_service.streaming_progress.connect(self.streaming_progress)
        
        # 基础请求信号
        for service in [self.streaming_service, self.content_service, self.analysis_service]:
            service.request_started.connect(self.request_started)
            service.request_completed.connect(self.request_completed)
            service.request_failed.connect(self.request_failed)
            
    # 实现IAIService接口
    async def generate_text(self, prompt: str, context: str = "") -> str:
        """生成文本"""
        return await self.content_service.generate_text(prompt, context)
        
    async def generate_text_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """流式生成文本"""
        async for chunk in self.streaming_service.generate_text_stream(prompt, context):
            yield chunk
            
    async def check_service_availability(self) -> bool:
        """检查服务可用性"""
        return await self.content_service.check_service_availability()
        
    def get_supported_features(self) -> list[str]:
        """获取支持的功能"""
        all_features = []
        for service in [self.streaming_service, self.content_service, self.analysis_service]:
            all_features.extend(service.get_supported_features())
        return list(set(all_features))  # 去重
        
    # 内容生成功能
    async def generate_continuation(
        self,
        content: str,
        context: str = "",
        style_requirements: Optional[str] = None,
        length_requirement: Optional[str] = None
    ) -> str:
        """生成续写内容"""
        return await self.content_service.generate_continuation(
            content, context, style_requirements, length_requirement
        )
        
    async def improve_dialogue(
        self,
        dialogue: str,
        improvement_type: str = "natural",
        character_info: Optional[str] = None
    ) -> str:
        """改进对话"""
        return await self.content_service.improve_dialogue(
            dialogue, improvement_type, character_info
        )
        
    async def expand_scene(
        self,
        scene: str,
        expansion_focus: str = "atmosphere",
        setting_info: Optional[str] = None
    ) -> str:
        """扩展场景描写"""
        return await self.content_service.expand_scene(
            scene, expansion_focus, setting_info
        )
        
    async def generate_character_description(
        self,
        character_name: str,
        character_traits: Optional[str] = None,
        story_context: Optional[str] = None,
        description_style: str = "detailed"
    ) -> str:
        """生成角色描述"""
        return await self.content_service.generate_character_description(
            character_name, character_traits, story_context, description_style
        )
        
    async def generate_plot_outline(
        self,
        story_theme: str,
        genre: Optional[str] = None,
        target_length: Optional[str] = None,
        key_elements: Optional[str] = None
    ) -> str:
        """生成情节大纲"""
        return await self.content_service.generate_plot_outline(
            story_theme, genre, target_length, key_elements
        )
        
    # 分析功能
    async def analyze_style(
        self,
        text: str,
        analysis_aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析文本风格"""
        return await self.analysis_service.analyze_style(text, analysis_aspects)
        
    async def analyze_plot(
        self,
        text: str,
        analysis_type: str = "structure"
    ) -> Dict[str, Any]:
        """分析情节结构"""
        return await self.analysis_service.analyze_plot(text, analysis_type)
        
    async def analyze_characters(
        self,
        text: str,
        focus_characters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析角色特征"""
        return await self.analysis_service.analyze_characters(text, focus_characters)
        
    async def analyze_themes(
        self,
        text: str,
        theme_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析主题内容"""
        return await self.analysis_service.analyze_themes(text, theme_categories)
        
    async def analyze_readability(
        self,
        text: str,
        target_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析可读性"""
        return await self.analysis_service.analyze_readability(text, target_audience)
        
    async def generate_summary(
        self,
        text: str,
        summary_type: str = "brief",
        max_length: Optional[int] = None
    ) -> str:
        """生成文本摘要"""
        return await self.analysis_service.generate_summary(text, summary_type, max_length)
        
    # 流式生成功能
    def start_streaming(self, prompt: str, context: str = "") -> bool:
        """开始流式生成"""
        return self.streaming_service.start_streaming(prompt, context)
        
    def stop_streaming(self):
        """停止流式生成"""
        self.streaming_service.stop_streaming()
        
    def is_streaming(self) -> bool:
        """检查是否正在流式生成"""
        return self.streaming_service.is_streaming()
        
    async def generate_streaming_continuation(self, content: str, context: str = "") -> bool:
        """生成流式续写"""
        return await self.streaming_service.generate_streaming_continuation(content, context)
        
    async def generate_streaming_dialogue_improvement(self, dialogue: str) -> bool:
        """生成流式对话优化"""
        return await self.streaming_service.generate_streaming_dialogue_improvement(dialogue)
        
    async def generate_streaming_scene_expansion(self, scene: str) -> bool:
        """生成流式场景扩展"""
        return await self.streaming_service.generate_streaming_scene_expansion(scene)
        
    # 管理功能
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃的请求"""
        all_requests = {}
        for service in [self.streaming_service, self.content_service, self.analysis_service]:
            all_requests.update(service.get_active_requests())
        return all_requests
        
    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        for service in [self.streaming_service, self.content_service, self.analysis_service]:
            if service.cancel_request(request_id):
                return True
        return False
        
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        all_stats = {}
        for service_name, service in [
            ("streaming", self.streaming_service),
            ("content", self.content_service),
            ("analysis", self.analysis_service)
        ]:
            try:
                stats = await service.get_usage_statistics()
                all_stats[service_name] = stats
            except Exception as e:
                logger.warning(f"获取{service_name}服务统计失败: {e}")
                all_stats[service_name] = {"error": str(e)}
                
        return all_stats
        
    def get_streaming_status(self) -> dict:
        """获取流式生成状态"""
        return self.streaming_service.get_streaming_status()
        
    # 便捷方法
    def get_service(self, service_type: str):
        """获取特定类型的服务"""
        services = {
            "streaming": self.streaming_service,
            "content": self.content_service,
            "analysis": self.analysis_service
        }
        return services.get(service_type)
        
    def get_all_services(self) -> Dict[str, BaseAIService]:
        """获取所有服务"""
        return {
            "streaming": self.streaming_service,
            "content": self.content_service,
            "analysis": self.analysis_service
        }

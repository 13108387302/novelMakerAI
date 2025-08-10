#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI编排服务

负责协调和编排AI请求的处理流程，是AI服务的主要入口点
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime

from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode
from src.domain.ai.value_objects.ai_priority import AIPriority
from src.domain.ai.value_objects.ai_capability import AICapability

from src.infrastructure.ai.unified_ai_client_manager import get_unified_ai_client_manager, UnifiedAIClientManager
from src.shared.constants import (
    AI_MAX_CONCURRENT_REQUESTS, AI_TIMEOUT_SECONDS, AI_RETRY_ATTEMPTS
)

logger = logging.getLogger(__name__)

# AI编排服务常量
DEFAULT_AI_PROVIDER = 'deepseek'  # 更新默认提供商
OPENAI_PROVIDER = 'openai'
DEEPSEEK_PROVIDER = 'deepseek'


class AIOrchestrationService:
    """
    AI编排服务 - 重构版本

    负责协调AI请求的完整处理流程，使用统一AI客户端管理器：
    - 请求验证和预处理
    - 委托给统一客户端管理器处理
    - 错误处理和重试机制
    - 性能监控和质量评估

    重构改进：
    - 移除重复的客户端管理逻辑
    - 委托给UnifiedAIClientManager处理具体实现
    - 专注于业务编排逻辑
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI编排服务

        Args:
            config: 服务配置
        """
        self.config = config
        self.is_initialized = False

        # 使用统一AI客户端管理器
        self.client_manager = get_unified_ai_client_manager(config)

        # 性能配置
        self.max_concurrent_requests = config.get('max_concurrent_requests', AI_MAX_CONCURRENT_REQUESTS)
        self.request_timeout = config.get('request_timeout', AI_TIMEOUT_SECONDS)
        self.retry_attempts = config.get('retry_attempts', AI_RETRY_ATTEMPTS)

        # 请求队列和限流（委托给客户端管理器）
        self.active_requests: Dict[str, AIRequest] = {}

        # 统计信息（委托给客户端管理器）
        self.start_time = datetime.now()

    async def initialize(self) -> bool:
        """
        初始化服务

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 客户端管理器已经在构造函数中初始化
            self.is_initialized = True
            logger.info("AI编排服务初始化成功")
            return True

        except Exception as e:
            logger.error(f"AI编排服务初始化失败: {e}")
            return False

    def reload_settings(self, new_config: Optional[Dict[str, Any]] = None) -> None:
        """应用新的AI配置到编排服务与客户端管理器"""
        try:
            if new_config:
                self.config.update(new_config)
            if hasattr(self.client_manager, 'update_config'):
                self.client_manager.update_config(self.config)
            logger.info("AI编排服务配置已刷新")
        except Exception as e:
            logger.warning(f"重载AI配置失败: {e}")

    async def process_request(
        self,
        request: AIRequest,
        use_streaming: bool = False,
        preferred_provider: Optional[str] = None
    ) -> AIResponse:
        """
        处理AI请求 - 委托给统一客户端管理器

        Args:
            request: AI请求
            use_streaming: 是否使用流式输出
            preferred_provider: 首选提供商

        Returns:
            AIResponse: AI响应
        """
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")

        # 委托给统一客户端管理器处理
        try:
            if use_streaming:
                # 流式处理
                response_content = ""
                async for chunk in self.client_manager.generate_text_stream(
                    prompt=request.prompt,
                    context=request.context,
                    max_tokens=request.parameters.get('max_tokens', 2000),
                    temperature=request.parameters.get('temperature', 0.7),
                    model=request.parameters.get('model'),
                    provider=preferred_provider
                ):
                    response_content += chunk

                # 创建响应对象
                from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
                response = AIResponse(
                    request_id=request.id,
                    content=response_content,
                    status=AIResponseStatus.COMPLETED,
                    provider=preferred_provider or self.client_manager.default_provider
                )
                return response
            else:
                # 非流式处理
                response_content = await self.client_manager.simple_generate(
                    prompt=request.prompt,
                    context=request.context,
                    max_tokens=request.parameters.get('max_tokens', 2000),
                    temperature=request.parameters.get('temperature', 0.7),
                    model=request.parameters.get('model'),
                    provider=preferred_provider
                )

                # 创建响应对象
                from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
                response = AIResponse(
                    request_id=request.id,
                    content=response_content,
                    status=AIResponseStatus.COMPLETED,
                    provider=preferred_provider or self.client_manager.default_provider
                )
                return response

        except Exception as e:
            logger.error(f"处理AI请求失败: {e}")
            from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
            response = AIResponse(
                request_id=request.id,
                content="",
                status=AIResponseStatus.FAILED,
                error=str(e),
                provider=preferred_provider or self.client_manager.default_provider
            )
            return response

    async def process_request_stream(
        self,
        request: AIRequest,
        preferred_provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式处理AI请求 - 委托给统一客户端管理器

        Args:
            request: AI请求
            preferred_provider: 首选提供商

        Yields:
            str: 响应文本块
        """
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")

        # 委托给统一客户端管理器处理
        async for chunk in self.client_manager.generate_text_stream(
            prompt=request.prompt,
            context=request.context,
            max_tokens=request.parameters.get('max_tokens', 2000),
            temperature=request.parameters.get('temperature', 0.7),
            model=request.parameters.get('model'),
            provider=preferred_provider
        ):
            yield chunk

    async def get_available_providers(self) -> List[str]:
        """
        获取可用的提供商列表 - 基于统一客户端管理器

        Returns:
            List[str]: 可用提供商名称列表
        """
        # 统一客户端管理器提供同步获取支持的提供商
        return self.client_manager.get_supported_providers()

    async def get_provider_capabilities(self, provider: str) -> List[AICapability]:
        """
        获取提供商支持的能力 - 委托给统一客户端管理器

        Args:
            provider: 提供商名称

        Returns:
            List[AICapability]: 支持的能力列表
        """
        # 委托给统一客户端管理器
        client_result = await self.client_manager.get_client(provider)
        if client_result.success:
            return await client_result.data.get_capabilities()
        return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息 - 委托给统一客户端管理器

        Returns:
            Dict[str, Any]: 统计信息
        """
        uptime = (datetime.now() - self.start_time).total_seconds()

        # 从客户端管理器获取统计信息
        client_stats = self.client_manager.get_statistics() if hasattr(self.client_manager, 'get_statistics') else {}

        return {
            'is_initialized': self.is_initialized,
            'uptime_seconds': uptime,
            'active_requests': len(self.active_requests),
            'client_manager_stats': client_stats
        }
    async def shutdown(self) -> None:
        """关闭服务 - 委托给统一客户端管理器"""
        logger.info("正在关闭AI编排服务...")

        # 设置关闭标志
        self.is_initialized = False

        # 清理活动请求
        self.active_requests.clear()

        # 客户端管理器会处理客户端的关闭
        logger.info("AI编排服务已关闭")


    # 兼容旧API：直接生成文本
    async def generate_text(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")
        return await self.client_manager.simple_generate(
            prompt=prompt,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            provider=provider
        )

    # 兼容旧API：流式生成文本
    async def generate_text_stream(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")
        async for chunk in self.client_manager.generate_text_stream(
            prompt=prompt,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            provider=provider
        ):
            yield chunk

    # 兼容旧API：分析文本（简单模板实现，可后续接入 AIIntelligenceService）
    async def analyze_text(
        self,
        text: str,
        analysis_type: str = "style",
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")
        from src.shared.config.ai_prompts import build_analysis_prompt
        prompt = build_analysis_prompt(text, analysis_type)
        content = await self.client_manager.simple_generate(
            prompt=prompt,
            context="",
            model=model,
            provider=provider
        )
        # 尝试解析结构化结果，若失败则返回原文
        try:
            import json
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"analysis_type": analysis_type, "report": content}

    # 兼容旧API：改进文本（简单模板实现）
    async def improve_text(
        self,
        text: str,
        improvement_type: str = "refine",
        instructions: str = "",
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")
        from src.shared.config.ai_prompts import build_improve_prompt
        prompt = build_improve_prompt(text, improvement_type, instructions)
        return await self.client_manager.simple_generate(
            prompt=prompt,
            context="",
            model=model,
            provider=provider
        )

    # 提示词构造迁移至 src/shared/config/ai_prompts.py，避免重复实现



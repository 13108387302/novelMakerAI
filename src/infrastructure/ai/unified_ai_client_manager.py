#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一AI客户端管理器

整合AI客户端工厂和旧的AI服务仓储功能，提供统一的AI客户端管理接口。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .clients.ai_client_factory import AIClientFactory
from .clients.base_ai_client import BaseAIClient
from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
from src.domain.ai.value_objects.ai_request_type import AIRequestType
from src.shared.utils.base_utils import BaseUtility, UtilResult, timed_operation
from src.shared.utils.unified_performance import get_performance_manager
from src.shared.utils.unified_error_handler import get_error_handler, ErrorCategory, ErrorSeverity
from src.shared.utils.unified_network_manager import get_network_manager
from src.shared.constants import AI_MAX_CONCURRENT_REQUESTS, AI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class UnifiedAIClientManager(BaseUtility):
    """
    统一AI客户端管理器

    整合AI客户端工厂和服务仓储功能，提供统一的AI客户端管理。
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化统一AI客户端管理器

        Args:
            config: 配置信息
        """
        super().__init__("UnifiedAIClientManager")

        self.config = config or {}
        self.factory = AIClientFactory()

        # 客户端池
        self._active_clients: Dict[str, BaseAIClient] = {}
        self._client_health: Dict[str, bool] = {}

        # 性能管理
        self.performance_manager = get_performance_manager()
        self.error_handler = get_error_handler()
        self.network_manager = get_network_manager()

        # 并发控制
        max_concurrent = self.config.get('max_concurrent_requests', AI_MAX_CONCURRENT_REQUESTS)
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 默认提供商
        self.default_provider = self.config.get('default_provider', 'deepseek')

        self.logger.info(f"统一AI客户端管理器初始化完成，默认提供商: {self.default_provider}")

    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            config: 新的配置信息
        """
        if config:
            self.config.update(config)
            # 更新相关配置
            if 'default_provider' in config:
                self.default_provider = config['default_provider']
            if 'max_concurrent_requests' in config:
                max_concurrent = config['max_concurrent_requests']
                self._semaphore = asyncio.Semaphore(max_concurrent)
            self.logger.info("配置已更新")

    @timed_operation("get_client")
    async def get_client(self, provider: str = None) -> UtilResult[BaseAIClient]:
        """
        获取AI客户端

        Args:
            provider: 提供商名称，默认使用配置的默认提供商

        Returns:
            UtilResult[BaseAIClient]: 客户端获取结果
        """
        provider = provider or self.default_provider

        try:
            # 检查是否已有活跃客户端
            if provider in self._active_clients:
                client = self._active_clients[provider]

                # 检查客户端健康状态
                if await self._check_client_health(client):
                    return UtilResult.success_result(client)
                else:
                    # 客户端不健康，移除并重新创建
                    await self._remove_client(provider)

            # 创建新客户端
            client_config = self._get_provider_config(provider)
            client = await self.factory.create_and_connect_client(
                provider=provider,
                config=client_config,
                use_cache=True
            )

            # 添加到活跃客户端池
            self._active_clients[provider] = client
            self._client_health[provider] = True

            return UtilResult.success_result(client)

        except Exception as e:
            error_msg = f"获取AI客户端失败: {provider}, 错误: {e}"
            self.error_handler.handle_error(
                error=e,
                operation="get_client",
                category=ErrorCategory.AI_SERVICE,
                severity=ErrorSeverity.HIGH
            )
            return UtilResult.failure_result(error_msg)

    @timed_operation("simple_generate")
    async def simple_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        provider: str = None
    ) -> str:
        """
        简单文本生成（向后兼容接口）

        Args:
            prompt: 提示词
            context: 上下文
            max_tokens: 最大令牌数
            temperature: 温度参数
            model: 模型名称
            provider: 提供商名称

        Returns:
            str: 生成的文本
        """
        async with self._semaphore:
            # 检查缓存
            cache_key = self._generate_cache_key(prompt, context, max_tokens, temperature, model, provider)
            cache_result = self.performance_manager.cache_get(cache_key)

            if cache_result.success:
                self.logger.debug("使用缓存的AI响应")
                return cache_result.data

            try:
                # 获取客户端
                client_result = await self.get_client(provider)
                if not client_result.success:
                    raise RuntimeError(client_result.error)

                client = client_result.data

                # 创建AI请求
                ai_request = AIRequest(
                    request_type=AIRequestType.TEXT_GENERATION,
                    prompt=prompt,
                    context=context,
                    parameters={
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'model': model
                    }
                )

                # 获取最优超时时间
                timeout_result = await self.network_manager.get_optimal_timeout()
                timeout = timeout_result.data if timeout_result.success else 30.0

                # 使用重试机制生成文本
                # 使用配置化的重试次数
                configured_retries = int(self.config.get('retry_attempts', 3))
                response = await self.network_manager.retry_with_backoff(
                    lambda: client.generate_text(ai_request, timeout),
                    max_retries=configured_retries
                )

                # 缓存响应
                if response and response.content:
                    self.performance_manager.cache_set(
                        cache_key,
                        response.content,
                        ttl=3600  # 1小时
                    )

                return response.content if response else ""

            except Exception as e:
                self.error_handler.handle_error(
                    error=e,
                    operation="simple_generate",
                    category=ErrorCategory.AI_SERVICE,
                    severity=ErrorSeverity.MEDIUM
                )
                raise RuntimeError(f"AI文本生成失败: {e}")

    @timed_operation("generate_text_stream")
    async def generate_text_stream(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None,
        provider: str = None
    ):
        """
        流式文本生成

        Args:
            prompt: 提示词
            context: 上下文
            max_tokens: 最大令牌数
            temperature: 温度参数
            model: 模型名称
            provider: 提供商名称

        Yields:
            str: 文本块
        """
        async with self._semaphore:
            try:
                # 获取客户端
                client_result = await self.get_client(provider)
                if not client_result.success:
                    raise RuntimeError(client_result.error)

                client = client_result.data

                # 创建AI请求
                ai_request = AIRequest(
                    request_type=AIRequestType.TEXT_GENERATION,
                    prompt=prompt,
                    context=context,
                    parameters={
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'model': model
                    }
                )

                # 获取最优超时时间
                timeout_result = await self.network_manager.get_optimal_timeout()

                # 如果配置关闭了流式输出，则退回非流式生成
                try:
                    if self.config is not None and self.config.get('enable_streaming') is False:
                        # 退回简单生成，将整段作为一个块输出
                        content = await self.simple_generate(
                            prompt=prompt,
                            context=context,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            model=model,
                            provider=provider
                        )
                        if content:
                            yield content
                        return
                except Exception:
                    pass

                timeout = timeout_result.data if timeout_result.success else 30.0

                # 流式生成
                async for chunk in client.generate_text_stream(ai_request, timeout):
                    yield chunk

            except Exception as e:
                self.error_handler.handle_error(
                    error=e,
                    operation="generate_text_stream",
                    category=ErrorCategory.AI_SERVICE,
                    severity=ErrorSeverity.MEDIUM
                )
                raise RuntimeError(f"AI流式生成失败: {e}")

    async def _check_client_health(self, client: BaseAIClient) -> bool:
        """检查客户端健康状态"""
        try:
            return await client.is_healthy()
        except Exception as e:
            self.logger.warning(f"客户端健康检查失败: {e}")
            return False

    async def _remove_client(self, provider: str) -> None:
        """移除客户端"""
        if provider in self._active_clients:
            client = self._active_clients.pop(provider)
            try:
                await client.disconnect()
            except Exception as e:
                self.logger.warning(f"断开客户端连接失败: {e}")

        self._client_health.pop(provider, None)

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """获取提供商配置"""
        provider_config = self.config.get('providers', {}).get(provider, {})
        default_config = self.factory.get_default_config(provider)

        # 合并配置
        merged_config = {**default_config, **provider_config}
        return merged_config

    def _generate_cache_key(self, prompt: str, context: str, max_tokens: int,
                          temperature: float, model: Optional[str], provider: Optional[str]) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{prompt}|{context}|{max_tokens}|{temperature}|{model}|{provider}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_supported_providers(self) -> List[str]:
        """获取支持的提供商列表"""
        return self.factory.get_supported_providers()

    def validate_config(self) -> UtilResult[bool]:
        """验证配置"""
        try:
            # 检查默认提供商是否支持
            if not self.factory.is_provider_supported(self.default_provider):
                return UtilResult.failure_result(f"不支持的默认提供商: {self.default_provider}")

            return UtilResult.success_result(True)

        except Exception as e:
            return UtilResult.failure_result(f"配置验证失败: {e}")

    async def cleanup(self) -> UtilResult[bool]:
        """清理资源"""
        try:
            # 断开所有客户端连接
            for provider in list(self._active_clients.keys()):
                await self._remove_client(provider)

            # 清空工厂缓存
            self.factory.clear_cache()

            return UtilResult.success_result(True)

        except Exception as e:
            return UtilResult.failure_result(f"清理失败: {e}")


# 全局统一AI客户端管理器实例
_global_ai_client_manager: Optional[UnifiedAIClientManager] = None


def get_unified_ai_client_manager(config: Dict[str, Any] = None) -> UnifiedAIClientManager:
    """获取全局统一AI客户端管理器"""
    global _global_ai_client_manager
    if _global_ai_client_manager is None:
        _global_ai_client_manager = UnifiedAIClientManager(config)
    elif config and hasattr(_global_ai_client_manager, 'update_config'):
        # 如果已存在但有新配置，更新配置
        _global_ai_client_manager.update_config(config)
    return _global_ai_client_manager


def set_unified_ai_client_manager(manager: UnifiedAIClientManager) -> None:
    """设置全局统一AI客户端管理器"""
    global _global_ai_client_manager
    _global_ai_client_manager = manager

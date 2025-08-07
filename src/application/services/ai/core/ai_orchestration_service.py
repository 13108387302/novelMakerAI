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

from src.infrastructure.ai.clients.ai_client_factory import AIClientFactory
from src.infrastructure.ai.clients.base_ai_client import BaseAIClient
from src.shared.constants import (
    AI_MAX_CONCURRENT_REQUESTS, AI_TIMEOUT_SECONDS, AI_RETRY_ATTEMPTS,
    AI_HEALTH_CHECK_INTERVAL
)

logger = logging.getLogger(__name__)

# AI编排服务常量
DEFAULT_AI_PROVIDER = 'openai'
OPENAI_PROVIDER = 'openai'
DEEPSEEK_PROVIDER = 'deepseek'


class AIOrchestrationService:
    """
    AI编排服务
    
    负责协调AI请求的完整处理流程，包括：
    - 请求验证和预处理
    - 提供商选择和负载均衡
    - 请求执行和响应处理
    - 错误处理和重试机制
    - 性能监控和质量评估
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI编排服务
        
        Args:
            config: 服务配置
        """
        self.config = config
        self.is_initialized = False
        
        # 提供商配置
        self.providers_config = config.get('providers', {})
        self.default_provider = config.get('default_provider', DEFAULT_AI_PROVIDER)

        # 性能配置
        self.max_concurrent_requests = config.get('max_concurrent_requests', AI_MAX_CONCURRENT_REQUESTS)
        self.request_timeout = config.get('request_timeout', AI_TIMEOUT_SECONDS)
        self.retry_attempts = config.get('retry_attempts', AI_RETRY_ATTEMPTS)
        
        # 客户端管理
        self.clients: Dict[str, BaseAIClient] = {}
        self.client_health: Dict[str, bool] = {}
        
        # 请求队列和限流
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        self.active_requests: Dict[str, AIRequest] = {}
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = datetime.now()

        # 任务管理
        self._health_check_task: Optional[asyncio.Task] = None  # 健康检查任务引用
    
    async def initialize(self) -> bool:
        """
        初始化服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化AI客户端
            await self._initialize_clients()
            
            # 启动健康检查
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.is_initialized = True
            logger.info("AI编排服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"AI编排服务初始化失败: {e}")
            return False
    
    async def process_request(
        self,
        request: AIRequest,
        use_streaming: bool = False,
        preferred_provider: Optional[str] = None
    ) -> AIResponse:
        """
        处理AI请求
        
        Args:
            request: AI请求
            use_streaming: 是否使用流式输出
            preferred_provider: 首选提供商
            
        Returns:
            AIResponse: AI响应
        """
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")
        
        async with self.request_semaphore:
            self.total_requests += 1
            self.active_requests[request.id] = request
            
            try:
                # 选择提供商
                provider = await self._select_provider(request, preferred_provider)
                client = self.clients.get(provider)
                
                if not client:
                    raise RuntimeError(f"提供商客户端不可用: {provider}")
                
                # 处理请求
                response = await client.process_request(
                    request=request,
                    use_streaming=use_streaming,
                    timeout=self._calculate_timeout(request)
                )
                
                # 更新统计
                if response.is_successful:
                    self.successful_requests += 1
                else:
                    self.failed_requests += 1
                
                return response
                
            except Exception as e:
                self.failed_requests += 1
                logger.error(f"AI请求处理失败: {e}")
                
                # 创建错误响应
                error_response = AIResponse(
                    request_id=request.id,
                    status=AIResponseStatus.FAILED,
                    error_message=str(e)
                )
                error_response.fail(str(e))
                return error_response
                
            finally:
                # 清理活动请求
                self.active_requests.pop(request.id, None)
    
    async def process_request_stream(
        self,
        request: AIRequest,
        preferred_provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式处理AI请求
        
        Args:
            request: AI请求
            preferred_provider: 首选提供商
            
        Yields:
            str: 响应文本块
        """
        if not self.is_initialized:
            raise RuntimeError("AI编排服务未初始化")
        
        async with self.request_semaphore:
            self.total_requests += 1
            self.active_requests[request.id] = request
            
            try:
                # 选择提供商
                provider = await self._select_provider(request, preferred_provider)
                client = self.clients.get(provider)
                
                if not client:
                    raise RuntimeError(f"提供商客户端不可用: {provider}")
                
                # 流式处理
                async for chunk in client.generate_text_stream(
                    request=request,
                    timeout=self._calculate_timeout(request)
                ):
                    yield chunk
                
                self.successful_requests += 1
                
            except Exception as e:
                self.failed_requests += 1
                logger.error(f"AI流式请求处理失败: {e}")
                raise
                
            finally:
                # 清理活动请求
                self.active_requests.pop(request.id, None)
    
    async def cancel_request(self, request_id: str) -> bool:
        """
        取消AI请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            bool: 是否成功取消
        """
        request = self.active_requests.get(request_id)
        if request:
            request.cancel()
            self.active_requests.pop(request_id, None)
            logger.info(f"AI请求已取消: {request_id}")
            return True
        return False
    
    async def get_available_providers(self) -> List[str]:
        """
        获取可用的提供商列表
        
        Returns:
            List[str]: 可用提供商名称列表
        """
        available = []
        for provider, is_healthy in self.client_health.items():
            if is_healthy and provider in self.clients:
                available.append(provider)
        return available
    
    async def get_provider_capabilities(self, provider: str) -> List[AICapability]:
        """
        获取提供商支持的能力
        
        Args:
            provider: 提供商名称
            
        Returns:
            List[AICapability]: 支持的能力列表
        """
        client = self.clients.get(provider)
        if client:
            return await client.get_capabilities()
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        success_rate = (
            self.successful_requests / self.total_requests 
            if self.total_requests > 0 else 0.0
        )
        
        return {
            'is_initialized': self.is_initialized,
            'uptime_seconds': uptime,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': success_rate,
            'active_requests': len(self.active_requests),
            'available_providers': list(self.client_health.keys()),
            'healthy_providers': [
                provider for provider, healthy in self.client_health.items() if healthy
            ]
        }
    
    async def shutdown(self) -> None:
        """关闭服务"""
        logger.info("正在关闭AI编排服务...")

        # 首先设置关闭标志，停止健康检查循环
        self.is_initialized = False

        # 取消健康检查任务
        if self._health_check_task and not self._health_check_task.done():
            logger.info("取消健康检查任务...")
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                logger.info("健康检查任务已取消")
            except Exception as e:
                logger.warning(f"取消健康检查任务时出错: {e}")

        # 取消所有活动请求
        for request_id in list(self.active_requests.keys()):
            await self.cancel_request(request_id)

        # 断开所有客户端
        for client in self.clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"断开客户端连接失败: {e}")

        self.clients.clear()
        self.client_health.clear()

        logger.info("AI编排服务已关闭")
    
    async def _initialize_clients(self) -> None:
        """初始化AI客户端"""
        for provider, config in self.providers_config.items():
            try:
                # 检查必要的配置
                if not self._validate_provider_config(provider, config):
                    logger.info(f"跳过AI客户端初始化: {provider} (配置不完整)")
                    self.client_health[provider] = False
                    continue

                client = await AIClientFactory.create_and_connect_client(
                    provider=provider,
                    config=config,
                    use_cache=True
                )

                self.clients[provider] = client
                self.client_health[provider] = True

                logger.info(f"AI客户端初始化成功: {provider}")

            except Exception as e:
                logger.error(f"AI客户端初始化失败: {provider}, 错误: {e}")
                self.client_health[provider] = False

    def _validate_provider_config(self, provider: str, config: dict) -> bool:
        """验证提供商配置是否完整"""
        if provider == OPENAI_PROVIDER:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                logger.info(f"OpenAI API密钥未配置，跳过OpenAI客户端初始化")
                return False
        elif provider == DEEPSEEK_PROVIDER:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                logger.info(f"DeepSeek API密钥未配置，跳过DeepSeek客户端初始化")
                return False

        return True
    
    async def _select_provider(
        self,
        request: AIRequest,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        选择最适合的提供商
        
        Args:
            request: AI请求
            preferred_provider: 首选提供商
            
        Returns:
            str: 选择的提供商名称
        """
        # 如果指定了首选提供商且可用，则使用它
        if preferred_provider and self.client_health.get(preferred_provider):
            return preferred_provider
        
        # 获取健康的提供商
        healthy_providers = [
            provider for provider, healthy in self.client_health.items() if healthy
        ]
        
        if not healthy_providers:
            raise RuntimeError("没有可用的AI提供商")
        
        # 简单的负载均衡：选择第一个健康的提供商
        # TODO: 实现更智能的选择策略（基于能力匹配、负载等）
        return healthy_providers[0]
    
    def _calculate_timeout(self, request: AIRequest) -> float:
        """
        计算请求超时时间
        
        Args:
            request: AI请求
            
        Returns:
            float: 超时时间（秒）
        """
        base_timeout = self.request_timeout
        priority_multiplier = request.priority.timeout_multiplier
        return base_timeout * priority_multiplier
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.is_initialized:
            try:
                for provider, client in self.clients.items():
                    try:
                        is_healthy = await client.is_healthy()
                        self.client_health[provider] = is_healthy
                        
                        if not is_healthy:
                            logger.warning(f"AI客户端不健康: {provider}")
                            
                    except Exception as e:
                        logger.error(f"健康检查失败: {provider}, 错误: {e}")
                        self.client_health[provider] = False
                
                # 定期健康检查
                await asyncio.sleep(AI_HEALTH_CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查循环错误: {e}")
                await asyncio.sleep(AI_HEALTH_CHECK_INTERVAL)

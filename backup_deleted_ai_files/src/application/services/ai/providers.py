#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI提供商适配器 - 重构版本

为不同的AI服务提供商提供统一的接口适配
"""

from typing import List, AsyncGenerator, Dict, Any, Optional
import asyncio
import time

from .core_abstractions import (
    IAIProvider, AIRequest, AIResponse, AICapability, AIServiceError
)
try:
    from src.infrastructure.ai_clients.openai_client import OpenAIStreamingClient
    from src.shared.utils.logger import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

    # 如果无法导入OpenAI客户端，创建一个模拟类
    class OpenAIStreamingClient:
        def __init__(self):
            pass

        async def simple_chat_completion(self, **kwargs):
            return "模拟响应：AI服务暂不可用"

        async def stream_chat_completion(self, **kwargs):
            yield "模拟响应：AI服务暂不可用"

logger = get_logger(__name__)


class OpenAIProvider(IAIProvider):
    """OpenAI提供商适配器"""
    
    def __init__(self, client: Optional[OpenAIStreamingClient] = None):
        self.client = client or OpenAIStreamingClient()
        self.name = "openai"
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """生成文本"""
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取参数
            model = request.parameters.get('model', 'gpt-3.5-turbo')
            max_tokens = request.parameters.get('max_tokens', 2000)
            temperature = request.parameters.get('temperature', 0.7)
            
            # 调用OpenAI API
            content = await self.client.simple_chat_completion(
                messages=messages,
                provider="openai",
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return AIResponse(
                request_id=request.id,
                content=content,
                metadata={
                    'provider': self.name,
                    'model': model,
                    'tokens_used': len(content.split())  # 简单估算
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI生成文本失败: {e}")
            return AIResponse(
                request_id=request.id,
                content="",
                error=str(e),
                is_complete=False
            )
    
    async def generate_text_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取参数
            model = request.parameters.get('model', 'gpt-3.5-turbo')
            max_tokens = request.parameters.get('max_tokens', 2000)
            temperature = request.parameters.get('temperature', 0.7)
            
            # 流式调用OpenAI API
            async for chunk in self.client.stream_chat_completion(
                messages=messages,
                provider="openai",
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"OpenAI流式生成失败: {e}")
            yield f"错误: {str(e)}"
    
    async def is_available(self) -> bool:
        """检查可用性"""
        try:
            # 简单的可用性测试
            test_request = AIRequest(
                prompt="测试",
                parameters={'max_tokens': 10}
            )
            response = await self.generate_text(test_request)
            return response.error is None
        except Exception:
            return False
    
    def get_capabilities(self) -> List[AICapability]:
        """获取支持的能力"""
        return [
            AICapability.TEXT_GENERATION,
            AICapability.CONVERSATION,
            AICapability.CONTENT_CREATION,
            AICapability.CREATIVE_WRITING,
            AICapability.QUESTION_ANSWERING,
            AICapability.SUMMARIZATION,
            AICapability.TRANSLATION
        ]
    
    def get_name(self) -> str:
        """获取提供商名称"""
        return self.name
    
    def _build_messages(self, request: AIRequest) -> List[Dict[str, str]]:
        """构建消息格式"""
        messages = []
        
        # 系统消息
        if request.context:
            messages.append({
                "role": "system",
                "content": request.context
            })
        
        # 用户消息
        messages.append({
            "role": "user",
            "content": request.prompt
        })
        
        return messages


class DeepSeekProvider(IAIProvider):
    """DeepSeek提供商适配器"""
    
    def __init__(self, client: Optional[OpenAIStreamingClient] = None):
        self.client = client or OpenAIStreamingClient()
        self.name = "deepseek"
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """生成文本"""
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取参数
            model = request.parameters.get('model', 'deepseek-chat')
            max_tokens = request.parameters.get('max_tokens', 2000)
            temperature = request.parameters.get('temperature', 0.7)
            
            # 调用DeepSeek API
            content = await self.client.simple_chat_completion(
                messages=messages,
                provider="deepseek",
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return AIResponse(
                request_id=request.id,
                content=content,
                metadata={
                    'provider': self.name,
                    'model': model,
                    'tokens_used': len(content.split())
                }
            )
            
        except Exception as e:
            logger.error(f"DeepSeek生成文本失败: {e}")
            return AIResponse(
                request_id=request.id,
                content="",
                error=str(e),
                is_complete=False
            )
    
    async def generate_text_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取参数
            model = request.parameters.get('model', 'deepseek-chat')
            max_tokens = request.parameters.get('max_tokens', 2000)
            temperature = request.parameters.get('temperature', 0.7)
            
            # 流式调用DeepSeek API
            async for chunk in self.client.stream_chat_completion(
                messages=messages,
                provider="deepseek",
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"DeepSeek流式生成失败: {e}")
            yield f"错误: {str(e)}"
    
    async def is_available(self) -> bool:
        """检查可用性"""
        try:
            test_request = AIRequest(
                prompt="测试",
                parameters={'max_tokens': 10}
            )
            response = await self.generate_text(test_request)
            return response.error is None
        except Exception:
            return False
    
    def get_capabilities(self) -> List[AICapability]:
        """获取支持的能力"""
        return [
            AICapability.TEXT_GENERATION,
            AICapability.CONVERSATION,
            AICapability.CONTENT_CREATION,
            AICapability.CREATIVE_WRITING,
            AICapability.QUESTION_ANSWERING,
            AICapability.CODE_GENERATION
        ]
    
    def get_name(self) -> str:
        """获取提供商名称"""
        return self.name
    
    def _build_messages(self, request: AIRequest) -> List[Dict[str, str]]:
        """构建消息格式"""
        messages = []
        
        # 系统消息
        if request.context:
            messages.append({
                "role": "system",
                "content": request.context
            })
        
        # 用户消息
        messages.append({
            "role": "user",
            "content": request.prompt
        })
        
        return messages


class MockProvider(IAIProvider):
    """模拟提供商（用于测试）"""
    
    def __init__(self, name: str = "mock"):
        self.name = name
        self._is_available = True
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """生成文本"""
        await asyncio.sleep(0.1)  # 模拟延迟
        
        content = f"模拟响应: {request.prompt[:50]}..."
        
        return AIResponse(
            request_id=request.id,
            content=content,
            metadata={
                'provider': self.name,
                'mock': True
            }
        )
    
    async def generate_text_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        content = f"模拟流式响应: {request.prompt[:50]}..."
        
        # 分块返回
        chunk_size = 10
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            await asyncio.sleep(0.05)  # 模拟延迟
            yield chunk
    
    async def is_available(self) -> bool:
        """检查可用性"""
        return self._is_available
    
    def get_capabilities(self) -> List[AICapability]:
        """获取支持的能力"""
        return [AICapability.TEXT_GENERATION, AICapability.CONVERSATION]
    
    def get_name(self) -> str:
        """获取提供商名称"""
        return self.name
    
    def set_availability(self, available: bool) -> None:
        """设置可用性（测试用）"""
        self._is_available = available


class ProviderFactory:
    """提供商工厂"""
    
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> IAIProvider:
        """创建提供商"""
        providers = {
            'openai': OpenAIProvider,
            'deepseek': DeepSeekProvider,
            'mock': MockProvider
        }
        
        provider_class = providers.get(provider_type)
        if not provider_class:
            raise AIServiceError(f"不支持的提供商类型: {provider_type}")
        
        return provider_class(**kwargs)
    
    @staticmethod
    def get_available_provider_types() -> List[str]:
        """获取可用的提供商类型"""
        return ['openai', 'deepseek', 'mock']

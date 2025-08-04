#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI客户端封装

使用官方OpenAI Python客户端实现更稳定的AI服务
"""

import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
import openai
from openai import AsyncOpenAI

from config.settings import get_settings
from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import handle_async_errors, ApplicationError

logger = get_logger(__name__)


class AIClientError(ApplicationError):
    """
    AI客户端错误基类

    所有AI客户端相关错误的基类，继承自ApplicationError。
    """
    pass


class AIServiceUnavailableError(AIClientError):
    """
    AI服务不可用错误

    当AI服务暂时不可用或网络连接失败时抛出。
    """
    pass


class AIQuotaExceededError(AIClientError):
    """
    AI配额超限错误

    当API调用超出配额限制时抛出。
    """
    pass


class AIRequestTimeoutError(AIClientError):
    """
    AI请求超时错误

    当AI请求超过设定的超时时间时抛出。
    """
    pass


# 全局设置服务实例（由主应用设置）
_global_settings_service = None

def set_global_settings_service(settings_service):
    """设置全局设置服务实例"""
    global _global_settings_service
    _global_settings_service = settings_service
    logger.info("全局设置服务已设置")

def get_ai_config():
    """获取AI配置（从设置服务或全局设置）"""
    global _global_settings_service

    # 尝试从全局设置服务获取
    if _global_settings_service:
        try:
            return {
                'openai_api_key': _global_settings_service.get_setting('ai.openai_api_key', ''),
                'openai_base_url': _global_settings_service.get_setting('ai.openai_base_url', 'https://api.openai.com/v1'),
                'openai_model': _global_settings_service.get_setting('ai.openai_model', 'gpt-3.5-turbo'),
                'deepseek_api_key': _global_settings_service.get_setting('ai.deepseek_api_key', ''),
                'deepseek_base_url': _global_settings_service.get_setting('ai.deepseek_base_url', 'https://api.deepseek.com/v1'),
                'deepseek_model': _global_settings_service.get_setting('ai.deepseek_model', 'deepseek-chat'),
                'default_provider': _global_settings_service.get_setting('ai.default_provider', 'openai'),
                'timeout': _global_settings_service.get_setting('ai.timeout', 30),
                'max_tokens': _global_settings_service.get_setting('ai.max_tokens', 2000),
                'temperature': _global_settings_service.get_setting('ai.temperature', 0.7),
            }
        except Exception as e:
            logger.warning(f"从设置服务获取AI配置失败，使用全局设置: {e}")
    else:
        logger.debug("全局设置服务未设置，使用全局设置")

    # 降级到全局设置
    settings = get_settings()
    return {
        'openai_api_key': settings.ai_service.openai_api_key or '',
        'openai_base_url': settings.ai_service.openai_base_url,
        'openai_model': settings.ai_service.openai_model,
        'deepseek_api_key': settings.ai_service.deepseek_api_key or '',
        'deepseek_base_url': settings.ai_service.deepseek_base_url,
        'deepseek_model': settings.ai_service.deepseek_model,
        'default_provider': settings.ai_service.default_provider,
        'timeout': settings.ai_service.timeout,
        'max_tokens': settings.ai_service.max_tokens,
        'temperature': settings.ai_service.temperature,
    }


class OpenAIStreamingClient:
    """
    OpenAI流式客户端

    封装OpenAI API的流式调用功能，支持多个AI服务提供商。
    提供统一的接口处理文本生成和流式响应。

    实现方式：
    - 支持OpenAI和DeepSeek等多个提供商
    - 使用异步客户端提高性能
    - 提供流式和非流式两种调用模式
    - 包含完整的错误处理和重试机制
    - 支持动态配置重载

    Attributes:
        config: AI服务配置字典
        _client: OpenAI客户端实例
        _deepseek_client: DeepSeek客户端实例
    """

    def __init__(self):
        """
        初始化OpenAI流式客户端

        加载AI配置并初始化客户端实例。
        """
        self.config = get_ai_config()
        self._client = None
        self._deepseek_client = None

    def reload_settings(self):
        """
        重新加载设置并重置客户端

        当配置发生变化时，重新加载配置并重置客户端实例。
        用于动态更新API密钥和其他配置。
        """
        self.config = get_ai_config()
        self._client = None
        self._deepseek_client = None
        logger.info("AI客户端设置已重新加载")
    
    def _get_openai_client(self) -> AsyncOpenAI:
        """获取OpenAI客户端"""
        if not self._client:
            api_key = self.config.get('openai_api_key', '').strip()
            if not api_key:
                raise AIClientError("OpenAI API密钥未配置")

            try:
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.config.get('openai_base_url', 'https://api.openai.com/v1'),
                    timeout=self.config.get('timeout', 30)
                )
            except Exception as e:
                raise AIClientError(f"创建OpenAI客户端失败: {e}")
        return self._client

    def _get_deepseek_client(self) -> AsyncOpenAI:
        """获取DeepSeek客户端"""
        if not self._deepseek_client:
            api_key = self.config.get('deepseek_api_key', '').strip()
            if not api_key:
                raise AIClientError("DeepSeek API密钥未配置")

            try:
                self._deepseek_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.config.get('deepseek_base_url', 'https://api.deepseek.com/v1'),
                    timeout=self.config.get('timeout', 30)
                )
            except Exception as e:
                raise AIClientError(f"创建DeepSeek客户端失败: {e}")
        return self._deepseek_client
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        provider: str = "openai",
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        try:
            if provider.lower() == "openai":
                client = self._get_openai_client()
                model = model or self.config.get('openai_model', 'gpt-3.5-turbo')
            elif provider.lower() == "deepseek":
                client = self._get_deepseek_client()
                model = model or self.config.get('deepseek_model', 'deepseek-chat')
            else:
                raise ValueError(f"不支持的AI提供商: {provider}")
            
            logger.info(f"开始流式生成，提供商: {provider}, 模型: {model}")
            
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
            
            logger.info("流式生成完成")
            
        except openai.APIError as e:
            logger.error(f"OpenAI API错误: {e}")
            raise AIClientError(f"API调用失败: {e}")
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI连接错误: {e}")
            raise AIServiceUnavailableError(f"无法连接到AI服务: {e}")
        except openai.RateLimitError as e:
            logger.error(f"OpenAI速率限制: {e}")
            raise AIQuotaExceededError(f"API调用频率超限: {e}")
        except asyncio.TimeoutError as e:
            logger.error(f"请求超时: {e}")
            raise AIRequestTimeoutError("AI服务响应超时")
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            raise AIClientError(f"未知错误: {e}")
    
    async def simple_chat_completion(
        self,
        messages: List[Dict[str, str]],
        provider: str = "openai",
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """简单聊天完成（非流式）"""
        try:
            if provider.lower() == "openai":
                client = self._get_openai_client()
                model = model or self.config.get('openai_model', 'gpt-3.5-turbo')
            elif provider.lower() == "deepseek":
                client = self._get_deepseek_client()
                model = model or self.config.get('deepseek_model', 'deepseek-chat')
            else:
                raise ValueError(f"不支持的AI提供商: {provider}")
            
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
                **kwargs
            )
            
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                raise AIClientError("AI响应为空")
                
        except openai.APIError as e:
            logger.error(f"OpenAI API错误: {e}")
            raise AIClientError(f"API调用失败: {e}")
        except openai.APIConnectionError as e:
            logger.error(f"OpenAI连接错误: {e}")
            raise AIServiceUnavailableError(f"无法连接到AI服务: {e}")
        except openai.RateLimitError as e:
            logger.error(f"OpenAI速率限制: {e}")
            raise AIQuotaExceededError(f"API调用频率超限: {e}")
        except asyncio.TimeoutError as e:
            logger.error(f"请求超时: {e}")
            raise AIRequestTimeoutError("AI服务响应超时")
        except Exception as e:
            logger.error(f"聊天完成失败: {e}")
            raise AIClientError(f"未知错误: {e}")
    
    async def stream_with_prompt(
        self,
        prompt: str,
        context: str = "",
        provider: str = "openai",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """使用提示词进行流式生成"""
        messages = []
        
        if context:
            messages.append({"role": "system", "content": context})
        
        messages.append({"role": "user", "content": prompt})
        
        async for chunk in self.stream_chat_completion(
            messages=messages,
            provider=provider,
            **kwargs
        ):
            yield chunk
    
    async def complete_with_prompt(
        self,
        prompt: str,
        context: str = "",
        provider: str = "openai",
        **kwargs
    ) -> str:
        """使用提示词进行完成（非流式）"""
        messages = []
        
        if context:
            messages.append({"role": "system", "content": context})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self.simple_chat_completion(
            messages=messages,
            provider=provider,
            **kwargs
        )


class AIClientManager:
    """AI客户端管理器"""
    
    def __init__(self):
        self.openai_client = OpenAIStreamingClient()
        self.config = get_ai_config()

    def reload_settings(self):
        """重新加载设置"""
        self.config = get_ai_config()
        self.openai_client.reload_settings()
        logger.info("AI客户端管理器设置已重新加载")
    
    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成（自动选择提供商）"""
        provider = self.config.get('default_provider', 'openai')
        
        try:
            async for chunk in self.openai_client.stream_with_prompt(
                prompt=prompt,
                context=context,
                provider=provider,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"使用{provider}流式生成失败: {e}")
            
            # 尝试降级到另一个提供商
            fallback_provider = "deepseek" if provider == "openai" else "openai"
            
            try:
                logger.info(f"尝试降级到{fallback_provider}")
                async for chunk in self.openai_client.stream_with_prompt(
                    prompt=prompt,
                    context=context,
                    provider=fallback_provider,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                ):
                    yield chunk
                    
            except Exception as fallback_error:
                logger.error(f"降级到{fallback_provider}也失败: {fallback_error}")
                # 最后降级到模拟响应
                async for chunk in self._fallback_mock_stream(prompt):
                    yield chunk
    
    async def simple_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """简单生成（非流式）"""
        provider = self.config.get('default_provider', 'openai')
        
        try:
            return await self.openai_client.complete_with_prompt(
                prompt=prompt,
                context=context,
                provider=provider,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
        except Exception as e:
            logger.error(f"使用{provider}生成失败: {e}")
            
            # 尝试降级到另一个提供商
            fallback_provider = "deepseek" if provider == "openai" else "openai"
            
            try:
                logger.info(f"尝试降级到{fallback_provider}")
                return await self.openai_client.complete_with_prompt(
                    prompt=prompt,
                    context=context,
                    provider=fallback_provider,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
            except Exception as fallback_error:
                logger.error(f"降级到{fallback_provider}也失败: {fallback_error}")
                return f"抱歉，AI服务暂时不可用。错误信息：{str(e)}"
    
    async def _fallback_mock_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """降级模拟流式响应"""
        mock_response = """抱歉，AI服务暂时不可用，这是一个模拟响应。

根据您的请求，我建议：

1. 检查网络连接是否正常
2. 确认API密钥配置正确
3. 稍后再试或联系技术支持

感谢您的理解！"""
        
        words = mock_response.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.1)


# 全局客户端实例
_ai_client_manager = None

def get_ai_client_manager() -> AIClientManager:
    """获取AI客户端管理器实例"""
    global _ai_client_manager
    if _ai_client_manager is None:
        _ai_client_manager = AIClientManager()
    return _ai_client_manager

def reload_ai_client_settings():
    """重新加载AI客户端设置"""
    global _ai_client_manager
    if _ai_client_manager is not None:
        _ai_client_manager.reload_settings()
    else:
        # 如果还没有创建实例，下次创建时会自动使用新设置
        logger.info("AI客户端管理器尚未创建，将在下次使用时应用新设置")

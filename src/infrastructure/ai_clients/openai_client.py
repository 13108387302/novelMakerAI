#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI客户端封装

使用官方OpenAI Python客户端实现更稳定的AI服务
"""

import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
import openai
import httpx
from openai import AsyncOpenAI
from functools import wraps

from config.settings import get_settings
from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import handle_async_errors, ApplicationError

logger = get_logger(__name__)


def retry_on_timeout(max_retries: int = 3, delay: float = 1.0):
    """
    超时重试装饰器

    当遇到超时错误时自动重试，支持指数退避和网络状态检测
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from src.shared.utils.network_utils import smart_retry_with_backoff

            # 使用智能重试机制
            async def execute_func():
                return await func(*args, **kwargs)

            return await smart_retry_with_backoff(
                execute_func,
                max_retries=max_retries,
                base_delay=delay
            )

        return wrapper
    return decorator


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
                'timeout': _global_settings_service.get_setting('ai.timeout', 120),
                'max_tokens': _global_settings_service.get_setting('ai.max_tokens', 2000),
                'temperature': _global_settings_service.get_setting('ai.temperature', 0.7),
            }
        except Exception as e:
            logger.warning(f"从设置服务获取AI配置失败，使用全局设置: {e}")
    else:
        logger.debug("全局设置服务未设置，使用全局设置")

    # 降级到全局设置
    try:
        from config.settings import get_settings
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
    except Exception as e:
        logger.error(f"获取全局设置失败: {e}")
        # 返回默认配置
        return {
            'openai_api_key': '',
            'openai_base_url': 'https://api.openai.com/v1',
            'openai_model': 'gpt-3.5-turbo',
            'deepseek_api_key': '',
            'deepseek_base_url': 'https://api.deepseek.com/v1',
            'deepseek_model': 'deepseek-chat',
            'default_provider': 'openai',
            'timeout': 120,
            'max_tokens': 2000,
            'temperature': 0.7,
        }

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
    OpenAI流式客户端 - 优化版本

    封装OpenAI API的流式调用功能，支持多个AI服务提供商。
    提供统一的接口处理文本生成和流式响应。

    优化功能：
    - 连接池管理和复用
    - 智能重试和故障转移
    - 性能监控和统计
    - 自适应超时和限流
    - 请求缓存机制

    Attributes:
        config: AI服务配置字典
        _clients: 客户端连接池
        _client_stats: 客户端统计信息
        _request_cache: 请求缓存
    """

    def __init__(self):
        """
        初始化OpenAI流式客户端

        加载AI配置并初始化客户端连接池。
        """
        self.config = get_ai_config()

        # 连接池管理
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}

        # 性能统计
        self._client_stats: Dict[str, Dict[str, Any]] = {}
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0

        # 缓存管理
        self._request_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5分钟缓存

        # 限流控制
        self._rate_limiters: Dict[str, asyncio.Semaphore] = {}

        logger.info("OpenAI流式客户端初始化完成（优化版本）")

    def reload_settings(self):
        """
        重新加载设置并重置客户端连接池

        当配置发生变化时，重新加载配置并重置所有客户端实例。
        用于动态更新API密钥和其他配置。
        """
        self.config = get_ai_config()

        # 清理现有连接
        self._clients.clear()
        self._client_locks.clear()
        self._rate_limiters.clear()

        # 重置统计信息
        self._client_stats.clear()
        self._request_cache.clear()

        logger.info("AI客户端设置已重新加载（连接池已重置）")
    
    async def _get_client(self, provider: str) -> AsyncOpenAI:
        """获取客户端实例 - 连接池版本"""
        # 确保有锁
        if provider not in self._client_locks:
            self._client_locks[provider] = asyncio.Lock()

        # 确保有限流器
        if provider not in self._rate_limiters:
            # 每个提供商最多同时5个请求
            self._rate_limiters[provider] = asyncio.Semaphore(5)

        async with self._client_locks[provider]:
            if provider not in self._clients:
                self._clients[provider] = await self._create_client(provider)

                # 初始化统计信息
                self._client_stats[provider] = {
                    'requests': 0,
                    'successes': 0,
                    'failures': 0,
                    'avg_response_time': 0.0,
                    'last_used': None
                }

        return self._clients[provider]

    async def _create_client(self, provider: str) -> AsyncOpenAI:
        """创建新的客户端实例"""
        if provider.lower() == 'openai':
            api_key = self.config.get('openai_api_key', '').strip()
            base_url = self.config.get('openai_base_url', 'https://api.openai.com/v1')
        elif provider.lower() == 'deepseek':
            api_key = self.config.get('deepseek_api_key', '').strip()
            base_url = self.config.get('deepseek_base_url', 'https://api.deepseek.com/v1')
        else:
            raise AIClientError(f"不支持的提供商: {provider}")

        if not api_key:
            raise AIClientError(f"{provider} API密钥未配置")

        try:
            # 使用自适应超时
            from src.shared.utils.network_utils import get_adaptive_timeout
            adaptive_timeout = get_adaptive_timeout()
            final_timeout = max(self.config.get('timeout', 120), adaptive_timeout)

            # 创建HTTP客户端配置
            http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(final_timeout),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0
                )
            )

            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client
            )

            logger.info(f"{provider}客户端创建成功，超时设置: {final_timeout:.1f}秒")
            return client

        except Exception as e:
            raise AIClientError(f"创建{provider}客户端失败: {e}")

    def _generate_cache_key(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """生成缓存键"""
        import hashlib
        import json

        # 构建缓存内容
        cache_content = {
            'messages': messages,
            'model': kwargs.get('model'),
            'max_tokens': kwargs.get('max_tokens'),
            'temperature': kwargs.get('temperature')
        }

        # 生成哈希
        content_str = json.dumps(cache_content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """获取缓存响应"""
        if cache_key in self._request_cache:
            cached_item = self._request_cache[cache_key]
            # 检查是否过期
            if time.time() - cached_item['timestamp'] < self._cache_ttl:
                return cached_item['response']
            else:
                # 清理过期缓存
                del self._request_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: str):
        """缓存响应"""
        self._request_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }

        # 限制缓存大小
        if len(self._request_cache) > 100:
            # 删除最旧的缓存项
            oldest_key = min(
                self._request_cache.keys(),
                key=lambda k: self._request_cache[k]['timestamp']
            )
            del self._request_cache[oldest_key]
    
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
        start_time = time.time()

        # 获取限流器
        rate_limiter = self._rate_limiters.get(provider)
        if not rate_limiter:
            rate_limiter = asyncio.Semaphore(5)
            self._rate_limiters[provider] = rate_limiter

        async with rate_limiter:
            try:
                # 获取客户端
                client = await self._get_client(provider)

                # 确定模型
                if provider.lower() == "openai":
                    model = model or self.config.get('openai_model', 'gpt-3.5-turbo')
                elif provider.lower() == "deepseek":
                    model = model or self.config.get('deepseek_model', 'deepseek-chat')
                else:
                    raise ValueError(f"不支持的AI提供商: {provider}")

                logger.info(f"开始流式生成，提供商: {provider}, 模型: {model}")

                # 更新统计
                self._request_count += 1
                stats = self._client_stats.get(provider, {})
                stats['requests'] = stats.get('requests', 0) + 1
                stats['last_used'] = datetime.now()

                # 创建流式请求
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                    **kwargs
                )

                # 处理流式响应
                chunk_count = 0
                try:
                    async for chunk in response:
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'content') and delta.content:
                                chunk_count += 1
                                yield delta.content

                except Exception as stream_error:
                    logger.error(f"处理流式响应失败: {stream_error}")
                    # 如果流式处理失败，尝试降级到非流式
                    logger.warning("流式处理失败，降级到非流式生成")

                    # 重新创建非流式请求
                    fallback_response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=False,
                        **kwargs
                    )

                    # 分块返回非流式结果
                    if fallback_response.choices and len(fallback_response.choices) > 0:
                        content = fallback_response.choices[0].message.content
                        if content:
                            # 将内容分成小块模拟流式输出
                            chunk_size = 10
                            for i in range(0, len(content), chunk_size):
                                chunk_count += 1
                                yield content[i:i + chunk_size]

                # 记录成功
                processing_time = time.time() - start_time
                self._success_count += 1
                stats['successes'] = stats.get('successes', 0) + 1

                # 更新平均响应时间
                if 'avg_response_time' not in stats:
                    stats['avg_response_time'] = processing_time
                else:
                    stats['avg_response_time'] = (
                        stats['avg_response_time'] * 0.7 + processing_time * 0.3
                    )

                logger.info(f"流式生成完成 - 块数: {chunk_count}, 耗时: {processing_time:.2f}秒")

            except openai.APIError as e:
                # 记录错误
                self._error_count += 1
                stats = self._client_stats.get(provider, {})
                stats['failures'] = stats.get('failures', 0) + 1

                logger.error(f"OpenAI API错误: {e}")
                raise AIClientError(f"API调用失败: {e}")
            except openai.APIConnectionError as e:
                # 记录错误
                self._error_count += 1
                stats = self._client_stats.get(provider, {})
                stats['failures'] = stats.get('failures', 0) + 1

                logger.error(f"OpenAI连接错误: {e}")
                raise AIServiceUnavailableError(f"无法连接到AI服务: {e}")
            except openai.RateLimitError as e:
                # 记录错误
                self._error_count += 1
                stats = self._client_stats.get(provider, {})
                stats['failures'] = stats.get('failures', 0) + 1

                logger.error(f"OpenAI速率限制: {e}")
                raise AIQuotaExceededError(f"API调用频率超限: {e}")
            except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.TimeoutException) as e:
                # 记录错误
                self._error_count += 1
                stats = self._client_stats.get(provider, {})
                stats['failures'] = stats.get('failures', 0) + 1

                logger.error(f"请求超时: {e}")
                raise AIRequestTimeoutError("AI服务响应超时，请检查网络连接或稍后重试")
            except Exception as e:
                # 记录错误
                self._error_count += 1
                stats = self._client_stats.get(provider, {})
                stats['failures'] = stats.get('failures', 0) + 1

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
                client = await self._get_client("openai")
                model = model or self.config.get('openai_model', 'gpt-3.5-turbo')
            elif provider.lower() == "deepseek":
                client = await self._get_client("deepseek")
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
        except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.TimeoutException) as e:
            logger.error(f"请求超时: {e}")
            raise AIRequestTimeoutError("AI服务响应超时，请检查网络连接或稍后重试")
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

    def _select_available_provider(self) -> str:
        """智能选择可用的AI提供商"""
        # 获取默认提供商
        default_provider = self.config.get('default_provider', 'deepseek')

        # 检查默认提供商的API密钥是否可用
        default_api_key = self.config.get(f"{default_provider}_api_key")
        if default_api_key:
            logger.info(f"🎯 使用默认提供商: {default_provider}")
            return default_provider

        # 如果默认提供商不可用，尝试其他提供商
        providers = ['deepseek', 'openai']
        for provider in providers:
            if provider != default_provider:
                api_key = self.config.get(f"{provider}_api_key")
                if api_key:
                    logger.info(f"🔄 默认提供商 {default_provider} 不可用，切换到: {provider}")
                    return provider

        # 如果都不可用，返回默认提供商（会在后续检查中报错）
        logger.warning(f"⚠️ 没有找到可用的API密钥，使用默认提供商: {default_provider}")
        return default_provider

    def reload_settings(self):
        """重新加载设置配置"""
        logger.info("🔄 重新加载AI客户端设置...")
        old_config = self.config.copy()
        self.config = get_ai_config()

        # 比较配置变化
        changes = []
        if old_config.get('default_provider') != self.config.get('default_provider'):
            changes.append(f"默认提供商: {old_config.get('default_provider')} → {self.config.get('default_provider')}")

        for provider in ['openai', 'deepseek']:
            old_key = old_config.get(f'{provider}_api_key')
            new_key = self.config.get(f'{provider}_api_key')
            if bool(old_key) != bool(new_key):
                status = "已配置" if new_key else "已移除"
                changes.append(f"{provider} API密钥: {status}")

        if changes:
            logger.info("📋 配置变化:")
            for change in changes:
                logger.info(f"  - {change}")
        else:
            logger.info("📋 配置无变化")

        logger.info("✅ AI客户端设置重新加载完成")

    def reload_settings(self):
        """重新加载设置"""
        self.config = get_ai_config()
        self.openai_client.reload_settings()
        logger.info("AI客户端管理器设置已重新加载")
    
    @retry_on_timeout(max_retries=3, delay=3.0)
    async def stream_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成（自动选择提供商）"""
        provider = self._select_available_provider()
        
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
                raise Exception(f"所有AI服务都不可用: 主服务 - {str(e)}, 备用服务 - {str(fallback_error)}")
    
    @retry_on_timeout(max_retries=3, delay=3.0)
    async def simple_generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """简单生成（非流式）"""
        logger.info(f"🎯 AI客户端管理器开始简单生成，提示词长度: {len(prompt)}")

        # 智能选择可用的提供商
        provider = self._select_available_provider()
        logger.debug(f"使用提供商: {provider}")
        logger.debug(f"配置信息: max_tokens={max_tokens}, temperature={temperature}, model={model}")

        # 检查API密钥
        api_key_key = f"{provider}_api_key"
        api_key = self.config.get(api_key_key)
        if not api_key:
            logger.error(f"❌ {provider} API密钥未配置")
            raise Exception(f"{provider} API密钥未配置")
        else:
            logger.debug(f"✅ {provider} API密钥已配置: {api_key[:10]}...")

        try:
            logger.info(f"📡 调用 {provider} 客户端...")
            result = await self.openai_client.complete_with_prompt(
                prompt=prompt,
                context=context,
                provider=provider,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )

            logger.info(f"✅ {provider} 生成成功，响应长度: {len(result) if result else 0}")
            return result
            
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
                raise Exception(f"所有AI服务都不可用: 主服务 - {str(e)}, 备用服务 - {str(fallback_error)}")
    



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


# 为OpenAIStreamingClient添加性能监控方法
def add_performance_methods_to_client():
    """为OpenAIStreamingClient添加性能监控方法"""

    def get_client_statistics(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return {
            'total_requests': getattr(self, '_request_count', 0),
            'total_successes': getattr(self, '_success_count', 0),
            'total_errors': getattr(self, '_error_count', 0),
            'success_rate': getattr(self, '_success_count', 0) / max(getattr(self, '_request_count', 1), 1),
            'active_clients': len(getattr(self, '_clients', {})),
            'cache_size': len(getattr(self, '_request_cache', {})),
            'provider_stats': dict(getattr(self, '_client_stats', {}))
        }

    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """获取提供商健康状态"""
        health_info = {}
        client_stats = getattr(self, '_client_stats', {})

        for provider, stats in client_stats.items():
            if stats.get('requests', 0) > 0:
                success_rate = stats.get('successes', 0) / stats['requests']
                health_info[provider] = {
                    'is_healthy': success_rate >= 0.8,
                    'success_rate': success_rate,
                    'avg_response_time': stats.get('avg_response_time', 0),
                    'total_requests': stats.get('requests', 0),
                    'last_used': stats.get('last_used')
                }

        return health_info

    def clear_cache(self):
        """清理缓存"""
        if hasattr(self, '_request_cache'):
            self._request_cache.clear()
            logger.info("AI客户端缓存已清理")

    def reset_statistics(self):
        """重置统计信息"""
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        if hasattr(self, '_client_stats'):
            self._client_stats.clear()
        logger.info("AI客户端统计信息已重置")

    # 动态添加方法到类
    OpenAIStreamingClient.get_client_statistics = get_client_statistics
    OpenAIStreamingClient.get_provider_health = get_provider_health
    OpenAIStreamingClient.clear_cache = clear_cache
    OpenAIStreamingClient.reset_statistics = reset_statistics

# 调用函数添加方法
add_performance_methods_to_client()

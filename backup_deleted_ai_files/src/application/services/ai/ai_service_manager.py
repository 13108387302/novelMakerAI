#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务管理器 - 重构版本

统一管理和协调各种AI服务和提供商
"""

import asyncio
import time
from typing import Dict, List, Optional, AsyncGenerator, Set, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

from PyQt6.QtCore import QObject, QTimer

from .core_abstractions import (
    IAIService, IAIServiceManager, IAIProvider, IAIFunctionModule,
    AIRequest, AIResponse, AICapability, AIRequestType,
    AIServiceEvents, AIServiceConfig, AIServiceError, AIRequestPriority
)
# 移除有问题的元类导入
try:
    from src.shared.utils.logger import get_logger
    from src.shared.events.event_bus import EventBus
    from src.shared.utils.cache_manager import CacheManager
except ImportError:
    # 如果无法导入，使用替代实现
    import logging
    def get_logger(name):
        return logging.getLogger(name)

    class EventBus:
        """事件总线替代实现"""
        def __init__(self):
            pass

    class CacheManager:
        """缓存管理器替代实现"""
        def __init__(self):
            self._cache = {}

        def get(self, key):
            return self._cache.get(key)

        def set(self, key, value, ttl=None):
            self._cache[key] = value

logger = get_logger(__name__)


class AIServiceManager(QObject):
    """
    AI服务管理器 - 优化版本

    统一管理AI提供商、功能模块和请求路由，提供高性能的AI服务调度

    新增功能：
    - 智能负载均衡
    - 请求优先级队列
    - 性能监控和统计
    - 智能缓存机制
    - 故障转移和恢复
    """

    def __init__(self, config: AIServiceConfig, event_bus: EventBus):
        super().__init__()
        self.config = config
        self.event_bus = event_bus
        self.events = AIServiceEvents()

        # 提供商管理
        self._providers: Dict[str, IAIProvider] = {}
        self._default_provider: Optional[str] = config.default_provider
        self._provider_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'avg_response_time': 0.0,
            'last_used': None,
            'is_healthy': True
        })

        # 功能模块管理
        self._function_modules: Dict[str, IAIFunctionModule] = {}

        # 请求管理 - 优先级队列
        self._request_queues: Dict[AIRequestPriority, deque] = {
            priority: deque() for priority in AIRequestPriority
        }
        self._active_requests: Dict[str, AIRequest] = {}
        self._request_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._processing_requests: Set[str] = set()

        # 缓存管理
        self._cache_manager = CacheManager() if config.enable_caching else None

        # 性能监控
        self._start_time = time.time()
        self._total_requests = 0
        self._total_successes = 0
        self._total_failures = 0

        # 健康检查定时器
        self._health_check_timer = QTimer()
        self._health_check_timer.timeout.connect(self._perform_health_check)
        self._health_check_timer.start(60000)  # 每分钟检查一次

        logger.info("AI服务管理器初始化完成（优化版本）")
    
    # IAIServiceManager 接口实现
    
    def register_provider(self, provider: IAIProvider) -> None:
        """注册AI提供商"""
        name = provider.get_name()
        self._providers[name] = provider
        self.events.provider_registered.emit(name)
        logger.info(f"注册AI提供商: {name}")
    
    def get_provider(self, name: str) -> Optional[IAIProvider]:
        """获取AI提供商"""
        return self._providers.get(name)
    
    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        return list(self._providers.keys())
    
    async def route_request(self, request: AIRequest, provider_name: Optional[str] = None) -> AIResponse:
        """路由请求到合适的提供商 - 优化版本"""
        start_time = time.time()

        try:
            # 验证请求
            if not request.is_valid():
                errors = request.validate()
                raise AIServiceError(
                    f"请求验证失败: {', '.join(errors)}",
                    error_code='INVALID_REQUEST'
                )

            # 检查缓存
            if self._cache_manager and not request.stream:
                cache_key = self._generate_cache_key(request)
                cached_response = self._cache_manager.get(cache_key)
                if cached_response:
                    logger.debug(f"缓存命中: {request.id}")
                    return cached_response

            # 获取信号量
            async with self._request_semaphore:
                self._active_requests[request.id] = request
                self._processing_requests.add(request.id)
                self.events.request_started.emit(request.id)

                try:
                    # 选择提供商
                    if provider_name:
                        provider = self.get_provider(provider_name)
                        if not provider:
                            raise AIServiceError(
                                f"提供商 {provider_name} 不存在",
                                error_code='PROVIDER_NOT_FOUND'
                            )
                    else:
                        provider = await self._select_best_provider(request)
                        if not provider:
                            raise AIServiceError(
                                "没有可用的AI提供商",
                                error_code='NO_PROVIDER_AVAILABLE'
                            )

                    provider_name = provider.get_name()

                    # 检查功能模块
                    function_module = self._get_function_module_for_request(request)
                    if function_module:
                        response = await function_module.process(request)
                    else:
                        # 直接使用提供商
                        response = await provider.generate_text(request)

                    # 更新统计信息
                    processing_time = time.time() - start_time
                    response.processing_time = processing_time
                    response.provider = provider_name

                    self._update_provider_stats(provider_name, True, processing_time)
                    self._total_requests += 1
                    self._total_successes += 1

                    # 缓存响应
                    if self._cache_manager and response.is_success() and not request.stream:
                        cache_key = self._generate_cache_key(request)
                        self._cache_manager.set(cache_key, response, ttl=self.config.cache_ttl)

                    self.events.request_completed.emit(request.id, response.content)
                    return response

                finally:
                    # 清理
                    self._active_requests.pop(request.id, None)
                    self._processing_requests.discard(request.id)

        except Exception as e:
            # 错误处理
            processing_time = time.time() - start_time
            if provider_name:
                self._update_provider_stats(provider_name, False, processing_time)

            self._total_requests += 1
            self._total_failures += 1

            error_msg = str(e)
            self.events.request_failed.emit(request.id, error_msg)

            if isinstance(e, AIServiceError):
                raise
            else:
                raise AIServiceError(
                    f"请求处理失败: {error_msg}",
                    error_code='PROCESSING_ERROR',
                    cause=e
                )
    
    # IAIService 接口实现
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """处理AI请求"""
        async with self._request_semaphore:
            try:
                self._active_requests[request.id] = request
                self.events.request_started.emit(request.id)
                
                response = await self.route_request(request)
                
                self.events.request_completed.emit(request.id, response.content)
                return response
                
            except Exception as e:
                error_msg = str(e)
                self.events.request_failed.emit(request.id, error_msg)
                logger.error(f"处理请求失败 {request.id}: {error_msg}")
                raise
            finally:
                self._active_requests.pop(request.id, None)
    
    async def process_request_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """流式处理AI请求"""
        async with self._request_semaphore:
            try:
                self._active_requests[request.id] = request
                self.events.stream_started.emit(request.id)
                
                provider = await self._select_best_provider(request)
                if not provider:
                    raise AIServiceError("没有可用的AI提供商")
                
                async for chunk in provider.generate_text_stream(request):
                    self.events.stream_chunk_received.emit(request.id, chunk)
                    yield chunk
                
                self.events.stream_completed.emit(request.id)
                
            except Exception as e:
                error_msg = str(e)
                self.events.stream_error.emit(request.id, error_msg)
                logger.error(f"流式处理请求失败 {request.id}: {error_msg}")
                raise
            finally:
                self._active_requests.pop(request.id, None)
    
    async def check_service_availability(self) -> bool:
        """检查服务可用性"""
        if not self._providers:
            return False
        
        # 检查至少有一个提供商可用
        for provider in self._providers.values():
            if await provider.is_available():
                return True
        
        return False
    
    def get_supported_capabilities(self) -> List[AICapability]:
        """获取支持的能力"""
        capabilities = set()
        for provider in self._providers.values():
            capabilities.update(provider.get_capabilities())
        return list(capabilities)
    
    async def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        if request_id in self._active_requests:
            self._active_requests.pop(request_id, None)
            self.events.request_cancelled.emit(request_id)
            logger.info(f"取消请求: {request_id}")
            return True
        return False
    
    def get_active_requests(self) -> List[str]:
        """获取活跃请求列表"""
        return list(self._active_requests.keys())
    
    # 功能模块管理
    
    def register_function_module(self, module: IAIFunctionModule) -> None:
        """注册功能模块"""
        name = module.get_module_name()
        self._function_modules[name] = module
        logger.info(f"注册AI功能模块: {name}")
    
    def get_function_module(self, name: str) -> Optional[IAIFunctionModule]:
        """获取功能模块"""
        return self._function_modules.get(name)
    
    def get_available_function_modules(self) -> List[str]:
        """获取可用的功能模块列表"""
        return [name for name, module in self._function_modules.items() if module.is_available()]
    
    # 私有方法 - 优化版本

    async def _select_best_provider(self, request: AIRequest) -> Optional[IAIProvider]:
        """选择最佳提供商 - 智能负载均衡"""
        available_providers = []

        # 检查所有提供商的可用性和健康状态
        for name, provider in self._providers.items():
            stats = self._provider_stats[name]
            if stats['is_healthy'] and await provider.is_available():
                available_providers.append((name, provider, stats))

        if not available_providers:
            return None

        # 优先使用默认提供商（如果健康）
        if self._default_provider:
            for name, provider, stats in available_providers:
                if name == self._default_provider:
                    return provider

        # 基于性能选择最佳提供商
        # 考虑因素：成功率、平均响应时间、最近使用时间
        def provider_score(item):
            name, provider, stats = item
            success_rate = stats['successes'] / max(stats['requests'], 1)
            response_time = stats['avg_response_time']

            # 成功率权重70%，响应时间权重30%
            score = success_rate * 0.7 + (1.0 / max(response_time, 0.1)) * 0.3

            # 如果最近没有使用，给予小幅加分（负载均衡）
            if stats['last_used'] is None or \
               (datetime.now() - stats['last_used']).seconds > 300:
                score += 0.1

            return score

        # 选择得分最高的提供商
        best_provider = max(available_providers, key=provider_score)
        return best_provider[1]

    def _generate_cache_key(self, request: AIRequest) -> str:
        """生成缓存键"""
        import hashlib

        # 基于请求内容生成唯一键
        content = f"{request.type.value}:{request.prompt}:{request.context}"

        # 添加重要参数
        if request.max_tokens:
            content += f":max_tokens={request.max_tokens}"
        if request.temperature:
            content += f":temperature={request.temperature}"

        return hashlib.md5(content.encode()).hexdigest()

    def _update_provider_stats(self, provider_name: str, success: bool, response_time: float):
        """更新提供商统计信息"""
        stats = self._provider_stats[provider_name]

        stats['requests'] += 1
        stats['last_used'] = datetime.now()

        if success:
            stats['successes'] += 1
        else:
            stats['failures'] += 1

        # 更新平均响应时间（指数移动平均）
        if stats['avg_response_time'] == 0:
            stats['avg_response_time'] = response_time
        else:
            alpha = 0.3  # 平滑因子
            stats['avg_response_time'] = (
                alpha * response_time +
                (1 - alpha) * stats['avg_response_time']
            )

        # 更新健康状态
        success_rate = stats['successes'] / stats['requests']
        stats['is_healthy'] = success_rate >= 0.8  # 成功率低于80%认为不健康

    async def _perform_health_check(self):
        """执行健康检查"""
        logger.debug("执行AI提供商健康检查")

        for name, provider in self._providers.items():
            try:
                is_available = await asyncio.wait_for(
                    provider.is_available(),
                    timeout=5.0
                )
                self._provider_stats[name]['is_healthy'] = is_available

                if not is_available:
                    logger.warning(f"提供商 {name} 健康检查失败")

            except asyncio.TimeoutError:
                logger.warning(f"提供商 {name} 健康检查超时")
                self._provider_stats[name]['is_healthy'] = False
            except Exception as e:
                logger.error(f"提供商 {name} 健康检查异常: {e}")
                self._provider_stats[name]['is_healthy'] = False
    
    def _get_function_module_for_request(self, request: AIRequest) -> Optional[IAIFunctionModule]:
        """为请求选择合适的功能模块"""
        for module in self._function_modules.values():
            if (module.is_available() and 
                request.type in module.get_supported_request_types()):
                return module
        return None
    
    # 配置管理
    
    def update_config(self, config: AIServiceConfig) -> None:
        """更新配置"""
        self.config = config
        self._default_provider = config.default_provider
        self._request_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        logger.info("AI服务配置已更新")
    
    def get_config(self) -> AIServiceConfig:
        """获取当前配置"""
        return self.config
    
    # 统计信息和监控 - 增强版本

    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        uptime = time.time() - self._start_time

        return {
            # 基础信息
            'providers_count': len(self._providers),
            'function_modules_count': len(self._function_modules),
            'active_requests_count': len(self._active_requests),
            'processing_requests_count': len(self._processing_requests),
            'registered_providers': list(self._providers.keys()),

            # 性能统计
            'total_requests': self._total_requests,
            'total_successes': self._total_successes,
            'total_failures': self._total_failures,
            'success_rate': self._total_successes / max(self._total_requests, 1),
            'uptime_seconds': uptime,

            # 提供商统计
            'provider_stats': dict(self._provider_stats),

            # 队列状态
            'queue_lengths': {
                priority.name: len(queue)
                for priority, queue in self._request_queues.items()
            },

            # 配置信息
            'config': self.config.to_dict()
        }

    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """获取提供商健康状态"""
        health_info = {}

        for name, stats in self._provider_stats.items():
            health_info[name] = {
                'is_healthy': stats['is_healthy'],
                'success_rate': stats['successes'] / max(stats['requests'], 1),
                'avg_response_time': stats['avg_response_time'],
                'total_requests': stats['requests'],
                'last_used': stats['last_used'].isoformat() if stats['last_used'] else None
            }

        return health_info

    def reset_statistics(self):
        """重置统计信息"""
        self._start_time = time.time()
        self._total_requests = 0
        self._total_successes = 0
        self._total_failures = 0

        # 重置提供商统计
        for stats in self._provider_stats.values():
            stats.update({
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0.0,
                'last_used': None
            })

        logger.info("AI服务管理器统计信息已重置")

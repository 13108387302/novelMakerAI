#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI客户端工厂

负责创建和管理AI客户端实例
"""

import logging
from typing import Dict, Any, Optional, Type, List
from enum import Enum

from .base_ai_client import BaseAIClient
from .openai_client import OpenAIClient
from .deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


class SupportedProvider(Enum):
    """支持的AI提供商"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class AIClientFactory:
    """
    AI客户端工厂
    
    负责创建和管理不同类型的AI客户端
    """
    
    # 客户端类型映射
    _client_classes: Dict[str, Type[BaseAIClient]] = {
        SupportedProvider.OPENAI.value: OpenAIClient,
        SupportedProvider.DEEPSEEK.value: DeepSeekClient,
    }
    
    # 客户端实例缓存
    _client_instances: Dict[str, BaseAIClient] = {}
    
    @classmethod
    def create_client(
        cls,
        provider: str,
        config: Dict[str, Any],
        use_cache: bool = True
    ) -> BaseAIClient:
        """
        创建AI客户端
        
        Args:
            provider: 提供商名称
            config: 配置信息
            use_cache: 是否使用缓存
            
        Returns:
            BaseAIClient: AI客户端实例
            
        Raises:
            ValueError: 不支持的提供商
            RuntimeError: 客户端创建失败
        """
        provider = provider.lower()
        
        # 检查是否支持该提供商
        if provider not in cls._client_classes:
            supported = list(cls._client_classes.keys())
            raise ValueError(f"不支持的AI提供商: {provider}，支持的提供商: {supported}")
        
        # 生成缓存键
        cache_key = cls._generate_cache_key(provider, config)
        
        # 检查缓存
        if use_cache and cache_key in cls._client_instances:
            logger.debug(f"使用缓存的AI客户端: {provider}")
            return cls._client_instances[cache_key]
        
        try:
            # 创建客户端实例
            client_class = cls._client_classes[provider]
            client = client_class(config)
            
            # 缓存实例
            if use_cache:
                cls._client_instances[cache_key] = client
            
            logger.info(f"创建AI客户端成功: {provider}")
            return client
            
        except Exception as e:
            logger.error(f"创建AI客户端失败: {provider}, 错误: {e}")
            raise RuntimeError(f"创建AI客户端失败: {e}")
    
    @classmethod
    async def create_and_connect_client(
        cls,
        provider: str,
        config: Dict[str, Any],
        use_cache: bool = True
    ) -> BaseAIClient:
        """
        创建并连接AI客户端
        
        Args:
            provider: 提供商名称
            config: 配置信息
            use_cache: 是否使用缓存
            
        Returns:
            BaseAIClient: 已连接的AI客户端实例
            
        Raises:
            ValueError: 不支持的提供商
            RuntimeError: 客户端创建或连接失败
        """
        client = cls.create_client(provider, config, use_cache)
        
        try:
            # 连接客户端
            if not await client.connect():
                raise RuntimeError(f"连接AI客户端失败: {provider}")
            
            logger.info(f"AI客户端连接成功: {provider}")
            return client
            
        except Exception as e:
            logger.error(f"连接AI客户端失败: {provider}, 错误: {e}")
            raise RuntimeError(f"连接AI客户端失败: {e}")
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """
        获取支持的提供商列表
        
        Returns:
            List[str]: 支持的提供商名称列表
        """
        return list(cls._client_classes.keys())
    
    @classmethod
    def is_provider_supported(cls, provider: str) -> bool:
        """
        检查是否支持指定提供商
        
        Args:
            provider: 提供商名称
            
        Returns:
            bool: 是否支持
        """
        return provider.lower() in cls._client_classes
    
    @classmethod
    def register_client_class(
        cls,
        provider: str,
        client_class: Type[BaseAIClient]
    ) -> None:
        """
        注册新的客户端类
        
        Args:
            provider: 提供商名称
            client_class: 客户端类
        """
        if not issubclass(client_class, BaseAIClient):
            raise ValueError("客户端类必须继承自BaseAIClient")
        
        cls._client_classes[provider.lower()] = client_class
        logger.info(f"注册AI客户端类: {provider}")
    
    @classmethod
    def clear_cache(cls) -> None:
        """清空客户端缓存"""
        cls._client_instances.clear()
        logger.info("AI客户端缓存已清空")
    
    @classmethod
    async def disconnect_all_clients(cls) -> None:
        """断开所有缓存的客户端连接"""
        for client in cls._client_instances.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"断开客户端连接失败: {e}")
        
        cls.clear_cache()
        logger.info("所有AI客户端已断开连接")
    
    @classmethod
    def get_client_statistics(cls) -> Dict[str, Any]:
        """
        获取所有客户端的统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            'total_clients': len(cls._client_instances),
            'supported_providers': cls.get_supported_providers(),
            'clients': {}
        }
        
        for cache_key, client in cls._client_instances.items():
            stats['clients'][cache_key] = client.get_statistics()
        
        return stats
    
    @classmethod
    def _generate_cache_key(cls, provider: str, config: Dict[str, Any]) -> str:
        """
        生成缓存键
        
        Args:
            provider: 提供商名称
            config: 配置信息
            
        Returns:
            str: 缓存键
        """
        # 使用提供商名称和关键配置生成缓存键
        key_parts = [provider]
        
        # 添加关键配置项
        key_configs = ['api_key', 'base_url', 'default_model']
        for key in key_configs:
            if key in config:
                # 对于敏感信息（如API密钥），只使用前几个字符
                value = config[key]
                if key == 'api_key' and len(value) > 8:
                    value = value[:8] + "..."
                key_parts.append(f"{key}={value}")
        
        return "|".join(key_parts)
    
    @classmethod
    def get_default_config(cls, provider: str) -> Dict[str, Any]:
        """
        获取提供商的默认配置
        
        Args:
            provider: 提供商名称
            
        Returns:
            Dict[str, Any]: 默认配置
        """
        default_configs = {
            SupportedProvider.OPENAI.value: {
                'base_url': 'https://api.openai.com/v1',
                'default_model': 'gpt-3.5-turbo',
                'max_tokens': 2000,
                'temperature': 0.7,
                'default_timeout': 30.0,
                'stream_timeout': 60.0,
                'max_concurrent_requests': 10
            },
            SupportedProvider.DEEPSEEK.value: {
                'base_url': 'https://api.deepseek.com/v1',
                'default_model': 'deepseek-chat',
                'max_tokens': 2000,
                'temperature': 0.7,
                'default_timeout': 30.0,
                'stream_timeout': 60.0,
                'max_concurrent_requests': 10
            }
        }
        
        return default_configs.get(provider.lower(), {})

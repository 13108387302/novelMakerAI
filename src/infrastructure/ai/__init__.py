#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI基础设施模块

提供AI相关的基础设施组件，包括客户端、适配器和仓储实现
遵循DDD架构原则，实现领域层定义的接口
"""

# 客户端
from .clients.base_ai_client import BaseAIClient
from .clients.openai_client import OpenAIClient
from .clients.deepseek_client import DeepSeekClient
from .clients.ai_client_factory import AIClientFactory

# 适配器
from .adapters.openai_adapter import OpenAIAdapter
from .adapters.deepseek_adapter import DeepSeekAdapter
from .adapters.ai_adapter_factory import AIAdapterFactory

# 仓储实现
from .repositories.ai_provider_repository_impl import AIProviderRepositoryImpl
from .repositories.ai_function_repository_impl import AIFunctionRepositoryImpl
from .repositories.ai_request_repository_impl import AIRequestRepositoryImpl

# 配置
from .config.ai_config import AIConfig
from .config.provider_config import ProviderConfig

# 工具
from .utils.token_counter import TokenCounter
from .utils.response_parser import ResponseParser
from .utils.error_handler import AIErrorHandler

__all__ = [
    # 客户端
    'BaseAIClient',
    'OpenAIClient',
    'DeepSeekClient',
    'AIClientFactory',
    
    # 适配器
    'OpenAIAdapter',
    'DeepSeekAdapter',
    'AIAdapterFactory',
    
    # 仓储实现
    'AIProviderRepositoryImpl',
    'AIFunctionRepositoryImpl',
    'AIRequestRepositoryImpl',
    
    # 配置
    'AIConfig',
    'ProviderConfig',
    
    # 工具
    'TokenCounter',
    'ResponseParser',
    'AIErrorHandler'
]

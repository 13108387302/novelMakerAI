#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI客户端实现

提供OpenAI API的客户端实现
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List
import openai
from openai import AsyncOpenAI

from .base_ai_client import BaseAIClient
from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
from src.domain.ai.value_objects.ai_capability import AICapability
from src.domain.ai.value_objects.ai_request_type import AIRequestType
from src.shared.constants import (
    AI_TIMEOUT_SECONDS, AI_MAX_TOKENS, AI_TEMPERATURE
)

logger = logging.getLogger(__name__)

# OpenAI客户端常量
DEFAULT_OPENAI_BASE_URL = 'https://api.openai.com/v1'
DEFAULT_OPENAI_MODEL = 'gpt-3.5-turbo'
DEFAULT_MAX_TOKENS = AI_MAX_TOKENS
DEFAULT_TEMPERATURE = AI_TEMPERATURE
SYSTEM_ROLE = "system"
USER_ROLE = "user"
TEST_MAX_TOKENS = 1
CONNECTION_TIMEOUT = AI_TIMEOUT_SECONDS
API_KEY_ERROR_MSG = "OpenAI API密钥未配置"
CLIENT_NOT_CONNECTED_MSG = "OpenAI客户端未连接"
CLIENT_NOT_INITIALIZED_MSG = "客户端未初始化"


class OpenAIClient(BaseAIClient):
    """
    OpenAI客户端实现
    
    提供OpenAI API的完整客户端功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化OpenAI客户端
        
        Args:
            config: 配置信息，包含API密钥等
        """
        super().__init__("openai", config)
        
        # OpenAI配置
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', DEFAULT_OPENAI_BASE_URL)
        self.default_model = config.get('default_model', DEFAULT_OPENAI_MODEL)
        self.max_tokens = config.get('max_tokens', DEFAULT_MAX_TOKENS)
        self.temperature = config.get('temperature', DEFAULT_TEMPERATURE)
        
        # 客户端实例
        self.client: Optional[AsyncOpenAI] = None
        
        # 支持的能力
        self._capabilities = [
            AICapability.TEXT_GENERATION,
            AICapability.CONVERSATION,
            AICapability.CREATIVE_WRITING,
            AICapability.TEXT_ANALYSIS,
            AICapability.TEXT_OPTIMIZATION,
            AICapability.TEXT_SUMMARIZATION,
            AICapability.LANGUAGE_TRANSLATION,
            AICapability.QUESTION_ANSWERING,
            AICapability.STREAMING_OUTPUT,
            AICapability.CONTEXT_AWARENESS
        ]
    
    async def connect(self) -> bool:
        """
        连接到OpenAI服务
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if not self.api_key:
                raise ValueError(API_KEY_ERROR_MSG)
            
            # 创建异步客户端
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.default_timeout
            )
            
            # 测试连接
            await self._test_connection()
            
            self.is_connected = True
            logger.info(f"OpenAI客户端连接成功: {self.base_url}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            logger.error(f"OpenAI客户端连接失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开OpenAI服务连接"""
        if self.client:
            await self.client.close()
            self.client = None
        
        self.is_connected = False
        logger.info("OpenAI客户端已断开连接")
    
    async def is_healthy(self) -> bool:
        """
        检查客户端健康状态
        
        Returns:
            bool: 是否健康
        """
        if not self.is_connected or not self.client:
            return False
        
        try:
            # 简单的健康检查
            await self._test_connection()
            return True
        except Exception as e:
            logger.warning(f"OpenAI客户端健康检查失败: {e}")
            return False
    
    async def get_capabilities(self) -> List[AICapability]:
        """
        获取客户端支持的能力
        
        Returns:
            List[AICapability]: 支持的能力列表
        """
        return self._capabilities.copy()
    
    async def generate_text(
        self,
        request: AIRequest,
        timeout: Optional[float] = None
    ) -> AIResponse:
        """
        生成文本
        
        Args:
            request: AI请求
            timeout: 超时时间
            
        Returns:
            AIResponse: AI响应
        """
        if not self.client:
            raise RuntimeError(CLIENT_NOT_CONNECTED_MSG)
        
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取模型参数
            model = request.parameters.get('model', self.default_model)
            max_tokens = request.parameters.get('max_tokens', self.max_tokens)
            temperature = request.parameters.get('temperature', self.temperature)
            
            # 调用OpenAI API
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout or self.default_timeout
            )
            
            # 构建响应
            content = response.choices[0].message.content or ""
            ai_response = AIResponse(
                request_id=request.id,
                content=content,
                status=AIResponseStatus.COMPLETED,
                provider=self.provider_name,
                model=model
            )
            
            # 设置质量指标
            ai_response.quality_metrics.token_count = response.usage.total_tokens if response.usage else 0
            ai_response.quality_metrics.calculate_content_metrics(content)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"OpenAI文本生成失败: {e}")
            raise
    
    async def generate_text_stream(
        self,
        request: AIRequest,
        timeout: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成文本
        
        Args:
            request: AI请求
            timeout: 超时时间
            
        Yields:
            str: 文本块
        """
        if not self.client:
            raise RuntimeError(CLIENT_NOT_CONNECTED_MSG)
        
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取模型参数
            model = request.parameters.get('model', self.default_model)
            max_tokens = request.parameters.get('max_tokens', self.max_tokens)
            temperature = request.parameters.get('temperature', self.temperature)
            
            # 调用OpenAI流式API
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=timeout or self.stream_timeout
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI流式生成失败: {e}")
            raise
    
    def _build_messages(self, request: AIRequest) -> List[Dict[str, str]]:
        """
        构建OpenAI消息格式
        
        Args:
            request: AI请求
            
        Returns:
            List[Dict[str, str]]: OpenAI消息格式
        """
        messages = []
        
        # 添加系统消息（如果有上下文）
        if request.context:
            messages.append({
                "role": SYSTEM_ROLE,
                "content": f"上下文信息：\n{request.context}"
            })
        
        # 添加用户消息
        messages.append({
            "role": USER_ROLE,
            "content": request.prompt
        })
        
        return messages
    
    async def _test_connection(self) -> None:
        """测试连接"""
        if not self.client:
            raise RuntimeError(CLIENT_NOT_INITIALIZED_MSG)
        
        # 发送简单的测试请求
        await self.client.chat.completions.create(
            model=self.default_model,
            messages=[{"role": USER_ROLE, "content": "test"}],
            max_tokens=TEST_MAX_TOKENS,
            timeout=CONNECTION_TIMEOUT
        )

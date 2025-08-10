#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek客户端实现

提供DeepSeek API的客户端实现
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
from src.shared.constants import (
    AI_TIMEOUT_SECONDS, AI_MAX_TOKENS, AI_TEMPERATURE
)

logger = logging.getLogger(__name__)

# DeepSeek客户端常量
DEFAULT_DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
DEFAULT_DEEPSEEK_MODEL = 'deepseek-chat'
DEFAULT_MAX_TOKENS = AI_MAX_TOKENS
DEFAULT_TEMPERATURE = AI_TEMPERATURE
SYSTEM_ROLE = "system"
USER_ROLE = "user"
TEST_MAX_TOKENS = 1
CONNECTION_TIMEOUT = AI_TIMEOUT_SECONDS
API_KEY_ERROR_MSG = "DeepSeek API密钥未配置"
CLIENT_NOT_CONNECTED_MSG = "DeepSeek客户端未连接"
CLIENT_NOT_INITIALIZED_MSG = "客户端未初始化"


class DeepSeekClient(BaseAIClient):
    """
    DeepSeek客户端实现
    
    提供DeepSeek API的完整客户端功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DeepSeek客户端
        
        Args:
            config: 配置信息，包含API密钥等
        """
        super().__init__("deepseek", config)
        
        # DeepSeek配置
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', DEFAULT_DEEPSEEK_BASE_URL)
        self.default_model = config.get('default_model', DEFAULT_DEEPSEEK_MODEL)
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
            AICapability.CONTEXT_AWARENESS,
            AICapability.CREATIVE_INSPIRATION
        ]
    
    async def connect(self) -> bool:
        """
        连接到DeepSeek服务
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if not self.api_key:
                raise ValueError("DeepSeek API密钥未配置")
            
            # 创建异步客户端（使用OpenAI兼容接口）
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.default_timeout
            )
            
            # 测试连接
            await self._test_connection()
            
            self.is_connected = True
            logger.info(f"DeepSeek客户端连接成功: {self.base_url}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.is_connected = False
            logger.error(f"DeepSeek客户端连接失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开DeepSeek服务连接"""
        if self.client:
            await self.client.close()
            self.client = None
        
        self.is_connected = False
        logger.info("DeepSeek客户端已断开连接")
    
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
            logger.warning(f"DeepSeek客户端健康检查失败: {e}")
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
            raise RuntimeError("DeepSeek客户端未连接")
        
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取模型参数（兼容显式传入None的情况，回落到默认模型）
            model = request.parameters.get('model') or self.default_model
            max_tokens = request.parameters.get('max_tokens', self.max_tokens)
            temperature = request.parameters.get('temperature', self.temperature)

            # 调用DeepSeek API
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
            logger.error(f"DeepSeek文本生成失败: {e}")
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
            raise RuntimeError("DeepSeek客户端未连接")
        
        try:
            # 构建消息
            messages = self._build_messages(request)
            
            # 获取模型参数（兼容显式传入None的情况，回落到默认模型）
            model = request.parameters.get('model') or self.default_model
            max_tokens = request.parameters.get('max_tokens', self.max_tokens)
            temperature = request.parameters.get('temperature', self.temperature)

            # 调用DeepSeek流式API
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=timeout or self.stream_timeout
            )
            
            chunk_count = 0
            async for chunk in stream:
                chunk_count += 1
                logger.debug(f"🔄 DeepSeek chunk {chunk_count}: {chunk}")

                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"📦 提取内容: '{content}' (长度: {len(content)})")
                    yield content
                else:
                    logger.debug(f"⚠️ 空chunk或无内容: choices={bool(chunk.choices)}")

            logger.info(f"✅ DeepSeek流式生成完成，共处理 {chunk_count} 个chunk")
                    
        except Exception as e:
            logger.error(f"DeepSeek流式生成失败: {e}")
            raise
    
    def _build_messages(self, request: AIRequest) -> List[Dict[str, str]]:
        """
        构建DeepSeek消息格式
        
        Args:
            request: AI请求
            
        Returns:
            List[Dict[str, str]]: DeepSeek消息格式
        """
        messages = []
        
        # 添加系统消息（如果有上下文）
        if request.context:
            messages.append({
                "role": "system",
                "content": f"上下文信息：\n{request.context}"
            })
        
        # 添加用户消息
        messages.append({
            "role": "user",
            "content": request.prompt
        })
        
        return messages
    
    async def _test_connection(self) -> None:
        """测试连接"""
        if not self.client:
            raise RuntimeError("客户端未初始化")
        
        # 发送简单的测试请求
        await self.client.chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
            timeout=5.0
        )

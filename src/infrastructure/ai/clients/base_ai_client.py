#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础AI客户端抽象类

定义AI客户端的通用接口和行为
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio
import logging
from datetime import datetime

from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse, AIResponseStatus
from src.domain.ai.value_objects.ai_capability import AICapability
from src.domain.ai.value_objects.ai_quality_metrics import AIQualityMetrics

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """
    基础AI客户端抽象类
    
    定义所有AI客户端必须实现的接口
    """
    
    def __init__(self, provider_name: str, config: Dict[str, Any]):
        """
        初始化AI客户端
        
        Args:
            provider_name: 提供商名称
            config: 配置信息
        """
        self.provider_name = provider_name
        self.config = config
        self.is_connected = False
        self.last_error = None
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # 连接池和限流
        self.max_concurrent_requests = config.get('max_concurrent_requests', 10)
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # 超时配置
        self.default_timeout = config.get('default_timeout', 30.0)
        self.stream_timeout = config.get('stream_timeout', 60.0)
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        连接到AI服务
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开AI服务连接"""
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        检查客户端健康状态
        
        Returns:
            bool: 是否健康
        """
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[AICapability]:
        """
        获取客户端支持的能力
        
        Returns:
            List[AICapability]: 支持的能力列表
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        # 子类必须实现此方法
        raise NotImplementedError("子类必须实现generate_text_stream方法")
        yield  # 使其成为生成器函数
    
    async def process_request(
        self,
        request: AIRequest,
        use_streaming: bool = False,
        timeout: Optional[float] = None
    ) -> AIResponse:
        """
        处理AI请求（统一入口）
        
        Args:
            request: AI请求
            use_streaming: 是否使用流式输出
            timeout: 超时时间
            
        Returns:
            AIResponse: AI响应
        """
        async with self.request_semaphore:
            self.request_count += 1
            start_time = datetime.now()
            
            try:
                # 检查连接状态
                if not self.is_connected:
                    await self.connect()
                
                # 创建响应对象
                response = AIResponse(
                    request_id=request.id,
                    provider=self.provider_name,
                    status=AIResponseStatus.PROCESSING
                )
                
                # 设置超时时间
                actual_timeout = timeout or (
                    self.stream_timeout if use_streaming else self.default_timeout
                )
                
                if use_streaming:
                    # 流式处理
                    response.is_streaming = True
                    response.status = AIResponseStatus.STREAMING
                    
                    async for chunk in self.generate_text_stream(request, actual_timeout):
                        response.append_stream_chunk(chunk)
                    
                    response.complete()
                else:
                    # 非流式处理
                    response = await self.generate_text(request, actual_timeout)
                
                # 计算响应时间
                end_time = datetime.now()
                response.quality_metrics.response_time = (end_time - start_time).total_seconds()
                
                # 更新统计
                self.success_count += 1
                
                return response
                
            except asyncio.TimeoutError:
                self.error_count += 1
                response = AIResponse(
                    request_id=request.id,
                    provider=self.provider_name,
                    status=AIResponseStatus.TIMEOUT,
                    error_message="请求超时"
                )
                response.timeout()
                return response
                
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                logger.error(f"AI请求处理失败: {e}")
                
                response = AIResponse(
                    request_id=request.id,
                    provider=self.provider_name,
                    status=AIResponseStatus.FAILED,
                    error_message=str(e)
                )
                response.fail(str(e))
                return response
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取客户端统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        success_rate = (
            self.success_count / self.request_count 
            if self.request_count > 0 else 0.0
        )
        
        return {
            'provider_name': self.provider_name,
            'is_connected': self.is_connected,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': success_rate,
            'last_error': self.last_error,
            'max_concurrent_requests': self.max_concurrent_requests
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_error = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name}, connected={self.is_connected})"
    
    def __repr__(self) -> str:
        return self.__str__()

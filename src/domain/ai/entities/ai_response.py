#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI响应实体

定义AI响应的核心业务逻辑和行为
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..value_objects.ai_quality_metrics import AIQualityMetrics


class AIResponseStatus(Enum):
    """AI响应状态"""
    PENDING = "pending"           # 等待中
    PROCESSING = "processing"     # 处理中
    STREAMING = "streaming"       # 流式输出中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"       # 已取消
    TIMEOUT = "timeout"          # 超时


@dataclass
class AIResponse:
    """
    AI响应实体
    
    封装AI响应的所有信息和业务逻辑
    """
    
    # 基本信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    content: str = ""
    
    # 状态信息
    status: AIResponseStatus = AIResponseStatus.PENDING
    error_message: Optional[str] = None
    
    # 提供商信息
    provider: str = ""
    model: str = ""
    
    # 质量指标
    quality_metrics: AIQualityMetrics = field(default_factory=AIQualityMetrics)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # 流式输出相关
    is_streaming: bool = False
    stream_chunks: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.request_id:
            raise ValueError("响应必须关联一个请求ID")
    
    def update_content(self, content: str) -> None:
        """更新响应内容"""
        self.content = content
        self.updated_at = datetime.now()
        
        # 更新质量指标中的内容指标
        self.quality_metrics.calculate_content_metrics(content)
    
    def append_stream_chunk(self, chunk: str) -> None:
        """添加流式输出块"""
        if not self.is_streaming:
            self.is_streaming = True
            self.status = AIResponseStatus.STREAMING
        
        self.stream_chunks.append(chunk)
        self.content += chunk
        self.updated_at = datetime.now()
        
        # 更新质量指标
        self.quality_metrics.calculate_content_metrics(self.content)
    
    def complete(self, final_content: str = None) -> None:
        """完成响应"""
        if final_content is not None:
            self.content = final_content
            self.quality_metrics.calculate_content_metrics(final_content)
        
        self.status = AIResponseStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = self.completed_at
        self.is_streaming = False
    
    def fail(self, error_message: str) -> None:
        """标记响应失败"""
        self.status = AIResponseStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now()
        self.is_streaming = False
    
    def cancel(self) -> None:
        """取消响应"""
        self.status = AIResponseStatus.CANCELLED
        self.updated_at = datetime.now()
        self.is_streaming = False
    
    def timeout(self) -> None:
        """标记响应超时"""
        self.status = AIResponseStatus.TIMEOUT
        self.error_message = "响应超时"
        self.updated_at = datetime.now()
        self.is_streaming = False
    
    def set_provider_info(self, provider: str, model: str) -> None:
        """设置提供商信息"""
        self.provider = provider
        self.model = model
        self.updated_at = datetime.now()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        if not key:
            raise ValueError("元数据键不能为空")
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def update_quality_metrics(self, **kwargs) -> None:
        """更新质量指标"""
        self.quality_metrics.set_quality_scores(**kwargs)
        self.updated_at = datetime.now()
    
    def set_user_feedback(self, rating: int, feedback: str = None) -> None:
        """设置用户反馈"""
        self.quality_metrics.update_user_feedback(rating, feedback)
        self.updated_at = datetime.now()
    
    @property
    def is_successful(self) -> bool:
        """是否成功"""
        return self.status == AIResponseStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status in [AIResponseStatus.FAILED, AIResponseStatus.TIMEOUT]
    
    @property
    def is_in_progress(self) -> bool:
        """是否正在处理中"""
        return self.status in [AIResponseStatus.PENDING, AIResponseStatus.PROCESSING, AIResponseStatus.STREAMING]
    
    @property
    def duration(self) -> Optional[float]:
        """获取处理时长（秒）"""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        elif self.is_in_progress:
            return (datetime.now() - self.created_at).total_seconds()
        return None
    
    @property
    def content_preview(self) -> str:
        """获取内容预览（前100个字符）"""
        if len(self.content) <= 100:
            return self.content
        return self.content[:100] + "..."
    
    def get_stream_content(self) -> str:
        """获取流式输出的完整内容"""
        return "".join(self.stream_chunks)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'request_id': self.request_id,
            'content': self.content,
            'status': self.status.value,
            'error_message': self.error_message,
            'provider': self.provider,
            'model': self.model,
            'quality_metrics': self.quality_metrics.to_dict(),
            'metadata': self.metadata.copy(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_streaming': self.is_streaming,
            'stream_chunks': self.stream_chunks.copy(),
            'duration': self.duration,
            'content_preview': self.content_preview
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIResponse':
        """从字典创建实例"""
        response = cls(
            id=data.get('id', str(uuid.uuid4())),
            request_id=data.get('request_id', ''),
            content=data.get('content', ''),
            status=AIResponseStatus(data.get('status', AIResponseStatus.PENDING.value)),
            error_message=data.get('error_message'),
            provider=data.get('provider', ''),
            model=data.get('model', ''),
            metadata=data.get('metadata', {}),
            is_streaming=data.get('is_streaming', False),
            stream_chunks=data.get('stream_chunks', [])
        )
        
        # 处理质量指标
        if 'quality_metrics' in data:
            response.quality_metrics = AIQualityMetrics.from_dict(data['quality_metrics'])
        
        # 处理时间戳
        if 'created_at' in data:
            response.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            response.updated_at = datetime.fromisoformat(data['updated_at'])
        if 'completed_at' in data and data['completed_at']:
            response.completed_at = datetime.fromisoformat(data['completed_at'])
            
        return response
    
    def __str__(self) -> str:
        return f"AIResponse(id={self.id[:8]}, status={self.status.value}, provider={self.provider})"
    
    def __repr__(self) -> str:
        return self.__str__()

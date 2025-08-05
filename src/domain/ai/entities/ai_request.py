#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI请求实体

定义AI请求的核心业务逻辑和行为
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ..value_objects.ai_request_type import AIRequestType
from ..value_objects.ai_execution_mode import AIExecutionMode
from ..value_objects.ai_priority import AIPriority


@dataclass
class AIRequest:
    """
    AI请求实体
    
    封装AI请求的所有信息和业务逻辑
    """
    
    # 基本信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str = ""
    context: str = ""
    
    # 请求类型和模式
    request_type: AIRequestType = AIRequestType.TEXT_GENERATION
    execution_mode: AIExecutionMode = AIExecutionMode.MANUAL_INPUT
    priority: AIPriority = AIPriority.NORMAL
    
    # 参数配置
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 状态信息
    is_streaming: bool = False
    is_cancelled: bool = False
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.prompt and not self.context:
            raise ValueError("请求必须包含提示词或上下文")
    
    def update_prompt(self, prompt: str) -> None:
        """更新提示词"""
        if not prompt.strip():
            raise ValueError("提示词不能为空")
        self.prompt = prompt.strip()
        self.updated_at = datetime.now()
    
    def update_context(self, context: str) -> None:
        """更新上下文"""
        self.context = context.strip()
        self.updated_at = datetime.now()
    
    def add_parameter(self, key: str, value: Any) -> None:
        """添加参数"""
        if not key:
            raise ValueError("参数键不能为空")
        self.parameters[key] = value
        self.updated_at = datetime.now()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        if not key:
            raise ValueError("元数据键不能为空")
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def cancel(self) -> None:
        """取消请求"""
        self.is_cancelled = True
        self.updated_at = datetime.now()
    
    def is_valid(self) -> bool:
        """检查请求是否有效"""
        return (
            bool(self.prompt.strip() or self.context.strip()) and
            not self.is_cancelled and
            isinstance(self.request_type, AIRequestType) and
            isinstance(self.execution_mode, AIExecutionMode) and
            isinstance(self.priority, AIPriority)
        )
    
    def get_content_length(self) -> int:
        """获取内容长度"""
        return len(self.prompt) + len(self.context)
    
    def get_estimated_tokens(self) -> int:
        """估算token数量（简单估算）"""
        content = f"{self.prompt} {self.context}"
        # 简单估算：平均4个字符 = 1个token
        return len(content) // 4
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'prompt': self.prompt,
            'context': self.context,
            'request_type': self.request_type.value,
            'execution_mode': self.execution_mode.value,
            'priority': self.priority.value,
            'parameters': self.parameters.copy(),
            'metadata': self.metadata.copy(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_streaming': self.is_streaming,
            'is_cancelled': self.is_cancelled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIRequest':
        """从字典创建实例"""
        request = cls(
            id=data.get('id', str(uuid.uuid4())),
            prompt=data.get('prompt', ''),
            context=data.get('context', ''),
            request_type=AIRequestType(data.get('request_type', AIRequestType.TEXT_GENERATION.value)),
            execution_mode=AIExecutionMode(data.get('execution_mode', AIExecutionMode.MANUAL_INPUT.value)),
            priority=AIPriority(data.get('priority', AIPriority.NORMAL.value)),
            parameters=data.get('parameters', {}),
            metadata=data.get('metadata', {}),
            is_streaming=data.get('is_streaming', False),
            is_cancelled=data.get('is_cancelled', False)
        )
        
        # 处理时间戳
        if 'created_at' in data:
            request.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            request.updated_at = datetime.fromisoformat(data['updated_at'])
            
        return request
    
    def __str__(self) -> str:
        return f"AIRequest(id={self.id[:8]}, type={self.request_type.value}, mode={self.execution_mode.value})"
    
    def __repr__(self) -> str:
        return self.__str__()

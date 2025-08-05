#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI领域模块

提供AI相关的领域模型、实体、值对象和领域服务
遵循DDD设计原则，确保业务逻辑的纯净性和可测试性
"""

# 实体
from .entities.ai_request import AIRequest
from .entities.ai_response import AIResponse, AIResponseStatus

# 值对象
from .value_objects.ai_capability import AICapability
from .value_objects.ai_request_type import AIRequestType
from .value_objects.ai_execution_mode import AIExecutionMode
from .value_objects.ai_quality_metrics import AIQualityMetrics
from .value_objects.ai_priority import AIPriority

__all__ = [
    # 实体
    'AIRequest',
    'AIResponse',
    'AIResponseStatus',

    # 值对象
    'AICapability',
    'AIRequestType',
    'AIExecutionMode',
    'AIQualityMetrics',
    'AIPriority'
]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI领域实体模块

提供AI相关的领域实体
"""

from .ai_request import AIRequest
from .ai_response import AIResponse, AIResponseStatus

__all__ = [
    'AIRequest',
    'AIResponse',
    'AIResponseStatus'
]

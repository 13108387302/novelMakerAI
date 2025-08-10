#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepContextAnalyzer 单例访问器

避免在不同组件中重复初始化重资源（如 jieba）。
"""
from __future__ import annotations
from typing import Optional
from .deep_context_analyzer import DeepContextAnalyzer

_singleton: Optional[DeepContextAnalyzer] = None

def get_deep_context_analyzer() -> DeepContextAnalyzer:
    global _singleton
    if _singleton is None:
        _singleton = DeepContextAnalyzer()
    return _singleton


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI相关领域事件 - 简化版本

只保留核心的AI事件，删除未使用的复杂事件类型。
"""

from dataclasses import dataclass
from typing import Optional
from src.shared.events.event_bus import Event


@dataclass
class AIRequestCompletedEvent(Event):
    """AI请求完成事件"""
    request_id: str = ""
    response_text: str = ""
    processing_time: float = 0.0
    success: bool = True

    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIRequestFailedEvent(Event):
    """AI请求失败事件"""
    request_id: str = ""
    error_message: str = ""
    retry_count: int = 0

    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIConfigurationChangedEvent(Event):
    """AI配置变更事件"""
    setting_key: str = ""
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "settings_service"



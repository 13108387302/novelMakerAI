#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用事件发布工具

提供统一的事件发布功能，减少重复的事件发布代码
"""

import logging
from typing import Any
from src.shared.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    通用事件发布器
    
    提供统一的事件发布功能，包含标准的错误处理和日志记录。
    减少服务类中重复的事件发布代码。
    """
    
    def __init__(self, event_bus: EventBus):
        """
        初始化事件发布器
        
        Args:
            event_bus: 事件总线实例
        """
        self.event_bus = event_bus
    
    async def publish_safe(self, event: Any, operation_name: str) -> bool:
        """
        安全发布事件
        
        提供统一的事件发布逻辑，包含异常处理和日志记录。
        
        Args:
            event: 要发布的事件对象
            operation_name: 操作名称，用于日志记录
            
        Returns:
            bool: 发布成功返回True，失败返回False
        """
        try:
            await self.event_bus.publish_async(event)
            logger.debug(f"{operation_name}事件发布成功: {event.__class__.__name__}")
            return True
        except Exception as e:
            logger.warning(f"发布{operation_name}事件失败: {e}")
            return False
    
    async def publish_multiple_safe(self, events: list, operation_name: str) -> int:
        """
        安全发布多个事件
        
        Args:
            events: 事件列表
            operation_name: 操作名称
            
        Returns:
            int: 成功发布的事件数量
        """
        success_count = 0
        for event in events:
            if await self.publish_safe(event, operation_name):
                success_count += 1
        
        logger.info(f"{operation_name}批量事件发布完成: {success_count}/{len(events)}")
        return success_count

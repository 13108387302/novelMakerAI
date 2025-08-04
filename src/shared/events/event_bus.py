#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件总线系统

实现发布-订阅模式，支持：
- 类型安全的事件处理
- 异步事件处理
- 事件优先级
- 事件过滤
- 错误处理和重试
"""

import asyncio
import logging
import threading
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union
from uuid import uuid4

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Event')


class EventPriority(Enum):
    """
    事件优先级枚举

    定义事件处理的优先级级别，用于事件队列的排序和处理顺序。

    Values:
        LOW: 低优先级，用于非关键的后台事件
        NORMAL: 普通优先级，默认的事件优先级
        HIGH: 高优先级，用于重要的业务事件
        CRITICAL: 关键优先级，用于系统关键事件
    """
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event(ABC):
    """
    事件基类

    所有事件的抽象基类，提供事件的基本属性和行为。
    使用dataclass简化事件定义，自动生成事件ID和时间戳。

    实现方式：
    - 使用dataclass装饰器简化定义
    - 自动生成唯一的事件ID
    - 记录事件创建时间戳
    - 支持事件源标识

    Attributes:
        event_id: 事件唯一标识符，自动生成
        timestamp: 事件创建时间戳，自动生成
        source: 事件源标识，可选
    """
    event_id: str = None
    timestamp: datetime = None
    source: Optional[str] = None

    def __post_init__(self):
        """
        数据类初始化后处理

        自动生成事件ID和时间戳（如果未提供）。
        """
        if self.event_id is None:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class EventSubscription:
    """事件订阅信息"""
    handler: Callable
    event_type: Type[Event]
    priority: EventPriority
    is_async: bool
    filter_func: Optional[Callable[[Event], bool]]
    max_retries: int
    subscriber_ref: Optional[weakref.ref]


class EventHandler(ABC):
    """事件处理器接口"""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """处理事件"""
        pass


class EventBus:
    """
    事件总线

    实现发布-订阅模式的事件总线，支持类型安全的事件处理。
    提供事件的发布、订阅和异步处理功能。

    实现方式：
    - 使用字典存储事件类型到订阅者的映射
    - 支持同步和异步事件处理
    - 使用弱引用避免内存泄漏
    - 提供线程安全的订阅管理
    - 支持事件过滤和优先级处理

    Attributes:
        _subscriptions: 事件订阅映射字典
        _lock: 线程锁，确保订阅操作的线程安全
        _event_queue: 异步事件队列
        _processing: 是否正在处理事件
    """

    def __init__(self):
        """
        初始化事件总线

        创建空的订阅映射和线程锁。
        """
        self._subscriptions: Dict[Type[Event], List[EventSubscription]] = {}
        self._lock = threading.RLock()
        self._is_running = True
        self._event_queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        
        # 启动事件处理任务
        self._start_processing()
    
    def subscribe(
        self,
        event_type: Type[T],
        handler: Union[Callable[[T], None], Callable[[T], asyncio.coroutine]],
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: Optional[Callable[[T], bool]] = None,
        max_retries: int = 3,
        subscriber: Optional[Any] = None
    ) -> str:
        """订阅事件"""
        with self._lock:
            # 检查处理器是否为异步
            is_async = asyncio.iscoroutinefunction(handler)
            
            # 创建弱引用（如果提供了订阅者）
            subscriber_ref = None
            if subscriber is not None:
                subscriber_ref = weakref.ref(subscriber, self._cleanup_subscription)
            
            # 创建订阅信息
            subscription = EventSubscription(
                handler=handler,
                event_type=event_type,
                priority=priority,
                is_async=is_async,
                filter_func=filter_func,
                max_retries=max_retries,
                subscriber_ref=subscriber_ref
            )
            
            # 添加到订阅列表
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            
            self._subscriptions[event_type].append(subscription)
            
            # 按优先级排序
            self._subscriptions[event_type].sort(
                key=lambda s: s.priority.value,
                reverse=True
            )
            
            logger.debug(f"订阅事件 {event_type.__name__}，处理器: {handler}")
            return subscription.handler.__name__
    
    def unsubscribe(
        self,
        event_type: Type[Event],
        handler: Optional[Callable] = None,
        subscriber: Optional[Any] = None
    ) -> None:
        """取消订阅"""
        with self._lock:
            if event_type not in self._subscriptions:
                return
            
            subscriptions = self._subscriptions[event_type]
            
            # 过滤要移除的订阅
            to_remove = []
            for subscription in subscriptions:
                should_remove = False
                
                if handler is not None and subscription.handler == handler:
                    should_remove = True
                elif subscriber is not None and subscription.subscriber_ref is not None:
                    if subscription.subscriber_ref() == subscriber:
                        should_remove = True
                
                if should_remove:
                    to_remove.append(subscription)
            
            # 移除订阅
            for subscription in to_remove:
                subscriptions.remove(subscription)
                logger.debug(f"取消订阅事件 {event_type.__name__}")
            
            # 如果没有订阅者了，移除事件类型
            if not subscriptions:
                del self._subscriptions[event_type]
    
    def publish(self, event: Event) -> None:
        """发布事件（同步）"""
        if not self._is_running:
            return
        
        logger.debug(f"发布事件: {event.__class__.__name__} (ID: {event.event_id})")
        
        # 添加到事件队列
        try:
            asyncio.create_task(self._event_queue.put(event))
        except RuntimeError:
            # 如果没有事件循环，直接处理
            asyncio.run(self._process_event(event))
    
    async def publish_async(self, event: Event) -> None:
        """发布事件（异步）"""
        if not self._is_running:
            return
        
        logger.debug(f"异步发布事件: {event.__class__.__name__} (ID: {event.event_id})")
        await self._event_queue.put(event)
    
    def _start_processing(self) -> None:
        """启动事件处理任务"""
        try:
            loop = asyncio.get_event_loop()
            self._processing_task = loop.create_task(self._process_events())
        except RuntimeError:
            # 没有事件循环，稍后启动
            pass
    
    async def _process_events(self) -> None:
        """处理事件队列"""
        while self._is_running:
            try:
                # 等待事件
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"事件处理错误: {e}")
    
    async def _process_event(self, event: Event) -> None:
        """处理单个事件"""
        event_type = type(event)
        
        with self._lock:
            subscriptions = self._subscriptions.get(event_type, []).copy()
        
        if not subscriptions:
            logger.debug(f"没有找到事件 {event_type.__name__} 的订阅者")
            return
        
        # 处理所有订阅
        for subscription in subscriptions:
            await self._handle_subscription(event, subscription)
    
    async def _handle_subscription(self, event: Event, subscription: EventSubscription) -> None:
        """处理单个订阅"""
        try:
            # 检查订阅者是否还存在
            if subscription.subscriber_ref is not None:
                if subscription.subscriber_ref() is None:
                    # 订阅者已被垃圾回收，移除订阅
                    self._cleanup_subscription(subscription.subscriber_ref)
                    return
            
            # 应用过滤器
            if subscription.filter_func is not None:
                if not subscription.filter_func(event):
                    return
            
            # 执行处理器
            retry_count = 0
            while retry_count <= subscription.max_retries:
                try:
                    if subscription.is_async:
                        await subscription.handler(event)
                    else:
                        subscription.handler(event)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count > subscription.max_retries:
                        logger.error(
                            f"事件处理失败 (重试 {subscription.max_retries} 次): "
                            f"{subscription.handler}, 错误: {e}"
                        )
                        break
                    else:
                        logger.warning(
                            f"事件处理失败，重试 {retry_count}/{subscription.max_retries}: {e}"
                        )
                        await asyncio.sleep(0.1 * retry_count)  # 指数退避
        
        except Exception as e:
            logger.error(f"订阅处理错误: {e}")
    
    def _cleanup_subscription(self, weak_ref: weakref.ref) -> None:
        """清理已失效的订阅"""
        with self._lock:
            for event_type, subscriptions in list(self._subscriptions.items()):
                subscriptions[:] = [
                    s for s in subscriptions
                    if s.subscriber_ref != weak_ref
                ]
                
                if not subscriptions:
                    del self._subscriptions[event_type]
    
    def get_subscription_count(self, event_type: Optional[Type[Event]] = None) -> int:
        """获取订阅数量"""
        with self._lock:
            if event_type is None:
                return sum(len(subs) for subs in self._subscriptions.values())
            else:
                return len(self._subscriptions.get(event_type, []))
    
    def clear_subscriptions(self, event_type: Optional[Type[Event]] = None) -> None:
        """清空订阅"""
        with self._lock:
            if event_type is None:
                self._subscriptions.clear()
            else:
                self._subscriptions.pop(event_type, None)
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._is_running = False
        
        if self._processing_task is not None:
            self._processing_task.cancel()
        
        self.clear_subscriptions()
        logger.info("事件总线已关闭")


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """设置全局事件总线"""
    global _global_event_bus
    _global_event_bus = event_bus

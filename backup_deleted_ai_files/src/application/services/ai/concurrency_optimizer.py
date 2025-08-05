#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI并发处理优化器

优化AI请求的并发处理，提供智能调度和负载均衡
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque
import heapq

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.shared.utils.logger import get_logger
from src.shared.events.event_bus import EventBus
from src.domain.events.ai_events import AIRequestQueuedEvent, AIRequestStartedEvent
from src.application.services.ai.core_abstractions import AIRequest, AIRequestPriority

logger = get_logger(__name__)


class QueueStrategy(Enum):
    """队列策略"""
    FIFO = "fifo"  # 先进先出
    PRIORITY = "priority"  # 优先级队列
    ROUND_ROBIN = "round_robin"  # 轮询
    LOAD_BALANCED = "load_balanced"  # 负载均衡


@dataclass
class QueuedRequest:
    """排队的请求"""
    request: AIRequest
    priority: AIRequestPriority
    queue_time: datetime = field(default_factory=datetime.now)
    estimated_processing_time: float = 0.0
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        # 优先级越高，数值越小，排序越靠前
        return self.priority.value < other.priority.value


@dataclass
class ProviderLoad:
    """提供商负载信息"""
    provider_name: str
    active_requests: int = 0
    max_concurrent: int = 5
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    last_request_time: Optional[datetime] = None
    
    @property
    def load_factor(self) -> float:
        """负载因子 (0-1)"""
        return self.active_requests / self.max_concurrent
    
    @property
    def efficiency_score(self) -> float:
        """效率评分"""
        # 基于成功率和响应时间计算效率
        time_penalty = min(self.avg_response_time / 10.0, 0.5)
        return self.success_rate * (1.0 - time_penalty)


class AIConcurrencyOptimizer(QObject):
    """
    AI并发处理优化器
    
    功能：
    - 智能请求调度
    - 负载均衡
    - 优先级处理
    - 并发控制
    - 性能优化
    """
    
    # 信号
    request_queued = pyqtSignal(str, int)  # request_id, queue_position
    request_dispatched = pyqtSignal(str, str)  # request_id, provider
    queue_status_changed = pyqtSignal(dict)  # queue_stats
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        
        self.event_bus = event_bus
        
        # 配置
        self.max_global_concurrent = 10
        self.max_provider_concurrent = 5
        self.queue_strategy = QueueStrategy.LOAD_BALANCED
        self.enable_adaptive_scheduling = True
        
        # 请求队列
        self._request_queue: List[QueuedRequest] = []
        self._priority_queue: List[QueuedRequest] = []
        
        # 提供商管理
        self._providers: Dict[str, ProviderLoad] = {}
        self._provider_round_robin_index = 0
        
        # 活跃请求跟踪
        self._active_requests: Dict[str, Tuple[str, datetime]] = {}  # request_id -> (provider, start_time)
        
        # 统计信息
        self._total_queued = 0
        self._total_processed = 0
        self._total_wait_time = 0.0
        
        # 调度器
        self._scheduler_timer = QTimer()
        self._scheduler_timer.timeout.connect(self._process_queue)
        self._scheduler_timer.start(100)  # 每100ms检查一次队列
        
        # 监控定时器
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._update_queue_status)
        self._monitor_timer.start(1000)  # 每秒更新状态
        
        logger.info("AI并发优化器初始化完成")
    
    def register_provider(self, provider_name: str, max_concurrent: int = 5):
        """注册AI提供商"""
        self._providers[provider_name] = ProviderLoad(
            provider_name=provider_name,
            max_concurrent=max_concurrent
        )
        logger.info(f"注册AI提供商: {provider_name} (最大并发: {max_concurrent})")
    
    def queue_request(
        self, 
        request: AIRequest, 
        priority: AIRequestPriority = AIRequestPriority.NORMAL,
        callback: Optional[Callable] = None
    ) -> str:
        """将请求加入队列"""
        queued_request = QueuedRequest(
            request=request,
            priority=priority,
            callback=callback
        )
        
        # 根据策略选择队列
        if self.queue_strategy == QueueStrategy.PRIORITY:
            heapq.heappush(self._priority_queue, queued_request)
        else:
            self._request_queue.append(queued_request)
        
        self._total_queued += 1
        
        # 发送排队事件
        queue_position = len(self._request_queue) + len(self._priority_queue)
        self.request_queued.emit(request.id, queue_position)
        
        queue_event = AIRequestQueuedEvent(
            request_id=request.id,
            queue_position=queue_position,
            estimated_wait_time=self._estimate_wait_time(),
            priority=priority.name.lower()
        )
        self.event_bus.publish(queue_event)
        
        logger.debug(f"请求已排队: {request.id} (优先级: {priority.name})")
        return request.id
    
    def _process_queue(self):
        """处理队列中的请求"""
        if not self._can_process_more_requests():
            return
        
        # 获取下一个请求
        next_request = self._get_next_request()
        if not next_request:
            return
        
        # 选择最佳提供商
        provider = self._select_best_provider()
        if not provider:
            # 没有可用的提供商，将请求放回队列
            if self.queue_strategy == QueueStrategy.PRIORITY:
                heapq.heappush(self._priority_queue, next_request)
            else:
                self._request_queue.insert(0, next_request)
            return
        
        # 分发请求
        self._dispatch_request(next_request, provider)
    
    def _can_process_more_requests(self) -> bool:
        """检查是否可以处理更多请求"""
        return len(self._active_requests) < self.max_global_concurrent
    
    def _get_next_request(self) -> Optional[QueuedRequest]:
        """获取下一个要处理的请求"""
        if self.queue_strategy == QueueStrategy.PRIORITY and self._priority_queue:
            return heapq.heappop(self._priority_queue)
        elif self._request_queue:
            return self._request_queue.pop(0)
        return None
    
    def _select_best_provider(self) -> Optional[str]:
        """选择最佳提供商"""
        available_providers = [
            name for name, load in self._providers.items()
            if load.active_requests < load.max_concurrent
        ]
        
        if not available_providers:
            return None
        
        if self.queue_strategy == QueueStrategy.ROUND_ROBIN:
            return self._select_round_robin_provider(available_providers)
        elif self.queue_strategy == QueueStrategy.LOAD_BALANCED:
            return self._select_load_balanced_provider(available_providers)
        else:
            return available_providers[0]
    
    def _select_round_robin_provider(self, available_providers: List[str]) -> str:
        """轮询选择提供商"""
        if not available_providers:
            return None
        
        provider = available_providers[self._provider_round_robin_index % len(available_providers)]
        self._provider_round_robin_index += 1
        return provider
    
    def _select_load_balanced_provider(self, available_providers: List[str]) -> str:
        """负载均衡选择提供商"""
        if not available_providers:
            return None
        
        # 计算每个提供商的综合评分
        best_provider = None
        best_score = -1
        
        for provider_name in available_providers:
            load = self._providers[provider_name]
            
            # 综合评分 = 效率评分 * (1 - 负载因子)
            score = load.efficiency_score * (1.0 - load.load_factor)
            
            if score > best_score:
                best_score = score
                best_provider = provider_name
        
        return best_provider
    
    def _dispatch_request(self, queued_request: QueuedRequest, provider: str):
        """分发请求到指定提供商"""
        request = queued_request.request
        
        # 更新提供商负载
        self._providers[provider].active_requests += 1
        self._providers[provider].last_request_time = datetime.now()
        
        # 记录活跃请求
        self._active_requests[request.id] = (provider, datetime.now())
        
        # 计算等待时间
        wait_time = (datetime.now() - queued_request.queue_time).total_seconds()
        self._total_wait_time += wait_time
        self._total_processed += 1
        
        # 发送分发信号和事件
        self.request_dispatched.emit(request.id, provider)
        
        start_event = AIRequestStartedEvent(
            request_id=request.id,
            request_type=request.request_type.value,
            provider=provider
        )
        self.event_bus.publish(start_event)
        
        # 执行回调
        if queued_request.callback:
            try:
                queued_request.callback(request, provider)
            except Exception as e:
                logger.error(f"执行请求回调失败: {e}")
        
        logger.debug(f"请求已分发: {request.id} -> {provider} (等待时间: {wait_time:.2f}秒)")
    
    def complete_request(self, request_id: str, success: bool = True, response_time: float = 0.0):
        """标记请求完成"""
        if request_id not in self._active_requests:
            return
        
        provider, start_time = self._active_requests.pop(request_id)
        
        # 更新提供商负载
        if provider in self._providers:
            load = self._providers[provider]
            load.active_requests = max(0, load.active_requests - 1)
            
            # 更新统计信息
            if response_time > 0:
                # 指数移动平均
                alpha = 0.3
                if load.avg_response_time == 0:
                    load.avg_response_time = response_time
                else:
                    load.avg_response_time = alpha * response_time + (1 - alpha) * load.avg_response_time
            
            # 更新成功率
            if hasattr(load, '_request_count'):
                load._request_count += 1
                load._success_count = getattr(load, '_success_count', 0) + (1 if success else 0)
                load.success_rate = load._success_count / load._request_count
            else:
                load._request_count = 1
                load._success_count = 1 if success else 0
                load.success_rate = load._success_count
        
        logger.debug(f"请求完成: {request_id} (提供商: {provider}, 成功: {success})")
    
    def _estimate_wait_time(self) -> float:
        """估算等待时间"""
        if not self._providers:
            return 0.0
        
        # 基于当前队列长度和平均处理时间估算
        queue_length = len(self._request_queue) + len(self._priority_queue)
        if queue_length == 0:
            return 0.0
        
        # 计算平均处理时间
        avg_processing_time = sum(
            load.avg_response_time for load in self._providers.values()
        ) / len(self._providers)
        
        # 计算可用容量
        available_capacity = sum(
            max(0, load.max_concurrent - load.active_requests)
            for load in self._providers.values()
        )
        
        if available_capacity == 0:
            return queue_length * avg_processing_time
        
        return (queue_length / available_capacity) * avg_processing_time
    
    def _update_queue_status(self):
        """更新队列状态"""
        status = {
            'queue_length': len(self._request_queue) + len(self._priority_queue),
            'active_requests': len(self._active_requests),
            'total_queued': self._total_queued,
            'total_processed': self._total_processed,
            'avg_wait_time': self._total_wait_time / max(self._total_processed, 1),
            'providers': {
                name: {
                    'active_requests': load.active_requests,
                    'max_concurrent': load.max_concurrent,
                    'load_factor': load.load_factor,
                    'efficiency_score': load.efficiency_score,
                    'avg_response_time': load.avg_response_time
                }
                for name, load in self._providers.items()
            }
        }
        
        self.queue_status_changed.emit(status)
    
    # 公共接口方法
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'queue_length': len(self._request_queue) + len(self._priority_queue),
            'active_requests': len(self._active_requests),
            'providers': dict(self._providers)
        }
    
    def set_max_concurrent(self, global_max: int, provider_max: Dict[str, int] = None):
        """设置最大并发数"""
        self.max_global_concurrent = global_max
        
        if provider_max:
            for provider, max_concurrent in provider_max.items():
                if provider in self._providers:
                    self._providers[provider].max_concurrent = max_concurrent
        
        logger.info(f"并发限制已更新: 全局={global_max}")
    
    def clear_queue(self):
        """清空队列"""
        self._request_queue.clear()
        self._priority_queue.clear()
        logger.info("请求队列已清空")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_queued': self._total_queued,
            'total_processed': self._total_processed,
            'avg_wait_time': self._total_wait_time / max(self._total_processed, 1),
            'current_queue_length': len(self._request_queue) + len(self._priority_queue),
            'active_requests': len(self._active_requests)
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI性能监控器

监控AI服务的性能指标，提供实时统计和优化建议
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.shared.utils.logger import get_logger
from src.shared.events.event_bus import EventBus
from src.domain.events.ai_events import (
    AIPerformanceMetricsEvent, AIProviderHealthChangedEvent,
    AIRequestStartedEvent, AIRequestCompletedEvent, AIRequestFailedEvent
)

logger = get_logger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class ProviderHealth:
    """提供商健康状态"""
    provider_name: str
    is_healthy: bool = True
    health_score: float = 1.0
    error_rate: float = 0.0
    avg_response_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_error: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_stats(self, success: bool, response_time: float, error: Optional[str] = None):
        """更新统计信息"""
        self.total_requests += 1
        self.last_updated = datetime.now()
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.last_error = error
        
        # 更新错误率
        self.error_rate = self.failed_requests / self.total_requests
        
        # 更新平均响应时间（指数移动平均）
        alpha = 0.3
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = alpha * response_time + (1 - alpha) * self.avg_response_time
        
        # 更新健康评分
        self._calculate_health_score()
    
    def _calculate_health_score(self):
        """计算健康评分"""
        # 基于错误率和响应时间计算健康评分
        error_penalty = min(self.error_rate * 2, 1.0)  # 错误率惩罚
        response_penalty = min(self.avg_response_time / 10.0, 0.5)  # 响应时间惩罚
        
        self.health_score = max(0.0, 1.0 - error_penalty - response_penalty)
        self.is_healthy = self.health_score >= 0.7


class AIPerformanceMonitor(QObject):
    """
    AI性能监控器
    
    监控AI服务的各项性能指标，包括：
    - 请求响应时间
    - 成功率和错误率
    - 提供商健康状态
    - 资源使用情况
    - 并发处理能力
    """
    
    # 性能指标信号
    metrics_updated = pyqtSignal(dict)
    health_changed = pyqtSignal(str, bool)  # provider, is_healthy
    alert_triggered = pyqtSignal(str, str, str)  # level, title, message
    
    def __init__(self, event_bus: EventBus, parent=None):
        super().__init__(parent)
        
        self.event_bus = event_bus
        
        # 性能指标存储
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._provider_health: Dict[str, ProviderHealth] = {}
        
        # 实时统计
        self._active_requests: Dict[str, float] = {}  # request_id -> start_time
        self._request_history: deque = deque(maxlen=10000)
        
        # 监控配置
        self.monitoring_interval = 30  # 秒
        self.alert_thresholds = {
            'error_rate': 0.1,  # 10%
            'avg_response_time': 10.0,  # 10秒
            'health_score': 0.7
        }
        
        # 定时器
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._collect_metrics)
        self._monitor_timer.start(self.monitoring_interval * 1000)
        
        # 事件订阅
        self._setup_event_subscriptions()
        
        logger.info("AI性能监控器初始化完成")
    
    def _setup_event_subscriptions(self):
        """设置事件订阅"""
        try:
            # 订阅AI请求事件
            self.event_bus.subscribe(
                AIRequestStartedEvent,
                self._on_request_started,
                subscriber=self
            )
            
            self.event_bus.subscribe(
                AIRequestCompletedEvent,
                self._on_request_completed,
                subscriber=self
            )
            
            self.event_bus.subscribe(
                AIRequestFailedEvent,
                self._on_request_failed,
                subscriber=self
            )
            
            logger.debug("性能监控事件订阅设置完成")
            
        except Exception as e:
            logger.error(f"设置性能监控事件订阅失败: {e}")
    
    def _on_request_started(self, event: AIRequestStartedEvent):
        """处理请求开始事件"""
        self._active_requests[event.request_id] = time.time()
        
        # 记录指标
        self._record_metric("ai.requests.started", 1, MetricType.COUNTER, {
            'provider': event.provider or 'unknown',
            'request_type': event.request_type
        })
    
    def _on_request_completed(self, event: AIRequestCompletedEvent):
        """处理请求完成事件"""
        start_time = self._active_requests.pop(event.request_id, None)
        if start_time:
            response_time = time.time() - start_time
            
            # 更新提供商健康状态
            if event.provider:
                self._update_provider_health(event.provider, True, response_time)
            
            # 记录指标
            self._record_metric("ai.requests.completed", 1, MetricType.COUNTER, {
                'provider': event.provider or 'unknown',
                'request_type': event.request_type
            })
            
            self._record_metric("ai.response_time", response_time, MetricType.TIMER, {
                'provider': event.provider or 'unknown'
            })
            
            # 记录请求历史
            self._request_history.append({
                'request_id': event.request_id,
                'success': True,
                'response_time': response_time,
                'provider': event.provider,
                'timestamp': datetime.now()
            })
    
    def _on_request_failed(self, event: AIRequestFailedEvent):
        """处理请求失败事件"""
        start_time = self._active_requests.pop(event.request_id, None)
        response_time = time.time() - start_time if start_time else 0
        
        # 从错误消息中提取提供商信息
        provider = self._extract_provider_from_error(event.error_message)
        
        # 更新提供商健康状态
        if provider:
            self._update_provider_health(provider, False, response_time, event.error_message)
        
        # 记录指标
        self._record_metric("ai.requests.failed", 1, MetricType.COUNTER, {
            'provider': provider or 'unknown',
            'request_type': event.request_type,
            'error_code': event.error_code or 'unknown'
        })
        
        # 记录请求历史
        self._request_history.append({
            'request_id': event.request_id,
            'success': False,
            'response_time': response_time,
            'provider': provider,
            'error': event.error_message,
            'timestamp': datetime.now()
        })
    
    def _update_provider_health(self, provider: str, success: bool, response_time: float, error: Optional[str] = None):
        """更新提供商健康状态"""
        if provider not in self._provider_health:
            self._provider_health[provider] = ProviderHealth(provider)
        
        health = self._provider_health[provider]
        old_health = health.is_healthy
        
        health.update_stats(success, response_time, error)
        
        # 如果健康状态发生变化，发送事件和信号
        if old_health != health.is_healthy:
            self.health_changed.emit(provider, health.is_healthy)
            
            # 发送健康状态变化事件
            health_event = AIProviderHealthChangedEvent(
                provider_name=provider,
                is_healthy=health.is_healthy,
                health_score=health.health_score,
                error_rate=health.error_rate,
                avg_response_time=health.avg_response_time,
                last_error=health.last_error
            )
            self.event_bus.publish(health_event)
            
            # 触发警报
            if not health.is_healthy:
                self.alert_triggered.emit(
                    "warning",
                    f"提供商 {provider} 健康状态异常",
                    f"健康评分: {health.health_score:.2f}, 错误率: {health.error_rate:.2%}"
                )
    
    def _record_metric(self, name: str, value: float, metric_type: MetricType, tags: Dict[str, str] = None):
        """记录性能指标"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {}
        )
        
        self._metrics[name].append(metric)
    
    def _collect_metrics(self):
        """收集性能指标"""
        try:
            # 收集当前活跃请求数
            active_count = len(self._active_requests)
            self._record_metric("ai.requests.active", active_count, MetricType.GAUGE)
            
            # 收集最近时间窗口的统计
            now = datetime.now()
            recent_requests = [
                req for req in self._request_history
                if (now - req['timestamp']).seconds < 300  # 最近5分钟
            ]
            
            if recent_requests:
                success_rate = sum(1 for req in recent_requests if req['success']) / len(recent_requests)
                avg_response_time = sum(req['response_time'] for req in recent_requests) / len(recent_requests)
                
                self._record_metric("ai.success_rate", success_rate, MetricType.GAUGE)
                self._record_metric("ai.avg_response_time", avg_response_time, MetricType.GAUGE)
            
            # 发送性能指标更新信号
            metrics_summary = self._get_metrics_summary()
            self.metrics_updated.emit(metrics_summary)
            
            # 发送性能指标事件
            metrics_event = AIPerformanceMetricsEvent(
                component_id="ai_performance_monitor",
                metrics=metrics_summary,
                time_window="5m"
            )
            self.event_bus.publish(metrics_event)
            
        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")

    def _get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {
            'active_requests': len(self._active_requests),
            'total_requests': len(self._request_history),
            'providers': {}
        }

        # 提供商健康状态
        for provider, health in self._provider_health.items():
            summary['providers'][provider] = {
                'is_healthy': health.is_healthy,
                'health_score': health.health_score,
                'error_rate': health.error_rate,
                'avg_response_time': health.avg_response_time,
                'total_requests': health.total_requests
            }

        # 最近指标
        now = datetime.now()
        recent_requests = [
            req for req in self._request_history
            if (now - req['timestamp']).seconds < 300
        ]

        if recent_requests:
            summary['recent_5m'] = {
                'total_requests': len(recent_requests),
                'success_rate': sum(1 for req in recent_requests if req['success']) / len(recent_requests),
                'avg_response_time': sum(req['response_time'] for req in recent_requests) / len(recent_requests)
            }

        return summary

    def _extract_provider_from_error(self, error_message: str) -> Optional[str]:
        """从错误消息中提取提供商信息"""
        error_lower = error_message.lower()
        if 'openai' in error_lower:
            return 'openai'
        elif 'deepseek' in error_lower:
            return 'deepseek'
        return None

    # 公共接口方法

    def get_provider_health(self, provider: str) -> Optional[ProviderHealth]:
        """获取提供商健康状态"""
        return self._provider_health.get(provider)

    def get_all_provider_health(self) -> Dict[str, ProviderHealth]:
        """获取所有提供商健康状态"""
        return self._provider_health.copy()

    def get_metrics(self, metric_name: str, time_window: int = 300) -> List[PerformanceMetric]:
        """获取指定时间窗口内的指标"""
        if metric_name not in self._metrics:
            return []

        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        return [
            metric for metric in self._metrics[metric_name]
            if metric.timestamp >= cutoff_time
        ]

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return self._get_metrics_summary()

    def reset_metrics(self):
        """重置所有指标"""
        self._metrics.clear()
        self._provider_health.clear()
        self._active_requests.clear()
        self._request_history.clear()
        logger.info("性能监控指标已重置")

    def set_alert_threshold(self, metric: str, threshold: float):
        """设置警报阈值"""
        self.alert_thresholds[metric] = threshold
        logger.info(f"警报阈值已更新: {metric} = {threshold}")

    def check_alerts(self):
        """检查警报条件"""
        for provider, health in self._provider_health.items():
            # 检查错误率
            if health.error_rate > self.alert_thresholds.get('error_rate', 0.1):
                self.alert_triggered.emit(
                    "error",
                    f"提供商 {provider} 错误率过高",
                    f"当前错误率: {health.error_rate:.2%}"
                )

            # 检查响应时间
            if health.avg_response_time > self.alert_thresholds.get('avg_response_time', 10.0):
                self.alert_triggered.emit(
                    "warning",
                    f"提供商 {provider} 响应时间过长",
                    f"平均响应时间: {health.avg_response_time:.2f}秒"
                )

            # 检查健康评分
            if health.health_score < self.alert_thresholds.get('health_score', 0.7):
                self.alert_triggered.emit(
                    "warning",
                    f"提供商 {provider} 健康评分过低",
                    f"健康评分: {health.health_score:.2f}"
                )


# 全局性能监控器实例
_global_performance_monitor: Optional[AIPerformanceMonitor] = None


def get_performance_monitor() -> Optional[AIPerformanceMonitor]:
    """获取全局性能监控器"""
    return _global_performance_monitor


def initialize_performance_monitor(event_bus: EventBus) -> AIPerformanceMonitor:
    """初始化全局性能监控器"""
    global _global_performance_monitor
    _global_performance_monitor = AIPerformanceMonitor(event_bus)
    logger.info("全局AI性能监控器已初始化")
    return _global_performance_monitor


def cleanup_performance_monitor():
    """清理全局性能监控器"""
    global _global_performance_monitor
    if _global_performance_monitor:
        _global_performance_monitor.reset_metrics()
        _global_performance_monitor = None
        logger.info("全局AI性能监控器已清理")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一性能监控和缓存管理

整合performance_optimizer和cache_manager的功能，提供统一的性能优化接口。
"""

import time
import threading
import asyncio
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, Union
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import pickle
import logging

from .base_utils import BaseUtility, UtilResult, timed_operation

logger = logging.getLogger(__name__)

# 类型变量
K = TypeVar('K')
V = TypeVar('V')

# 性能常量
DEFAULT_CACHE_SIZE = 1000
DEFAULT_TTL = 3600  # 1小时
DEFAULT_CLEANUP_THRESHOLD = 0.8
DEFAULT_MAX_MEMORY_MB = 100


@dataclass
class CacheEntry(Generic[V]):
    """缓存条目"""
    value: V
    timestamp: float
    ttl: float
    access_count: int = 0
    size: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def touch(self) -> None:
        """更新访问时间和计数"""
        self.access_count += 1


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation_name: str
    duration: float
    timestamp: float
    success: bool
    memory_usage: Optional[int] = None
    cpu_usage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'operation': self.operation_name,
            'duration': self.duration,
            'timestamp': self.timestamp,
            'success': self.success,
            'memory_usage': self.memory_usage,
            'cpu_usage': self.cpu_usage
        }


class UnifiedPerformanceManager(BaseUtility):
    """
    统一性能管理器
    
    整合缓存管理和性能监控功能，提供统一的接口。
    """
    
    def __init__(
        self,
        max_cache_size: int = DEFAULT_CACHE_SIZE,
        default_ttl: float = DEFAULT_TTL,
        max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
        enable_metrics: bool = True
    ):
        """
        初始化性能管理器
        
        Args:
            max_cache_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            max_memory_mb: 最大内存使用（MB）
            enable_metrics: 是否启用性能指标收集
        """
        super().__init__("UnifiedPerformanceManager")
        
        # 缓存配置
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # 缓存存储
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: deque = deque()
        self._lock = threading.RLock()
        
        # 性能指标
        self.enable_metrics = enable_metrics
        self._metrics: deque = deque(maxlen=10000)  # 保留最近10000条记录
        self._metrics_lock = threading.RLock()
        
        # 统计信息
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_usage': 0
        }
        
        self.logger.info(f"性能管理器初始化完成: cache_size={max_cache_size}, ttl={default_ttl}")
    
    @timed_operation("cache_get")
    def cache_get(self, key: str) -> UtilResult[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._cache_stats['misses'] += 1
                return UtilResult.failure_result(f"缓存键不存在: {key}")
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._cache_stats['misses'] += 1
                return UtilResult.failure_result(f"缓存已过期: {key}")
            
            # 更新访问信息
            entry.touch()
            self._access_order.remove(key)
            self._access_order.append(key)
            self._cache_stats['hits'] += 1
            
            return UtilResult.success_result(entry.value)
    
    @timed_operation("cache_set")
    def cache_set(self, key: str, value: Any, ttl: Optional[float] = None) -> UtilResult[bool]:
        """设置缓存值"""
        with self._lock:
            # 计算值的大小
            try:
                size = len(pickle.dumps(value))
            except Exception:
                size = 1024  # 默认大小
            
            # 检查是否需要清理
            if len(self._cache) >= self.max_cache_size:
                self._evict_lru()
            
            # 创建缓存条目
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl,
                size=size
            )
            
            # 如果键已存在，从访问顺序中移除
            if key in self._cache:
                self._access_order.remove(key)
            
            self._cache[key] = entry
            self._access_order.append(key)
            self._update_memory_usage()
            
            return UtilResult.success_result(True)
    
    @timed_operation("cache_delete")
    def cache_delete(self, key: str) -> UtilResult[bool]:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._update_memory_usage()
                return UtilResult.success_result(True)
            return UtilResult.failure_result(f"缓存键不存在: {key}")
    
    def _evict_lru(self) -> None:
        """清理最近最少使用的缓存条目"""
        if not self._access_order:
            return
        
        # 计算需要清理的数量
        cleanup_count = max(1, int(self.max_cache_size * (1 - DEFAULT_CLEANUP_THRESHOLD)))
        
        for _ in range(cleanup_count):
            if self._access_order:
                oldest_key = self._access_order.popleft()
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
                    self._cache_stats['evictions'] += 1
        
        self._update_memory_usage()
        self.logger.debug(f"LRU清理完成，移除了 {cleanup_count} 个条目")
    
    def _update_memory_usage(self) -> None:
        """更新内存使用统计"""
        total_size = sum(entry.size for entry in self._cache.values())
        self._cache_stats['memory_usage'] = total_size
    
    @timed_operation("record_metric")
    def record_metric(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        memory_usage: Optional[int] = None,
        cpu_usage: Optional[float] = None
    ) -> UtilResult[bool]:
        """记录性能指标"""
        if not self.enable_metrics:
            return UtilResult.success_result(True)
        
        metric = PerformanceMetrics(
            operation_name=operation_name,
            duration=duration,
            timestamp=time.time(),
            success=success,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )
        
        with self._metrics_lock:
            self._metrics.append(metric)
        
        return UtilResult.success_result(True)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            stats = self._cache_stats.copy()
            stats['size'] = len(self._cache)
            
            total_requests = stats['hits'] + stats['misses']
            if total_requests > 0:
                stats['hit_rate'] = stats['hits'] / total_requests
            else:
                stats['hit_rate'] = 0.0
            
            stats['memory_usage_mb'] = stats['memory_usage'] / (1024 * 1024)
            return stats
    
    def get_performance_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._metrics_lock:
            if operation_name:
                metrics = [m for m in self._metrics if m.operation_name == operation_name]
            else:
                metrics = list(self._metrics)
        
        if not metrics:
            return {}
        
        durations = [m.duration for m in metrics]
        success_count = sum(1 for m in metrics if m.success)
        
        return {
            'operation': operation_name or 'all',
            'total_operations': len(metrics),
            'success_count': success_count,
            'success_rate': success_count / len(metrics),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations)
        }
    
    @timed_operation("cleanup_expired")
    def cleanup_expired(self) -> UtilResult[int]:
        """清理过期的缓存条目"""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            self._update_memory_usage()
            
            return UtilResult.success_result(len(expired_keys))
    
    def validate_config(self) -> UtilResult[bool]:
        """验证配置"""
        if self.max_cache_size <= 0:
            return UtilResult.failure_result("缓存大小必须大于0")
        
        if self.default_ttl < 0:
            return UtilResult.failure_result("TTL不能为负数")
        
        return UtilResult.success_result(True)
    
    def cleanup(self) -> UtilResult[bool]:
        """清理资源"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
        
        with self._metrics_lock:
            self._metrics.clear()
        
        return UtilResult.success_result(True)


# 性能监控装饰器
def performance_monitor(operation_name: str = ""):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 记录成功的性能指标
                manager = get_performance_manager()
                if manager:
                    manager.record_metric(op_name, duration, True)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # 记录失败的性能指标
                manager = get_performance_manager()
                if manager:
                    manager.record_metric(op_name, duration, False)
                
                raise e
        
        return wrapper
    return decorator


# 全局性能管理器实例
_global_performance_manager: Optional[UnifiedPerformanceManager] = None


def get_performance_manager() -> Optional[UnifiedPerformanceManager]:
    """获取全局性能管理器"""
    global _global_performance_manager
    if _global_performance_manager is None:
        _global_performance_manager = UnifiedPerformanceManager()
    return _global_performance_manager


def set_performance_manager(manager: UnifiedPerformanceManager) -> None:
    """设置全局性能管理器"""
    global _global_performance_manager
    _global_performance_manager = manager

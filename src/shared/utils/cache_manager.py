#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一缓存管理器

提供高性能的缓存管理功能，支持多种缓存策略和自动清理机制。
"""

import time
import threading
import weakref
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import pickle

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheManager:
    """
    统一缓存管理器
    
    提供高性能的内存缓存功能，支持TTL、LRU、大小限制等多种策略。
    线程安全，支持自动清理和统计功能。
    
    Features:
    - TTL (Time To Live) 支持
    - LRU (Least Recently Used) 淘汰策略
    - 内存大小限制
    - 线程安全
    - 自动清理
    - 缓存统计
    - 持久化支持
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = 3600,  # 1小时
        max_memory_mb: int = 100,
        cleanup_interval: float = 300,  # 5分钟
        enable_persistence: bool = False,
        persistence_path: Optional[Path] = None
    ):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            max_memory_mb: 最大内存使用（MB）
            cleanup_interval: 清理间隔（秒）
            enable_persistence: 是否启用持久化
            persistence_path: 持久化文件路径
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cleanup_interval = cleanup_interval
        self._enable_persistence = enable_persistence
        self._persistence_path = persistence_path
        
        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanups': 0,
            'memory_usage': 0
        }
        
        # 启动清理线程
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()
        
        # 加载持久化数据
        if self._enable_persistence:
            self._load_from_disk()

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return default
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                return default
            
            entry.touch()
            self._stats['hits'] += 1
            return entry.value

    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[float] = None,
        force: bool = False
    ) -> bool:
        """设置缓存值"""
        with self._lock:
            # 计算值的大小
            try:
                size = len(pickle.dumps(value))
            except:
                size = 1024  # 默认大小

            # 检查内存限制
            if not force and self._would_exceed_memory(size):
                self._evict_lru()
            
            # 检查大小限制
            if not force and len(self._cache) >= self._max_size:
                self._evict_lru()
            
            # 创建缓存条目
            entry = CacheEntry(
                value=value,
                ttl=ttl or self._default_ttl,
                size=size
            )
            
            self._cache[key] = entry
            self._update_memory_usage()
            return True

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._update_memory_usage()
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._stats['memory_usage'] = 0

    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[key]
                return False
            return True

    def get_or_set(
        self, 
        key: str, 
        factory: Callable[[], T], 
        ttl: Optional[float] = None
    ) -> T:
        """获取或设置缓存值"""
        value = self.get(key)
        if value is not None:
            return value
        
        # 生成新值
        new_value = factory()
        self.set(key, new_value, ttl)
        return new_value

    def _would_exceed_memory(self, additional_size: int) -> bool:
        """检查是否会超出内存限制"""
        return self._stats['memory_usage'] + additional_size > self._max_memory_bytes

    def _evict_lru(self) -> None:
        """淘汰最近最少使用的条目"""
        if not self._cache:
            return
        
        # 找到最近最少使用的条目
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self._stats['evictions'] += 1
        self._update_memory_usage()

    def _update_memory_usage(self) -> None:
        """更新内存使用统计"""
        total_size = sum(entry.size for entry in self._cache.values())
        self._stats['memory_usage'] = total_size

    def _cleanup_expired(self) -> None:
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self._stats['cleanups'] += 1
                self._update_memory_usage()
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")

    def _start_cleanup_timer(self) -> None:
        """启动清理定时器"""
        def cleanup_and_reschedule():
            try:
                self._cleanup_expired()
                if self._enable_persistence:
                    self._save_to_disk()
            except Exception as e:
                logger.error(f"缓存清理失败: {e}")
            finally:
                # 重新调度
                self._start_cleanup_timer()
        
        self._cleanup_timer = threading.Timer(self._cleanup_interval, cleanup_and_reschedule)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def _save_to_disk(self) -> None:
        """保存到磁盘"""
        if not self._persistence_path:
            return
        
        try:
            # 只保存非过期的条目
            valid_cache = {
                key: {
                    'value': entry.value,
                    'created_at': entry.created_at,
                    'ttl': entry.ttl
                }
                for key, entry in self._cache.items()
                if not entry.is_expired()
            }
            
            with open(self._persistence_path, 'w', encoding='utf-8') as f:
                json.dump(valid_cache, f, default=str)
                
        except Exception as e:
            logger.error(f"保存缓存到磁盘失败: {e}")

    def _load_from_disk(self) -> None:
        """从磁盘加载"""
        if not self._persistence_path or not self._persistence_path.exists():
            return
        
        try:
            with open(self._persistence_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            current_time = time.time()
            for key, item in data.items():
                # 检查是否过期
                if item.get('ttl') and current_time - item['created_at'] > item['ttl']:
                    continue
                
                entry = CacheEntry(
                    value=item['value'],
                    created_at=item['created_at'],
                    ttl=item.get('ttl')
                )
                self._cache[key] = entry
            
            self._update_memory_usage()
            logger.info(f"从磁盘加载了 {len(self._cache)} 个缓存条目")
            
        except Exception as e:
            logger.error(f"从磁盘加载缓存失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            hit_rate = 0
            total_requests = self._stats['hits'] + self._stats['misses']
            if total_requests > 0:
                hit_rate = self._stats['hits'] / total_requests
            
            return {
                **self._stats,
                'size': len(self._cache),
                'hit_rate': hit_rate,
                'memory_usage_mb': self._stats['memory_usage'] / (1024 * 1024)
            }

    def shutdown(self) -> None:
        """关闭缓存管理器"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
        
        if self._enable_persistence:
            self._save_to_disk()


# 全局缓存管理器实例
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def set_cache_manager(cache_manager: CacheManager) -> None:
    """设置全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager:
        _global_cache_manager.shutdown()
    _global_cache_manager = cache_manager

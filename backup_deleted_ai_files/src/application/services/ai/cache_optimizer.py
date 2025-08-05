#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI缓存优化器

智能缓存AI请求和响应，提升性能和用户体验
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import pickle
import threading

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.shared.utils.logger import get_logger
from src.application.services.ai.core_abstractions import AIRequest, AIResponse

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频率
    TTL = "ttl"  # 生存时间
    ADAPTIVE = "adaptive"  # 自适应


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None  # 秒
    size: int = 0
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    @property
    def age(self) -> float:
        """获取年龄（秒）"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def access(self):
        """记录访问"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class AICacheOptimizer(QObject):
    """
    AI缓存优化器
    
    功能：
    - 智能缓存AI请求和响应
    - 多种缓存策略
    - 自动过期清理
    - 缓存命中率统计
    - 内存使用优化
    """
    
    # 信号
    cache_hit = pyqtSignal(str)  # cache_key
    cache_miss = pyqtSignal(str)  # cache_key
    cache_stats_updated = pyqtSignal(dict)  # statistics
    
    def __init__(self, 
                 max_size: int = 1000,
                 default_ttl: int = 3600,  # 1小时
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 parent=None):
        super().__init__(parent)
        
        # 配置
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        
        # 缓存存储
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # 用于LRU
        self._lock = threading.RLock()
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._total_size = 0
        
        # 清理定时器
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_expired)
        self._cleanup_timer.start(300000)  # 每5分钟清理一次
        
        # 统计定时器
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._emit_stats)
        self._stats_timer.start(60000)  # 每分钟发送统计
        
        logger.info(f"AI缓存优化器初始化完成 (策略: {strategy.value}, 最大大小: {max_size})")
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """生成缓存键"""
        # 创建包含关键信息的字典
        cache_data = {
            'prompt': request.prompt,
            'context': request.context,
            'request_type': request.request_type.value,
            'max_tokens': request.max_tokens,
            'temperature': request.temperature,
            'model': getattr(request, 'model', None),
            'provider': getattr(request, 'provider', None)
        }
        
        # 生成哈希
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]
    
    def get(self, request: AIRequest) -> Optional[AIResponse]:
        """从缓存获取响应"""
        cache_key = self._generate_cache_key(request)
        
        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                self.cache_miss.emit(cache_key)
                return None
            
            entry = self._cache[cache_key]
            
            # 检查是否过期
            if entry.is_expired:
                del self._cache[cache_key]
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._total_size -= entry.size
                self._misses += 1
                self.cache_miss.emit(cache_key)
                return None
            
            # 记录访问
            entry.access()
            self._update_access_order(cache_key)
            
            self._hits += 1
            self.cache_hit.emit(cache_key)
            
            logger.debug(f"缓存命中: {cache_key}")
            return entry.value
    
    def put(self, request: AIRequest, response: AIResponse, ttl: Optional[int] = None):
        """将响应放入缓存"""
        cache_key = self._generate_cache_key(request)
        
        # 计算大小
        try:
            size = len(pickle.dumps(response))
        except:
            size = len(str(response))
        
        with self._lock:
            # 检查是否需要腾出空间
            self._ensure_space(size)
            
            # 创建缓存条目
            entry = CacheEntry(
                key=cache_key,
                value=response,
                ttl=ttl or self.default_ttl,
                size=size
            )
            
            # 如果已存在，先移除旧的
            if cache_key in self._cache:
                old_entry = self._cache[cache_key]
                self._total_size -= old_entry.size
            
            # 添加新条目
            self._cache[cache_key] = entry
            self._total_size += size
            self._update_access_order(cache_key)
            
            logger.debug(f"缓存存储: {cache_key} (大小: {size} bytes)")
    
    def _ensure_space(self, required_size: int):
        """确保有足够的空间"""
        while (len(self._cache) >= self.max_size or 
               self._total_size + required_size > self.max_size * 1024 * 1024):  # 假设每个条目平均1MB
            
            if not self._cache:
                break
            
            # 根据策略选择要移除的条目
            key_to_remove = self._select_eviction_candidate()
            if key_to_remove:
                self._evict(key_to_remove)
            else:
                break
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """选择要移除的缓存条目"""
        if not self._cache:
            return None
        
        if self.strategy == CacheStrategy.LRU:
            return self._access_order[0] if self._access_order else None
        
        elif self.strategy == CacheStrategy.LFU:
            # 选择访问次数最少的
            min_access = min(entry.access_count for entry in self._cache.values())
            for key, entry in self._cache.items():
                if entry.access_count == min_access:
                    return key
        
        elif self.strategy == CacheStrategy.TTL:
            # 选择最快过期的
            now = datetime.now()
            earliest_expiry = None
            earliest_key = None
            
            for key, entry in self._cache.items():
                if entry.ttl is not None:
                    expiry_time = entry.created_at + timedelta(seconds=entry.ttl)
                    if earliest_expiry is None or expiry_time < earliest_expiry:
                        earliest_expiry = expiry_time
                        earliest_key = key
            
            return earliest_key
        
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # 自适应策略：综合考虑访问频率、时间和大小
            best_score = float('inf')
            best_key = None
            
            for key, entry in self._cache.items():
                # 计算综合评分（越小越容易被移除）
                age_factor = entry.age / 3600  # 年龄因子（小时）
                frequency_factor = 1.0 / max(entry.access_count, 1)  # 频率因子
                size_factor = entry.size / (1024 * 1024)  # 大小因子（MB）
                
                score = age_factor + frequency_factor + size_factor * 0.1
                
                if score < best_score:
                    best_score = score
                    best_key = key
            
            return best_key
        
        # 默认返回第一个
        return next(iter(self._cache.keys()))
    
    def _evict(self, key: str):
        """移除缓存条目"""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._total_size -= entry.size
            self._evictions += 1
            
            if key in self._access_order:
                self._access_order.remove(key)
            
            logger.debug(f"缓存移除: {key}")
    
    def _update_access_order(self, key: str):
        """更新访问顺序（用于LRU）"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _cleanup_expired(self):
        """清理过期的缓存条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                self._evict(key)
            
            if expired_keys:
                logger.info(f"清理过期缓存条目: {len(expired_keys)} 个")
    
    def _emit_stats(self):
        """发送统计信息"""
        stats = self.get_statistics()
        self.cache_stats_updated.emit(stats)
    
    # 公共接口方法
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'evictions': self._evictions,
            'cache_size': len(self._cache),
            'max_size': self.max_size,
            'total_size_bytes': self._total_size,
            'strategy': self.strategy.value
        }
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._total_size = 0
            logger.info("缓存已清空")
    
    def remove(self, request: AIRequest) -> bool:
        """移除特定请求的缓存"""
        cache_key = self._generate_cache_key(request)
        
        with self._lock:
            if cache_key in self._cache:
                self._evict(cache_key)
                return True
            return False
    
    def set_strategy(self, strategy: CacheStrategy):
        """设置缓存策略"""
        self.strategy = strategy
        logger.info(f"缓存策略已更新: {strategy.value}")
    
    def set_max_size(self, max_size: int):
        """设置最大缓存大小"""
        self.max_size = max_size
        
        # 如果当前缓存超过新的限制，进行清理
        with self._lock:
            while len(self._cache) > max_size:
                key_to_remove = self._select_eviction_candidate()
                if key_to_remove:
                    self._evict(key_to_remove)
                else:
                    break
        
        logger.info(f"最大缓存大小已更新: {max_size}")
    
    def get_cache_keys(self) -> List[str]:
        """获取所有缓存键"""
        with self._lock:
            return list(self._cache.keys())
    
    def get_cache_info(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存条目信息"""
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            entry = self._cache[cache_key]
            return {
                'key': entry.key,
                'created_at': entry.created_at.isoformat(),
                'last_accessed': entry.last_accessed.isoformat(),
                'access_count': entry.access_count,
                'ttl': entry.ttl,
                'size': entry.size,
                'age': entry.age,
                'is_expired': entry.is_expired
            }


# 全局缓存优化器实例
_global_cache_optimizer: Optional[AICacheOptimizer] = None


def get_cache_optimizer() -> Optional[AICacheOptimizer]:
    """获取全局缓存优化器"""
    return _global_cache_optimizer


def initialize_cache_optimizer(
    max_size: int = 1000,
    default_ttl: int = 3600,
    strategy: CacheStrategy = CacheStrategy.ADAPTIVE
) -> AICacheOptimizer:
    """初始化全局缓存优化器"""
    global _global_cache_optimizer
    _global_cache_optimizer = AICacheOptimizer(max_size, default_ttl, strategy)
    logger.info("全局AI缓存优化器已初始化")
    return _global_cache_optimizer


def cleanup_cache_optimizer():
    """清理全局缓存优化器"""
    global _global_cache_optimizer
    if _global_cache_optimizer:
        _global_cache_optimizer.clear()
        _global_cache_optimizer = None
        logger.info("全局AI缓存优化器已清理")

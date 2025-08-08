#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对象池管理器

提供统一的对象池管理，减少频繁对象创建和销毁的开销。
支持多种对象类型的池化管理。
"""

import threading
import weakref
from typing import Dict, List, Optional, Callable, Any, Type, TypeVar
from collections import deque
from dataclasses import dataclass

from src.shared.utils.logger import get_logger
from src.shared.constants import OBJECT_POOL_SIZE

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class PoolConfig:
    """对象池配置"""
    max_size: int = OBJECT_POOL_SIZE
    factory: Optional[Callable[[], Any]] = None
    reset_func: Optional[Callable[[Any], None]] = None
    validate_func: Optional[Callable[[Any], bool]] = None


class ObjectPool:
    """
    通用对象池
    
    管理特定类型对象的创建、复用和清理。
    """
    
    def __init__(self, config: PoolConfig):
        """
        初始化对象池
        
        Args:
            config: 对象池配置
        """
        self.config = config
        self._pool: deque = deque(maxlen=config.max_size)
        self._active_objects: weakref.WeakSet = weakref.WeakSet()
        self._lock = threading.RLock()
        self._created_count = 0
        self._reused_count = 0
        
        logger.debug(f"对象池初始化: 最大大小={config.max_size}")
    
    def acquire(self) -> Any:
        """
        获取对象
        
        Returns:
            Any: 池化对象
        """
        with self._lock:
            # 尝试从池中获取对象
            while self._pool:
                obj = self._pool.popleft()
                
                # 验证对象是否有效
                if self.config.validate_func and not self.config.validate_func(obj):
                    continue
                
                # 重置对象状态
                if self.config.reset_func:
                    try:
                        self.config.reset_func(obj)
                    except Exception as e:
                        logger.warning(f"重置对象失败: {e}")
                        continue
                
                self._active_objects.add(obj)
                self._reused_count += 1
                logger.debug(f"从池中复用对象: {type(obj).__name__}")
                return obj
            
            # 池中没有可用对象，创建新对象
            if self.config.factory:
                try:
                    obj = self.config.factory()
                    self._active_objects.add(obj)
                    self._created_count += 1
                    logger.debug(f"创建新对象: {type(obj).__name__}")
                    return obj
                except Exception as e:
                    logger.error(f"创建对象失败: {e}")
                    raise
            else:
                raise RuntimeError("对象池没有配置工厂函数")
    
    def release(self, obj: Any) -> None:
        """
        释放对象回池中
        
        Args:
            obj: 要释放的对象
        """
        if obj is None:
            return
        
        with self._lock:
            # 检查对象是否来自此池
            if obj not in self._active_objects:
                logger.warning(f"尝试释放不属于此池的对象: {type(obj).__name__}")
                return
            
            # 验证对象状态
            if self.config.validate_func and not self.config.validate_func(obj):
                logger.debug(f"对象状态无效，不回收: {type(obj).__name__}")
                return
            
            # 如果池未满，将对象放回池中
            if len(self._pool) < self.config.max_size:
                self._pool.append(obj)
                logger.debug(f"对象已回收到池: {type(obj).__name__}")
            else:
                logger.debug(f"池已满，丢弃对象: {type(obj).__name__}")
    
    def clear(self) -> None:
        """清空对象池"""
        with self._lock:
            self._pool.clear()
            self._active_objects.clear()
            logger.debug("对象池已清空")
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取池统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'active_objects': len(self._active_objects),
                'created_count': self._created_count,
                'reused_count': self._reused_count,
                'max_size': self.config.max_size
            }


class ObjectPoolManager:
    """
    对象池管理器
    
    管理多个不同类型的对象池。
    """
    
    def __init__(self):
        """初始化对象池管理器"""
        self._pools: Dict[str, ObjectPool] = {}
        self._lock = threading.RLock()
        
        # 注册常用对象池
        self._register_common_pools()
        
        logger.info("对象池管理器初始化完成")
    
    def _register_common_pools(self) -> None:
        """注册常用对象池"""
        # 字符串缓冲区池
        self.register_pool(
            'string_buffer',
            PoolConfig(
                max_size=20,
                factory=lambda: [],
                reset_func=lambda buf: buf.clear(),
                validate_func=lambda buf: isinstance(buf, list)
            )
        )
        
        # 字典池
        self.register_pool(
            'dict',
            PoolConfig(
                max_size=30,
                factory=lambda: {},
                reset_func=lambda d: d.clear(),
                validate_func=lambda d: isinstance(d, dict)
            )
        )
        
        # 集合池
        self.register_pool(
            'set',
            PoolConfig(
                max_size=20,
                factory=lambda: set(),
                reset_func=lambda s: s.clear(),
                validate_func=lambda s: isinstance(s, set)
            )
        )

        # 列表池
        self.register_pool(
            'list',
            PoolConfig(
                max_size=30,
                factory=lambda: [],
                reset_func=lambda l: l.clear(),
                validate_func=lambda l: isinstance(l, list)
            )
        )
    
    def register_pool(self, name: str, config: PoolConfig) -> None:
        """
        注册对象池
        
        Args:
            name: 池名称
            config: 池配置
        """
        with self._lock:
            if name in self._pools:
                logger.warning(f"对象池已存在，将被替换: {name}")
            
            self._pools[name] = ObjectPool(config)
            logger.debug(f"注册对象池: {name}")
    
    def get_pool(self, name: str) -> Optional[ObjectPool]:
        """
        获取对象池
        
        Args:
            name: 池名称
        
        Returns:
            Optional[ObjectPool]: 对象池实例
        """
        with self._lock:
            return self._pools.get(name)
    
    def acquire(self, pool_name: str) -> Any:
        """
        从指定池获取对象
        
        Args:
            pool_name: 池名称
        
        Returns:
            Any: 池化对象
        """
        pool = self.get_pool(pool_name)
        if pool:
            return pool.acquire()
        else:
            raise ValueError(f"对象池不存在: {pool_name}")
    
    def release(self, pool_name: str, obj: Any) -> None:
        """
        释放对象到指定池
        
        Args:
            pool_name: 池名称
            obj: 要释放的对象
        """
        pool = self.get_pool(pool_name)
        if pool:
            pool.release(obj)
        else:
            logger.warning(f"尝试释放到不存在的池: {pool_name}")
    
    def clear_all(self) -> None:
        """清空所有对象池"""
        with self._lock:
            for pool in self._pools.values():
                pool.clear()
            logger.info("所有对象池已清空")
    
    def get_all_stats(self) -> Dict[str, Dict[str, int]]:
        """
        获取所有池的统计信息
        
        Returns:
            Dict[str, Dict[str, int]]: 所有池的统计信息
        """
        with self._lock:
            return {
                name: pool.get_stats()
                for name, pool in self._pools.items()
            }


# 全局对象池管理器实例
_global_pool_manager: Optional[ObjectPoolManager] = None


def get_pool_manager() -> ObjectPoolManager:
    """
    获取全局对象池管理器
    
    Returns:
        ObjectPoolManager: 全局对象池管理器实例
    """
    global _global_pool_manager
    if _global_pool_manager is None:
        _global_pool_manager = ObjectPoolManager()
    return _global_pool_manager


def acquire_object(pool_name: str) -> Any:
    """
    从指定池获取对象的便捷函数
    
    Args:
        pool_name: 池名称
    
    Returns:
        Any: 池化对象
    """
    return get_pool_manager().acquire(pool_name)


def release_object(pool_name: str, obj: Any) -> None:
    """
    释放对象到指定池的便捷函数
    
    Args:
        pool_name: 池名称
        obj: 要释放的对象
    """
    get_pool_manager().release(pool_name, obj)


# 上下文管理器支持
class PooledObject:
    """池化对象上下文管理器"""
    
    def __init__(self, pool_name: str):
        """
        初始化池化对象上下文管理器
        
        Args:
            pool_name: 池名称
        """
        self.pool_name = pool_name
        self.obj = None
    
    def __enter__(self):
        """进入上下文"""
        self.obj = acquire_object(self.pool_name)
        return self.obj
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.obj is not None:
            release_object(self.pool_name, self.obj)
            self.obj = None

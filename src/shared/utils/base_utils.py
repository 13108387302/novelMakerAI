#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具类基础架构

提供统一的工具类基类和接口规范，确保所有工具类的一致性。
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum

# 类型变量
T = TypeVar('T')
R = TypeVar('R')

logger = logging.getLogger(__name__)


class OperationResult(Enum):
    """操作结果枚举"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class UtilResult(Generic[T]):
    """
    统一的工具操作结果
    
    所有工具类方法都应该返回这个结果类型，确保一致性。
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    operation: str = ""
    duration: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def success_result(cls, data: T, operation: str = "", duration: float = 0.0, **metadata) -> 'UtilResult[T]':
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            operation=operation,
            duration=duration,
            metadata=metadata
        )
    
    @classmethod
    def failure_result(cls, error: str, operation: str = "", duration: float = 0.0, **metadata) -> 'UtilResult[T]':
        """创建失败结果"""
        return cls(
            success=False,
            error=error,
            operation=operation,
            duration=duration,
            metadata=metadata
        )


class BaseUtility(ABC):
    """
    工具类基类
    
    定义所有工具类的通用接口和行为规范。
    """
    
    def __init__(self, name: str = None):
        """
        初始化工具类
        
        Args:
            name: 工具类名称，用于日志记录
        """
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._stats = {
            'operations_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_duration': 0.0
        }
    
    def _record_operation(self, success: bool, duration: float) -> None:
        """记录操作统计"""
        self._stats['operations_count'] += 1
        self._stats['total_duration'] += duration
        
        if success:
            self._stats['success_count'] += 1
        else:
            self._stats['failure_count'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工具类统计信息"""
        stats = self._stats.copy()
        if stats['operations_count'] > 0:
            stats['success_rate'] = stats['success_count'] / stats['operations_count']
            stats['average_duration'] = stats['total_duration'] / stats['operations_count']
        else:
            stats['success_rate'] = 0.0
            stats['average_duration'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'operations_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_duration': 0.0
        }
    
    @abstractmethod
    def validate_config(self) -> UtilResult[bool]:
        """验证工具类配置"""
        pass
    
    @abstractmethod
    def cleanup(self) -> UtilResult[bool]:
        """清理资源"""
        pass


def timed_operation(operation_name: str = ""):
    """
    统一的操作计时装饰器
    
    为工具类方法提供统一的计时和错误处理。
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            op_name = operation_name or func.__name__
            
            try:
                result = func(self, *args, **kwargs)
                duration = time.time() - start_time
                
                # 如果返回的是UtilResult，更新其duration
                if isinstance(result, UtilResult):
                    result.duration = duration
                    result.operation = op_name
                    self._record_operation(result.success, duration)
                else:
                    # 如果不是UtilResult，包装成功结果
                    self._record_operation(True, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                
                self.logger.error(f"{op_name}失败: {error_msg}")
                self._record_operation(False, duration)
                
                # 返回失败结果
                return UtilResult.failure_result(
                    error=error_msg,
                    operation=op_name,
                    duration=duration
                )
        
        return wrapper
    return decorator


class UtilityRegistry:
    """
    工具类注册表
    
    管理所有工具类实例，提供统一的访问接口。
    """
    
    def __init__(self):
        self._utilities: Dict[str, BaseUtility] = {}
        self._logger = logging.getLogger(f"{__name__}.UtilityRegistry")
    
    def register(self, name: str, utility: BaseUtility) -> None:
        """注册工具类"""
        if name in self._utilities:
            self._logger.warning(f"工具类 {name} 已存在，将被覆盖")
        
        self._utilities[name] = utility
        self._logger.debug(f"注册工具类: {name}")
    
    def get(self, name: str) -> Optional[BaseUtility]:
        """获取工具类"""
        return self._utilities.get(name)
    
    def unregister(self, name: str) -> bool:
        """注销工具类"""
        if name in self._utilities:
            utility = self._utilities.pop(name)
            # 清理资源
            try:
                utility.cleanup()
            except Exception as e:
                self._logger.error(f"清理工具类 {name} 失败: {e}")
            
            self._logger.debug(f"注销工具类: {name}")
            return True
        return False
    
    def list_utilities(self) -> Dict[str, str]:
        """列出所有注册的工具类"""
        return {name: util.__class__.__name__ for name, util in self._utilities.items()}
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有工具类的统计信息"""
        return {name: util.get_stats() for name, util in self._utilities.items()}
    
    def cleanup_all(self) -> None:
        """清理所有工具类"""
        for name, utility in self._utilities.items():
            try:
                utility.cleanup()
            except Exception as e:
                self._logger.error(f"清理工具类 {name} 失败: {e}")


# 全局工具类注册表
_global_registry = UtilityRegistry()


def get_utility_registry() -> UtilityRegistry:
    """获取全局工具类注册表"""
    return _global_registry


def register_utility(name: str, utility: BaseUtility) -> None:
    """注册工具类到全局注册表"""
    _global_registry.register(name, utility)


def get_utility(name: str) -> Optional[BaseUtility]:
    """从全局注册表获取工具类"""
    return _global_registry.get(name)


# 常用的工具类装饰器
def utility_method(operation_name: str = ""):
    """工具类方法装饰器，提供统一的错误处理和日志记录"""
    return timed_operation(operation_name)

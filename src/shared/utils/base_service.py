#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础服务类

提供通用的服务功能，减少重复代码
"""

import logging
from typing import Any, Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseService:
    """
    基础服务类
    
    提供通用的服务功能，包括：
    - 标准化的错误处理
    - 统一的日志记录
    - 操作结果包装
    """
    
    def __init__(self, service_name: str):
        """
        初始化基础服务
        
        Args:
            service_name: 服务名称，用于日志记录
        """
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
    
    async def execute_safe(
        self, 
        operation: Callable[[], T], 
        operation_name: str,
        default_return: T = None,
        log_success: bool = True
    ) -> T:
        """
        安全执行操作
        
        提供统一的异常处理和日志记录。
        
        Args:
            operation: 要执行的操作函数
            operation_name: 操作名称，用于日志记录
            default_return: 操作失败时的默认返回值
            log_success: 是否记录成功日志
            
        Returns:
            T: 操作结果或默认返回值
        """
        try:
            result = await operation() if hasattr(operation, '__call__') else operation
            if log_success:
                self.logger.info(f"{operation_name}成功")
            return result
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {e}")
            return default_return
    
    def execute_safe_sync(
        self, 
        operation: Callable[[], T], 
        operation_name: str,
        default_return: T = None,
        log_success: bool = True
    ) -> T:
        """
        安全执行同步操作
        
        Args:
            operation: 要执行的操作函数
            operation_name: 操作名称，用于日志记录
            default_return: 操作失败时的默认返回值
            log_success: 是否记录成功日志
            
        Returns:
            T: 操作结果或默认返回值
        """
        try:
            result = operation()
            if log_success:
                self.logger.info(f"{operation_name}成功")
            return result
        except Exception as e:
            self.logger.error(f"{operation_name}失败: {e}")
            return default_return
    
    def validate_required(self, value: Any, field_name: str) -> bool:
        """
        验证必需字段
        
        Args:
            value: 要验证的值
            field_name: 字段名称
            
        Returns:
            bool: 验证是否通过
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            self.logger.warning(f"必需字段为空: {field_name}")
            return False
        return True


def service_operation(operation_name: str, log_success: bool = True):
    """
    服务操作装饰器
    
    为服务方法提供统一的错误处理和日志记录。
    
    Args:
        operation_name: 操作名称
        log_success: 是否记录成功日志
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                result = await func(self, *args, **kwargs)
                if log_success and hasattr(self, 'logger'):
                    self.logger.info(f"{operation_name}成功")
                return result
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.error(f"{operation_name}失败: {e}")
                else:
                    logger.error(f"{operation_name}失败: {e}")
                raise
        return wrapper
    return decorator

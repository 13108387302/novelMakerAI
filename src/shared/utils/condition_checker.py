#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件检查工具

提供统一的条件检查和验证功能，减少重复的验证逻辑。
"""

from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, date
from pathlib import Path

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ConditionChecker:
    """
    通用条件检查器
    
    提供各种常用的条件检查方法。
    """
    
    @staticmethod
    def is_valid_string(value: Any, min_length: int = 1, max_length: Optional[int] = None) -> bool:
        """
        检查字符串是否有效
        
        Args:
            value: 要检查的值
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            bool: 是否有效
        """
        if not isinstance(value, str):
            return False
        
        if len(value) < min_length:
            return False
        
        if max_length is not None and len(value) > max_length:
            return False
        
        return True
    
    @staticmethod
    def is_valid_number(value: Any, min_value: Optional[Union[int, float]] = None, 
                       max_value: Optional[Union[int, float]] = None) -> bool:
        """
        检查数字是否有效
        
        Args:
            value: 要检查的值
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            bool: 是否有效
        """
        if not isinstance(value, (int, float)):
            return False
        
        if min_value is not None and value < min_value:
            return False
        
        if max_value is not None and value > max_value:
            return False
        
        return True
    
    @staticmethod
    def is_valid_file_path(path: Union[str, Path], must_exist: bool = False, 
                          allowed_extensions: Optional[List[str]] = None) -> bool:
        """
        检查文件路径是否有效
        
        Args:
            path: 文件路径
            must_exist: 是否必须存在
            allowed_extensions: 允许的扩展名列表
            
        Returns:
            bool: 是否有效
        """
        try:
            path_obj = Path(path)
            
            if must_exist and not path_obj.exists():
                return False
            
            if allowed_extensions:
                extension = path_obj.suffix.lower()
                if extension not in allowed_extensions:
                    return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def is_valid_date_range(start_date: Optional[date], end_date: Optional[date]) -> bool:
        """
        检查日期范围是否有效
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            bool: 是否有效
        """
        if start_date is None or end_date is None:
            return True  # 允许空值
        
        return start_date <= end_date
    
    @staticmethod
    def has_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        检查是否包含必需字段
        
        Args:
            data: 数据字典
            required_fields: 必需字段列表
            
        Returns:
            bool: 是否包含所有必需字段
        """
        if not isinstance(data, dict):
            return False
        
        for field in required_fields:
            if field not in data or data[field] is None:
                return False
        
        return True
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        检查邮箱地址是否有效
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 是否有效
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        检查URL是否有效
        
        Args:
            url: URL地址
            
        Returns:
            bool: 是否有效
        """
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def meets_word_count_requirements(text: str, min_words: int = 0, max_words: Optional[int] = None) -> bool:
        """
        检查文本是否满足字数要求
        
        Args:
            text: 文本内容
            min_words: 最少字数
            max_words: 最多字数
            
        Returns:
            bool: 是否满足要求
        """
        if not isinstance(text, str):
            return False
        
        word_count = len(text.split())
        
        if word_count < min_words:
            return False
        
        if max_words is not None and word_count > max_words:
            return False
        
        return True


class ConditionalExecutor:
    """
    条件执行器
    
    根据条件执行不同的操作。
    """
    
    def __init__(self):
        """初始化条件执行器"""
        self.conditions: List[Dict[str, Any]] = []
    
    def add_condition(self, name: str, condition: Callable[[], bool], 
                     action: Callable[[], Any], priority: int = 0) -> None:
        """
        添加条件和对应的动作
        
        Args:
            name: 条件名称
            condition: 条件函数
            action: 动作函数
            priority: 优先级（数字越大优先级越高）
        """
        self.conditions.append({
            'name': name,
            'condition': condition,
            'action': action,
            'priority': priority
        })
        
        # 按优先级排序
        self.conditions.sort(key=lambda x: x['priority'], reverse=True)
    
    def execute(self) -> Optional[Any]:
        """
        执行第一个满足条件的动作
        
        Returns:
            Optional[Any]: 执行结果
        """
        for item in self.conditions:
            try:
                if item['condition']():
                    logger.debug(f"执行条件动作: {item['name']}")
                    return item['action']()
            except Exception as e:
                logger.error(f"条件检查或执行失败 {item['name']}: {e}")
        
        return None
    
    def execute_all_matching(self) -> List[Any]:
        """
        执行所有满足条件的动作
        
        Returns:
            List[Any]: 所有执行结果
        """
        results = []
        
        for item in self.conditions:
            try:
                if item['condition']():
                    logger.debug(f"执行条件动作: {item['name']}")
                    result = item['action']()
                    results.append(result)
            except Exception as e:
                logger.error(f"条件检查或执行失败 {item['name']}: {e}")
        
        return results
    
    def clear(self) -> None:
        """清空所有条件"""
        self.conditions.clear()


class ValidationChain:
    """
    验证链
    
    按顺序执行多个验证，支持短路逻辑。
    """
    
    def __init__(self, short_circuit: bool = True):
        """
        初始化验证链
        
        Args:
            short_circuit: 是否短路（遇到失败立即停止）
        """
        self.short_circuit = short_circuit
        self.validators: List[Dict[str, Any]] = []
    
    def add_validator(self, name: str, validator: Callable[[Any], bool], 
                     error_message: str = "") -> 'ValidationChain':
        """
        添加验证器
        
        Args:
            name: 验证器名称
            validator: 验证函数
            error_message: 错误消息
            
        Returns:
            ValidationChain: 支持链式调用
        """
        self.validators.append({
            'name': name,
            'validator': validator,
            'error_message': error_message
        })
        return self
    
    def validate(self, data: Any) -> Dict[str, Any]:
        """
        执行验证
        
        Args:
            data: 要验证的数据
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        results = {
            'valid': True,
            'errors': [],
            'passed_validators': [],
            'failed_validators': []
        }
        
        for validator_info in self.validators:
            try:
                is_valid = validator_info['validator'](data)
                
                if is_valid:
                    results['passed_validators'].append(validator_info['name'])
                else:
                    results['valid'] = False
                    results['failed_validators'].append(validator_info['name'])
                    
                    error_msg = validator_info['error_message'] or f"验证失败: {validator_info['name']}"
                    results['errors'].append(error_msg)
                    
                    if self.short_circuit:
                        break
                        
            except Exception as e:
                results['valid'] = False
                results['failed_validators'].append(validator_info['name'])
                results['errors'].append(f"验证器异常 {validator_info['name']}: {e}")
                
                if self.short_circuit:
                    break
        
        return results


# 便捷函数
def create_string_validator(min_length: int = 1, max_length: Optional[int] = None) -> Callable[[Any], bool]:
    """创建字符串验证器"""
    return lambda value: ConditionChecker.is_valid_string(value, min_length, max_length)


def create_number_validator(min_value: Optional[Union[int, float]] = None, 
                          max_value: Optional[Union[int, float]] = None) -> Callable[[Any], bool]:
    """创建数字验证器"""
    return lambda value: ConditionChecker.is_valid_number(value, min_value, max_value)


def create_file_validator(must_exist: bool = False, 
                         allowed_extensions: Optional[List[str]] = None) -> Callable[[Any], bool]:
    """创建文件路径验证器"""
    return lambda path: ConditionChecker.is_valid_file_path(path, must_exist, allowed_extensions)


def create_required_fields_validator(required_fields: List[str]) -> Callable[[Any], bool]:
    """创建必需字段验证器"""
    return lambda data: ConditionChecker.has_required_fields(data, required_fields)


def quick_validate(data: Any, validators: List[Callable[[Any], bool]], 
                  short_circuit: bool = True) -> bool:
    """
    快速验证
    
    Args:
        data: 要验证的数据
        validators: 验证器列表
        short_circuit: 是否短路
        
    Returns:
        bool: 验证是否通过
    """
    for validator in validators:
        try:
            if not validator(data):
                if short_circuit:
                    return False
        except Exception as e:
            logger.error(f"验证器执行失败: {e}")
            if short_circuit:
                return False
    
    return True

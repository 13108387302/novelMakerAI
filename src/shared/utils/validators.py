#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用验证模块

提供常用的数据验证功能
"""

import re
from typing import Any, List, Optional, Union, Callable
from pathlib import Path


class ValidationResult:
    """
    验证结果类

    封装验证操作的结果，包括验证状态和错误信息。
    支持多个验证结果的合并操作。

    Attributes:
        is_valid: 验证是否通过
        errors: 错误信息列表
    """

    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None):
        """
        初始化验证结果

        Args:
            is_valid: 验证是否通过，默认为True
            errors: 错误信息列表，默认为空列表
        """
        self.is_valid = is_valid
        self.errors = errors or []

    def add_error(self, error: str):
        """
        添加错误信息

        Args:
            error: 错误信息字符串
        """
        self.errors.append(error)
        self.is_valid = False

    def merge(self, other: 'ValidationResult'):
        """
        合并另一个验证结果

        Args:
            other: 要合并的验证结果
        """
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)


class Validator:
    """
    通用验证器类

    提供常用的数据验证方法，包括必填验证、长度验证、格式验证等。
    所有验证方法都返回ValidationResult对象。

    实现方式：
    - 使用静态方法提供验证功能
    - 返回统一的ValidationResult对象
    - 支持自定义字段名称和错误消息
    - 提供链式验证和结果合并
    """
    
    @staticmethod
    def required(value: Any, field_name: str = "字段") -> ValidationResult:
        """必填验证"""
        result = ValidationResult()
        
        if value is None:
            result.add_error(f"{field_name}不能为空")
        elif isinstance(value, str) and not value.strip():
            result.add_error(f"{field_name}不能为空")
        elif isinstance(value, (list, dict, tuple)) and len(value) == 0:
            result.add_error(f"{field_name}不能为空")
            
        return result
    
    @staticmethod
    def string_length(value: str, min_length: int = 0, max_length: int = None, field_name: str = "字符串") -> ValidationResult:
        """字符串长度验证"""
        result = ValidationResult()
        
        if not isinstance(value, str):
            result.add_error(f"{field_name}必须是字符串")
            return result
            
        length = len(value)
        
        if length < min_length:
            result.add_error(f"{field_name}长度不能少于{min_length}个字符")
            
        if max_length is not None and length > max_length:
            result.add_error(f"{field_name}长度不能超过{max_length}个字符")
            
        return result
    
    @staticmethod
    def number_range(value: Union[int, float], min_value: Union[int, float] = None, 
                    max_value: Union[int, float] = None, field_name: str = "数值") -> ValidationResult:
        """数值范围验证"""
        result = ValidationResult()
        
        if not isinstance(value, (int, float)):
            result.add_error(f"{field_name}必须是数值")
            return result
            
        if min_value is not None and value < min_value:
            result.add_error(f"{field_name}不能小于{min_value}")
            
        if max_value is not None and value > max_value:
            result.add_error(f"{field_name}不能大于{max_value}")
            
        return result
    
    @staticmethod
    def email(value: str, field_name: str = "邮箱") -> ValidationResult:
        """邮箱格式验证"""
        result = ValidationResult()
        
        if not isinstance(value, str):
            result.add_error(f"{field_name}必须是字符串")
            return result
            
        if not value.strip():
            return result  # 空值不验证格式
            
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value.strip()):
            result.add_error(f"{field_name}格式不正确")
            
        return result
    
    @staticmethod
    def url(value: str, field_name: str = "网址") -> ValidationResult:
        """URL格式验证"""
        result = ValidationResult()
        
        if not isinstance(value, str):
            result.add_error(f"{field_name}必须是字符串")
            return result
            
        if not value.strip():
            return result  # 空值不验证格式
            
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, value.strip(), re.IGNORECASE):
            result.add_error(f"{field_name}格式不正确")
            
        return result
    
    @staticmethod
    def file_path(value: Union[str, Path], must_exist: bool = False, 
                 allowed_extensions: Optional[List[str]] = None, field_name: str = "文件路径") -> ValidationResult:
        """文件路径验证"""
        result = ValidationResult()
        
        try:
            path = Path(value) if isinstance(value, str) else value
        except Exception:
            result.add_error(f"{field_name}格式不正确")
            return result
            
        if must_exist and not path.exists():
            result.add_error(f"{field_name}指向的文件不存在")
            
        if allowed_extensions:
            ext = path.suffix.lower()
            if ext not in [e.lower() for e in allowed_extensions]:
                result.add_error(f"{field_name}扩展名必须是: {', '.join(allowed_extensions)}")
                
        return result
    
    @staticmethod
    def regex_pattern(value: str, pattern: str, field_name: str = "字段") -> ValidationResult:
        """正则表达式验证"""
        result = ValidationResult()
        
        if not isinstance(value, str):
            result.add_error(f"{field_name}必须是字符串")
            return result
            
        if not value.strip():
            return result  # 空值不验证格式
            
        try:
            if not re.match(pattern, value):
                result.add_error(f"{field_name}格式不正确")
        except re.error:
            result.add_error(f"{field_name}验证规则错误")
            
        return result
    
    @staticmethod
    def choice(value: Any, choices: List[Any], field_name: str = "字段") -> ValidationResult:
        """选择验证"""
        result = ValidationResult()
        
        if value not in choices:
            result.add_error(f"{field_name}必须是以下值之一: {', '.join(map(str, choices))}")
            
        return result
    
    @staticmethod
    def custom(value: Any, validator_func: Callable[[Any], bool], 
              error_message: str, field_name: str = "字段") -> ValidationResult:
        """自定义验证"""
        result = ValidationResult()
        
        try:
            if not validator_func(value):
                result.add_error(error_message)
        except Exception:
            result.add_error(f"{field_name}验证失败")
            
        return result


class ProjectValidator:
    """项目验证器"""
    
    @staticmethod
    def validate_project_name(name: str) -> ValidationResult:
        """验证项目名称"""
        result = ValidationResult()
        
        # 必填验证
        required_result = Validator.required(name, "项目名称")
        result.merge(required_result)
        
        if not result.is_valid:
            return result
            
        # 长度验证
        length_result = Validator.string_length(name, 1, 200, "项目名称")
        result.merge(length_result)
        
        # 特殊字符验证
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
        for char in invalid_chars:
            if char in name:
                result.add_error(f"项目名称不能包含特殊字符: {char}")
                break
                
        return result
    
    @staticmethod
    def validate_target_word_count(count: int) -> ValidationResult:
        """验证目标字数"""
        return Validator.number_range(count, 1, 10000000, "目标字数")
    
    @staticmethod
    def validate_author_name(name: str) -> ValidationResult:
        """验证作者名称"""
        result = ValidationResult()
        
        if name:  # 非必填
            length_result = Validator.string_length(name, 0, 100, "作者名称")
            result.merge(length_result)
            
        return result


class DocumentValidator:
    """文档验证器"""
    
    @staticmethod
    def validate_document_title(title: str) -> ValidationResult:
        """验证文档标题"""
        result = ValidationResult()
        
        # 必填验证
        required_result = Validator.required(title, "文档标题")
        result.merge(required_result)
        
        if not result.is_valid:
            return result
            
        # 长度验证
        length_result = Validator.string_length(title, 1, 200, "文档标题")
        result.merge(length_result)
        
        return result
    
    @staticmethod
    def validate_document_content(content: str) -> ValidationResult:
        """验证文档内容"""
        result = ValidationResult()
        
        if content and len(content) > 1000000:  # 100万字符限制
            result.add_error("文档内容过长（最多100万字符）")
            
        return result


class SettingsValidator:
    """设置验证器"""
    
    @staticmethod
    def validate_auto_save_interval(interval: int) -> ValidationResult:
        """验证自动保存间隔"""
        return Validator.number_range(interval, 5, 3600, "自动保存间隔")
    
    @staticmethod
    def validate_font_size(size: int) -> ValidationResult:
        """验证字体大小"""
        return Validator.number_range(size, 8, 72, "字体大小")
    
    @staticmethod
    def validate_ai_creativity_level(level: float) -> ValidationResult:
        """验证AI创造力水平"""
        return Validator.number_range(level, 0.0, 1.0, "AI创造力水平")


def validate_object(obj: Any, validation_rules: dict) -> ValidationResult:
    """验证对象"""
    result = ValidationResult()
    
    for field_name, rules in validation_rules.items():
        field_value = getattr(obj, field_name, None)
        
        for rule in rules:
            if callable(rule):
                field_result = rule(field_value)
            else:
                # 假设是 (validator_func, *args) 的形式
                validator_func, *args = rule
                field_result = validator_func(field_value, *args)
                
            result.merge(field_result)
            
    return result


# 便捷函数
def is_valid_project_name(name: str) -> bool:
    """检查项目名称是否有效"""
    return ProjectValidator.validate_project_name(name).is_valid


def is_valid_email(email: str) -> bool:
    """检查邮箱是否有效"""
    return Validator.email(email).is_valid


def is_valid_file_path(path: Union[str, Path], must_exist: bool = False) -> bool:
    """检查文件路径是否有效"""
    return Validator.file_path(path, must_exist).is_valid

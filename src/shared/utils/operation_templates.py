#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作模板工厂

提供通用的操作模板，减少跨模块的重复代码。
包括文件操作、数据验证、错误处理等常用模式。
"""

import asyncio
from typing import Any, Callable, Optional, Dict, List, Union, TypeVar, Generic
from pathlib import Path
from functools import wraps

from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import handle_errors, ApplicationError, ErrorSeverity

logger = get_logger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class OperationTemplate(Generic[T, R]):
    """
    通用操作模板
    
    提供标准化的操作执行模式，包括验证、执行、错误处理和清理。
    """
    
    def __init__(self, operation_name: str):
        """
        初始化操作模板
        
        Args:
            operation_name: 操作名称，用于日志和错误消息
        """
        self.operation_name = operation_name
        self.validators: List[Callable[[T], bool]] = []
        self.pre_processors: List[Callable[[T], T]] = []
        self.post_processors: List[Callable[[R], R]] = []
        self.cleanup_handlers: List[Callable[[], None]] = []
        
    def add_validator(self, validator: Callable[[T], bool], error_message: str = "") -> 'OperationTemplate[T, R]':
        """
        添加验证器
        
        Args:
            validator: 验证函数
            error_message: 验证失败时的错误消息
            
        Returns:
            self: 支持链式调用
        """
        def wrapped_validator(data: T) -> bool:
            try:
                result = validator(data)
                if not result and error_message:
                    logger.warning(f"{self.operation_name}验证失败: {error_message}")
                return result
            except Exception as e:
                logger.error(f"{self.operation_name}验证器异常: {e}")
                return False
        
        self.validators.append(wrapped_validator)
        return self
    
    def add_pre_processor(self, processor: Callable[[T], T]) -> 'OperationTemplate[T, R]':
        """
        添加预处理器
        
        Args:
            processor: 预处理函数
            
        Returns:
            self: 支持链式调用
        """
        self.pre_processors.append(processor)
        return self
    
    def add_post_processor(self, processor: Callable[[R], R]) -> 'OperationTemplate[T, R]':
        """
        添加后处理器
        
        Args:
            processor: 后处理函数
            
        Returns:
            self: 支持链式调用
        """
        self.post_processors.append(processor)
        return self
    
    def add_cleanup_handler(self, handler: Callable[[], None]) -> 'OperationTemplate[T, R]':
        """
        添加清理处理器
        
        Args:
            handler: 清理函数
            
        Returns:
            self: 支持链式调用
        """
        self.cleanup_handlers.append(handler)
        return self
    
    def execute(self, data: T, operation: Callable[[T], R]) -> Optional[R]:
        """
        执行操作
        
        Args:
            data: 输入数据
            operation: 操作函数
            
        Returns:
            Optional[R]: 操作结果，失败时返回None
        """
        try:
            # 验证输入
            for validator in self.validators:
                if not validator(data):
                    logger.error(f"{self.operation_name}输入验证失败")
                    return None
            
            # 预处理
            processed_data = data
            for processor in self.pre_processors:
                processed_data = processor(processed_data)
            
            # 执行操作
            logger.debug(f"开始执行{self.operation_name}")
            result = operation(processed_data)
            
            # 后处理
            processed_result = result
            for processor in self.post_processors:
                processed_result = processor(processed_result)
            
            logger.debug(f"{self.operation_name}执行成功")
            return processed_result
            
        except Exception as e:
            logger.error(f"{self.operation_name}执行失败: {e}")
            return None
        finally:
            # 清理
            for handler in self.cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    logger.warning(f"{self.operation_name}清理失败: {e}")
    
    async def execute_async(self, data: T, operation: Callable[[T], R]) -> Optional[R]:
        """
        异步执行操作
        
        Args:
            data: 输入数据
            operation: 操作函数（可以是同步或异步）
            
        Returns:
            Optional[R]: 操作结果，失败时返回None
        """
        try:
            # 验证输入
            for validator in self.validators:
                if not validator(data):
                    logger.error(f"{self.operation_name}输入验证失败")
                    return None
            
            # 预处理
            processed_data = data
            for processor in self.pre_processors:
                processed_data = processor(processed_data)
            
            # 执行操作
            logger.debug(f"开始异步执行{self.operation_name}")
            if asyncio.iscoroutinefunction(operation):
                result = await operation(processed_data)
            else:
                result = operation(processed_data)
            
            # 后处理
            processed_result = result
            for processor in self.post_processors:
                processed_result = processor(processed_result)
            
            logger.debug(f"{self.operation_name}异步执行成功")
            return processed_result
            
        except Exception as e:
            logger.error(f"{self.operation_name}异步执行失败: {e}")
            return None
        finally:
            # 清理
            for handler in self.cleanup_handlers:
                try:
                    handler()
                except Exception as e:
                    logger.warning(f"{self.operation_name}清理失败: {e}")


class FileOperationTemplate:
    """
    文件操作模板
    
    提供标准化的文件操作模式。
    """
    
    @staticmethod
    def safe_file_operation(operation_name: str, file_path: Union[str, Path], 
                          operation: Callable[[Path], T], 
                          create_dirs: bool = False,
                          backup: bool = False) -> Optional[T]:
        """
        安全的文件操作模板
        
        Args:
            operation_name: 操作名称
            file_path: 文件路径
            operation: 文件操作函数
            create_dirs: 是否创建目录
            backup: 是否备份原文件
            
        Returns:
            Optional[T]: 操作结果
        """
        path = Path(file_path)
        backup_path = None
        
        try:
            # 创建目录
            if create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                logger.debug(f"创建目录: {path.parent}")
            
            # 备份原文件
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + '.backup')
                import shutil
                shutil.copy2(path, backup_path)
                logger.debug(f"备份文件: {backup_path}")
            
            # 执行操作
            logger.debug(f"开始{operation_name}: {path}")
            result = operation(path)
            logger.debug(f"{operation_name}成功: {path}")
            
            # 删除备份文件（操作成功）
            if backup_path and backup_path.exists():
                backup_path.unlink()
                logger.debug(f"删除备份文件: {backup_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"{operation_name}失败: {path}, 错误: {e}")
            
            # 恢复备份文件
            if backup_path and backup_path.exists():
                try:
                    import shutil
                    shutil.move(backup_path, path)
                    logger.info(f"已恢复备份文件: {path}")
                except Exception as restore_error:
                    logger.error(f"恢复备份文件失败: {restore_error}")
            
            return None


class ValidationTemplate:
    """
    数据验证模板
    
    提供常用的数据验证模式。
    """
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        验证必需字段
        
        Args:
            data: 数据字典
            required_fields: 必需字段列表
            
        Returns:
            bool: 验证是否通过
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            logger.warning(f"缺少必需字段: {missing_fields}")
            return False
        return True
    
    @staticmethod
    def validate_string_length(value: str, min_length: int = 0, max_length: int = None) -> bool:
        """
        验证字符串长度
        
        Args:
            value: 字符串值
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            bool: 验证是否通过
        """
        if not isinstance(value, str):
            return False
        
        if len(value) < min_length:
            logger.warning(f"字符串长度不足: {len(value)} < {min_length}")
            return False
        
        if max_length is not None and len(value) > max_length:
            logger.warning(f"字符串长度超限: {len(value)} > {max_length}")
            return False
        
        return True
    
    @staticmethod
    def validate_file_path(path: Union[str, Path], must_exist: bool = False, 
                          allowed_extensions: List[str] = None) -> bool:
        """
        验证文件路径
        
        Args:
            path: 文件路径
            must_exist: 文件是否必须存在
            allowed_extensions: 允许的文件扩展名列表
            
        Returns:
            bool: 验证是否通过
        """
        try:
            path_obj = Path(path)
            
            if must_exist and not path_obj.exists():
                logger.warning(f"文件不存在: {path}")
                return False
            
            if allowed_extensions:
                extension = path_obj.suffix.lower()
                if extension not in allowed_extensions:
                    logger.warning(f"不支持的文件扩展名: {extension}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"文件路径验证失败: {e}")
            return False


class ConfigurationTemplate:
    """
    配置操作模板
    
    提供标准化的配置读取和设置模式。
    """
    
    @staticmethod
    def get_setting_with_fallback(settings_service, key: str, default: Any, 
                                 validators: List[Callable[[Any], bool]] = None) -> Any:
        """
        获取设置值，支持回退和验证
        
        Args:
            settings_service: 设置服务
            key: 设置键
            default: 默认值
            validators: 验证器列表
            
        Returns:
            Any: 设置值
        """
        try:
            value = settings_service.get_setting(key, default)
            
            # 验证值
            if validators:
                for validator in validators:
                    if not validator(value):
                        logger.warning(f"设置值验证失败: {key}={value}, 使用默认值")
                        return default
            
            return value
            
        except Exception as e:
            logger.error(f"获取设置失败: {key}, 错误: {e}, 使用默认值")
            return default
    
    @staticmethod
    def batch_get_settings(settings_service, settings_config: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量获取设置
        
        Args:
            settings_service: 设置服务
            settings_config: 设置配置字典 {key: {default: value, validators: [...]}}
            
        Returns:
            Dict[str, Any]: 设置值字典
        """
        result = {}
        
        for key, config in settings_config.items():
            default = config.get('default')
            validators = config.get('validators', [])
            
            result[key] = ConfigurationTemplate.get_setting_with_fallback(
                settings_service, key, default, validators
            )
        
        return result


# 便捷函数
def create_file_operation_template(operation_name: str) -> OperationTemplate[Path, Any]:
    """
    创建文件操作模板的便捷函数
    
    Args:
        operation_name: 操作名称
        
    Returns:
        OperationTemplate: 配置好的文件操作模板
    """
    template = OperationTemplate[Path, Any](operation_name)
    
    # 添加文件路径验证
    template.add_validator(
        lambda path: ValidationTemplate.validate_file_path(path),
        "无效的文件路径"
    )
    
    return template


def create_data_operation_template(operation_name: str, required_fields: List[str] = None) -> OperationTemplate[Dict[str, Any], Any]:
    """
    创建数据操作模板的便捷函数
    
    Args:
        operation_name: 操作名称
        required_fields: 必需字段列表
        
    Returns:
        OperationTemplate: 配置好的数据操作模板
    """
    template = OperationTemplate[Dict[str, Any], Any](operation_name)
    
    # 添加必需字段验证
    if required_fields:
        template.add_validator(
            lambda data: ValidationTemplate.validate_required_fields(data, required_fields),
            f"缺少必需字段: {required_fields}"
        )
    
    return template

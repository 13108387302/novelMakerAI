#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器

实现简单而强大的依赖注入功能，支持：
- 单例和瞬态生命周期
- 构造函数注入
- 接口到实现的映射
- 循环依赖检测
"""

import inspect
import threading
from typing import Any, Callable, Dict, Type, TypeVar, Union, Optional, Set, get_origin, get_args
from abc import ABC, abstractmethod

T = TypeVar('T')


class LifetimeScope:
    """
    生命周期范围枚举

    定义服务实例的生命周期管理策略。

    Values:
        SINGLETON: 单例模式，整个应用程序生命周期内只创建一个实例
        TRANSIENT: 瞬态模式，每次请求都创建新实例
        SCOPED: 作用域模式，在特定作用域内共享实例
    """
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """
    服务描述符

    描述服务的注册信息，包括服务类型、实现类型、工厂函数和生命周期。
    用于在容器中存储服务的元数据。

    Attributes:
        service_type: 服务接口类型
        implementation_type: 实现类型
        factory: 工厂函数
        lifetime: 生命周期范围
        instance: 单例实例（仅用于单例模式）
    """

    def __init__(
        self,
        service_type: Type,
        implementation_type: Optional[Type] = None,
        factory: Optional[Callable] = None,
        lifetime: str = LifetimeScope.TRANSIENT,
        instance: Optional[Any] = None
    ):
        """
        初始化服务描述符

        Args:
            service_type: 服务接口类型
            implementation_type: 实现类型，默认与服务类型相同
            factory: 工厂函数，用于创建实例
            lifetime: 生命周期范围，默认为瞬态
            instance: 预创建的实例（可选）

        Raises:
            ValueError: 当工厂函数和实现类型都未提供时抛出
        """
        self.service_type = service_type
        self.implementation_type = implementation_type or service_type
        self.factory = factory
        self.lifetime = lifetime
        self.instance = instance

        if not factory and not implementation_type:
            raise ValueError("Either factory or implementation_type must be provided")


class Container:
    """
    依赖注入容器

    实现简单而强大的依赖注入功能，支持多种生命周期管理和循环依赖检测。
    提供服务注册、解析和生命周期管理功能。

    实现方式：
    - 使用字典存储服务描述符
    - 支持构造函数参数自动注入
    - 提供单例和瞬态生命周期管理
    - 包含循环依赖检测机制
    - 线程安全的实例创建

    Attributes:
        _services: 服务描述符字典
        _instances: 单例实例缓存
        _lock: 线程锁
        _resolving: 正在解析的服务集合（用于循环依赖检测）
    """
    
    def __init__(self):
        """
        初始化依赖注入容器

        创建空的服务注册表和实例缓存，初始化线程锁。
        """
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._resolving: Set[Type] = set()

    def register_singleton(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'Container':
        """
        注册单例服务

        注册一个单例生命周期的服务，整个应用程序生命周期内只创建一个实例。

        Args:
            service_type: 服务接口类型
            implementation_type: 实现类型，默认与服务类型相同
            factory: 工厂函数，用于创建实例

        Returns:
            Container: 容器实例，支持链式调用
        """
        return self._register(
            service_type,
            implementation_type,
            factory,
            LifetimeScope.SINGLETON
        )

    def register_transient(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'Container':
        """
        注册瞬态服务

        注册一个瞬态生命周期的服务，每次请求都创建新实例。

        Args:
            service_type: 服务接口类型
            implementation_type: 实现类型，默认与服务类型相同
            factory: 工厂函数，用于创建实例

        Returns:
            Container: 容器实例，支持链式调用
        """
        return self._register(
            service_type,
            implementation_type,
            factory,
            LifetimeScope.TRANSIENT
        )
    
    def register_scoped(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'Container':
        """注册作用域服务"""
        return self._register(
            service_type,
            implementation_type,
            factory,
            LifetimeScope.SCOPED
        )
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'Container':
        """注册实例"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=type(instance),  # 使用实例的类型作为实现类型
                lifetime=LifetimeScope.SINGLETON,
                instance=instance
            )
            self._services[service_type] = descriptor
            self._instances[service_type] = instance
        return self
    
    def _register(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]],
        factory: Optional[Callable[[], T]],
        lifetime: str
    ) -> 'Container':
        """内部注册方法"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type,
                factory=factory,
                lifetime=lifetime
            )
            self._services[service_type] = descriptor
        return self
    
    def get(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        with self._lock:
            return self._resolve(service_type)
    
    def try_get(self, service_type: Type[T]) -> Optional[T]:
        """尝试获取服务实例，失败时返回None"""
        try:
            return self.get(service_type)
        except Exception:
            return None
    
    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services
    
    def _resolve(self, service_type: Type[T]) -> T:
        """解析服务实例"""
        # 检查循环依赖
        if service_type in self._resolving:
            raise RuntimeError(f"Circular dependency detected for {service_type}")
        
        # 检查是否已注册
        if service_type not in self._services:
            raise ValueError(f"Service {service_type} is not registered")
        
        descriptor = self._services[service_type]
        
        # 如果是单例且已创建实例，直接返回
        if descriptor.lifetime == LifetimeScope.SINGLETON:
            if service_type in self._instances:
                return self._instances[service_type]
            elif descriptor.instance is not None:
                return descriptor.instance
        
        # 标记正在解析
        self._resolving.add(service_type)
        
        try:
            # 创建实例
            if descriptor.factory:
                instance = self._create_from_factory(descriptor.factory)
            else:
                instance = self._create_from_type(descriptor.implementation_type)
            
            # 如果是单例，缓存实例
            if descriptor.lifetime == LifetimeScope.SINGLETON:
                self._instances[service_type] = instance
            
            return instance
            
        finally:
            # 移除解析标记
            self._resolving.discard(service_type)
    
    def _create_from_factory(self, factory: Callable) -> Any:
        """从工厂函数创建实例"""
        # 检查工厂函数的参数
        sig = inspect.signature(factory)
        
        if not sig.parameters:
            # 无参数工厂函数
            return factory()
        else:
            # 有参数工厂函数，注入依赖
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param.annotation != inspect.Parameter.empty:
                    resolved_value = self._resolve_parameter(param.annotation)
                    if resolved_value is not None:
                        kwargs[param_name] = resolved_value
            return factory(**kwargs)
    
    def _create_from_type(self, implementation_type: Type) -> Any:
        """从类型创建实例"""
        # 获取构造函数签名
        sig = inspect.signature(implementation_type.__init__)
        
        # 准备构造函数参数
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            if param.annotation != inspect.Parameter.empty:
                # 有类型注解，尝试解析依赖
                resolved_value = self._resolve_parameter(param.annotation)
                if resolved_value is not None:
                    kwargs[param_name] = resolved_value
            elif param.default != inspect.Parameter.empty:
                # 有默认值，使用默认值
                kwargs[param_name] = param.default
            else:
                # 无类型注解且无默认值，跳过
                continue
        
        return implementation_type(**kwargs)

    def _resolve_parameter(self, annotation: Type) -> Any:
        """解析参数类型"""
        try:
            # 处理Optional类型
            origin = get_origin(annotation)
            if origin is Union:
                args = get_args(annotation)
                # Optional[T] 等价于 Union[T, None]
                if len(args) == 2 and type(None) in args:
                    # 获取非None的类型
                    actual_type = args[0] if args[1] is type(None) else args[1]
                    # 如果实际类型已注册，则解析它；否则返回None
                    if self.is_registered(actual_type):
                        return self._resolve(actual_type)
                    else:
                        return None

            # 处理普通类型
            if self.is_registered(annotation):
                return self._resolve(annotation)
            else:
                return None

        except Exception:
            # 如果解析失败，返回None
            return None

    def create_scope(self) -> 'ScopedContainer':
        """创建作用域容器"""
        return ScopedContainer(self)
    
    def dispose(self) -> None:
        """释放容器资源"""
        with self._lock:
            # 释放实现了IDisposable接口的实例
            for instance in self._instances.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception:
                        pass  # 忽略释放错误
            
            self._instances.clear()
            self._services.clear()
            self._resolving.clear()


class ScopedContainer:
    """作用域容器"""
    
    def __init__(self, parent: Container):
        self._parent = parent
        self._scoped_instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
    
    def get(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        with self._lock:
            # 检查是否已注册
            if not self._parent.is_registered(service_type):
                raise ValueError(f"Service {service_type} is not registered")
            
            descriptor = self._parent._services[service_type]
            
            # 如果是作用域服务且已创建实例，直接返回
            if descriptor.lifetime == LifetimeScope.SCOPED:
                if service_type in self._scoped_instances:
                    return self._scoped_instances[service_type]
                
                # 创建新实例
                instance = self._parent._resolve(service_type)
                self._scoped_instances[service_type] = instance
                return instance
            else:
                # 非作用域服务，委托给父容器
                return self._parent.get(service_type)
    
    def dispose(self) -> None:
        """释放作用域资源"""
        with self._lock:
            # 释放作用域实例
            for instance in self._scoped_instances.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception:
                        pass  # 忽略释放错误
            
            self._scoped_instances.clear()


class IDisposable(ABC):
    """可释放接口"""

    @abstractmethod
    def dispose(self) -> None:
        """释放资源"""
        pass


# 全局容器实例
_global_container: Optional[Container] = None
_container_lock = threading.Lock()


def set_global_container(container: Container) -> None:
    """设置全局容器实例"""
    global _global_container
    with _container_lock:
        _global_container = container


def get_global_container() -> Optional[Container]:
    """获取全局容器实例"""
    global _global_container
    with _container_lock:
        return _global_container


def get_container() -> Optional[Container]:
    """获取全局容器实例"""
    global _global_container
    with _container_lock:
        return _global_container


def clear_global_container() -> None:
    """清除全局容器实例"""
    global _global_container
    with _container_lock:
        _global_container = None

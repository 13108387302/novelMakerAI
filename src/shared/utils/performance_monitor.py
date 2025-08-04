#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具

提供应用程序性能监控和分析功能。
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
from collections import deque

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    category: str = "general"


@dataclass
class MemoryUsage:
    """内存使用情况"""
    rss: int  # 物理内存
    vms: int  # 虚拟内存
    percent: float  # 内存使用百分比
    available: int  # 可用内存
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CPUUsage:
    """CPU使用情况"""
    percent: float  # CPU使用百分比
    count: int  # CPU核心数
    timestamp: datetime = field(default_factory=datetime.now)


class PerformanceMonitor:
    """
    性能监控器
    
    监控应用程序的性能指标，包括内存使用、CPU使用、响应时间等。
    """
    
    def __init__(self, max_history: int = 1000):
        """
        初始化性能监控器
        
        Args:
            max_history: 最大历史记录数量
        """
        self.max_history = max_history
        self.metrics: deque = deque(maxlen=max_history)
        self.memory_history: deque = deque(maxlen=max_history)
        self.cpu_history: deque = deque(maxlen=max_history)
        
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_interval = 5.0  # 秒
        
        # 性能阈值
        self.memory_threshold = 80.0  # 内存使用百分比阈值
        self.cpu_threshold = 80.0     # CPU使用百分比阈值
        self.response_time_threshold = 1.0  # 响应时间阈值（秒）
        
        # 回调函数
        self.alert_callbacks: List[Callable] = []
        
    def start_monitoring(self, interval: float = 5.0):
        """
        开始性能监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self._monitoring:
            return
            
        self._monitor_interval = interval
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"性能监控已启动，间隔: {interval}秒")
        
    def stop_monitoring(self):
        """停止性能监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        logger.info("性能监控已停止")
        
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                
                # 检查阈值
                self._check_thresholds()
                
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                logger.error(f"性能监控错误: {e}")
                time.sleep(self._monitor_interval)
                
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # 内存使用
            memory = psutil.virtual_memory()
            memory_usage = MemoryUsage(
                rss=memory.used,
                vms=memory.total,
                percent=memory.percent,
                available=memory.available
            )
            self.memory_history.append(memory_usage)
            
            # CPU使用
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage = CPUUsage(
                percent=cpu_percent,
                count=psutil.cpu_count()
            )
            self.cpu_history.append(cpu_usage)
            
            # 添加性能指标
            self.add_metric("memory_usage", memory.percent, "%", "system")
            self.add_metric("cpu_usage", cpu_percent, "%", "system")
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            
    def _check_thresholds(self):
        """检查性能阈值"""
        if not self.memory_history or not self.cpu_history:
            return
            
        latest_memory = self.memory_history[-1]
        latest_cpu = self.cpu_history[-1]
        
        # 检查内存阈值
        if latest_memory.percent > self.memory_threshold:
            self._trigger_alert(
                "memory_high",
                f"内存使用率过高: {latest_memory.percent:.1f}%"
            )
            
        # 检查CPU阈值
        if latest_cpu.percent > self.cpu_threshold:
            self._trigger_alert(
                "cpu_high",
                f"CPU使用率过高: {latest_cpu.percent:.1f}%"
            )
            
    def _trigger_alert(self, alert_type: str, message: str):
        """触发性能警报"""
        logger.warning(f"性能警报 [{alert_type}]: {message}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, message)
            except Exception as e:
                logger.error(f"性能警报回调失败: {e}")
                
    def add_metric(self, name: str, value: float, unit: str = "", category: str = "general"):
        """
        添加性能指标
        
        Args:
            name: 指标名称
            value: 指标值
            unit: 单位
            category: 分类
        """
        metric = PerformanceMetric(name, value, unit, category=category)
        self.metrics.append(metric)
        
    def get_metrics(self, category: Optional[str] = None, 
                   since: Optional[datetime] = None) -> List[PerformanceMetric]:
        """
        获取性能指标
        
        Args:
            category: 指标分类过滤
            since: 时间过滤
            
        Returns:
            List[PerformanceMetric]: 性能指标列表
        """
        metrics = list(self.metrics)
        
        if category:
            metrics = [m for m in metrics if m.category == category]
            
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
            
        return metrics
        
    def get_average_metric(self, name: str, 
                          since: Optional[datetime] = None) -> Optional[float]:
        """
        获取指标平均值
        
        Args:
            name: 指标名称
            since: 时间过滤
            
        Returns:
            Optional[float]: 平均值
        """
        metrics = [m for m in self.metrics if m.name == name]
        
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
            
        if not metrics:
            return None
            
        return sum(m.value for m in metrics) / len(metrics)
        
    def get_memory_usage_trend(self, hours: int = 1) -> List[MemoryUsage]:
        """
        获取内存使用趋势
        
        Args:
            hours: 小时数
            
        Returns:
            List[MemoryUsage]: 内存使用历史
        """
        since = datetime.now() - timedelta(hours=hours)
        return [m for m in self.memory_history if m.timestamp >= since]
        
    def get_cpu_usage_trend(self, hours: int = 1) -> List[CPUUsage]:
        """
        获取CPU使用趋势
        
        Args:
            hours: 小时数
            
        Returns:
            List[CPUUsage]: CPU使用历史
        """
        since = datetime.now() - timedelta(hours=hours)
        return [c for c in self.cpu_history if c.timestamp >= since]
        
    def add_alert_callback(self, callback: Callable[[str, str], None]):
        """
        添加警报回调
        
        Args:
            callback: 回调函数，接收(alert_type, message)参数
        """
        self.alert_callbacks.append(callback)
        
    def get_performance_summary(self) -> Dict:
        """
        获取性能摘要
        
        Returns:
            Dict: 性能摘要信息
        """
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        
        summary = {
            "timestamp": now,
            "memory": {
                "current": self.memory_history[-1].percent if self.memory_history else 0,
                "average_1h": self.get_average_metric("memory_usage", last_hour) or 0,
                "peak_1h": max((m.percent for m in self.get_memory_usage_trend(1)), default=0)
            },
            "cpu": {
                "current": self.cpu_history[-1].percent if self.cpu_history else 0,
                "average_1h": self.get_average_metric("cpu_usage", last_hour) or 0,
                "peak_1h": max((c.percent for c in self.get_cpu_usage_trend(1)), default=0)
            },
            "metrics_count": len(self.metrics)
        }
        
        return summary


def performance_timer(category: str = "timing"):
    """
    性能计时装饰器
    
    Args:
        category: 指标分类
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                monitor = get_performance_monitor()
                monitor.add_metric(
                    f"{func.__name__}_time",
                    execution_time,
                    "seconds",
                    category
                )
        return wrapper
    return decorator


def async_performance_timer(category: str = "timing"):
    """
    异步性能计时装饰器
    
    Args:
        category: 指标分类
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                monitor = get_performance_monitor()
                monitor.add_metric(
                    f"{func.__name__}_time",
                    execution_time,
                    "seconds",
                    category
                )
        return wrapper
    return decorator


# 全局性能监控器实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def start_performance_monitoring(interval: float = 5.0):
    """启动性能监控"""
    monitor = get_performance_monitor()
    monitor.start_monitoring(interval)


def stop_performance_monitoring():
    """停止性能监控"""
    monitor = get_performance_monitor()
    monitor.stop_monitoring()

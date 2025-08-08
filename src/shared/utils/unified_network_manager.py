#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一网络连接管理器

整合网络状态检测、自适应超时和重试机制，提供统一的网络管理接口。
"""

import asyncio
import time
import httpx
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from .base_utils import BaseUtility, UtilResult, timed_operation
from .unified_performance import get_performance_manager

import logging
logger = logging.getLogger(__name__)


class NetworkQuality(Enum):
    """网络质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    OFFLINE = "offline"


@dataclass
class NetworkMetrics:
    """网络指标"""
    connected: bool
    latency: Optional[float]
    quality: NetworkQuality
    timestamp: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'connected': self.connected,
            'latency': self.latency,
            'quality': self.quality.value,
            'timestamp': self.timestamp,
            'error': self.error
        }


class UnifiedNetworkManager(BaseUtility):
    """
    统一网络连接管理器
    
    整合网络状态检测、自适应超时和重试机制。
    """
    
    def __init__(self, check_interval: int = 30):
        """
        初始化网络管理器
        
        Args:
            check_interval: 网络状态检查间隔（秒）
        """
        super().__init__("UnifiedNetworkManager")
        
        self.check_interval = check_interval
        self.performance_manager = get_performance_manager()
        
        # 网络状态
        self._last_check_time = 0
        self._last_metrics: Optional[NetworkMetrics] = None
        
        # 自适应超时
        self._success_count = 0
        self._failure_count = 0
        self._current_timeout = 30.0
        self._min_timeout = 10.0
        self._max_timeout = 300.0
        
        # 测试URL列表
        self._test_urls = [
            'https://api.openai.com',
            'https://api.deepseek.com',
            'https://www.google.com',
            'https://www.baidu.com'
        ]
        
        self.logger.info("统一网络管理器初始化完成")
    
    @timed_operation("check_network_status")
    async def check_network_status(self, force_check: bool = False) -> UtilResult[NetworkMetrics]:
        """
        检查网络状态
        
        Args:
            force_check: 是否强制检查（忽略缓存）
            
        Returns:
            UtilResult[NetworkMetrics]: 网络状态检查结果
        """
        current_time = time.time()
        
        # 检查是否需要重新检查
        if (not force_check and 
            self._last_metrics and 
            current_time - self._last_check_time < self.check_interval):
            return UtilResult.success_result(self._last_metrics)
        
        try:
            start_time = time.time()
            connected = False
            latency = None
            error = None
            
            # 测试连接
            async with httpx.AsyncClient(timeout=10.0) as client:
                for url in self._test_urls:
                    try:
                        response = await client.get(url)
                        if response.status_code in [200, 401, 403]:
                            connected = True
                            latency = time.time() - start_time
                            break
                    except Exception:
                        continue
            
            if not connected:
                error = "无法连接到任何测试服务器"
            
            # 确定网络质量
            quality = self._determine_network_quality(connected, latency)
            
            # 创建网络指标
            metrics = NetworkMetrics(
                connected=connected,
                latency=latency,
                quality=quality,
                timestamp=current_time,
                error=error
            )
            
            # 更新缓存
            self._last_check_time = current_time
            self._last_metrics = metrics
            
            # 记录性能指标
            self.performance_manager.record_metric(
                "network_check",
                time.time() - start_time,
                connected
            )
            
            return UtilResult.success_result(metrics)
            
        except Exception as e:
            error_msg = f"网络状态检查失败: {e}"
            self.logger.error(error_msg)
            
            # 创建离线指标
            metrics = NetworkMetrics(
                connected=False,
                latency=None,
                quality=NetworkQuality.OFFLINE,
                timestamp=current_time,
                error=str(e)
            )
            
            return UtilResult.failure_result(error_msg, data=metrics)
    
    def _determine_network_quality(self, connected: bool, latency: Optional[float]) -> NetworkQuality:
        """确定网络质量"""
        if not connected:
            return NetworkQuality.OFFLINE
        
        if latency is None:
            return NetworkQuality.FAIR
        
        if latency < 0.5:
            return NetworkQuality.EXCELLENT
        elif latency < 1.0:
            return NetworkQuality.GOOD
        elif latency < 3.0:
            return NetworkQuality.FAIR
        else:
            return NetworkQuality.POOR
    
    @timed_operation("get_optimal_timeout")
    async def get_optimal_timeout(self) -> UtilResult[float]:
        """
        获取最优超时时间
        
        Returns:
            UtilResult[float]: 推荐的超时时间
        """
        try:
            # 检查网络状态
            status_result = await self.check_network_status()
            
            if status_result.success:
                metrics = status_result.data
                
                if not metrics.connected:
                    timeout = self._max_timeout
                elif metrics.quality == NetworkQuality.EXCELLENT:
                    timeout = 30.0
                elif metrics.quality == NetworkQuality.GOOD:
                    timeout = 60.0
                elif metrics.quality == NetworkQuality.FAIR:
                    timeout = 90.0
                else:  # POOR
                    timeout = 120.0
            else:
                timeout = self._current_timeout
            
            # 应用自适应调整
            timeout = max(self._min_timeout, min(timeout, self._max_timeout))
            
            return UtilResult.success_result(timeout)
            
        except Exception as e:
            return UtilResult.failure_result(f"获取最优超时时间失败: {e}", data=self._current_timeout)
    
    def record_request_success(self) -> None:
        """记录请求成功"""
        self._success_count += 1
        self._failure_count = 0
        
        # 如果连续成功，减少超时时间
        if self._success_count >= 3:
            self._current_timeout = max(
                self._min_timeout,
                self._current_timeout * 0.9
            )
            self._success_count = 0
    
    def record_request_failure(self) -> None:
        """记录请求失败"""
        self._failure_count += 1
        self._success_count = 0
        
        # 如果连续失败，增加超时时间
        if self._failure_count >= 2:
            self._current_timeout = min(
                self._max_timeout,
                self._current_timeout * 1.5
            )
            self.logger.warning(f"网络状况不佳，调整超时时间为: {self._current_timeout:.1f}秒")
    
    @timed_operation("retry_with_backoff")
    async def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ) -> Any:
        """
        带退避的重试机制
        
        Args:
            func: 要重试的函数
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
            
        Returns:
            函数执行结果
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await func()
                self.record_request_success()
                return result
                
            except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.TimeoutException) as e:
                last_exception = e
                self.record_request_failure()
                
                if attempt < max_retries:
                    # 计算延迟时间（指数退避）
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    # 检查网络状况
                    status_result = await self.check_network_status()
                    if status_result.success and not status_result.data.connected:
                        delay *= 2  # 网络不好时延迟更久
                    
                    self.logger.warning(
                        f"请求超时，{delay:.1f}秒后重试 "
                        f"(第{attempt + 1}/{max_retries}次)"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"重试{max_retries}次后仍然超时")
                    break
                    
            except Exception as e:
                # 其他异常不重试
                self.logger.error(f"非超时异常，不重试: {e}")
                raise e
        
        # 所有重试都失败了
        raise last_exception or RuntimeError("重试失败")
    
    def get_network_summary(self) -> Dict[str, Any]:
        """获取网络状态摘要"""
        summary = {
            'last_check': self._last_check_time,
            'current_timeout': self._current_timeout,
            'success_count': self._success_count,
            'failure_count': self._failure_count
        }
        
        if self._last_metrics:
            summary.update(self._last_metrics.to_dict())
        
        return summary
    
    def validate_config(self) -> UtilResult[bool]:
        """验证配置"""
        if self.check_interval <= 0:
            return UtilResult.failure_result("检查间隔必须大于0")
        
        if self._min_timeout >= self._max_timeout:
            return UtilResult.failure_result("最小超时时间必须小于最大超时时间")
        
        return UtilResult.success_result(True)
    
    def cleanup(self) -> UtilResult[bool]:
        """清理资源"""
        self._last_metrics = None
        return UtilResult.success_result(True)


# 全局统一网络管理器实例
_global_network_manager: Optional[UnifiedNetworkManager] = None


def get_network_manager() -> UnifiedNetworkManager:
    """获取全局网络管理器"""
    global _global_network_manager
    if _global_network_manager is None:
        _global_network_manager = UnifiedNetworkManager()
    return _global_network_manager


def set_network_manager(manager: UnifiedNetworkManager) -> None:
    """设置全局网络管理器"""
    global _global_network_manager
    _global_network_manager = manager


# 便捷函数（向后兼容）
async def check_network_connectivity(timeout: float = 10.0) -> Dict[str, Any]:
    """检查网络连接状态（向后兼容）"""
    manager = get_network_manager()
    result = await manager.check_network_status()
    
    if result.success:
        metrics = result.data
        return {
            'connected': metrics.connected,
            'latency': metrics.latency,
            'error': metrics.error,
            'timestamp': metrics.timestamp
        }
    else:
        return {
            'connected': False,
            'latency': None,
            'error': result.error,
            'timestamp': time.time()
        }


async def get_optimal_timeout() -> float:
    """获取最优超时时间（向后兼容）"""
    manager = get_network_manager()
    result = await manager.get_optimal_timeout()
    return result.data if result.success else 30.0


async def retry_with_backoff(func: Callable, max_retries: int = 3) -> Any:
    """带退避的重试机制（向后兼容）"""
    manager = get_network_manager()
    return await manager.retry_with_backoff(func, max_retries)

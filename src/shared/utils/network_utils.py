#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络工具

提供网络连接检测和优化功能
"""

import asyncio
import time
import httpx
from typing import Optional, Dict, Any
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class NetworkStatus:
    """网络状态检测器"""
    
    def __init__(self):
        self.last_check_time = 0
        self.last_status = None
        self.check_interval = 30  # 30秒检查一次
        
    async def check_connectivity(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        检查网络连接状态
        
        Returns:
            Dict包含连接状态信息
        """
        current_time = time.time()
        
        # 如果最近检查过，返回缓存结果
        if (self.last_status and 
            current_time - self.last_check_time < self.check_interval):
            return self.last_status
        
        status = {
            'connected': False,
            'latency': None,
            'error': None,
            'timestamp': current_time
        }
        
        try:
            start_time = time.time()
            
            # 测试连接到常用的AI服务
            test_urls = [
                'https://api.openai.com',
                'https://api.deepseek.com',
                'https://www.google.com'
            ]
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                for url in test_urls:
                    try:
                        response = await client.get(url)
                        if response.status_code in [200, 401, 403]:  # 401/403表示服务可达但需要认证
                            status['connected'] = True
                            status['latency'] = time.time() - start_time
                            break
                    except Exception:
                        continue
            
            if not status['connected']:
                status['error'] = '无法连接到任何测试服务器'
                
        except Exception as e:
            status['error'] = str(e)
            logger.debug(f"网络连接检查失败: {e}")
        
        self.last_check_time = current_time
        self.last_status = status
        
        return status
    
    async def get_optimal_timeout(self) -> float:
        """
        根据网络状况获取最优超时时间
        
        Returns:
            推荐的超时时间（秒）
        """
        status = await self.check_connectivity()
        
        if not status['connected']:
            return 180.0  # 网络不好时使用更长超时
        
        latency = status.get('latency', 1.0)
        
        if latency < 1.0:
            return 60.0   # 网络很好
        elif latency < 3.0:
            return 90.0   # 网络一般
        else:
            return 120.0  # 网络较慢


# 全局网络状态检测器
_network_status = NetworkStatus()


async def check_network_connectivity(timeout: float = 10.0) -> Dict[str, Any]:
    """检查网络连接状态"""
    return await _network_status.check_connectivity(timeout)


async def get_optimal_timeout() -> float:
    """获取最优超时时间"""
    return await _network_status.get_optimal_timeout()


async def test_ai_service_connectivity(base_url: str, timeout: float = 10.0) -> bool:
    """
    测试特定AI服务的连接性
    
    Args:
        base_url: AI服务的基础URL
        timeout: 超时时间
        
    Returns:
        是否可以连接
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(base_url)
            # 200表示正常，401/403表示需要认证但服务可达
            return response.status_code in [200, 401, 403]
    except Exception as e:
        logger.debug(f"测试AI服务连接失败 {base_url}: {e}")
        return False


class AdaptiveTimeout:
    """自适应超时管理器"""
    
    def __init__(self, base_timeout: float = 60.0):
        self.base_timeout = base_timeout
        self.success_count = 0
        self.failure_count = 0
        self.current_timeout = base_timeout
        
    def on_success(self):
        """记录成功"""
        self.success_count += 1
        self.failure_count = max(0, self.failure_count - 1)
        
        # 如果连续成功，可以适当减少超时时间
        if self.success_count >= 3 and self.current_timeout > self.base_timeout:
            self.current_timeout = max(
                self.base_timeout,
                self.current_timeout * 0.9
            )
            logger.debug(f"网络状况良好，调整超时时间为: {self.current_timeout:.1f}秒")
    
    def on_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.success_count = 0
        
        # 如果连续失败，增加超时时间
        if self.failure_count >= 2:
            self.current_timeout = min(
                300.0,  # 最大5分钟
                self.current_timeout * 1.5
            )
            logger.warning(f"网络状况不佳，调整超时时间为: {self.current_timeout:.1f}秒")
    
    def get_timeout(self) -> float:
        """获取当前推荐的超时时间"""
        return self.current_timeout


# 全局自适应超时管理器
_adaptive_timeout = AdaptiveTimeout()


def get_adaptive_timeout() -> float:
    """获取自适应超时时间"""
    return _adaptive_timeout.get_timeout()


def record_request_success():
    """记录请求成功"""
    _adaptive_timeout.on_success()


def record_request_failure():
    """记录请求失败"""
    _adaptive_timeout.on_failure()


async def smart_retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    timeout_multiplier: float = 1.5
):
    """
    智能重试机制，支持自适应超时和退避策略
    
    Args:
        func: 要重试的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        timeout_multiplier: 超时时间倍数
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            result = await func()
            record_request_success()
            return result
            
        except (asyncio.TimeoutError, httpx.ReadTimeout, httpx.TimeoutException) as e:
            last_exception = e
            record_request_failure()
            
            if attempt < max_retries:
                # 计算延迟时间（指数退避）
                delay = min(base_delay * (2 ** attempt), max_delay)
                
                # 检查网络状况
                network_status = await check_network_connectivity(timeout=5.0)
                if not network_status['connected']:
                    delay *= 2  # 网络不好时延迟更久
                
                logger.warning(
                    f"请求超时，{delay:.1f}秒后重试 "
                    f"(第{attempt + 1}/{max_retries}次) "
                    f"网络状态: {'连接' if network_status['connected'] else '断开'}"
                )
                
                await asyncio.sleep(delay)
            else:
                logger.error(f"重试{max_retries}次后仍然超时")
                break
                
        except Exception as e:
            # 其他异常不重试
            logger.error(f"非超时异常，不重试: {e}")
            raise e
    
    # 所有重试都失败了
    if last_exception:
        from src.infrastructure.ai_clients.openai_client import AIRequestTimeoutError
        raise AIRequestTimeoutError(
            f"网络请求超时，已重试{max_retries}次。"
            f"请检查网络连接或稍后重试。"
        )

"""
性能监控器

监控文档加载、渲染和编辑操作的性能指标。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    operation: str
    duration: float
    memory_before: int
    memory_after: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """性能报告"""
    operation_type: str
    total_operations: int
    avg_duration: float
    min_duration: float
    max_duration: float
    p95_duration: float
    avg_memory_usage: int
    max_memory_usage: int
    success_rate: float
    error_count: int


class PerformanceMonitor:
    """
    性能监控器
    
    监控和分析应用程序的性能指标：
    1. 文档加载性能
    2. 内存使用情况
    3. 渲染性能
    4. 用户操作响应时间
    """
    
    def __init__(self):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._active_operations: Dict[str, float] = {}  # 操作ID -> 开始时间
        self._lock = threading.RLock()
        
        # 系统资源监控
        self._process = psutil.Process()
        self._baseline_memory = self._get_memory_usage()
        
        # 性能阈值
        self._performance_thresholds = {
            'document_load': 2.0,      # 文档加载超过2秒为慢
            'render': 0.1,             # 渲染超过100ms为慢
            'save': 1.0,               # 保存超过1秒为慢
            'memory_growth': 100 * 1024 * 1024  # 内存增长超过100MB为异常
        }
        
        logger.info("性能监控器初始化完成")
    
    def start_operation(self, operation_id: str, operation_type: str, metadata: Dict[str, Any] = None) -> str:
        """开始监控操作"""
        try:
            with self._lock:
                start_time = time.time()
                self._active_operations[operation_id] = start_time
                
                logger.debug(f"开始监控操作: {operation_type} ({operation_id})")
                
                return operation_id
                
        except Exception as e:
            logger.error(f"开始监控操作失败: {e}")
            return operation_id
    
    def end_operation(self, operation_id: str, operation_type: str, success: bool = True, metadata: Dict[str, Any] = None) -> Optional[PerformanceMetric]:
        """结束监控操作"""
        try:
            with self._lock:
                if operation_id not in self._active_operations:
                    logger.warning(f"未找到活动操作: {operation_id}")
                    return None
                
                start_time = self._active_operations.pop(operation_id)
                end_time = time.time()
                duration = end_time - start_time
                
                # 获取内存使用情况
                current_memory = self._get_memory_usage()
                
                # 创建性能指标
                metric = PerformanceMetric(
                    operation=operation_type,
                    duration=duration,
                    memory_before=self._baseline_memory,
                    memory_after=current_memory,
                    metadata=metadata or {}
                )
                
                # 添加成功状态
                metric.metadata['success'] = success
                metric.metadata['operation_id'] = operation_id
                
                # 存储指标
                self._metrics[operation_type].append(metric)
                
                # 检查性能阈值
                self._check_performance_threshold(operation_type, metric)
                
                logger.debug(f"操作完成: {operation_type} ({operation_id}), 耗时: {duration:.3f}秒")
                
                return metric
                
        except Exception as e:
            logger.error(f"结束监控操作失败: {e}")
            return None
    
    def _get_memory_usage(self) -> int:
        """获取当前内存使用量"""
        try:
            return self._process.memory_info().rss
        except Exception:
            return 0
    
    def _check_performance_threshold(self, operation_type: str, metric: PerformanceMetric):
        """检查性能阈值"""
        try:
            threshold = self._performance_thresholds.get(operation_type)
            if threshold and metric.duration > threshold:
                logger.warning(f"性能警告: {operation_type} 耗时 {metric.duration:.3f}秒 (阈值: {threshold}秒)")
                
                # 记录性能问题
                self._record_performance_issue(operation_type, metric)
        
        except Exception as e:
            logger.error(f"检查性能阈值失败: {e}")
    
    def _record_performance_issue(self, operation_type: str, metric: PerformanceMetric):
        """记录性能问题"""
        try:
            issue_info = {
                'operation_type': operation_type,
                'duration': metric.duration,
                'memory_usage': metric.memory_after - metric.memory_before,
                'timestamp': metric.timestamp.isoformat(),
                'metadata': metric.metadata
            }
            
            # 这里可以集成到日志系统或监控系统
            logger.warning(f"性能问题记录: {issue_info}")
            
        except Exception as e:
            logger.error(f"记录性能问题失败: {e}")
    
    def get_performance_report(self, operation_type: str, time_range: Optional[timedelta] = None) -> Optional[PerformanceReport]:
        """获取性能报告"""
        try:
            with self._lock:
                metrics = self._metrics.get(operation_type, deque())
                
                if not metrics:
                    return None
                
                # 过滤时间范围
                if time_range:
                    cutoff_time = datetime.now() - time_range
                    filtered_metrics = [m for m in metrics if m.timestamp >= cutoff_time]
                else:
                    filtered_metrics = list(metrics)
                
                if not filtered_metrics:
                    return None
                
                # 计算统计信息
                durations = [m.duration for m in filtered_metrics]
                memory_usages = [m.memory_after - m.memory_before for m in filtered_metrics]
                successful_ops = [m for m in filtered_metrics if m.metadata.get('success', True)]
                
                # 计算百分位数
                sorted_durations = sorted(durations)
                p95_index = int(len(sorted_durations) * 0.95)
                p95_duration = sorted_durations[p95_index] if sorted_durations else 0
                
                return PerformanceReport(
                    operation_type=operation_type,
                    total_operations=len(filtered_metrics),
                    avg_duration=sum(durations) / len(durations),
                    min_duration=min(durations),
                    max_duration=max(durations),
                    p95_duration=p95_duration,
                    avg_memory_usage=sum(memory_usages) / len(memory_usages),
                    max_memory_usage=max(memory_usages),
                    success_rate=len(successful_ops) / len(filtered_metrics),
                    error_count=len(filtered_metrics) - len(successful_ops)
                )
                
        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
            return None
    
    def get_all_reports(self, time_range: Optional[timedelta] = None) -> Dict[str, PerformanceReport]:
        """获取所有操作类型的性能报告"""
        reports = {}
        
        for operation_type in self._metrics.keys():
            report = self.get_performance_report(operation_type, time_range)
            if report:
                reports[operation_type] = report
        
        return reports
    
    def clear_metrics(self, operation_type: Optional[str] = None):
        """清理性能指标"""
        try:
            with self._lock:
                if operation_type:
                    if operation_type in self._metrics:
                        self._metrics[operation_type].clear()
                        logger.info(f"已清理性能指标: {operation_type}")
                else:
                    self._metrics.clear()
                    logger.info("已清理所有性能指标")
        
        except Exception as e:
            logger.error(f"清理性能指标失败: {e}")
    
    def get_current_memory_usage(self) -> Dict[str, int]:
        """获取当前内存使用情况"""
        try:
            memory_info = self._process.memory_info()
            return {
                'rss': memory_info.rss,  # 物理内存
                'vms': memory_info.vms,  # 虚拟内存
                'percent': self._process.memory_percent(),
                'growth': memory_info.rss - self._baseline_memory
            }
        except Exception as e:
            logger.error(f"获取内存使用情况失败: {e}")
            return {}


# 全局性能监控器实例
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# 性能监控装饰器
def monitor_performance(operation_type: str):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            operation_id = f"{operation_type}_{int(time.time() * 1000)}"
            
            # 开始监控
            monitor.start_operation(operation_id, operation_type)
            
            try:
                result = func(*args, **kwargs)
                # 成功结束监控
                monitor.end_operation(operation_id, operation_type, True)
                return result
            except Exception as e:
                # 失败结束监控
                monitor.end_operation(operation_id, operation_type, False, {'error': str(e)})
                raise
        
        return wrapper
    return decorator


# 异步性能监控装饰器
def monitor_async_performance(operation_type: str):
    """异步性能监控装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            operation_id = f"{operation_type}_{int(time.time() * 1000)}"
            
            # 开始监控
            monitor.start_operation(operation_id, operation_type)
            
            try:
                result = await func(*args, **kwargs)
                # 成功结束监控
                monitor.end_operation(operation_id, operation_type, True)
                return result
            except Exception as e:
                # 失败结束监控
                monitor.end_operation(operation_id, operation_type, False, {'error': str(e)})
                raise
        
        return wrapper
    return decorator

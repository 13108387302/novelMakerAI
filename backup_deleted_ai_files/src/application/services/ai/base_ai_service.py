#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务基类

定义AI服务的基础接口和通用功能
"""

import asyncio
from abc import ABC, abstractmethod, ABCMeta
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtCore import QMetaObject, Qt


# 解决QObject和ABC的元类冲突
class QABCMeta(type(QObject), ABCMeta):
    """兼容QObject和ABC的元类"""
    pass

from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.domain.events.ai_events import (
    AIRequestStartedEvent, AIRequestCompletedEvent, AIRequestFailedEvent
)
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import ApplicationError

logger = get_logger(__name__)


class AIServiceError(ApplicationError):
    """
    AI服务错误基类

    所有AI服务相关错误的基类，继承自ApplicationError。
    用于标识AI服务层的各种错误情况。
    """
    pass


class IAIService(ABC):
    """AI服务接口"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, context: str = "") -> str:
        """生成文本"""
        pass
        
    @abstractmethod
    async def generate_text_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """流式生成文本"""
        pass
        
    @abstractmethod
    async def check_service_availability(self) -> bool:
        """检查服务可用性"""
        pass
        
    @abstractmethod
    def get_supported_features(self) -> list[str]:
        """获取支持的功能"""
        pass


class BaseAIService(QObject, IAIService, metaclass=QABCMeta):
    """AI服务基类"""
    
    # 基础信号
    request_started = pyqtSignal(str)  # 请求ID
    request_completed = pyqtSignal(str, str)  # 请求ID, 响应内容
    request_failed = pyqtSignal(str, str)  # 请求ID, 错误信息
    
    def __init__(
        self,
        ai_repository: IAIServiceRepository,
        event_bus: EventBus
    ):
        super().__init__()
        self.ai_repository = ai_repository
        self.event_bus = event_bus

        # 请求管理
        self._request_counter = 0
        self._active_requests: Dict[str, Dict[str, Any]] = {}

        # 最大请求历史数量
        self._max_request_history = 100
        
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        self._request_counter += 1
        return f"ai_request_{self._request_counter}_{int(datetime.now().timestamp())}"

    def _update_request_status(self, request_id: str, status: str, **kwargs) -> None:
        """更新请求状态"""
        if request_id in self._active_requests:
            self._active_requests[request_id]["status"] = status
            self._active_requests[request_id]["end_time"] = datetime.now()
            for key, value in kwargs.items():
                self._active_requests[request_id][key] = value

    def _publish_event_safe(self, event) -> None:
        """安全发布事件（非阻塞）"""
        try:
            # 使用QTimer.singleShot在主线程中异步发布事件
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._do_publish_event(event))
        except Exception as e:
            logger.warning(f"事件发布失败: {e}")

    @pyqtSlot(object)
    def _do_publish_event(self, event) -> None:
        """实际发布事件的方法"""
        try:
            if not self.event_bus:
                logger.debug("事件总线未初始化，跳过事件发布")
                return

            # 检查是否有运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 创建异步任务来发布事件
                asyncio.create_task(self.event_bus.publish(event))
            except RuntimeError:
                # 没有运行的事件循环，尝试创建新的事件循环
                try:
                    asyncio.run(self.event_bus.publish(event))
                except Exception as e:
                    logger.debug(f"同步事件发布失败: {e}")
        except Exception as e:
            logger.warning(f"异步事件发布失败: {e}")
        
    async def _execute_request(self, request_id: str, prompt: str, context: str = "") -> str:
        """执行AI请求的通用逻辑"""
        try:
            # 记录请求开始
            self._active_requests[request_id] = {
                "prompt": prompt,
                "context": context,
                "start_time": datetime.now(),
                "status": "running"
            }
            
            # 发出信号和事件
            self.request_started.emit(request_id)
            self._publish_event_safe(AIRequestStartedEvent(
                request_id=request_id,
                request_type="text_generation",
                timestamp=datetime.now()
            ))
            
            # 调用具体的AI实现
            response = await self._do_generate_text(prompt, context)
            
            # 记录请求完成
            self._update_request_status(request_id, "completed", response=response)

            # 发出信号和事件
            self.request_completed.emit(request_id, response)
            self._publish_event_safe(AIRequestCompletedEvent(
                request_id=request_id,
                request_type="text_generation",
                timestamp=datetime.now()
            ))
            
            return response
            
        except Exception as e:
            # 记录请求失败
            error_msg = str(e)
            self._update_request_status(request_id, "failed", error=error_msg)

            # 发出信号和事件
            self.request_failed.emit(request_id, error_msg)
            self._publish_event_safe(AIRequestFailedEvent(
                request_id=request_id,
                request_type="text_generation",
                error_message=error_msg,
                timestamp=datetime.now()
            ))

            raise

        finally:
            # 清理完成的请求（保留最近的请求）
            self._cleanup_old_requests()

    def _cleanup_old_requests(self) -> None:
        """清理旧的请求记录"""
        if len(self._active_requests) > self._max_request_history:
            # 按开始时间排序，删除最旧的请求
            sorted_requests = sorted(
                self._active_requests.items(),
                key=lambda x: x[1].get("start_time", datetime.min)
            )
            # 保留最新的请求，删除多余的
            requests_to_delete = sorted_requests[:len(self._active_requests) - self._max_request_history]
            for req_id, _ in requests_to_delete:
                del self._active_requests[req_id]
    
    @abstractmethod
    async def _do_generate_text(self, prompt: str, context: str = "") -> str:
        """具体的文本生成实现 - 子类必须实现"""
        pass
        
    async def generate_text(self, prompt: str, context: str = "") -> str:
        """生成文本"""
        request_id = self._generate_request_id()
        return await self._execute_request(request_id, prompt, context)
        
    async def generate_text_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """流式生成文本 - 默认实现，子类可以重写"""
        response = await self.generate_text(prompt, context)
        
        # 模拟流式输出
        words = response.split()
        for i, word in enumerate(words):
            if i == 0:
                yield word
            else:
                yield " " + word
            await asyncio.sleep(0.01)  # 小延迟模拟流式效果
            
    async def check_service_availability(self) -> bool:
        """检查AI服务可用性"""
        try:
            # 检查AI仓库是否有可用的方法
            if hasattr(self.ai_repository, 'is_available'):
                return await self.ai_repository.is_available()
            elif hasattr(self.ai_repository, 'get_available_clients'):
                clients = await self.ai_repository.get_available_clients()
                return len(clients) > 0
            else:
                # 尝试简单的测试请求
                test_response = await self._do_generate_text("测试", "")
                return bool(test_response)
        except Exception as e:
            logger.error(f"AI服务可用性检查失败: {e}")
            return False
            
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃的请求"""
        return {
            req_id: req_info for req_id, req_info in self._active_requests.items()
            if req_info.get("status") == "running"
        }
        
    def get_request_history(self, limit: int = 50) -> Dict[str, Dict[str, Any]]:
        """获取请求历史"""
        sorted_requests = sorted(
            self._active_requests.items(),
            key=lambda x: x[1].get("start_time", datetime.min),
            reverse=True
        )
        return dict(sorted_requests[:limit])
        
    def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        if request_id in self._active_requests:
            request_info = self._active_requests[request_id]
            if request_info.get("status") == "running":
                request_info["status"] = "cancelled"
                request_info["end_time"] = datetime.now()
                return True
        return False
        
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        total_requests = len(self._active_requests)
        completed_requests = sum(1 for req in self._active_requests.values() if req.get("status") == "completed")
        failed_requests = sum(1 for req in self._active_requests.values() if req.get("status") == "failed")
        running_requests = sum(1 for req in self._active_requests.values() if req.get("status") == "running")
        
        # 计算平均响应时间
        completed_with_time = [
            req for req in self._active_requests.values()
            if req.get("status") == "completed" and "start_time" in req and "end_time" in req
        ]
        
        avg_response_time = 0
        if completed_with_time:
            total_time = sum(
                (req["end_time"] - req["start_time"]).total_seconds()
                for req in completed_with_time
            )
            avg_response_time = total_time / len(completed_with_time)
        
        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "failed_requests": failed_requests,
            "running_requests": running_requests,
            "success_rate": completed_requests / total_requests if total_requests > 0 else 0,
            "average_response_time": avg_response_time
        }
        
    def get_supported_features(self) -> list[str]:
        """获取支持的功能 - 基础功能"""
        return [
            "text_generation",
            "availability_check",
            "usage_statistics",
            "request_management"
        ]




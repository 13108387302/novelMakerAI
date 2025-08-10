#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI控制器

专门处理AI相关的UI操作和业务逻辑
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal

from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService
from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse
from src.shared.utils.base_service import BaseService

logger = logging.getLogger(__name__)


class AIController(BaseService, QObject):
    """
    AI控制器
    
    专门处理AI相关的操作，从主控制器中分离出来。
    负责AI请求的处理、响应管理和UI交互。
    
    重构改进：
    - 单一职责：只处理AI相关操作
    - 减少主控制器的复杂度
    - 提供清晰的AI操作接口
    - 统一的AI请求处理机制
    """
    
    # 信号定义
    ai_response_received = pyqtSignal(object)  # AI响应接收
    ai_error_occurred = pyqtSignal(str)  # AI错误发生
    ai_processing_started = pyqtSignal()  # AI处理开始
    ai_processing_finished = pyqtSignal()  # AI处理完成
    status_message = pyqtSignal(str)  # 状态消息
    
    def __init__(self, ai_service: AIOrchestrationService):
        """
        初始化AI控制器
        
        Args:
            ai_service: AI编排服务
        """
        QObject.__init__(self)
        BaseService.__init__(self, "AIController")
        
        self.ai_service = ai_service
        self._is_processing = False
    
    async def process_ai_request(
        self,
        prompt: str,
        context: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        use_streaming: bool = False,
        preferred_provider: Optional[str] = None
    ) -> Optional[AIResponse]:
        """
        处理AI请求
        
        Args:
            prompt: 提示词
            context: 上下文
            parameters: 请求参数
            use_streaming: 是否使用流式输出
            preferred_provider: 首选提供商
            
        Returns:
            Optional[AIResponse]: AI响应
        """
        if self._is_processing:
            self.logger.warning("正在处理其他AI请求，无法处理新请求")
            return None
        
        self._is_processing = True
        self.ai_processing_started.emit()
        
        try:
            self.status_message.emit("正在处理AI请求...")
            
            # 创建AI请求
            from src.domain.ai.value_objects.ai_request_type import AIRequestType
            ai_request = AIRequest(
                request_type=AIRequestType.TEXT_GENERATION,
                prompt=prompt,
                context=context,
                parameters=parameters or {}
            )
            
            # 处理请求
            response = await self.ai_service.process_request(
                request=ai_request,
                use_streaming=use_streaming,
                preferred_provider=preferred_provider
            )
            
            if response and response.is_successful:
                self.ai_response_received.emit(response)
                self.status_message.emit("AI请求处理完成")
                self.logger.info("AI请求处理成功")
                return response
            else:
                error_msg = response.error if response else "AI请求处理失败"
                self.ai_error_occurred.emit(error_msg)
                self.status_message.emit(f"AI请求失败: {error_msg}")
                self.logger.error(f"AI请求处理失败: {error_msg}")
                return None
                
        except Exception as e:
            error_msg = str(e)
            self.ai_error_occurred.emit(error_msg)
            self.status_message.emit(f"AI请求异常: {error_msg}")
            self.logger.error(f"AI请求处理异常: {e}")
            return None
        finally:
            self._is_processing = False
            self.ai_processing_finished.emit()
    
    async def process_ai_request_stream(
        self,
        prompt: str,
        context: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        preferred_provider: Optional[str] = None
    ):
        """
        流式处理AI请求
        
        Args:
            prompt: 提示词
            context: 上下文
            parameters: 请求参数
            preferred_provider: 首选提供商
            
        Yields:
            str: 响应文本块
        """
        if self._is_processing:
            self.logger.warning("正在处理其他AI请求，无法处理新请求")
            return
        
        self._is_processing = True
        self.ai_processing_started.emit()
        
        try:
            self.status_message.emit("正在流式处理AI请求...")
            
            # 创建AI请求
            from src.domain.ai.value_objects.ai_request_type import AIRequestType
            ai_request = AIRequest(
                request_type=AIRequestType.TEXT_GENERATION,
                prompt=prompt,
                context=context,
                parameters=parameters or {}
            )
            
            # 流式处理
            async for chunk in self.ai_service.process_request_stream(
                request=ai_request,
                preferred_provider=preferred_provider
            ):
                yield chunk
            
            self.status_message.emit("AI流式处理完成")
            self.logger.info("AI流式处理成功")
            
        except Exception as e:
            error_msg = str(e)
            self.ai_error_occurred.emit(error_msg)
            self.status_message.emit(f"AI流式处理异常: {error_msg}")
            self.logger.error(f"AI流式处理异常: {e}")
        finally:
            self._is_processing = False
            self.ai_processing_finished.emit()
    
    async def get_available_providers(self) -> List[str]:
        """
        获取可用的AI提供商
        
        Returns:
            List[str]: 可用提供商列表
        """
        try:
            providers = await self.ai_service.get_available_providers()
            self.logger.info(f"获取到 {len(providers)} 个可用提供商")
            return providers
        except Exception as e:
            self.logger.error(f"获取可用提供商失败: {e}")
            return []
    
    def show_ai_panel(self, panel_type: str = "global") -> None:
        """
        显示AI面板
        
        Args:
            panel_type: 面板类型（global, document等）
        """
        try:
            # 这里可以添加显示AI面板的逻辑
            # 具体实现依赖于主窗口的AI面板组件
            self.status_message.emit(f"显示AI面板: {panel_type}")
            self.logger.info(f"显示AI面板: {panel_type}")
        except Exception as e:
            self.logger.error(f"显示AI面板失败: {e}")
    
    def analyze_characters(self) -> None:
        """AI角色分析"""
        try:
            # 这里可以添加角色分析的逻辑
            self.status_message.emit("开始AI角色分析")
            self.logger.info("开始AI角色分析")
        except Exception as e:
            self.logger.error(f"AI角色分析失败: {e}")
    
    def analyze_plot(self) -> None:
        """AI情节分析"""
        try:
            # 这里可以添加情节分析的逻辑
            self.status_message.emit("开始AI情节分析")
            self.logger.info("开始AI情节分析")
        except Exception as e:
            self.logger.error(f"AI情节分析失败: {e}")
    
    def analyze_style(self) -> None:
        """AI风格分析"""
        try:
            # 这里可以添加风格分析的逻辑
            self.status_message.emit("开始AI风格分析")
            self.logger.info("开始AI风格分析")
        except Exception as e:
            self.logger.error(f"AI风格分析失败: {e}")
    
    @property
    def is_processing(self) -> bool:
        """是否正在处理AI请求"""
        return self._is_processing
    
    @property
    def service_statistics(self) -> Dict[str, Any]:
        """获取AI服务统计信息"""
        try:
            return self.ai_service.get_statistics()
        except Exception as e:
            self.logger.error(f"获取AI服务统计失败: {e}")
            return {}

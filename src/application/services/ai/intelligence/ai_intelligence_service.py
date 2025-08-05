#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能化服务

负责实现AI功能的智能化操作，支持100%智能化功能
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.domain.ai.entities.ai_request import AIRequest
from src.domain.ai.entities.ai_response import AIResponse
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode
from src.domain.ai.value_objects.ai_request_type import AIRequestType
from src.domain.ai.value_objects.ai_priority import AIPriority

logger = logging.getLogger(__name__)


@dataclass
class AIFunctionMetadata:
    """AI功能元数据"""
    id: str
    name: str
    description: str
    category: str
    icon: str
    tooltip: str
    
    # 智能化配置
    execution_mode: AIExecutionMode
    min_context_length: int = 0
    supports_streaming: bool = True
    estimated_time: int = 10
    
    # 功能配置
    requires_input: bool = False
    requires_context: bool = True
    smart_description: str = ""


class AIIntelligentFunction:
    """
    AI智能化功能
    
    封装AI功能的智能化逻辑和行为
    """
    
    def __init__(self, metadata: AIFunctionMetadata):
        """
        初始化AI智能化功能
        
        Args:
            metadata: 功能元数据
        """
        self.metadata = metadata
        self.request_count = 0
        self.success_count = 0
        self.total_processing_time = 0.0
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """
        检查是否可以智能化执行
        
        Args:
            context: 上下文内容
            selected_text: 选中的文字
            
        Returns:
            bool: 是否可以智能化执行
        """
        return self.metadata.execution_mode.can_execute_with(context, selected_text)
    
    def build_auto_request(
        self,
        context: str = "",
        selected_text: str = "",
        parameters: Dict[str, Any] = None
    ) -> Optional[AIRequest]:
        """
        构建智能化AI请求
        
        Args:
            context: 上下文内容
            selected_text: 选中的文字
            parameters: 额外参数
            
        Returns:
            Optional[AIRequest]: AI请求，如果无法构建则返回None
        """
        if not self.can_auto_execute(context, selected_text):
            return None
        
        # 获取输入内容
        input_text = self.metadata.execution_mode.get_input_source(context, selected_text)
        
        # 构建智能化提示词
        prompt = self._build_intelligent_prompt(input_text, context, selected_text)
        
        # 创建请求
        request = AIRequest(
            prompt=prompt,
            context=context,
            request_type=self._get_request_type(),
            execution_mode=self.metadata.execution_mode,
            priority=AIPriority.NORMAL,
            parameters=parameters or {},
            is_streaming=self.metadata.supports_streaming
        )
        
        # 添加功能元数据
        request.add_metadata("function_id", self.metadata.id)
        request.add_metadata("function_name", self.metadata.name)
        request.add_metadata("execution_mode", self.metadata.execution_mode.value)
        
        return request
    
    def _build_intelligent_prompt(
        self,
        input_text: str,
        context: str,
        selected_text: str
    ) -> str:
        """
        构建智能化提示词
        
        Args:
            input_text: 输入文本
            context: 上下文
            selected_text: 选中文字
            
        Returns:
            str: 智能化提示词
        """
        # 子类应该重写此方法以提供特定的提示词逻辑
        return self._get_default_prompt_template().format(
            input_text=input_text,
            context=context,
            selected_text=selected_text
        )
    
    def _get_default_prompt_template(self) -> str:
        """获取默认提示词模板"""
        return "请处理以下内容：\n{input_text}"
    
    def _get_request_type(self) -> AIRequestType:
        """获取请求类型"""
        # 根据功能类别映射到请求类型
        category_mapping = {
            "generation": AIRequestType.TEXT_GENERATION,
            "optimization": AIRequestType.TEXT_OPTIMIZATION,
            "analysis": AIRequestType.TEXT_ANALYSIS,
            "summarization": AIRequestType.TEXT_SUMMARIZATION,
            "translation": AIRequestType.TRANSLATION,
            "conversation": AIRequestType.CONVERSATION,
            "inspiration": AIRequestType.WRITING_INSPIRATION
        }
        return category_mapping.get(self.metadata.category, AIRequestType.TEXT_GENERATION)
    
    def update_statistics(self, processing_time: float, success: bool) -> None:
        """
        更新统计信息
        
        Args:
            processing_time: 处理时间
            success: 是否成功
        """
        self.request_count += 1
        self.total_processing_time += processing_time
        if success:
            self.success_count += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_time = (
            self.total_processing_time / self.request_count 
            if self.request_count > 0 else 0.0
        )
        success_rate = (
            self.success_count / self.request_count 
            if self.request_count > 0 else 0.0
        )
        
        return {
            'function_id': self.metadata.id,
            'function_name': self.metadata.name,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'success_rate': success_rate,
            'average_processing_time': avg_time,
            'execution_mode': self.metadata.execution_mode.value,
            'is_intelligent': self.metadata.execution_mode.is_intelligent
        }


class AIIntelligenceService:
    """
    AI智能化服务
    
    管理和协调AI功能的智能化操作
    """
    
    def __init__(self):
        """初始化AI智能化服务"""
        self.functions: Dict[str, AIIntelligentFunction] = {}
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """
        初始化服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 注册内置的智能化功能
            self._register_builtin_functions()
            
            self.is_initialized = True
            logger.info("AI智能化服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"AI智能化服务初始化失败: {e}")
            return False
    
    def register_function(self, function: AIIntelligentFunction) -> None:
        """
        注册AI智能化功能
        
        Args:
            function: AI智能化功能
        """
        self.functions[function.metadata.id] = function
        logger.info(f"注册AI智能化功能: {function.metadata.name}")
    
    def get_function(self, function_id: str) -> Optional[AIIntelligentFunction]:
        """
        获取AI智能化功能
        
        Args:
            function_id: 功能ID
            
        Returns:
            Optional[AIIntelligentFunction]: AI智能化功能
        """
        return self.functions.get(function_id)
    
    def get_all_functions(self) -> List[AIIntelligentFunction]:
        """
        获取所有AI智能化功能
        
        Returns:
            List[AIIntelligentFunction]: 所有功能列表
        """
        return list(self.functions.values())
    
    def get_functions_by_category(self, category: str) -> List[AIIntelligentFunction]:
        """
        根据类别获取AI智能化功能
        
        Args:
            category: 功能类别
            
        Returns:
            List[AIIntelligentFunction]: 功能列表
        """
        return [
            func for func in self.functions.values()
            if func.metadata.category == category
        ]
    
    def get_intelligent_functions(self) -> List[AIIntelligentFunction]:
        """
        获取所有智能化功能
        
        Returns:
            List[AIIntelligentFunction]: 智能化功能列表
        """
        return [
            func for func in self.functions.values()
            if func.metadata.execution_mode.is_intelligent
        ]
    
    def calculate_intelligence_score(self) -> float:
        """
        计算整体智能化程度
        
        Returns:
            float: 智能化程度（0-1）
        """
        if not self.functions:
            return 0.0
        
        intelligent_count = len(self.get_intelligent_functions())
        total_count = len(self.functions)
        
        return intelligent_count / total_count
    
    def get_intelligence_report(self) -> Dict[str, Any]:
        """
        获取智能化报告
        
        Returns:
            Dict[str, Any]: 智能化报告
        """
        all_functions = self.get_all_functions()
        intelligent_functions = self.get_intelligent_functions()
        
        # 按执行模式分组
        mode_stats = {}
        for func in all_functions:
            mode = func.metadata.execution_mode.value
            if mode not in mode_stats:
                mode_stats[mode] = 0
            mode_stats[mode] += 1
        
        return {
            'total_functions': len(all_functions),
            'intelligent_functions': len(intelligent_functions),
            'intelligence_score': self.calculate_intelligence_score(),
            'intelligence_percentage': self.calculate_intelligence_score() * 100,
            'execution_mode_distribution': mode_stats,
            'function_statistics': [func.get_statistics() for func in all_functions]
        }
    
    def _register_builtin_functions(self) -> None:
        """注册内置的智能化功能"""
        # 这里可以注册内置的智能化功能
        # 实际的功能注册将在具体的功能模块中进行
        pass

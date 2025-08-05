#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务仓储接口

定义AI服务数据访问的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime


class IAIServiceRepository(ABC):
    """
    AI服务仓储接口

    定义AI服务数据访问的抽象接口，封装与AI服务提供商的交互。
    提供文本生成、分析和其他AI功能的统一接口。

    实现方式：
    - 使用抽象基类定义接口契约
    - 支持多种AI服务提供商
    - 提供同步和异步生成模式
    - 支持流式响应和批量处理
    - 包含完整的参数配置选项
    """

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        生成文本内容

        Args:
            prompt: 提示词
            context: 上下文信息
            max_tokens: 最大令牌数
            temperature: 生成温度（0.0-2.0）
            model: 指定模型名称

        Returns:
            str: 生成的文本内容
        """
        pass

    @abstractmethod
    async def generate_text_stream(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成文本内容

        Args:
            prompt: 提示词
            context: 上下文信息
            max_tokens: 最大令牌数
            temperature: 生成温度（0.0-2.0）
            model: 指定模型名称

        Yields:
            str: 生成的文本片段
        """
        pass

    @abstractmethod
    async def analyze_text(
        self,
        text: str,
        analysis_type: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析文本内容

        Args:
            text: 要分析的文本
            analysis_type: 分析类型（sentiment/style/structure等）
            model: 指定模型名称

        Returns:
            Dict[str, Any]: 分析结果字典
        """
        pass
    
    @abstractmethod
    async def improve_text(
        self, 
        text: str, 
        improvement_type: str,
        instructions: str = "",
        model: Optional[str] = None
    ) -> str:
        """改进文本"""
        pass
    
    @abstractmethod
    async def check_availability(self, provider: str) -> bool:
        """检查AI服务可用性"""
        pass
    
    @abstractmethod
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    async def list_available_models(self, provider: str) -> List[str]:
        """列出可用模型"""
        pass


class IAIRequestRepository(ABC):
    """AI请求仓储接口"""
    
    @abstractmethod
    async def save_request(
        self, 
        request_id: str, 
        request_data: Dict[str, Any]
    ) -> bool:
        """保存AI请求记录"""
        pass
    
    @abstractmethod
    async def load_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """加载AI请求记录"""
        pass
    
    @abstractmethod
    async def list_requests(
        self, 
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出AI请求记录"""
        pass
    
    @abstractmethod
    async def get_request_statistics(
        self, 
        user_id: Optional[str] = None,
        period: str = "daily"
    ) -> Dict[str, Any]:
        """获取请求统计信息"""
        pass
    
    @abstractmethod
    async def delete_old_requests(self, days: int = 30) -> int:
        """删除旧的请求记录"""
        pass


class IAIPromptRepository(ABC):
    """AI提示词仓储接口"""
    
    @abstractmethod
    async def save_prompt_template(
        self, 
        template_id: str, 
        template_data: Dict[str, Any]
    ) -> bool:
        """保存提示词模板"""
        pass
    
    @abstractmethod
    async def load_prompt_template(
        self, 
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """加载提示词模板"""
        pass
    
    @abstractmethod
    async def list_prompt_templates(
        self, 
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出提示词模板"""
        pass
    
    @abstractmethod
    async def delete_prompt_template(self, template_id: str) -> bool:
        """删除提示词模板"""
        pass
    
    @abstractmethod
    async def render_prompt(
        self, 
        template_id: str, 
        variables: Dict[str, str]
    ) -> str:
        """渲染提示词"""
        pass


class IAIResponseCacheRepository(ABC):
    """AI响应缓存仓储接口"""
    
    @abstractmethod
    async def get_cached_response(
        self, 
        prompt_hash: str
    ) -> Optional[str]:
        """获取缓存的响应"""
        pass
    
    @abstractmethod
    async def cache_response(
        self, 
        prompt_hash: str, 
        response: str,
        ttl: int = 3600
    ) -> bool:
        """缓存响应"""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, prompt_hash: str) -> bool:
        """使缓存失效"""
        pass
    
    @abstractmethod
    async def clear_cache(self) -> bool:
        """清空缓存"""
        pass
    
    @abstractmethod
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        pass


class IAIUsageRepository(ABC):
    """AI使用统计仓储接口"""
    
    @abstractmethod
    async def record_usage(
        self, 
        user_id: Optional[str],
        provider: str,
        model: str,
        tokens_used: int,
        cost: float,
        request_type: str
    ) -> bool:
        """记录使用情况"""
        pass
    
    @abstractmethod
    async def get_usage_statistics(
        self, 
        user_id: Optional[str] = None,
        period: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取使用统计"""
        pass
    
    @abstractmethod
    async def get_cost_breakdown(
        self, 
        user_id: Optional[str] = None,
        period: str = "monthly"
    ) -> Dict[str, Any]:
        """获取成本分解"""
        pass
    
    @abstractmethod
    async def check_usage_limits(
        self, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """检查使用限制"""
        pass
    
    @abstractmethod
    async def reset_usage_counters(
        self, 
        user_id: Optional[str] = None,
        period: str = "monthly"
    ) -> bool:
        """重置使用计数器"""
        pass


class IAIFeedbackRepository(ABC):
    """AI反馈仓储接口"""
    
    @abstractmethod
    async def save_feedback(
        self, 
        feedback_id: str, 
        feedback_data: Dict[str, Any]
    ) -> bool:
        """保存反馈"""
        pass
    
    @abstractmethod
    async def load_feedback(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        """加载反馈"""
        pass
    
    @abstractmethod
    async def list_feedback(
        self, 
        request_id: Optional[str] = None,
        feedback_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出反馈"""
        pass
    
    @abstractmethod
    async def get_feedback_statistics(self) -> Dict[str, Any]:
        """获取反馈统计"""
        pass
    
    @abstractmethod
    async def delete_feedback(self, feedback_id: str) -> bool:
        """删除反馈"""
        pass


class IAIConfigRepository(ABC):
    """AI配置仓储接口"""
    
    @abstractmethod
    async def save_config(
        self, 
        user_id: Optional[str], 
        config: Dict[str, Any]
    ) -> bool:
        """保存AI配置"""
        pass
    
    @abstractmethod
    async def load_config(
        self, 
        user_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """加载AI配置"""
        pass
    
    @abstractmethod
    async def update_config(
        self, 
        user_id: Optional[str], 
        key: str, 
        value: Any
    ) -> bool:
        """更新配置项"""
        pass
    
    @abstractmethod
    async def delete_config(self, user_id: Optional[str]) -> bool:
        """删除配置"""
        pass
    
    @abstractmethod
    async def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        pass

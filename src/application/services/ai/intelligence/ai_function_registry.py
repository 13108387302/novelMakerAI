#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI功能注册表

管理和注册所有AI智能化功能模块
"""

import logging
from typing import Dict, Any, Optional, List, Type
from enum import Enum

from .ai_intelligence_service import AIIntelligentFunction, AIFunctionMetadata
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode

logger = logging.getLogger(__name__)


class AIFunctionCategory(Enum):
    """AI功能分类"""
    GENERATION = "generation"        # 生成类
    OPTIMIZATION = "optimization"    # 优化类
    ANALYSIS = "analysis"           # 分析类
    SUMMARIZATION = "summarization" # 总结类
    TRANSLATION = "translation"     # 翻译类
    CONVERSATION = "conversation"    # 对话类
    INSPIRATION = "inspiration"      # 灵感类


class AIFunctionRegistry:
    """
    AI功能注册表
    
    单例模式，管理所有AI智能化功能的注册和访问
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.functions: Dict[str, AIIntelligentFunction] = {}
            self.categories: Dict[str, List[str]] = {}
            self._initialized = True
    
    def register_function(
        self,
        function_id: str,
        function_class: Type[AIIntelligentFunction],
        metadata: AIFunctionMetadata
    ) -> None:
        """
        注册AI功能
        
        Args:
            function_id: 功能ID
            function_class: 功能类
            metadata: 功能元数据
        """
        try:
            # 创建功能实例
            function = function_class(metadata)
            
            # 注册功能
            self.functions[function_id] = function
            
            # 更新分类索引
            category = metadata.category
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(function_id)
            
            logger.info(f"注册AI功能: {metadata.name} ({function_id})")
            
        except Exception as e:
            logger.error(f"注册AI功能失败: {function_id}, 错误: {e}")
            raise
    
    def get_function(self, function_id: str) -> Optional[AIIntelligentFunction]:
        """
        获取AI功能
        
        Args:
            function_id: 功能ID
            
        Returns:
            Optional[AIIntelligentFunction]: AI功能实例
        """
        return self.functions.get(function_id)
    
    def get_all_functions(self) -> Dict[str, AIIntelligentFunction]:
        """
        获取所有AI功能
        
        Returns:
            Dict[str, AIIntelligentFunction]: 所有功能字典
        """
        return self.functions.copy()
    
    def get_functions_by_category(self, category: str) -> List[AIIntelligentFunction]:
        """
        根据分类获取AI功能
        
        Args:
            category: 功能分类
            
        Returns:
            List[AIIntelligentFunction]: 功能列表
        """
        function_ids = self.categories.get(category, [])
        return [self.functions[fid] for fid in function_ids if fid in self.functions]
    
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
    
    def get_auto_functions(self) -> List[AIIntelligentFunction]:
        """
        获取所有自动执行功能
        
        Returns:
            List[AIIntelligentFunction]: 自动执行功能列表
        """
        return [
            func for func in self.functions.values()
            if func.metadata.execution_mode.is_automatic
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
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        all_functions = list(self.functions.values())
        intelligent_functions = self.get_intelligent_functions()
        auto_functions = self.get_auto_functions()
        
        # 按执行模式分组统计
        mode_stats = {}
        for func in all_functions:
            mode = func.metadata.execution_mode.value
            mode_stats[mode] = mode_stats.get(mode, 0) + 1
        
        # 按分类统计
        category_stats = {}
        for category, function_ids in self.categories.items():
            category_stats[category] = len(function_ids)
        
        return {
            'total_functions': len(all_functions),
            'intelligent_functions': len(intelligent_functions),
            'auto_functions': len(auto_functions),
            'intelligence_score': self.calculate_intelligence_score(),
            'intelligence_percentage': self.calculate_intelligence_score() * 100,
            'execution_mode_distribution': mode_stats,
            'category_distribution': category_stats,
            'available_categories': list(self.categories.keys())
        }
    
    def clear_registry(self) -> None:
        """清空注册表"""
        self.functions.clear()
        self.categories.clear()
        logger.info("AI功能注册表已清空")
    
    def is_function_registered(self, function_id: str) -> bool:
        """
        检查功能是否已注册
        
        Args:
            function_id: 功能ID
            
        Returns:
            bool: 是否已注册
        """
        return function_id in self.functions


# 全局注册表实例
ai_function_registry = AIFunctionRegistry()


# 便捷的注册装饰器
def register_ai_function(
    function_id: str,
    name: str,
    description: str,
    category: AIFunctionCategory,
    execution_mode: AIExecutionMode,
    icon: str = "🤖",
    tooltip: str = "",
    min_context_length: int = 0,
    supports_streaming: bool = True,
    estimated_time: int = 10,
    smart_description: str = ""
):
    """
    AI功能注册装饰器
    
    Args:
        function_id: 功能ID
        name: 功能名称
        description: 功能描述
        category: 功能分类
        execution_mode: 执行模式
        icon: 图标
        tooltip: 提示文字
        min_context_length: 最小上下文长度
        supports_streaming: 是否支持流式输出
        estimated_time: 预估时间
        smart_description: 智能化描述
    """
    def decorator(cls: Type[AIIntelligentFunction]):
        metadata = AIFunctionMetadata(
            id=function_id,
            name=name,
            description=description,
            category=category.value,
            icon=icon,
            tooltip=tooltip,
            execution_mode=execution_mode,
            min_context_length=min_context_length,
            supports_streaming=supports_streaming,
            estimated_time=estimated_time,
            requires_input=not execution_mode.is_intelligent,
            requires_context=execution_mode.requires_context,
            smart_description=smart_description
        )
        
        # 注册功能
        ai_function_registry.register_function(function_id, cls, metadata)
        
        return cls
    
    return decorator


# 便捷的获取函数
def get_function(function_id: str) -> Optional[AIIntelligentFunction]:
    """获取AI功能"""
    return ai_function_registry.get_function(function_id)


def get_all_functions() -> Dict[str, AIIntelligentFunction]:
    """获取所有AI功能"""
    return ai_function_registry.get_all_functions()


def get_intelligent_functions() -> List[AIIntelligentFunction]:
    """获取所有智能化功能"""
    return ai_function_registry.get_intelligent_functions()


def get_intelligence_score() -> float:
    """获取智能化程度"""
    return ai_function_registry.calculate_intelligence_score()


def register_novel_writing_functions():
    """注册小说写作功能"""

    # 文档专属功能
    ai_function_registry.register_function(
        "continue_writing",
        AIIntelligentFunction,
        AIFunctionMetadata(
            id="continue_writing",
            name="智能续写",
            description="基于当前内容智能续写下一段",
            category=AIFunctionCategory.GENERATION.value,
            icon="📝",
            tooltip="基于当前内容智能续写下一段",
            execution_mode=AIExecutionMode.HYBRID,
            requires_context=True
        )
    )

    ai_function_registry.register_function(
        "expand_content",
        AIIntelligentFunction,
        AIFunctionMetadata(
            id="expand_content",
            name="内容扩展",
            description="扩展选中段落，增加细节描述",
            category=AIFunctionCategory.OPTIMIZATION.value,
            icon="📖",
            tooltip="扩展选中段落，增加细节描述",
            execution_mode=AIExecutionMode.AUTO_SELECTION,
            requires_context=True
        )
    )

    ai_function_registry.register_function(
        "generate_dialogue",
        AIIntelligentFunction,
        AIFunctionMetadata(
            id="generate_dialogue",
            name="对话生成",
            description="为角色生成符合性格的对话",
            category=AIFunctionCategory.GENERATION.value,
            icon="💬",
            tooltip="为角色生成符合性格的对话",
            execution_mode=AIExecutionMode.HYBRID,
            requires_context=True
        )
    )

    ai_function_registry.register_function(
        "generate_description",
        AIIntelligentFunction,
        AIFunctionMetadata(
            id="generate_description",
            name="场景描写",
            description="生成生动的场景和环境描写",
            category=AIFunctionCategory.GENERATION.value,
            icon="🎭",
            tooltip="生成生动的场景和环境描写",
            execution_mode=AIExecutionMode.HYBRID,
            requires_context=True
        )
    )

    # 注册核心小说写作功能
    ai_function_registry.register_function(
        "polish_language",
        AIIntelligentFunction,
        AIFunctionMetadata(
            id="polish_language",
            name="语言润色",
            description="优化文字表达，提升文学性",
            category=AIFunctionCategory.OPTIMIZATION.value,
            icon="✨",
            tooltip="优化文字表达，提升文学性",
            execution_mode=AIExecutionMode.AUTO_SELECTION,
            requires_context=True
        )
    )

    logger.info("小说写作功能注册完成")


# 自动注册小说写作功能
register_novel_writing_functions()

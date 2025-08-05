#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置智能化AI功能

提供一系列内置的智能化AI功能，展示重构后架构的能力
"""

import logging
from typing import Dict, Any, Optional

from .ai_intelligence_service import AIIntelligentFunction
from .ai_function_registry import register_ai_function, AIFunctionCategory
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode
from src.domain.ai.value_objects.ai_request_type import AIRequestType

logger = logging.getLogger(__name__)


@register_ai_function(
    function_id="intelligent_continuation",
    name="智能续写",
    description="基于文档上下文智能续写内容，无需手动输入",
    category=AIFunctionCategory.GENERATION,
    execution_mode=AIExecutionMode.AUTO_CONTEXT,
    icon="✍️",
    tooltip="AI将自动分析当前文档内容并进行智能续写",
    min_context_length=50,
    supports_streaming=True,
    estimated_time=15,
    smart_description="100%智能化：无需任何输入，AI自动分析文档内容并续写"
)
class IntelligentContinuationFunction(AIIntelligentFunction):
    """智能续写功能 - 100%智能化"""
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """检查是否可以自动执行"""
        return len(context.strip()) >= self.metadata.min_context_length
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能化提示词"""
        # 分析上下文类型
        context_type = self._analyze_context_type(context)
        
        # 构建智能化提示词
        prompt = f"""请基于以下{context_type}内容进行智能续写：

{context}

续写要求：
1. 保持原有的写作风格和语调
2. 确保情节发展的连贯性和合理性
3. 字数控制在200-500字之间
4. 如果是对话，请保持角色性格一致
5. 如果是描述，请保持场景氛围连贯

请开始续写："""
        
        return prompt
    
    def _analyze_context_type(self, context: str) -> str:
        """分析上下文类型"""
        if '"' in context or '"' in context or '：' in context:
            return "对话"
        elif any(word in context for word in ['描述', '场景', '环境', '外观']):
            return "描述"
        elif any(word in context for word in ['情节', '故事', '发生', '然后']):
            return "情节"
        else:
            return "文本"
    
    def _get_request_type(self) -> AIRequestType:
        return AIRequestType.TEXT_CONTINUATION


@register_ai_function(
    function_id="intelligent_optimization",
    name="智能优化",
    description="智能优化选中文字或文档内容，自动选择最佳输入源",
    category=AIFunctionCategory.OPTIMIZATION,
    execution_mode=AIExecutionMode.HYBRID,
    icon="🔧",
    tooltip="选中文字时优化选中内容，否则优化整个文档",
    min_context_length=20,
    supports_streaming=True,
    estimated_time=12,
    smart_description="智能化：自动选择优化目标，无需手动指定"
)
class IntelligentOptimizationFunction(AIIntelligentFunction):
    """智能优化功能 - 混合智能化"""
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """检查是否可以自动执行"""
        return bool(selected_text.strip()) or len(context.strip()) >= self.metadata.min_context_length
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能化提示词"""
        if selected_text.strip():
            # 优化选中文字
            optimization_type = self._detect_optimization_type(selected_text)
            prompt = f"""请优化以下选中的{optimization_type}：

原文：
{selected_text}

优化要求：
1. 提高表达的准确性和流畅性
2. 增强语言的感染力和表现力
3. 保持原意不变
4. 适当调整句式结构
5. 确保语法正确

请提供优化后的版本："""
        else:
            # 优化整个文档
            doc_type = self._analyze_document_type(context)
            prompt = f"""请对以下{doc_type}进行整体优化：

原文：
{context}

优化要求：
1. 提升整体文档质量和可读性
2. 优化段落结构和逻辑关系
3. 增强语言表达效果
4. 保持原有风格和主题
5. 确保内容完整性

请提供优化后的版本："""
        
        return prompt
    
    def _detect_optimization_type(self, text: str) -> str:
        """检测优化类型"""
        if len(text) <= 50:
            return "短句"
        elif len(text) <= 200:
            return "段落"
        else:
            return "长文本"
    
    def _analyze_document_type(self, context: str) -> str:
        """分析文档类型"""
        if any(word in context for word in ['章节', '第一章', '第二章']):
            return "章节内容"
        elif any(word in context for word in ['角色', '人物', '性格']):
            return "角色描述"
        else:
            return "文档内容"
    
    def _get_request_type(self) -> AIRequestType:
        return AIRequestType.TEXT_OPTIMIZATION


@register_ai_function(
    function_id="intelligent_analysis",
    name="智能分析",
    description="自动分析选中文字的内容特征和写作技巧",
    category=AIFunctionCategory.ANALYSIS,
    execution_mode=AIExecutionMode.AUTO_SELECTION,
    icon="🔍",
    tooltip="选中文字后自动进行深度分析",
    min_context_length=30,
    supports_streaming=False,
    estimated_time=10,
    smart_description="智能化：选中文字即可自动分析，无需额外操作"
)
class IntelligentAnalysisFunction(AIIntelligentFunction):
    """智能分析功能 - 自动选择模式"""
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """检查是否可以自动执行"""
        return len(selected_text.strip()) >= self.metadata.min_context_length
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能化提示词"""
        analysis_aspects = self._determine_analysis_aspects(selected_text)
        
        prompt = f"""请对以下选中文字进行深度分析：

分析文本：
{selected_text}

请从以下角度进行分析：
{analysis_aspects}

分析要求：
1. 提供具体的分析结果和建议
2. 指出优点和可改进之处
3. 给出具体的改进建议
4. 分析语言特色和技巧运用
5. 评估整体效果

请提供详细的分析报告："""
        
        return prompt
    
    def _determine_analysis_aspects(self, text: str) -> str:
        """确定分析角度"""
        aspects = []
        
        # 基础分析
        aspects.append("1. 语言表达：词汇选择、句式结构、语法规范")
        aspects.append("2. 内容质量：逻辑性、完整性、准确性")
        
        # 根据内容特征添加特定分析
        if '"' in text or '"' in text:
            aspects.append("3. 对话分析：角色语言特色、对话自然度")
        
        if any(word in text for word in ['描述', '场景', '环境']):
            aspects.append("3. 描写技巧：感官运用、细节刻画、氛围营造")
        
        if any(word in text for word in ['情感', '心理', '感受']):
            aspects.append("4. 情感表达：情感层次、感染力、共鸣度")
        
        aspects.append("5. 写作技巧：修辞手法、表现手法、文学性")
        
        return "\n".join(aspects)
    
    def _get_request_type(self) -> AIRequestType:
        return AIRequestType.TEXT_ANALYSIS


@register_ai_function(
    function_id="intelligent_inspiration",
    name="写作灵感",
    description="基于当前文档内容智能生成写作灵感和创意建议",
    category=AIFunctionCategory.INSPIRATION,
    execution_mode=AIExecutionMode.AUTO_CONTEXT,
    icon="💡",
    tooltip="AI自动分析文档内容并提供创意灵感",
    min_context_length=40,
    supports_streaming=True,
    estimated_time=8,
    smart_description="智能化：自动分析文档并生成相关创意灵感"
)
class IntelligentInspirationFunction(AIIntelligentFunction):
    """智能灵感功能 - 100%智能化"""
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """检查是否可以自动执行"""
        return len(context.strip()) >= self.metadata.min_context_length
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能化提示词"""
        content_themes = self._extract_themes(context)
        inspiration_types = self._determine_inspiration_types(context)
        
        prompt = f"""基于以下文档内容，请提供创意写作灵感：

当前内容：
{context}

识别的主题：{content_themes}

请提供以下类型的创意灵感：
{inspiration_types}

灵感要求：
1. 与当前内容高度相关
2. 具有创新性和可操作性
3. 提供具体的实施建议
4. 考虑情节发展的可能性
5. 保持风格和主题一致性

请生成创意灵感："""
        
        return prompt
    
    def _extract_themes(self, context: str) -> str:
        """提取内容主题"""
        themes = []
        
        # 简单的主题识别
        if any(word in context for word in ['爱情', '恋爱', '情感']):
            themes.append("情感关系")
        if any(word in context for word in ['冒险', '探险', '旅行']):
            themes.append("冒险探索")
        if any(word in context for word in ['悬疑', '神秘', '谜团']):
            themes.append("悬疑推理")
        if any(word in context for word in ['成长', '学习', '进步']):
            themes.append("成长励志")
        
        return "、".join(themes) if themes else "日常生活"
    
    def _determine_inspiration_types(self, context: str) -> str:
        """确定灵感类型"""
        types = [
            "1. 情节发展：下一步可能的故事走向",
            "2. 角色发展：角色性格深化和关系变化",
            "3. 场景扩展：新场景和环境设定",
            "4. 冲突设计：潜在的矛盾和冲突点",
            "5. 细节丰富：可以添加的生动细节"
        ]
        
        return "\n".join(types)
    
    def _get_request_type(self) -> AIRequestType:
        return AIRequestType.WRITING_INSPIRATION


def register_builtin_functions():
    """注册所有内置智能化功能"""
    logger.info("内置智能化AI功能已通过装饰器自动注册")
    
    # 获取注册统计
    from .ai_function_registry import ai_function_registry
    stats = ai_function_registry.get_registry_statistics()
    
    logger.info(f"已注册 {stats['total_functions']} 个AI功能")
    logger.info(f"智能化功能: {stats['intelligent_functions']} 个")
    logger.info(f"智能化程度: {stats['intelligence_percentage']:.1f}%")
    
    return stats

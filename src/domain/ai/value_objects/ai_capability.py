#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI能力值对象

定义AI提供商和功能模块的能力
"""

from enum import Enum
from typing import Set, Dict, Any, List


class AICapability(Enum):
    """
    AI能力枚举
    
    定义AI系统支持的各种能力
    """
    
    # 基础能力
    TEXT_GENERATION = "text_generation"
    TEXT_ANALYSIS = "text_analysis"
    CONVERSATION = "conversation"
    
    # 创作能力
    CREATIVE_WRITING = "creative_writing"
    STORY_WRITING = "story_writing"
    CHARACTER_DEVELOPMENT = "character_development"
    PLOT_GENERATION = "plot_generation"
    DIALOGUE_CREATION = "dialogue_creation"
    SCENE_WRITING = "scene_writing"
    
    # 优化能力
    TEXT_OPTIMIZATION = "text_optimization"
    STYLE_IMPROVEMENT = "style_improvement"
    GRAMMAR_CORRECTION = "grammar_correction"
    READABILITY_ENHANCEMENT = "readability_enhancement"
    
    # 分析能力
    CONTENT_ANALYSIS = "content_analysis"
    STYLE_ANALYSIS = "style_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    THEME_ANALYSIS = "theme_analysis"
    CHARACTER_ANALYSIS = "character_analysis"
    PLOT_ANALYSIS = "plot_analysis"
    
    # 总结能力
    TEXT_SUMMARIZATION = "text_summarization"
    CONTENT_EXTRACTION = "content_extraction"
    KEY_POINTS_IDENTIFICATION = "key_points_identification"
    
    # 翻译能力
    LANGUAGE_TRANSLATION = "language_translation"
    LANGUAGE_DETECTION = "language_detection"
    CROSS_CULTURAL_ADAPTATION = "cross_cultural_adaptation"
    
    # 交互能力
    QUESTION_ANSWERING = "question_answering"
    CONTEXTUAL_UNDERSTANDING = "contextual_understanding"
    MULTI_TURN_CONVERSATION = "multi_turn_conversation"
    
    # 灵感能力
    IDEA_GENERATION = "idea_generation"
    BRAINSTORMING = "brainstorming"
    CREATIVE_INSPIRATION = "creative_inspiration"
    
    # 技术能力
    STREAMING_OUTPUT = "streaming_output"
    BATCH_PROCESSING = "batch_processing"
    CONTEXT_AWARENESS = "context_awareness"
    MEMORY_RETENTION = "memory_retention"
    
    @property
    def category(self) -> str:
        """获取能力分类"""
        categories = {
            # 基础能力
            self.TEXT_GENERATION: "basic",
            self.TEXT_ANALYSIS: "basic",
            self.CONVERSATION: "basic",
            
            # 创作能力
            self.CREATIVE_WRITING: "creative",
            self.STORY_WRITING: "creative",
            self.CHARACTER_DEVELOPMENT: "creative",
            self.PLOT_GENERATION: "creative",
            self.DIALOGUE_CREATION: "creative",
            self.SCENE_WRITING: "creative",
            
            # 优化能力
            self.TEXT_OPTIMIZATION: "optimization",
            self.STYLE_IMPROVEMENT: "optimization",
            self.GRAMMAR_CORRECTION: "optimization",
            self.READABILITY_ENHANCEMENT: "optimization",
            
            # 分析能力
            self.CONTENT_ANALYSIS: "analysis",
            self.STYLE_ANALYSIS: "analysis",
            self.SENTIMENT_ANALYSIS: "analysis",
            self.THEME_ANALYSIS: "analysis",
            self.CHARACTER_ANALYSIS: "analysis",
            self.PLOT_ANALYSIS: "analysis",
            
            # 总结能力
            self.TEXT_SUMMARIZATION: "summarization",
            self.CONTENT_EXTRACTION: "summarization",
            self.KEY_POINTS_IDENTIFICATION: "summarization",
            
            # 翻译能力
            self.LANGUAGE_TRANSLATION: "translation",
            self.LANGUAGE_DETECTION: "translation",
            self.CROSS_CULTURAL_ADAPTATION: "translation",
            
            # 交互能力
            self.QUESTION_ANSWERING: "interaction",
            self.CONTEXTUAL_UNDERSTANDING: "interaction",
            self.MULTI_TURN_CONVERSATION: "interaction",
            
            # 灵感能力
            self.IDEA_GENERATION: "inspiration",
            self.BRAINSTORMING: "inspiration",
            self.CREATIVE_INSPIRATION: "inspiration",
            
            # 技术能力
            self.STREAMING_OUTPUT: "technical",
            self.BATCH_PROCESSING: "technical",
            self.CONTEXT_AWARENESS: "technical",
            self.MEMORY_RETENTION: "technical"
        }
        return categories.get(self, "unknown")
    
    @property
    def is_core_capability(self) -> bool:
        """是否为核心能力"""
        core_capabilities = {
            self.TEXT_GENERATION,
            self.TEXT_ANALYSIS,
            self.CONVERSATION,
            self.CREATIVE_WRITING,
            self.TEXT_OPTIMIZATION,
            self.TEXT_SUMMARIZATION,
            self.LANGUAGE_TRANSLATION
        }
        return self in core_capabilities
    
    @property
    def requires_context(self) -> bool:
        """是否需要上下文"""
        context_required = {
            self.STORY_WRITING,
            self.CHARACTER_DEVELOPMENT,
            self.PLOT_GENERATION,
            self.CONTENT_ANALYSIS,
            self.STYLE_ANALYSIS,
            self.THEME_ANALYSIS,
            self.CHARACTER_ANALYSIS,
            self.PLOT_ANALYSIS,
            self.TEXT_SUMMARIZATION,
            self.CONTEXTUAL_UNDERSTANDING,
            self.CREATIVE_INSPIRATION
        }
        return self in context_required
    
    def get_description(self) -> str:
        """获取能力描述"""
        descriptions = {
            self.TEXT_GENERATION: "文本生成",
            self.TEXT_ANALYSIS: "文本分析",
            self.CONVERSATION: "对话交流",
            self.CREATIVE_WRITING: "创意写作",
            self.STORY_WRITING: "故事创作",
            self.CHARACTER_DEVELOPMENT: "角色发展",
            self.PLOT_GENERATION: "情节生成",
            self.DIALOGUE_CREATION: "对话创作",
            self.SCENE_WRITING: "场景描写",
            self.TEXT_OPTIMIZATION: "文本优化",
            self.STYLE_IMPROVEMENT: "风格改进",
            self.GRAMMAR_CORRECTION: "语法纠正",
            self.READABILITY_ENHANCEMENT: "可读性增强",
            self.CONTENT_ANALYSIS: "内容分析",
            self.STYLE_ANALYSIS: "风格分析",
            self.SENTIMENT_ANALYSIS: "情感分析",
            self.THEME_ANALYSIS: "主题分析",
            self.CHARACTER_ANALYSIS: "角色分析",
            self.PLOT_ANALYSIS: "情节分析",
            self.TEXT_SUMMARIZATION: "文本总结",
            self.CONTENT_EXTRACTION: "内容提取",
            self.KEY_POINTS_IDENTIFICATION: "要点识别",
            self.LANGUAGE_TRANSLATION: "语言翻译",
            self.LANGUAGE_DETECTION: "语言检测",
            self.CROSS_CULTURAL_ADAPTATION: "跨文化适应",
            self.QUESTION_ANSWERING: "问答",
            self.CONTEXTUAL_UNDERSTANDING: "上下文理解",
            self.MULTI_TURN_CONVERSATION: "多轮对话",
            self.IDEA_GENERATION: "想法生成",
            self.BRAINSTORMING: "头脑风暴",
            self.CREATIVE_INSPIRATION: "创意灵感",
            self.STREAMING_OUTPUT: "流式输出",
            self.BATCH_PROCESSING: "批量处理",
            self.CONTEXT_AWARENESS: "上下文感知",
            self.MEMORY_RETENTION: "记忆保持"
        }
        return descriptions.get(self, "未知能力")
    
    @classmethod
    def get_by_category(cls, category: str) -> List['AICapability']:
        """根据分类获取能力列表"""
        return [capability for capability in cls if capability.category == category]
    
    @classmethod
    def get_core_capabilities(cls) -> Set['AICapability']:
        """获取核心能力集合"""
        return {capability for capability in cls if capability.is_core_capability}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'value': self.value,
            'name': self.name,
            'category': self.category,
            'description': self.get_description(),
            'is_core_capability': self.is_core_capability,
            'requires_context': self.requires_context
        }
    
    def __str__(self) -> str:
        return f"{self.get_description()}({self.value})"
    
    def __repr__(self) -> str:
        return f"AICapability.{self.name}"

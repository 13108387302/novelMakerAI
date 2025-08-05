#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI请求类型值对象

定义AI请求的类型和分类
"""

from enum import Enum
from typing import List, Dict, Any


class AIRequestType(Enum):
    """
    AI请求类型枚举
    
    定义不同类型的AI请求，对应不同的AI能力
    """
    
    # 基础文本生成
    TEXT_GENERATION = "text_generation"
    TEXT_COMPLETION = "text_completion"
    TEXT_CONTINUATION = "text_continuation"
    
    # 创作类型
    CREATIVE_WRITING = "creative_writing"
    STORY_WRITING = "story_writing"
    CHARACTER_CREATION = "character_creation"
    PLOT_GENERATION = "plot_generation"
    DIALOGUE_WRITING = "dialogue_writing"
    SCENE_DESCRIPTION = "scene_description"
    
    # 优化类型
    TEXT_OPTIMIZATION = "text_optimization"
    TEXT_REWRITING = "text_rewriting"
    STYLE_IMPROVEMENT = "style_improvement"
    GRAMMAR_CHECK = "grammar_check"
    
    # 分析类型
    TEXT_ANALYSIS = "text_analysis"
    CONTENT_ANALYSIS = "content_analysis"
    STYLE_ANALYSIS = "style_analysis"
    CHARACTER_ANALYSIS = "character_analysis"
    PLOT_ANALYSIS = "plot_analysis"
    THEME_ANALYSIS = "theme_analysis"
    
    # 总结类型
    TEXT_SUMMARIZATION = "text_summarization"
    CONTENT_SUMMARY = "content_summary"
    CHAPTER_SUMMARY = "chapter_summary"
    
    # 翻译类型
    TRANSLATION = "translation"
    LANGUAGE_DETECTION = "language_detection"
    
    # 对话类型
    CONVERSATION = "conversation"
    QUESTION_ANSWERING = "question_answering"
    
    # 灵感类型
    WRITING_INSPIRATION = "writing_inspiration"
    CREATIVE_IDEAS = "creative_ideas"
    BRAINSTORMING = "brainstorming"
    
    @property
    def category(self) -> str:
        """获取请求类型的分类"""
        categories = {
            # 生成类
            self.TEXT_GENERATION: "generation",
            self.TEXT_COMPLETION: "generation", 
            self.TEXT_CONTINUATION: "generation",
            self.CREATIVE_WRITING: "generation",
            self.STORY_WRITING: "generation",
            self.CHARACTER_CREATION: "generation",
            self.PLOT_GENERATION: "generation",
            self.DIALOGUE_WRITING: "generation",
            self.SCENE_DESCRIPTION: "generation",
            
            # 优化类
            self.TEXT_OPTIMIZATION: "optimization",
            self.TEXT_REWRITING: "optimization",
            self.STYLE_IMPROVEMENT: "optimization",
            self.GRAMMAR_CHECK: "optimization",
            
            # 分析类
            self.TEXT_ANALYSIS: "analysis",
            self.CONTENT_ANALYSIS: "analysis",
            self.STYLE_ANALYSIS: "analysis",
            self.CHARACTER_ANALYSIS: "analysis",
            self.PLOT_ANALYSIS: "analysis",
            self.THEME_ANALYSIS: "analysis",
            
            # 总结类
            self.TEXT_SUMMARIZATION: "summarization",
            self.CONTENT_SUMMARY: "summarization",
            self.CHAPTER_SUMMARY: "summarization",
            
            # 翻译类
            self.TRANSLATION: "translation",
            self.LANGUAGE_DETECTION: "translation",
            
            # 对话类
            self.CONVERSATION: "conversation",
            self.QUESTION_ANSWERING: "conversation",
            
            # 灵感类
            self.WRITING_INSPIRATION: "inspiration",
            self.CREATIVE_IDEAS: "inspiration",
            self.BRAINSTORMING: "inspiration"
        }
        return categories.get(self, "unknown")
    
    @property
    def is_creative(self) -> bool:
        """是否为创作类型"""
        return self.category in ["generation", "inspiration"]
    
    @property
    def is_analytical(self) -> bool:
        """是否为分析类型"""
        return self.category in ["analysis", "summarization"]
    
    @property
    def is_transformative(self) -> bool:
        """是否为转换类型"""
        return self.category in ["optimization", "translation"]
    
    @property
    def requires_context(self) -> bool:
        """是否通常需要上下文"""
        context_required = {
            self.TEXT_CONTINUATION,
            self.STORY_WRITING,
            self.DIALOGUE_WRITING,
            self.SCENE_DESCRIPTION,
            self.TEXT_ANALYSIS,
            self.CONTENT_ANALYSIS,
            self.STYLE_ANALYSIS,
            self.CHARACTER_ANALYSIS,
            self.PLOT_ANALYSIS,
            self.THEME_ANALYSIS,
            self.TEXT_SUMMARIZATION,
            self.CONTENT_SUMMARY,
            self.CHAPTER_SUMMARY,
            self.WRITING_INSPIRATION
        }
        return self in context_required
    
    @property
    def supports_streaming(self) -> bool:
        """是否支持流式输出"""
        streaming_supported = {
            self.TEXT_GENERATION,
            self.TEXT_COMPLETION,
            self.TEXT_CONTINUATION,
            self.CREATIVE_WRITING,
            self.STORY_WRITING,
            self.CHARACTER_CREATION,
            self.PLOT_GENERATION,
            self.DIALOGUE_WRITING,
            self.SCENE_DESCRIPTION,
            self.TEXT_OPTIMIZATION,
            self.TEXT_REWRITING,
            self.WRITING_INSPIRATION,
            self.CREATIVE_IDEAS,
            self.BRAINSTORMING
        }
        return self in streaming_supported
    
    def get_description(self) -> str:
        """获取类型描述"""
        descriptions = {
            self.TEXT_GENERATION: "文本生成",
            self.TEXT_COMPLETION: "文本补全",
            self.TEXT_CONTINUATION: "文本续写",
            self.CREATIVE_WRITING: "创意写作",
            self.STORY_WRITING: "故事创作",
            self.CHARACTER_CREATION: "角色创建",
            self.PLOT_GENERATION: "情节生成",
            self.DIALOGUE_WRITING: "对话创作",
            self.SCENE_DESCRIPTION: "场景描写",
            self.TEXT_OPTIMIZATION: "文本优化",
            self.TEXT_REWRITING: "文本重写",
            self.STYLE_IMPROVEMENT: "风格改进",
            self.GRAMMAR_CHECK: "语法检查",
            self.TEXT_ANALYSIS: "文本分析",
            self.CONTENT_ANALYSIS: "内容分析",
            self.STYLE_ANALYSIS: "风格分析",
            self.CHARACTER_ANALYSIS: "角色分析",
            self.PLOT_ANALYSIS: "情节分析",
            self.THEME_ANALYSIS: "主题分析",
            self.TEXT_SUMMARIZATION: "文本总结",
            self.CONTENT_SUMMARY: "内容摘要",
            self.CHAPTER_SUMMARY: "章节总结",
            self.TRANSLATION: "文本翻译",
            self.LANGUAGE_DETECTION: "语言检测",
            self.CONVERSATION: "对话交流",
            self.QUESTION_ANSWERING: "问答",
            self.WRITING_INSPIRATION: "写作灵感",
            self.CREATIVE_IDEAS: "创意想法",
            self.BRAINSTORMING: "头脑风暴"
        }
        return descriptions.get(self, "未知类型")
    
    @classmethod
    def get_by_category(cls, category: str) -> List['AIRequestType']:
        """根据分类获取请求类型列表"""
        return [req_type for req_type in cls if req_type.category == category]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'value': self.value,
            'name': self.name,
            'category': self.category,
            'description': self.get_description(),
            'is_creative': self.is_creative,
            'is_analytical': self.is_analytical,
            'is_transformative': self.is_transformative,
            'requires_context': self.requires_context,
            'supports_streaming': self.supports_streaming
        }
    
    def __str__(self) -> str:
        return f"{self.get_description()}({self.value})"
    
    def __repr__(self) -> str:
        return f"AIRequestType.{self.name}"

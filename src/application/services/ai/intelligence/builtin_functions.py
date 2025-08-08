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
from .deep_context_analyzer import DeepContextAnalyzer
from .intelligent_prompt_builder import IntelligentPromptBuilder
from .ai_response_evaluator import AIResponseEvaluator
from src.domain.ai.value_objects.ai_execution_mode import AIExecutionMode
from src.domain.ai.value_objects.ai_request_type import AIRequestType

logger = logging.getLogger(__name__)


class EnhancedAIIntelligentFunction(AIIntelligentFunction):
    """
    增强的智能AI功能基类

    集成深度上下文分析、智能提示词生成和响应质量评估
    """

    def __init__(self):
        super().__init__()
        # 初始化深度分析组件
        self._context_analyzer = DeepContextAnalyzer()
        self._prompt_builder = IntelligentPromptBuilder(self._context_analyzer)
        self._response_evaluator = AIResponseEvaluator(self._context_analyzer)

        logger.info(f"增强AI功能初始化: {self.__class__.__name__}")

    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """
        构建智能化提示词（增强版本）

        使用深度上下文分析和智能提示词构建器
        """
        try:
            # 使用智能提示词构建器
            intelligent_prompt = self._prompt_builder.build_intelligent_prompt(
                content=context,
                request_type=self._get_request_type(),
                selected_text=selected_text,
                user_intent=input_text,
                target_length=self._get_target_length()
            )

            logger.info(f"智能提示词构建完成，质量评分: {intelligent_prompt.estimated_quality:.2f}")
            logger.debug(f"构建推理: {intelligent_prompt.reasoning}")

            return intelligent_prompt.content

        except Exception as e:
            logger.error(f"智能提示词构建失败: {e}")
            # 回退到原有方法
            return super()._build_intelligent_prompt(input_text, context, selected_text)

    def _get_target_length(self) -> int:
        """获取目标长度（子类可重写）"""
        return 300

    def evaluate_response(self, ai_response: str, original_context: str) -> Dict[str, Any]:
        """
        评估AI响应质量

        Args:
            ai_response: AI生成的响应
            original_context: 原始上下文

        Returns:
            Dict[str, Any]: 评估结果
        """
        try:
            assessment = self._response_evaluator.evaluate_response(
                ai_response=ai_response,
                original_context=original_context,
                request_type=self._get_request_type().value
            )

            return {
                'overall_score': assessment.overall_score,
                'overall_level': assessment.overall_level.value,
                'strengths': assessment.strengths,
                'weaknesses': assessment.weaknesses,
                'suggestions': assessment.improvement_suggestions,
                'confidence': assessment.confidence,
                'summary': assessment.evaluation_summary
            }

        except Exception as e:
            logger.error(f"响应质量评估失败: {e}")
            return {
                'overall_score': 60.0,
                'overall_level': 'acceptable',
                'strengths': [],
                'weaknesses': ['评估失败'],
                'suggestions': ['建议重新评估'],
                'confidence': 0.3,
                'summary': '评估过程中出现错误'
            }

    def get_context_analysis(self, content: str) -> Dict[str, Any]:
        """
        获取上下文分析结果

        Args:
            content: 要分析的内容

        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            writing_context = self._context_analyzer.analyze_writing_context(content)

            return {
                'narrative_voice': writing_context.narrative_voice.description,
                'writing_style': writing_context.writing_style.get_description(),
                'emotional_tone': writing_context.emotional_tone.value,
                'characters': list(writing_context.character_analysis.keys()),
                'themes': writing_context.themes,
                'genre_indicators': writing_context.genre_indicators,
                'literary_devices': writing_context.literary_devices,
                'scene_setting': writing_context.scene_setting.get_description(),
                'keywords': writing_context.keywords[:10]  # 前10个关键词
            }

        except Exception as e:
            logger.error(f"上下文分析失败: {e}")
            return {
                'narrative_voice': '未知',
                'writing_style': '未知',
                'emotional_tone': 'neutral',
                'characters': [],
                'themes': [],
                'genre_indicators': [],
                'literary_devices': [],
                'scene_setting': '未知',
                'keywords': []
            }


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
class IntelligentContinuationFunction(EnhancedAIIntelligentFunction):
    """智能续写功能 - 100%智能化"""
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """检查是否可以自动执行"""
        return len(context.strip()) >= self.metadata.min_context_length
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能化提示词（增强版本）"""
        try:
            # 使用父类的增强方法
            enhanced_prompt = super()._build_intelligent_prompt(input_text, context, selected_text)

            # 如果增强方法成功，直接返回
            if enhanced_prompt and len(enhanced_prompt) > 100:
                return enhanced_prompt

        except Exception as e:
            logger.warning(f"增强提示词构建失败，使用原有方法: {e}")

        # 回退到原有方法
        context_type = self._analyze_context_type(context)

        # 获取上下文分析（如果可用）
        try:
            context_analysis = self.get_context_analysis(context)
            narrative_voice = context_analysis.get('narrative_voice', '第三人称叙述')
            writing_style = context_analysis.get('writing_style', '适中平衡的写作风格')
            emotional_tone = context_analysis.get('emotional_tone', 'neutral')

            # 构建增强的提示词
            prompt = f"""请基于以下{context_type}内容进行智能续写：

【原文内容】
{context}

【写作分析】
- 叙述视角: {narrative_voice}
- 写作风格: {writing_style}
- 情感基调: {emotional_tone}

【续写要求】
1. 严格保持{narrative_voice}的叙述视角
2. 延续{writing_style}的表达特色
3. 保持{emotional_tone}的情感氛围
4. 确保情节发展的逻辑连贯性
5. 字数控制在200-500字之间
6. 如果涉及角色，请保持性格一致性
7. 如果涉及场景，请保持环境连贯性

请开始智能续写："""

        except Exception as e:
            logger.warning(f"上下文分析失败，使用简化提示词: {e}")
            # 最简化的回退版本
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
class IntelligentOptimizationFunction(EnhancedAIIntelligentFunction):
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
class IntelligentAnalysisFunction(EnhancedAIIntelligentFunction):
    """智能分析功能 - 自动选择模式"""
    
    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """检查是否可以自动执行"""
        return len(selected_text.strip()) >= self.metadata.min_context_length
    
    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能化提示词（增强版本）"""
        try:
            # 使用父类的增强方法
            enhanced_prompt = super()._build_intelligent_prompt(input_text, context, selected_text)

            if enhanced_prompt and len(enhanced_prompt) > 100:
                return enhanced_prompt

        except Exception as e:
            logger.warning(f"增强提示词构建失败，使用原有方法: {e}")

        # 回退到增强的原有方法
        analysis_aspects = self._determine_analysis_aspects(selected_text)

        try:
            # 获取深度上下文分析
            context_analysis = self.get_context_analysis(selected_text)

            prompt = f"""请对以下选中文字进行专业深度分析：

【分析文本】
{selected_text}

【智能识别结果】
- 叙述视角: {context_analysis.get('narrative_voice', '未识别')}
- 写作风格: {context_analysis.get('writing_style', '未识别')}
- 情感基调: {context_analysis.get('emotional_tone', '未识别')}
- 文体特征: {', '.join(context_analysis.get('genre_indicators', [])) or '未识别'}
- 文学手法: {', '.join(context_analysis.get('literary_devices', [])) or '未识别'}

【专业分析维度】
{analysis_aspects}

【分析要求】
1. 结合智能识别结果进行深度分析
2. 提供具体的文本证据支持分析结论
3. 从文学创作角度给出专业评价
4. 指出写作技巧的优点和可改进之处
5. 提供具体可操作的改进建议
6. 评估文本的艺术价值和表达效果

请提供专业详细的分析报告："""

        except Exception as e:
            logger.warning(f"深度分析失败，使用简化版本: {e}")
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
class IntelligentInspirationFunction(EnhancedAIIntelligentFunction):
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


@register_ai_function(
    function_id="enhanced_ai_chat",
    name="智能对话",
    description="与AI进行智能对话，支持上下文理解和多轮对话",
    category=AIFunctionCategory.INTERACTION,
    execution_mode=AIExecutionMode.INTERACTIVE,
    icon="💬",
    tooltip="与AI助手进行智能对话，支持文档上下文理解",
    min_context_length=0,
    supports_streaming=True,
    estimated_time=5,
    smart_description="智能化对话：理解文档上下文，支持多轮对话记忆"
)
class EnhancedAIChatFunction(EnhancedAIIntelligentFunction):
    """增强AI对话功能 - 支持上下文和对话历史"""

    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """聊天功能总是可以执行"""
        return True

    def _build_intelligent_prompt(self, input_text: str, context: str, selected_text: str) -> str:
        """构建智能对话提示词"""
        # 基础系统提示
        system_prompt = """你是一个专业的AI写作助手，专门帮助用户进行小说创作。你的特点是：

🎯 核心能力：
- 深度理解小说创作的各个环节
- 提供具体、实用、可操作的建议
- 分析文本结构、人物塑造、情节发展
- 协助解决创作中的具体问题

💡 交互风格：
- 友好、耐心、专业
- 回答简洁明了，重点突出
- 提供多种解决方案供选择
- 鼓励创意思维和个性表达

📚 专业领域：
- 小说结构设计和情节规划
- 人物性格塑造和对话写作
- 场景描写和氛围营造
- 文学技巧和语言润色
- 创意灵感和写作突破"""

        # 添加文档上下文分析
        context_info = ""
        if context and len(context.strip()) > 50:
            try:
                # 使用深度分析器分析文档
                writing_context = self._context_analyzer.analyze_content(context)

                context_info = f"""

📖 当前文档分析：
- 叙述视角：{writing_context.narrative_voice.value}
- 情感基调：{writing_context.emotional_tone.value}
- 场景设定：{writing_context.scene_setting.location}
- 主要角色：{', '.join(list(writing_context.character_analysis.keys())[:3]) if writing_context.character_analysis else '未识别'}
- 核心主题：{', '.join(writing_context.themes[:2]) if writing_context.themes else '未识别'}

文档内容摘要：
{context[:800]}{'...' if len(context) > 800 else ''}"""

            except Exception as e:
                logger.warning(f"文档分析失败: {e}")
                context_info = f"""

📖 当前文档内容：
{context[:500]}{'...' if len(context) > 500 else ''}"""

        # 添加选中文本信息
        selection_info = ""
        if selected_text and len(selected_text.strip()) > 10:
            selection_info = f"""

🎯 用户选中的文本：
"{selected_text}"

请特别关注用户选中的这段文本，可能与问题相关。"""

        # 构建完整提示
        full_prompt = f"""{system_prompt}{context_info}{selection_info}

用户问题：{input_text}

请基于以上信息提供专业、有帮助的回答："""

        return full_prompt

"""
智能提示词构建器

基于深度上下文分析结果，智能构建高质量的AI提示词。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .deep_context_analyzer import (
    DeepContextAnalyzer, WritingContext, NarrativeVoice, 
    WritingComplexity, EmotionalTone, WritingStyle
)
from src.domain.ai.value_objects.ai_request_type import AIRequestType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class PromptTemplate(Enum):
    """提示词模板类型"""
    CONTINUATION = "continuation"       # 续写
    OPTIMIZATION = "optimization"       # 优化
    ANALYSIS = "analysis"              # 分析
    INSPIRATION = "inspiration"        # 灵感
    CHARACTER_DEVELOPMENT = "character_development"  # 角色发展
    DIALOGUE_ENHANCEMENT = "dialogue_enhancement"   # 对话增强
    SCENE_DESCRIPTION = "scene_description"         # 场景描述
    PLOT_ADVANCEMENT = "plot_advancement"           # 情节推进


@dataclass
class PromptContext:
    """提示词上下文"""
    request_type: AIRequestType
    writing_context: WritingContext
    user_intent: str = ""
    target_length: int = 300
    specific_requirements: List[str] = None
    
    def __post_init__(self):
        if self.specific_requirements is None:
            self.specific_requirements = []


@dataclass
class IntelligentPrompt:
    """智能提示词"""
    content: str
    confidence_score: float  # 置信度分数 (0-1)
    reasoning: str          # 构建推理过程
    template_used: PromptTemplate
    context_factors: List[str]  # 影响因素
    estimated_quality: float    # 预估质量 (0-1)


class IntelligentPromptBuilder:
    """
    智能提示词构建器
    
    基于深度上下文分析结果，智能构建针对性的AI提示词：
    1. 分析写作上下文特征
    2. 选择最适合的提示词模板
    3. 动态调整提示词内容
    4. 优化提示词质量
    5. 提供构建推理过程
    """
    
    def __init__(self, context_analyzer: Optional[DeepContextAnalyzer] = None):
        self.context_analyzer = context_analyzer or DeepContextAnalyzer()
        
        # 加载提示词模板
        self._load_prompt_templates()
        
        # 加载优化规则
        self._load_optimization_rules()
        
        logger.info("智能提示词构建器初始化完成")
    
    def _load_prompt_templates(self):
        """加载提示词模板"""
        self.templates = {
            PromptTemplate.CONTINUATION: {
                'base': """基于以下{narrative_voice}小说内容进行智能续写：

【当前内容】
{content}

【写作要求】
{writing_requirements}

【续写指导】
{continuation_guidance}

请开始续写：""",
                
                'requirements': {
                    WritingComplexity.SIMPLE: "保持简洁明快的表达风格",
                    WritingComplexity.MODERATE: "保持适中平衡的叙述节奏",
                    WritingComplexity.COMPLEX: "保持复杂精细的描写层次",
                    WritingComplexity.SOPHISTICATED: "保持精致优雅的文学品质"
                }
            },
            
            PromptTemplate.OPTIMIZATION: {
                'base': """请优化以下{text_type}，提升其{optimization_focus}：

【原文】
{content}

【优化目标】
{optimization_goals}

【风格要求】
{style_requirements}

请提供优化后的版本：""",
                
                'focus_areas': {
                    'language': '语言表达效果',
                    'structure': '结构逻辑性',
                    'emotion': '情感感染力',
                    'imagery': '意象生动性'
                }
            },
            
            PromptTemplate.ANALYSIS: {
                'base': """请对以下{genre}文本进行深度分析：

【分析文本】
{content}

【分析维度】
{analysis_dimensions}

【专业要求】
{professional_requirements}

请提供详细的分析报告：""",
                
                'dimensions': [
                    '叙述技巧：视角运用、节奏控制、结构安排',
                    '语言艺术：词汇选择、句式变化、修辞运用',
                    '人物塑造：性格刻画、对话特色、发展轨迹',
                    '情节设计：冲突设置、悬念营造、转折处理',
                    '主题表达：思想深度、价值取向、现实意义'
                ]
            },
            
            PromptTemplate.CHARACTER_DEVELOPMENT: {
                'base': """基于当前故事情境，请为角色{character_name}设计发展方案：

【当前情境】
{content}

【角色现状】
{character_status}

【发展方向】
{development_directions}

请提供角色发展建议：""",
                
                'directions': [
                    '性格深化：挖掘角色内在特质和成长潜力',
                    '关系演变：分析角色间关系的发展可能',
                    '行为逻辑：确保角色行为符合性格设定',
                    '情感层次：丰富角色的情感表达和变化'
                ]
            }
        }
    
    def _load_optimization_rules(self):
        """加载优化规则"""
        self.optimization_rules = {
            # 基于叙述视角的优化
            'narrative_voice': {
                NarrativeVoice.FIRST_PERSON: {
                    'emphasis': '内心感受和主观体验',
                    'language_style': '更加个人化和情感化的表达',
                    'perspective_consistency': '保持第一人称视角的一致性'
                },
                NarrativeVoice.THIRD_PERSON: {
                    'emphasis': '客观描述和全知视角',
                    'language_style': '更加客观和全面的叙述',
                    'perspective_consistency': '保持第三人称的叙述距离'
                }
            },
            
            # 基于情感基调的优化
            'emotional_tone': {
                EmotionalTone.POSITIVE: {
                    'mood_enhancement': '强化积极向上的情感氛围',
                    'word_choice': '选择更多正面和温暖的词汇',
                    'energy_level': '保持轻快活泼的叙述节奏'
                },
                EmotionalTone.MELANCHOLIC: {
                    'mood_enhancement': '深化忧郁沉思的情感层次',
                    'word_choice': '选择更多深沉和内敛的词汇',
                    'energy_level': '保持缓慢深沉的叙述节奏'
                }
            },
            
            # 基于文体类型的优化
            'genre_specific': {
                '言情': {
                    'focus_areas': ['情感描写', '心理刻画', '浪漫氛围'],
                    'language_features': ['细腻感性', '情感丰富', '意境优美']
                },
                '悬疑': {
                    'focus_areas': ['悬念营造', '线索布置', '紧张氛围'],
                    'language_features': ['简洁有力', '节奏紧凑', '逻辑严密']
                }
            }
        }
    
    def build_intelligent_prompt(
        self,
        content: str,
        request_type: AIRequestType,
        selected_text: str = "",
        user_intent: str = "",
        target_length: int = 300
    ) -> IntelligentPrompt:
        """
        构建智能提示词
        
        Args:
            content: 文档内容
            request_type: 请求类型
            selected_text: 选中文本
            user_intent: 用户意图
            target_length: 目标长度
            
        Returns:
            IntelligentPrompt: 智能提示词
        """
        try:
            logger.info(f"开始构建智能提示词: {request_type.value}")
            
            # 深度分析写作上下文
            writing_context = self.context_analyzer.analyze_writing_context(content)
            
            # 创建提示词上下文
            prompt_context = PromptContext(
                request_type=request_type,
                writing_context=writing_context,
                user_intent=user_intent,
                target_length=target_length
            )
            
            # 选择最适合的模板
            template_type = self._select_optimal_template(prompt_context, selected_text)
            
            # 构建提示词内容
            prompt_content = self._build_prompt_content(
                template_type, prompt_context, content, selected_text
            )
            
            # 优化提示词
            optimized_prompt = self._optimize_prompt(prompt_content, writing_context)
            
            # 评估提示词质量
            quality_score = self._evaluate_prompt_quality(optimized_prompt, writing_context)
            
            # 生成推理过程
            reasoning = self._generate_reasoning(
                template_type, writing_context, prompt_context
            )
            
            # 提取影响因素
            context_factors = self._extract_context_factors(writing_context)
            
            intelligent_prompt = IntelligentPrompt(
                content=optimized_prompt,
                confidence_score=self._calculate_confidence(writing_context, quality_score),
                reasoning=reasoning,
                template_used=template_type,
                context_factors=context_factors,
                estimated_quality=quality_score
            )
            
            logger.info(f"智能提示词构建完成，质量评分: {quality_score:.2f}")
            return intelligent_prompt
            
        except Exception as e:
            logger.error(f"构建智能提示词失败: {e}")
            return self._create_fallback_prompt(content, request_type)
    
    def _select_optimal_template(
        self, 
        prompt_context: PromptContext, 
        selected_text: str
    ) -> PromptTemplate:
        """选择最优模板"""
        try:
            request_type = prompt_context.request_type
            writing_context = prompt_context.writing_context
            
            # 基于请求类型的基础映射
            type_mapping = {
                AIRequestType.TEXT_CONTINUATION: PromptTemplate.CONTINUATION,
                AIRequestType.TEXT_OPTIMIZATION: PromptTemplate.OPTIMIZATION,
                AIRequestType.TEXT_ANALYSIS: PromptTemplate.ANALYSIS,
                AIRequestType.CREATIVE_INSPIRATION: PromptTemplate.INSPIRATION
            }
            
            base_template = type_mapping.get(request_type, PromptTemplate.CONTINUATION)
            
            # 基于上下文的智能调整
            if selected_text and '"' in selected_text:
                # 选中的是对话内容
                return PromptTemplate.DIALOGUE_ENHANCEMENT
            
            if writing_context.character_analysis and len(writing_context.character_analysis) > 0:
                # 有明显的角色信息
                if request_type == AIRequestType.TEXT_CONTINUATION:
                    return PromptTemplate.CHARACTER_DEVELOPMENT
            
            if writing_context.scene_setting.location != "unknown":
                # 有明确的场景设定
                if request_type == AIRequestType.TEXT_CONTINUATION:
                    return PromptTemplate.SCENE_DESCRIPTION
            
            return base_template
            
        except Exception as e:
            logger.error(f"选择模板失败: {e}")
            return PromptTemplate.CONTINUATION
    
    def _build_prompt_content(
        self,
        template_type: PromptTemplate,
        prompt_context: PromptContext,
        content: str,
        selected_text: str
    ) -> str:
        """构建提示词内容"""
        try:
            writing_context = prompt_context.writing_context
            template_config = self.templates.get(template_type, self.templates[PromptTemplate.CONTINUATION])
            
            # 准备模板变量
            template_vars = {
                'content': selected_text if selected_text else content,
                'narrative_voice': writing_context.narrative_voice.description,
                'text_type': self._determine_text_type(selected_text, content),
                'genre': ', '.join(writing_context.genre_indicators) or '文学',
            }
            
            # 根据模板类型添加特定变量
            if template_type == PromptTemplate.CONTINUATION:
                template_vars.update({
                    'writing_requirements': self._build_writing_requirements(writing_context),
                    'continuation_guidance': self._build_continuation_guidance(writing_context)
                })
            
            elif template_type == PromptTemplate.OPTIMIZATION:
                template_vars.update({
                    'optimization_focus': self._determine_optimization_focus(writing_context),
                    'optimization_goals': self._build_optimization_goals(writing_context),
                    'style_requirements': self._build_style_requirements(writing_context)
                })
            
            elif template_type == PromptTemplate.ANALYSIS:
                template_vars.update({
                    'analysis_dimensions': '\n'.join(f"{i+1}. {dim}" for i, dim in enumerate(template_config['dimensions'])),
                    'professional_requirements': self._build_professional_requirements(writing_context)
                })
            
            # 格式化模板
            prompt_content = template_config['base'].format(**template_vars)
            
            return prompt_content
            
        except Exception as e:
            logger.error(f"构建提示词内容失败: {e}")
            return f"请处理以下内容：\n\n{content}"
    
    def _build_writing_requirements(self, writing_context: WritingContext) -> str:
        """构建写作要求"""
        requirements = []
        
        # 基于写作风格的要求
        style = writing_context.writing_style
        complexity_req = self.templates[PromptTemplate.CONTINUATION]['requirements'].get(
            style.sentence_complexity, "保持原有的写作风格"
        )
        requirements.append(f"1. 风格一致性：{complexity_req}")
        
        # 基于叙述视角的要求
        if writing_context.narrative_voice == NarrativeVoice.FIRST_PERSON:
            requirements.append("2. 视角保持：继续使用第一人称叙述，注重内心感受")
        elif writing_context.narrative_voice == NarrativeVoice.THIRD_PERSON:
            requirements.append("2. 视角保持：继续使用第三人称叙述，保持客观描述")
        
        # 基于情感基调的要求
        if writing_context.emotional_tone != EmotionalTone.NEUTRAL:
            requirements.append(f"3. 情感延续：保持{writing_context.emotional_tone.value}的情感基调")
        
        # 基于角色的要求
        if writing_context.character_analysis:
            requirements.append("4. 角色一致：保持已建立角色的性格特征和行为逻辑")
        
        return '\n'.join(requirements)
    
    def _build_continuation_guidance(self, writing_context: WritingContext) -> str:
        """构建续写指导"""
        guidance = []
        
        # 基于情节结构的指导
        plot = writing_context.plot_structure
        if plot.current_stage == "开端":
            guidance.append("• 可以进一步展开背景设定或引入新的情节元素")
        elif plot.current_stage == "发展":
            guidance.append("• 推进情节发展，可以增加冲突或转折")
        elif plot.current_stage == "高潮":
            guidance.append("• 维持紧张感，准备情节的解决或转向")
        
        # 基于场景设定的指导
        scene = writing_context.scene_setting
        if scene.location != "unknown":
            guidance.append(f"• 充分利用{scene.location}的环境特色")
        
        # 基于文学手法的指导
        if writing_context.literary_devices:
            devices_str = '、'.join(writing_context.literary_devices)
            guidance.append(f"• 可以继续运用{devices_str}等文学手法")
        
        return '\n'.join(guidance) if guidance else "• 自然延续当前的叙述节奏和风格"
    
    def _determine_text_type(self, selected_text: str, content: str) -> str:
        """确定文本类型"""
        if selected_text:
            if len(selected_text) < 50:
                return "选中片段"
            elif '"' in selected_text:
                return "对话内容"
            else:
                return "选中段落"
        else:
            return "文档内容"
    
    def _determine_optimization_focus(self, writing_context: WritingContext) -> str:
        """确定优化重点"""
        style = writing_context.writing_style
        
        if style.literary_sophistication < 0.3:
            return "文学表现力和艺术性"
        elif style.descriptive_density < 0.2:
            return "描述生动性和画面感"
        elif style.dialogue_frequency > 0.8:
            return "对话自然性和角色特色"
        else:
            return "整体表达效果和可读性"
    
    def _build_optimization_goals(self, writing_context: WritingContext) -> str:
        """构建优化目标"""
        goals = [
            "1. 提升语言表达的准确性和流畅性",
            "2. 增强文字的感染力和表现力",
            "3. 优化句式结构和节奏感"
        ]
        
        # 基于写作风格添加特定目标
        if writing_context.writing_style.vocabulary_richness < 0.5:
            goals.append("4. 丰富词汇选择，避免重复用词")
        
        if writing_context.emotional_tone == EmotionalTone.NEUTRAL:
            goals.append("4. 增强情感色彩和感染力")
        
        return '\n'.join(goals)
    
    def _build_style_requirements(self, writing_context: WritingContext) -> str:
        """构建风格要求"""
        requirements = []
        
        # 基于叙述视角
        voice_rules = self.optimization_rules['narrative_voice'].get(writing_context.narrative_voice, {})
        if voice_rules:
            requirements.append(f"• {voice_rules.get('perspective_consistency', '')}")
        
        # 基于情感基调
        tone_rules = self.optimization_rules['emotional_tone'].get(writing_context.emotional_tone, {})
        if tone_rules:
            requirements.append(f"• {tone_rules.get('mood_enhancement', '')}")
        
        # 基于文体类型
        for genre in writing_context.genre_indicators:
            genre_rules = self.optimization_rules['genre_specific'].get(genre, {})
            if genre_rules:
                features = genre_rules.get('language_features', [])
                if features:
                    requirements.append(f"• 体现{genre}文体特色：{', '.join(features)}")
        
        return '\n'.join(requirements) if requirements else "• 保持原有风格特色，提升表达质量"
    
    def _build_professional_requirements(self, writing_context: WritingContext) -> str:
        """构建专业要求"""
        requirements = [
            "1. 分析应当客观专业，避免主观臆断",
            "2. 提供具体的文本证据支持分析结论",
            "3. 给出建设性的改进建议和方向"
        ]
        
        # 基于文体添加专业要求
        if writing_context.genre_indicators:
            genre = writing_context.genre_indicators[0]
            requirements.append(f"4. 结合{genre}文体的特点进行专业分析")
        
        return '\n'.join(requirements)
    
    def _optimize_prompt(self, prompt_content: str, writing_context: WritingContext) -> str:
        """优化提示词"""
        try:
            # 基础优化：确保提示词清晰明确
            optimized = prompt_content
            
            # 添加长度控制
            if "续写" in optimized:
                optimized += f"\n\n【长度要求】\n请控制续写内容在200-500字之间，确保内容完整。"
            
            # 添加质量要求
            optimized += f"\n\n【质量标准】\n请确保输出内容具有较高的文学质量和可读性。"
            
            return optimized
            
        except Exception as e:
            logger.error(f"优化提示词失败: {e}")
            return prompt_content
    
    def _evaluate_prompt_quality(self, prompt: str, writing_context: WritingContext) -> float:
        """评估提示词质量"""
        try:
            quality_score = 0.5  # 基础分数
            
            # 长度适中性 (0.1)
            if 100 <= len(prompt) <= 1000:
                quality_score += 0.1
            
            # 结构完整性 (0.2)
            if all(section in prompt for section in ['【', '】']):
                quality_score += 0.1
            if '要求' in prompt or '指导' in prompt:
                quality_score += 0.1
            
            # 上下文相关性 (0.2)
            if writing_context.narrative_voice.description in prompt:
                quality_score += 0.1
            if any(theme in prompt for theme in writing_context.themes):
                quality_score += 0.1
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.error(f"评估提示词质量失败: {e}")
            return 0.5
    
    def _calculate_confidence(self, writing_context: WritingContext, quality_score: float) -> float:
        """计算置信度"""
        try:
            confidence = quality_score * 0.6  # 基于质量分数
            
            # 基于上下文完整性调整
            if writing_context.character_analysis:
                confidence += 0.1
            if writing_context.themes:
                confidence += 0.1
            if writing_context.literary_devices:
                confidence += 0.1
            if writing_context.genre_indicators:
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"计算置信度失败: {e}")
            return 0.5
    
    def _generate_reasoning(
        self,
        template_type: PromptTemplate,
        writing_context: WritingContext,
        prompt_context: PromptContext
    ) -> str:
        """生成推理过程"""
        reasoning_parts = []
        
        # 模板选择推理
        reasoning_parts.append(f"选择{template_type.value}模板，因为请求类型为{prompt_context.request_type.value}")
        
        # 上下文分析推理
        reasoning_parts.append(f"检测到{writing_context.narrative_voice.description}，调整提示词以保持视角一致性")
        
        if writing_context.emotional_tone != EmotionalTone.NEUTRAL:
            reasoning_parts.append(f"识别出{writing_context.emotional_tone.value}情感基调，强化相应的情感指导")
        
        if writing_context.genre_indicators:
            genres = ', '.join(writing_context.genre_indicators)
            reasoning_parts.append(f"识别出{genres}文体特征，添加相应的专业要求")
        
        return ' | '.join(reasoning_parts)
    
    def _extract_context_factors(self, writing_context: WritingContext) -> List[str]:
        """提取影响因素"""
        factors = []
        
        factors.append(f"叙述视角: {writing_context.narrative_voice.description}")
        factors.append(f"写作复杂度: {writing_context.writing_style.sentence_complexity.value}")
        factors.append(f"情感基调: {writing_context.emotional_tone.value}")
        
        if writing_context.character_analysis:
            factors.append(f"角色数量: {len(writing_context.character_analysis)}")
        
        if writing_context.themes:
            factors.append(f"主题: {', '.join(writing_context.themes[:3])}")
        
        if writing_context.genre_indicators:
            factors.append(f"文体: {', '.join(writing_context.genre_indicators)}")
        
        return factors
    
    def _create_fallback_prompt(self, content: str, request_type: AIRequestType) -> IntelligentPrompt:
        """创建回退提示词"""
        fallback_content = f"""请根据以下内容进行{request_type.value}：

{content}

请提供高质量的结果。"""
        
        return IntelligentPrompt(
            content=fallback_content,
            confidence_score=0.3,
            reasoning="使用回退模板，因为智能分析失败",
            template_used=PromptTemplate.CONTINUATION,
            context_factors=["回退模式"],
            estimated_quality=0.3
        )

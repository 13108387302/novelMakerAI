"""
AI响应质量评估器

对AI生成的内容进行多维度质量评估，确保输出质量符合预期。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import re
import jieba
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .deep_context_analyzer import DeepContextAnalyzer, WritingContext, NarrativeVoice, EmotionalTone
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class QualityDimension(Enum):
    """质量评估维度"""
    STYLE_CONSISTENCY = "style_consistency"       # 风格一致性
    NARRATIVE_COHERENCE = "narrative_coherence"   # 叙事连贯性
    CHARACTER_CONSISTENCY = "character_consistency"  # 角色一致性
    EMOTIONAL_APPROPRIATENESS = "emotional_appropriateness"  # 情感适宜性
    LANGUAGE_QUALITY = "language_quality"         # 语言质量
    CONTENT_RELEVANCE = "content_relevance"       # 内容相关性
    CREATIVITY_LEVEL = "creativity_level"         # 创意水平
    TECHNICAL_ACCURACY = "technical_accuracy"     # 技术准确性


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"    # 优秀 (90-100)
    GOOD = "good"             # 良好 (70-89)
    ACCEPTABLE = "acceptable"  # 可接受 (50-69)
    POOR = "poor"             # 较差 (30-49)
    UNACCEPTABLE = "unacceptable"  # 不可接受 (0-29)
    
    @classmethod
    def from_score(cls, score: float) -> 'QualityLevel':
        """根据分数确定质量等级"""
        if score >= 90:
            return cls.EXCELLENT
        elif score >= 70:
            return cls.GOOD
        elif score >= 50:
            return cls.ACCEPTABLE
        elif score >= 30:
            return cls.POOR
        else:
            return cls.UNACCEPTABLE


@dataclass
class DimensionScore:
    """维度评分"""
    dimension: QualityDimension
    score: float  # 0-100
    confidence: float  # 0-1
    details: str = ""
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """质量评估结果"""
    overall_score: float  # 总体评分 0-100
    overall_level: QualityLevel
    dimension_scores: Dict[QualityDimension, DimensionScore]
    strengths: List[str]  # 优点
    weaknesses: List[str]  # 缺点
    improvement_suggestions: List[str]  # 改进建议
    confidence: float  # 评估置信度 0-1
    evaluation_summary: str  # 评估摘要


class AIResponseEvaluator:
    """
    AI响应质量评估器
    
    对AI生成的内容进行多维度质量评估：
    1. 风格一致性：与原文风格的匹配度
    2. 叙事连贯性：情节和逻辑的连贯性
    3. 角色一致性：角色行为和性格的一致性
    4. 情感适宜性：情感表达的适宜性
    5. 语言质量：语法、词汇、表达的质量
    6. 内容相关性：与上下文的相关性
    7. 创意水平：创新性和想象力
    8. 技术准确性：技术细节的准确性
    """
    
    def __init__(self, context_analyzer: Optional[DeepContextAnalyzer] = None):
        self.context_analyzer = context_analyzer or DeepContextAnalyzer()
        
        # 初始化评估规则
        self._load_evaluation_rules()
        
        # 初始化质量标准
        self._load_quality_standards()
        
        logger.info("AI响应质量评估器初始化完成")
    
    def _load_evaluation_rules(self):
        """加载评估规则"""
        self.evaluation_rules = {
            QualityDimension.STYLE_CONSISTENCY: {
                'weight': 0.20,  # 权重
                'criteria': [
                    '叙述视角一致性',
                    '句式风格匹配',
                    '词汇选择风格',
                    '语言复杂度匹配'
                ]
            },
            
            QualityDimension.NARRATIVE_COHERENCE: {
                'weight': 0.18,
                'criteria': [
                    '情节逻辑连贯',
                    '时间线一致',
                    '因果关系合理',
                    '场景转换自然'
                ]
            },
            
            QualityDimension.CHARACTER_CONSISTENCY: {
                'weight': 0.15,
                'criteria': [
                    '角色性格一致',
                    '行为逻辑合理',
                    '对话风格匹配',
                    '角色发展合理'
                ]
            },
            
            QualityDimension.EMOTIONAL_APPROPRIATENESS: {
                'weight': 0.12,
                'criteria': [
                    '情感基调匹配',
                    '情感表达自然',
                    '情感强度适宜',
                    '情感转换合理'
                ]
            },
            
            QualityDimension.LANGUAGE_QUALITY: {
                'weight': 0.15,
                'criteria': [
                    '语法正确性',
                    '词汇丰富性',
                    '表达流畅性',
                    '修辞运用恰当'
                ]
            },
            
            QualityDimension.CONTENT_RELEVANCE: {
                'weight': 0.10,
                'criteria': [
                    '主题相关性',
                    '内容连贯性',
                    '信息完整性',
                    '重点突出性'
                ]
            },
            
            QualityDimension.CREATIVITY_LEVEL: {
                'weight': 0.05,
                'criteria': [
                    '创意新颖性',
                    '想象力丰富',
                    '表达独特性',
                    '思维发散性'
                ]
            },
            
            QualityDimension.TECHNICAL_ACCURACY: {
                'weight': 0.05,
                'criteria': [
                    '事实准确性',
                    '逻辑严密性',
                    '细节真实性',
                    '专业性准确'
                ]
            }
        }
    
    def _load_quality_standards(self):
        """加载质量标准"""
        self.quality_standards = {
            'excellent_threshold': 90,
            'good_threshold': 70,
            'acceptable_threshold': 50,
            'minimum_length': 20,  # 最小长度
            'maximum_repetition_rate': 0.3,  # 最大重复率
            'minimum_coherence_score': 0.6,  # 最小连贯性分数
        }
    
    def evaluate_response(
        self,
        ai_response: str,
        original_context: str,
        request_type: str = "continuation",
        expected_style: Optional[WritingContext] = None
    ) -> QualityAssessment:
        """
        评估AI响应质量
        
        Args:
            ai_response: AI生成的响应内容
            original_context: 原始上下文
            request_type: 请求类型
            expected_style: 期望的写作风格
            
        Returns:
            QualityAssessment: 质量评估结果
        """
        try:
            logger.info(f"开始评估AI响应质量: {len(ai_response)} 字符")
            
            # 分析原始上下文和AI响应的写作特征
            original_context_analysis = self.context_analyzer.analyze_writing_context(original_context)
            response_analysis = self.context_analyzer.analyze_writing_context(ai_response)
            
            # 执行各维度评估
            dimension_scores = {}
            
            # 1. 风格一致性评估
            dimension_scores[QualityDimension.STYLE_CONSISTENCY] = self._evaluate_style_consistency(
                original_context_analysis, response_analysis
            )
            
            # 2. 叙事连贯性评估
            dimension_scores[QualityDimension.NARRATIVE_COHERENCE] = self._evaluate_narrative_coherence(
                original_context, ai_response, original_context_analysis
            )
            
            # 3. 角色一致性评估
            dimension_scores[QualityDimension.CHARACTER_CONSISTENCY] = self._evaluate_character_consistency(
                original_context_analysis, response_analysis
            )
            
            # 4. 情感适宜性评估
            dimension_scores[QualityDimension.EMOTIONAL_APPROPRIATENESS] = self._evaluate_emotional_appropriateness(
                original_context_analysis, response_analysis
            )
            
            # 5. 语言质量评估
            dimension_scores[QualityDimension.LANGUAGE_QUALITY] = self._evaluate_language_quality(
                ai_response
            )
            
            # 6. 内容相关性评估
            dimension_scores[QualityDimension.CONTENT_RELEVANCE] = self._evaluate_content_relevance(
                original_context, ai_response
            )
            
            # 7. 创意水平评估
            dimension_scores[QualityDimension.CREATIVITY_LEVEL] = self._evaluate_creativity_level(
                ai_response, original_context_analysis
            )
            
            # 8. 技术准确性评估
            dimension_scores[QualityDimension.TECHNICAL_ACCURACY] = self._evaluate_technical_accuracy(
                ai_response
            )
            
            # 计算总体评分
            overall_score = self._calculate_overall_score(dimension_scores)
            overall_level = QualityLevel.from_score(overall_score)
            
            # 提取优缺点和建议
            strengths, weaknesses, suggestions = self._extract_insights(dimension_scores)
            
            # 计算评估置信度
            confidence = self._calculate_evaluation_confidence(dimension_scores)
            
            # 生成评估摘要
            summary = self._generate_evaluation_summary(overall_score, dimension_scores)
            
            assessment = QualityAssessment(
                overall_score=overall_score,
                overall_level=overall_level,
                dimension_scores=dimension_scores,
                strengths=strengths,
                weaknesses=weaknesses,
                improvement_suggestions=suggestions,
                confidence=confidence,
                evaluation_summary=summary
            )
            
            logger.info(f"AI响应质量评估完成: {overall_level.value} ({overall_score:.1f}分)")
            return assessment
            
        except Exception as e:
            logger.error(f"评估AI响应质量失败: {e}")
            return self._create_fallback_assessment(ai_response)
    
    def _evaluate_style_consistency(
        self,
        original_analysis: WritingContext,
        response_analysis: WritingContext
    ) -> DimensionScore:
        """评估风格一致性"""
        try:
            score = 0.0
            details = []
            suggestions = []
            
            # 叙述视角一致性 (25%)
            if original_analysis.narrative_voice == response_analysis.narrative_voice:
                score += 25
                details.append(f"✓ 叙述视角保持一致: {original_analysis.narrative_voice.description}")
            else:
                details.append(f"✗ 叙述视角不一致: {original_analysis.narrative_voice.description} → {response_analysis.narrative_voice.description}")
                suggestions.append("保持原文的叙述视角")
            
            # 句式复杂度匹配 (25%)
            original_complexity = original_analysis.writing_style.sentence_complexity
            response_complexity = response_analysis.writing_style.sentence_complexity
            
            if original_complexity == response_complexity:
                score += 25
                details.append(f"✓ 句式复杂度匹配: {original_complexity.value}")
            else:
                complexity_diff = abs(list(original_complexity.__class__).index(original_complexity) - 
                                    list(response_complexity.__class__).index(response_complexity))
                if complexity_diff <= 1:
                    score += 15
                    details.append(f"△ 句式复杂度基本匹配")
                else:
                    details.append(f"✗ 句式复杂度差异较大")
                    suggestions.append(f"调整句式复杂度以匹配原文的{original_complexity.value}风格")
            
            # 情感基调匹配 (25%)
            if original_analysis.emotional_tone == response_analysis.emotional_tone:
                score += 25
                details.append(f"✓ 情感基调保持一致: {original_analysis.emotional_tone.value}")
            elif original_analysis.emotional_tone == EmotionalTone.MIXED or response_analysis.emotional_tone == EmotionalTone.MIXED:
                score += 15
                details.append("△ 情感基调部分匹配")
            else:
                details.append(f"✗ 情感基调不匹配: {original_analysis.emotional_tone.value} → {response_analysis.emotional_tone.value}")
                suggestions.append(f"调整情感基调以匹配原文的{original_analysis.emotional_tone.value}氛围")
            
            # 文学手法运用 (25%)
            original_devices = set(original_analysis.literary_devices)
            response_devices = set(response_analysis.literary_devices)
            
            if original_devices and response_devices:
                overlap = len(original_devices & response_devices)
                total = len(original_devices | response_devices)
                device_score = (overlap / total) * 25 if total > 0 else 0
                score += device_score
                
                if overlap > 0:
                    details.append(f"✓ 运用了相似的文学手法: {', '.join(original_devices & response_devices)}")
                else:
                    details.append("△ 文学手法运用有差异")
                    suggestions.append("可以运用与原文相似的文学手法")
            else:
                score += 12.5  # 中等分数
                details.append("△ 文学手法运用情况一般")
            
            return DimensionScore(
                dimension=QualityDimension.STYLE_CONSISTENCY,
                score=score,
                confidence=0.8,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估风格一致性失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.STYLE_CONSISTENCY,
                score=50.0,
                confidence=0.3,
                details="评估过程中出现错误",
                suggestions=["建议重新评估"]
            )
    
    def _evaluate_narrative_coherence(
        self,
        original_context: str,
        ai_response: str,
        original_analysis: WritingContext
    ) -> DimensionScore:
        """评估叙事连贯性"""
        try:
            score = 0.0
            details = []
            suggestions = []
            
            # 逻辑连贯性 (40%)
            logical_score = self._assess_logical_coherence(original_context, ai_response)
            score += logical_score * 0.4
            
            if logical_score > 80:
                details.append("✓ 逻辑连贯性优秀")
            elif logical_score > 60:
                details.append("△ 逻辑连贯性良好")
            else:
                details.append("✗ 逻辑连贯性需要改进")
                suggestions.append("加强情节的逻辑连贯性")
            
            # 时间线一致性 (30%)
            time_consistency = self._check_time_consistency(original_context, ai_response)
            score += time_consistency * 0.3
            
            if time_consistency > 80:
                details.append("✓ 时间线保持一致")
            else:
                details.append("△ 时间线存在一些问题")
                suggestions.append("注意保持时间线的一致性")
            
            # 场景连贯性 (30%)
            scene_coherence = self._assess_scene_coherence(original_analysis, ai_response)
            score += scene_coherence * 0.3
            
            if scene_coherence > 70:
                details.append("✓ 场景转换自然")
            else:
                details.append("△ 场景连贯性可以改进")
                suggestions.append("优化场景转换的自然性")
            
            return DimensionScore(
                dimension=QualityDimension.NARRATIVE_COHERENCE,
                score=score,
                confidence=0.7,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估叙事连贯性失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.NARRATIVE_COHERENCE,
                score=60.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _assess_logical_coherence(self, original_context: str, ai_response: str) -> float:
        """评估逻辑连贯性"""
        try:
            # 简化的逻辑连贯性评估
            score = 70.0  # 基础分数
            
            # 检查是否有明显的逻辑矛盾
            contradiction_indicators = ['但是', '然而', '相反', '不过']
            contradictions = sum(ai_response.count(indicator) for indicator in contradiction_indicators)
            
            # 适量的转折是好的，过多可能表示逻辑混乱
            if contradictions <= 2:
                score += 10
            elif contradictions > 5:
                score -= 20
            
            # 检查因果关系
            causal_indicators = ['因为', '所以', '因此', '由于', '导致']
            causal_relations = sum(ai_response.count(indicator) for indicator in causal_indicators)
            
            if causal_relations > 0:
                score += 10
            
            # 检查连接词使用
            connectors = ['然后', '接着', '随后', '于是', '接下来']
            connector_count = sum(ai_response.count(connector) for connector in connectors)
            
            if connector_count > 0:
                score += 10
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"评估逻辑连贯性失败: {e}")
            return 60.0
    
    def _check_time_consistency(self, original_context: str, ai_response: str) -> float:
        """检查时间一致性"""
        try:
            # 简化的时间一致性检查
            time_indicators = ['早晨', '上午', '中午', '下午', '傍晚', '晚上', '深夜', '昨天', '今天', '明天']
            
            original_times = [indicator for indicator in time_indicators if indicator in original_context]
            response_times = [indicator for indicator in time_indicators if indicator in ai_response]
            
            if not original_times and not response_times:
                return 80.0  # 没有明确时间指示，给中等分数
            
            if not response_times:
                return 70.0  # 响应中没有时间指示
            
            # 检查时间逻辑
            time_order = ['早晨', '上午', '中午', '下午', '傍晚', '晚上', '深夜']
            
            # 简单检查：如果响应中的时间在原文时间之后，认为是合理的
            if original_times and response_times:
                original_latest = max([time_order.index(t) for t in original_times if t in time_order], default=0)
                response_earliest = min([time_order.index(t) for t in response_times if t in time_order], default=6)
                
                if response_earliest >= original_latest:
                    return 90.0
                else:
                    return 60.0
            
            return 75.0
            
        except Exception as e:
            logger.error(f"检查时间一致性失败: {e}")
            return 70.0
    
    def _assess_scene_coherence(self, original_analysis: WritingContext, ai_response: str) -> float:
        """评估场景连贯性"""
        try:
            score = 70.0  # 基础分数
            
            # 检查场景设定的一致性
            original_location = original_analysis.scene_setting.location
            
            if original_location != "unknown":
                if original_location in ai_response:
                    score += 20
                else:
                    # 检查是否有合理的场景转换
                    transition_words = ['来到', '走向', '前往', '到达', '进入']
                    if any(word in ai_response for word in transition_words):
                        score += 10  # 有场景转换提示
                    else:
                        score -= 10  # 场景突然改变
            
            # 检查氛围的连贯性
            original_atmosphere = original_analysis.scene_setting.atmosphere
            if original_atmosphere != "neutral":
                # 简单检查氛围词汇
                atmosphere_words = {
                    'peaceful': ['宁静', '安详', '平和'],
                    'tense': ['紧张', '压抑', '沉重'],
                    'joyful': ['欢快', '热闹', '活跃']
                }
                
                expected_words = atmosphere_words.get(original_atmosphere, [])
                if any(word in ai_response for word in expected_words):
                    score += 10
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"评估场景连贯性失败: {e}")
            return 70.0
    
    def _evaluate_character_consistency(
        self,
        original_analysis: WritingContext,
        response_analysis: WritingContext
    ) -> DimensionScore:
        """评估角色一致性"""
        try:
            score = 70.0  # 基础分数
            details = []
            suggestions = []
            
            original_characters = original_analysis.character_analysis
            response_characters = response_analysis.character_analysis
            
            if not original_characters:
                details.append("△ 原文中未检测到明确的角色信息")
                return DimensionScore(
                    dimension=QualityDimension.CHARACTER_CONSISTENCY,
                    score=score,
                    confidence=0.5,
                    details='\n'.join(details),
                    suggestions=suggestions
                )
            
            # 检查角色是否保持一致
            common_characters = set(original_characters.keys()) & set(response_characters.keys())
            
            if common_characters:
                score += 20
                details.append(f"✓ 保持了角色的连续性: {', '.join(common_characters)}")
            else:
                details.append("△ 响应中未明确提及原有角色")
                suggestions.append("保持角色的连续性和一致性")
            
            # 检查新角色的引入是否合理
            new_characters = set(response_characters.keys()) - set(original_characters.keys())
            if new_characters:
                if len(new_characters) <= 2:
                    score += 10
                    details.append(f"✓ 合理引入新角色: {', '.join(new_characters)}")
                else:
                    score -= 10
                    details.append("△ 引入了过多新角色")
                    suggestions.append("控制新角色的引入数量")
            
            return DimensionScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=min(score, 100.0),
                confidence=0.6,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估角色一致性失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.CHARACTER_CONSISTENCY,
                score=60.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _evaluate_emotional_appropriateness(
        self,
        original_analysis: WritingContext,
        response_analysis: WritingContext
    ) -> DimensionScore:
        """评估情感适宜性"""
        try:
            score = 0.0
            details = []
            suggestions = []
            
            original_tone = original_analysis.emotional_tone
            response_tone = response_analysis.emotional_tone
            
            # 情感基调匹配度 (60%)
            if original_tone == response_tone:
                score += 60
                details.append(f"✓ 情感基调完全匹配: {original_tone.value}")
            elif original_tone == EmotionalTone.MIXED or response_tone == EmotionalTone.MIXED:
                score += 40
                details.append("△ 情感基调部分匹配")
            else:
                score += 20
                details.append(f"✗ 情感基调不匹配: {original_tone.value} → {response_tone.value}")
                suggestions.append(f"调整情感表达以匹配原文的{original_tone.value}基调")
            
            # 情感表达自然度 (40%)
            emotion_naturalness = self._assess_emotion_naturalness(response_analysis)
            score += emotion_naturalness * 0.4
            
            if emotion_naturalness > 80:
                details.append("✓ 情感表达自然流畅")
            elif emotion_naturalness > 60:
                details.append("△ 情感表达基本自然")
            else:
                details.append("✗ 情感表达略显生硬")
                suggestions.append("增强情感表达的自然性")
            
            return DimensionScore(
                dimension=QualityDimension.EMOTIONAL_APPROPRIATENESS,
                score=score,
                confidence=0.7,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估情感适宜性失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.EMOTIONAL_APPROPRIATENESS,
                score=60.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _assess_emotion_naturalness(self, response_analysis: WritingContext) -> float:
        """评估情感表达自然度"""
        try:
            # 基于情感词汇的多样性和适度性
            score = 70.0
            
            # 检查情感词汇的使用
            emotion_words = ['高兴', '悲伤', '愤怒', '恐惧', '惊讶', '厌恶', '喜悦', '痛苦']
            # 这里可以根据response_analysis中的信息进行更详细的分析
            
            return score
            
        except Exception as e:
            logger.error(f"评估情感自然度失败: {e}")
            return 60.0
    
    def _evaluate_language_quality(self, ai_response: str) -> DimensionScore:
        """评估语言质量"""
        try:
            score = 0.0
            details = []
            suggestions = []
            
            # 基础语法检查 (30%)
            grammar_score = self._check_basic_grammar(ai_response)
            score += grammar_score * 0.3
            
            if grammar_score > 85:
                details.append("✓ 语法基本正确")
            else:
                details.append("△ 语法存在一些问题")
                suggestions.append("检查并修正语法错误")
            
            # 词汇丰富性 (25%)
            vocabulary_richness = self._assess_vocabulary_richness(ai_response)
            score += vocabulary_richness * 0.25
            
            if vocabulary_richness > 70:
                details.append("✓ 词汇使用丰富")
            else:
                details.append("△ 词汇使用可以更丰富")
                suggestions.append("增加词汇的多样性")
            
            # 表达流畅性 (25%)
            fluency_score = self._assess_fluency(ai_response)
            score += fluency_score * 0.25
            
            if fluency_score > 75:
                details.append("✓ 表达流畅自然")
            else:
                details.append("△ 表达流畅性可以改进")
                suggestions.append("优化句子结构，提高流畅性")
            
            # 修辞运用 (20%)
            rhetoric_score = self._assess_rhetoric_usage(ai_response)
            score += rhetoric_score * 0.2
            
            if rhetoric_score > 60:
                details.append("✓ 修辞运用恰当")
            else:
                details.append("△ 可以适当运用修辞手法")
                suggestions.append("适当运用比喻、拟人等修辞手法")
            
            return DimensionScore(
                dimension=QualityDimension.LANGUAGE_QUALITY,
                score=score,
                confidence=0.8,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估语言质量失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.LANGUAGE_QUALITY,
                score=70.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _check_basic_grammar(self, text: str) -> float:
        """基础语法检查"""
        try:
            score = 90.0  # 基础分数
            
            # 检查标点符号使用
            if not re.search(r'[。！？]', text):
                score -= 10  # 缺少句号等结束标点
            
            # 检查引号配对
            quote_count = text.count('"') + text.count('"')
            if quote_count % 2 != 0:
                score -= 5  # 引号不配对
            
            # 检查明显的语法错误模式
            # 这里可以添加更多的语法检查规则
            
            return max(score, 0.0)
            
        except Exception as e:
            logger.error(f"基础语法检查失败: {e}")
            return 80.0
    
    def _assess_vocabulary_richness(self, text: str) -> float:
        """评估词汇丰富性"""
        try:
            words = list(jieba.cut(text))
            if not words:
                return 50.0
            
            unique_words = len(set(words))
            total_words = len(words)
            
            # 计算词汇丰富度
            richness_ratio = unique_words / total_words
            
            # 转换为0-100分数
            score = min(richness_ratio * 150, 100)  # 调整系数
            
            return score
            
        except Exception as e:
            logger.error(f"评估词汇丰富性失败: {e}")
            return 60.0
    
    def _assess_fluency(self, text: str) -> float:
        """评估表达流畅性"""
        try:
            # 基于句子长度变化和连接词使用评估流畅性
            sentences = re.split(r'[。！？]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return 50.0
            
            # 计算句子长度的变化
            lengths = [len(s) for s in sentences]
            if len(lengths) > 1:
                avg_length = sum(lengths) / len(lengths)
                length_variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
                
                # 适度的长度变化表示良好的节奏
                if 10 <= avg_length <= 30 and length_variance < 200:
                    score = 80.0
                else:
                    score = 60.0
            else:
                score = 70.0
            
            # 检查连接词使用
            connectors = ['而且', '但是', '然而', '因此', '所以', '然后', '接着']
            connector_count = sum(text.count(conn) for conn in connectors)
            
            if connector_count > 0:
                score += 10
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"评估表达流畅性失败: {e}")
            return 70.0
    
    def _assess_rhetoric_usage(self, text: str) -> float:
        """评估修辞运用"""
        try:
            score = 50.0  # 基础分数
            
            # 检查常见修辞手法
            rhetoric_patterns = {
                '比喻': ['像', '如同', '仿佛', '好似', '犹如'],
                '拟人': ['微笑', '哭泣', '舞蹈', '歌唱', '怒吼'],
                '排比': ['一个', '一种', '一片', '一阵'],
                '设问': ['吗？', '呢？', '吧？']
            }
            
            found_devices = []
            for device, patterns in rhetoric_patterns.items():
                if any(pattern in text for pattern in patterns):
                    found_devices.append(device)
                    score += 10
            
            # 限制最高分数
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"评估修辞运用失败: {e}")
            return 50.0
    
    def _evaluate_content_relevance(self, original_context: str, ai_response: str) -> DimensionScore:
        """评估内容相关性"""
        try:
            score = 0.0
            details = []
            suggestions = []
            
            # 关键词重叠度 (40%)
            keyword_overlap = self._calculate_keyword_overlap(original_context, ai_response)
            score += keyword_overlap * 0.4
            
            if keyword_overlap > 70:
                details.append("✓ 与原文关键词高度相关")
            elif keyword_overlap > 40:
                details.append("△ 与原文关键词部分相关")
            else:
                details.append("✗ 与原文关键词相关性较低")
                suggestions.append("增强与原文主题的相关性")
            
            # 主题一致性 (35%)
            theme_consistency = self._assess_theme_consistency(original_context, ai_response)
            score += theme_consistency * 0.35
            
            if theme_consistency > 75:
                details.append("✓ 主题保持一致")
            else:
                details.append("△ 主题一致性可以改进")
                suggestions.append("保持与原文主题的一致性")
            
            # 内容完整性 (25%)
            completeness = self._assess_content_completeness(ai_response)
            score += completeness * 0.25
            
            if completeness > 80:
                details.append("✓ 内容完整充实")
            else:
                details.append("△ 内容可以更加完整")
                suggestions.append("增加内容的完整性和充实度")
            
            return DimensionScore(
                dimension=QualityDimension.CONTENT_RELEVANCE,
                score=score,
                confidence=0.7,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估内容相关性失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.CONTENT_RELEVANCE,
                score=60.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _calculate_keyword_overlap(self, original_context: str, ai_response: str) -> float:
        """计算关键词重叠度"""
        try:
            # 提取关键词
            original_words = set(jieba.cut(original_context))
            response_words = set(jieba.cut(ai_response))
            
            # 过滤停用词
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
            
            original_keywords = original_words - stop_words
            response_keywords = response_words - stop_words
            
            if not original_keywords:
                return 50.0
            
            # 计算重叠度
            overlap = len(original_keywords & response_keywords)
            total = len(original_keywords)
            
            overlap_ratio = overlap / total
            return min(overlap_ratio * 100, 100.0)
            
        except Exception as e:
            logger.error(f"计算关键词重叠度失败: {e}")
            return 50.0
    
    def _assess_theme_consistency(self, original_context: str, ai_response: str) -> float:
        """评估主题一致性"""
        try:
            # 简化的主题一致性评估
            theme_words = {
                '爱情': ['爱', '情', '恋', '心'],
                '友情': ['朋友', '友谊', '伙伴'],
                '冒险': ['冒险', '探险', '发现'],
                '成长': ['成长', '学习', '改变']
            }
            
            original_themes = []
            response_themes = []
            
            for theme, words in theme_words.items():
                if any(word in original_context for word in words):
                    original_themes.append(theme)
                if any(word in ai_response for word in words):
                    response_themes.append(theme)
            
            if not original_themes:
                return 70.0  # 没有明确主题，给中等分数
            
            # 计算主题匹配度
            common_themes = set(original_themes) & set(response_themes)
            if common_themes:
                return 85.0
            else:
                return 50.0
                
        except Exception as e:
            logger.error(f"评估主题一致性失败: {e}")
            return 60.0
    
    def _assess_content_completeness(self, ai_response: str) -> float:
        """评估内容完整性"""
        try:
            # 基于长度和结构完整性评估
            score = 50.0
            
            # 长度评估
            if len(ai_response) >= 100:
                score += 20
            elif len(ai_response) >= 50:
                score += 10
            
            # 结构完整性
            if ai_response.endswith(('。', '！', '？')):
                score += 15  # 有完整的结尾
            
            # 内容丰富性
            sentences = re.split(r'[。！？]', ai_response)
            if len(sentences) >= 3:
                score += 15
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"评估内容完整性失败: {e}")
            return 60.0
    
    def _evaluate_creativity_level(self, ai_response: str, original_analysis: WritingContext) -> DimensionScore:
        """评估创意水平"""
        try:
            score = 50.0  # 基础分数
            details = []
            suggestions = []
            
            # 新颖性评估 (40%)
            novelty_score = self._assess_novelty(ai_response)
            score += (novelty_score - 50) * 0.4
            
            if novelty_score > 70:
                details.append("✓ 内容具有新颖性")
            else:
                details.append("△ 内容新颖性一般")
                suggestions.append("增加创意元素和新颖表达")
            
            # 想象力评估 (35%)
            imagination_score = self._assess_imagination(ai_response)
            score += (imagination_score - 50) * 0.35
            
            if imagination_score > 65:
                details.append("✓ 展现了丰富的想象力")
            else:
                details.append("△ 想象力可以更丰富")
                suggestions.append("发挥更多想象力，增加创意描述")
            
            # 表达独特性 (25%)
            uniqueness_score = self._assess_expression_uniqueness(ai_response)
            score += (uniqueness_score - 50) * 0.25
            
            if uniqueness_score > 60:
                details.append("✓ 表达方式有独特性")
            else:
                details.append("△ 表达方式较为常规")
                suggestions.append("尝试更独特的表达方式")
            
            return DimensionScore(
                dimension=QualityDimension.CREATIVITY_LEVEL,
                score=max(score, 0.0),
                confidence=0.6,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估创意水平失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.CREATIVITY_LEVEL,
                score=50.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _assess_novelty(self, text: str) -> float:
        """评估新颖性"""
        try:
            # 基于词汇使用的独特性
            words = list(jieba.cut(text))
            
            # 检查是否使用了不常见的词汇或表达
            uncommon_indicators = ['竟然', '居然', '忽然', '突然', '意外', '惊讶']
            novelty_count = sum(text.count(indicator) for indicator in uncommon_indicators)
            
            base_score = 50.0
            novelty_bonus = min(novelty_count * 5, 30)
            
            return base_score + novelty_bonus
            
        except Exception as e:
            logger.error(f"评估新颖性失败: {e}")
            return 50.0
    
    def _assess_imagination(self, text: str) -> float:
        """评估想象力"""
        try:
            # 检查想象力相关的词汇和表达
            imagination_indicators = [
                '想象', '幻想', '梦境', '奇幻', '神奇', '魔法',
                '仿佛', '好像', '似乎', '宛如', '犹如'
            ]
            
            imagination_count = sum(text.count(indicator) for indicator in imagination_indicators)
            
            base_score = 50.0
            imagination_bonus = min(imagination_count * 8, 40)
            
            return base_score + imagination_bonus
            
        except Exception as e:
            logger.error(f"评估想象力失败: {e}")
            return 50.0
    
    def _assess_expression_uniqueness(self, text: str) -> float:
        """评估表达独特性"""
        try:
            # 检查独特的表达方式
            unique_patterns = [
                r'[^，。！？]{10,}[，。！？]',  # 较长的句子
                r'[一-龯]{2,}地[一-龯]{2,}',   # 副词+地+动词结构
                r'[一-龯]{3,}的[一-龯]{3,}'    # 形容词+的+名词结构
            ]
            
            unique_count = 0
            for pattern in unique_patterns:
                matches = re.findall(pattern, text)
                unique_count += len(matches)
            
            base_score = 50.0
            uniqueness_bonus = min(unique_count * 3, 25)
            
            return base_score + uniqueness_bonus
            
        except Exception as e:
            logger.error(f"评估表达独特性失败: {e}")
            return 50.0
    
    def _evaluate_technical_accuracy(self, ai_response: str) -> DimensionScore:
        """评估技术准确性"""
        try:
            score = 80.0  # 基础分数（假设大部分内容是准确的）
            details = []
            suggestions = []
            
            # 事实一致性检查 (40%)
            # 这里可以添加更复杂的事实检查逻辑
            fact_score = self._check_factual_consistency(ai_response)
            score = score * 0.6 + fact_score * 0.4
            
            if fact_score > 85:
                details.append("✓ 事实表述基本准确")
            else:
                details.append("△ 事实准确性需要验证")
                suggestions.append("验证并确保事实表述的准确性")
            
            # 逻辑严密性 (35%)
            logic_score = self._assess_logical_rigor(ai_response)
            score = score * 0.65 + logic_score * 0.35
            
            if logic_score > 80:
                details.append("✓ 逻辑表述严密")
            else:
                details.append("△ 逻辑严密性可以改进")
                suggestions.append("加强逻辑推理的严密性")
            
            # 专业性准确 (25%)
            professional_score = self._assess_professional_accuracy(ai_response)
            score = score * 0.75 + professional_score * 0.25
            
            if professional_score > 75:
                details.append("✓ 专业表述恰当")
            else:
                details.append("△ 专业性表述可以提升")
                suggestions.append("提高专业术语使用的准确性")
            
            return DimensionScore(
                dimension=QualityDimension.TECHNICAL_ACCURACY,
                score=score,
                confidence=0.7,
                details='\n'.join(details),
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"评估技术准确性失败: {e}")
            return DimensionScore(
                dimension=QualityDimension.TECHNICAL_ACCURACY,
                score=75.0,
                confidence=0.3,
                details="评估过程中出现错误"
            )
    
    def _check_factual_consistency(self, text: str) -> float:
        """检查事实一致性"""
        try:
            # 简化的事实一致性检查
            # 在实际应用中，这里可以集成知识库或事实检查API
            
            # 检查明显的事实错误指示
            error_indicators = ['错误', '不对', '有误', '不准确']
            error_count = sum(text.count(indicator) for indicator in error_indicators)
            
            base_score = 85.0
            error_penalty = min(error_count * 10, 30)
            
            return max(base_score - error_penalty, 0.0)
            
        except Exception as e:
            logger.error(f"检查事实一致性失败: {e}")
            return 80.0
    
    def _assess_logical_rigor(self, text: str) -> float:
        """评估逻辑严密性"""
        try:
            # 检查逻辑连接词的使用
            logic_connectors = ['因为', '所以', '因此', '由于', '导致', '结果', '原因']
            connector_count = sum(text.count(connector) for connector in logic_connectors)
            
            # 检查逻辑矛盾
            contradiction_patterns = [
                ('是', '不是'),
                ('有', '没有'),
                ('能', '不能'),
                ('会', '不会')
            ]
            
            contradiction_count = 0
            for pos, neg in contradiction_patterns:
                if pos in text and neg in text:
                    contradiction_count += 1
            
            base_score = 75.0
            logic_bonus = min(connector_count * 3, 15)
            contradiction_penalty = contradiction_count * 10
            
            return max(base_score + logic_bonus - contradiction_penalty, 0.0)
            
        except Exception as e:
            logger.error(f"评估逻辑严密性失败: {e}")
            return 75.0
    
    def _assess_professional_accuracy(self, text: str) -> float:
        """评估专业性准确"""
        try:
            # 简化的专业性评估
            # 检查是否使用了适当的专业术语
            
            professional_indicators = ['技术', '方法', '理论', '原理', '概念', '定义']
            professional_count = sum(text.count(indicator) for indicator in professional_indicators)
            
            base_score = 70.0
            professional_bonus = min(professional_count * 2, 20)
            
            return base_score + professional_bonus
            
        except Exception as e:
            logger.error(f"评估专业性准确失败: {e}")
            return 70.0
    
    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, DimensionScore]) -> float:
        """计算总体评分"""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for dimension, score_obj in dimension_scores.items():
                weight = self.evaluation_rules[dimension]['weight']
                weighted_score = score_obj.score * weight
                total_weighted_score += weighted_score
                total_weight += weight
            
            if total_weight > 0:
                overall_score = total_weighted_score / total_weight
            else:
                overall_score = 60.0  # 默认分数
            
            return round(overall_score, 1)
            
        except Exception as e:
            logger.error(f"计算总体评分失败: {e}")
            return 60.0
    
    def _extract_insights(
        self, 
        dimension_scores: Dict[QualityDimension, DimensionScore]
    ) -> Tuple[List[str], List[str], List[str]]:
        """提取优缺点和建议"""
        try:
            strengths = []
            weaknesses = []
            suggestions = []
            
            for dimension, score_obj in dimension_scores.items():
                dimension_name = dimension.value.replace('_', ' ').title()
                
                if score_obj.score >= 80:
                    strengths.append(f"{dimension_name}: {score_obj.score:.1f}分")
                elif score_obj.score < 60:
                    weaknesses.append(f"{dimension_name}: {score_obj.score:.1f}分")
                
                suggestions.extend(score_obj.suggestions)
            
            # 去重建议
            suggestions = list(set(suggestions))
            
            return strengths, weaknesses, suggestions
            
        except Exception as e:
            logger.error(f"提取洞察失败: {e}")
            return [], [], []
    
    def _calculate_evaluation_confidence(
        self, 
        dimension_scores: Dict[QualityDimension, DimensionScore]
    ) -> float:
        """计算评估置信度"""
        try:
            confidences = [score_obj.confidence for score_obj in dimension_scores.values()]
            
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                return round(avg_confidence, 2)
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"计算评估置信度失败: {e}")
            return 0.5
    
    def _generate_evaluation_summary(
        self, 
        overall_score: float, 
        dimension_scores: Dict[QualityDimension, DimensionScore]
    ) -> str:
        """生成评估摘要"""
        try:
            level = QualityLevel.from_score(overall_score)
            
            # 找出最高分和最低分的维度
            best_dimension = max(dimension_scores.items(), key=lambda x: x[1].score)
            worst_dimension = min(dimension_scores.items(), key=lambda x: x[1].score)
            
            summary = f"""AI响应质量评估结果：

总体评分：{overall_score:.1f}分 ({level.value})

表现最佳：{best_dimension[0].value.replace('_', ' ').title()} ({best_dimension[1].score:.1f}分)
需要改进：{worst_dimension[0].value.replace('_', ' ').title()} ({worst_dimension[1].score:.1f}分)

评估建议：根据各维度表现，建议重点关注得分较低的维度，并保持优势维度的水准。"""
            
            return summary
            
        except Exception as e:
            logger.error(f"生成评估摘要失败: {e}")
            return f"AI响应质量评估完成，总体评分：{overall_score:.1f}分"
    
    def _create_fallback_assessment(self, ai_response: str) -> QualityAssessment:
        """创建回退评估结果"""
        fallback_score = DimensionScore(
            dimension=QualityDimension.LANGUAGE_QUALITY,
            score=60.0,
            confidence=0.3,
            details="评估过程中出现错误，使用回退评估",
            suggestions=["建议重新进行质量评估"]
        )
        
        return QualityAssessment(
            overall_score=60.0,
            overall_level=QualityLevel.ACCEPTABLE,
            dimension_scores={QualityDimension.LANGUAGE_QUALITY: fallback_score},
            strengths=[],
            weaknesses=["评估过程不完整"],
            improvement_suggestions=["建议重新进行完整的质量评估"],
            confidence=0.3,
            evaluation_summary="评估过程中出现错误，结果可能不准确"
        )

"""
深度上下文分析引擎

实现对文档内容的深度语义分析，为AI功能提供精准的上下文理解。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import re
import jieba
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter, defaultdict

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class NarrativeVoice(Enum):
    """叙述视角"""
    FIRST_PERSON = "first_person"      # 第一人称
    THIRD_PERSON = "third_person"      # 第三人称
    SECOND_PERSON = "second_person"    # 第二人称
    MIXED = "mixed"                    # 混合视角

    @property
    def description(self) -> str:
        descriptions = {
            self.FIRST_PERSON: "第一人称叙述",
            self.THIRD_PERSON: "第三人称叙述",
            self.SECOND_PERSON: "第二人称叙述",
            self.MIXED: "混合叙述视角"
        }
        return descriptions.get(self, "未知视角")


class WritingComplexity(Enum):
    """写作复杂度"""
    SIMPLE = "simple"          # 简单
    MODERATE = "moderate"      # 中等
    COMPLEX = "complex"        # 复杂
    SOPHISTICATED = "sophisticated"  # 精致


class EmotionalTone(Enum):
    """情感基调"""
    POSITIVE = "positive"      # 积极
    NEGATIVE = "negative"      # 消极
    NEUTRAL = "neutral"        # 中性
    MIXED = "mixed"           # 混合
    MELANCHOLIC = "melancholic"  # 忧郁
    JOYFUL = "joyful"         # 欢快
    TENSE = "tense"           # 紧张
    PEACEFUL = "peaceful"     # 平静


@dataclass
class CharacterInfo:
    """角色信息"""
    name: str
    mentions: int = 0
    dialogue_count: int = 0
    personality_traits: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    emotional_state: str = "unknown"


@dataclass
class WritingStyle:
    """写作风格"""
    sentence_complexity: WritingComplexity = WritingComplexity.MODERATE
    avg_sentence_length: float = 0.0
    descriptive_density: float = 0.0  # 描述性密度
    dialogue_frequency: float = 0.0   # 对话频率
    literary_sophistication: float = 0.0  # 文学性
    vocabulary_richness: float = 0.0  # 词汇丰富度

    def get_description(self) -> str:
        """获取风格描述"""
        complexity_desc = {
            WritingComplexity.SIMPLE: "简洁明快",
            WritingComplexity.MODERATE: "适中平衡",
            WritingComplexity.COMPLEX: "复杂精细",
            WritingComplexity.SOPHISTICATED: "精致优雅"
        }

        return f"{complexity_desc.get(self.sentence_complexity, '未知')}的写作风格"


@dataclass
class PlotStructure:
    """情节结构"""
    current_stage: str = "unknown"     # 当前阶段
    tension_level: float = 0.0         # 紧张程度
    pacing: str = "moderate"           # 节奏
    conflict_intensity: float = 0.0    # 冲突强度
    character_development: float = 0.0  # 角色发展程度


@dataclass
class SceneSetting:
    """场景设定"""
    location: str = "unknown"          # 地点
    time_period: str = "unknown"       # 时间
    atmosphere: str = "neutral"        # 氛围
    sensory_details: List[str] = field(default_factory=list)  # 感官细节

    def get_description(self) -> str:
        """获取场景描述"""
        return f"{self.time_period}的{self.location}，{self.atmosphere}氛围"


@dataclass
class WritingContext:
    """写作上下文"""
    narrative_voice: NarrativeVoice
    writing_style: WritingStyle
    character_analysis: Dict[str, CharacterInfo]
    plot_structure: PlotStructure
    emotional_tone: EmotionalTone
    scene_setting: SceneSetting
    literary_devices: List[str]
    genre_indicators: List[str]
    keywords: List[str]
    themes: List[str]


class DeepContextAnalyzer:
    """
    深度上下文分析器

    对文档内容进行多维度的深度分析：
    1. 叙述视角检测
    2. 写作风格分析
    3. 角色关系分析
    4. 情节结构分析
    5. 情感基调分析
    6. 场景设定分析

    7. 文学手法识别
    8. 主题提取
    """

    def __init__(self):
        # 初始化中文分词
        jieba.initialize()

        # 加载词典和模式
        self._load_literary_patterns()
        self._load_character_patterns()
        self._load_emotion_patterns()

        logger.info("深度上下文分析器初始化完成")

    def analyze_content(self, content: str) -> Dict[str, Any]:
        """对外的统一分析入口，兼容调用方"""
        try:
            return self._analyze_content_internal(content)
        except Exception as e:
            logger.error(f"文档上下文分析失败: {e}")
            return {}

    def _analyze_content_internal(self, content: str) -> Dict[str, Any]:
        """内部分析实现，原先分散的分析流程整合"""
        processed_content = self._preprocess_content(content)
        return {
            'narrative_voice': self._detect_narrative_voice(processed_content),
            'writing_style': self._analyze_writing_style(processed_content),
            'character_analysis': self._extract_character_info(processed_content),
            'plot_structure': self._analyze_plot_structure(processed_content),
            'emotional_tone': self._analyze_emotional_tone(processed_content),
            'scene_setting': self._extract_scene_setting(processed_content),
            'literary_devices': self._detect_literary_devices(processed_content),
            'genre_indicators': self._detect_genre_indicators(processed_content),
            'keywords': self._extract_keywords(processed_content),
            'themes': self._extract_themes(processed_content)
        }

    def _load_literary_patterns(self):
        """加载文学模式"""
        # 叙述视角指示词
        self.narrative_indicators = {
            NarrativeVoice.FIRST_PERSON: ['我', '我们', '我的', '我们的', '咱们'],
            NarrativeVoice.THIRD_PERSON: ['他', '她', '它', '他们', '她们', '它们'],
            NarrativeVoice.SECOND_PERSON: ['你', '您', '你们', '你的', '您的']
        }

        # 情感词典
        self.emotion_words = {
            EmotionalTone.POSITIVE: ['高兴', '快乐', '喜悦', '兴奋', '满足', '幸福', '愉快'],
            EmotionalTone.NEGATIVE: ['悲伤', '痛苦', '愤怒', '恐惧', '焦虑', '绝望', '沮丧'],
            EmotionalTone.PEACEFUL: ['平静', '安详', '宁静', '祥和', '温和', '舒缓'],
            EmotionalTone.TENSE: ['紧张', '激烈', '急促', '危险', '刺激', '惊险']
        }

        # 文学手法
        self.literary_devices = {
            '比喻': ['像', '如同', '仿佛', '好似', '犹如'],
            '拟人': ['微笑', '哭泣', '舞蹈', '歌唱'],
            '排比': ['一个', '一种', '一片'],
            '对比': ['然而', '但是', '相反', '不同']
        }

    def _load_character_patterns(self):
        """加载角色模式"""
        # 角色称谓
        self.character_titles = ['先生', '女士', '小姐', '老师', '医生', '警官', '队长']

        # 性格特征词
        self.personality_traits = {
            '温和': ['温和', '温柔', '和善', '亲切'],
            '强势': ['强势', '霸道', '强硬', '坚决'],
            '聪明': ['聪明', '智慧', '机智', '睿智'],
            '勇敢': ['勇敢', '无畏', '英勇', '胆大']
        }

    def _load_emotion_patterns(self):
        """加载情感模式"""
        # 情感强度词
        self.emotion_intensity = {
            '轻微': ['有点', '稍微', '略微', '一点'],
            '中等': ['比较', '相当', '挺', '很'],
            '强烈': ['非常', '极其', '十分', '特别']
        }

    def analyze_writing_context(self, content: str) -> WritingContext:
        """
        深度分析写作上下文

        Args:
            content: 要分析的文档内容

        Returns:
            WritingContext: 完整的写作上下文分析结果
        """
        try:
            logger.info(f"开始深度上下文分析: {len(content)} 字符")

            # 预处理文本
            processed_content = self._preprocess_text(content)

            # 执行各项分析
            narrative_voice = self._detect_narrative_voice(processed_content)
            writing_style = self._analyze_writing_style(processed_content)
            character_analysis = self._extract_character_info(processed_content)
            plot_structure = self._analyze_plot_structure(processed_content)
            emotional_tone = self._analyze_emotional_tone(processed_content)
            scene_setting = self._extract_scene_setting(processed_content)
            literary_devices = self._detect_literary_devices(processed_content)
            genre_indicators = self._detect_genre_indicators(processed_content)
            keywords = self._extract_keywords(processed_content)
            themes = self._extract_themes(processed_content)

            context = WritingContext(
                narrative_voice=narrative_voice,
                writing_style=writing_style,
                character_analysis=character_analysis,
                plot_structure=plot_structure,
                emotional_tone=emotional_tone,
                scene_setting=scene_setting,
                literary_devices=literary_devices,
                genre_indicators=genre_indicators,
                keywords=keywords,
                themes=themes
            )

            logger.info("深度上下文分析完成")
            return context

        except Exception as e:
            logger.error(f"深度上下文分析失败: {e}")
            # 返回默认上下文
            return self._create_default_context()

    def _preprocess_text(self, content: str) -> str:
        """预处理文本"""
        # 清理多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        # 标准化标点符号
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        return content.strip()

    def _detect_narrative_voice(self, content: str) -> NarrativeVoice:
        """检测叙述视角"""
        try:
            voice_counts = {}

            for voice, indicators in self.narrative_indicators.items():
                count = sum(content.count(word) for word in indicators)
                voice_counts[voice] = count

            # 找到最多的视角
            if not any(voice_counts.values()):
                return NarrativeVoice.THIRD_PERSON  # 默认第三人称

            max_voice = max(voice_counts, key=voice_counts.get)
            max_count = voice_counts[max_voice]

            # 检查是否为混合视角
            other_counts = [count for voice, count in voice_counts.items() if voice != max_voice]
            if other_counts and max(other_counts) > max_count * 0.3:
                return NarrativeVoice.MIXED

            return max_voice

        except Exception as e:
            logger.error(f"检测叙述视角失败: {e}")
            return NarrativeVoice.THIRD_PERSON

    def _analyze_writing_style(self, content: str) -> WritingStyle:
        """分析写作风格"""
        try:
            sentences = self._split_sentences(content)

            if not sentences:
                return WritingStyle()

            # 计算句子长度统计
            sentence_lengths = [len(s) for s in sentences]
            avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)

            # 分析句子复杂度
            complex_sentences = sum(1 for s in sentences if self._is_complex_sentence(s))
            complexity_ratio = complex_sentences / len(sentences)

            # 确定复杂度级别
            if avg_sentence_length < 15 and complexity_ratio < 0.2:
                sentence_complexity = WritingComplexity.SIMPLE
            elif avg_sentence_length < 25 and complexity_ratio < 0.4:
                sentence_complexity = WritingComplexity.MODERATE
            elif avg_sentence_length < 35 and complexity_ratio < 0.6:
                sentence_complexity = WritingComplexity.COMPLEX
            else:
                sentence_complexity = WritingComplexity.SOPHISTICATED

            # 计算描述性密度
            descriptive_words = self._count_descriptive_words(content)
            descriptive_density = descriptive_words / len(content.split()) if content.split() else 0

            # 计算对话频率
            dialogue_count = content.count('"') + content.count('"')
            dialogue_frequency = dialogue_count / len(sentences) if sentences else 0

            # 计算词汇丰富度
            words = list(jieba.cut(content))
            unique_words = len(set(words))
            vocabulary_richness = unique_words / len(words) if words else 0

            # 评估文学性
            literary_sophistication = self._assess_literary_sophistication(content)

            return WritingStyle(
                sentence_complexity=sentence_complexity,
                avg_sentence_length=avg_sentence_length,
                descriptive_density=descriptive_density,
                dialogue_frequency=dialogue_frequency,
                literary_sophistication=literary_sophistication,
                vocabulary_richness=vocabulary_richness
            )

        except Exception as e:
            logger.error(f"分析写作风格失败: {e}")
            return WritingStyle()

    def _split_sentences(self, content: str) -> List[str]:
        """分割句子"""
        # 中文句子分割
        sentence_endings = ['。', '！', '？', '…', '；']
        sentences = []
        current_sentence = ""

        for char in content:
            current_sentence += char
            if char in sentence_endings:
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""

        # 添加最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return sentences

    def _is_complex_sentence(self, sentence: str) -> bool:
        """判断是否为复杂句子"""
        # 复杂句子的特征
        complex_indicators = ['虽然', '尽管', '不仅', '而且', '因为', '所以', '如果', '那么']
        return any(indicator in sentence for indicator in complex_indicators)

    def _count_descriptive_words(self, content: str) -> int:
        """计算描述性词汇数量"""
        descriptive_patterns = [
            r'[形容词]+的',  # 形容词+的
            r'[副词]+地',    # 副词+地
        ]

        descriptive_words = ['美丽', '漂亮', '优雅', '壮观', '宁静', '热闹', '繁华', '古老']

        count = 0
        for word in descriptive_words:
            count += content.count(word)

        return count

    def _assess_literary_sophistication(self, content: str) -> float:
        """评估文学性"""
        try:
            # 文学性指标
            literary_indicators = {
                '修辞手法': ['比喻', '拟人', '排比', '对偶'],
                '文学词汇': ['诗意', '韵味', '意境', '神韵'],
                '深度表达': ['内心', '灵魂', '精神', '哲理']
            }

            total_score = 0
            max_score = 0

            for category, indicators in literary_indicators.items():
                category_score = sum(content.count(word) for word in indicators)
                total_score += category_score
                max_score += len(indicators)

            # 标准化到0-1范围
            if max_score > 0:
                return min(total_score / max_score, 1.0)
            else:
                return 0.0

        except Exception as e:
            logger.error(f"评估文学性失败: {e}")
            return 0.0

    def _extract_character_info(self, content: str) -> Dict[str, CharacterInfo]:
        """提取角色信息"""
        try:
            characters = {}

            # 使用正则表达式查找可能的角色名
            # 中文姓名模式
            name_patterns = [
                r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}',
                r'[A-Z][a-z]+',  # 英文名
            ]

            for pattern in name_patterns:
                matches = re.findall(pattern, content)
                for name in matches:
                    if len(name) >= 2 and len(name) <= 4:  # 合理的姓名长度
                        if name not in characters:
                            characters[name] = CharacterInfo(name=name)
                        characters[name].mentions += 1

            # 分析对话
            dialogue_pattern = r'"([^"]*)"'
            dialogues = re.findall(dialogue_pattern, content)

            # 简单的对话归属分析
            for dialogue in dialogues:
                # 查找对话前后的角色名
                for name in characters:
                    if name in dialogue or content.find(dialogue) > content.find(name):
                        characters[name].dialogue_count += 1
                        break

            logger.debug(f"提取角色信息: {len(characters)} 个角色")
            return characters

        except Exception as e:
            logger.error(f"提取角色信息失败: {e}")
            return {}

    def _analyze_plot_structure(self, content: str) -> PlotStructure:
        """分析情节结构"""
        try:
            # 情节阶段指示词
            stage_indicators = {
                '开端': ['开始', '起初', '最初', '首先'],
                '发展': ['然后', '接着', '随后', '后来'],
                '高潮': ['突然', '忽然', '瞬间', '终于'],
                '结局': ['最后', '最终', '结果', '终于']
            }

            # 分析当前阶段
            stage_scores = {}
            for stage, indicators in stage_indicators.items():
                score = sum(content.count(word) for word in indicators)
                stage_scores[stage] = score

            current_stage = max(stage_scores, key=stage_scores.get) if stage_scores else "发展"

            # 分析紧张程度
            tension_words = ['紧张', '危险', '急迫', '焦虑', '担心', '害怕']
            tension_count = sum(content.count(word) for word in tension_words)
            tension_level = min(tension_count / 10, 1.0)  # 标准化到0-1

            # 分析节奏
            sentence_count = len(self._split_sentences(content))
            avg_sentence_length = len(content) / sentence_count if sentence_count > 0 else 0

            if avg_sentence_length < 15:
                pacing = "fast"
            elif avg_sentence_length > 30:
                pacing = "slow"
            else:
                pacing = "moderate"

            return PlotStructure(
                current_stage=current_stage,
                tension_level=tension_level,
                pacing=pacing,
                conflict_intensity=tension_level,  # 简化处理
                character_development=0.5  # 默认值
            )

        except Exception as e:
            logger.error(f"分析情节结构失败: {e}")
            return PlotStructure()

    def _analyze_emotional_tone(self, content: str) -> EmotionalTone:
        """分析情感基调"""
        try:
            emotion_scores = {}

            for tone, words in self.emotion_words.items():
                score = sum(content.count(word) for word in words)
                emotion_scores[tone] = score

            if not any(emotion_scores.values()):
                return EmotionalTone.NEUTRAL

            # 找到主导情感
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[dominant_emotion]

            # 检查是否为混合情感
            other_scores = [score for tone, score in emotion_scores.items() if tone != dominant_emotion]
            if other_scores and max(other_scores) > max_score * 0.5:
                return EmotionalTone.MIXED

            return dominant_emotion

        except Exception as e:
            logger.error(f"分析情感基调失败: {e}")
            return EmotionalTone.NEUTRAL

    def _extract_scene_setting(self, content: str) -> SceneSetting:
        """提取场景设定"""
        try:
            # 地点词汇
            location_words = ['房间', '客厅', '卧室', '厨房', '花园', '公园', '街道', '学校', '办公室']
            detected_locations = [word for word in location_words if word in content]
            location = detected_locations[0] if detected_locations else "unknown"

            # 时间词汇
            time_words = ['早晨', '上午', '中午', '下午', '傍晚', '晚上', '深夜', '春天', '夏天', '秋天', '冬天']
            detected_times = [word for word in time_words if word in content]
            time_period = detected_times[0] if detected_times else "unknown"

            # 氛围词汇
            atmosphere_words = {
                'peaceful': ['宁静', '安详', '平和'],
                'tense': ['紧张', '压抑', '沉重'],
                'joyful': ['欢快', '热闹', '活跃'],
                'melancholic': ['忧郁', '悲伤', '沉闷']
            }

            atmosphere = "neutral"
            for mood, words in atmosphere_words.items():
                if any(word in content for word in words):
                    atmosphere = mood
                    break

            return SceneSetting(
                location=location,
                time_period=time_period,
                atmosphere=atmosphere,
                sensory_details=self._extract_sensory_details(content)
            )

        except Exception as e:
            logger.error(f"提取场景设定失败: {e}")
            return SceneSetting()

    def _extract_sensory_details(self, content: str) -> List[str]:
        """提取感官细节"""
        sensory_patterns = {
            '视觉': ['看到', '看见', '观察', '注视', '颜色', '光线'],
            '听觉': ['听到', '听见', '声音', '音乐', '噪音'],
            '触觉': ['触摸', '感受', '温度', '质感'],
            '嗅觉': ['闻到', '香味', '气味'],
            '味觉': ['尝到', '味道', '甜', '苦', '酸']
        }

        detected_details = []
        for sense, words in sensory_patterns.items():
            if any(word in content for word in words):
                detected_details.append(sense)

        return detected_details

    def _detect_literary_devices(self, content: str) -> List[str]:
        """检测文学手法"""
        detected_devices = []

        for device, indicators in self.literary_devices.items():
            if any(indicator in content for indicator in indicators):
                detected_devices.append(device)

        return detected_devices

    def _detect_genre_indicators(self, content: str) -> List[str]:
        """检测文体指示器"""
        genre_patterns = {
            '言情': ['爱情', '恋爱', '情感', '浪漫'],
            '悬疑': ['谜团', '线索', '调查', '真相'],
            '科幻': ['科技', '未来', '机器人', '太空'],
            '奇幻': ['魔法', '精灵', '龙', '魔兽'],
            '历史': ['古代', '朝代', '皇帝', '宫廷']
        }

        detected_genres = []
        for genre, indicators in genre_patterns.items():
            if any(indicator in content for indicator in indicators):
                detected_genres.append(genre)

        return detected_genres

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        try:
            # 使用jieba分词
            words = list(jieba.cut(content))

            # 过滤停用词
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}

            filtered_words = [word for word in words if word not in stop_words and len(word) > 1]

            # 统计词频
            word_freq = Counter(filtered_words)

            # 返回前10个高频词
            keywords = [word for word, freq in word_freq.most_common(10)]

            return keywords

        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
            return []

    def _extract_themes(self, content: str) -> List[str]:
        """提取主题"""
        theme_patterns = {
            '成长': ['成长', '学习', '进步', '改变'],
            '友情': ['朋友', '友谊', '伙伴', '同伴'],
            '亲情': ['家人', '父母', '兄弟', '姐妹'],
            '爱情': ['爱情', '恋爱', '情侣', '爱人'],
            '冒险': ['冒险', '探险', '旅行', '发现'],
            '正义': ['正义', '公平', '善良', '帮助']
        }

        detected_themes = []
        for theme, indicators in theme_patterns.items():
            if any(indicator in content for indicator in indicators):
                detected_themes.append(theme)

        return detected_themes

    def _create_default_context(self) -> WritingContext:
        """创建默认上下文"""
        return WritingContext(
            narrative_voice=NarrativeVoice.THIRD_PERSON,
            writing_style=WritingStyle(),
            character_analysis={},
            plot_structure=PlotStructure(),
            emotional_tone=EmotionalTone.NEUTRAL,
            scene_setting=SceneSetting(),
            literary_devices=[],
            genre_indicators=[],
            keywords=[],
            themes=[]
        )

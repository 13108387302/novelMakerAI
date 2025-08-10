"""
智能写作助手

提供实时写作建议、风格检查和创作灵感推荐，显著提升写作效率和质量。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import re
import time
import threading
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque

from src.application.services.ai.intelligence.deep_context_analyzer import WritingContext
from src.application.services.ai.intelligence.singleton import get_deep_context_analyzer
from src.application.services.ai.intelligence.intelligent_prompt_builder import IntelligentPromptBuilder
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class SuggestionType(Enum):
    """建议类型"""
    GRAMMAR = "grammar"                   # 语法建议
    STYLE = "style"                       # 风格建议
    STRUCTURE = "structure"               # 结构建议
    VOCABULARY = "vocabulary"             # 词汇建议
    FLOW = "flow"                         # 流畅性建议
    CREATIVITY = "creativity"             # 创意建议
    CHARACTER = "character"               # 角色建议
    PLOT = "plot"                         # 情节建议
    DIALOGUE = "dialogue"                 # 对话建议
    DESCRIPTION = "description"           # 描述建议


class SuggestionPriority(Enum):
    """建议优先级"""
    LOW = "low"                          # 低优先级
    MEDIUM = "medium"                    # 中优先级
    HIGH = "high"                        # 高优先级
    CRITICAL = "critical"                # 关键优先级


@dataclass
class WritingSuggestion:
    """写作建议"""
    suggestion_id: str
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    original_text: str = ""
    suggested_text: str = ""
    position: int = -1                   # 在文档中的位置
    confidence: float = 0.0              # 建议置信度 (0-1)
    reasoning: str = ""                  # 建议理由
    timestamp: datetime = field(default_factory=datetime.now)
    applied: bool = False                # 是否已应用
    dismissed: bool = False              # 是否已忽略


@dataclass
class WritingInsight:
    """写作洞察"""
    insight_type: str
    title: str
    content: str
    actionable_tips: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WritingStats:
    """写作统计"""
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    reading_time_minutes: float = 0.0
    complexity_score: float = 0.0
    readability_score: float = 0.0


class IntelligentWritingAssistant:
    """
    智能写作助手
    
    提供全面的写作辅助功能：
    1. 实时写作建议：语法、风格、结构等多维度建议
    2. 智能风格检查：保持写作风格一致性
    3. 创作灵感推荐：基于上下文的创意建议
    4. 写作统计分析：详细的写作数据分析
    5. 个性化建议：基于用户写作习惯的定制建议
    6. 实时反馈：即时的写作质量评估
    """
    
    def __init__(self):
        # 核心分析组件
        self._context_analyzer = get_deep_context_analyzer()
        self._prompt_builder = IntelligentPromptBuilder(self._context_analyzer)

        # 建议系统
        self._suggestions: Dict[str, WritingSuggestion] = {}
        self._suggestion_history: deque = deque(maxlen=1000)
        self._active_suggestions: Set[str] = set()
        
        # 洞察系统
        self._insights: List[WritingInsight] = []
        self._insight_cache: Dict[str, WritingInsight] = {}
        
        # 实时分析
        self._analysis_enabled = True
        self._analysis_thread: Optional[threading.Thread] = None
        self._analysis_queue: deque = deque()
        self._stop_analysis = threading.Event()
        
        # 用户偏好
        self._user_preferences = {
            'suggestion_frequency': 'medium',  # low, medium, high
            'auto_apply_grammar': False,
            'show_style_suggestions': True,
            'creativity_level': 'balanced',    # conservative, balanced, creative
            'preferred_writing_style': 'adaptive'
        }
        
        # 写作模式
        self._writing_modes = {
            'focus_mode': False,              # 专注模式，减少干扰
            'creative_mode': False,           # 创意模式，更多灵感建议
            'editing_mode': False,            # 编辑模式，更多修改建议
            'learning_mode': False            # 学习模式，详细解释
        }
        
        # 统计数据
        self._writing_stats = WritingStats()
        self._session_stats = {
            'start_time': datetime.now(),
            'words_written': 0,
            'suggestions_accepted': 0,
            'suggestions_dismissed': 0
        }
        
        # 回调函数
        self._suggestion_callbacks: List[Callable[[WritingSuggestion], None]] = []
        self._insight_callbacks: List[Callable[[WritingInsight], None]] = []
        self._stats_callbacks: List[Callable[[WritingStats], None]] = []
        
        # 启动实时分析
        self._start_analysis_thread()
        
        logger.info("智能写作助手初始化完成")
    
    def _start_analysis_thread(self):
        """启动分析线程"""
        if self._analysis_thread and self._analysis_thread.is_alive():
            return
        
        self._analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._analysis_thread.start()
        
        logger.debug("写作分析线程已启动")
    
    def _analysis_loop(self):
        """分析主循环"""
        try:
            while not self._stop_analysis.is_set():
                try:
                    if self._analysis_queue:
                        # 处理分析请求
                        analysis_request = self._analysis_queue.popleft()
                        self._process_analysis_request(analysis_request)
                    else:
                        # 等待新的分析请求
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"写作分析循环异常: {e}")
                    time.sleep(1.0)
                    
        except Exception as e:
            logger.error(f"写作分析线程异常: {e}")
    
    def analyze_text_realtime(self, text: str, cursor_position: int = -1, selected_text: str = ""):
        """实时分析文本"""
        try:
            if not self._analysis_enabled:
                return
            
            # 添加到分析队列
            analysis_request = {
                'text': text,
                'cursor_position': cursor_position,
                'selected_text': selected_text,
                'timestamp': datetime.now(),
                'request_id': f"analysis_{int(time.time() * 1000)}"
            }
            
            self._analysis_queue.append(analysis_request)
            
            # 限制队列大小
            if len(self._analysis_queue) > 10:
                self._analysis_queue.popleft()
            
        except Exception as e:
            logger.error(f"实时文本分析失败: {e}")
    
    def _process_analysis_request(self, request: Dict[str, Any]):
        """处理分析请求"""
        try:
            text = request['text']
            cursor_position = request.get('cursor_position', -1)
            selected_text = request.get('selected_text', '')
            
            # 更新写作统计
            self._update_writing_stats(text)
            
            # 生成写作建议
            suggestions = self._generate_suggestions(text, cursor_position, selected_text)
            
            # 处理新建议
            for suggestion in suggestions:
                self._add_suggestion(suggestion)
            
            # 生成写作洞察
            if len(text) > 500:  # 只对较长文本生成洞察
                insights = self._generate_insights(text)
                for insight in insights:
                    self._add_insight(insight)
            
        except Exception as e:
            logger.error(f"处理分析请求失败: {e}")
    
    def _generate_suggestions(self, text: str, cursor_position: int, selected_text: str) -> List[WritingSuggestion]:
        """生成写作建议"""
        suggestions = []
        
        try:
            # 分析写作上下文
            writing_context = self._context_analyzer.analyze_writing_context(text)
            
            # 语法检查建议
            grammar_suggestions = self._check_grammar(text, writing_context)
            suggestions.extend(grammar_suggestions)
            
            # 风格一致性建议
            style_suggestions = self._check_style_consistency(text, writing_context)
            suggestions.extend(style_suggestions)
            
            # 结构优化建议
            structure_suggestions = self._check_structure(text, writing_context)
            suggestions.extend(structure_suggestions)
            
            # 词汇丰富性建议
            vocabulary_suggestions = self._check_vocabulary(text, writing_context)
            suggestions.extend(vocabulary_suggestions)
            
            # 创意建议
            if self._writing_modes['creative_mode']:
                creativity_suggestions = self._generate_creativity_suggestions(text, writing_context)
                suggestions.extend(creativity_suggestions)
            
            # 根据选中文本生成特定建议
            if selected_text:
                selection_suggestions = self._generate_selection_suggestions(selected_text, text, writing_context)
                suggestions.extend(selection_suggestions)
            
        except Exception as e:
            logger.error(f"生成写作建议失败: {e}")
        
        return suggestions
    
    def _check_grammar(self, text: str, context: WritingContext) -> List[WritingSuggestion]:
        """检查语法问题"""
        suggestions = []
        
        try:
            # 常见语法问题检查
            grammar_issues = [
                # 标点符号问题
                (r'[，。！？；：]([a-zA-Z])', '中英文之间缺少空格'),
                (r'([a-zA-Z])[，。！？；：]', '英文后标点符号使用错误'),
                (r'[。！？]{2,}', '重复的句号'),
                (r'[，；：]{2,}', '重复的逗号或分号'),
                
                # 引号问题
                (r'"[^"]*"[^，。！？；：\s]', '引号后缺少标点'),
                (r'[^，。！？；：\s]"[^"]*"', '引号前缺少标点'),
                
                # 常见错别字
                (r'的地得', '的地得使用混乱'),
                (r'在再', '在再使用错误'),
            ]
            
            for pattern, issue_desc in grammar_issues:
                matches = list(re.finditer(pattern, text))
                for match in matches:
                    suggestion = WritingSuggestion(
                        suggestion_id=f"grammar_{match.start()}_{int(time.time())}",
                        suggestion_type=SuggestionType.GRAMMAR,
                        priority=SuggestionPriority.HIGH,
                        title="语法问题",
                        description=issue_desc,
                        original_text=match.group(),
                        position=match.start(),
                        confidence=0.8,
                        reasoning=f"检测到语法问题：{issue_desc}"
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"语法检查失败: {e}")
        
        return suggestions
    
    def _check_style_consistency(self, text: str, context: WritingContext) -> List[WritingSuggestion]:
        """检查风格一致性"""
        suggestions = []
        
        try:
            # 叙述视角一致性检查
            if context.narrative_voice.value == 'mixed':
                suggestion = WritingSuggestion(
                    suggestion_id=f"style_voice_{int(time.time())}",
                    suggestion_type=SuggestionType.STYLE,
                    priority=SuggestionPriority.MEDIUM,
                    title="叙述视角不一致",
                    description="文本中混合使用了不同的叙述视角，建议保持一致",
                    confidence=0.7,
                    reasoning="检测到混合的叙述视角，可能影响阅读体验"
                )
                suggestions.append(suggestion)
            
            # 情感基调一致性检查
            if context.emotional_tone.value == 'mixed':
                suggestion = WritingSuggestion(
                    suggestion_id=f"style_tone_{int(time.time())}",
                    suggestion_type=SuggestionType.STYLE,
                    priority=SuggestionPriority.LOW,
                    title="情感基调变化",
                    description="文本的情感基调有所变化，确认是否符合创作意图",
                    confidence=0.6,
                    reasoning="检测到情感基调的变化"
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"风格一致性检查失败: {e}")
        
        return suggestions
    
    def _check_structure(self, text: str, context: WritingContext) -> List[WritingSuggestion]:
        """检查结构问题"""
        suggestions = []
        
        try:
            # 段落长度检查
            paragraphs = text.split('\n\n')
            for i, paragraph in enumerate(paragraphs):
                if len(paragraph) > 500:  # 段落过长
                    suggestion = WritingSuggestion(
                        suggestion_id=f"structure_long_para_{i}_{int(time.time())}",
                        suggestion_type=SuggestionType.STRUCTURE,
                        priority=SuggestionPriority.LOW,
                        title="段落过长",
                        description=f"第{i+1}段较长，建议分割为多个段落以提高可读性",
                        confidence=0.6,
                        reasoning="长段落可能影响阅读体验"
                    )
                    suggestions.append(suggestion)
            
            # 句子长度检查
            sentences = re.split(r'[。！？]', text)
            for i, sentence in enumerate(sentences):
                if len(sentence) > 100:  # 句子过长
                    suggestion = WritingSuggestion(
                        suggestion_id=f"structure_long_sent_{i}_{int(time.time())}",
                        suggestion_type=SuggestionType.STRUCTURE,
                        priority=SuggestionPriority.LOW,
                        title="句子过长",
                        description="句子较长，建议分解为多个短句",
                        original_text=sentence[:50] + "...",
                        confidence=0.5,
                        reasoning="长句子可能影响理解"
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"结构检查失败: {e}")
        
        return suggestions
    
    def _check_vocabulary(self, text: str, context: WritingContext) -> List[WritingSuggestion]:
        """检查词汇使用"""
        suggestions = []
        
        try:
            # 重复词汇检查
            words = re.findall(r'[\u4e00-\u9fff]+', text)  # 提取中文词汇
            word_counts = defaultdict(int)
            
            for word in words:
                if len(word) >= 2:  # 只检查2字以上的词
                    word_counts[word] += 1
            
            # 找出过度重复的词汇
            for word, count in word_counts.items():
                if count > 5 and len(word) >= 3:  # 3字以上词汇重复超过5次
                    suggestion = WritingSuggestion(
                        suggestion_id=f"vocab_repeat_{word}_{int(time.time())}",
                        suggestion_type=SuggestionType.VOCABULARY,
                        priority=SuggestionPriority.MEDIUM,
                        title="词汇重复",
                        description=f"'{word}'重复使用{count}次，建议使用同义词替换",
                        original_text=word,
                        confidence=0.7,
                        reasoning=f"词汇'{word}'使用频率过高"
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"词汇检查失败: {e}")
        
        return suggestions
    
    def _generate_creativity_suggestions(self, text: str, context: WritingContext) -> List[WritingSuggestion]:
        """生成创意建议"""
        suggestions = []
        
        try:
            # 基于文学手法的创意建议
            if not context.literary_devices:
                suggestion = WritingSuggestion(
                    suggestion_id=f"creativity_devices_{int(time.time())}",
                    suggestion_type=SuggestionType.CREATIVITY,
                    priority=SuggestionPriority.LOW,
                    title="增加文学手法",
                    description="可以尝试使用比喻、拟人等文学手法来增强表现力",
                    confidence=0.5,
                    reasoning="文本中缺少文学修辞手法"
                )
                suggestions.append(suggestion)
            
            # 基于角色发展的建议
            if context.character_analysis and len(context.character_analysis) > 0:
                suggestion = WritingSuggestion(
                    suggestion_id=f"creativity_character_{int(time.time())}",
                    suggestion_type=SuggestionType.CHARACTER,
                    priority=SuggestionPriority.MEDIUM,
                    title="角色发展建议",
                    description="可以进一步深化角色的内心世界和性格特征",
                    confidence=0.6,
                    reasoning="检测到角色信息，可以进一步发展"
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"生成创意建议失败: {e}")
        
        return suggestions
    
    def _generate_selection_suggestions(self, selected_text: str, full_text: str, context: WritingContext) -> List[WritingSuggestion]:
        """生成选中文本的建议"""
        suggestions = []
        
        try:
            # 扩展建议
            if len(selected_text) < 50:
                suggestion = WritingSuggestion(
                    suggestion_id=f"selection_expand_{int(time.time())}",
                    suggestion_type=SuggestionType.CREATIVITY,
                    priority=SuggestionPriority.MEDIUM,
                    title="内容扩展",
                    description="选中的内容较短，可以考虑添加更多细节描述",
                    original_text=selected_text,
                    confidence=0.6,
                    reasoning="选中文本较短，有扩展空间"
                )
                suggestions.append(suggestion)
            
            # 对话优化建议
            if '"' in selected_text:
                suggestion = WritingSuggestion(
                    suggestion_id=f"selection_dialogue_{int(time.time())}",
                    suggestion_type=SuggestionType.DIALOGUE,
                    priority=SuggestionPriority.MEDIUM,
                    title="对话优化",
                    description="可以为对话添加更多的动作描写和心理活动",
                    original_text=selected_text,
                    confidence=0.7,
                    reasoning="检测到对话内容"
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            logger.error(f"生成选中文本建议失败: {e}")
        
        return suggestions
    
    def _generate_insights(self, text: str) -> List[WritingInsight]:
        """生成写作洞察"""
        insights = []
        
        try:
            # 分析写作上下文
            context = self._context_analyzer.analyze_writing_context(text)
            
            # 写作风格洞察
            style_insight = WritingInsight(
                insight_type="writing_style",
                title="写作风格分析",
                content=f"您的写作风格：{context.writing_style.get_description()}",
                actionable_tips=[
                    "保持风格一致性",
                    "适当调整句式长度",
                    "注意叙述节奏"
                ]
            )
            insights.append(style_insight)
            
            # 主题洞察
            if context.themes:
                theme_insight = WritingInsight(
                    insight_type="themes",
                    title="主题分析",
                    content=f"识别到的主题：{', '.join(context.themes)}",
                    actionable_tips=[
                        "深化主题表达",
                        "通过情节强化主题",
                        "保持主题连贯性"
                    ]
                )
                insights.append(theme_insight)
            
        except Exception as e:
            logger.error(f"生成写作洞察失败: {e}")
        
        return insights
    
    def _update_writing_stats(self, text: str):
        """更新写作统计"""
        try:
            # 基本统计
            self._writing_stats.word_count = len(re.findall(r'[\u4e00-\u9fff]', text))
            self._writing_stats.character_count = len(text)
            self._writing_stats.paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
            
            sentences = re.split(r'[。！？]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            self._writing_stats.sentence_count = len(sentences)
            
            if sentences:
                self._writing_stats.avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
            
            # 阅读时间估算（按每分钟200字计算）
            self._writing_stats.reading_time_minutes = self._writing_stats.word_count / 200
            
            # 通知统计回调
            for callback in self._stats_callbacks:
                try:
                    callback(self._writing_stats)
                except Exception as e:
                    logger.error(f"统计回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"更新写作统计失败: {e}")
    
    def _add_suggestion(self, suggestion: WritingSuggestion):
        """添加建议"""
        try:
            # 检查是否已存在相似建议
            existing_key = f"{suggestion.suggestion_type.value}_{suggestion.position}"
            if existing_key in self._active_suggestions:
                return
            
            self._suggestions[suggestion.suggestion_id] = suggestion
            self._active_suggestions.add(existing_key)
            
            # 通知建议回调
            for callback in self._suggestion_callbacks:
                try:
                    callback(suggestion)
                except Exception as e:
                    logger.error(f"建议回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"添加建议失败: {e}")
    
    def _add_insight(self, insight: WritingInsight):
        """添加洞察"""
        try:
            # 检查缓存，避免重复
            cache_key = f"{insight.insight_type}_{hash(insight.content)}"
            if cache_key in self._insight_cache:
                return
            
            self._insights.append(insight)
            self._insight_cache[cache_key] = insight
            
            # 限制洞察数量
            if len(self._insights) > 50:
                self._insights = self._insights[-50:]
            
            # 通知洞察回调
            for callback in self._insight_callbacks:
                try:
                    callback(insight)
                except Exception as e:
                    logger.error(f"洞察回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"添加洞察失败: {e}")
    
    def apply_suggestion(self, suggestion_id: str) -> bool:
        """应用建议"""
        try:
            if suggestion_id not in self._suggestions:
                return False
            
            suggestion = self._suggestions[suggestion_id]
            suggestion.applied = True
            
            # 更新会话统计
            self._session_stats['suggestions_accepted'] += 1
            
            logger.info(f"建议已应用: {suggestion.title}")
            return True
            
        except Exception as e:
            logger.error(f"应用建议失败: {e}")
            return False
    
    def dismiss_suggestion(self, suggestion_id: str) -> bool:
        """忽略建议"""
        try:
            if suggestion_id not in self._suggestions:
                return False
            
            suggestion = self._suggestions[suggestion_id]
            suggestion.dismissed = True
            
            # 更新会话统计
            self._session_stats['suggestions_dismissed'] += 1
            
            logger.debug(f"建议已忽略: {suggestion.title}")
            return True
            
        except Exception as e:
            logger.error(f"忽略建议失败: {e}")
            return False
    
    def get_active_suggestions(self, limit: int = 10) -> List[WritingSuggestion]:
        """获取活跃建议"""
        try:
            active = [s for s in self._suggestions.values() 
                     if not s.applied and not s.dismissed]
            
            # 按优先级和置信度排序
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            active.sort(key=lambda s: (priority_order.get(s.priority.value, 4), -s.confidence))
            
            return active[:limit]
            
        except Exception as e:
            logger.error(f"获取活跃建议失败: {e}")
            return []
    
    def get_writing_stats(self) -> WritingStats:
        """获取写作统计"""
        return self._writing_stats
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计"""
        session_time = (datetime.now() - self._session_stats['start_time']).total_seconds() / 60
        
        return {
            **self._session_stats,
            'session_time_minutes': session_time,
            'words_per_minute': self._session_stats['words_written'] / max(session_time, 1),
            'suggestion_acceptance_rate': (
                self._session_stats['suggestions_accepted'] / 
                max(self._session_stats['suggestions_accepted'] + self._session_stats['suggestions_dismissed'], 1)
            )
        }
    
    def get_recent_insights(self, limit: int = 5) -> List[WritingInsight]:
        """获取最近的洞察"""
        return self._insights[-limit:] if self._insights else []
    
    def set_writing_mode(self, mode: str, enabled: bool):
        """设置写作模式"""
        if mode in self._writing_modes:
            self._writing_modes[mode] = enabled
            logger.info(f"写作模式 {mode}: {'启用' if enabled else '禁用'}")
    
    def set_user_preference(self, key: str, value: Any):
        """设置用户偏好"""
        if key in self._user_preferences:
            self._user_preferences[key] = value
            logger.info(f"用户偏好已更新: {key} = {value}")
    
    def add_suggestion_callback(self, callback: Callable[[WritingSuggestion], None]):
        """添加建议回调"""
        self._suggestion_callbacks.append(callback)
    
    def add_insight_callback(self, callback: Callable[[WritingInsight], None]):
        """添加洞察回调"""
        self._insight_callbacks.append(callback)
    
    def add_stats_callback(self, callback: Callable[[WritingStats], None]):
        """添加统计回调"""
        self._stats_callbacks.append(callback)
    
    def shutdown(self):
        """关闭写作助手"""
        try:
            logger.info("关闭智能写作助手")
            
            # 停止分析线程
            self._stop_analysis.set()
            if self._analysis_thread and self._analysis_thread.is_alive():
                self._analysis_thread.join(timeout=5.0)
            
            # 清理资源
            self._suggestions.clear()
            self._insights.clear()
            self._analysis_queue.clear()
            
            logger.info("智能写作助手已关闭")
            
        except Exception as e:
            logger.error(f"关闭写作助手失败: {e}")


# 全局写作助手实例
_global_writing_assistant = None

def get_writing_assistant() -> IntelligentWritingAssistant:
    """获取全局写作助手"""
    global _global_writing_assistant
    if _global_writing_assistant is None:
        _global_writing_assistant = IntelligentWritingAssistant()
    return _global_writing_assistant

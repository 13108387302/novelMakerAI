#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级统计分析服务

提供深度分析、可视化图表、写作习惯分析等功能
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import statistics

from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.document_repository import IDocumentRepository
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WritingPattern:
    """写作模式"""
    peak_hours: List[int] = field(default_factory=list)
    average_session_duration: float = 0.0
    words_per_session: float = 0.0
    most_productive_day: str = ""
    writing_frequency: Dict[str, int] = field(default_factory=dict)
    preferred_document_types: List[str] = field(default_factory=list)


@dataclass
class ContentAnalysis:
    """内容分析"""
    vocabulary_richness: float = 0.0
    average_sentence_length: float = 0.0
    paragraph_length_distribution: Dict[str, int] = field(default_factory=dict)
    common_words: List[Tuple[str, int]] = field(default_factory=list)
    readability_score: float = 0.0
    sentiment_analysis: Dict[str, float] = field(default_factory=dict)


@dataclass
class ProgressAnalysis:
    """进度分析"""
    daily_word_counts: Dict[str, int] = field(default_factory=dict)
    weekly_progress: Dict[str, int] = field(default_factory=dict)
    monthly_progress: Dict[str, int] = field(default_factory=dict)
    completion_rate: float = 0.0
    estimated_completion_date: Optional[str] = None
    productivity_trends: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CharacterAnalysis:
    """角色分析"""
    character_mentions: Dict[str, int] = field(default_factory=dict)
    character_relationships: Dict[str, List[str]] = field(default_factory=dict)
    character_development: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dialogue_distribution: Dict[str, float] = field(default_factory=dict)


class AnalyticsService:
    """高级统计分析服务"""
    
    def __init__(
        self,
        project_repository: IProjectRepository,
        document_repository: IDocumentRepository,
        data_dir: Path
    ):
        self.project_repository = project_repository
        self.document_repository = document_repository
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 分析数据库
        self.analytics_db = data_dir / "analytics.db"
        self._init_analytics_database()
        
        logger.debug("高级统计分析服务初始化完成")
    
    def _init_analytics_database(self):
        """初始化分析数据库"""
        try:
            with sqlite3.connect(self.analytics_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS writing_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        words_written INTEGER DEFAULT 0,
                        characters_written INTEGER DEFAULT 0,
                        session_duration INTEGER DEFAULT 0
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS content_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL,
                        analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        word_count INTEGER DEFAULT 0,
                        character_count INTEGER DEFAULT 0,
                        sentence_count INTEGER DEFAULT 0,
                        paragraph_count INTEGER DEFAULT 0,
                        vocabulary_size INTEGER DEFAULT 0,
                        readability_score REAL DEFAULT 0.0,
                        sentiment_score REAL DEFAULT 0.0
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        words_written INTEGER DEFAULT 0,
                        time_spent INTEGER DEFAULT 0,
                        documents_modified INTEGER DEFAULT 0,
                        sessions_count INTEGER DEFAULT 0
                    )
                """)

                # 创建索引以提高查询性能
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON writing_sessions(project_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_document ON writing_sessions(document_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_time ON writing_sessions(start_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_document ON content_metrics(document_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_project ON daily_stats(project_id)")

        except Exception as e:
            logger.error(f"初始化分析数据库失败: {e}")
            raise
    
    async def analyze_writing_patterns(self, project_id: str, days: int = 30) -> WritingPattern:
        """分析写作模式"""
        try:
            pattern = WritingPattern()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.analytics_db) as conn:
                # 分析高峰时段
                cursor = conn.execute("""
                    SELECT strftime('%H', start_time) as hour, COUNT(*) as count
                    FROM writing_sessions 
                    WHERE project_id = ? AND start_time > ?
                    GROUP BY hour
                    ORDER BY count DESC
                    LIMIT 3
                """, (project_id, cutoff_date))
                
                pattern.peak_hours = [int(row[0]) for row in cursor.fetchall()]
                
                # 分析会话时长
                cursor = conn.execute("""
                    SELECT AVG(session_duration), AVG(words_written)
                    FROM writing_sessions 
                    WHERE project_id = ? AND start_time > ?
                """, (project_id, cutoff_date))
                
                row = cursor.fetchone()
                if row and row[0]:
                    pattern.average_session_duration = row[0] / 60  # 转换为分钟
                    pattern.words_per_session = row[1] or 0
                
                # 分析最高产的日期
                cursor = conn.execute("""
                    SELECT strftime('%w', start_time) as day_of_week, SUM(words_written) as total_words
                    FROM writing_sessions 
                    WHERE project_id = ? AND start_time > ?
                    GROUP BY day_of_week
                    ORDER BY total_words DESC
                    LIMIT 1
                """, (project_id, cutoff_date))
                
                row = cursor.fetchone()
                if row:
                    days_map = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
                    pattern.most_productive_day = days_map[int(row[0])]
                
                # 分析写作频率
                cursor = conn.execute("""
                    SELECT date, sessions_count
                    FROM daily_stats 
                    WHERE project_id = ? AND date > ?
                    ORDER BY date
                """, (project_id, cutoff_date.strftime('%Y-%m-%d')))
                
                for row in cursor.fetchall():
                    pattern.writing_frequency[row[0]] = row[1]
            
            # 分析偏好的文档类型
            try:
                documents = await self.document_repository.list_by_project(project_id)
                if documents:
                    doc_type_counts = Counter(
                        doc.document_type.value if hasattr(doc.document_type, 'value')
                        else str(doc.document_type)
                        for doc in documents
                    )
                    pattern.preferred_document_types = [doc_type for doc_type, _ in doc_type_counts.most_common(3)]
            except Exception as e:
                logger.warning(f"分析文档类型偏好失败: {e}")
                pattern.preferred_document_types = []
            
            return pattern
            
        except Exception as e:
            logger.error(f"分析写作模式失败: {e}")
            return WritingPattern()
    
    async def analyze_content(self, document_id: str) -> ContentAnalysis:
        """分析内容"""
        try:
            analysis = ContentAnalysis()
            
            # 获取文档
            document = await self.document_repository.load(document_id)
            if not document or not document.content:
                return analysis
            
            content = document.content
            
            # 基础统计
            words = re.findall(r'\b\w+\b', content.lower())
            sentences = re.split(r'[.!?]+', content)
            paragraphs = content.split('\n\n')
            
            # 词汇丰富度
            unique_words = set(words)
            if words:
                analysis.vocabulary_richness = len(unique_words) / len(words)
            
            # 平均句子长度
            if sentences:
                sentence_lengths = [len(re.findall(r'\b\w+\b', sentence)) for sentence in sentences if sentence.strip()]
                if sentence_lengths:
                    analysis.average_sentence_length = statistics.mean(sentence_lengths)
            
            # 段落长度分布
            paragraph_lengths = [len(re.findall(r'\b\w+\b', para)) for para in paragraphs if para.strip()]
            if paragraph_lengths:
                length_ranges = {
                    '短段落(1-50词)': sum(1 for length in paragraph_lengths if 1 <= length <= 50),
                    '中段落(51-150词)': sum(1 for length in paragraph_lengths if 51 <= length <= 150),
                    '长段落(151+词)': sum(1 for length in paragraph_lengths if length > 150)
                }
                analysis.paragraph_length_distribution = length_ranges
            
            # 常用词
            word_counts = Counter(words)
            # 过滤常见停用词
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
            filtered_words = {word: count for word, count in word_counts.items() if word not in stop_words and len(word) > 1}
            analysis.common_words = list(Counter(filtered_words).most_common(20))
            
            # 简单的可读性评分（基于句子长度和词汇复杂度）
            if sentence_lengths:
                avg_sentence_length = statistics.mean(sentence_lengths)
                # 简化的可读性评分
                analysis.readability_score = max(0, min(100, 100 - (avg_sentence_length - 15) * 2))
            
            # 保存分析结果到数据库
            with sqlite3.connect(self.analytics_db) as conn:
                conn.execute("""
                    INSERT INTO content_metrics 
                    (document_id, word_count, character_count, sentence_count, paragraph_count, 
                     vocabulary_size, readability_score, sentiment_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document_id,
                    len(words),
                    len(content),
                    len([s for s in sentences if s.strip()]),
                    len([p for p in paragraphs if p.strip()]),
                    len(unique_words),
                    analysis.readability_score,
                    0.0  # 情感分析暂时设为0
                ))
            
            return analysis
            
        except Exception as e:
            logger.error(f"内容分析失败: {e}")
            return ContentAnalysis()
    
    async def analyze_progress(self, project_id: str, days: int = 90) -> ProgressAnalysis:
        """分析进度"""
        try:
            analysis = ProgressAnalysis()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 获取项目信息
            project = await self.project_repository.load(project_id)
            if not project:
                return analysis
            
            with sqlite3.connect(self.analytics_db) as conn:
                # 每日字数统计
                cursor = conn.execute("""
                    SELECT date, words_written
                    FROM daily_stats 
                    WHERE project_id = ? AND date > ?
                    ORDER BY date
                """, (project_id, cutoff_date.strftime('%Y-%m-%d')))
                
                daily_data = dict(cursor.fetchall())
                analysis.daily_word_counts = daily_data
                
                # 周进度统计
                cursor = conn.execute("""
                    SELECT strftime('%Y-W%W', date) as week, SUM(words_written) as total_words
                    FROM daily_stats 
                    WHERE project_id = ? AND date > ?
                    GROUP BY week
                    ORDER BY week
                """, (project_id, cutoff_date.strftime('%Y-%m-%d')))
                
                analysis.weekly_progress = dict(cursor.fetchall())
                
                # 月进度统计
                cursor = conn.execute("""
                    SELECT strftime('%Y-%m', date) as month, SUM(words_written) as total_words
                    FROM daily_stats 
                    WHERE project_id = ? AND date > ?
                    GROUP BY month
                    ORDER BY month
                """, (project_id, cutoff_date.strftime('%Y-%m-%d')))
                
                analysis.monthly_progress = dict(cursor.fetchall())
            
            # 计算完成率（基于目标字数）
            current_words = project.statistics.total_words
            target_words = getattr(project.metadata, 'target_words', 100000)  # 默认目标10万字
            
            if target_words > 0:
                analysis.completion_rate = min(100, (current_words / target_words) * 100)
                
                # 估算完成日期
                if daily_data:
                    recent_days = list(daily_data.values())[-7:]  # 最近7天
                    if recent_days:
                        avg_daily_words = statistics.mean([w for w in recent_days if w > 0])
                        if avg_daily_words > 0:
                            remaining_words = target_words - current_words
                            days_to_complete = remaining_words / avg_daily_words
                            completion_date = datetime.now() + timedelta(days=days_to_complete)
                            analysis.estimated_completion_date = completion_date.strftime('%Y-%m-%d')
            
            # 生产力趋势
            if daily_data:
                dates = sorted(daily_data.keys())
                for i in range(len(dates) - 6):  # 7天移动平均
                    week_dates = dates[i:i+7]
                    week_words = [daily_data[date] for date in week_dates]
                    avg_words = statistics.mean(week_words)
                    
                    analysis.productivity_trends.append({
                        'date': week_dates[-1],
                        'average_words': round(avg_words, 2),
                        'trend': 'up' if i > 0 and avg_words > analysis.productivity_trends[-1]['average_words'] else 'down'
                    })
            
            return analysis
            
        except Exception as e:
            logger.error(f"进度分析失败: {e}")
            return ProgressAnalysis()
    
    async def analyze_characters(self, project_id: str) -> CharacterAnalysis:
        """分析角色"""
        try:
            analysis = CharacterAnalysis()
            
            # 获取项目文档
            documents = await self.document_repository.list_by_project(project_id)
            
            # 获取角色文档
            character_docs = [doc for doc in documents if doc.document_type == DocumentType.CHARACTER]
            chapter_docs = [doc for doc in documents if doc.document_type == DocumentType.CHAPTER]
            
            # 提取角色名称
            character_names = []
            for char_doc in character_docs:
                # 简单提取：使用文档标题作为角色名
                character_names.append(char_doc.metadata.title)
            
            # 在章节中统计角色出现次数
            for chapter in chapter_docs:
                content = chapter.content.lower()
                for char_name in character_names:
                    count = content.count(char_name.lower())
                    if count > 0:
                        analysis.character_mentions[char_name] = analysis.character_mentions.get(char_name, 0) + count
            
            # 简单的对话分析（基于引号）
            total_dialogue_chars = 0
            total_content_chars = 0
            
            for chapter in chapter_docs:
                content = chapter.content
                total_content_chars += len(content)
                
                # 统计引号内的内容
                dialogue_matches = re.findall(r'"([^"]*)"', content)
                dialogue_chars = sum(len(match) for match in dialogue_matches)
                total_dialogue_chars += dialogue_chars
            
            if total_content_chars > 0:
                dialogue_ratio = total_dialogue_chars / total_content_chars
                analysis.dialogue_distribution['对话比例'] = round(dialogue_ratio * 100, 2)
                analysis.dialogue_distribution['叙述比例'] = round((1 - dialogue_ratio) * 100, 2)
            
            return analysis
            
        except Exception as e:
            logger.error(f"角色分析失败: {e}")
            return CharacterAnalysis()
    
    async def generate_comprehensive_report(self, project_id: str) -> Dict[str, Any]:
        """生成综合分析报告"""
        try:
            report = {
                "project_id": project_id,
                "generated_at": datetime.now().isoformat(),
                "writing_patterns": {},
                "content_analysis": {},
                "progress_analysis": {},
                "character_analysis": {},
                "insights": [],
                "recommendations": []
            }
            
            # 获取各项分析
            writing_patterns = await self.analyze_writing_patterns(project_id)
            progress_analysis = await self.analyze_progress(project_id)
            character_analysis = await self.analyze_characters(project_id)
            
            report["writing_patterns"] = asdict(writing_patterns)
            report["progress_analysis"] = asdict(progress_analysis)
            report["character_analysis"] = asdict(character_analysis)
            
            # 生成洞察和建议
            insights, recommendations = self._generate_insights_and_recommendations(
                writing_patterns, progress_analysis, character_analysis
            )
            
            report["insights"] = insights
            report["recommendations"] = recommendations
            
            return report
            
        except Exception as e:
            logger.error(f"生成综合分析报告失败: {e}")
            return {"error": str(e)}
    
    def _generate_insights_and_recommendations(
        self, 
        patterns: WritingPattern, 
        progress: ProgressAnalysis, 
        characters: CharacterAnalysis
    ) -> Tuple[List[str], List[str]]:
        """生成洞察和建议"""
        insights = []
        recommendations = []
        
        # 写作模式洞察
        if patterns.peak_hours:
            insights.append(f"您的写作高峰时段是 {', '.join(map(str, patterns.peak_hours))} 点")
        
        if patterns.average_session_duration > 0:
            insights.append(f"平均写作会话时长为 {patterns.average_session_duration:.1f} 分钟")
        
        if patterns.most_productive_day:
            insights.append(f"最高产的日子是 {patterns.most_productive_day}")
        
        # 进度洞察
        if progress.completion_rate > 0:
            insights.append(f"项目完成度为 {progress.completion_rate:.1f}%")
        
        if progress.estimated_completion_date:
            insights.append(f"预计完成日期为 {progress.estimated_completion_date}")
        
        # 角色洞察
        if characters.character_mentions:
            top_character = max(characters.character_mentions.items(), key=lambda x: x[1])
            insights.append(f"出现最多的角色是 {top_character[0]}，共出现 {top_character[1]} 次")
        
        # 生成建议
        if patterns.average_session_duration < 30:
            recommendations.append("建议延长写作会话时间，每次至少30分钟以提高效率")
        
        if progress.completion_rate < 50 and progress.productivity_trends:
            recent_trend = progress.productivity_trends[-1]['trend'] if progress.productivity_trends else 'stable'
            if recent_trend == 'down':
                recommendations.append("最近写作进度有所下降，建议调整写作计划或寻找新的灵感源")
        
        if len(characters.character_mentions) > 10:
            recommendations.append("角色数量较多，建议关注主要角色的发展，避免角色过于分散")
        
        return insights, recommendations

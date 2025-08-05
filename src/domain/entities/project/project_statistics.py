#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目统计

定义项目的统计信息
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Any, Optional


@dataclass
class WritingSession:
    """写作会话"""
    start_time: datetime
    end_time: Optional[datetime] = None
    words_written: int = 0
    characters_written: int = 0
    session_notes: str = ""
    
    @property
    def duration_minutes(self) -> float:
        """会话持续时间（分钟）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0.0
    
    @property
    def words_per_minute(self) -> float:
        """每分钟字数"""
        duration = self.duration_minutes
        if duration > 0:
            return self.words_written / duration
        return 0.0
    
    def end_session(self, words_written: int = 0, characters_written: int = 0) -> None:
        """结束会话"""
        self.end_time = datetime.now()
        self.words_written = words_written
        self.characters_written = characters_written


@dataclass
class DailyStatistics:
    """每日统计"""
    date: date
    words_written: int = 0
    characters_written: int = 0
    writing_time_minutes: float = 0.0
    sessions_count: int = 0
    
    @property
    def average_words_per_session(self) -> float:
        """平均每次写作字数"""
        if self.sessions_count > 0:
            return self.words_written / self.sessions_count
        return 0.0
    
    @property
    def words_per_minute(self) -> float:
        """每分钟字数"""
        if self.writing_time_minutes > 0:
            return self.words_written / self.writing_time_minutes
        return 0.0


@dataclass
class ProjectStatistics:
    """项目统计信息"""
    # 基础统计
    total_words: int = 0
    total_characters: int = 0
    total_chapters: int = 0
    total_scenes: int = 0
    total_documents: int = 0
    
    # 写作统计
    writing_sessions: int = 0
    total_writing_time_minutes: float = 0.0
    words_today: int = 0
    characters_today: int = 0
    
    # 历史记录
    daily_word_counts: Dict[str, int] = field(default_factory=dict)  # 日期 -> 字数
    daily_statistics: Dict[str, DailyStatistics] = field(default_factory=dict)
    writing_sessions_history: List[WritingSession] = field(default_factory=list)
    
    # 目标追踪
    daily_word_goal: int = 1000
    weekly_word_goal: int = 7000
    monthly_word_goal: int = 30000
    
    # 里程碑
    milestones: Dict[str, datetime] = field(default_factory=dict)  # 里程碑名称 -> 达成时间
    
    def update_word_count(self, word_count: int, character_count: int) -> None:
        """更新字数统计"""
        self.total_words = word_count
        self.total_characters = character_count
        
        # 更新今日字数
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_word_counts:
            self.daily_word_counts[today] = 0
        
        # 计算今日新增字数（简化处理）
        previous_total = sum(self.daily_word_counts.values()) - self.daily_word_counts.get(today, 0)
        self.words_today = max(0, word_count - previous_total)
        self.daily_word_counts[today] = self.words_today
    
    def add_writing_session(self, duration_minutes: float, words_written: int = 0, characters_written: int = 0) -> None:
        """添加写作会话"""
        self.writing_sessions += 1
        self.total_writing_time_minutes += duration_minutes
        
        # 创建写作会话记录
        session = WritingSession(
            start_time=datetime.now(),
            end_time=datetime.now(),
            words_written=words_written,
            characters_written=characters_written
        )
        self.writing_sessions_history.append(session)
        
        # 更新今日统计
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_date = datetime.now().date()
        
        if today_str not in self.daily_statistics:
            self.daily_statistics[today_str] = DailyStatistics(date=today_date)
        
        daily_stats = self.daily_statistics[today_str]
        daily_stats.words_written += words_written
        daily_stats.characters_written += characters_written
        daily_stats.writing_time_minutes += duration_minutes
        daily_stats.sessions_count += 1
        
        # 更新今日字数
        self.words_today += words_written
        self.characters_today += characters_written
    
    def get_average_words_per_session(self) -> float:
        """获取平均每次写作字数"""
        if self.writing_sessions == 0:
            return 0.0
        return self.total_words / self.writing_sessions
    
    def get_words_today(self) -> int:
        """获取今日字数"""
        return self.words_today
    
    def get_words_this_week(self) -> int:
        """获取本周字数"""
        today = datetime.now().date()
        week_start = today - datetime.timedelta(days=today.weekday())
        
        total = 0
        for i in range(7):
            date_str = (week_start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            total += self.daily_word_counts.get(date_str, 0)
        
        return total
    
    def get_words_this_month(self) -> int:
        """获取本月字数"""
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        total = 0
        current_date = month_start
        while current_date.month == today.month:
            date_str = current_date.strftime("%Y-%m-%d")
            total += self.daily_word_counts.get(date_str, 0)
            current_date += datetime.timedelta(days=1)
            if current_date > today:
                break
        
        return total
    
    def get_writing_streak(self) -> int:
        """获取连续写作天数"""
        if not self.daily_word_counts:
            return 0
        
        today = datetime.now().date()
        streak = 0
        
        current_date = today
        while True:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in self.daily_word_counts and self.daily_word_counts[date_str] > 0:
                streak += 1
                current_date -= datetime.timedelta(days=1)
            else:
                break
        
        return streak
    
    def get_productivity_trend(self, days: int = 30) -> List[tuple[str, int]]:
        """获取生产力趋势（最近N天）"""
        today = datetime.now().date()
        trend = []
        
        for i in range(days):
            date = today - datetime.timedelta(days=days - 1 - i)
            date_str = date.strftime("%Y-%m-%d")
            words = self.daily_word_counts.get(date_str, 0)
            trend.append((date_str, words))
        
        return trend
    
    def add_milestone(self, name: str, achieved_at: Optional[datetime] = None) -> None:
        """添加里程碑"""
        if achieved_at is None:
            achieved_at = datetime.now()
        self.milestones[name] = achieved_at
    
    def get_milestone(self, name: str) -> Optional[datetime]:
        """获取里程碑时间"""
        return self.milestones.get(name)
    
    def check_daily_goal_achieved(self) -> bool:
        """检查是否达成今日目标"""
        return self.words_today >= self.daily_word_goal
    
    def check_weekly_goal_achieved(self) -> bool:
        """检查是否达成本周目标"""
        return self.get_words_this_week() >= self.weekly_word_goal
    
    def check_monthly_goal_achieved(self) -> bool:
        """检查是否达成本月目标"""
        return self.get_words_this_month() >= self.monthly_word_goal
    
    def get_goal_progress(self) -> Dict[str, float]:
        """获取目标进度"""
        return {
            "daily": min(1.0, self.words_today / self.daily_word_goal) if self.daily_word_goal > 0 else 0.0,
            "weekly": min(1.0, self.get_words_this_week() / self.weekly_word_goal) if self.weekly_word_goal > 0 else 0.0,
            "monthly": min(1.0, self.get_words_this_month() / self.monthly_word_goal) if self.monthly_word_goal > 0 else 0.0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            "total_words": self.total_words,
            "total_characters": self.total_characters,
            "total_documents": self.total_documents,
            "writing_sessions": self.writing_sessions,
            "total_writing_hours": round(self.total_writing_time_minutes / 60, 2),
            "words_today": self.words_today,
            "words_this_week": self.get_words_this_week(),
            "words_this_month": self.get_words_this_month(),
            "writing_streak": self.get_writing_streak(),
            "average_words_per_session": round(self.get_average_words_per_session(), 2),
            "goal_progress": self.get_goal_progress(),
            "milestones_count": len(self.milestones)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_words": self.total_words,
            "total_characters": self.total_characters,
            "total_chapters": self.total_chapters,
            "total_scenes": self.total_scenes,
            "total_documents": self.total_documents,
            "writing_sessions": self.writing_sessions,
            "total_writing_time_minutes": self.total_writing_time_minutes,
            "words_today": self.words_today,
            "characters_today": self.characters_today,
            "daily_word_counts": self.daily_word_counts.copy(),
            "daily_statistics": {k: {
                "date": v.date.isoformat(),
                "words_written": v.words_written,
                "characters_written": v.characters_written,
                "writing_time_minutes": v.writing_time_minutes,
                "sessions_count": v.sessions_count
            } for k, v in self.daily_statistics.items()},
            "daily_word_goal": self.daily_word_goal,
            "weekly_word_goal": self.weekly_word_goal,
            "monthly_word_goal": self.monthly_word_goal,
            "milestones": {k: v.isoformat() for k, v in self.milestones.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectStatistics':
        """从字典创建统计"""
        stats = cls()
        
        # 基础字段
        for field in ["total_words", "total_characters", "total_chapters", "total_scenes", 
                     "total_documents", "writing_sessions", "total_writing_time_minutes",
                     "words_today", "characters_today", "daily_word_goal", 
                     "weekly_word_goal", "monthly_word_goal"]:
            if field in data:
                setattr(stats, field, data[field])
        
        # 复杂字段
        if "daily_word_counts" in data:
            stats.daily_word_counts = data["daily_word_counts"].copy()
        
        if "daily_statistics" in data:
            for k, v in data["daily_statistics"].items():
                stats.daily_statistics[k] = DailyStatistics(
                    date=datetime.fromisoformat(v["date"]).date(),
                    words_written=v.get("words_written", 0),
                    characters_written=v.get("characters_written", 0),
                    writing_time_minutes=v.get("writing_time_minutes", 0.0),
                    sessions_count=v.get("sessions_count", 0)
                )
        
        if "milestones" in data:
            stats.milestones = {k: datetime.fromisoformat(v) for k, v in data["milestones"].items()}
        
        return stats

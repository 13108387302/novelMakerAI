#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI质量指标值对象

定义AI响应的质量评估指标
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class AIQualityMetrics:
    """
    AI质量指标
    
    用于评估AI响应的质量和性能
    """
    
    # 基础指标
    response_time: float = 0.0          # 响应时间（秒）
    token_count: int = 0                # Token数量
    word_count: int = 0                 # 字数
    character_count: int = 0            # 字符数
    
    # 质量指标
    relevance_score: float = 0.0        # 相关性评分 (0-1)
    coherence_score: float = 0.0        # 连贯性评分 (0-1)
    creativity_score: float = 0.0       # 创意性评分 (0-1)
    accuracy_score: float = 0.0         # 准确性评分 (0-1)
    
    # 技术指标
    model_confidence: float = 0.0       # 模型置信度 (0-1)
    processing_cost: float = 0.0        # 处理成本
    cache_hit: bool = False             # 是否命中缓存
    
    # 用户反馈
    user_rating: Optional[int] = None   # 用户评分 (1-5)
    user_feedback: Optional[str] = None # 用户反馈
    
    # 时间戳
    created_at: datetime = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def overall_quality_score(self) -> float:
        """计算综合质量评分"""
        scores = [
            self.relevance_score,
            self.coherence_score,
            self.creativity_score,
            self.accuracy_score
        ]
        valid_scores = [score for score in scores if score > 0]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    
    @property
    def performance_grade(self) -> str:
        """获取性能等级"""
        score = self.overall_quality_score
        if score >= 0.9:
            return "A+"
        elif score >= 0.8:
            return "A"
        elif score >= 0.7:
            return "B"
        elif score >= 0.6:
            return "C"
        elif score >= 0.5:
            return "D"
        else:
            return "F"
    
    @property
    def is_high_quality(self) -> bool:
        """是否为高质量响应"""
        return self.overall_quality_score >= 0.8
    
    @property
    def is_fast_response(self) -> bool:
        """是否为快速响应（小于3秒）"""
        return self.response_time < 3.0
    
    @property
    def is_cost_effective(self) -> bool:
        """是否成本效益良好"""
        if self.processing_cost <= 0:
            return True
        # 简单的成本效益计算：质量分数/成本
        cost_effectiveness = self.overall_quality_score / self.processing_cost
        return cost_effectiveness > 0.1
    
    def update_user_feedback(self, rating: int, feedback: str = None) -> None:
        """更新用户反馈"""
        if not 1 <= rating <= 5:
            raise ValueError("用户评分必须在1-5之间")
        self.user_rating = rating
        self.user_feedback = feedback
    
    def calculate_content_metrics(self, content: str) -> None:
        """计算内容指标"""
        if not content:
            return
            
        self.character_count = len(content)
        self.word_count = len(content.split())
        # 简单的token估算：平均4个字符 = 1个token
        self.token_count = self.character_count // 4
    
    def set_quality_scores(
        self,
        relevance: float = None,
        coherence: float = None,
        creativity: float = None,
        accuracy: float = None
    ) -> None:
        """设置质量评分"""
        def validate_score(score: float, name: str) -> float:
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{name}评分必须在0.0-1.0之间")
            return score
        
        if relevance is not None:
            self.relevance_score = validate_score(relevance, "相关性")
        if coherence is not None:
            self.coherence_score = validate_score(coherence, "连贯性")
        if creativity is not None:
            self.creativity_score = validate_score(creativity, "创意性")
        if accuracy is not None:
            self.accuracy_score = validate_score(accuracy, "准确性")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            'overall_quality_score': round(self.overall_quality_score, 3),
            'performance_grade': self.performance_grade,
            'response_time': round(self.response_time, 3),
            'word_count': self.word_count,
            'is_high_quality': self.is_high_quality,
            'is_fast_response': self.is_fast_response,
            'is_cost_effective': self.is_cost_effective,
            'user_rating': self.user_rating
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'response_time': self.response_time,
            'token_count': self.token_count,
            'word_count': self.word_count,
            'character_count': self.character_count,
            'relevance_score': self.relevance_score,
            'coherence_score': self.coherence_score,
            'creativity_score': self.creativity_score,
            'accuracy_score': self.accuracy_score,
            'model_confidence': self.model_confidence,
            'processing_cost': self.processing_cost,
            'cache_hit': self.cache_hit,
            'user_rating': self.user_rating,
            'user_feedback': self.user_feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'overall_quality_score': self.overall_quality_score,
            'performance_grade': self.performance_grade
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIQualityMetrics':
        """从字典创建实例"""
        metrics = cls(
            response_time=data.get('response_time', 0.0),
            token_count=data.get('token_count', 0),
            word_count=data.get('word_count', 0),
            character_count=data.get('character_count', 0),
            relevance_score=data.get('relevance_score', 0.0),
            coherence_score=data.get('coherence_score', 0.0),
            creativity_score=data.get('creativity_score', 0.0),
            accuracy_score=data.get('accuracy_score', 0.0),
            model_confidence=data.get('model_confidence', 0.0),
            processing_cost=data.get('processing_cost', 0.0),
            cache_hit=data.get('cache_hit', False),
            user_rating=data.get('user_rating'),
            user_feedback=data.get('user_feedback')
        )
        
        if 'created_at' in data and data['created_at']:
            metrics.created_at = datetime.fromisoformat(data['created_at'])
            
        return metrics
    
    def __str__(self) -> str:
        return f"AIQualityMetrics(quality={self.overall_quality_score:.2f}, grade={self.performance_grade})"
    
    def __repr__(self) -> str:
        return self.__str__()

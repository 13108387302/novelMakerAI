#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文分析器

提供智能化的上下文分析功能
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ContextAnalyzer(QObject):
    """
    上下文分析器
    
    提供智能化的上下文分析功能，支持内容分析和智能建议
    """
    
    # 信号
    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    suggestion_generated = pyqtSignal(str, list)  # 建议生成信号
    
    def __init__(self, parent=None):
        """
        初始化上下文分析器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._enabled = True
        
    def analyze_content(self, content: str, content_type: str = "text") -> Dict[str, Any]:
        """
        分析内容
        
        Args:
            content: 内容文本
            content_type: 内容类型
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self._enabled or not content:
            return {}
            
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(content, content_type)
            
            # 检查缓存
            if cache_key in self._analysis_cache:
                return self._analysis_cache[cache_key]
                
            # 执行分析
            analysis_result = self._perform_analysis(content, content_type)
            
            # 缓存结果
            self._analysis_cache[cache_key] = analysis_result
            
            # 发射完成信号
            self.analysis_completed.emit(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"内容分析失败: {e}")
            return {}
            
    def _perform_analysis(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        执行具体的分析
        
        Args:
            content: 内容文本
            content_type: 内容类型
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        result = {
            'content_type': content_type,
            'length': len(content),
            'word_count': self._count_words(content),
            'paragraph_count': self._count_paragraphs(content),
            'sentiment': self._analyze_sentiment(content),
            'keywords': self._extract_keywords(content),
            'structure': self._analyze_structure(content),
            'suggestions': self._generate_suggestions(content, content_type)
        }
        
        return result
        
    def _count_words(self, content: str) -> int:
        """统计词数"""
        # 简单的中英文词数统计
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        return chinese_chars + english_words
        
    def _count_paragraphs(self, content: str) -> int:
        """统计段落数"""
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        return len(paragraphs)
        
    def _analyze_sentiment(self, content: str) -> str:
        """分析情感倾向"""
        # 简单的情感分析（实际应用中可以使用更复杂的算法）
        positive_words = ['好', '棒', '优秀', '喜欢', '开心', '快乐', '美好', 'good', 'great', 'excellent', 'happy']
        negative_words = ['坏', '差', '糟糕', '讨厌', '难过', '痛苦', '失望', 'bad', 'terrible', 'awful', 'sad']
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
            
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', content)
        word_freq = {}
        
        for word in words:
            if len(word) > 1:  # 过滤单字符
                word_freq[word] = word_freq.get(word, 0) + 1
                
        # 返回频率最高的前10个词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:10]]
        
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """分析文本结构"""
        lines = content.split('\n')
        structure = {
            'total_lines': len(lines),
            'empty_lines': sum(1 for line in lines if not line.strip()),
            'avg_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
            'has_dialogue': '「' in content or '"' in content or '"' in content,
            'has_description': any(len(line.strip()) > 50 for line in lines)
        }
        
        return structure
        
    def _generate_suggestions(self, content: str, content_type: str) -> List[str]:
        """生成建议"""
        suggestions = []
        
        # 基于内容长度的建议
        word_count = self._count_words(content)
        if word_count < 100:
            suggestions.append("内容较短，可以考虑增加更多细节描述")
        elif word_count > 2000:
            suggestions.append("内容较长，可以考虑分段或精简")
            
        # 基于结构的建议
        structure = self._analyze_structure(content)
        if structure['avg_line_length'] > 100:
            suggestions.append("句子较长，可以考虑分解为更短的句子")
            
        if not structure['has_dialogue'] and content_type == 'chapter':
            suggestions.append("可以考虑添加对话来增加生动性")
            
        # 基于情感的建议
        sentiment = self._analyze_sentiment(content)
        if sentiment == 'negative':
            suggestions.append("内容情感偏负面，可以考虑添加一些积极元素")
            
        return suggestions
        
    def _generate_cache_key(self, content: str, content_type: str) -> str:
        """生成缓存键"""
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{content_type}_{content_hash}"
        
    def get_smart_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """
        获取智能建议
        
        Args:
            context: 上下文数据
            
        Returns:
            List[str]: 建议列表
        """
        suggestions = []
        
        try:
            content = context.get('content', '')
            selected_text = context.get('selected_text', '')
            document_type = context.get('document_type', 'text')
            
            if selected_text:
                # 基于选中文字的建议
                if len(selected_text) < 20:
                    suggestions.append("可以对选中文字进行扩展描述")
                else:
                    suggestions.append("可以对选中文字进行精简或重写")
                    
            elif content:
                # 基于整体内容的建议
                analysis = self.analyze_content(content, document_type)
                suggestions.extend(analysis.get('suggestions', []))
                
            # 发射建议信号
            if suggestions:
                self.suggestion_generated.emit(document_type, suggestions)
                
        except Exception as e:
            logger.error(f"生成智能建议失败: {e}")
            
        return suggestions
        
    def clear_cache(self):
        """清空分析缓存"""
        self._analysis_cache.clear()
        logger.debug("分析缓存已清空")
        
    def set_enabled(self, enabled: bool):
        """
        设置是否启用分析器
        
        Args:
            enabled: 是否启用
        """
        self._enabled = enabled
        logger.info(f"上下文分析器 {'启用' if enabled else '禁用'}")
        
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled

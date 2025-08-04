#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索相关的数据模型

包含搜索匹配项、搜索结果、搜索选项等数据类
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime


@dataclass
class SearchMatch:
    """搜索匹配项"""
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: str = ""
    context_after: str = ""
    highlighted_content: str = ""


@dataclass
class SearchResult:
    """搜索结果"""
    item_type: str  # project, document, content
    item_id: str
    title: str
    content_preview: str
    relevance_score: float
    matches: List[SearchMatch] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchOptions:
    """搜索选项"""
    case_sensitive: bool = False
    whole_words: bool = False
    use_regex: bool = False
    search_in_content: bool = True
    search_in_titles: bool = True
    search_in_metadata: bool = False
    max_results: int = 100
    include_context: bool = True
    context_lines: int = 2
    highlight_matches: bool = True
    search_types: Set[str] = field(default_factory=lambda: {"project", "document", "content"})
    date_range: Optional[tuple] = None
    file_types: Set[str] = field(default_factory=set)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class SearchHistoryItem:
    """搜索历史项"""
    id: str
    query: str
    options: SearchOptions
    timestamp: datetime
    result_count: int = 0


@dataclass
class SearchStatistics:
    """搜索统计"""
    total_searches: int = 0
    total_results: int = 0
    average_results_per_search: float = 0.0
    most_searched_terms: Dict[str, int] = field(default_factory=dict)
    search_frequency_by_hour: Dict[int, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class IndexStatus:
    """索引状态"""
    total_documents: int = 0
    indexed_documents: int = 0
    last_update: Optional[datetime] = None
    index_size: int = 0  # 字节
    is_building: bool = False
    build_progress: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class SearchFilter:
    """搜索过滤器"""
    document_types: Set[str] = field(default_factory=set)
    projects: Set[str] = field(default_factory=set)
    authors: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    date_created_start: Optional[datetime] = None
    date_created_end: Optional[datetime] = None
    date_modified_start: Optional[datetime] = None
    date_modified_end: Optional[datetime] = None
    min_word_count: Optional[int] = None
    max_word_count: Optional[int] = None


@dataclass
class SearchQuery:
    """搜索查询"""
    text: str
    options: SearchOptions = field(default_factory=SearchOptions)
    filters: SearchFilter = field(default_factory=SearchFilter)
    sort_by: str = "relevance"  # relevance, date, title, word_count
    sort_order: str = "desc"  # asc, desc
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'text': self.text,
            'options': self.options.__dict__,
            'filters': self.filters.__dict__,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchQuery':
        """从字典创建"""
        query = cls(text=data['text'])
        if 'options' in data:
            query.options = SearchOptions(**data['options'])
        if 'filters' in data:
            query.filters = SearchFilter(**data['filters'])
        if 'sort_by' in data:
            query.sort_by = data['sort_by']
        if 'sort_order' in data:
            query.sort_order = data['sort_order']
        return query


class SearchResultSet:
    """搜索结果集"""
    
    def __init__(self, query: SearchQuery, results: List[SearchResult] = None):
        self.query = query
        self.results = results or []
        self.total_count = len(self.results)
        self.search_time = 0.0
        self.timestamp = datetime.now()
    
    def add_result(self, result: SearchResult):
        """添加搜索结果"""
        self.results.append(result)
        self.total_count = len(self.results)
    
    def sort_results(self):
        """排序结果"""
        if self.query.sort_by == "relevance":
            self.results.sort(key=lambda r: r.relevance_score, 
                            reverse=(self.query.sort_order == "desc"))
        elif self.query.sort_by == "date":
            self.results.sort(key=lambda r: r.created_at, 
                            reverse=(self.query.sort_order == "desc"))
        elif self.query.sort_by == "title":
            self.results.sort(key=lambda r: r.title.lower(), 
                            reverse=(self.query.sort_order == "desc"))
    
    def filter_results(self, max_results: int = None) -> List[SearchResult]:
        """过滤结果"""
        if max_results is None:
            max_results = self.query.options.max_results
        
        return self.results[:max_results]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.results:
            return {}
        
        return {
            'total_results': self.total_count,
            'search_time': self.search_time,
            'average_relevance': sum(r.relevance_score for r in self.results) / len(self.results),
            'result_types': {
                result_type: len([r for r in self.results if r.item_type == result_type])
                for result_type in set(r.item_type for r in self.results)
            },
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'query': self.query.to_dict(),
            'results': [
                {
                    'item_type': r.item_type,
                    'item_id': r.item_id,
                    'title': r.title,
                    'content_preview': r.content_preview,
                    'relevance_score': r.relevance_score,
                    'matches_count': len(r.matches),
                    'created_at': r.created_at.isoformat()
                }
                for r in self.results
            ],
            'statistics': self.get_statistics()
        }


class SearchException(Exception):
    """搜索异常"""
    pass


class IndexException(Exception):
    """索引异常"""
    pass


class SearchTimeoutException(SearchException):
    """搜索超时异常"""
    pass


class IndexCorruptedException(IndexException):
    """索引损坏异常"""
    pass

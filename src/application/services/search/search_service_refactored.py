#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的搜索服务

提供全文搜索、智能搜索和高级搜索功能
"""

import re
import json
import threading
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from uuid import uuid4

from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.document_repository import IDocumentRepository
from src.domain.events.document_events import DocumentSearchedEvent
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger

# 导入拆分的模块
from .search_models import (
    SearchMatch, SearchResult, SearchOptions, SearchHistoryItem, 
    SearchStatistics, SearchQuery, SearchResultSet, SearchFilter,
    SearchException, SearchTimeoutException
)
from .search_index import SearchIndex

logger = get_logger(__name__)


class SearchService:
    """
    重构后的搜索服务

    提供高性能的全文搜索功能，支持多种搜索模式和高级搜索选项。
    使用本地索引提高搜索速度，支持搜索历史和统计功能。

    实现方式：
    - 使用本地SQLite数据库作为搜索索引
    - 支持全文搜索、正则表达式搜索和模糊搜索
    - 提供搜索结果排序和过滤功能
    - 记录搜索历史和统计信息
    - 使用线程锁确保并发安全
    - 集成事件总线发布搜索事件

    Attributes:
        project_repository: 项目仓储接口
        document_repository: 文档仓储接口
        event_bus: 事件总线
        search_index: 搜索索引实例
        search_history: 搜索历史记录
        search_statistics: 搜索统计信息
    """

    def __init__(
        self,
        project_repository: IProjectRepository,
        document_repository: IDocumentRepository,
        event_bus: EventBus,
        index_path: Path = None
    ):
        """
        初始化搜索服务

        Args:
            project_repository: 项目仓储接口
            document_repository: 文档仓储接口
            event_bus: 事件总线
            index_path: 搜索索引文件路径，默认为用户目录下的search_index.db
        """
        self.project_repository = project_repository
        self.document_repository = document_repository
        self.event_bus = event_bus

        # 搜索索引
        if index_path is None:
            index_path = Path.home() / "AI小说编辑器" / "search_index.db"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        self.search_index = SearchIndex(index_path)

        # 搜索历史和统计
        self.search_history: List[SearchHistoryItem] = []
        self.search_statistics = SearchStatistics()

        # 线程锁
        self._lock = threading.RLock()

        logger.info("搜索服务初始化完成")

    def search(self, query: SearchQuery, timeout: float = 30.0) -> SearchResultSet:
        """
        执行搜索操作（增强健壮性版本）

        根据搜索查询执行全文搜索，返回排序后的搜索结果集。
        记录搜索历史和统计信息，发布搜索事件。
        增加了输入验证、超时处理和错误恢复机制。

        实现方式：
        - 输入验证和边界条件检查
        - 使用线程锁确保并发安全
        - 超时保护机制（Unix系统）
        - 记录搜索开始时间和历史
        - 调用内部搜索方法执行实际搜索
        - 对结果进行排序和后处理
        - 更新搜索统计信息
        - 安全发布搜索完成事件

        Args:
            query: 搜索查询对象，包含搜索文本和选项
            timeout: 搜索超时时间（秒），默认30秒

        Returns:
            SearchResultSet: 搜索结果集，包含匹配的文档和统计信息
        """
        # 输入验证
        if not query:
            logger.warning("搜索查询为空")
            return SearchResultSet(SearchQuery("", SearchOptions()), [])

        if not query.text or not query.text.strip():
            logger.warning("搜索文本为空")
            return SearchResultSet(query, [])

        # 查询长度限制
        if len(query.text) > 1000:
            logger.warning(f"搜索查询过长: {len(query.text)} 字符，截断到1000字符")
            query.text = query.text[:1000]

        start_time = datetime.now()

        try:
            # 使用超时机制（仅在Unix系统上）
            import signal

            def timeout_handler(signum, frame):
                raise SearchTimeoutException(f"搜索超时: {timeout}秒")

            # 设置超时（仅在Unix系统上）
            old_handler = None
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout))

            try:
                with self._lock:
                    # 记录搜索历史
                    history_item = SearchHistoryItem(
                        id=str(uuid4()),
                        query=query.text,
                        options=query.options,
                        timestamp=start_time,
                        result_count=0
                    )

                    # 执行搜索
                    results = self._perform_search(query)

                    # 创建结果集
                    result_set = SearchResultSet(query, results)
                    result_set.search_time = (datetime.now() - start_time).total_seconds()

                    # 排序结果
                    result_set.sort_results()

                    # 更新历史和统计
                    history_item.result_count = len(results)
                    self.search_history.append(history_item)
                    self._update_statistics(query, len(results), result_set.search_time)

                    # 发布搜索事件（安全发布）
                    try:
                        self.event_bus.publish(DocumentSearchedEvent(
                            query=query.text,
                            result_count=len(results),
                            search_time=result_set.search_time
                        ))
                    except Exception as event_error:
                        logger.warning(f"发布搜索事件失败: {event_error}")

                    logger.info(f"搜索完成: '{query.text}' -> {len(results)} 个结果")
                    return result_set

            finally:
                # 清除超时设置
                if hasattr(signal, 'SIGALRM') and old_handler is not None:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

        except SearchTimeoutException as e:
            logger.error(f"搜索超时: {e}")
            if hasattr(self.search_statistics, 'timeout_count'):
                self.search_statistics.timeout_count += 1
            return SearchResultSet(query, [])
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            if hasattr(self.search_statistics, 'error_count'):
                self.search_statistics.error_count += 1
            return SearchResultSet(query, [])

    def _perform_search(self, query: SearchQuery) -> List[SearchResult]:
        """执行实际搜索"""
        results = []
        
        # 使用索引搜索
        index_results = self.search_index.search(query.text, query.options.max_results)
        
        for index_result in index_results:
            # 转换为SearchResult
            search_result = SearchResult(
                item_type="document",
                item_id=index_result['id'],
                title=index_result['title'],
                content_preview=self._generate_preview(index_result['content'], query.text),
                relevance_score=index_result['relevance_score'],
                metadata=index_result['metadata']
            )
            
            # 查找匹配项
            matches = self._find_matches(index_result['content'], query.text, query.options)
            search_result.matches = matches
            
            results.append(search_result)
        
        # 应用过滤器
        if query.filters:
            results = self._apply_filters(results, query.filters)
        
        return results

    def _generate_preview(self, content: str, query: str, max_length: int = 200) -> str:
        """生成内容预览"""
        if not content:
            return ""
        
        # 查找查询词在内容中的位置
        query_lower = query.lower()
        content_lower = content.lower()
        
        pos = content_lower.find(query_lower)
        if pos == -1:
            # 如果没找到，返回开头部分
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # 以查询词为中心生成预览
        start = max(0, pos - max_length // 2)
        end = min(len(content), start + max_length)
        
        preview = content[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."
        
        return preview

    def _find_matches(self, content: str, query: str, options: SearchOptions) -> List[SearchMatch]:
        """查找匹配项"""
        matches = []
        
        if not content or not query:
            return matches
        
        # 构建搜索模式
        pattern = query
        flags = 0
        
        if not options.case_sensitive:
            flags |= re.IGNORECASE
        
        if options.whole_words:
            pattern = r'\b' + re.escape(pattern) + r'\b'
        elif not options.use_regex:
            pattern = re.escape(pattern)
        
        try:
            # 按行搜索
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                for match in re.finditer(pattern, line, flags):
                    search_match = SearchMatch(
                        line_number=line_num,
                        line_content=line,
                        match_start=match.start(),
                        match_end=match.end()
                    )
                    
                    # 添加上下文
                    if options.include_context:
                        search_match.context_before = self._get_context_before(
                            lines, line_num - 1, options.context_lines
                        )
                        search_match.context_after = self._get_context_after(
                            lines, line_num - 1, options.context_lines
                        )
                    
                    # 高亮匹配内容
                    search_match.highlighted_content = self._highlight_match(
                        line, match.start(), match.end()
                    )
                    
                    matches.append(search_match)
                    
        except re.error as e:
            logger.warning(f"正则表达式错误: {e}")
        
        return matches

    def _get_context_before(self, lines: List[str], line_index: int, context_lines: int) -> str:
        """获取前置上下文"""
        start = max(0, line_index - context_lines)
        return '\n'.join(lines[start:line_index])

    def _get_context_after(self, lines: List[str], line_index: int, context_lines: int) -> str:
        """获取后置上下文"""
        end = min(len(lines), line_index + 1 + context_lines)
        return '\n'.join(lines[line_index + 1:end])

    def _highlight_match(self, line: str, start: int, end: int) -> str:
        """高亮匹配内容"""
        return (
            line[:start] + 
            f"<mark>{line[start:end]}</mark>" + 
            line[end:]
        )

    def _apply_filters(self, results: List[SearchResult], filters: SearchFilter) -> List[SearchResult]:
        """应用搜索过滤器"""
        filtered_results = []
        
        for result in results:
            # 应用各种过滤条件
            if filters.document_types and result.metadata.get('document_type') not in filters.document_types:
                continue
            
            if filters.projects and result.metadata.get('project_id') not in filters.projects:
                continue
            
            # 日期过滤
            if filters.date_created_start or filters.date_created_end:
                created_at = result.metadata.get('created_at')
                if created_at:
                    try:
                        created_date = datetime.fromisoformat(created_at)
                        if filters.date_created_start and created_date < filters.date_created_start:
                            continue
                        if filters.date_created_end and created_date > filters.date_created_end:
                            continue
                    except:
                        pass
            
            # 字数过滤
            word_count = result.metadata.get('word_count', 0)
            if filters.min_word_count and word_count < filters.min_word_count:
                continue
            if filters.max_word_count and word_count > filters.max_word_count:
                continue
            
            filtered_results.append(result)
        
        return filtered_results

    def _update_statistics(self, query: SearchQuery, result_count: int, search_time: float):
        """更新搜索统计"""
        self.search_statistics.total_searches += 1
        self.search_statistics.total_results += result_count
        
        if self.search_statistics.total_searches > 0:
            self.search_statistics.average_results_per_search = (
                self.search_statistics.total_results / self.search_statistics.total_searches
            )
        
        # 更新搜索词频率
        words = query.text.lower().split()
        for word in words:
            if word not in self.search_statistics.most_searched_terms:
                self.search_statistics.most_searched_terms[word] = 0
            self.search_statistics.most_searched_terms[word] += 1
        
        # 更新时间统计
        hour = datetime.now().hour
        if hour not in self.search_statistics.search_frequency_by_hour:
            self.search_statistics.search_frequency_by_hour[hour] = 0
        self.search_statistics.search_frequency_by_hour[hour] += 1

    def add_document_to_index(self, document: Document) -> bool:
        """添加文档到索引"""
        try:
            return self.search_index.add_document(document)
        except Exception as e:
            logger.error(f"添加文档到索引失败: {e}")
            return False

    def remove_document_from_index(self, document_id: str) -> bool:
        """从索引中移除文档"""
        try:
            return self.search_index.remove_document(document_id)
        except Exception as e:
            logger.error(f"从索引移除文档失败: {e}")
            return False

    def rebuild_index(self) -> bool:
        """重建搜索索引"""
        try:
            # 获取所有文档
            documents = []
            for project in self.project_repository.get_all():
                project_docs = self.document_repository.get_by_project_id(project.id)
                documents.extend(project_docs)
            
            return self.search_index.rebuild_index(documents)
            
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False

    def get_search_history(self, limit: int = 50) -> List[SearchHistoryItem]:
        """
        获取搜索历史记录

        Args:
            limit: 返回的历史记录数量限制，默认50条

        Returns:
            List[SearchHistoryItem]: 按时间倒序排列的搜索历史记录列表
        """
        return sorted(self.search_history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_search_statistics(self) -> SearchStatistics:
        """
        获取搜索统计信息

        Returns:
            SearchStatistics: 包含搜索次数、结果数量、平均时间等统计信息
        """
        return self.search_statistics

    def get_word_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """获取词汇建议"""
        try:
            return self.search_index.get_word_suggestions(prefix, limit)
        except Exception as e:
            logger.error(f"获取词汇建议失败: {e}")
            return []

    def clear_search_history(self):
        """清空搜索历史"""
        with self._lock:
            self.search_history.clear()
            logger.info("搜索历史已清空")

    def get_index_status(self):
        """获取索引状态"""
        try:
            return self.search_index.get_status()
        except Exception as e:
            logger.error(f"获取索引状态失败: {e}")
            return None

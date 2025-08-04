#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索服务

提供全文搜索、智能搜索和高级搜索功能
"""

import re
import json
import sqlite3
import threading
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
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

logger = get_logger(__name__)


@dataclass
class SearchMatch:
    """
    搜索匹配项数据类

    记录搜索结果中的具体匹配信息，包括位置、内容和上下文。

    Attributes:
        line_number: 匹配所在行号
        line_content: 匹配行的完整内容
        match_start: 匹配开始位置
        match_end: 匹配结束位置
        context_before: 匹配前的上下文
        context_after: 匹配后的上下文
        highlighted_content: 高亮显示的内容
    """
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: str = ""
    context_after: str = ""
    highlighted_content: str = ""


@dataclass
class SearchResult:
    """
    搜索结果数据类

    记录搜索操作的结果信息，包括匹配项和相关性评分。

    Attributes:
        item_type: 项目类型（project/document/content）
        item_id: 项目唯一标识符
        title: 项目标题
        content_preview: 内容预览
        relevance_score: 相关性评分
        matches: 匹配项列表
        metadata: 附加元数据
    """
    item_type: str  # project, document, content
    item_id: str
    title: str
    content_preview: str
    relevance_score: float
    matches: List[SearchMatch] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    snippet: str = ""
    match_count: int = 0


@dataclass
class SearchOptions:
    """搜索选项"""
    case_sensitive: bool = False
    whole_words: bool = False
    use_regex: bool = False
    search_content: bool = True
    search_titles: bool = True
    search_descriptions: bool = True
    search_tags: bool = True
    document_types: Optional[List[DocumentType]] = None
    project_id: Optional[str] = None
    max_results: int = 100
    include_context: bool = True
    context_lines: int = 2
    min_relevance_score: float = 0.0
    date_range: Optional[Tuple[datetime, datetime]] = None
    author_filter: Optional[str] = None
    fuzzy_search: bool = False
    fuzzy_threshold: float = 0.8


@dataclass
class SearchHistoryItem:
    """搜索历史项"""
    id: str
    query: str
    timestamp: datetime
    result_count: int
    search_options: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


@dataclass
class SearchStatistics:
    """搜索统计"""
    total_searches: int = 0
    total_results: int = 0
    average_results_per_search: float = 0.0
    average_execution_time: float = 0.0
    most_searched_terms: List[Tuple[str, int]] = field(default_factory=list)
    search_frequency_by_hour: Dict[int, int] = field(default_factory=dict)
    search_frequency_by_day: Dict[str, int] = field(default_factory=dict)
    popular_document_types: List[Tuple[str, int]] = field(default_factory=list)


class SearchIndex:
    """搜索索引"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_index (
                    document_id TEXT,
                    word TEXT,
                    frequency INTEGER,
                    positions TEXT,
                    PRIMARY KEY (document_id, word)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    document_id TEXT PRIMARY KEY,
                    title TEXT,
                    content_hash TEXT,
                    last_indexed TIMESTAMP,
                    word_count INTEGER
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_word ON search_index(word)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_document ON search_index(document_id)")

    def index_document(self, document: Document):
        """索引文档"""
        with self._lock:
            try:
                # 计算内容哈希
                import hashlib
                content_hash = hashlib.md5(document.content.encode()).hexdigest()

                with sqlite3.connect(self.db_path) as conn:
                    # 检查是否需要重新索引
                    cursor = conn.execute(
                        "SELECT content_hash FROM document_metadata WHERE document_id = ?",
                        (document.id,)
                    )
                    row = cursor.fetchone()

                    if row and row[0] == content_hash:
                        return  # 内容未变化，无需重新索引

                    # 删除旧索引
                    conn.execute("DELETE FROM search_index WHERE document_id = ?", (document.id,))

                    # 分词并建立索引
                    word_positions = self._extract_words(document.content)

                    for word, positions in word_positions.items():
                        conn.execute(
                            "INSERT OR REPLACE INTO search_index (document_id, word, frequency, positions) VALUES (?, ?, ?, ?)",
                            (document.id, word, len(positions), json.dumps(positions))
                        )

                    # 更新元数据
                    conn.execute(
                        "INSERT OR REPLACE INTO document_metadata (document_id, title, content_hash, last_indexed, word_count) VALUES (?, ?, ?, ?, ?)",
                        (document.id, document.metadata.title, content_hash, datetime.now(), len(word_positions))
                    )

                logger.debug(f"文档索引完成: {document.id}")

            except Exception as e:
                logger.error(f"索引文档失败: {e}")

    def _extract_words(self, content: str) -> Dict[str, List[int]]:
        """提取单词和位置"""
        word_positions = defaultdict(list)

        # 中文分词（简单实现）
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        english_pattern = re.compile(r'\b[a-zA-Z]+\b')

        # 处理中文
        for match in chinese_pattern.finditer(content):
            text = match.group()
            start_pos = match.start()

            # 简单的中文分词（按字符）
            for i, char in enumerate(text):
                if len(char.strip()) > 0:
                    word_positions[char].append(start_pos + i)

        # 处理英文
        for match in english_pattern.finditer(content):
            word = match.group().lower()
            word_positions[word].append(match.start())

        return dict(word_positions)

    def search_words(self, words: List[str]) -> Dict[str, List[str]]:
        """搜索单词"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    results = defaultdict(list)

                    for word in words:
                        cursor = conn.execute(
                            "SELECT document_id, frequency FROM search_index WHERE word = ? ORDER BY frequency DESC",
                            (word.lower(),)
                        )

                        for row in cursor.fetchall():
                            results[word].append(row[0])

                    return dict(results)

            except Exception as e:
                logger.error(f"搜索单词失败: {e}")
                return {}

    def remove_document(self, document_id: str):
        """移除文档索引"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM search_index WHERE document_id = ?", (document_id,))
                    conn.execute("DELETE FROM document_metadata WHERE document_id = ?", (document_id,))

                logger.debug(f"文档索引已移除: {document_id}")

            except Exception as e:
                logger.error(f"移除文档索引失败: {e}")


class SearchService:
    """
    搜索服务

    提供全文搜索、智能搜索和高级搜索功能。
    支持项目和文档的快速检索，包含搜索历史和统计功能。

    实现方式：
    - 使用SQLite构建全文搜索索引
    - 提供多种搜索模式（精确、模糊、正则表达式）
    - 支持搜索结果相关性排序
    - 维护搜索历史和使用统计
    - 提供搜索建议和自动完成功能

    Attributes:
        project_repository: 项目仓储接口
        document_repository: 文档仓储接口
        event_bus: 事件总线
        data_dir: 搜索数据存储目录
        search_index: 搜索索引实例
        _search_history: 搜索历史记录
        _search_stats: 搜索统计信息
    """

    def __init__(
        self,
        project_repository: IProjectRepository,
        document_repository: IDocumentRepository,
        event_bus: EventBus,
        data_dir: Path = None
    ):
        """
        初始化搜索服务

        Args:
            project_repository: 项目仓储接口
            document_repository: 文档仓储接口
            event_bus: 事件总线
            data_dir: 搜索数据存储目录，默认为data/search
        """
        self.project_repository = project_repository
        self.document_repository = document_repository
        self.event_bus = event_bus

        # 初始化数据目录
        self.data_dir = data_dir or Path("data/search")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 搜索索引
        self.search_index = SearchIndex(self.data_dir / "search_index.db")

        # 搜索历史
        self._search_history: List[SearchHistoryItem] = []
        self._history_file = self.data_dir / "search_history.json"
        self._load_search_history()

        # 搜索统计
        self._search_stats = SearchStatistics()
        self._stats_file = self.data_dir / "search_stats.json"
        self._load_search_statistics()

        logger.debug("搜索服务初始化完成")

    def _load_search_history(self):
        """加载搜索历史"""
        try:
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # 验证数据格式
                    if not isinstance(data, list):
                        logger.warning("搜索历史文件格式无效")
                        self._search_history = []
                        return

                    self._search_history = []
                    for item in data:
                        try:
                            if not isinstance(item, dict) or 'query' not in item or 'timestamp' not in item:
                                continue

                            history_item = SearchHistoryItem(
                                id=item.get('id', str(uuid4())),
                                query=item['query'],
                                timestamp=datetime.fromisoformat(item['timestamp']),
                                result_count=item.get('result_count', 0),
                                search_options=item.get('search_options', {}),
                                execution_time=item.get('execution_time', 0.0)
                            )
                            self._search_history.append(history_item)
                        except (ValueError, KeyError, TypeError) as e:
                            logger.warning(f"跳过无效的搜索历史项: {e}")
                            continue
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"搜索历史文件格式错误: {e}")
            self._search_history = []
        except Exception as e:
            logger.error(f"加载搜索历史失败: {e}")
            self._search_history = []

    def _save_search_history(self):
        """保存搜索历史"""
        try:
            data = []
            for item in self._search_history:
                try:
                    item_dict = asdict(item)
                    # 转换datetime为字符串
                    if isinstance(item_dict.get('timestamp'), datetime):
                        item_dict['timestamp'] = item_dict['timestamp'].isoformat()
                    data.append(item_dict)
                except Exception as e:
                    logger.warning(f"跳过无效的搜索历史项: {e}")
                    continue

            # 确保目录存在
            self._history_file.parent.mkdir(parents=True, exist_ok=True)

            # 使用临时文件确保原子性写入
            temp_file = self._history_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # 验证JSON格式

                # 原子性替换
                temp_file.replace(self._history_file)

            except Exception:
                # 清理临时文件
                if temp_file.exists():
                    temp_file.unlink()
                raise

        except Exception as e:
            logger.error(f"保存搜索历史失败: {e}")

    def _load_search_statistics(self):
        """加载搜索统计"""
        try:
            if self._stats_file.exists():
                with open(self._stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # 验证数据格式
                    if not isinstance(data, dict):
                        logger.warning("搜索统计文件格式无效")
                        self._search_stats = SearchStatistics()
                        return

                    # 安全地创建SearchStatistics对象
                    try:
                        self._search_stats = SearchStatistics(**data)
                    except TypeError as e:
                        logger.warning(f"搜索统计数据格式不兼容: {e}")
                        # 只保留有效字段
                        valid_data = {}
                        for field in ['total_searches', 'total_results', 'average_results_per_search', 'average_execution_time']:
                            if field in data and isinstance(data[field], (int, float)):
                                valid_data[field] = data[field]
                        self._search_stats = SearchStatistics(**valid_data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"搜索统计文件格式错误: {e}")
            self._search_stats = SearchStatistics()
        except Exception as e:
            logger.error(f"加载搜索统计失败: {e}")
            self._search_stats = SearchStatistics()

    def _save_search_statistics(self):
        """保存搜索统计"""
        try:
            with open(self._stats_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._search_stats), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存搜索统计失败: {e}")

    async def search_all(
        self,
        query: str,
        options: Optional[SearchOptions] = None
    ) -> List[SearchResult]:
        """全局搜索"""
        if not query.strip():
            return []

        options = options or SearchOptions()
        results = []
        start_time = datetime.now()

        try:
            # 搜索项目
            project_results = await self._search_projects(query, options)
            results.extend(project_results)

            # 搜索文档
            document_results = await self._search_documents(query, options)
            results.extend(document_results)

            # 搜索内容
            if options.search_content:
                content_results = await self._search_content(query, options)
                results.extend(content_results)

            # 过滤低相关性结果
            if options.min_relevance_score > 0:
                results = [r for r in results if r.relevance_score >= options.min_relevance_score]

            # 按相关性排序
            results.sort(key=lambda r: r.relevance_score, reverse=True)

            # 限制结果数量
            results = results[:options.max_results]

            # 记录搜索历史和统计
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._add_to_history(query, options, len(results), execution_time)
            await self._update_search_statistics(query, options, len(results), execution_time)

            logger.info(f"全局搜索完成: '{query}' 找到 {len(results)} 个结果，耗时 {execution_time:.2f}s")
            return results

        except Exception as e:
            logger.error(f"全局搜索失败: {e}")
            return []
    
    async def _search_projects(
        self,
        query: str,
        options: SearchOptions
    ) -> List[SearchResult]:
        """搜索项目"""
        try:
            projects = await self.project_repository.search(query)
            results = []

            for project in projects:
                matches = []
                relevance_score = 0.0

                # 检查标题匹配
                if options.search_titles and self._text_matches(project.title, query, options):
                    title_matches = self._create_search_matches(project.title, query, options)
                    matches.extend(title_matches)
                    relevance_score += 1.0

                # 检查描述匹配
                if options.search_descriptions and project.metadata.description:
                    if self._text_matches(project.metadata.description, query, options):
                        desc_matches = self._create_search_matches(project.metadata.description, query, options)
                        matches.extend(desc_matches)
                        relevance_score += 0.8

                # 检查标签匹配
                if options.search_tags:
                    for tag in project.metadata.tags:
                        if self._text_matches(tag, query, options):
                            tag_matches = self._create_search_matches(tag, query, options)
                            matches.extend(tag_matches)
                            relevance_score += 0.5

                if matches:
                    result = SearchResult(
                        item_type="project",
                        item_id=project.id,
                        title=project.title,
                        content_preview=project.metadata.description[:200] if project.metadata.description else "",
                        relevance_score=relevance_score,
                        matches=matches,
                        metadata={
                            "author": project.metadata.author,
                            "type": project.project_type.value,
                            "status": project.status.value,
                            "word_count": project.statistics.total_words
                        },
                        match_count=len(matches)
                    )
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"搜索项目失败: {e}")
            return []
    
    async def _search_documents(
        self,
        query: str,
        options: SearchOptions
    ) -> List[SearchResult]:
        """搜索文档"""
        try:
            documents = await self.document_repository.search(query, options.project_id)
            results = []
            
            for document in documents:
                # 过滤文档类型
                if options.document_types and document.document_type not in options.document_types:
                    continue
                
                matches = []
                relevance_score = 0.0
                
                # 检查标题匹配
                if options.search_titles and self._text_matches(document.title, query, options):
                    matches.append({
                        "field": "title",
                        "text": document.title,
                        "positions": self._find_match_positions(document.title, query, options)
                    })
                    relevance_score += 1.0
                
                # 检查描述匹配
                if options.search_descriptions and self._text_matches(document.metadata.description, query, options):
                    matches.append({
                        "field": "description",
                        "text": document.metadata.description,
                        "positions": self._find_match_positions(document.metadata.description, query, options)
                    })
                    relevance_score += 0.8
                
                # 检查标签匹配
                if options.search_tags:
                    for tag in document.metadata.tags:
                        if self._text_matches(tag, query, options):
                            matches.append({
                                "field": "tag",
                                "text": tag,
                                "positions": self._find_match_positions(tag, query, options)
                            })
                            relevance_score += 0.5
                
                if matches:
                    result = SearchResult(
                        item_type="document",
                        item_id=document.id,
                        title=document.title,
                        content_preview=document.content[:200],
                        relevance_score=relevance_score,
                        matches=matches,
                        metadata={
                            "type": document.document_type.value,
                            "status": document.status.value,
                            "word_count": document.statistics.word_count,
                            "project_id": document.project_id
                        }
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索文档失败: {e}")
            return []
    
    async def _search_content(
        self,
        query: str,
        options: SearchOptions
    ) -> List[SearchResult]:
        """搜索内容"""
        try:
            content_matches = await self.document_repository.search_content(query, options.project_id)
            results = []
            
            for match in content_matches:
                document_id = match["document_id"]
                document = await self.document_repository.load(document_id)
                
                if not document:
                    continue
                
                # 过滤文档类型
                if options.document_types and document.document_type not in options.document_types:
                    continue
                
                # 计算相关性分数
                relevance_score = len(match["matches"]) * 0.6
                
                # 生成内容预览
                preview_parts = []
                for content_match in match["matches"][:3]:  # 最多显示3个匹配
                    preview_parts.append(content_match["context"])
                
                content_preview = " ... ".join(preview_parts)
                
                result = SearchResult(
                    item_type="content",
                    item_id=document_id,
                    title=document.title,
                    content_preview=content_preview,
                    relevance_score=relevance_score,
                    matches=match["matches"],
                    metadata={
                        "type": document.document_type.value,
                        "match_count": len(match["matches"]),
                        "project_id": document.project_id
                    }
                )
                results.append(result)
                
                # 发布搜索事件
                event = DocumentSearchedEvent(
                    document_id=document_id,
                    search_query=query,
                    results_count=len(match["matches"])
                )
                await self.event_bus.publish_async(event)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索内容失败: {e}")
            return []
    
    def _text_matches(self, text: str, query: str, options: SearchOptions) -> bool:
        """检查文本是否匹配查询"""
        if not text or not query:
            return False
        
        if options.use_regex:
            try:
                flags = 0 if options.case_sensitive else re.IGNORECASE
                return bool(re.search(query, text, flags))
            except re.error:
                return False
        
        if not options.case_sensitive:
            text = text.lower()
            query = query.lower()
        
        if options.whole_words:
            # 使用正则表达式匹配完整单词
            pattern = r'\b' + re.escape(query) + r'\b'
            flags = 0 if options.case_sensitive else re.IGNORECASE
            return bool(re.search(pattern, text, flags))
        else:
            return query in text
    
    def _find_match_positions(self, text: str, query: str, options: SearchOptions) -> List[Dict[str, int]]:
        """查找匹配位置"""
        positions = []
        
        if not text or not query:
            return positions
        
        if options.use_regex:
            try:
                flags = 0 if options.case_sensitive else re.IGNORECASE
                for match in re.finditer(query, text, flags):
                    positions.append({
                        "start": match.start(),
                        "end": match.end(),
                        "length": match.end() - match.start()
                    })
            except re.error:
                pass
        else:
            search_text = text if options.case_sensitive else text.lower()
            search_query = query if options.case_sensitive else query.lower()
            
            if options.whole_words:
                pattern = r'\b' + re.escape(search_query) + r'\b'
                flags = 0 if options.case_sensitive else re.IGNORECASE
                for match in re.finditer(pattern, text, flags):
                    positions.append({
                        "start": match.start(),
                        "end": match.end(),
                        "length": match.end() - match.start()
                    })
            else:
                start = 0
                while True:
                    pos = search_text.find(search_query, start)
                    if pos == -1:
                        break
                    positions.append({
                        "start": pos,
                        "end": pos + len(search_query),
                        "length": len(search_query)
                    })
                    start = pos + 1
        
        return positions
    
    def _add_to_history(self, query: str, options: SearchOptions) -> None:
        """添加到搜索历史"""
        history_item = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "options": {
                "case_sensitive": options.case_sensitive,
                "whole_words": options.whole_words,
                "use_regex": options.use_regex,
                "project_id": options.project_id
            }
        }
        
        # 移除重复项
        self._search_history = [h for h in self._search_history if h["query"] != query]
        
        # 添加到开头
        self._search_history.insert(0, history_item)
        
        # 限制历史大小
        if len(self._search_history) > self._max_history_size:
            self._search_history = self._search_history[:self._max_history_size]
    
    def get_search_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self._search_history[:limit]
    
    def clear_search_history(self) -> None:
        """清空搜索历史"""
        self._search_history.clear()
        logger.info("搜索历史已清空")
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """获取搜索建议"""
        if not partial_query.strip():
            return []
        
        suggestions = []
        partial_lower = partial_query.lower()
        
        # 从历史中查找匹配的查询
        for item in self._search_history:
            query = item["query"]
            if query.lower().startswith(partial_lower) and query not in suggestions:
                suggestions.append(query)
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    async def search_and_replace(
        self,
        search_query: str,
        replace_text: str,
        options: SearchOptions,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """搜索和替换"""
        try:
            if not search_query:
                return {"success": False, "error": "搜索查询不能为空"}
            
            replaced_count = 0
            affected_documents = []
            
            # 确定要处理的文档
            if document_ids:
                documents = []
                for doc_id in document_ids:
                    doc = await self.document_repository.load(doc_id)
                    if doc:
                        documents.append(doc)
            else:
                # 搜索所有匹配的文档
                content_results = await self._search_content(search_query, options)
                document_ids = [r.item_id for r in content_results]
                documents = []
                for doc_id in document_ids:
                    doc = await self.document_repository.load(doc_id)
                    if doc:
                        documents.append(doc)
            
            # 执行替换
            for document in documents:
                original_content = document.content
                
                if options.use_regex:
                    try:
                        flags = 0 if options.case_sensitive else re.IGNORECASE
                        new_content, count = re.subn(search_query, replace_text, original_content, flags=flags)
                    except re.error as e:
                        logger.error(f"正则表达式错误: {e}")
                        continue
                else:
                    if options.case_sensitive:
                        new_content = original_content.replace(search_query, replace_text)
                    else:
                        # 大小写不敏感的替换
                        import re
                        pattern = re.escape(search_query)
                        new_content = re.sub(pattern, replace_text, original_content, flags=re.IGNORECASE)
                    
                    count = original_content.count(search_query) if options.case_sensitive else \
                           len(re.findall(re.escape(search_query), original_content, re.IGNORECASE))
                
                if count > 0:
                    document.content = new_content
                    await self.document_repository.save(document)
                    
                    replaced_count += count
                    affected_documents.append({
                        "document_id": document.id,
                        "title": document.title,
                        "replacements": count
                    })
            
            result = {
                "success": True,
                "replaced_count": replaced_count,
                "affected_documents": affected_documents,
                "total_documents": len(affected_documents)
            }
            
            logger.info(f"搜索替换完成: {replaced_count} 处替换，{len(affected_documents)} 个文档")
            return result
            
        except Exception as e:
            logger.error(f"搜索替换失败: {e}")
            return {"success": False, "error": str(e)}

    def _create_search_matches(self, text: str, query: str, options: SearchOptions) -> List[SearchMatch]:
        """创建搜索匹配项"""
        matches = []
        if not text or not query:
            return matches

        lines = text.split('\n')
        for line_number, line in enumerate(lines, 1):
            if self._text_matches(line, query, options):
                positions = self._find_match_positions(line, query, options)
                for pos in positions:
                    # 生成高亮内容
                    highlighted = (
                        line[:pos['start']] +
                        "**" + line[pos['start']:pos['end']] + "**" +
                        line[pos['end']:]
                    )

                    match = SearchMatch(
                        line_number=line_number,
                        line_content=line,
                        match_start=pos['start'],
                        match_end=pos['end'],
                        highlighted_content=highlighted
                    )

                    # 添加上下文
                    if options.include_context:
                        context_start = max(0, line_number - options.context_lines - 1)
                        context_end = min(len(lines), line_number + options.context_lines)
                        match.context_before = '\n'.join(lines[context_start:line_number-1])
                        match.context_after = '\n'.join(lines[line_number:context_end])

                    matches.append(match)

        return matches

    async def _add_to_history(self, query: str, options: SearchOptions, result_count: int, execution_time: float):
        """添加到搜索历史"""
        try:
            history_item = SearchHistoryItem(
                id=str(uuid4()),
                query=query,
                timestamp=datetime.now(),
                result_count=result_count,
                search_options=asdict(options),
                execution_time=execution_time
            )

            # 移除重复项
            self._search_history = [h for h in self._search_history if h.query != query]

            # 添加到开头
            self._search_history.insert(0, history_item)

            # 限制历史大小
            if len(self._search_history) > 100:
                self._search_history = self._search_history[:100]

            # 保存到文件
            self._save_search_history()

        except Exception as e:
            logger.error(f"添加搜索历史失败: {e}")

    async def _update_search_statistics(self, query: str, options: SearchOptions, result_count: int, execution_time: float):
        """更新搜索统计"""
        try:
            self._search_stats.total_searches += 1
            self._search_stats.total_results += result_count

            # 更新平均值
            if self._search_stats.total_searches > 0:
                self._search_stats.average_results_per_search = (
                    self._search_stats.total_results / self._search_stats.total_searches
                )

                # 更新平均执行时间
                total_time = (self._search_stats.average_execution_time * (self._search_stats.total_searches - 1) + execution_time)
                self._search_stats.average_execution_time = total_time / self._search_stats.total_searches

            # 更新热门搜索词
            term_counts = Counter([item.query for item in self._search_history[:50]])
            self._search_stats.most_searched_terms = term_counts.most_common(10)

            # 更新按小时统计
            hour = datetime.now().hour
            self._search_stats.search_frequency_by_hour[hour] = (
                self._search_stats.search_frequency_by_hour.get(hour, 0) + 1
            )

            # 更新按天统计
            day = datetime.now().strftime('%Y-%m-%d')
            self._search_stats.search_frequency_by_day[day] = (
                self._search_stats.search_frequency_by_day.get(day, 0) + 1
            )

            # 更新热门文档类型
            if options.document_types:
                type_counts = Counter()
                for doc_type in options.document_types:
                    type_counts[doc_type.value] += 1
                self._search_stats.popular_document_types = type_counts.most_common(10)

            # 保存统计
            self._save_search_statistics()

        except Exception as e:
            logger.error(f"更新搜索统计失败: {e}")

    async def fuzzy_search(self, query: str, options: Optional[SearchOptions] = None) -> List[SearchResult]:
        """模糊搜索"""
        try:
            options = options or SearchOptions()
            options.fuzzy_search = True

            # 生成模糊查询词
            fuzzy_queries = self._generate_fuzzy_queries(query, options.fuzzy_threshold)

            all_results = []
            for fuzzy_query in fuzzy_queries:
                results = await self.search_all(fuzzy_query, options)
                all_results.extend(results)

            # 去重并按相关性排序
            unique_results = {}
            for result in all_results:
                key = f"{result.item_type}:{result.item_id}"
                if key not in unique_results or result.relevance_score > unique_results[key].relevance_score:
                    unique_results[key] = result

            final_results = list(unique_results.values())
            final_results.sort(key=lambda r: r.relevance_score, reverse=True)

            return final_results[:options.max_results]

        except Exception as e:
            logger.error(f"模糊搜索失败: {e}")
            return []

    def _generate_fuzzy_queries(self, query: str, threshold: float) -> List[str]:
        """生成模糊查询词"""
        queries = [query]

        # 简单的模糊匹配：添加通配符
        if len(query) > 2:
            queries.append(f"*{query}*")
            queries.append(f"{query}*")
            queries.append(f"*{query}")

        # 处理拼写错误（简单实现）
        if len(query) > 3:
            # 删除一个字符
            for i in range(len(query)):
                fuzzy_query = query[:i] + query[i+1:]
                if len(fuzzy_query) > 1:
                    queries.append(fuzzy_query)

            # 替换一个字符
            for i in range(len(query)):
                for char in 'abcdefghijklmnopqrstuvwxyz':
                    if char != query[i]:
                        fuzzy_query = query[:i] + char + query[i+1:]
                        queries.append(fuzzy_query)

        return list(set(queries))

    async def advanced_search(self, search_criteria: Dict[str, Any]) -> List[SearchResult]:
        """高级搜索"""
        try:
            options = SearchOptions()

            # 解析搜索条件
            query = search_criteria.get('query', '')
            options.case_sensitive = search_criteria.get('case_sensitive', False)
            options.whole_words = search_criteria.get('whole_words', False)
            options.use_regex = search_criteria.get('use_regex', False)
            options.fuzzy_search = search_criteria.get('fuzzy_search', False)

            # 文档类型过滤
            if 'document_types' in search_criteria:
                options.document_types = [
                    DocumentType(dt) for dt in search_criteria['document_types']
                ]

            # 日期范围过滤
            if 'date_from' in search_criteria and 'date_to' in search_criteria:
                date_from = datetime.fromisoformat(search_criteria['date_from'])
                date_to = datetime.fromisoformat(search_criteria['date_to'])
                options.date_range = (date_from, date_to)

            # 作者过滤
            options.author_filter = search_criteria.get('author_filter')

            # 相关性阈值
            options.min_relevance_score = search_criteria.get('min_relevance_score', 0.0)

            # 结果数量限制
            options.max_results = search_criteria.get('max_results', 100)

            # 执行搜索
            if options.fuzzy_search:
                return await self.fuzzy_search(query, options)
            else:
                return await self.search_all(query, options)

        except Exception as e:
            logger.error(f"高级搜索失败: {e}")
            return []

    def get_search_history(self, limit: int = 20) -> List[SearchHistoryItem]:
        """获取搜索历史"""
        return self._search_history[:limit]

    def get_search_statistics(self) -> SearchStatistics:
        """获取搜索统计"""
        return self._search_stats

    def clear_search_history(self):
        """清空搜索历史"""
        self._search_history.clear()
        self._save_search_history()
        logger.info("搜索历史已清空")

    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """获取搜索建议"""
        if not partial_query.strip():
            return []

        suggestions = []
        partial_lower = partial_query.lower()

        # 从历史中查找匹配的查询
        for item in self._search_history:
            query = item.query
            if query.lower().startswith(partial_lower) and query not in suggestions:
                suggestions.append(query)
                if len(suggestions) >= limit:
                    break

        return suggestions

    async def index_document(self, document: Document):
        """索引文档"""
        try:
            self.search_index.index_document(document)
            logger.debug(f"文档已索引: {document.id}")
        except Exception as e:
            logger.error(f"索引文档失败: {e}")

    async def remove_document_index(self, document_id: str):
        """移除文档索引"""
        try:
            self.search_index.remove_document(document_id)
            logger.debug(f"文档索引已移除: {document_id}")
        except Exception as e:
            logger.error(f"移除文档索引失败: {e}")

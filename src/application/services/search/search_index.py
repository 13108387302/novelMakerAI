#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索索引

提供文档索引的创建、更新和查询功能
"""

import sqlite3
import json
import threading
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

from .search_models import SearchResult, SearchMatch, IndexStatus, IndexException
from src.domain.entities.document import Document
from src.shared.utils.logger import get_logger
from src.shared.utils.unified_performance import get_performance_manager, performance_monitor

logger = get_logger(__name__)


class SearchIndex:
    """搜索索引"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.performance_manager = get_performance_manager()  # 统一性能管理器
        self._ensure_database()
        
    def _ensure_database(self):
        """确保数据库存在"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_index (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        content TEXT,
                        document_type TEXT,
                        project_id TEXT,
                        metadata TEXT,
                        word_count INTEGER,
                        created_at TEXT,
                        updated_at TEXT,
                        indexed_at TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS word_index (
                        word TEXT,
                        document_id TEXT,
                        frequency INTEGER,
                        positions TEXT,
                        PRIMARY KEY (word, document_id)
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_word_index_word 
                    ON word_index(word)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_index_project 
                    ON document_index(project_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_index_type 
                    ON document_index(document_type)
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"创建搜索索引数据库失败: {e}")
            raise IndexException(f"无法创建搜索索引: {e}")
    
    def add_document(self, document: Document) -> bool:
        """添加文档到索引"""
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    # 删除旧索引
                    self._remove_document_from_index(conn, document.id)
                    
                    # 添加文档信息
                    conn.execute("""
                        INSERT OR REPLACE INTO document_index 
                        (id, title, content, document_type, project_id, metadata, 
                         word_count, created_at, updated_at, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        document.id,
                        document.title,
                        document.content,
                        document.document_type.value if document.document_type else "",
                        document.project_id,
                        json.dumps(document.metadata or {}),
                        len(document.content.split()) if document.content else 0,
                        document.created_at.isoformat() if document.created_at else "",
                        document.updated_at.isoformat() if document.updated_at else "",
                        datetime.now().isoformat()
                    ))
                    
                    # 构建词汇索引
                    self._build_word_index(conn, document)
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"添加文档到索引失败: {e}")
            return False
    
    def remove_document(self, document_id: str) -> bool:
        """从索引中移除文档"""
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    self._remove_document_from_index(conn, document_id)
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"从索引移除文档失败: {e}")
            return False
    
    def _remove_document_from_index(self, conn: sqlite3.Connection, document_id: str):
        """从索引中移除文档（内部方法）"""
        conn.execute("DELETE FROM document_index WHERE id = ?", (document_id,))
        conn.execute("DELETE FROM word_index WHERE document_id = ?", (document_id,))
    
    def _build_word_index(self, conn: sqlite3.Connection, document: Document):
        """构建词汇索引"""
        if not document.content:
            return
        
        # 简单的词汇分割（可以改进为更复杂的分词）
        words = self._tokenize(document.content + " " + document.title)
        word_freq = Counter(words)
        
        for word, frequency in word_freq.items():
            if len(word) < 2:  # 忽略太短的词
                continue
                
            # 查找词汇位置
            positions = self._find_word_positions(document.content, word)
            
            conn.execute("""
                INSERT OR REPLACE INTO word_index 
                (word, document_id, frequency, positions)
                VALUES (?, ?, ?, ?)
            """, (
                word.lower(),
                document.id,
                frequency,
                json.dumps(positions)
            ))
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        import re
        # 简单的分词，可以改进
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _find_word_positions(self, text: str, word: str) -> List[int]:
        """查找词汇在文本中的位置（优化版本）"""
        # 使用对象池获取位置列表
        from src.shared.utils.object_pool import acquire_object, release_object

        positions = acquire_object('list')
        try:
            word_lower = word.lower()
            text_lower = text.lower()
            word_len = len(word_lower)

            # 使用更高效的搜索算法
            start = 0
            while start < len(text_lower):
                pos = text_lower.find(word_lower, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + word_len  # 跳过整个词，避免重叠匹配

            # 复制结果并释放池对象
            result = positions.copy()
            return result

        finally:
            release_object('list', positions)
    
    @performance_monitor("搜索执行")
    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """搜索文档（优化版本，带缓存）"""
        # 生成缓存键
        cache_key = f"search:{query.strip().lower()}:{limit}"

        # 尝试从缓存获取结果
        cache_result = self.performance_manager.cache_get(cache_key)
        if cache_result.success:
            logger.debug(f"搜索缓存命中: {query}")
            return cache_result.data

        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row

                    # 优化的搜索实现
                    words = self._tokenize(query)
                    if not words:
                        return []

                    # 使用更高效的查询策略
                    if len(words) == 1:
                        # 单词搜索优化
                        cursor = conn.execute("""
                            SELECT d.*, w.frequency as relevance_score
                            FROM document_index d
                            JOIN word_index w ON d.id = w.document_id
                            WHERE w.word LIKE ?
                            ORDER BY w.frequency DESC, d.updated_at DESC
                            LIMIT ?
                        """, [f"%{words[0]}%", limit])
                    else:
                        # 多词搜索优化
                        placeholders = " OR ".join(["w.word LIKE ?"] * len(words))
                        search_params = [f"%{word}%" for word in words]

                        cursor = conn.execute(f"""
                            SELECT d.*,
                                   SUM(w.frequency) as relevance_score,
                                   COUNT(DISTINCT w.word) as word_matches
                            FROM document_index d
                            JOIN word_index w ON d.id = w.document_id
                            WHERE {placeholders}
                            GROUP BY d.id
                            ORDER BY word_matches DESC, relevance_score DESC, d.updated_at DESC
                            LIMIT ?
                        """, search_params + [limit])
                    
                    results = []
                    for row in cursor:
                        result = {
                            'id': row['id'],
                            'title': row['title'],
                            'content': row['content'],
                            'document_type': row['document_type'],
                            'project_id': row['project_id'],
                            'metadata': json.loads(row['metadata'] or '{}'),
                            'word_count': row['word_count'],
                            'relevance_score': float(row['total_frequency']),
                            'created_at': row['created_at'],
                            'updated_at': row['updated_at']
                        }
                        results.append(result)

                    # 缓存搜索结果
                    self.performance_manager.cache_set(cache_key, results, ttl=300)  # 5分钟缓存
                    logger.debug(f"搜索结果已缓存: {query}")

                    return results
                    
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def get_status(self) -> IndexStatus:
        """获取索引状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM document_index")
                total_docs = cursor.fetchone()[0]
                
                # 获取数据库文件大小
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                # 获取最后更新时间
                cursor = conn.execute("""
                    SELECT MAX(indexed_at) FROM document_index
                """)
                last_update_str = cursor.fetchone()[0]
                last_update = None
                if last_update_str:
                    try:
                        last_update = datetime.fromisoformat(last_update_str)
                    except:
                        pass
                
                return IndexStatus(
                    total_documents=total_docs,
                    indexed_documents=total_docs,
                    last_update=last_update,
                    index_size=db_size,
                    is_building=False,
                    build_progress=100.0
                )
                
        except Exception as e:
            logger.error(f"获取索引状态失败: {e}")
            return IndexStatus(errors=[str(e)])
    
    def rebuild_index(self, documents: List[Document]) -> bool:
        """重建索引"""
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    # 清空现有索引
                    conn.execute("DELETE FROM document_index")
                    conn.execute("DELETE FROM word_index")
                    conn.commit()
                    
                    # 重新添加所有文档
                    for document in documents:
                        self._add_document_to_connection(conn, document)
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False
    
    def _add_document_to_connection(self, conn: sqlite3.Connection, document: Document):
        """在给定连接上添加文档（内部方法）"""
        # 添加文档信息
        conn.execute("""
            INSERT OR REPLACE INTO document_index 
            (id, title, content, document_type, project_id, metadata, 
             word_count, created_at, updated_at, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document.id,
            document.title,
            document.content,
            document.document_type.value if document.document_type else "",
            document.project_id,
            json.dumps(document.metadata or {}),
            len(document.content.split()) if document.content else 0,
            document.created_at.isoformat() if document.created_at else "",
            document.updated_at.isoformat() if document.updated_at else "",
            datetime.now().isoformat()
        ))
        
        # 构建词汇索引
        self._build_word_index(conn, document)
    
    def get_word_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """获取词汇建议"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT word 
                    FROM word_index 
                    WHERE word LIKE ? 
                    ORDER BY word 
                    LIMIT ?
                """, (f"{prefix.lower()}%", limit))
                
                return [row[0] for row in cursor]
                
        except Exception as e:
            logger.error(f"获取词汇建议失败: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                
                # 文档统计
                cursor = conn.execute("SELECT COUNT(*) FROM document_index")
                stats['total_documents'] = cursor.fetchone()[0]
                
                # 词汇统计
                cursor = conn.execute("SELECT COUNT(DISTINCT word) FROM word_index")
                stats['unique_words'] = cursor.fetchone()[0]
                
                # 平均词汇数
                cursor = conn.execute("SELECT AVG(word_count) FROM document_index")
                avg_words = cursor.fetchone()[0]
                stats['average_words_per_document'] = float(avg_words) if avg_words else 0
                
                # 文档类型分布
                cursor = conn.execute("""
                    SELECT document_type, COUNT(*) 
                    FROM document_index 
                    GROUP BY document_type
                """)
                stats['document_types'] = dict(cursor.fetchall())
                
                return stats
                
        except Exception as e:
            logger.error(f"获取索引统计失败: {e}")
            return {}

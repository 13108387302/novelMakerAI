#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件系统文档仓储实现

基于文件系统的文档数据持久化实现
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.domain.entities.document import Document, DocumentType, DocumentStatus, create_document
from src.domain.repositories.document_repository import IDocumentRepository
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class FileDocumentRepository(IDocumentRepository):
    """
    文件系统文档仓储实现

    基于文件系统的文档数据持久化实现，使用JSON格式存储文档元数据，
    使用文本文件存储文档内容。

    实现方式：
    - 使用JSON文件存储文档元数据
    - 使用独立的文本文件存储文档内容
    - 支持跨项目的文档查找
    - 提供完整的CRUD操作
    - 包含文档内容的搜索功能

    Attributes:
        base_path: 文档存储的基础路径
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        初始化文件系统文档仓储

        Args:
            base_path: 文档存储的基础路径，默认为用户目录下的.novel_editor/documents
        """
        self.base_path = base_path or Path.home() / ".novel_editor" / "documents"
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 添加文档路径缓存以提高性能
        self._document_path_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 缓存5分钟

    def _get_document_path(self, document_id: str) -> Path:
        """
        获取文档元数据文件路径

        Args:
            document_id: 文档唯一标识符

        Returns:
            Path: 文档元数据文件路径
        """
        return self.base_path / f"{document_id}.json"

    def _get_content_path(self, document_id: str) -> Path:
        """
        获取文档内容文件路径

        Args:
            document_id: 文档唯一标识符

        Returns:
            Path: 文档内容文件路径
        """
        return self.base_path / f"{document_id}_content.txt"

    async def _find_document_in_projects(self, document_id: str) -> tuple[Optional[Path], Optional[Path]]:
        """在所有项目目录中查找文档（带缓存优化）"""
        try:
            import time
            current_time = time.time()

            # 检查缓存
            if (document_id in self._document_path_cache and
                current_time - self._cache_timestamp < self._cache_ttl):
                cached_paths = self._document_path_cache[document_id]
                if cached_paths[0] and cached_paths[0].exists():
                    logger.debug(f"⚡ 从缓存中找到文档: {cached_paths[0]}")
                    return cached_paths
                else:
                    # 缓存的路径不存在，移除缓存
                    del self._document_path_cache[document_id]

            from config.settings import get_settings
            settings = get_settings()

            # 检查项目索引
            projects_dir = settings.data_dir / "projects"
            index_file = projects_dir / "projects_index.json"

            if index_file.exists():
                import json
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                # 在每个项目的documents目录中查找
                for project_id, project_info in index.items():
                    project_path_str = project_info.get('path')
                    if project_path_str:
                        project_path = Path(project_path_str)
                        docs_dir = project_path / "documents"

                        if docs_dir.exists():
                            doc_path = docs_dir / f"{document_id}.json"
                            content_path = docs_dir / f"{document_id}_content.txt"

                            if doc_path.exists():
                                logger.debug(f"🔍 在项目 {project_id} 中找到文档: {doc_path}")

                                # 缓存结果
                                self._document_path_cache[document_id] = (doc_path, content_path)
                                self._cache_timestamp = current_time

                                return doc_path, content_path

            return None, None

        except Exception as e:
            logger.error(f"在项目中查找文档失败: {e}")
            return None, None

    async def _get_document_save_path(self, document: Document) -> Path:
        """获取文档保存路径"""
        logger.debug(f"获取文档保存路径，项目ID: {document.project_id}")

        # 如果文档有项目ID，尝试在项目目录下保存
        if document.project_id:
            try:
                # 方法1: 检查全局索引
                from config.settings import get_settings
                settings = get_settings()

                # 确保projects目录存在
                projects_dir = settings.data_dir / "projects"
                projects_dir.mkdir(parents=True, exist_ok=True)

                index_file = projects_dir / "projects_index.json"
                logger.debug(f"检查索引文件: {index_file}")

                if index_file.exists():
                    import json
                    with open(index_file, 'r', encoding='utf-8') as f:
                        index = json.load(f)

                    logger.debug(f"索引中的项目数量: {len(index)}")
                    project_info = index.get(document.project_id)

                    if project_info:
                        logger.debug(f"找到项目信息: {project_info}")

                        # 尝试获取项目路径，支持多种字段名
                        project_path_str = project_info.get('path') or project_info.get('file_path')

                        # 如果是file_path，需要获取其父目录
                        if project_path_str:
                            project_path = Path(project_path_str)

                            # 如果是file_path（指向JSON文件），获取其父目录
                            if project_path_str == project_info.get('file_path') and project_path.suffix == '.json':
                                # 这是一个JSON文件路径，不是项目目录路径
                                # 对于这种情况，我们使用默认路径
                                logger.debug(f"项目存储为JSON文件: {project_path}，使用默认文档路径")
                            else:
                                # 这是一个项目目录路径
                                logger.debug(f"项目路径: {project_path}")

                                if project_path.exists():
                                    # 在项目目录下创建documents子目录
                                    documents_path = project_path / "documents"
                                    documents_path.mkdir(parents=True, exist_ok=True)
                                    logger.info(f"文档将保存到项目目录: {documents_path}")
                                    return documents_path
                                else:
                                    logger.debug(f"项目路径不存在: {project_path}")

                            # 检查是否有 'path' 字段（项目目录路径）
                            if 'path' in project_info and project_info['path']:
                                project_dir_path = Path(project_info['path'])
                                if project_dir_path.exists():
                                    documents_path = project_dir_path / "documents"
                                    documents_path.mkdir(parents=True, exist_ok=True)
                                    logger.info(f"文档将保存到项目目录: {documents_path}")
                                    return documents_path
                        else:
                            logger.warning(f"项目信息中没有路径字段")
                    else:
                        logger.warning(f"索引中未找到项目: {document.project_id}")
                else:
                    logger.warning(f"索引文件不存在: {index_file}")

                # 方法2: 在默认项目目录中查找
                default_project_path = projects_dir / document.project_id
                logger.debug(f"尝试默认项目路径: {default_project_path}")

                if default_project_path.exists():
                    documents_path = default_project_path / "documents"
                    documents_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"文档将保存到默认项目目录: {documents_path}")
                    return documents_path

            except Exception as e:
                logger.error(f"获取项目路径失败: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # 使用默认路径
        logger.info(f"使用默认文档目录: {self.base_path}")
        logger.debug(f"项目 {document.project_id} 的文档将保存到默认位置，这是正常的")
        return self.base_path
    
    async def save(self, document: Document) -> bool:
        """保存文档（带缓存清理）"""
        doc_temp_file = None
        content_temp_file = None
        try:
            # 确定保存路径
            save_path = await self._get_document_save_path(document)

            # 保存文档元数据
            doc_path = save_path / f"{document.id}.json"
            doc_temp_file = doc_path.with_suffix('.tmp')
            doc_data = document.to_dict()

            # 分离内容和元数据
            content = doc_data.pop('content', '')

            # 使用临时文件确保原子性写入
            with open(doc_temp_file, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2, ensure_ascii=False)

            # 验证写入的元数据文件
            with open(doc_temp_file, 'r', encoding='utf-8') as f:
                json.load(f)

            # 保存文档内容
            content_path = save_path / f"{document.id}_content.txt"
            content_temp_file = content_path.with_suffix('.tmp')

            with open(content_temp_file, 'w', encoding='utf-8') as f:
                f.write(content or '')

            # 原子性替换
            doc_temp_file.replace(doc_path)
            content_temp_file.replace(content_path)

            # 清理相关缓存
            self._clear_project_cache(document.project_id)

            logger.info(f"文档保存成功: {document.title} ({document.id})")
            return True

        except Exception as e:
            # 清理临时文件
            if doc_temp_file and doc_temp_file.exists():
                try:
                    doc_temp_file.unlink()
                except Exception:
                    pass
            if content_temp_file and content_temp_file.exists():
                try:
                    content_temp_file.unlink()
                except Exception:
                    pass
            logger.error(f"保存文档失败: {e}")
            return False
    
    async def load(self, document_id: str) -> Optional[Document]:
        """根据ID加载文档（性能优化版本）"""
        try:
            import time
            start_time = time.time()

            # 首先尝试从默认路径加载
            doc_path = self._get_document_path(document_id)
            content_path = self._get_content_path(document_id)

            # 如果默认路径不存在，尝试在所有项目目录中查找
            if not doc_path.exists():
                doc_path, content_path = await self._find_document_in_projects(document_id)
                if not doc_path or not doc_path.exists():
                    return None

            # 加载元数据
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)

                # 验证数据格式
                if not isinstance(doc_data, dict):
                    logger.error(f"文档元数据格式无效: {doc_path}")
                    return None

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"文档元数据文件格式错误 {doc_path}: {e}")
                return None

            # 加载内容
            content = ""
            if content_path and content_path.exists():
                try:
                    with open(content_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError as e:
                    logger.warning(f"文档内容编码错误 {content_path}: {e}")
                    # 尝试其他编码
                    try:
                        with open(content_path, 'r', encoding='gbk') as f:
                            content = f.read()
                    except Exception:
                        content = ""

            doc_data['content'] = content
            
            # 创建文档对象
            document_type = DocumentType(doc_data.get('type', 'chapter'))
            document = create_document(
                document_type=document_type,
                title=doc_data['metadata']['title'],
                document_id=doc_data['id'],
                content=content,
                status=DocumentStatus(doc_data.get('status', 'draft')),
                project_id=doc_data.get('project_id')
            )
            
            # 恢复其他属性
            if 'metadata' in doc_data:
                metadata = doc_data['metadata']
                document.metadata.description = metadata.get('description', '')
                document.metadata.tags = set(metadata.get('tags', []))
                document.metadata.author = metadata.get('author', '')
                if metadata.get('created_at'):
                    document.metadata.created_at = datetime.fromisoformat(metadata['created_at'])
                if metadata.get('updated_at'):
                    document.metadata.updated_at = datetime.fromisoformat(metadata['updated_at'])
            
            load_time = time.time() - start_time
            logger.info(f"⚡ 文档加载成功: {document.title} ({document.id}) - 耗时: {load_time:.3f}s")
            return document
            
        except Exception as e:
            logger.error(f"加载文档失败: {e}")
            return None
    
    async def delete(self, document_id: str) -> bool:
        """删除文档"""
        try:
            doc_path = self._get_document_path(document_id)
            content_path = self._get_content_path(document_id)
            
            if doc_path.exists():
                doc_path.unlink()
            
            if content_path.exists():
                content_path.unlink()
            
            logger.info(f"文档删除成功: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    async def exists(self, document_id: str) -> bool:
        """检查文档是否存在"""
        doc_path = self._get_document_path(document_id)
        return doc_path.exists()
    
    async def list_by_project(self, project_id: str) -> List[Document]:
        """列出项目中的所有文档（性能优化版本）"""
        try:
            import time
            start_time = time.time()

            logger.info(f"📋 开始获取项目文档列表: {project_id}")

            # 使用缓存的文档列表
            cache_key = f"project_docs_{project_id}"
            if hasattr(self, '_project_docs_cache'):
                cached_data = self._project_docs_cache.get(cache_key)
                if cached_data and time.time() - cached_data['timestamp'] < 60:  # 1分钟缓存
                    logger.info(f"⚡ 从缓存获取项目文档: {len(cached_data['documents'])} 个")
                    return cached_data['documents']

            documents = []
            found_doc_ids = set()

            # 优化的文档查找策略
            search_paths = await self._get_project_document_paths(project_id)

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                logger.debug(f"🔍 搜索路径: {search_path}")

                # 批量读取文档元数据，避免逐个加载完整文档
                doc_files = list(search_path.glob("*.json"))
                logger.debug(f"📄 找到 {len(doc_files)} 个文档文件")

                for doc_file in doc_files:
                    try:
                        # 只读取元数据，不加载内容
                        with open(doc_file, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)

                        # 验证文档数据的基本结构
                        if not self._validate_document_data(doc_data, project_id):
                            continue

                        if doc_data.get('id') not in found_doc_ids:
                            # 创建轻量级文档对象（不加载内容）
                            document = await self._create_lightweight_document(doc_data)
                            if document:
                                documents.append(document)
                                found_doc_ids.add(document.id)
                                logger.debug(f"✅ 成功加载文档: {document.title}")

                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON格式错误: {doc_file}, {e}")
                    except Exception as e:
                        logger.warning(f"读取文档元数据失败: {doc_file}, {e}")

            # 缓存结果
            if not hasattr(self, '_project_docs_cache'):
                self._project_docs_cache = {}
            self._project_docs_cache[cache_key] = {
                'documents': documents,
                'timestamp': time.time()
            }

            load_time = time.time() - start_time
            logger.info(f"⚡ 项目文档列表获取完成: {len(documents)} 个文档, 耗时: {load_time:.3f}s")

            return documents

        except Exception as e:
            logger.error(f"❌ 获取项目文档列表失败: {e}")
            return []

    async def _get_project_document_paths(self, project_id: str) -> List[Path]:
        """获取项目文档的搜索路径"""
        try:
            paths = []

            # 1. 项目特定路径
            try:
                from src.domain.entities.document import Document, DocumentType
                temp_doc = Document(
                    title="temp",
                    document_type=DocumentType.CHAPTER,
                    project_id=project_id
                )
                project_docs_path = await self._get_document_save_path(temp_doc)
                paths.append(project_docs_path)
            except Exception as e:
                logger.debug(f"获取项目特定路径失败: {e}")

            # 2. 默认文档目录
            paths.append(self.base_path)

            return paths

        except Exception as e:
            logger.error(f"获取项目文档路径失败: {e}")
            return [self.base_path]

    def _validate_document_data(self, doc_data: dict, project_id: str) -> bool:
        """验证文档数据的基本结构"""
        try:
            # 检查基本字段
            if not isinstance(doc_data, dict):
                return False

            # 检查ID
            if not doc_data.get('id'):
                logger.debug("文档数据缺少ID字段")
                return False

            # 检查项目ID匹配
            doc_project_id = doc_data.get('project_id')
            if doc_project_id != project_id:
                logger.debug(f"项目ID不匹配: 期望 {project_id}, 实际 {doc_project_id}")
                return False

            # 检查文档类型
            doc_type = doc_data.get('type') or doc_data.get('document_type')
            if not doc_type:
                logger.debug("文档数据缺少类型字段")
                return False

            return True

        except Exception as e:
            logger.debug(f"验证文档数据失败: {e}")
            return False

    async def _create_lightweight_document(self, doc_data: dict):
        """创建轻量级文档对象（不加载内容）"""
        try:
            from src.domain.entities.document import Document, DocumentType

            # 验证基本必要字段
            if 'id' not in doc_data:
                logger.debug(f"文档数据缺少必要字段: id")
                return None

            # 检查文档类型字段（可能是type或document_type）
            doc_type_value = doc_data.get('type') or doc_data.get('document_type')
            if not doc_type_value:
                logger.debug(f"文档数据缺少文档类型字段")
                return None

            # 安全转换文档类型
            try:
                if isinstance(doc_type_value, str):
                    doc_type = DocumentType(doc_type_value)
                else:
                    doc_type = DocumentType.CHAPTER
            except ValueError:
                logger.debug(f"无效的文档类型: {doc_type_value}, 使用默认类型")
                doc_type = DocumentType.CHAPTER

            # 检查标题（支持多种格式）
            title = self._extract_document_title(doc_data)

            # 提取元数据
            metadata = self._extract_document_metadata(doc_data, title)

            # 提取统计信息
            statistics = self._extract_document_statistics(doc_data)

            # 确保数据结构正确
            normalized_data = {
                'id': doc_data['id'],
                'type': doc_type.value,
                'content': '',  # 轻量级对象不加载内容
                'project_id': doc_data.get('project_id', ''),
                'metadata': metadata,
                'statistics': statistics,
                'status': doc_data.get('status', 'draft'),
                'type_specific_data': doc_data.get('type_specific_data', {})
            }

            # 创建文档对象
            document = Document.from_dict(normalized_data)

            return document

        except Exception as e:
            logger.debug(f"创建轻量级文档对象失败: {e}")
            return None

    def _extract_document_title(self, doc_data: dict) -> str:
        """提取文档标题（支持多种格式）"""
        # 方法1: 从metadata中获取
        if 'metadata' in doc_data and isinstance(doc_data['metadata'], dict):
            title = doc_data['metadata'].get('title', '')
            if title:
                return title

        # 方法2: 从顶级字段获取
        title = doc_data.get('title', '')
        if title:
            return title

        # 方法3: 从name字段获取（兼容旧格式）
        title = doc_data.get('name', '')
        if title:
            return title

        # 方法4: 使用默认标题
        doc_id = doc_data.get('id', 'unknown')
        return f"文档_{doc_id[:8]}"

    def _extract_document_metadata(self, doc_data: dict, title: str) -> dict:
        """提取文档元数据"""
        metadata = {
            'title': title,
            'description': '',
            'tags': [],
            'author': '',
            'created_at': '',
            'updated_at': ''
        }

        # 从metadata字段提取
        if 'metadata' in doc_data and isinstance(doc_data['metadata'], dict):
            source_metadata = doc_data['metadata']
            metadata.update({
                'description': source_metadata.get('description', ''),
                'tags': source_metadata.get('tags', []),
                'author': source_metadata.get('author', ''),
                'created_at': source_metadata.get('created_at', ''),
                'updated_at': source_metadata.get('updated_at', '')
            })

        # 兼容旧格式的顶级字段
        if not metadata['created_at']:
            metadata['created_at'] = doc_data.get('created_at', '')
        if not metadata['updated_at']:
            metadata['updated_at'] = doc_data.get('updated_at', '')

        return metadata

    def _extract_document_statistics(self, doc_data: dict) -> dict:
        """提取文档统计信息"""
        default_stats = {
            'word_count': 0,
            'character_count': 0,
            'paragraph_count': 0,
            'sentence_count': 0,
            'reading_time_minutes': 0.0
        }

        # 从statistics字段提取
        if 'statistics' in doc_data and isinstance(doc_data['statistics'], dict):
            stats = doc_data['statistics']
            default_stats.update({
                'word_count': max(0, stats.get('word_count', 0)),
                'character_count': max(0, stats.get('character_count', 0)),
                'paragraph_count': max(0, stats.get('paragraph_count', 0)),
                'sentence_count': max(0, stats.get('sentence_count', 0)),
                'reading_time_minutes': max(0.0, stats.get('reading_time_minutes', 0.0))
            })

        return default_stats

    def _clear_project_cache(self, project_id: str) -> None:
        """清理指定项目的缓存"""
        try:
            if hasattr(self, '_project_docs_cache'):
                cache_key = f"project_docs_{project_id}"
                if cache_key in self._project_docs_cache:
                    del self._project_docs_cache[cache_key]
                    logger.debug(f"✅ 已清理项目文档缓存: {project_id}")

        except Exception as e:
            logger.debug(f"清理项目缓存失败: {e}")

    def clear_all_cache(self) -> None:
        """清理所有缓存"""
        try:
            if hasattr(self, '_project_docs_cache'):
                self._project_docs_cache.clear()
                logger.debug("✅ 已清理所有文档缓存")

            if hasattr(self, '_document_path_cache'):
                self._document_path_cache.clear()
                logger.debug("✅ 已清理文档路径缓存")

        except Exception as e:
            logger.debug(f"清理所有缓存失败: {e}")
    
    async def list_by_type(
        self, 
        document_type: DocumentType, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """根据类型列出文档"""
        documents = []
        
        for doc_file in self.base_path.glob("*.json"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                if (doc_data.get('document_type') == document_type.value and
                    (project_id is None or doc_data.get('project_id') == project_id)):
                    document = await self.load(doc_data['id'])
                    if document:
                        documents.append(document)
            except Exception as e:
                logger.warning(f"加载文档失败: {doc_file}, {e}")
        
        return documents
    
    async def list_by_status(
        self, 
        status: DocumentStatus, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """根据状态列出文档"""
        documents = []
        
        for doc_file in self.base_path.glob("*.json"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                if (doc_data.get('status') == status.value and
                    (project_id is None or doc_data.get('project_id') == project_id)):
                    document = await self.load(doc_data['id'])
                    if document:
                        documents.append(document)
            except Exception as e:
                logger.warning(f"加载文档失败: {doc_file}, {e}")
        
        return documents
    
    async def search(
        self, 
        query: str, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """搜索文档"""
        documents = []
        query_lower = query.lower()
        
        for doc_file in self.base_path.glob("*.json"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                if project_id and doc_data.get('project_id') != project_id:
                    continue
                
                # 搜索标题和描述
                metadata = doc_data.get('metadata', {})
                title = metadata.get('title', '').lower()
                description = metadata.get('description', '').lower()
                tags = metadata.get('tags', [])
                
                if (query_lower in title or 
                    query_lower in description or
                    any(query_lower in tag.lower() for tag in tags)):
                    document = await self.load(doc_data['id'])
                    if document:
                        documents.append(document)
            except Exception as e:
                logger.warning(f"搜索文档失败: {doc_file}, {e}")
        
        return documents
    
    async def search_content(
        self, 
        query: str, 
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档内容"""
        results = []
        query_lower = query.lower()
        
        for content_file in self.base_path.glob("*_content.txt"):
            try:
                document_id = content_file.stem.replace('_content', '')
                
                # 检查项目ID
                if project_id:
                    doc_path = self._get_document_path(document_id)
                    if doc_path.exists():
                        with open(doc_path, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                        if doc_data.get('project_id') != project_id:
                            continue
                
                # 搜索内容
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if query_lower in content.lower():
                    # 查找匹配的上下文
                    lines = content.split('\n')
                    matches = []
                    
                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            # 获取上下文（前后各2行）
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(lines[start:end])
                            
                            matches.append({
                                "line_number": i + 1,
                                "line": line.strip(),
                                "context": context
                            })
                    
                    if matches:
                        results.append({
                            "document_id": document_id,
                            "matches": matches
                        })
            
            except Exception as e:
                logger.warning(f"搜索内容失败: {content_file}, {e}")
        
        return results
    
    async def get_recent_documents(
        self, 
        limit: int = 10, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """获取最近编辑的文档"""
        documents = []
        
        for doc_file in self.base_path.glob("*.json"):
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                if project_id and doc_data.get('project_id') != project_id:
                    continue
                
                document = await self.load(doc_data['id'])
                if document:
                    documents.append(document)
            except Exception as e:
                logger.warning(f"加载文档失败: {doc_file}, {e}")
        
        # 按更新时间排序
        documents.sort(
            key=lambda d: d.metadata.updated_at,
            reverse=True
        )
        
        return documents[:limit]
    
    async def update_content(self, document_id: str, content: str) -> bool:
        """更新文档内容"""
        try:
            document = await self.load(document_id)
            if not document:
                return False
            
            document.content = content
            return await self.save(document)
            
        except Exception as e:
            logger.error(f"更新文档内容失败: {e}")
            return False
    
    async def update_metadata(
        self, 
        document_id: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """更新文档元数据"""
        try:
            document = await self.load(document_id)
            if not document:
                return False
            
            # 更新元数据
            for key, value in metadata.items():
                if hasattr(document.metadata, key):
                    setattr(document.metadata, key, value)
            
            document.metadata.updated_at = datetime.now()
            return await self.save(document)
            
        except Exception as e:
            logger.error(f"更新文档元数据失败: {e}")
            return False
    
    async def get_word_count(self, document_id: str) -> int:
        """获取文档字数"""
        try:
            content_path = self._get_content_path(document_id)
            if not content_path.exists():
                return 0
            
            with open(content_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return len(content.split()) if content.strip() else 0
            
        except Exception as e:
            logger.error(f"获取文档字数失败: {e}")
            return 0
    
    async def get_statistics(self, document_id: str) -> Dict[str, Any]:
        """获取文档统计信息"""
        try:
            document = await self.load(document_id)
            if not document:
                return {}
            
            return {
                "document_id": document_id,
                "title": document.title,
                "word_count": document.statistics.word_count,
                "character_count": document.statistics.character_count,
                "paragraph_count": document.statistics.paragraph_count,
                "sentence_count": document.statistics.sentence_count,
                "reading_time_minutes": document.statistics.reading_time_minutes,
                "last_edit_time": document.statistics.last_edit_time.isoformat() if document.statistics.last_edit_time else None,
                "edit_count": document.statistics.edit_count,
                "created_at": document.metadata.created_at.isoformat(),
                "updated_at": document.metadata.updated_at.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"获取文档统计信息失败: {e}")
            return {}

    # 版本管理方法（简单实现）
    async def cleanup_old_versions(self, document_id: str, keep_count: int = 10) -> bool:
        """清理旧版本"""
        # 简单实现：不支持版本管理
        logger.warning("cleanup_old_versions方法暂未实现")
        return True

    async def delete_version(self, document_id: str, version_id: str) -> bool:
        """删除指定版本"""
        # 简单实现：不支持版本管理
        logger.warning("delete_version方法暂未实现")
        return False

    async def get_version_diff(self, document_id: str, version1_id: str, version2_id: str) -> Optional[Dict[str, Any]]:
        """获取版本差异"""
        # 简单实现：不支持版本管理
        logger.warning("get_version_diff方法暂未实现")
        return None

    async def restore_version(self, document_id: str, version_id: str) -> bool:
        """恢复到指定版本"""
        # 简单实现：不支持版本管理
        logger.warning("restore_version方法暂未实现")
        return False

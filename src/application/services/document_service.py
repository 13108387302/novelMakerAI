#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档服务

管理文档的创建、编辑、保存等操作
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path

from src.domain.entities.document import Document, DocumentType, DocumentStatus, create_document
from src.domain.repositories.document_repository import IDocumentRepository
from src.domain.events.document_events import (
    DocumentCreatedEvent, DocumentOpenedEvent, DocumentClosedEvent,
    DocumentSavedEvent, DocumentContentChangedEvent
)
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger
from src.shared.constants import DEFAULT_RECENT_DOCUMENTS_LIMIT

if TYPE_CHECKING:
    from src.application.services.search.search_service_refactored import SearchService

logger = get_logger(__name__)

# 文档服务常量
COPY_DESCRIPTION_PREFIX = "复制自: "


class DocumentService:
    """
    文档服务

    管理文档的完整生命周期，包括创建、打开、编辑、保存和关闭操作。
    提供文档状态管理和事件发布功能，支持多文档并发操作。

    实现方式：
    - 使用仓储模式进行数据持久化
    - 通过事件总线发布文档状态变更事件
    - 维护当前打开文档的内存缓存
    - 提供文档工厂方法支持不同类型文档创建
    - 支持异步操作确保UI响应性

    Attributes:
        document_repository: 文档仓储接口
        event_bus: 事件总线用于发布文档事件
        _open_documents: 当前打开文档的缓存字典
        _current_document_id: 当前活动文档的ID
    """

    def __init__(
        self,
        document_repository: IDocumentRepository,
        event_bus: EventBus,
        search_service: Optional['SearchService'] = None
    ):
        """
        初始化文档服务

        Args:
            document_repository: 文档仓储接口实现
            event_bus: 事件总线用于发布文档相关事件
            search_service: 搜索服务（可选，用于统一搜索功能）
        """
        self.document_repository = document_repository
        self.event_bus = event_bus
        self.search_service = search_service
        self._open_documents: Dict[str, Document] = {}
        self._current_document_id: Optional[str] = None
    
    async def create_document(
        self,
        title: str,
        project_id: Optional[str] = None,
        document_type: DocumentType = DocumentType.CHAPTER,
        content: str = ""
    ) -> Optional[Document]:
        """
        创建新文档

        使用工厂模式创建指定类型的文档，并保存到仓储中。
        创建成功后发布文档创建事件。

        实现方式：
        - 使用create_document工厂函数创建文档实例
        - 通过仓储接口保存文档
        - 发布DocumentCreatedEvent事件
        - 提供完整的错误处理和日志记录

        Args:
            title: 文档标题
            project_id: 所属项目ID（可选）
            document_type: 文档类型，默认为章节
            content: 初始内容，默认为空

        Returns:
            Optional[Document]: 创建成功返回文档实例，失败返回None

        Raises:
            Exception: 文档创建或保存失败时抛出
        """
        try:
            logger.info(f"📝 开始创建文档: {title} (类型: {document_type.value}, 项目: {project_id})")

            # 使用工厂函数创建文档
            document = create_document(
                document_type=document_type,
                title=title,
                content=content,
                project_id=project_id
            )

            logger.info(f"📄 文档实体已创建: {document.title} (ID: {document.id})")

            # 保存文档
            success = await self.document_repository.save(document)
            if success:
                logger.info(f"💾 文档保存成功: {document.title} (ID: {document.id})")

                # 发布文档创建事件
                event = DocumentCreatedEvent(
                    document_id=document.id,
                    document_title=document.title,
                    document_type=document_type,
                    project_id=project_id
                )
                try:
                    logger.info(f"📢 发布文档创建事件: {document.title} (ID: {document.id})")
                    await self.event_bus.publish_async(event)
                    logger.info(f"✅ 文档创建事件发布成功: {document.title}")
                except Exception as e:
                    logger.warning(f"发布文档创建事件失败: {e}")

                logger.info(f"🎉 文档创建完成: {title} ({document.id})")
                return document
            else:
                logger.error(f"❌ 文档保存失败: {title}")
                return None
                
        except Exception as e:
            logger.error(f"创建文档失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None
    
    async def open_document(self, document_id: str) -> Optional[Document]:
        """打开文档"""
        try:
            # 如果已经打开，直接返回
            if document_id in self._open_documents:
                self._current_document_id = document_id
                return self._open_documents[document_id]
            
            # 从仓储加载文档
            document = await self.document_repository.load(document_id)
            if document:
                # 添加到打开的文档列表
                self._open_documents[document_id] = document
                self._current_document_id = document_id
                
                # 发布文档打开事件
                event = DocumentOpenedEvent(
                    document_id=document.id,
                    document_title=document.title,
                    project_id=document.project_id
                )
                try:
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布文档打开事件失败: {e}")
                
                logger.info(f"文档打开成功: {document.title} ({document.id})")
                return document
            else:
                logger.warning(f"文档不存在: {document_id}")
                return None
                
        except Exception as e:
            logger.error(f"打开文档失败: {e}")
            return None
    
    async def close_document(self, document_id: str) -> bool:
        """关闭文档"""
        try:
            if document_id in self._open_documents:
                document = self._open_documents[document_id]

                # 保存文档，如果保存失败则不关闭
                save_success = await self.save_document(document_id)
                if not save_success:
                    logger.error(f"保存文档失败，取消关闭操作: {document.title}")
                    return False

                # 从打开列表中移除
                del self._open_documents[document_id]
                
                # 如果是当前文档，清除当前文档ID
                if self._current_document_id == document_id:
                    self._current_document_id = None
                
                # 发布文档关闭事件
                event = DocumentClosedEvent(
                    document_id=document.id,
                    document_title=document.title
                )
                try:
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布文档关闭事件失败: {e}")
                
                logger.info(f"文档关闭: {document.title}")
                return True
            else:
                logger.warning(f"文档未打开: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"关闭文档失败: {e}")
            return False
    
    async def save_document(self, document_id: str) -> bool:
        """保存文档"""
        try:
            if document_id in self._open_documents:
                document = self._open_documents[document_id]
                
                success = await self.document_repository.save(document)
                if success:
                    # 发布文档保存事件
                    event = DocumentSavedEvent(
                        document_id=document.id,
                        document_title=document.title,
                        word_count=document.statistics.word_count,
                        character_count=document.statistics.character_count
                    )
                    await self.event_bus.publish_async(event)
                    
                    logger.info(f"文档保存成功: {document.title}")
                    return True
                else:
                    logger.error(f"文档保存失败: {document.title}")
                    return False
            else:
                logger.warning(f"文档未打开: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"保存文档失败: {e}")
            return False

    async def save_document_object(self, document: Document) -> bool:
        """保存文档对象"""
        try:
            logger.info(f"保存文档对象: {document.title}")

            # 直接保存文档对象
            success = await self.document_repository.save(document)
            if success:
                # 如果文档在打开列表中，更新它
                if document.id in self._open_documents:
                    self._open_documents[document.id] = document

                # 发布文档保存事件
                event = DocumentSavedEvent(
                    document_id=document.id,
                    document_title=document.title,
                    word_count=document.statistics.word_count,
                    character_count=document.statistics.character_count
                )
                await self.event_bus.publish_async(event)

                logger.info(f"文档对象保存成功: {document.title}")
                return True
            else:
                logger.error(f"文档对象保存失败: {document.title}")
                return False

        except Exception as e:
            logger.error(f"保存文档对象失败: {e}")
            return False
    
    async def save_all_documents(self) -> bool:
        """保存所有打开的文档"""
        try:
            if not self._open_documents:
                logger.info("没有打开的文档需要保存")
                return True

            success_count = 0
            total_count = len(self._open_documents)
            # 创建文档ID列表的副本，避免在迭代过程中字典被修改
            document_ids = list(self._open_documents.keys())

            for document_id in document_ids:
                try:
                    if await self.save_document(document_id):
                        success_count += 1
                except Exception as e:
                    logger.error(f"保存文档 {document_id} 失败: {e}")

            logger.info(f"批量保存完成: {success_count}/{total_count} 个文档")
            return success_count == total_count

        except Exception as e:
            logger.error(f"批量保存失败: {e}")
            return False
    
    async def update_document_content(self, document_id: str, content: str) -> bool:
        """更新文档内容"""
        try:
            if document_id in self._open_documents:
                document = self._open_documents[document_id]
                old_content = document.content
                
                # 更新内容
                document.content = content
                
                # 发布内容变更事件
                event = DocumentContentChangedEvent(
                    document_id=document.id,
                    old_content=old_content,
                    new_content=content
                )
                await self.event_bus.publish_async(event)
                
                logger.debug(f"文档内容更新: {document.title}")
                return True
            else:
                logger.warning(f"文档未打开: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新文档内容失败: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            # 如果文档已打开，先关闭
            if document_id in self._open_documents:
                await self.close_document(document_id)
            
            success = await self.document_repository.delete(document_id)
            if success:
                logger.info(f"文档删除成功: {document_id}")
                return True
            else:
                logger.error(f"文档删除失败: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    async def list_documents_by_project(self, project_id: str) -> List[Document]:
        """列出项目中的所有文档"""
        try:
            documents = await self.document_repository.list_by_project(project_id)
            logger.info(f"获取项目文档列表成功: {len(documents)} 个文档")
            return documents
            
        except Exception as e:
            logger.error(f"获取项目文档列表失败: {e}")
            return []
    
    async def search_documents(
        self,
        query: str,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """搜索文档（优先使用SearchService）"""
        try:
            # 如果有SearchService，使用统一的搜索功能
            if self.search_service:
                from src.application.services.search.search_models import SearchQuery, SearchOptions, SearchFilter

                # 构建搜索查询
                search_query = SearchQuery(
                    text=query,
                    options=SearchOptions(search_in_titles=True, search_in_content=True),
                    filters=SearchFilter(projects={project_id} if project_id else set())
                )

                # 执行搜索
                result_set = self.search_service.search(search_query)

                # 转换结果为Document对象
                documents = []
                for result in result_set.results:
                    if result.item_type == "document":
                        document = await self.document_repository.get_by_id(result.item_id)
                        if document:
                            documents.append(document)

                logger.info(f"文档搜索完成（使用SearchService）: 找到 {len(documents)} 个结果")
                return documents

            # 回退到仓储搜索
            else:
                documents = await self.document_repository.search(query, project_id)
                logger.info(f"文档搜索完成（使用仓储）: 找到 {len(documents)} 个结果")
                return documents

        except Exception as e:
            logger.error(f"搜索文档失败: {e}")
            return []
    
    async def search_content(
        self,
        query: str,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索文档内容（优先使用SearchService）

        在文档内容中搜索指定的查询文本，优先使用统一的搜索服务。
        如果搜索服务不可用，则回退到仓储层的搜索功能。

        Args:
            query: 搜索查询文本
            project_id: 可选的项目ID，用于限制搜索范围

        Returns:
            List[Dict[str, Any]]: 搜索结果列表，包含匹配的文档信息
        """
        try:
            # 如果有SearchService，使用统一的搜索功能
            if self.search_service:
                from src.application.services.search.search_models import SearchQuery, SearchOptions, SearchFilter

                # 构建搜索查询
                search_query = SearchQuery(
                    text=query,
                    options=SearchOptions(
                        search_in_content=True,
                        search_in_titles=False,
                        include_context=True,
                        highlight_matches=True
                    ),
                    filters=SearchFilter(projects={project_id} if project_id else set())
                )

                # 执行搜索
                result_set = self.search_service.search(search_query)

                # 转换结果为内容匹配格式
                content_results = []
                for result in result_set.results:
                    if result.item_type == "document":
                        content_result = {
                            "document_id": result.item_id,
                            "document_title": result.title,
                            "content_preview": result.content_preview,
                            "relevance_score": result.relevance_score,
                            "matches": [
                                {
                                    "line_number": match.line_number,
                                    "line_content": match.line_content,
                                    "highlighted_content": match.highlighted_content,
                                    "context_before": match.context_before,
                                    "context_after": match.context_after
                                }
                                for match in result.matches
                            ]
                        }
                        content_results.append(content_result)

                logger.info(f"内容搜索完成（使用SearchService）: 找到 {len(content_results)} 个匹配")
                return content_results

            # 回退到仓储搜索
            else:
                results = await self.document_repository.search_content(query, project_id)
                logger.info(f"内容搜索完成（使用仓储）: 找到 {len(results)} 个匹配")
                return results

        except Exception as e:
            logger.error(f"搜索内容失败: {e}")
            return []
    
    async def get_recent_documents(
        self, 
        limit: int = DEFAULT_RECENT_DOCUMENTS_LIMIT,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """获取最近编辑的文档"""
        try:
            documents = await self.document_repository.get_recent_documents(limit, project_id)
            logger.info(f"获取最近文档成功: {len(documents)} 个文档")
            return documents
            
        except Exception as e:
            logger.error(f"获取最近文档失败: {e}")
            return []
    
    async def duplicate_document(self, document_id: str, new_title: str) -> Optional[Document]:
        """复制文档"""
        try:
            original = await self.document_repository.load(document_id)
            if not original:
                logger.warning(f"原文档不存在: {document_id}")
                return None
            
            # 创建副本
            duplicate = create_document(
                document_type=original.type,
                title=new_title,
                content=original.content,
                project_id=original.project_id
            )
            
            # 复制元数据
            duplicate.metadata.description = f"{COPY_DESCRIPTION_PREFIX}{original.title}"
            duplicate.metadata.tags = original.metadata.tags.copy()
            
            # 保存副本
            success = await self.document_repository.save(duplicate)
            if success:
                logger.info(f"文档复制成功: {new_title}")
                return duplicate
            else:
                logger.error(f"文档复制失败: {new_title}")
                return None
                
        except Exception as e:
            logger.error(f"复制文档失败: {e}")
            return None
    
    def get_open_documents(self) -> List[Document]:
        """获取所有打开的文档"""
        return list(self._open_documents.values())
    
    def get_current_document(self) -> Optional[Document]:
        """获取当前文档"""
        if self._current_document_id and self._current_document_id in self._open_documents:
            return self._open_documents[self._current_document_id]
        return None
    
    def set_current_document(self, document_id: str) -> bool:
        """设置当前文档"""
        if document_id in self._open_documents:
            self._current_document_id = document_id
            return True
        return False
    
    @property
    def current_document_id(self) -> Optional[str]:
        """当前文档ID"""
        return self._current_document_id
    
    @property
    def has_open_documents(self) -> bool:
        """是否有打开的文档"""
        return len(self._open_documents) > 0





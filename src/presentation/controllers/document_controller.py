#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档控制器

专门处理文档相关的UI操作和业务逻辑
"""

import logging
from typing import Optional, List, Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from src.application.services.document_service import DocumentService
from src.domain.entities.document import Document, DocumentType
from src.domain.events.document_events import (
    DocumentCreatedEvent,
    DocumentOpenedEvent,
    DocumentClosedEvent,
    DocumentSavedEvent,
    DocumentDeletedEvent,
    DocumentTitleChangedEvent,
)
from src.shared.utils.base_service import BaseService
from src.shared.constants import OPEN_DOCUMENT_DEBOUNCE_SECONDS

logger = logging.getLogger(__name__)


class DocumentController(BaseService, QObject):
    """
    文档控制器

    专门处理文档相关的操作，从主控制器中分离出来。
    负责文档的创建、打开、保存、关闭等操作。

    重构改进：
    - 单一职责：只处理文档相关操作
    - 减少主控制器的复杂度
    - 提供清晰的文档操作接口
    - 统一的异步处理机制
    """

    # 信号定义（统一发送领域事件对象）
    document_opened = pyqtSignal(object)   # DocumentOpenedEvent
    document_closed = pyqtSignal(object)   # DocumentClosedEvent
    document_created = pyqtSignal(object)  # DocumentCreatedEvent
    document_saved = pyqtSignal(object)    # DocumentSavedEvent
    document_deleted = pyqtSignal(object)  # DocumentDeletedEvent
    document_renamed = pyqtSignal(object)  # DocumentTitleChangedEvent
    status_message = pyqtSignal(str)

    def __init__(self, document_service: DocumentService):
        """
        初始化文档控制器

        Args:
            document_service: 文档服务
        """
        QObject.__init__(self)
        BaseService.__init__(self, "DocumentController")

        self.document_service = document_service

        # 操作状态跟踪
        self._creating_documents: Set[str] = set()
        self._opening_documents: Set[str] = set()
        self._last_open_time: dict = {}

    async def create_document(
        self,
        title: str,
        project_id: Optional[str] = None,
        document_type: DocumentType = DocumentType.CHAPTER,
        content: str = ""
    ) -> Optional[Document]:
        """
        创建新文档

        Args:
            title: 文档标题
            project_id: 所属项目ID
            document_type: 文档类型
            content: 初始内容

        Returns:
            Optional[Document]: 创建的文档实例
        """
        # 防止重复创建
        if title in self._creating_documents:
            self.logger.warning(f"文档 '{title}' 正在创建中，跳过重复创建")
            return None

        self._creating_documents.add(title)

        try:
            self.status_message.emit(f"正在创建文档: {title}")

            document = await self.document_service.create_document(
                title=title,
                project_id=project_id,
                document_type=document_type,
                content=content
            )

            if document:
                # 统一发出领域事件
                try:
                    event = DocumentCreatedEvent(
                        document_id=getattr(document, 'id', ''),
                        document_title=getattr(document, 'title', title) or title,
                        document_type=getattr(document, 'document_type', DocumentType.CHAPTER),
                        project_id=getattr(document, 'project_id', None)
                    )
                except Exception:
                    event = DocumentCreatedEvent(document_id=getattr(document, 'id', ''), document_title=title)
                self.document_created.emit(event)
                self.status_message.emit(f"文档创建成功: {title}")
                self.logger.info(f"文档创建成功: {title}")
                return document
            else:
                self.logger.error(f"文档创建失败: {title}")
                return None

        except Exception as e:
            self.logger.error(f"创建文档失败: {e}")
            return None
        finally:
            self._creating_documents.discard(title)

    async def open_document(self, document_id: str) -> Optional[Document]:
        """
        打开文档

        Args:
            document_id: 文档ID

        Returns:
            Optional[Document]: 打开的文档实例
        """
        # 防重复打开检查
        if not self._should_open_document(document_id):
            return None

        self._opening_documents.add(document_id)

        try:
            self.status_message.emit(f"正在打开文档: {document_id}")

            document = await self.document_service.open_document(document_id)

            if document:
                # 统一发出领域事件
                try:
                    event = DocumentOpenedEvent(
                        document_id=getattr(document, 'id', ''),
                        document_title=getattr(document, 'title', '')
                    )
                except Exception:
                    event = DocumentOpenedEvent(document_id=document_id, document_title='')
                self.document_opened.emit(event)
                self.status_message.emit(f"文档已打开: {getattr(document, 'title', document_id)}")
                self.logger.info(f"文档打开成功: {getattr(document, 'title', document_id)}")
                return document
            else:
                self.logger.warning(f"文档不存在: {document_id}")
                return None

        except Exception as e:
            self.logger.error(f"打开文档失败: {e}")
            return None
        finally:
            self._opening_documents.discard(document_id)

    async def save_document(self, document_id: str) -> bool:
        """
        保存文档

        Args:
            document_id: 文档ID

        Returns:
            bool: 保存是否成功
        """
        try:
            self.status_message.emit(f"正在保存文档: {document_id}")

            success = await self.document_service.save_document(document_id)

            if success:
                # 统一发出领域事件（缺少标题等信息时使用默认值）
                try:
                    doc = await self.document_service.open_document(document_id)  # 尝试获取文档信息
                    title = getattr(doc, 'title', '') if doc else ''
                except Exception:
                    title = ''
                event = DocumentSavedEvent(document_id=document_id, document_title=title)
                self.document_saved.emit(event)
                self.status_message.emit("文档保存成功")
                self.logger.info(f"文档保存成功: {document_id}")
                return True
            else:
                self.logger.error(f"文档保存失败: {document_id}")
                return False

        except Exception as e:
            self.logger.error(f"保存文档失败: {e}")
            return False

    async def save_all_documents(self) -> bool:
        """
        保存所有文档

        Returns:
            bool: 保存是否成功
        """
        try:
            self.status_message.emit("正在保存所有文档...")
            success = await self.document_service.save_all_documents()
            if success:
                self.status_message.emit("所有文档保存成功")
                self.logger.info("所有文档保存成功")
                return True
            else:
                self.logger.error("保存文档失败")
                return False
        except Exception as e:
            self.logger.error(f"保存所有文档失败: {e}")
            return False
    async def rename_document(self, document_id: str, new_title: str) -> bool:
        """
        重命名文档
        """
        try:
            success = await self.document_service.rename_document(document_id, new_title)
            if success:
                self.status_message.emit("文档重命名成功")
                event = DocumentTitleChangedEvent(document_id=document_id, old_title='', new_title=new_title)
                self.document_renamed.emit(event)
                self.logger.info(f"文档重命名成功: {document_id} -> {new_title}")
                return True
            else:
                self.logger.error(f"文档重命名失败: {document_id}")
                return False
        except Exception as e:
            self.logger.error(f"重命名文档失败: {e}")
            return False

    async def copy_document(self, document_id: str, new_title: str) -> Optional[Document]:
        """
        复制文档（调用服务层 duplicate_document）
        """
        try:
            doc = await self.document_service.duplicate_document(document_id, new_title)
            if doc:
                try:
                    event = DocumentCreatedEvent(
                        document_id=getattr(doc, 'id', ''),
                        document_title=getattr(doc, 'title', new_title) or new_title,
                        document_type=getattr(doc, 'document_type', DocumentType.CHAPTER),
                        project_id=getattr(doc, 'project_id', None)
                    )
                except Exception:
                    event = DocumentCreatedEvent(document_id=getattr(doc, 'id', ''), document_title=new_title)
                self.document_created.emit(event)
                self.status_message.emit("文档复制成功")
                self.logger.info(f"文档复制成功: {doc.title}")
                return doc
            else:
                self.logger.error(f"文档复制失败: {document_id}")
                return None
        except Exception as e:
            self.logger.error(f"复制文档失败: {e}")
            return None

    async def close_document(self, document_id: str) -> bool:
        """
        关闭文档

        Args:
            document_id: 文档ID

        Returns:
            bool: 关闭是否成功
        """
        try:
            success = await self.document_service.close_document(document_id)

            if success:
                event = DocumentClosedEvent(document_id=document_id, document_title='')
                self.document_closed.emit(event)
                self.logger.info(f"文档关闭成功: {document_id}")
                return True
            else:
                self.logger.error(f"文档关闭失败: {document_id}")
                return False

        except Exception as e:
            self.logger.error(f"关闭文档失败: {e}")
            return False
    async def delete_document(self, document_id: str) -> bool:
        """
        删除文档

        Args:
            document_id: 文档ID

        Returns:
            bool: 删除是否成功
        """
        try:
            success = await self.document_service.delete_document(document_id)
            if success:
                # 若编辑器中打开该文档，由 UI 层接收删除事件后自行关闭
                event = DocumentDeletedEvent(document_id=document_id, document_title='', document_type=DocumentType.CHAPTER)
                self.document_deleted.emit(event)
                self.logger.info(f"文档删除成功: {document_id}")
                self.status_message.emit("文档删除成功")
                return True
            else:
                self.logger.error(f"文档删除失败: {document_id}")
                return False
        except Exception as e:
            self.logger.error(f"删除文档失败: {e}")
            return False


    async def update_document_content(self, document_id: str, content: str) -> bool:
        """
        更新文档内容

        Args:
            document_id: 文档ID
            content: 新内容

        Returns:
            bool: 更新是否成功
        """
        try:
            success = await self.document_service.update_document_content(document_id, content)

            if success:
                self.logger.debug(f"文档内容更新成功: {document_id}")
                return True
            else:
                self.logger.error(f"文档内容更新失败: {document_id}")
                return False

        except Exception as e:
            self.logger.error(f"更新文档内容失败: {e}")
            return False

    async def reload_document(self, document_id: str) -> Optional[Document]:
        """强制重载指定文档（从仓储加载并覆盖打开缓存）"""
        try:
            doc = await self.document_service.reload_document(document_id)
            return doc
        except Exception as e:
            self.logger.error(f"重载文档失败: {e}")
            return None

    def _should_open_document(self, document_id: str) -> bool:
        """检查是否应该打开文档（防重复）"""
        import time
        current_time = time.time()

        # 检查是否正在打开
        if document_id in self._opening_documents:
            self.logger.debug(f"文档 {document_id} 正在打开中，跳过重复请求")
            return False

        # 检查是否在短时间内重复打开（防抖动）
        last_time = self._last_open_time.get(document_id, 0)
        if current_time - last_time < OPEN_DOCUMENT_DEBOUNCE_SECONDS:
            self.logger.debug(f"文档 {document_id} 在{OPEN_DOCUMENT_DEBOUNCE_SECONDS}秒内重复打开，跳过")
            return False

        # 记录打开时间
        self._last_open_time[document_id] = current_time
        return True

    @property
    def open_documents(self) -> List[Document]:
        """获取所有打开的文档"""
        return self.document_service.get_open_documents()

    @property
    def current_document(self) -> Optional[Document]:
        """获取当前文档"""
        return self.document_service.get_current_document()

    @property
    def has_open_documents(self) -> bool:
        """是否有打开的文档"""
        return self.document_service.has_open_documents

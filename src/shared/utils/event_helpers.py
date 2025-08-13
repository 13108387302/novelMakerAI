#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件构造辅助函数

统一由实体对象构造标准领域事件，减少重复代码和 try/except，
并提升字段一致性与可维护性。
"""

from typing import Optional

from src.domain.entities.document import Document
from src.domain.events.document_events import (
    DocumentCreatedEvent,
    DocumentOpenedEvent,
    DocumentClosedEvent,
    DocumentSavedEvent,
)


def build_document_created_event(doc: Document) -> DocumentCreatedEvent:
    return DocumentCreatedEvent(
        document_id=getattr(doc, "id", "") or "",
        document_title=getattr(doc, "title", "") or "",
        document_type=getattr(doc, "type", None) or getattr(doc, "document_type", None),
        project_id=getattr(doc, "project_id", None),
    )


def build_document_opened_event(doc: Document) -> DocumentOpenedEvent:
    return DocumentOpenedEvent(
        document_id=getattr(doc, "id", "") or "",
        document_title=getattr(doc, "title", "") or "",
        project_id=getattr(doc, "project_id", None),
    )


def build_document_closed_event(doc: Document) -> DocumentClosedEvent:
    return DocumentClosedEvent(
        document_id=getattr(doc, "id", "") or "",
        document_title=getattr(doc, "title", "") or "",
    )


def build_document_saved_event(doc: Document) -> DocumentSavedEvent:
    # 使用实体统计信息，避免在控制器/服务重复计算
    word_count = 0
    char_count = 0
    try:
        stats = getattr(doc, "statistics", None)
        if stats is not None:
            word_count = getattr(stats, "word_count", 0) or 0
            char_count = getattr(stats, "character_count", 0) or 0
    except Exception:
        pass
    return DocumentSavedEvent(
        document_id=getattr(doc, "id", "") or "",
        document_title=getattr(doc, "title", "") or "",
        word_count=word_count,
        character_count=char_count,
    )


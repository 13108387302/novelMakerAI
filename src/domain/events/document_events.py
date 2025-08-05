#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档相关领域事件

定义文档生命周期中的各种事件
"""

from dataclasses import dataclass
from typing import Optional

from src.shared.events.event_bus import Event
from src.domain.entities.document import DocumentStatus, DocumentType


@dataclass
class DocumentCreatedEvent(Event):
    """
    文档创建事件

    当新文档被创建时触发的领域事件。
    包含文档的基本信息，用于通知其他组件文档创建完成。

    Attributes:
        document_id: 文档唯一标识符
        document_title: 文档标题
        document_type: 文档类型
        project_id: 所属项目ID（可选）
    """
    document_id: str = ""
    document_title: str = ""
    document_type: DocumentType = DocumentType.CHAPTER
    project_id: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "document_service"


@dataclass
class DocumentOpenedEvent(Event):
    """
    文档打开事件

    当文档被打开时触发的领域事件。
    用于通知UI组件更新文档状态和加载文档内容。

    Attributes:
        document_id: 文档唯一标识符
        document_title: 文档标题
        project_id: 所属项目ID（可选）
    """
    document_id: str = ""
    document_title: str = ""
    project_id: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "document_service"


@dataclass
class DocumentClosedEvent(Event):
    """
    文档关闭事件

    当文档被关闭时触发的领域事件。
    用于通知组件清理文档相关资源和状态。

    Attributes:
        document_id: 文档唯一标识符
        document_title: 文档标题
    """
    document_id: str = ""
    document_title: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.source = "document_service"


@dataclass
class DocumentSavedEvent(Event):
    """文档保存事件"""
    document_id: str = ""
    document_title: str = ""
    word_count: int = 0
    character_count: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_service"


@dataclass
class DocumentTitleChangedEvent(Event):
    """文档标题变更事件"""
    document_id: str = ""
    old_title: str = ""
    new_title: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentContentChangedEvent(Event):
    """文档内容变更事件"""
    document_id: str = ""
    old_content: str = ""
    new_content: str = ""
    word_count_change: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"
        # 安全计算字数变化
        try:
            old_words = len(self.old_content.split()) if self.old_content else 0
            new_words = len(self.new_content.split()) if self.new_content else 0
            self.word_count_change = new_words - old_words
        except (AttributeError, TypeError):
            self.word_count_change = 0


@dataclass
class DocumentStatusChangedEvent(Event):
    """文档状态变更事件"""
    document_id: str = ""
    old_status: DocumentStatus = DocumentStatus.DRAFT
    new_status: DocumentStatus = DocumentStatus.DRAFT
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentVersionCreatedEvent(Event):
    """文档版本创建事件"""
    document_id: str = ""
    version_id: str = ""
    version_comment: str = ""
    author: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentVersionRestoredEvent(Event):
    """文档版本恢复事件"""
    document_id: str = ""
    version_id: str = ""
    restored_by: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentDeletedEvent(Event):
    """文档删除事件"""
    document_id: str = ""
    document_title: str = ""
    document_type: DocumentType = DocumentType.CHAPTER
    project_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_service"


@dataclass
class DocumentTagAddedEvent(Event):
    """文档标签添加事件"""
    document_id: str = ""
    tag: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentTagRemovedEvent(Event):
    """文档标签移除事件"""
    document_id: str = ""
    tag: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentStatisticsUpdatedEvent(Event):
    """文档统计信息更新事件"""
    document_id: str = ""
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    sentence_count: int = 0
    reading_time_minutes: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "document_entity"


@dataclass
class DocumentExportedEvent(Event):
    """文档导出事件"""
    document_id: str = ""
    export_format: str = ""
    export_path: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "export_service"


@dataclass
class DocumentImportedEvent(Event):
    """文档导入事件"""
    document_id: str = ""
    import_source: str = ""
    import_format: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "import_service"


@dataclass
class DocumentSearchedEvent(Event):
    """文档搜索事件"""
    document_id: str = ""
    search_query: str = ""
    results_count: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "search_service"


@dataclass
class DocumentSpellCheckEvent(Event):
    """文档拼写检查事件"""
    document_id: str = ""
    errors_found: int = 0
    errors_fixed: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "spell_check_service"

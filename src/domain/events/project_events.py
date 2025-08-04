#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目相关领域事件

定义项目生命周期中的各种事件
"""

from dataclasses import dataclass
from typing import Optional

from src.shared.events.event_bus import Event
from src.domain.entities.project import ProjectStatus


@dataclass
class ProjectCreatedEvent(Event):
    """
    项目创建事件

    当新项目被创建时触发的领域事件。
    包含项目的基本信息，用于通知其他组件项目创建完成。

    Attributes:
        project_id: 项目唯一标识符
        project_name: 项目名称
        project_path: 项目路径（可选）
    """
    project_id: str = ""
    project_name: str = ""
    project_path: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "project_service"


@dataclass
class ProjectOpenedEvent(Event):
    """
    项目打开事件

    当项目被打开时触发的领域事件。
    用于通知UI组件更新项目状态和加载项目数据。

    Attributes:
        project_id: 项目唯一标识符
        project_name: 项目名称
        project_path: 项目路径
    """
    project_id: str = ""
    project_name: str = ""
    project_path: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.source = "project_service"


@dataclass
class ProjectClosedEvent(Event):
    """
    项目关闭事件

    当项目被关闭时触发的领域事件。
    用于通知组件清理项目相关资源和状态。

    Attributes:
        project_id: 项目唯一标识符
        project_name: 项目名称
    """
    project_id: str = ""
    project_name: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.source = "project_service"


@dataclass
class ProjectSavedEvent(Event):
    """项目保存事件"""
    project_id: str = ""
    project_name: str = ""
    save_path: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_service"


@dataclass
class ProjectTitleChangedEvent(Event):
    """项目标题变更事件"""
    project_id: str = ""
    old_title: str = ""
    new_title: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_entity"


@dataclass
class ProjectStatusChangedEvent(Event):
    """项目状态变更事件"""
    project_id: str = ""
    old_status: ProjectStatus = ProjectStatus.ACTIVE
    new_status: ProjectStatus = ProjectStatus.ACTIVE
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_entity"


@dataclass
class ProjectStatisticsUpdatedEvent(Event):
    """项目统计信息更新事件"""
    project_id: str = ""
    total_words: int = 0
    total_characters: int = 0
    total_documents: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_entity"


@dataclass
class ProjectDocumentAddedEvent(Event):
    """项目文档添加事件"""
    project_id: str = ""
    document_id: str = ""
    document_title: str = ""
    document_type: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_entity"


@dataclass
class ProjectDocumentRemovedEvent(Event):
    """项目文档移除事件"""
    project_id: str = ""
    document_id: str = ""
    document_title: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_entity"


@dataclass
class ProjectSettingsChangedEvent(Event):
    """项目设置变更事件"""
    project_id: str = ""
    setting_key: str = ""
    old_value: str = ""
    new_value: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "project_entity"


@dataclass
class ProjectBackupCreatedEvent(Event):
    """项目备份创建事件"""
    project_id: str = ""
    backup_path: str = ""
    backup_size: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "backup_service"


@dataclass
class ProjectExportedEvent(Event):
    """项目导出事件"""
    project_id: str = ""
    export_format: str = ""
    export_path: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "export_service"


@dataclass
class ProjectImportedEvent(Event):
    """项目导入事件"""
    project_id: str = ""
    import_source: str = ""
    import_format: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "import_service"

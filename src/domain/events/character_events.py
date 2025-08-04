#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色相关领域事件

定义角色管理中的各种事件
"""

from dataclasses import dataclass
from typing import Optional

from src.shared.events.event_bus import Event
from src.domain.entities.character import CharacterRole, RelationshipType


@dataclass
class CharacterCreatedEvent(Event):
    """角色创建事件"""
    character_id: str = ""
    character_name: str = ""
    character_role: CharacterRole = CharacterRole.SUPPORTING
    project_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_service"


@dataclass
class CharacterDeletedEvent(Event):
    """角色删除事件"""
    character_id: str = ""
    character_name: str = ""
    project_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_service"


@dataclass
class CharacterNameChangedEvent(Event):
    """角色名称变更事件"""
    character_id: str = ""
    old_name: str = ""
    new_name: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterRoleChangedEvent(Event):
    """角色定位变更事件"""
    character_id: str = ""
    old_role: CharacterRole = CharacterRole.SUPPORTING
    new_role: CharacterRole = CharacterRole.SUPPORTING
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterAppearanceUpdatedEvent(Event):
    """角色外貌更新事件"""
    character_id: str = ""
    updated_fields: list = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"
        if self.updated_fields is None:
            self.updated_fields = []
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterPersonalityUpdatedEvent(Event):
    """角色性格更新事件"""
    character_id: str
    trait_category: str
    trait_added: Optional[str] = None
    trait_removed: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterBackgroundUpdatedEvent(Event):
    """角色背景更新事件"""
    character_id: str
    updated_fields: list
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterRelationshipAddedEvent(Event):
    """角色关系添加事件"""
    character_id: str
    target_character_id: str
    relationship_type: RelationshipType
    description: str
    intensity: int
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterRelationshipRemovedEvent(Event):
    """角色关系移除事件"""
    character_id: str
    target_character_id: str
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterRelationshipUpdatedEvent(Event):
    """角色关系更新事件"""
    character_id: str
    target_character_id: str
    old_intensity: int
    new_intensity: int
    old_description: str
    new_description: str
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterAppearanceAddedEvent(Event):
    """角色出场记录添加事件"""
    character_id: str
    document_id: str
    chapter_number: Optional[int] = None
    scene_description: str = ""
    importance: int = 5
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterDevelopmentStageAddedEvent(Event):
    """角色发展阶段添加事件"""
    character_id: str
    stage: str
    description: str
    key_events: list
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterStatisticsUpdatedEvent(Event):
    """角色统计信息更新事件"""
    character_id: str
    total_appearances: int
    total_words_spoken: int
    relationship_network_size: int
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "character_entity"


@dataclass
class CharacterAnalysisRequestedEvent(Event):
    """角色分析请求事件"""
    character_id: str
    analysis_type: str  # personality, development, relationships, etc.
    requested_by: str
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class CharacterAnalysisCompletedEvent(Event):
    """角色分析完成事件"""
    character_id: str
    analysis_type: str
    analysis_result: str
    confidence_score: float
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class CharacterConsistencyCheckEvent(Event):
    """角色一致性检查事件"""
    character_id: str
    inconsistencies_found: list
    suggestions: list
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "validation_service"


@dataclass
class CharacterMentionDetectedEvent(Event):
    """角色提及检测事件"""
    character_id: str
    document_id: str
    mention_context: str
    confidence: float
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "nlp_service"

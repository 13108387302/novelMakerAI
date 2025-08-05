#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档实体 - 重构版本

使用组合模式和配置驱动的方式简化文档类型管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Union
from uuid import uuid4

# 简化验证结果类，避免外部依赖
class ValidationResult:
    """验证结果"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, error: str):
        self.errors.append(error)

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class DocumentType(Enum):
    """
    文档类型枚举

    定义小说创作中的各种文档类型，每种类型都有特定的用途和特征。
    提供类型值和显示名称的映射。

    实现方式：
    - 使用Enum确保类型安全
    - 提供英文值和中文显示名称
    - 支持扩展新的文档类型

    Values:
        CHAPTER: 章节文档，包含小说正文内容
        CHARACTER: 角色档案，记录人物信息
        SETTING: 设定文档，记录世界观设定
        OUTLINE: 大纲文档，记录故事结构
        NOTE: 笔记文档，记录创作想法
        RESEARCH: 资料文档，记录参考资料
        TIMELINE: 时间线文档，记录事件顺序
        WORLDBUILDING: 世界观文档，记录世界构建
    """
    CHAPTER = "chapter"           # 章节
    CHARACTER = "character"       # 角色档案
    SETTING = "setting"          # 设定文档
    OUTLINE = "outline"          # 大纲
    NOTE = "note"                # 笔记
    RESEARCH = "research"        # 资料
    TIMELINE = "timeline"        # 时间线
    WORLDBUILDING = "worldbuilding"  # 世界观

    @property
    def display_name(self) -> str:
        """
        获取文档类型的显示名称

        返回用户友好的中文显示名称。

        Returns:
            str: 文档类型的中文显示名称
        """
        names = {
            self.CHAPTER: "章节",
            self.CHARACTER: "角色档案",
            self.SETTING: "设定文档",
            self.OUTLINE: "大纲",
            self.NOTE: "笔记",
            self.RESEARCH: "资料",
            self.TIMELINE: "时间线",
            self.WORLDBUILDING: "世界观"
        }
        return names.get(self, self.value)


class DocumentStatus(Enum):
    """
    文档状态枚举

    定义文档在创作过程中的不同状态，用于跟踪文档的完成进度。

    Values:
        DRAFT: 草稿状态，初始创建的文档
        IN_PROGRESS: 进行中状态，正在编辑的文档
        REVIEW: 待审阅状态，需要检查的文档
        COMPLETED: 完成状态，已完成的文档
        ARCHIVED: 归档状态，不再使用的文档
    """
    DRAFT = "draft"              # 草稿
    IN_PROGRESS = "in_progress"  # 进行中
    REVIEW = "review"            # 待审阅
    COMPLETED = "completed"      # 已完成
    ARCHIVED = "archived"        # 已归档

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            self.DRAFT: "草稿",
            self.IN_PROGRESS: "进行中",
            self.REVIEW: "待审阅",
            self.COMPLETED: "已完成",
            self.ARCHIVED: "已归档"
        }
        return names.get(self, self.value)


@dataclass
class DocumentMetadata:
    """文档元数据"""
    title: str
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag and tag.strip():
            self.tags.add(tag.strip().lower())
    
    def remove_tag(self, tag: str) -> None:
        """移除标签"""
        self.tags.discard(tag.strip().lower())
    
    def has_tag(self, tag: str) -> bool:
        """检查是否有标签"""
        return tag.strip().lower() in self.tags
    
    def touch(self):
        """更新修改时间"""
        self.updated_at = datetime.now()


@dataclass
class DocumentStatistics:
    """文档统计信息"""
    word_count: int = 0
    character_count: int = 0
    paragraph_count: int = 0
    sentence_count: int = 0
    reading_time_minutes: float = 0.0
    
    def update_from_content(self, content: str):
        """从内容更新统计"""
        self.character_count = len(content)
        self.word_count = len(content.split())
        self.paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        self.sentence_count = len([s for s in content.split('.') if s.strip()])
        # 估算阅读时间（每分钟250字）
        self.reading_time_minutes = self.word_count / 250.0


@dataclass
class DocumentTypeConfig:
    """文档类型配置"""
    document_type: DocumentType
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    default_values: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_fields(self) -> List[str]:
        """获取所有字段"""
        return self.required_fields + self.optional_fields
    
    def is_required_field(self, field_name: str) -> bool:
        """检查是否为必填字段"""
        return field_name in self.required_fields
    
    def get_default_value(self, field_name: str) -> Any:
        """获取默认值"""
        return self.default_values.get(field_name)


class Document:
    """文档实体 - 重构版本"""
    
    # 文档类型配置
    _type_configs: Dict[DocumentType, DocumentTypeConfig] = {}
    
    def __init__(
        self,
        document_id: Optional[str] = None,
        document_type: DocumentType = DocumentType.CHAPTER,
        title: str = "",
        content: str = "",
        project_id: Optional[str] = None,
        **kwargs
    ):
        # 确保类型配置已初始化
        self._init_type_configs()

        self.id = document_id or str(uuid4())
        self.type = document_type
        self.content = content
        self.project_id = project_id

        # 元数据
        self.metadata = DocumentMetadata(title=title or "未命名文档")

        # 统计信息
        self.statistics = DocumentStatistics()
        self.statistics.update_from_content(content)

        # 状态
        self.status = DocumentStatus.DRAFT

        # 类型特定的属性
        self.type_specific_data: Dict[str, Any] = {}

        # 应用类型配置
        self._apply_type_config(**kwargs)
    
    @classmethod
    def _init_type_configs(cls):
        """初始化文档类型配置"""
        if cls._type_configs:
            return
            
        # 章节配置
        cls._type_configs[DocumentType.CHAPTER] = DocumentTypeConfig(
            document_type=DocumentType.CHAPTER,
            optional_fields=["chapter_number", "scene_count", "pov_character"],
            default_values={"chapter_number": None, "scene_count": 1, "pov_character": ""}
        )
        
        # 角色配置
        cls._type_configs[DocumentType.CHARACTER] = DocumentTypeConfig(
            document_type=DocumentType.CHARACTER,
            required_fields=["character_name"],
            optional_fields=["age", "gender", "occupation", "personality_traits", "relationships"],
            default_values={
                "character_name": "",
                "age": None,
                "gender": "",
                "occupation": "",
                "personality_traits": [],
                "relationships": {}
            }
        )
        
        # 设定配置
        cls._type_configs[DocumentType.SETTING] = DocumentTypeConfig(
            document_type=DocumentType.SETTING,
            optional_fields=["setting_category", "location", "time_period", "rules"],
            default_values={
                "setting_category": "",
                "location": "",
                "time_period": "",
                "rules": []
            }
        )
        
        # 大纲配置
        cls._type_configs[DocumentType.OUTLINE] = DocumentTypeConfig(
            document_type=DocumentType.OUTLINE,
            optional_fields=["outline_level", "structure_type", "plot_points"],
            default_values={
                "outline_level": 1,
                "structure_type": "三幕式",
                "plot_points": []
            }
        )
        
        # 其他类型使用默认配置
        for doc_type in DocumentType:
            if doc_type not in cls._type_configs:
                cls._type_configs[doc_type] = DocumentTypeConfig(document_type=doc_type)
    
    def _apply_type_config(self, **kwargs):
        """应用类型配置"""
        self._init_type_configs()
        
        config = self._type_configs.get(self.type)
        if not config:
            return
        
        # 设置默认值
        for field, default_value in config.default_values.items():
            self.type_specific_data[field] = kwargs.get(field, default_value)
        
        # 设置其他传入的值
        for field in config.get_all_fields():
            if field in kwargs:
                self.type_specific_data[field] = kwargs[field]
    
    def get_type_specific_field(self, field_name: str, default=None):
        """获取类型特定字段"""
        return self.type_specific_data.get(field_name, default)
    
    def set_type_specific_field(self, field_name: str, value: Any):
        """设置类型特定字段"""
        self.type_specific_data[field_name] = value
        self.metadata.touch()
    
    def update_content(self, new_content: str):
        """更新内容"""
        if new_content is None:
            new_content = ""
        self.content = new_content
        self.statistics.update_from_content(new_content)
        self.metadata.touch()

    def change_status(self, new_status: DocumentStatus):
        """更改状态"""
        if not isinstance(new_status, DocumentStatus):
            raise ValueError("状态必须是DocumentStatus枚举")
        self.status = new_status
        self.metadata.touch()
    
    def validate(self) -> ValidationResult:
        """验证文档"""
        result = ValidationResult()
        
        # 基础验证
        if not self.metadata.title.strip():
            result.add_error("文档标题不能为空")
        
        if len(self.metadata.title) > 200:
            result.add_error("文档标题过长（最多200字符）")
        
        if len(self.content) > 1000000:  # 100万字符
            result.add_error("文档内容过长（最多100万字符）")
        
        # 类型特定验证
        config = self._type_configs.get(self.type)
        if config:
            for field in config.required_fields:
                value = self.get_type_specific_field(field)
                if not value:
                    result.add_error(f"必填字段 {field} 不能为空")
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "project_id": self.project_id,
            "metadata": {
                "title": self.metadata.title,
                "description": self.metadata.description,
                "tags": list(self.metadata.tags),
                "author": self.metadata.author,
                "created_at": self.metadata.created_at.isoformat(),
                "updated_at": self.metadata.updated_at.isoformat()
            },
            "statistics": {
                "word_count": self.statistics.word_count,
                "character_count": self.statistics.character_count,
                "paragraph_count": self.statistics.paragraph_count,
                "sentence_count": self.statistics.sentence_count,
                "reading_time_minutes": self.statistics.reading_time_minutes
            },
            "status": self.status.value,
            "type_specific_data": self.type_specific_data.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """从字典创建文档"""
        if not isinstance(data, dict):
            raise ValueError("数据必须是字典类型")

        # 安全获取文档类型
        try:
            doc_type = DocumentType(data.get("type", DocumentType.CHAPTER.value))
        except ValueError:
            doc_type = DocumentType.CHAPTER

        # 安全获取元数据
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        # 基础信息
        doc = cls(
            document_id=data.get("id"),
            document_type=doc_type,
            title=metadata.get("title", ""),
            content=data.get("content", ""),
            project_id=data.get("project_id")
        )
        
        # 元数据
        metadata = data.get("metadata", {})
        doc.metadata.description = metadata.get("description", "")
        doc.metadata.tags = set(metadata.get("tags", []))
        doc.metadata.author = metadata.get("author", "")
        
        if metadata.get("created_at"):
            try:
                doc.metadata.created_at = datetime.fromisoformat(metadata["created_at"])
            except (ValueError, TypeError):
                pass
        
        if metadata.get("updated_at"):
            try:
                doc.metadata.updated_at = datetime.fromisoformat(metadata["updated_at"])
            except (ValueError, TypeError):
                pass
        
        # 统计信息
        statistics = data.get("statistics", {})
        if isinstance(statistics, dict):
            doc.statistics.word_count = max(0, statistics.get("word_count", 0))
            doc.statistics.character_count = max(0, statistics.get("character_count", 0))
            doc.statistics.paragraph_count = max(0, statistics.get("paragraph_count", 0))
            doc.statistics.sentence_count = max(0, statistics.get("sentence_count", 0))
            doc.statistics.reading_time_minutes = max(0.0, statistics.get("reading_time_minutes", 0.0))

        # 状态
        try:
            doc.status = DocumentStatus(data.get("status", DocumentStatus.DRAFT.value))
        except ValueError:
            doc.status = DocumentStatus.DRAFT

        # 类型特定数据
        type_specific_data = data.get("type_specific_data", {})
        if isinstance(type_specific_data, dict):
            doc.type_specific_data = type_specific_data.copy()
        else:
            doc.type_specific_data = {}
        
        return doc
    
    def copy(self) -> 'Document':
        """创建副本"""
        data = self.to_dict()
        data["id"] = str(uuid4())
        data["metadata"]["title"] = f"{self.metadata.title} - 副本"
        data["metadata"]["created_at"] = datetime.now().isoformat()
        data["metadata"]["updated_at"] = datetime.now().isoformat()
        return Document.from_dict(data)
    
    # 便捷属性（向后兼容）
    @property
    def title(self) -> str:
        return self.metadata.title
    
    @title.setter
    def title(self, value: str):
        self.metadata.title = value
        self.metadata.touch()
    
    @property
    def word_count(self) -> int:
        return self.statistics.word_count
    
    def __str__(self) -> str:
        return f"Document(id={self.id[:8]}..., type={self.type.display_name}, title='{self.title}')"
    
    def __repr__(self) -> str:
        return f"Document(id='{self.id}', type={self.type.value}, title='{self.title}')"


# 便捷函数
def create_document(
    document_type: DocumentType,
    title: str = "",
    content: str = "",
    project_id: Optional[str] = None,
    **kwargs
) -> Document:
    """创建文档"""
    return Document(
        document_type=document_type,
        title=title,
        content=content,
        project_id=project_id,
        **kwargs
    )

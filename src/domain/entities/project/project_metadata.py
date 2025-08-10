#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目元数据

定义项目的元数据信息
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Set, Dict, Any, Optional
from .project_types import ProjectType, ProjectLanguage, ProjectPriority, ProjectVisibility


@dataclass
class ProjectMetadata:
    """项目元数据"""
    title: str
    author: str = ""
    genre: str = ""
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    target_word_count: int = 80000
    language: ProjectLanguage = ProjectLanguage.ZH_CN
    copyright_info: str = ""
    priority: ProjectPriority = ProjectPriority.NORMAL
    visibility: ProjectVisibility = ProjectVisibility.PRIVATE
    
    # 扩展元数据
    keywords: Set[str] = field(default_factory=set)
    themes: Set[str] = field(default_factory=set)
    target_audience: str = ""
    content_rating: str = ""  # 内容分级
    series_info: Optional[str] = None  # 系列信息
    inspiration_sources: Set[str] = field(default_factory=set)
    
    # 发布相关
    publication_status: str = "unpublished"  # 发布状态
    publisher: str = ""
    publication_date: Optional[datetime] = None
    isbn: str = ""
    
    # 自定义字段
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag and tag.strip():
            self.tags.add(tag.strip().lower())
    
    def remove_tag(self, tag: str) -> None:
        """移除标签"""
        self.tags.discard(tag.strip().lower())
    
    def has_tag(self, tag: str) -> bool:
        """检查是否有指定标签"""
        return tag.strip().lower() in self.tags
    
    def add_keyword(self, keyword: str) -> None:
        """添加关键词"""
        if keyword and keyword.strip():
            self.keywords.add(keyword.strip().lower())
    
    def remove_keyword(self, keyword: str) -> None:
        """移除关键词"""
        self.keywords.discard(keyword.strip().lower())
    
    def add_theme(self, theme: str) -> None:
        """添加主题"""
        if theme and theme.strip():
            self.themes.add(theme.strip().lower())
    
    def remove_theme(self, theme: str) -> None:
        """移除主题"""
        self.themes.discard(theme.strip().lower())
    
    def add_inspiration_source(self, source: str) -> None:
        """添加灵感来源"""
        if source and source.strip():
            self.inspiration_sources.add(source.strip())
    
    def remove_inspiration_source(self, source: str) -> None:
        """移除灵感来源"""
        self.inspiration_sources.discard(source.strip())
    
    def set_custom_field(self, key: str, value: Any) -> None:
        """设置自定义字段"""
        if key and key.strip():
            self.custom_fields[key.strip()] = value
    
    def get_custom_field(self, key: str, default: Any = None) -> Any:
        """获取自定义字段"""
        return self.custom_fields.get(key.strip(), default)
    
    def remove_custom_field(self, key: str) -> None:
        """移除自定义字段"""
        self.custom_fields.pop(key.strip(), None)
    
    def update_target_word_count_by_type(self, project_type: ProjectType) -> None:
        """根据项目类型更新目标字数"""
        self.target_word_count = project_type.default_target_word_count
    
    def get_all_searchable_text(self) -> str:
        """获取所有可搜索的文本"""
        searchable_parts = [
            self.title,
            self.author,
            self.genre,
            self.description,
            self.copyright_info,
            self.target_audience,
            self.content_rating,
            self.series_info or "",
            self.publisher,
            self.isbn,
            " ".join(self.tags),
            " ".join(self.keywords),
            " ".join(self.themes),
            " ".join(self.inspiration_sources)
        ]
        return " ".join(filter(None, searchable_parts)).lower()
    
    def validate(self) -> list[str]:
        """验证元数据"""
        errors = []
        
        # 必填字段验证
        if not self.title or not self.title.strip():
            errors.append("项目标题不能为空")
        
        # 字数验证
        if self.target_word_count < 0:
            errors.append("目标字数不能为负数")
        elif self.target_word_count > 10000000:  # 1000万字
            errors.append("目标字数过大")
        
        # 标题长度验证
        if len(self.title) > 200:
            errors.append("项目标题过长（最多200字符）")
        
        # 描述长度验证
        if len(self.description) > 5000:
            errors.append("项目描述过长（最多5000字符）")
        
        # 作者名长度验证
        if len(self.author) > 100:
            errors.append("作者名过长（最多100字符）")
        
        # 标签数量验证
        if len(self.tags) > 50:
            errors.append("标签数量过多（最多50个）")
        
        # 关键词数量验证
        if len(self.keywords) > 100:
            errors.append("关键词数量过多（最多100个）")
        
        # ISBN格式验证（简单验证）
        if self.isbn and not self._is_valid_isbn(self.isbn):
            errors.append("ISBN格式无效")
        
        return errors
    
    def _is_valid_isbn(self, isbn: str) -> bool:
        """简单的ISBN格式验证"""
        # 移除连字符和空格
        clean_isbn = isbn.replace("-", "").replace(" ", "")
        
        # ISBN-10 或 ISBN-13
        if len(clean_isbn) == 10:
            return clean_isbn[:-1].isdigit() and (clean_isbn[-1].isdigit() or clean_isbn[-1].upper() == 'X')
        elif len(clean_isbn) == 13:
            return clean_isbn.isdigit()
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "description": self.description,
            "tags": list(self.tags),
            "target_word_count": self.target_word_count,
            "language": self.language.value,
            "copyright_info": self.copyright_info,
            "priority": self.priority.value,
            "visibility": self.visibility.value,
            "keywords": list(self.keywords),
            "themes": list(self.themes),
            "target_audience": self.target_audience,
            "content_rating": self.content_rating,
            "series_info": self.series_info,
            "inspiration_sources": list(self.inspiration_sources),
            "publication_status": self.publication_status,
            "publisher": self.publisher,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "isbn": self.isbn,
            "custom_fields": self.custom_fields.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectMetadata':
        """从字典创建元数据"""
        # 处理枚举类型（兼容大小写与直接枚举值）
        lang_val = data.get("language", ProjectLanguage.ZH_CN.value)
        if isinstance(lang_val, ProjectLanguage):
            language = lang_val
        else:
            try:
                language = ProjectLanguage(lang_val)
            except Exception:
                # 兼容传入中文或大小写不同的值
                normalized = str(lang_val).strip()
                mapping = {
                    "zh_cn": ProjectLanguage.ZH_CN,
                    "zh_cn": ProjectLanguage.ZH_CN,
                    "zh-CN": ProjectLanguage.ZH_CN,
                    "中文": ProjectLanguage.ZH_CN,
                }
                language = mapping.get(normalized, ProjectLanguage.ZH_CN)

        prio_val = data.get("priority", ProjectPriority.NORMAL.value)
        if isinstance(prio_val, ProjectPriority):
            priority = prio_val
        else:
            try:
                priority = ProjectPriority(prio_val)
            except Exception:
                normalized = str(prio_val).strip().lower()
                prio_map = {
                    "low": ProjectPriority.LOW,
                    "normal": ProjectPriority.NORMAL,
                    "high": ProjectPriority.HIGH,
                    "urgent": ProjectPriority.URGENT,
                    "低": ProjectPriority.LOW,
                    "普通": ProjectPriority.NORMAL,
                    "高": ProjectPriority.HIGH,
                    "紧急": ProjectPriority.URGENT,
                }
                priority = prio_map.get(normalized, ProjectPriority.NORMAL)

        vis_val = data.get("visibility", ProjectVisibility.PRIVATE.value)
        if isinstance(vis_val, ProjectVisibility):
            visibility = vis_val
        else:
            try:
                visibility = ProjectVisibility(vis_val)
            except Exception:
                normalized = str(vis_val).strip().lower()
                vis_map = {
                    "private": ProjectVisibility.PRIVATE,
                    "shared": ProjectVisibility.SHARED,
                    "public": ProjectVisibility.PUBLIC,
                    "私有": ProjectVisibility.PRIVATE,
                    "共享": ProjectVisibility.SHARED,
                    "公开": ProjectVisibility.PUBLIC,
                }
                visibility = vis_map.get(normalized, ProjectVisibility.PRIVATE)
        
        # 处理日期
        publication_date = None
        if data.get("publication_date"):
            try:
                publication_date = datetime.fromisoformat(data["publication_date"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            title=data.get("title", ""),
            author=data.get("author", ""),
            genre=data.get("genre", ""),
            description=data.get("description", ""),
            tags=set(data.get("tags", [])),
            target_word_count=data.get("target_word_count", 80000),
            language=language,
            copyright_info=data.get("copyright_info", ""),
            priority=priority,
            visibility=visibility,
            keywords=set(data.get("keywords", [])),
            themes=set(data.get("themes", [])),
            target_audience=data.get("target_audience", ""),
            content_rating=data.get("content_rating", ""),
            series_info=data.get("series_info"),
            inspiration_sources=set(data.get("inspiration_sources", [])),
            publication_status=data.get("publication_status", "unpublished"),
            publisher=data.get("publisher", ""),
            publication_date=publication_date,
            isbn=data.get("isbn", ""),
            custom_fields=data.get("custom_fields", {}).copy()
        )
    
    def copy(self) -> 'ProjectMetadata':
        """创建副本"""
        return ProjectMetadata.from_dict(self.to_dict())
    
    def merge_with(self, other: 'ProjectMetadata', prefer_other: bool = True) -> 'ProjectMetadata':
        """与另一个元数据合并"""
        if prefer_other:
            # 优先使用other的值
            merged = other.copy()
            # 合并集合类型的字段
            merged.tags.update(self.tags)
            merged.keywords.update(self.keywords)
            merged.themes.update(self.themes)
            merged.inspiration_sources.update(self.inspiration_sources)
            merged.custom_fields.update(self.custom_fields)
        else:
            # 优先使用self的值
            merged = self.copy()
            # 合并集合类型的字段
            merged.tags.update(other.tags)
            merged.keywords.update(other.keywords)
            merged.themes.update(other.themes)
            merged.inspiration_sources.update(other.inspiration_sources)
            merged.custom_fields.update(other.custom_fields)
        
        return merged

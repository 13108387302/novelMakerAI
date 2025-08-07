#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目实体 - 重构版本

使用组件化架构的项目实体
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid

from .project_types import ProjectStatus, ProjectType, can_transition_status
from .project_metadata import ProjectMetadata
from .project_settings import ProjectSettings
from .project_statistics import ProjectStatistics
from src.shared.constants import (
    DEFAULT_TREND_DAYS, DEFAULT_PROJECT_VERSION, DEFAULT_FORMAT_VERSION, COPY_SUFFIX
)


@dataclass
class Project:
    """
    项目实体 - 重构版本

    表示一个小说创作项目的核心实体，使用组件化架构设计。
    包含项目的基本信息、元数据、设置和统计信息。

    实现方式：
    - 使用dataclass简化数据类定义
    - 采用组合模式整合不同功能组件
    - 提供状态转换和验证方法
    - 支持项目的完整生命周期管理
    - 包含版本控制和兼容性信息

    Attributes:
        id: 项目唯一标识符，自动生成UUID
        name: 项目名称
        project_type: 项目类型（小说、短篇等）
        status: 项目状态（草稿、进行中、完成等）
        root_path: 项目根目录路径
        created_at: 创建时间
        updated_at: 最后更新时间
        last_opened_at: 最后打开时间
        metadata: 项目元数据组件
        settings: 项目设置组件
        statistics: 项目统计信息组件
        version: 项目版本号
        format_version: 项目格式版本，用于兼容性检查
    """

    # 基础信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    project_type: ProjectType = ProjectType.NOVEL
    status: ProjectStatus = ProjectStatus.DRAFT

    # 路径信息
    root_path: Optional[Path] = None

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_opened_at: Optional[datetime] = None

    # 组件
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    statistics: ProjectStatistics = field(default_factory=ProjectStatistics)

    # 版本信息
    version: str = "1.0.0"
    format_version: str = "2.0"  # 项目格式版本
    
    def __post_init__(self):
        """
        初始化后处理

        在dataclass初始化完成后执行的后处理逻辑。
        确保项目名称和元数据的一致性，设置合适的默认值。

        实现方式：
        - 同步项目名称和元数据标题
        - 根据项目类型设置合适的目标字数
        - 确保数据的一致性和完整性
        """
        # 确保元数据标题与项目名称同步
        if not self.metadata.title and self.name:
            self.metadata.title = self.name
        elif not self.name and self.metadata.title:
            self.name = self.metadata.title

        # 根据项目类型设置默认目标字数
        if self.metadata.target_word_count == 80000:  # 默认值
            self.metadata.update_target_word_count_by_type(self.project_type)

    @property
    def title(self) -> str:
        """
        项目标题（兼容性属性）

        提供与旧版本兼容的title属性，实际返回name字段的值。

        Returns:
            str: 项目标题
        """
        return self.name

    @title.setter
    def title(self, value: str):
        """
        设置项目标题

        同时更新项目名称和元数据标题，确保数据一致性。

        Args:
            value: 新的项目标题
        """
        self.name = value
        self.metadata.title = value
        self.touch()

    @property
    def path(self) -> Optional[str]:
        """
        项目路径（兼容性属性）

        提供与旧版本兼容的path属性，返回root_path的字符串表示。

        Returns:
            Optional[str]: 项目路径字符串，如果未设置则返回None
        """
        return str(self.root_path) if self.root_path else None

    @path.setter
    def path(self, value: Optional[str]):
        """
        设置项目路径

        将字符串路径转换为Path对象并更新root_path字段。

        Args:
            value: 新的项目路径字符串，None表示清除路径
        """
        self.root_path = Path(value) if value else None
        self.touch()
    
    @property
    def description(self) -> str:
        """项目描述（兼容性属性）"""
        return self.metadata.description
    
    @description.setter
    def description(self, value: str):
        """设置项目描述"""
        self.metadata.description = value
        self.touch()
    
    @property
    def author(self) -> str:
        """作者（兼容性属性）"""
        return self.metadata.author
    
    @author.setter
    def author(self, value: str):
        """设置作者"""
        self.metadata.author = value
        self.touch()
    
    @property
    def word_count(self) -> int:
        """字数（兼容性属性）"""
        return self.statistics.total_words
    
    @property
    def target_word_count(self) -> int:
        """目标字数（兼容性属性）"""
        return self.metadata.target_word_count
    
    @target_word_count.setter
    def target_word_count(self, value: int):
        """设置目标字数"""
        self.metadata.target_word_count = value
        self.touch()
    
    def touch(self):
        """更新修改时间"""
        self.updated_at = datetime.now()
    
    def open(self):
        """标记项目为已打开"""
        self.last_opened_at = datetime.now()
        self.touch()
    
    def change_status(self, new_status: ProjectStatus) -> bool:
        """更改项目状态"""
        if not isinstance(new_status, ProjectStatus):
            raise ValueError("状态必须是ProjectStatus枚举")

        if can_transition_status(self.status, new_status):
            old_status = self.status
            self.status = new_status
            self.touch()

            # 记录状态变更里程碑
            try:
                milestone_name = f"状态变更: {old_status.display_name} -> {new_status.display_name}"
                self.statistics.add_milestone(milestone_name)
            except Exception:
                # 里程碑记录失败不应影响状态变更
                pass

            return True
        return False
    
    def update_word_count(self, word_count: int, character_count: int = None):
        """更新字数统计"""
        if not isinstance(word_count, int) or word_count < 0:
            raise ValueError("字数必须是非负整数")

        if character_count is not None and (not isinstance(character_count, int) or character_count < 0):
            raise ValueError("字符数必须是非负整数")

        if character_count is None:
            character_count = word_count * 2  # 估算字符数

        self.statistics.update_word_count(word_count, character_count)
        self.touch()

        # 检查里程碑
        try:
            self._check_word_count_milestones(word_count)
        except Exception:
            # 里程碑检查失败不应影响字数更新
            pass
    
    def _check_word_count_milestones(self, word_count: int):
        """检查字数里程碑"""
        for milestone in WORD_COUNT_MILESTONES:
            milestone_name = f"{milestone}字"
            if (word_count >= milestone and 
                not self.statistics.get_milestone(milestone_name)):
                self.statistics.add_milestone(milestone_name)
    
    def add_writing_session(self, duration_minutes: float, words_written: int = 0):
        """添加写作会话"""
        self.statistics.add_writing_session(duration_minutes, words_written)
        self.touch()
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.metadata.target_word_count <= 0:
            return 0.0
        return min(100.0, (self.statistics.total_words / self.metadata.target_word_count) * 100)
    
    def is_completed(self) -> bool:
        """检查项目是否完成"""
        return (self.status == ProjectStatus.COMPLETED or 
                self.statistics.total_words >= self.metadata.target_word_count)
    
    def get_estimated_completion_date(self) -> Optional[datetime]:
        """估算完成日期"""
        if self.is_completed():
            return None
        
        remaining_words = max(0, self.metadata.target_word_count - self.statistics.total_words)
        if remaining_words == 0:
            return datetime.now()
        
        # 基于最近的写作速度估算
        recent_daily_average = self._get_recent_daily_average()
        if recent_daily_average <= 0:
            return None
        
        days_needed = remaining_words / recent_daily_average
        return datetime.now() + datetime.timedelta(days=days_needed)
    
    def _get_recent_daily_average(self, days: int = DEFAULT_TREND_DAYS) -> float:
        """获取最近几天的日均字数"""
        trend = self.statistics.get_productivity_trend(days)
        if not trend:
            return 0.0
        
        total_words = sum(words for _, words in trend)
        return total_words / len(trend)
    
    def validate(self) -> List[str]:
        """验证项目数据"""
        errors = []
        
        # 基础验证
        if not self.name or not self.name.strip():
            errors.append("项目名称不能为空")
        
        if len(self.name) > 200:  # 使用硬编码值，因为constants中没有定义
            errors.append("项目名称过长")
        
        # 验证组件
        errors.extend(self.metadata.validate())
        errors.extend(self.settings.validate())
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "project_type": self.project_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_opened_at": self.last_opened_at.isoformat() if self.last_opened_at else None,
            "metadata": self.metadata.to_dict(),
            "settings": self.settings.to_dict(),
            "statistics": self.statistics.to_dict(),
            "version": self.version,
            "format_version": self.format_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """从字典创建项目"""
        if not isinstance(data, dict):
            raise ValueError("数据必须是字典类型")

        # 安全处理枚举类型
        try:
            project_type = ProjectType(data.get("project_type", ProjectType.NOVEL.value))
        except ValueError:
            project_type = ProjectType.NOVEL

        try:
            status = ProjectStatus(data.get("status", ProjectStatus.DRAFT.value))
        except ValueError:
            status = ProjectStatus.DRAFT

        # 安全处理时间戳
        created_at = datetime.now()
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass

        updated_at = datetime.now()
        if data.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass

        last_opened_at = None
        if data.get("last_opened_at"):
            try:
                last_opened_at = datetime.fromisoformat(data["last_opened_at"])
            except (ValueError, TypeError):
                pass

        # 安全处理组件
        try:
            metadata = ProjectMetadata.from_dict(data.get("metadata", {}))
        except Exception:
            metadata = ProjectMetadata()

        try:
            settings = ProjectSettings.from_dict(data.get("settings", {}))
        except Exception:
            settings = ProjectSettings()

        try:
            statistics = ProjectStatistics.from_dict(data.get("statistics", {}))
        except Exception:
            statistics = ProjectStatistics()
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            project_type=project_type,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            last_opened_at=last_opened_at,
            metadata=metadata,
            settings=settings,
            statistics=statistics,
            version=data.get("version", DEFAULT_PROJECT_VERSION),
            format_version=data.get("format_version", DEFAULT_FORMAT_VERSION)
        )
    
    def copy(self) -> 'Project':
        """创建项目副本"""
        data = self.to_dict()
        data["id"] = str(uuid.uuid4())  # 新的ID
        data["name"] = f"{self.name}{COPY_SUFFIX}"
        data["created_at"] = datetime.now().isoformat()
        data["updated_at"] = datetime.now().isoformat()
        data["last_opened_at"] = None
        return Project.from_dict(data)
    
    def __str__(self) -> str:
        return f"Project(id={self.id[:8]}..., name='{self.name}', status={self.status.display_name})"
    
    def __repr__(self) -> str:
        return (f"Project(id='{self.id}', name='{self.name}', "
                f"type={self.project_type.value}, status={self.status.value})")


# 便捷函数
def create_project(
    name: str,
    project_type: ProjectType = ProjectType.NOVEL,
    author: str = "",
    description: str = "",
    target_word_count: Optional[int] = None
) -> Project:
    """创建新项目"""
    project = Project(name=name, project_type=project_type)
    
    # 设置元数据
    project.metadata.title = name
    project.metadata.author = author
    project.metadata.description = description
    
    if target_word_count is not None:
        project.metadata.target_word_count = target_word_count
    else:
        project.metadata.update_target_word_count_by_type(project_type)
    
    return project

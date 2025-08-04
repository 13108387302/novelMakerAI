#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目实体模块

提供模块化的项目实体组件
"""

from .project_types import (
    ProjectStatus,
    ProjectType,
    ProjectPriority,
    ProjectVisibility,
    ProjectLanguage,
    FICTION_TYPES,
    NON_FICTION_TYPES,
    CREATIVE_TYPES,
    VALID_STATUS_TRANSITIONS,
    can_transition_status,
    get_next_valid_statuses
)

# 导入主项目类
from .project import Project, create_project

from .project_metadata import ProjectMetadata
from .project_settings import ProjectSettings
from .project_statistics import (
    ProjectStatistics,
    WritingSession,
    DailyStatistics
)

__all__ = [
    # 主项目类
    'Project',
    'create_project',

    # 类型和枚举
    'ProjectStatus',
    'ProjectType',
    'ProjectPriority',
    'ProjectVisibility',
    'ProjectLanguage',
    'FICTION_TYPES',
    'NON_FICTION_TYPES',
    'CREATIVE_TYPES',
    'VALID_STATUS_TRANSITIONS',
    'can_transition_status',
    'get_next_valid_statuses',

    # 组件类
    'ProjectMetadata',
    'ProjectSettings',
    'ProjectStatistics',
    'WritingSession',
    'DailyStatistics'
]

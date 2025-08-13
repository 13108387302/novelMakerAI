#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目事件构造辅助函数

统一由项目实体构造标准领域事件，减少重复代码。
"""
from typing import Optional
from pathlib import Path

from src.domain.entities.project import Project
from src.domain.events.project_events import (
    ProjectCreatedEvent,
    ProjectOpenedEvent,
    ProjectClosedEvent,
    ProjectSavedEvent,
)


def build_project_created_event(project: Project) -> ProjectCreatedEvent:
    return ProjectCreatedEvent(
        project_id=getattr(project, "id", "") or "",
        project_name=getattr(project, "title", "") or "",
        project_path=str(getattr(project, "root_path", "")) or None,
    )


def build_project_opened_event(project: Project) -> ProjectOpenedEvent:
    return ProjectOpenedEvent(
        project_id=getattr(project, "id", "") or "",
        project_name=getattr(project, "title", "") or "",
        project_path=str(getattr(project, "root_path", "") or ""),
    )


def build_project_closed_event(project: Project) -> ProjectClosedEvent:
    return ProjectClosedEvent(
        project_id=getattr(project, "id", "") or "",
        project_name=getattr(project, "title", "") or "",
    )


def build_project_saved_event(project: Project, save_path: Optional[Path] = None) -> ProjectSavedEvent:
    # 优先使用实体的 root_path；允许调用方覆盖保存路径
    if save_path is None:
        try:
            rp = getattr(project, "root_path", None)
            save_path = rp if rp else None
        except Exception:
            save_path = None
    return ProjectSavedEvent(
        project_id=getattr(project, "id", "") or "",
        project_name=getattr(project, "title", "") or "",
        save_path=str(save_path or ""),
    )


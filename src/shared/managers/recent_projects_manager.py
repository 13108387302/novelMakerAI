#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最近项目管理器

管理最近打开的项目列表，提供持久化存储功能。
注意：这是应用级配置，不依赖特定项目上下文。
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


# 应用级配置目录定位（跨平台）
def _get_app_config_dir() -> Path:
    import os
    from platform import system
    home = Path.home()
    sys_name = system()
    try:
        if sys_name == "Windows":
            base = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
            return base / "AI_Novel_Editor"
        elif sys_name == "Darwin":
            # macOS 应用支持目录
            return home / "Library" / "Application Support" / "AI Novel Editor"
        else:
            # Linux/XDG
            base = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config")))
            return base / "ai-novel-editor"
    except Exception:
        # 兜底：使用用户主目录下隐藏目录
        return home / ".ai_novel_editor_app"

def _get_legacy_app_config_dir() -> Path:
    # 旧位置：当前工作目录下 .ai_novel_editor_app
    return Path.cwd() / ".ai_novel_editor_app"


class RecentProjectsManager:
    """最近项目管理器"""

    def __init__(self, config_file: Optional[Path] = None):
        """
        初始化最近项目管理器

        Args:
            config_file: 配置文件路径，如果为None则使用默认位置
        """
        # 使用应用级配置文件（不依赖项目上下文）
        if config_file is None:
            # 使用用户级应用配置目录（迁移旧位置）
            new_dir = _get_app_config_dir()
            legacy_dir = _get_legacy_app_config_dir()
            new_dir.mkdir(parents=True, exist_ok=True)

            self.config_file = new_dir / "recent_projects.json"

            # 迁移旧文件（仅首次）
            legacy_file = legacy_dir / "recent_projects.json"
            if legacy_file.exists() and not self.config_file.exists():
                try:
                    import shutil
                    shutil.move(str(legacy_file), str(self.config_file))
                    logger.info(f"已迁移最近项目文件到用户目录: {self.config_file}")
                    # 尝试清理旧空目录
                    try:
                        if not any(legacy_dir.iterdir()):
                            legacy_dir.rmdir()
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning(f"迁移最近项目文件失败，继续使用新位置: {e}")
        else:
            self.config_file = config_file

        self.max_projects = 10
        self._recent_projects: List[Dict[str, Any]] = []

        self._load_recent_projects()

    def _load_recent_projects(self):
        """从文件加载最近项目列表"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._recent_projects = data.get('recent_projects', [])

                # 验证和清理无效项目
                self._validate_and_clean_projects()
                logger.debug(f"加载了 {len(self._recent_projects)} 个最近项目")
            else:
                self._recent_projects = []
                logger.debug("最近项目文件不存在，使用空列表")

        except Exception as e:
            logger.error(f"加载最近项目失败: {e}")
            self._recent_projects = []

    def _save_recent_projects(self):
        """保存最近项目列表到文件"""
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'recent_projects': self._recent_projects,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"保存了 {len(self._recent_projects)} 个最近项目")

        except Exception as e:
            logger.error(f"保存最近项目失败: {e}")

    def _validate_and_clean_projects(self):
        """验证和清理无效的项目路径"""
        valid_projects = []

        for project in self._recent_projects:
            try:
                project_path = Path(project['path'])
                if project_path.exists() and project_path.is_dir():
                    valid_projects.append(project)
                else:
                    logger.debug(f"移除无效项目路径: {project['path']}")
            except Exception as e:
                logger.debug(f"验证项目路径失败: {e}")

        if len(valid_projects) != len(self._recent_projects):
            self._recent_projects = valid_projects
            self._save_recent_projects()

    def add_project(self, project_path: Path, project_name: Optional[str] = None):
        """
        添加项目到最近项目列表

        Args:
            project_path: 项目路径
            project_name: 项目名称，如果为None则使用文件夹名称
        """
        try:
            project_path = Path(project_path).resolve()
            project_path_str = str(project_path)

            # 如果项目已存在，先移除
            self._recent_projects = [p for p in self._recent_projects if p['path'] != project_path_str]

            # 获取项目名称
            if project_name is None:
                project_name = project_path.name

            # 添加到列表开头
            project_info = {
                'path': project_path_str,
                'name': project_name,
                'last_opened': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'added_time': datetime.now().isoformat()
            }

            self._recent_projects.insert(0, project_info)

            # 限制列表长度
            if len(self._recent_projects) > self.max_projects:
                self._recent_projects = self._recent_projects[:self.max_projects]

            # 保存到文件
            self._save_recent_projects()

            logger.info(f"添加最近项目: {project_name} ({project_path_str})")

        except Exception as e:
            logger.error(f"添加最近项目失败: {e}")

    def remove_project(self, project_path: str):
        """
        从最近项目列表中移除项目

        Args:
            project_path: 要移除的项目路径
        """
        try:
            original_count = len(self._recent_projects)
            self._recent_projects = [p for p in self._recent_projects if p['path'] != project_path]

            if len(self._recent_projects) < original_count:
                self._save_recent_projects()
                logger.info(f"移除最近项目: {project_path}")

        except Exception as e:
            logger.error(f"移除最近项目失败: {e}")

    def get_recent_projects(self) -> List[Dict[str, Any]]:
        """
        获取最近项目列表

        Returns:
            List[Dict[str, Any]]: 最近项目列表
        """
        # 每次获取时都验证一下项目是否仍然存在
        self._validate_and_clean_projects()
        return self._recent_projects.copy()

    def clear_recent_projects(self):
        """清空最近项目列表"""
        try:
            self._recent_projects = []
            self._save_recent_projects()
            logger.info("清空最近项目列表")

        except Exception as e:
            logger.error(f"清空最近项目失败: {e}")

    def get_project_info(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        获取指定项目的信息

        Args:
            project_path: 项目路径

        Returns:
            Optional[Dict[str, Any]]: 项目信息，如果不存在则返回None
        """
        for project in self._recent_projects:
            if project['path'] == project_path:
                return project.copy()
        return None

    def update_project_access_time(self, project_path: str):
        """
        更新项目的最后访问时间

        Args:
            project_path: 项目路径
        """
        try:
            for project in self._recent_projects:
                if project['path'] == project_path:
                    project['last_opened'] = datetime.now().strftime('%Y-%m-%d %H:%M')

                    # 移动到列表开头
                    self._recent_projects.remove(project)
                    self._recent_projects.insert(0, project)

                    self._save_recent_projects()
                    logger.debug(f"更新项目访问时间: {project_path}")
                    break

        except Exception as e:
            logger.error(f"更新项目访问时间失败: {e}")


# 全局实例（应用级，不依赖项目上下文）
_recent_projects_manager: Optional[RecentProjectsManager] = None


def get_recent_projects_manager() -> RecentProjectsManager:
    """获取全局最近项目管理器实例"""
    global _recent_projects_manager
    if _recent_projects_manager is None:
        _recent_projects_manager = RecentProjectsManager()
    return _recent_projects_manager

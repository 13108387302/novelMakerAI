#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目服务

管理项目的创建、打开、保存等操作
"""

from typing import List, Optional
from pathlib import Path

from src.domain.entities.project import Project, ProjectType, ProjectStatus, ProjectMetadata
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.events.project_events import (
    ProjectCreatedEvent, ProjectOpenedEvent, ProjectClosedEvent, ProjectSavedEvent
)
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger
from src.shared.constants import (
    DEFAULT_TARGET_WORD_COUNT, DEFAULT_RECENT_PROJECTS_LIMIT
)

logger = get_logger(__name__)

# 项目服务常量
PROJECT_SUBDIRS = ["documents", "backups", "exports", "cache"]
DEFAULT_EXPORT_FORMAT = "json"


class ProjectService:
    """
    项目服务

    管理小说项目的完整生命周期，包括创建、打开、保存、关闭和删除操作。
    提供项目状态管理和事件发布功能，支持不同类型的项目。

    实现方式：
    - 使用仓储模式进行项目数据持久化
    - 通过事件总线发布项目状态变更事件
    - 维护当前活动项目的引用
    - 提供项目元数据管理功能
    - 支持异步操作确保UI响应性

    Attributes:
        project_repository: 项目仓储接口
        event_bus: 事件总线用于发布项目事件
        _current_project: 当前打开的项目实例
    """

    def __init__(
        self,
        project_repository: IProjectRepository,
        event_bus: EventBus
    ):
        """
        初始化项目服务

        Args:
            project_repository: 项目仓储接口实现
            event_bus: 事件总线用于发布项目相关事件
        """
        self.project_repository = project_repository
        self.event_bus = event_bus
        self._current_project: Optional[Project] = None
    
    async def create_project(
        self,
        name: str,
        project_type: ProjectType = ProjectType.NOVEL,
        description: str = "",
        author: str = "",
        target_word_count: int = DEFAULT_TARGET_WORD_COUNT,
        project_path: Optional[str] = None
    ) -> Optional[Project]:
        """
        创建新项目

        创建一个新的小说项目，包含项目元数据和基本设置。
        创建成功后发布项目创建事件。

        实现方式：
        - 创建ProjectMetadata包含项目基本信息
        - 使用Project实体类封装项目数据
        - 通过仓储接口保存项目
        - 发布ProjectCreatedEvent事件
        - 提供完整的错误处理和日志记录

        Args:
            name: 项目名称
            project_type: 项目类型，默认为小说
            description: 项目描述
            author: 作者名称
            target_word_count: 目标字数，默认8万字
            project_path: 项目保存路径（可选）

        Returns:
            Optional[Project]: 创建成功返回项目实例，失败返回None

        Raises:
            Exception: 项目创建或保存失败时抛出
        """
        try:
            # 创建项目元数据
            metadata = ProjectMetadata(
                title=name,
                description=description,
                author=author,
                target_word_count=target_word_count
            )

            # 创建项目实体
            project = Project(
                metadata=metadata,
                project_type=project_type,
                status=ProjectStatus.ACTIVE
            )

            # 如果指定了项目路径，设置项目的根路径
            if project_path:
                from pathlib import Path
                base_path = Path(project_path)

                # 检查路径是否已经包含项目名
                if base_path.name == name:
                    # 路径已经包含项目名，直接使用
                    project.root_path = base_path
                else:
                    # 路径不包含项目名，添加项目名作为子目录
                    project.root_path = base_path / name

                # 确保项目根目录存在
                project.root_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"项目根目录已创建: {project.root_path}")

                # 在项目目录下创建必要的子目录
                for subdir in PROJECT_SUBDIRS:
                    subdir_path = project.root_path / subdir
                    subdir_path.mkdir(exist_ok=True)
                    logger.debug(f"子目录已创建: {subdir_path}")
            
            # 保存项目
            saved_project = await self.project_repository.save(project)
            if saved_project:
                # 设置为当前项目
                self._current_project = saved_project

                # 发布项目创建事件
                event = ProjectCreatedEvent(
                    project_id=saved_project.id,
                    project_name=saved_project.title,
                    project_path=str(saved_project.root_path) if saved_project.root_path else None
                )
                # 使用统一的事件发布方法
                try:
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布项目创建事件失败: {e}")

                logger.info(f"项目创建成功: {name} ({saved_project.id})")
                return saved_project
            else:
                logger.error(f"项目保存失败: {name}")
                return None
                
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            return None
    
    async def open_project(self, project_id: str) -> Optional[Project]:
        """打开项目"""
        try:
            logger.debug(f"尝试打开项目: {project_id}")
            project = await self.project_repository.load(project_id)

            if project:
                # 更新最后打开时间
                try:
                    await self.project_repository.update_last_opened(project_id)
                except Exception as e:
                    logger.warning(f"更新最后打开时间失败: {e}")

                # 设置为当前项目
                self._current_project = project

                # 发布项目打开事件
                try:
                    event = ProjectOpenedEvent(
                        project_id=project.id,
                        project_name=project.title,
                        project_path=str(project.root_path) if project.root_path else ""
                    )
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布项目打开事件失败: {e}")

                logger.info(f"项目打开成功: {project.title} ({project.id}) -> {project.root_path}")
                return project
            else:
                logger.warning(f"项目不存在: {project_id}")
                return None

        except Exception as e:
            logger.error(f"打开项目失败: {project_id}, 错误: {e}")
            return None
    
    async def open_project_by_path(self, project_path: Path) -> Optional[Project]:
        """根据路径打开项目"""
        try:
            # 检查路径是否存在
            if not project_path.exists():
                logger.warning(f"项目路径不存在: {project_path}")
                return None

            # 加载项目
            project = await self.project_repository.load_by_path(project_path)
            if project:
                # 尝试打开项目
                opened_project = await self.open_project(project.id)
                if opened_project:
                    logger.info(f"通过路径打开项目成功: {project_path}")
                    return opened_project
                else:
                    logger.warning(f"项目打开失败，ID可能无效: {project.id}")
                    return None
            else:
                logger.warning(f"项目路径无效或配置文件损坏: {project_path}")
                return None

        except Exception as e:
            logger.error(f"根据路径打开项目失败: {project_path}, 错误: {e}")
            return None
    
    async def close_project(self) -> bool:
        """关闭当前项目"""
        try:
            if self._current_project:
                # 保存项目
                await self.save_current_project()
                
                # 发布项目关闭事件
                event = ProjectClosedEvent(
                    project_id=self._current_project.id,
                    project_name=self._current_project.title
                )
                try:
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布项目关闭事件失败: {e}")
                
                logger.info(f"项目关闭: {self._current_project.title}")
                self._current_project = None
                return True
            else:
                logger.warning("没有打开的项目")
                return False
                
        except Exception as e:
            logger.error(f"关闭项目失败: {e}")
            return False
    
    async def save_current_project(self) -> bool:
        """保存当前项目"""
        try:
            if self._current_project:
                success = await self.project_repository.save(self._current_project)
                if success:
                    # 发布项目保存事件
                    event = ProjectSavedEvent(
                        project_id=self._current_project.id,
                        project_name=self._current_project.title,
                        save_path=str(self._current_project.root_path) if self._current_project.root_path else ""
                    )
                    try:
                        await self.event_bus.publish_async(event)
                    except Exception as e:
                        logger.warning(f"发布项目保存事件失败: {e}")
                    
                    logger.info(f"项目保存成功: {self._current_project.title}")
                    return True
                else:
                    logger.error(f"项目保存失败: {self._current_project.title}")
                    return False
            else:
                logger.warning("没有打开的项目")
                return False
                
        except Exception as e:
            logger.error(f"保存项目失败: {e}")
            return False
    
    async def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        try:
            # 如果是当前项目，先关闭
            if self._current_project and self._current_project.id == project_id:
                close_success = await self.close_project()
                if not close_success:
                    logger.error(f"关闭当前项目失败，取消删除操作: {project_id}")
                    return False

            success = await self.project_repository.delete(project_id)
            if success:
                logger.info(f"项目删除成功: {project_id}")
                return True
            else:
                logger.error(f"项目删除失败: {project_id}")
                return False

        except Exception as e:
            logger.error(f"删除项目失败: {e}")
            return False
    
    async def list_all_projects(self) -> List[Project]:
        """列出所有项目"""
        try:
            projects = await self.project_repository.list_all()
            logger.info(f"获取项目列表成功，共 {len(projects)} 个项目")
            return projects
            
        except Exception as e:
            logger.error(f"获取项目列表失败: {e}")
            return []
    
    async def get_recent_projects(self, limit: int = DEFAULT_RECENT_PROJECTS_LIMIT) -> List[Project]:
        """获取最近的项目"""
        try:
            projects = await self.project_repository.get_recent_projects(limit)
            logger.info(f"获取最近项目成功，共 {len(projects)} 个项目")
            return projects
            
        except Exception as e:
            logger.error(f"获取最近项目失败: {e}")
            return []
    
    async def search_projects(self, query: str) -> List[Project]:
        """搜索项目"""
        try:
            projects = await self.project_repository.search(query)
            logger.info(f"项目搜索完成，找到 {len(projects)} 个结果")
            return projects
            
        except Exception as e:
            logger.error(f"搜索项目失败: {e}")
            return []
    
    async def update_project_metadata(
        self,
        project_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        target_word_count: Optional[int] = None
    ) -> bool:
        """更新项目元数据"""
        try:
            project = await self.project_repository.load(project_id)
            if not project:
                logger.warning(f"项目不存在: {project_id}")
                return False
            
            # 更新元数据
            if title is not None:
                project.title = title
            if description is not None:
                project.metadata.description = description
            if author is not None:
                project.metadata.author = author
            if target_word_count is not None:
                project.metadata.target_word_count = target_word_count
            
            # 保存更新
            success = await self.project_repository.save(project)
            if success:
                # 如果是当前项目，更新引用
                if self._current_project and self._current_project.id == project_id:
                    self._current_project = project
                
                logger.info(f"项目元数据更新成功: {project_id}")
                return True
            else:
                logger.error(f"项目元数据更新失败: {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新项目元数据失败: {e}")
            return False
    
    async def create_project_backup(self, project_id: str, backup_path: Path) -> bool:
        """创建项目备份"""
        try:
            success = await self.project_repository.create_backup(project_id, backup_path)
            if success:
                logger.info(f"项目备份创建成功: {project_id} -> {backup_path}")
                return True
            else:
                logger.error(f"项目备份创建失败: {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"创建项目备份失败: {e}")
            return False
    
    async def export_project(
        self,
        project_id: str,
        export_path: Path,
        export_format: str = DEFAULT_EXPORT_FORMAT
    ) -> bool:
        """导出项目"""
        try:
            success = await self.project_repository.export_project(
                project_id, export_path, export_format
            )
            if success:
                logger.info(f"项目导出成功: {project_id} -> {export_path}")
                return True
            else:
                logger.error(f"项目导出失败: {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            return False
    
    async def import_project(
        self,
        import_path: Path,
        import_format: str = DEFAULT_EXPORT_FORMAT
    ) -> Optional[Project]:
        """导入项目"""
        try:
            project = await self.project_repository.import_project(import_path, import_format)
            if project:
                logger.info(f"项目导入成功: {import_path}")
                return project
            else:
                logger.error(f"项目导入失败: {import_path}")
                return None
                
        except Exception as e:
            logger.error(f"导入项目失败: {e}")
            return None
    
    @property
    def current_project(self) -> Optional[Project]:
        """当前项目"""
        return self._current_project

    def get_current_project(self) -> Optional[Project]:
        """获取当前项目"""
        return self._current_project

    def get_current_project_path(self) -> Optional[Path]:
        """获取当前项目路径"""
        if self._current_project and hasattr(self._current_project, 'root_path'):
            return self._current_project.root_path
        return None

    @property
    def has_current_project(self) -> bool:
        """是否有当前项目"""
        return self._current_project is not None

    async def save_project_as(self, project: Project, file_path: Path) -> bool:
        """另存为项目"""
        try:
            # 设置项目路径
            project.file_path = file_path

            # 保存项目
            success = await self.project_repository.save(project)
            if success:
                logger.info(f"项目另存为成功: {project.title} -> {file_path}")

                # 发布项目保存事件
                try:
                    event = ProjectSavedEvent(
                        project_id=project.id,
                        project_name=project.title,
                        save_path=str(file_path)
                    )
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布项目保存事件失败: {e}")
                return True
            else:
                logger.error(f"项目另存为失败: {project.title}")
                return False

        except Exception as e:
            logger.error(f"另存为项目失败: {e}")
            return False

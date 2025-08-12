#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件系统项目仓储实现

基于文件系统的项目数据持久化实现
"""

import json
import asyncio
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.domain.entities.project import Project, ProjectStatus, ProjectType
from src.domain.repositories.project_repository import IProjectRepository
from .base_file_repository import BaseFileRepository
from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import handle_async_errors
from src.shared.utils.file_operations import get_file_operations

logger = get_logger(__name__)


class FileProjectRepository(BaseFileRepository[Project], IProjectRepository):
    """
    文件系统项目仓储实现

    基于文件系统的项目数据持久化实现，使用JSON格式存储项目数据。
    继承BaseFileRepository提供通用的文件操作功能。

    实现方式：
    - 使用JSON文件存储项目数据
    - 维护项目索引提高查询性能
    - 支持项目的完整CRUD操作
    - 提供多种查询方式（状态、类型等）
    - 包含完整的错误处理和日志记录

    Attributes:
        base_path: 项目存储的基础路径
        entity_name: 实体名称，用于日志和错误信息
    """

    def __init__(self, base_path: Path):
        """
        初始化文件系统项目仓储

        Args:
            base_path: 项目存储的基础路径（必须提供，通常为项目内路径）
        """
        super().__init__(
            base_path=base_path,
            entity_name="project"
        )

        # 统一文件操作工具
        self.file_ops = get_file_operations("project_repo")

    def _extract_index_info(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取项目索引信息

        从项目数据中提取用于索引的关键信息，提高查询性能。

        Args:
            entity_data: 项目数据字典

        Returns:
            Dict[str, Any]: 索引信息字典
        """
        return {
            "name": entity_data.get("name", ""),
            "project_type": entity_data.get("project_type", ""),
            "status": entity_data.get("status", ""),
            "created_at": entity_data.get("created_at", ""),
            "word_count": entity_data.get("statistics", {}).get("total_words", 0)
        }

    async def _entity_to_dict(self, entity: Project) -> Dict[str, Any]:
        """
        项目实体转换为字典

        Args:
            entity: 项目实体实例

        Returns:
            Dict[str, Any]: 项目数据字典
        """
        return entity.to_dict()

    async def _dict_to_entity(self, data: Dict[str, Any]) -> Project:
        """
        字典转换为项目实体

        Args:
            data: 项目数据字典

        Returns:
            Project: 项目实体实例
        """
        return Project.from_dict(data)
    # 项目特定方法

    def _get_project_path(self, project_id: str) -> Path:
        """获取项目路径"""
        return self.base_path / project_id

    def _get_project_config_file(self, project_id: str) -> Path:
        """获取项目配置文件路径"""
        return self._get_project_path(project_id) / "project.json"
    
    @handle_async_errors("保存项目")
    async def save(self, project: Project) -> Project:
        """保存项目"""
        # 如果项目有自定义根路径，优先保存到那里
        if hasattr(project, 'root_path') and project.root_path:
            await self._save_to_custom_path(project)
            # 在编辑器目录保存项目索引信息
            await self._save_project_index(project)
            # 同时更新主索引，确保项目可以被找到
            await self._update_main_index(project)
            return project
        else:
            # 如果没有自定义路径，使用基类的保存方法（保存到编辑器目录）
            return await super().save(project)

    async def _save_to_custom_path(self, project: Project) -> None:
        """保存到自定义路径"""
        temp_file = None
        try:
            project_path = project.root_path
            project_path.mkdir(parents=True, exist_ok=True)

            config_file = project_path / "project.json"
            project_data = project.to_dict()

            # 使用统一文件操作工具原子保存
            await self.file_ops.save_json_atomic(
                file_path=config_file,
                data=project_data,
                create_backup=True,
                cache_key=f"project:{project.id}:config",
                cache_ttl=3600
            )
            logger.info(f"项目保存到自定义路径: {project.name} -> {project_path}")

        except Exception as e:
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, temp_file.unlink)
                except Exception:
                    pass
            logger.error(f"保存到自定义路径失败: {e}")
            # 不抛出异常，因为基类保存仍然会成功

    async def _save_project_index(self, project: Project) -> None:
        """在编辑器目录保存项目索引信息"""
        try:
            # 创建项目索引信息（只包含基本信息和路径引用）
            index_data = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "project_type": project.project_type.value,
                "status": project.status.value,
                "root_path": str(project.root_path) if project.root_path else None,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "last_opened_at": project.last_opened_at.isoformat() if project.last_opened_at else None,
                "is_index": True  # 标记这是索引文件
            }

            # 保存到编辑器目录的索引文件
            index_path = self.base_path / f"{project.id}_index.json"
            await self.file_ops.save_json_atomic(
                file_path=index_path,
                data=index_data,
                create_backup=True,
                cache_key=f"project:{project.id}:index",
                cache_ttl=3600
            )
            logger.info(f"项目索引已保存: {index_path}")

        except Exception as e:
            logger.error(f"保存项目索引失败: {e}")
            raise

    async def _update_main_index(self, project: Project) -> None:
        """更新主索引，确保项目可以被找到"""
        try:
            # 使用基类的索引更新方法
            project_data = await self._entity_to_dict(project)
            self._update_index_entry(project.id, project_data)
            logger.info(f"已更新主索引: {project.title} ({project.id})")
        except Exception as e:
            logger.error(f"更新主索引失败: {e}")

    # 项目特定方法（基类已提供通用的get_by_id）
    async def load(self, project_id: str) -> Optional[Project]:
        """根据ID加载项目（支持自定义路径）"""
        try:
            # 首先尝试从基础路径加载（编辑器目录）
            project = await self.get_by_id(project_id)
            if project:
                logger.debug(f"从基础路径加载项目成功: {project.title}")
                return project

            # 如果基础路径没有找到，尝试从索引中查找自定义路径
            logger.debug(f"基础路径未找到项目 {project_id}，尝试从索引查找自定义路径")
            index = self._load_index()

            if project_id in index:
                project_info = index[project_id]
                custom_path = project_info.get('path')

                if custom_path:
                    custom_path = Path(custom_path)
                    logger.debug(f"从索引找到自定义路径: {custom_path}")

                    # 使用自定义路径加载项目
                    project = await self.load_by_path(custom_path)
                    if project:
                        logger.info(f"从自定义路径加载项目成功: {project.title} ({custom_path})")
                        return project
                    else:
                        logger.warning(f"自定义路径中的项目文件损坏或不存在: {custom_path}")
                else:
                    logger.warning(f"索引中的项目 {project_id} 没有路径信息")
            else:
                logger.warning(f"索引中未找到项目: {project_id}")

            logger.warning(f"无法加载项目: {project_id}")
            return None

        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            return None
    
    @handle_async_errors("根据路径加载项目")
    async def load_by_path(self, project_path: Path) -> Optional[Project]:
        """根据路径加载项目"""
        try:
            config_file = project_path / "project.json"
            if not config_file.exists():
                return None

            project_data = await self.file_ops.load_json_cached(
                file_path=config_file,
                cache_key=f"project:path:{str(project_path)}",
                cache_ttl=3600
            )
            if not isinstance(project_data, dict):
                logger.error(f"项目配置文件格式无效: {config_file}")
                return None

            project = Project.from_dict(project_data)

            # 设置自定义根路径
            if hasattr(project, 'root_path'):
                project.root_path = project_path

            # 更新项目索引中的路径信息，如果不存在则添加
            try:
                await self._ensure_project_in_index(project, str(project_path))
            except Exception as e:
                logger.warning(f"确保项目在索引中失败: {e}")

            return project

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"项目配置文件格式错误 {config_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载项目失败 {project_path}: {e}")
            return None

    async def _ensure_project_in_index(self, project: Project, project_path: str):
        """确保项目在索引中，如果不存在则添加"""
        try:
            index = self._load_index()

            if project.id in index:
                # 更新路径信息
                index[project.id]['path'] = project_path
                index[project.id]['updated_at'] = datetime.now().isoformat()
                logger.debug(f"已更新项目索引路径: {project.id} -> {project_path}")
            else:
                # 项目不在索引中，添加到索引
                logger.info(f"项目不在索引中，正在添加: {project.id}")
                index[project.id] = {
                    'id': project.id,
                    'title': project.title,
                    'description': project.description,
                    'project_type': project.project_type.value,
                    'status': project.status.value,
                    'path': project_path,
                    'created_at': project.created_at.isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'last_opened_at': project.last_opened_at.isoformat() if project.last_opened_at else None
                }
                logger.info(f"已添加项目到索引: {project.title} ({project.id})")

            # 保存索引
            self._save_index(index)

        except Exception as e:
            logger.error(f"确保项目在索引中失败: {e}")

    async def _update_project_path_in_index(self, project_id: str, project_path: str):
        """更新项目索引中的路径信息（保留向后兼容）"""
        try:
            index = self._load_index()

            if project_id in index:
                # 更新路径信息
                index[project_id]['path'] = project_path
                index[project_id]['updated_at'] = datetime.now().isoformat()

                # 保存索引
                self._save_index(index)
                logger.debug(f"已更新项目索引路径: {project_id} -> {project_path}")
            else:
                logger.warning(f"项目索引中未找到项目: {project_id}")

        except Exception as e:
            logger.error(f"更新项目索引路径失败: {e}")

    # 基类已提供delete、exists、get_all方法，这里提供兼容性方法
    async def list_all(self) -> List[Project]:
        """列出所有项目（兼容性方法）"""
        return await self.get_all()
    
    async def list_by_status(self, status: ProjectStatus) -> List[Project]:
        """根据状态列出项目"""
        projects = await self.get_all()
        return [p for p in projects if p.status == status]

    async def list_by_type(self, project_type: ProjectType) -> List[Project]:
        """根据类型列出项目"""
        projects = await self.get_all()
        return [p for p in projects if p.project_type == project_type]

    async def search(self, query: str) -> List[Project]:
        """搜索项目"""
        projects = await self.get_all()
        query_lower = query.lower()

        results = []
        for project in projects:
            if (query_lower in project.name.lower() or
                query_lower in project.metadata.description.lower() or
                any(query_lower in tag for tag in project.metadata.tags)):
                results.append(project)

        return results

    async def get_recent_projects(self, limit: int = 10) -> List[Project]:
        """获取最近打开的项目"""
        projects = await self.get_all()

        # 按最后打开时间排序
        projects.sort(
            key=lambda p: p.last_opened_at or datetime.min,
            reverse=True
        )

        return projects[:limit]

    async def update_last_opened(self, project_id: str) -> bool:
        """更新最后打开时间"""
        project = await self.get_by_id(project_id)
        if project:
            project.open()  # 使用项目的open方法
            await self.save(project)
            return True
        return False

    # 项目特定的备份和导入导出功能
    async def create_backup(self, project_id: str, backup_path: Path) -> bool:
        """创建项目备份"""
        try:
            project_path = self._get_project_path(project_id)
            if not project_path.exists():
                return False
            
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(project_path, backup_path)
            
            logger.info(f"项目备份创建成功: {project_id} -> {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建项目备份失败: {e}")
            return False
    
    async def restore_backup(self, project_id: str, backup_path: Path) -> bool:
        """恢复项目备份"""
        try:
            if not backup_path.exists():
                return False
            
            project_path = self._get_project_path(project_id)
            
            # 删除现有项目
            if project_path.exists():
                shutil.rmtree(project_path)
            
            # 恢复备份
            shutil.copytree(backup_path, project_path)
            
            logger.info(f"项目备份恢复成功: {backup_path} -> {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复项目备份失败: {e}")
            return False
    
    # 项目特定的实用方法
    async def validate_project_structure(self, project_path: Path) -> List[str]:
        """验证项目结构"""
        errors = []

        if not project_path.exists():
            errors.append("项目路径不存在")
            return errors

        if not project_path.is_dir():
            errors.append("项目路径不是目录")
            return errors

        # 检查必需文件
        config_file = project_path / "project.json"
        if not config_file.exists():
            errors.append("缺少项目配置文件 project.json")

        return errors

    # 实现缺失的抽象方法（简单实现）
    async def export_project(self, project_id: str, export_path: Path, export_format: str) -> bool:
        """
        导出项目（委托给ImportExportService）

        .. deprecated:: 当前版本
            这个方法主要用于接口兼容性，实际的导出功能应该通过ImportExportService调用。
            建议直接使用 ImportExportService.export_project() 方法。

        Args:
            project_id: 项目ID
            export_path: 导出路径
            export_format: 导出格式

        Returns:
            bool: 导出是否成功
        """
        import warnings
        warnings.warn(
            "file_project_repository.export_project() 已弃用，请使用 ImportExportService.export_project()",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning("export_project方法应该通过ImportExportService调用")

        # 提供基本的导出功能作为后备
        try:
            project = await self.load(project_id)
            if not project:
                logger.error(f"项目不存在: {project_id}")
                return False

            # 简单的JSON导出
            if export_format.lower() in ['json', '.json']:
                project_data = {
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'type': project.type.value if hasattr(project.type, 'value') else str(project.type),
                    'status': project.status.value if hasattr(project.status, 'value') else str(project.status),
                    'metadata': project.metadata.__dict__ if hasattr(project.metadata, '__dict__') else {},
                    'settings': project.settings.__dict__ if hasattr(project.settings, '__dict__') else {},
                    'exported_at': datetime.now().isoformat()
                }

                # 使用统一文件操作保存
                from pathlib import Path
                export_path = Path(export_path)
                await self.file_ops.save_json_atomic(
                    file_path=export_path,
                    data=project_data,
                    create_backup=False,
                    cache_key=None,
                    cache_ttl=0
                )

                logger.info(f"项目导出成功: {export_path}")
                return True

            logger.warning(f"不支持的导出格式: {export_format}")
            return False

        except Exception as e:
            logger.error(f"项目导出失败: {e}")
            return False

    async def import_project(self, import_path: Path, import_format: str) -> Optional[Project]:
        """
        导入项目（委托给ImportExportService）

        .. deprecated:: 当前版本
            这个方法主要用于接口兼容性，实际的导入功能应该通过ImportExportService调用。
            建议直接使用 ImportExportService.import_project() 方法。

        Args:
            import_path: 导入路径
            import_format: 导入格式

        Returns:
            Optional[Project]: 导入的项目，失败时返回None
        """
        import warnings
        warnings.warn(
            "file_project_repository.import_project() 已弃用，请使用 ImportExportService.import_project()",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning("import_project方法应该通过ImportExportService调用")

        # 提供基本的导入功能作为后备
        try:
            if not import_path.exists():
                logger.error(f"导入文件不存在: {import_path}")
                return None

            # 简单的JSON导入
            if import_format.lower() in ['json', '.json']:
                # 使用统一文件操作加载
                project_data = await self.file_ops.load_json_cached(
                    file_path=import_path,
                    cache_key=f"project:import:{str(import_path)}",
                    cache_ttl=0
                )
                if not isinstance(project_data, dict):
                    logger.error(f"导入文件不是有效的JSON对象: {import_path}")
                    return None

                # 创建项目对象
                from src.domain.entities.project import Project, ProjectType, ProjectStatus
                from src.domain.entities.project.project_metadata import ProjectMetadata
                from src.domain.entities.project.project_settings import ProjectSettings

                project = Project(
                    id=project_data.get('id', str(uuid4())),
                    name=project_data.get('name', '导入的项目'),
                    description=project_data.get('description', ''),
                    type=ProjectType(project_data.get('type', 'novel')),
                    status=ProjectStatus(project_data.get('status', 'active')),
                    metadata=ProjectMetadata(**project_data.get('metadata', {})),
                    settings=ProjectSettings(**project_data.get('settings', {}))
                )

                # 保存项目
                success = await self.save(project)
                if success:
                    logger.info(f"项目导入成功: {project.name}")
                    return project
                else:
                    logger.error("项目保存失败")
                    return None

            logger.warning(f"不支持的导入格式: {import_format}")
            return None

        except Exception as e:
            logger.error(f"项目导入失败: {e}")
            return None

    async def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计信息"""
        project = await self.get_by_id(project_id)
        if not project:
            return {}

        return {
            "project_id": project_id,
            "name": project.name,
            "total_words": project.statistics.total_words,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }

    async def migrate_project(self, project_id: str, target_version: str) -> bool:
        """迁移项目到新版本格式"""
        project = await self.get_by_id(project_id)
        if not project:
            return False

        # 简单的版本更新
        project.format_version = target_version
        project.touch()
        await self.save(project)
        return True

    # 元数据管理方法（简单实现）
    async def save_metadata(self, project_id: str, metadata: Dict[str, Any]) -> bool:
        """保存项目元数据"""
        project = await self.get_by_id(project_id)
        if not project:
            return False

        # 更新项目元数据
        for key, value in metadata.items():
            if hasattr(project.metadata, key):
                setattr(project.metadata, key, value)

        await self.save(project)
        return True

    async def load_metadata(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载项目元数据"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        return {
            "title": project.metadata.title,
            "description": project.metadata.description,
            "author": project.metadata.author,
            "tags": list(project.metadata.tags),
            "created_at": project.metadata.created_at.isoformat(),
            "updated_at": project.metadata.updated_at.isoformat()
        }

    async def update_metadata(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """更新项目元数据"""
        return await self.save_metadata(project_id, updates)

    async def delete_metadata(self, project_id: str) -> bool:
        """删除项目元数据"""
        # 元数据是项目的一部分，不能单独删除
        return False

    async def search_by_metadata(self, filters: Dict[str, Any]) -> List[Project]:
        """根据元数据搜索项目"""
        projects = await self.get_all()
        results = []

        for project in projects:
            match = True
            for key, value in filters.items():
                if hasattr(project.metadata, key):
                    field_value = getattr(project.metadata, key)
                    if isinstance(field_value, str) and isinstance(value, str):
                        if value.lower() not in field_value.lower():
                            match = False
                            break
                    elif field_value != value:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                results.append(project)

        return results

    # 配置管理方法
    async def save_config(self, project_id: str, config: Dict[str, Any]) -> bool:
        """保存项目配置"""
        project = await self.get_by_id(project_id)
        if not project:
            return False

        # 更新项目设置
        for key, value in config.items():
            if hasattr(project.settings, key):
                setattr(project.settings, key, value)

        await self.save(project)
        return True

    async def load_config(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载项目配置"""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        return project.settings.to_dict()

    async def update_config(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """更新项目配置"""
        return await self.save_config(project_id, updates)

    async def delete_config(self, project_id: str) -> bool:
        """删除项目配置"""
        # 配置是项目的一部分，不能单独删除
        return False

    async def get_config_value(self, project_id: str, key: str, default_value: Any = None) -> Any:
        """获取配置值"""
        config = await self.load_config(project_id)
        if not config:
            return default_value
        return config.get(key, default_value)

    async def set_config_value(self, project_id: str, key: str, value: Any) -> bool:
        """设置配置值"""
        return await self.update_config(project_id, {key: value})

    # 模板管理方法（简单实现）
    async def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有项目模板"""
        # 简单实现：返回空列表
        return []

    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取项目模板"""
        # 简单实现：返回None
        return None

    async def create_project_from_template(self, template_id: str, project_name: str, project_path: Path) -> Optional[Project]:
        """从模板创建项目"""
        try:
            # 获取模板
            templates_dir = self.base_path.parent / "templates"
            template_dir = templates_dir / template_id

            if not template_dir.exists():
                logger.error(f"模板不存在: {template_id}")
                return None

            # 读取模板元数据
            metadata_file = template_dir / "template.json"
            project_template_file = template_dir / "project_template.json"

            if not metadata_file.exists() or not project_template_file.exists():
                logger.error(f"模板文件不完整: {template_id}")
                return None

            # 使用统一文件操作加载模板
            template_metadata = await self.file_ops.load_json_cached(
                file_path=metadata_file,
                cache_key=f"template:{template_id}:metadata",
                cache_ttl=3600
            ) or {}

            project_template = await self.file_ops.load_json_cached(
                file_path=project_template_file,
                cache_key=f"template:{template_id}:project",
                cache_ttl=3600
            ) or {}

            # 创建项目
            from src.domain.entities.project import create_project, ProjectType

            # 解析项目类型
            project_type_str = project_template.get("project_type", "NOVEL")
            try:
                project_type = ProjectType(project_type_str)
            except ValueError:
                project_type = ProjectType.NOVEL

            # 创建项目实例
            project = create_project(project_name, project_type)

            # 应用模板数据
            if "metadata" in project_template and project.metadata:
                template_meta = project_template["metadata"]

                # 替换占位符
                project.metadata.title = template_meta.get("title", "").replace("{{PROJECT_TITLE}}", project_name)
                project.metadata.author = template_meta.get("author", "").replace("{{AUTHOR}}", "")
                project.metadata.genre = template_meta.get("genre", "")
                # 如果模板未提供作者/体裁，使用设置中的默认值
                try:
                    from src.shared.ioc.container import get_global_container
                    container = get_global_container()
                    if container is not None:
                        try:
                            from src.application.services.settings_service import SettingsService
                            ss = container.try_get(SettingsService)
                        except Exception:
                            ss = None
                        if ss is not None:
                            if not project.metadata.author:
                                project.metadata.author = ss.get_setting("project.default_author", "") or project.metadata.author
                            if not project.metadata.genre:
                                project.metadata.genre = ss.get_setting("project.default_genre", "") or project.metadata.genre
                except Exception:
                    pass
                project.metadata.target_word_count = template_meta.get("target_word_count", 50000)
                project.metadata.tags = template_meta.get("tags", [])
                project.metadata.themes = template_meta.get("themes", [])

            # 保存项目
            await self.save(project)

            # 创建模板文档
            if "documents" in project_template:
                from src.domain.entities.document import Document, DocumentType

                for doc_template in project_template["documents"]:
                    try:
                        # 解析文档类型
                        doc_type_str = doc_template.get("document_type", "CHAPTER")
                        try:
                            doc_type = DocumentType(doc_type_str)
                        except ValueError:
                            doc_type = DocumentType.CHAPTER

                        # 创建文档
                        document = Document(
                            title=doc_template.get("title", "新文档"),
                            document_type=doc_type,
                            project_id=project.id,
                            content=doc_template.get("content", "").replace("{{DOCUMENT_CONTENT}}", ""),
                            order=doc_template.get("order", 0)
                        )

                        # 保存文档（需要文档仓储）
                        # 这里暂时跳过，因为需要DocumentRepository
                        logger.debug(f"模板文档: {document.title}")

                    except Exception as e:
                        logger.warning(f"创建模板文档失败: {e}")
                        continue

            logger.info(f"从模板创建项目成功: {project_name} (模板: {template_metadata.get('name', template_id)})")
            return project

        except Exception as e:
            logger.error(f"从模板创建项目失败: {e}")
            return None

    async def save_as_template(self, project_id: str, template_name: str, template_description: str = "") -> bool:
        """将项目保存为模板"""
        try:
            # 获取项目
            project = await self.get_by_id(project_id)
            if not project:
                logger.error(f"项目不存在: {project_id}")
                return False

            # 创建模板目录
            templates_dir = self.base_path.parent / "templates"
            templates_dir.mkdir(exist_ok=True)

            # 生成模板ID
            import uuid
            template_id = str(uuid.uuid4())
            template_dir = templates_dir / template_id
            template_dir.mkdir(exist_ok=True)

            # 创建模板元数据
            template_metadata = {
                "id": template_id,
                "name": template_name,
                "description": template_description,
                "created_at": datetime.now().isoformat(),
                "source_project_id": project_id,
                "source_project_name": project.name,
                "project_type": project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
                "version": "1.0.0"
            }

            # 保存模板元数据
            metadata_file = template_dir / "template.json"
            await self.file_ops.save_json_atomic(
                file_path=metadata_file,
                data=template_metadata,
                create_backup=False,
                cache_key=f"template:{template_id}:metadata",
                cache_ttl=0
            )

            # 复制项目结构（不包含具体内容）
            project_template = {
                "name": "{{PROJECT_NAME}}",  # 占位符
                "description": "{{PROJECT_DESCRIPTION}}",
                "project_type": project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
                "created_at": "{{CREATED_AT}}",
                "metadata": {
                    "title": "{{PROJECT_TITLE}}",
                    "author": "{{AUTHOR}}",
                    "genre": project.metadata.genre if project.metadata else "",
                    "target_word_count": project.metadata.target_word_count if project.metadata else 50000,
                    "tags": project.metadata.tags if project.metadata else [],
                    "themes": project.metadata.themes if project.metadata else []
                },
                "documents": []
            }

            # 如果项目有文档，创建文档模板结构
            if hasattr(project, 'documents') and project.documents:
                for doc in project.documents:
                    doc_template = {
                        "title": doc.title,
                        "document_type": doc.document_type.value if hasattr(doc.document_type, 'value') else str(doc.document_type),
                        "content": "{{DOCUMENT_CONTENT}}",  # 占位符
                        "order": getattr(doc, 'order', 0)
                    }
                    project_template["documents"].append(doc_template)

            # 保存项目模板
            project_template_file = template_dir / "project_template.json"
            await self.file_ops.save_json_atomic(
                file_path=project_template_file,
                data=project_template,
                create_backup=False,
                cache_key=f"template:{template_id}:project",
                cache_ttl=0
            )

            logger.info(f"项目模板保存成功: {template_name} ({template_id})")
            return True

        except Exception as e:
            logger.error(f"保存项目模板失败: {e}")
            return False

    async def delete_template(self, template_id: str) -> bool:
        """删除项目模板"""
        try:
            # 模板目录
            templates_dir = self.base_path.parent / "templates"
            template_dir = templates_dir / template_id

            if not template_dir.exists():
                logger.warning(f"模板不存在: {template_id}")
                return False

            # 验证是否为有效模板
            metadata_file = template_dir / "template.json"
            if not metadata_file.exists():
                logger.error(f"无效的模板目录: {template_id}")
                return False

            # 读取模板元数据（用于日志）
            try:
                metadata = await self.file_ops.load_json_cached(
                    file_path=metadata_file,
                    cache_key=f"template:{template_id}:metadata",
                    cache_ttl=3600
                ) or {}
                template_name = metadata.get("name", template_id)
            except Exception:
                template_name = template_id

            # 删除模板目录
            import shutil
            shutil.rmtree(template_dir)

            logger.info(f"项目模板删除成功: {template_name} ({template_id})")
            return True

        except Exception as e:
            logger.error(f"删除项目模板失败: {e}")
            return False

    async def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用的项目模板"""
        try:
            templates_dir = self.base_path.parent / "templates"
            if not templates_dir.exists():
                return []

            templates = []
            for template_dir in templates_dir.iterdir():
                if not template_dir.is_dir():
                    continue

                metadata_file = template_dir / "template.json"
                if not metadata_file.exists():
                    continue

                try:
                    metadata = await self.file_ops.load_json_cached(
                        file_path=metadata_file,
                        cache_key=f"template:{template_dir.name}:metadata",
                        cache_ttl=3600
                    )
                    if metadata:
                        templates.append(metadata)
                except Exception as e:
                    logger.warning(f"读取模板元数据失败 {template_dir}: {e}")
                    continue

            # 按创建时间排序
            templates.sort(key=lambda t: t.get("created_at", ""), reverse=True)
            return templates

        except Exception as e:
            logger.error(f"列出项目模板失败: {e}")
            return []

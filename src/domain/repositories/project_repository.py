#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目仓储接口

定义项目数据访问的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.domain.entities.project import Project, ProjectStatus, ProjectType


class IProjectRepository(ABC):
    """
    项目仓储接口

    定义项目数据访问的抽象接口，遵循仓储模式。
    提供项目的CRUD操作和查询功能。

    实现方式：
    - 使用抽象基类定义接口契约
    - 支持异步操作提高性能
    - 提供多种查询方式（ID、路径、状态等）
    - 支持项目的完整生命周期管理
    """

    @abstractmethod
    async def save(self, project: Project) -> bool:
        """
        保存项目到存储介质

        Args:
            project: 要保存的项目实例

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        pass

    @abstractmethod
    async def load(self, project_id: str) -> Optional[Project]:
        """
        根据项目ID加载项目

        Args:
            project_id: 项目唯一标识符

        Returns:
            Optional[Project]: 项目实例，不存在时返回None
        """
        pass

    @abstractmethod
    async def load_by_path(self, project_path: Path) -> Optional[Project]:
        """
        根据项目路径加载项目

        Args:
            project_path: 项目文件路径

        Returns:
            Optional[Project]: 项目实例，不存在时返回None
        """
        pass

    @abstractmethod
    async def delete(self, project_id: str) -> bool:
        """
        删除指定项目

        Args:
            project_id: 项目唯一标识符

        Returns:
            bool: 删除成功返回True，失败返回False
        """
        pass

    @abstractmethod
    async def exists(self, project_id: str) -> bool:
        """
        检查项目是否存在

        Args:
            project_id: 项目唯一标识符

        Returns:
            bool: 存在返回True，不存在返回False
        """
        pass

    @abstractmethod
    async def list_all(self) -> List[Project]:
        """
        列出所有项目

        Returns:
            List[Project]: 所有项目的列表
        """
        pass

    @abstractmethod
    async def list_by_status(self, status: ProjectStatus) -> List[Project]:
        """根据状态列出项目"""
        pass
    
    @abstractmethod
    async def list_by_type(self, project_type: ProjectType) -> List[Project]:
        """根据类型列出项目"""
        pass
    
    @abstractmethod
    async def search(self, query: str) -> List[Project]:
        """搜索项目"""
        pass
    
    @abstractmethod
    async def get_recent_projects(self, limit: int = 10) -> List[Project]:
        """获取最近打开的项目"""
        pass
    
    @abstractmethod
    async def update_last_opened(self, project_id: str) -> bool:
        """更新最后打开时间"""
        pass
    
    @abstractmethod
    async def create_backup(self, project_id: str, backup_path: Path) -> bool:
        """创建项目备份"""
        pass
    
    @abstractmethod
    async def restore_backup(self, project_id: str, backup_path: Path) -> bool:
        """恢复项目备份"""
        pass
    
    @abstractmethod
    async def export_project(
        self, 
        project_id: str, 
        export_path: Path, 
        export_format: str
    ) -> bool:
        """导出项目"""
        pass
    
    @abstractmethod
    async def import_project(
        self, 
        import_path: Path, 
        import_format: str
    ) -> Optional[Project]:
        """导入项目"""
        pass
    
    @abstractmethod
    async def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取项目统计信息"""
        pass
    
    @abstractmethod
    async def validate_project_structure(self, project_path: Path) -> List[str]:
        """验证项目结构"""
        pass
    
    @abstractmethod
    async def migrate_project(self, project_id: str, target_version: str) -> bool:
        """迁移项目到新版本格式"""
        pass


class IProjectMetadataRepository(ABC):
    """项目元数据仓储接口"""
    
    @abstractmethod
    async def save_metadata(self, project_id: str, metadata: Dict[str, Any]) -> bool:
        """保存项目元数据"""
        pass
    
    @abstractmethod
    async def load_metadata(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载项目元数据"""
        pass
    
    @abstractmethod
    async def update_metadata(
        self, 
        project_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """更新项目元数据"""
        pass
    
    @abstractmethod
    async def delete_metadata(self, project_id: str) -> bool:
        """删除项目元数据"""
        pass
    
    @abstractmethod
    async def search_by_metadata(
        self, 
        filters: Dict[str, Any]
    ) -> List[str]:
        """根据元数据搜索项目ID"""
        pass


class IProjectConfigRepository(ABC):
    """项目配置仓储接口"""
    
    @abstractmethod
    async def save_config(self, project_id: str, config: Dict[str, Any]) -> bool:
        """保存项目配置"""
        pass
    
    @abstractmethod
    async def load_config(self, project_id: str) -> Optional[Dict[str, Any]]:
        """加载项目配置"""
        pass
    
    @abstractmethod
    async def update_config(
        self, 
        project_id: str, 
        key: str, 
        value: Any
    ) -> bool:
        """更新配置项"""
        pass
    
    @abstractmethod
    async def delete_config(self, project_id: str) -> bool:
        """删除项目配置"""
        pass
    
    @abstractmethod
    async def get_config_value(
        self, 
        project_id: str, 
        key: str, 
        default: Any = None
    ) -> Any:
        """获取配置值"""
        pass


class IProjectTemplateRepository(ABC):
    """项目模板仓储接口"""
    
    @abstractmethod
    async def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有项目模板"""
        pass
    
    @abstractmethod
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取项目模板"""
        pass
    
    @abstractmethod
    async def create_project_from_template(
        self, 
        template_id: str, 
        project_name: str, 
        project_path: Path
    ) -> Optional[Project]:
        """从模板创建项目"""
        pass
    
    @abstractmethod
    async def save_as_template(
        self, 
        project_id: str, 
        template_name: str, 
        template_description: str
    ) -> bool:
        """将项目保存为模板"""
        pass
    
    @abstractmethod
    async def delete_template(self, template_id: str) -> bool:
        """删除项目模板"""
        pass

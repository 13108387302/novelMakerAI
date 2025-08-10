#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目控制器

专门处理项目相关的UI操作和业务逻辑
"""

import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

from src.application.services.project_service import ProjectService
from src.application.services.settings_service import SettingsService
from src.domain.entities.project import Project, ProjectType
from src.shared.utils.base_service import BaseService

logger = logging.getLogger(__name__)


class ProjectController(BaseService, QObject):
    """
    项目控制器
    
    专门处理项目相关的操作，从主控制器中分离出来。
    负责项目的创建、打开、保存、关闭等操作。
    
    重构改进：
    - 单一职责：只处理项目相关操作
    - 减少主控制器的复杂度
    - 提供清晰的项目操作接口
    """
    
    # 信号定义
    project_opened = pyqtSignal(object)  # 项目打开
    project_closed = pyqtSignal()  # 项目关闭
    project_created = pyqtSignal(object)  # 项目创建
    status_message = pyqtSignal(str)  # 状态消息
    
    def __init__(
        self,
        project_service: ProjectService,
        settings_service: SettingsService
    ):
        """
        初始化项目控制器
        
        Args:
            project_service: 项目服务
            settings_service: 设置服务
        """
        QObject.__init__(self)
        BaseService.__init__(self, "ProjectController")
        
        self.project_service = project_service
        self.settings_service = settings_service
    
    async def create_project(
        self,
        name: str,
        project_type: ProjectType = ProjectType.NOVEL,
        description: str = "",
        author: str = "",
        target_word_count: int = 80000,
        project_path: Optional[str] = None
    ) -> Optional[Project]:
        """
        创建新项目
        
        Args:
            name: 项目名称
            project_type: 项目类型
            description: 项目描述
            author: 作者名称
            target_word_count: 目标字数
            project_path: 项目路径
            
        Returns:
            Optional[Project]: 创建的项目实例
        """
        try:
            self.status_message.emit(f"正在创建项目: {name}")
            
            project = await self.project_service.create_project(
                name=name,
                project_type=project_type,
                description=description,
                author=author,
                target_word_count=target_word_count,
                project_path=project_path
            )
            
            if project:
                self.project_created.emit(project)
                self.status_message.emit(f"项目创建成功: {name}")
                self.logger.info(f"项目创建成功: {name}")
                return project
            else:
                self.logger.error(f"项目创建失败: {name}")
                return None
                
        except Exception as e:
            self.logger.error(f"创建项目失败: {e}")
            return None
    
    async def open_project(self, project_id: str) -> Optional[Project]:
        """
        打开项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            Optional[Project]: 打开的项目实例
        """
        try:
            self.status_message.emit(f"正在打开项目: {project_id}")
            
            project = await self.project_service.open_project(project_id)
            
            if project:
                # 更新设置
                await self._update_project_settings(project)
                
                self.project_opened.emit(project)
                self.status_message.emit(f"项目打开成功: {project.title}")
                self.logger.info(f"项目打开成功: {project.title}")
                return project
            else:
                self.logger.warning(f"项目不存在: {project_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"打开项目失败: {e}")
            return None
    
    async def open_project_by_path(self, project_path: Path) -> Optional[Project]:
        """
        根据路径打开项目
        
        Args:
            project_path: 项目路径
            
        Returns:
            Optional[Project]: 打开的项目实例
        """
        try:
            self.status_message.emit(f"正在打开项目: {project_path}")
            
            project = await self.project_service.open_project_by_path(project_path)
            
            if project:
                # 更新设置
                await self._update_project_settings(project)
                
                self.project_opened.emit(project)
                self.status_message.emit(f"项目打开成功: {project.title}")
                return project
            else:
                self.logger.warning(f"无法打开项目: {project_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"根据路径打开项目失败: {e}")
            return None
    
    async def close_project(self) -> bool:
        """
        关闭当前项目
        
        Returns:
            bool: 关闭是否成功
        """
        try:
            current_project = self.project_service.current_project
            if current_project:
                self.status_message.emit(f"正在关闭项目: {current_project.title}")
                
                success = await self.project_service.close_project()
                if success:
                    self.project_closed.emit()
                    self.status_message.emit("项目已关闭")
                    self.logger.info("项目关闭成功")
                    return True
                else:
                    self.logger.error("项目关闭失败")
                    return False
            else:
                self.logger.info("没有打开的项目需要关闭")
                return True
                
        except Exception as e:
            self.logger.error(f"关闭项目失败: {e}")
            return False
    
    async def save_current_project(self) -> bool:
        """
        保存当前项目
        
        Returns:
            bool: 保存是否成功
        """
        try:
            if self.project_service.has_current_project:
                self.status_message.emit("正在保存项目...")
                
                success = await self.project_service.save_current_project()
                if success:
                    self.status_message.emit("项目保存成功")
                    self.logger.info("项目保存成功")
                    return True
                else:
                    self.logger.error("项目保存失败")
                    return False
            else:
                self.logger.warning("没有打开的项目需要保存")
                return True
                
        except Exception as e:
            self.logger.error(f"保存项目失败: {e}")
            return False
    
    async def _update_project_settings(self, project: Project) -> None:
        """更新项目相关设置"""
        try:
            # 保存最近打开的目录
            if project.root_path:
                self.settings_service.set_last_opened_directory(str(project.root_path))
                self.settings_service.set_last_project_info(project.id, str(project.root_path))
            
            # 更新最近项目列表
            try:
                from src.shared.managers.recent_projects_manager import get_recent_projects_manager
                recent_manager = get_recent_projects_manager()
                if project.root_path:
                    recent_manager.add_project(project.root_path, project.title)
            except Exception as e:
                self.logger.warning(f"更新最近项目列表失败: {e}")
                
        except Exception as e:
            self.logger.warning(f"更新项目设置失败: {e}")
    
    @property
    def current_project(self) -> Optional[Project]:
        """获取当前项目"""
        return self.project_service.current_project
    
    @property
    def has_current_project(self) -> bool:
        """是否有当前项目"""
        return self.project_service.has_current_project

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序服务

管理应用程序的生命周期和全局状态
"""

from typing import Optional
from pathlib import Path
from datetime import datetime
import json
import asyncio

from src.shared.events.event_bus import EventBus
from src.shared.ioc.container import Container
from src.shared.utils.logger import get_logger
from config.settings import Settings

# 提前导入事件类，避免在方法中导入
try:
    from src.domain.events.project_events import (
        ProjectCreatedEvent, ProjectOpenedEvent, ProjectClosedEvent
    )
except ImportError:
    # 如果导入失败，定义空的事件类
    ProjectCreatedEvent = ProjectOpenedEvent = ProjectClosedEvent = None

logger = get_logger(__name__)


def safe_execute(operation_name: str):
    """安全执行装饰器"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logger.debug(f"{operation_name}完成")
                return result
            except Exception as e:
                logger.error(f"{operation_name}失败: {e}")
                return False if func.__name__.startswith('_') else None
        return wrapper
    return decorator


class ApplicationService:
    """应用程序服务"""
    
    def __init__(
        self,
        container: Container,
        event_bus: EventBus,
        settings: Settings
    ):
        self.container = container
        self.event_bus = event_bus
        self.settings = settings
        self._is_initialized = False
        self._current_project_id: Optional[str] = None
    
    def initialize(self) -> bool:
        """初始化应用程序服务"""
        try:
            logger.info("初始化应用程序服务...")
            
            # 确保必要的目录存在
            self._ensure_directories()
            
            # 初始化事件订阅
            self._setup_event_subscriptions()
            
            # 加载应用程序状态
            self._load_application_state()
            
            self._is_initialized = True
            logger.info("应用程序服务初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"应用程序服务初始化失败: {e}")
            return False
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        directories = [
            self.settings.data_dir,
            self.settings.cache_dir,
            self.settings.log_dir,
            self.settings.data_dir / "projects",
            self.settings.data_dir / "documents",
            self.settings.data_dir / "characters",
            self.settings.data_dir / "templates",
            self.settings.data_dir / "backups",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"确保目录存在: {directory}")
    
    @safe_execute("事件订阅设置")
    def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        # 订阅项目相关事件（如果事件类可用）
        if ProjectCreatedEvent:
            self.event_bus.subscribe(ProjectCreatedEvent, self._on_project_created)
        if ProjectOpenedEvent:
            self.event_bus.subscribe(ProjectOpenedEvent, self._on_project_opened)
        if ProjectClosedEvent:
            self.event_bus.subscribe(ProjectClosedEvent, self._on_project_closed)

        logger.info("事件订阅设置完成")
    
    @safe_execute("应用程序状态加载")
    def _load_application_state(self) -> None:
        """加载应用程序状态"""
        state_file = self.settings.data_dir / "app_state.json"
        if not state_file.exists():
            logger.info("应用程序状态加载完成，当前项目: None")
            return

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # 验证状态数据格式
            if not isinstance(state, dict):
                logger.warning("应用程序状态文件格式无效")
                return

            project_id = state.get('current_project_id')
            if project_id and isinstance(project_id, str):
                self._current_project_id = project_id
                # 项目存在性验证将在项目服务中异步进行
                logger.info(f"应用程序状态加载完成，上次项目: {project_id}")
            else:
                logger.info("应用程序状态加载完成，当前项目: None")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"应用程序状态文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载应用程序状态失败: {e}")
    
    @safe_execute("应用程序状态保存")
    def _save_application_state(self) -> None:
        """保存应用程序状态"""
        try:
            state = {
                'current_project_id': self._current_project_id,
                'last_saved': datetime.now().isoformat(),
                'app_version': getattr(self.settings, 'app_version', '1.0.0'),
            }

            state_file = self.settings.data_dir / "app_state.json"

            # 确保目录存在
            state_file.parent.mkdir(parents=True, exist_ok=True)

            # 使用临时文件确保原子性写入
            temp_file = state_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # 验证JSON格式

                # 原子性替换
                temp_file.replace(state_file)

            except Exception:
                # 清理临时文件
                if temp_file.exists():
                    temp_file.unlink()
                raise

            logger.debug("应用程序状态保存完成")

        except Exception as e:
            logger.error(f"保存应用程序状态失败: {e}")
            raise
    
    async def _on_project_created(self, event) -> None:
        """处理项目创建事件"""
        logger.info(f"项目创建: {event.project_name} ({event.project_id})")
    
    async def _on_project_opened(self, event) -> None:
        """处理项目打开事件"""
        self._current_project_id = event.project_id
        self._save_application_state()
        logger.info(f"项目打开: {event.project_name} ({event.project_id})")
    
    async def _on_project_closed(self, event) -> None:
        """处理项目关闭事件"""
        if self._current_project_id == event.project_id:
            self._current_project_id = None
            self._save_application_state()
        logger.info(f"项目关闭: {event.project_name} ({event.project_id})")
    
    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._is_initialized
    
    @property
    def current_project_id(self) -> Optional[str]:
        """当前项目ID"""
        return self._current_project_id
    
    def get_data_directory(self) -> Path:
        """获取数据目录"""
        return self.settings.data_dir
    
    def get_cache_directory(self) -> Path:
        """获取缓存目录"""
        return self.settings.cache_dir
    
    def get_log_directory(self) -> Path:
        """获取日志目录"""
        return self.settings.log_dir
    
    def shutdown(self) -> None:
        """关闭应用程序服务"""
        try:
            logger.info("关闭应用程序服务...")
            
            # 保存应用程序状态
            self._save_application_state()
            
            # 清理资源
            self._cleanup_resources()
            
            self._is_initialized = False
            logger.info("应用程序服务关闭完成")
            
        except Exception as e:
            logger.error(f"关闭应用程序服务失败: {e}")
    
    @safe_execute("资源清理")
    def _cleanup_resources(self) -> None:
        """清理资源"""
        try:
            # 清理缓存
            cache_dir = self.settings.cache_dir
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    try:
                        if item.is_file() and item.suffix == '.tmp':
                            item.unlink()
                            logger.debug(f"清理临时文件: {item}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败 {item}: {e}")

            logger.info("资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")
    
    def get_application_info(self) -> dict:
        """获取应用程序信息"""
        return {
            "app_name": self.settings.app_name,
            "app_version": self.settings.app_version,
            "is_initialized": self._is_initialized,
            "current_project_id": self._current_project_id,
            "data_directory": str(self.settings.data_dir),
            "cache_directory": str(self.settings.cache_dir),
            "log_directory": str(self.settings.log_dir),
        }

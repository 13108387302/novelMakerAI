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
        """确保项目目录存在（现在由项目上下文管理）"""
        # 项目目录现在由 ProjectPaths 和 ensure_project_dirs 管理
        logger.info("项目目录由项目上下文管理，跳过应用级目录创建")
    
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

            # 统一文件操作进行原子性写入
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("app_state")
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(ops.save_json_atomic(state_file, state, create_backup=True))

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
        """清理资源（增强健壮性版本）"""
        cleanup_tasks = []

        try:
            # 1. 清理缓存目录
            cache_dir = self.settings.cache_dir
            if cache_dir and cache_dir.exists():
                cleanup_tasks.append(("缓存目录", self._cleanup_cache_directory, cache_dir))

            # 2. 清理临时文件
            temp_dirs = [
                self.settings.data_dir / "temp",
                Path.home() / ".novel_editor" / "temp"
            ]
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    cleanup_tasks.append(("临时目录", self._cleanup_temp_directory, temp_dir))

            # 3. 清理日志文件（保留最近7天）
            log_dir = self.settings.data_dir / "logs"
            if log_dir.exists():
                cleanup_tasks.append(("日志目录", self._cleanup_log_directory, log_dir))

            # 4. 清理缓存管理器
            try:
                from src.shared.utils.cache_manager import get_cache_manager
                cache_manager = get_cache_manager()
                cleanup_tasks.append(("缓存管理器", self._cleanup_cache_manager, cache_manager))
            except Exception as cache_error:
                logger.warning(f"获取缓存管理器失败: {cache_error}")

            # 执行清理任务
            success_count = 0
            for task_name, task_func, task_arg in cleanup_tasks:
                try:
                    task_func(task_arg)
                    success_count += 1
                    logger.debug(f"✅ {task_name}清理成功")
                except Exception as task_error:
                    logger.warning(f"❌ {task_name}清理失败: {task_error}")

            logger.info(f"资源清理完成: {success_count}/{len(cleanup_tasks)} 个任务成功")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")

    def _cleanup_cache_directory(self, cache_dir: Path) -> None:
        """清理缓存目录"""
        cleaned_count = 0
        for item in cache_dir.iterdir():
            try:
                if item.is_file():
                    # 清理临时文件和过期缓存
                    if item.suffix in ['.tmp', '.cache'] or 'temp' in item.name.lower():
                        item.unlink()
                        cleaned_count += 1
                elif item.is_dir() and item.name.startswith('temp_'):
                    # 清理临时目录
                    import shutil
                    shutil.rmtree(item)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"清理缓存项失败 {item}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个缓存项")

    def _cleanup_temp_directory(self, temp_dir: Path) -> None:
        """清理临时目录"""
        import time
        current_time = time.time()
        max_age = 24 * 3600  # 24小时
        cleaned_count = 0

        for item in temp_dir.iterdir():
            try:
                # 检查文件年龄
                if item.stat().st_mtime < current_time - max_age:
                    if item.is_file():
                        item.unlink()
                        cleaned_count += 1
                    elif item.is_dir():
                        import shutil
                        shutil.rmtree(item)
                        cleaned_count += 1
            except Exception as e:
                logger.warning(f"清理临时项失败 {item}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个临时项")

    def _cleanup_log_directory(self, log_dir: Path) -> None:
        """清理日志目录（保留最近7天）"""
        import time
        current_time = time.time()
        max_age = 7 * 24 * 3600  # 7天
        cleaned_count = 0

        for log_file in log_dir.glob('*.log*'):
            try:
                if log_file.stat().st_mtime < current_time - max_age:
                    log_file.unlink()
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"清理日志文件失败 {log_file}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个过期日志文件")

    def _cleanup_cache_manager(self, cache_manager) -> None:
        """清理缓存管理器"""
        try:
            stats = cache_manager.get_stats()
            logger.debug(f"缓存统计: {stats}")

            # 可以在这里添加缓存清理逻辑
            # 例如：清理过期缓存、压缩缓存等

        except Exception as e:
            logger.warning(f"清理缓存管理器失败: {e}")
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目设置热更新（Hot Reload）

监控项目配置目录下的配置文件变化，并在检测到外部改动时：
- 重新加载项目主配置（config.json -> Settings）
- 同步到 SettingsService 的用户设置
- 触发主题、语言应用
- 刷新 AI 编排服务的配置（provider、重试、流式等）

实现要点：
- 使用 watchdog 监听 .novel_editor 目录（仅监控目标文件）
- Debounce + 内容哈希，避免重复触发与自写入回环
- 在主线程应用 UI 相关变更（通过 Qt 单次定时器）
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Callable

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    _WATCHDOG_AVAILABLE = True
except Exception:
    # 降级为无操作实现
    FileSystemEventHandler = object  # type: ignore
    Observer = None  # type: ignore
    _WATCHDOG_AVAILABLE = False

# 懒导入Qt（避免在无GUI环境报错）
try:  # pragma: no cover
    from PyQt6.QtCore import QTimer
except Exception:  # pragma: no cover
    QTimer = None


@dataclass
class WatchTargets:
    config_dir: Path
    main_config_file: Path  # .novel_editor/config.json（Settings）
    user_config_file: Path  # .novel_editor/user_settings.json（SettingsService）


class _SettingsChangeHandler(FileSystemEventHandler):  # type: ignore
    def __init__(self, targets: WatchTargets, on_change: Callable[[Path], None]):
        super().__init__()
        self.targets = targets
        self.on_change = on_change

    def _is_target(self, src_path: str) -> bool:
        try:
            p = Path(src_path)
            return p.resolve() in {self.targets.main_config_file.resolve(), self.targets.user_config_file.resolve()}
        except Exception:
            return False

    # 合并处理不同事件类型
    def on_any_event(self, event):  # type: ignore
        if getattr(event, 'is_directory', False):
            return
        src = getattr(event, 'src_path', None)
        if not src:
            return
        if self._is_target(src):
            self.on_change(Path(src))


class ProjectSettingsHotReloader:
    def __init__(
        self,
        project_root: Path,
        apply_language: Optional[Callable[[str], None]] = None,
        apply_theme: Optional[Callable[[str], None]] = None,
        apply_ai_config: Optional[Callable[[], None]] = None,
    ):
        from src.shared.project_context import ProjectPaths, ensure_project_dirs
        pp = ProjectPaths(project_root)
        ensure_project_dirs(pp)

        config_dir = pp.config_dir
        self.targets = WatchTargets(
            config_dir=config_dir,
            main_config_file=pp.config_file,
            user_config_file=config_dir / 'user_settings.json'
        )

        self._observer: Optional[Observer] = None
        self._lock = threading.RLock()
        self._last_hash: Dict[str, str] = {}
        self._running = False

        # 应用回调
        self._apply_language = apply_language
        self._apply_theme = apply_theme
        self._apply_ai_config = apply_ai_config

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            if not _WATCHDOG_AVAILABLE:
                # 无 watchog 时降级为 no-op，不报错
                return
            handler = _SettingsChangeHandler(self.targets, self._handle_change)
            self._observer = Observer()
            self._observer.schedule(handler, str(self.targets.config_dir), recursive=False)
            self._observer.start()
            self._running = True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            try:
                if self._observer:
                    self._observer.stop()
                    self._observer.join(timeout=2.0)
            finally:
                self._observer = None
                self._running = False

    # 计算文件内容哈希，防抖用
    def _content_hash(self, p: Path) -> str:
        try:
            data = p.read_bytes()
            return hashlib.md5(data).hexdigest()
        except Exception:
            return ""

    def _handle_change(self, file_path: Path) -> None:
        # Debounce: 相同内容不触发
        h = self._content_hash(file_path)
        key = str(file_path.resolve())
        if h and self._last_hash.get(key) == h:
            return
        self._last_hash[key] = h

        # 在主线程应用（若Qt可用）
        def _apply():
            try:
                self._reload_and_apply()
            except Exception as e:
                from src.shared.utils.logger import get_logger
                get_logger(__name__).warning(f"应用热更新失败: {e}")

        if QTimer is not None:
            QTimer.singleShot(0, _apply)
        else:
            _apply()

    def _reload_and_apply(self) -> None:
        """从磁盘重载 Settings，并同步至 SettingsService 与依赖组件。"""
        from config.settings import reload_settings_for_project
        from src.shared.ioc.container import get_global_container
        from config.settings import Settings

        container = get_global_container()
        if not container:
            return

        # 读取当前项目根
        from src.shared.project_context import ProjectPaths
        project_paths = container.try_get(ProjectPaths)
        if not project_paths:
            return

        # 1) 重新加载 Settings（config.json）并更新容器实例
        new_settings = reload_settings_for_project(project_paths.root)
        try:
            container.register_instance(Settings, new_settings)
        except Exception:
            pass

        # 2) 同步到 SettingsService 的主配置并保存回用户设置
        try:
            from src.application.services.settings_service import SettingsService
            settings_service = container.try_get(SettingsService)
            if settings_service is not None:
                # 切换主配置引用
                settings_service.settings = new_settings
                # 从主配置同步用户设置（会做必要的映射/保存）
                settings_service.sync_from_main_config()
        except Exception:
            pass

        # 3) 应用界面主题/语言（如果提供回调）
        try:
            ui_lang = getattr(new_settings.ui, 'language', 'zh_CN')
            ui_theme = getattr(new_settings.ui, 'theme', 'dark')
            if self._apply_language:
                self._apply_language(ui_lang)
            if self._apply_theme:
                self._apply_theme(ui_theme)
        except Exception:
            pass

        # 4) 刷新 AI 编排服务配置
        try:
            if self._apply_ai_config:
                self._apply_ai_config()
        except Exception:
            pass


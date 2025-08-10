#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置服务

管理用户设置和应用配置
"""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger
from src.shared.config.base_config_manager import BaseConfigManager
from config.settings import Settings

logger = get_logger(__name__)


class SettingsService(BaseConfigManager):
    """
    设置服务

    管理用户设置和应用配置，提供设置的读取、保存和同步功能。
    支持设置迁移和默认值管理。

    实现方式：
    - 使用JSON文件存储用户设置
    - 提供设置的增删改查操作
    - 支持设置变更事件通知
    - 提供设置迁移和版本兼容性
    - 支持设置的导入导出功能

    Attributes:
        settings: 应用程序配置实例
        event_bus: 事件总线
        _user_settings: 用户设置字典
        _settings_file: 设置文件路径
    """

    def __init__(
        self,
        settings: Settings,
        event_bus: EventBus
    ):
        """
        初始化设置服务

        Args:
            settings: 应用程序配置实例
            event_bus: 事件总线
        """
        self.settings = settings
        self.event_bus = event_bus

        # 调用父类构造函数（使用项目内配置目录）
        from src.shared.project_context import ProjectPaths
        from src.shared.ioc.container import get_global_container
        container = get_global_container()
        if container:
            project_paths = container.try_get(ProjectPaths)
            if project_paths:
                super().__init__(project_paths.config_dir)
            else:
                raise RuntimeError("SettingsService需要项目上下文，但未找到ProjectPaths")
        else:
            raise RuntimeError("SettingsService需要全局容器，但未找到")

        # 迁移设置（添加缺失的字段）
        self._migrate_settings()

        # 从主配置同步设置
        self.sync_from_main_config()

    def get_config_file_name(self) -> str:
        """获取配置文件名"""
        return "user_settings.json"

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self._get_default_user_settings()

    def _load_user_settings(self) -> None:
        """加载用户设置（向后兼容）"""
        # 基类已经在构造函数中加载了配置
        pass

    def _save_user_settings(self) -> bool:
        """保存用户设置（向后兼容）"""
        return self.save()

    @property
    def _user_settings(self) -> Dict[str, Any]:
        """获取用户设置数据（向后兼容）"""
        return self.config_data

    @_user_settings.setter
    def _user_settings(self, value: Dict[str, Any]) -> None:
        """设置用户设置数据（向后兼容）"""
        self.config_data = value

    @property
    def _settings_file(self) -> Path:
        """获取设置文件路径（向后兼容）"""
        return self.config_file



    def _migrate_settings(self) -> None:
        """迁移设置（添加缺失的字段）"""
        try:
            default_settings = self._get_default_user_settings()
            settings_updated = False

            # 递归合并默认设置到用户设置
            def merge_settings(user_dict, default_dict):
                nonlocal settings_updated
                for key, default_value in default_dict.items():
                    if key not in user_dict:
                        user_dict[key] = default_value
                        settings_updated = True
                        logger.info(f"添加缺失的设置项: {key}")
                    elif isinstance(default_value, dict) and isinstance(user_dict[key], dict):
                        merge_settings(user_dict[key], default_value)

            # 使用config_data而不是_user_settings
            merge_settings(self.config_data, default_settings)

            # 如果有更新，保存设置
            if settings_updated:
                self._save_user_settings()
                logger.info("设置迁移完成，已保存更新")

        except Exception as e:
            logger.error(f"设置迁移失败: {e}")
    



    
    def _get_default_user_settings(self) -> Dict[str, Any]:
        """获取默认用户设置（基于config/settings.py的配置定义）"""
        # 使用config/settings.py中定义的默认值，确保一致性
        ui_settings = self.settings.ui
        ai_settings = self.settings.ai_service

        return {
            "ui": {
                "theme": ui_settings.theme,
                "language": ui_settings.language,
                "font_family": ui_settings.font_family,
                "font_size": ui_settings.font_size,
                "line_spacing": 1.5,  # 扩展配置
                "auto_save_interval": ui_settings.auto_save_interval,
                "show_word_count": True,
                "show_character_count": True,
                "show_reading_time": True,
                "enable_spell_check": True,
                "enable_grammar_check": True,
                "window_state": {
                    "maximized": False,
                    "width": ui_settings.window_width,
                    "height": ui_settings.window_height,
                    "x": 100,
                    "y": 100
                },
                "splitter_sizes": [300, 800, 350],
                "recent_projects_count": ui_settings.recent_projects_count,
                "last_opened_directory": "",
                "recent_directories": [],
                "window_geometry": "",
                "window_state": "",
                "dock_state": "",
                "auto_open_last_project": True,
                "last_project_id": "",
                "last_project_path": ""
            },
            "editor": {
                "tab_size": 4,
                "word_wrap": True,
                "show_line_numbers": False,
                "highlight_current_line": True,
                "auto_indent": True,
                "smart_quotes": True,
                "auto_complete": True,
                "vim_mode": False,
                "typewriter_mode": False,
                "focus_mode": False,
                "distraction_free": False
            },
            "ai": {
                "default_provider": ai_settings.default_provider,
                "auto_suggestions": True,
                "suggestion_delay": 2000,  # 毫秒
                "max_tokens": ai_settings.max_tokens,
                "temperature": ai_settings.temperature,
                "enable_continuation": True,
                "enable_dialogue_improvement": True,
                "enable_scene_expansion": True,
                "enable_style_analysis": True,
                "cache_responses": True,
                "show_confidence": True
            },
            "project": {
                "default_project_type": "novel",
                "default_target_word_count": 80000,
                "auto_backup": True,
                "backup_interval": 3600,  # 秒
                "backup_count": 5,
                "version_control": True,
                "export_format": "docx",
                "default_author": "",
                "default_genre": ""
            },
            "advanced": {
                "debug_mode": False,
                "log_level": "INFO",
                "performance_monitoring": False,
                "crash_reporting": True,
                "usage_analytics": True,
                "check_updates": True,
                "beta_features": False
            }
        }
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        return self.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """设置值"""
        try:
            # 获取旧值用于事件发布
            old_value = self.get(key)

            # 使用基类的set方法
            success = self.set(key, value, save_immediately=True)

            # 同步到主配置对象（如果是核心配置项）
            self._sync_to_main_config(key, value)

            if success:
                # 发布设置变更事件（线程安全方式）
                try:
                    from src.domain.events.ai_events import AIConfigurationChangedEvent
                    event = AIConfigurationChangedEvent(
                        setting_key=key,
                        old_value=old_value,
                        new_value=value
                    )

                    # 检查是否有运行的事件循环
                    try:
                        loop = asyncio.get_running_loop()
                        # 如果有事件循环，创建任务
                        asyncio.create_task(self.event_bus.publish_async(event))
                    except RuntimeError:
                        # 没有事件循环，使用同步方式或跳过事件发布
                        logger.debug(f"没有运行的事件循环，跳过事件发布: {key}")
                        pass

                except Exception as e:
                    logger.warning(f"发布设置变更事件失败: {e}")

                logger.info(f"设置更新成功: {key} = {value}")
                return True
            else:
                # 设置失败，直接返回False（回滚由底层配置管理负责，避免未定义变量）
                return False

        except Exception as e:
            logger.error(f"设置值失败: {key}, {e}")
            return False
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """获取UI设置"""
        return self.get_setting("ui", {})
    
    def get_editor_settings(self) -> Dict[str, Any]:
        """获取编辑器设置"""
        return self.get_setting("editor", {})
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """获取AI设置"""
        return self.get_setting("ai", {})
    
    def get_project_settings(self) -> Dict[str, Any]:
        """获取项目设置"""
        return self.get_setting("project", {})
    
    def update_ui_settings(self, updates: Dict[str, Any]) -> bool:
        """批量更新UI设置"""
        try:
            success_count = 0
            for key, value in updates.items():
                if self.set_setting(f"ui.{key}", value):
                    success_count += 1
            
            logger.info(f"UI设置批量更新: {success_count}/{len(updates)} 项成功")
            return success_count == len(updates)
            
        except Exception as e:
            logger.error(f"批量更新UI设置失败: {e}")
            return False
    
    def update_ai_settings(self, updates: Dict[str, Any]) -> bool:
        """批量更新AI设置"""
        try:
            success_count = 0
            for key, value in updates.items():
                if self.set_setting(f"ai.{key}", value):
                    success_count += 1
            
            logger.info(f"AI设置批量更新: {success_count}/{len(updates)} 项成功")
            return success_count == len(updates)
            
        except Exception as e:
            logger.error(f"批量更新AI设置失败: {e}")
            return False
    
    def reset_to_defaults(self, category: Optional[str] = None) -> bool:
        """重置为默认设置"""
        try:
            defaults = self._get_default_user_settings()
            
            if category:
                if category in defaults:
                    self._user_settings[category] = defaults[category]
                    logger.info(f"重置 {category} 设置为默认值")
                else:
                    logger.warning(f"未知的设置类别: {category}")
                    return False
            else:
                self._user_settings = defaults
                logger.info("重置所有设置为默认值")
            
            return self._save_user_settings()
            
        except Exception as e:
            logger.error(f"重置设置失败: {e}")
            return False
    
    def export_settings(self, export_path: Path) -> bool:
        """导出设置"""
        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                "version": "2.0",
                "exported_at": datetime.now().isoformat(),
                "settings": self._user_settings
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"设置导出成功: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出设置失败: {e}")
            return False
    
    def import_settings(self, import_path: Path) -> bool:
        """导入设置"""
        try:
            if not import_path.exists():
                logger.error(f"设置文件不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "settings" in import_data:
                # 备份当前设置
                backup_path = self._settings_file.with_suffix('.backup.json')
                self.export_settings(backup_path)
                
                # 导入新设置
                self._user_settings = import_data["settings"]
                success = self._save_user_settings()
                
                if success:
                    logger.info(f"设置导入成功: {import_path}")
                    return True
                else:
                    # 恢复备份
                    self._load_user_settings()
                    logger.error("设置导入失败，已恢复原设置")
                    return False
            else:
                logger.error("无效的设置文件格式")
                return False

        except Exception as e:
            logger.error(f"导入设置失败: {e}")
            return False

    def get_last_opened_directory(self) -> str:
        """获取上次打开的目录"""
        return self.get_setting("ui.last_opened_directory", "")

    def set_last_opened_directory(self, directory_path: str) -> bool:
        """设置上次打开的目录"""
        try:
            # 更新最近目录
            self.set_setting("ui.last_opened_directory", directory_path)

            # 更新最近目录列表
            recent_dirs = self.get_setting("ui.recent_directories", [])

            # 如果目录已存在，先移除
            if directory_path in recent_dirs:
                recent_dirs.remove(directory_path)

            # 添加到列表开头
            recent_dirs.insert(0, directory_path)

            # 限制最近目录数量（最多保存10个）
            max_recent = 10
            if len(recent_dirs) > max_recent:
                recent_dirs = recent_dirs[:max_recent]

            self.set_setting("ui.recent_directories", recent_dirs)

            logger.info(f"已更新最近打开目录: {directory_path}")
            return True

        except Exception as e:
            logger.error(f"设置最近目录失败: {e}")
            return False

    def get_recent_directories(self) -> list:
        """获取最近目录列表"""
        recent_dirs = self.get_setting("ui.recent_directories", [])

        # 过滤掉不存在的目录
        valid_dirs = []
        for dir_path in recent_dirs:
            try:
                if Path(dir_path).exists():
                    valid_dirs.append(dir_path)
            except Exception:
                # 忽略无效路径
                continue

        # 如果有目录被过滤掉，更新设置
        if len(valid_dirs) != len(recent_dirs):
            self.set_setting("ui.recent_directories", valid_dirs)

        return valid_dirs

    def clear_recent_directories(self) -> bool:
        """清空最近目录列表"""
        try:
            self.set_setting("ui.recent_directories", [])
            self.set_setting("ui.last_opened_directory", "")
            logger.info("已清空最近目录列表")
            return True
        except Exception as e:
            logger.error(f"清空最近目录失败: {e}")
            return False

    def get_auto_open_last_project(self) -> bool:
        """获取是否自动打开上次项目的设置"""
        return self.get_setting("ui.auto_open_last_project", True)

    def set_auto_open_last_project(self, enabled: bool) -> bool:
        """设置是否自动打开上次项目"""
        return self.set_setting("ui.auto_open_last_project", enabled)

    def get_last_project_info(self) -> tuple[str, str]:
        """获取上次打开的项目信息"""
        project_id = self.get_setting("ui.last_project_id", "")
        project_path = self.get_setting("ui.last_project_path", "")
        return project_id, project_path

    def set_last_project_info(self, project_id: str, project_path: str) -> bool:
        """设置上次打开的项目信息"""
        try:
            self.set_setting("ui.last_project_id", project_id)
            self.set_setting("ui.last_project_path", project_path)
            logger.info(f"已更新上次项目信息: {project_id} -> {project_path}")
            return True
        except Exception as e:
            logger.error(f"设置上次项目信息失败: {e}")
            return False

    def clear_last_project_info(self) -> bool:
        """清空上次项目信息"""
        try:
            self.set_setting("ui.last_project_id", "")
            self.set_setting("ui.last_project_path", "")
            logger.info("已清空上次项目信息")
            return True
        except Exception as e:
            logger.error(f"清空上次项目信息失败: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置"""
        return self._user_settings.copy()
    
    def validate_settings(self) -> Dict[str, Any]:
        """验证设置"""
        errors = []
        warnings = []
        
        try:
            # 验证UI设置
            ui_settings = self.get_ui_settings()
            if ui_settings.get("font_size", 12) < 8 or ui_settings.get("font_size", 12) > 24:
                warnings.append("字体大小超出推荐范围 (8-24)")
            
            # 验证AI设置
            ai_settings = self.get_ai_settings()
            if ai_settings.get("temperature", 0.7) < 0 or ai_settings.get("temperature", 0.7) > 2:
                errors.append("AI温度参数超出有效范围 (0-2)")
            
            # 验证项目设置
            project_settings = self.get_project_settings()
            if project_settings.get("default_target_word_count", 80000) < 1000:
                warnings.append("默认目标字数过小")
            
            logger.info(f"设置验证完成: {len(errors)} 个错误, {len(warnings)} 个警告")
            
        except Exception as e:
            errors.append(f"设置验证失败: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    # 窗口几何相关方法
    def get_window_geometry(self) -> str:
        """获取窗口几何信息"""
        return self.get_setting("ui.window_geometry", "")

    def save_window_geometry(self, geometry: str) -> bool:
        """保存窗口几何信息"""
        return self.set_setting("ui.window_geometry", geometry)

    def set_window_geometry(self, geometry) -> bool:
        """设置窗口几何信息（兼容性方法）"""
        if hasattr(geometry, 'toBase64'):
            # QByteArray对象
            geometry_str = geometry.toBase64().data().decode()
        elif isinstance(geometry, bytes):
            # bytes对象
            import base64
            geometry_str = base64.b64encode(geometry).decode()
        else:
            # 字符串
            geometry_str = str(geometry)
        return self.set_setting("ui.window_geometry", geometry_str)

    def get_window_state(self) -> str:
        """获取窗口状态"""
        return self.get_setting("ui.window_state", "")

    def save_window_state(self, state: str) -> bool:
        """保存窗口状态"""
        return self.set_setting("ui.window_state", state)

    def get_dock_state(self) -> str:
        """获取停靠窗口状态"""
        return self.get_setting("ui.dock_state", "")

    def save_dock_state(self, state: str) -> bool:
        """保存停靠窗口状态"""
        return self.set_setting("ui.dock_state", state)

    def set_dock_state(self, state) -> bool:
        """设置停靠窗口状态（兼容性方法）"""
        if hasattr(state, 'toBase64'):
            # QByteArray对象
            state_str = state.toBase64().data().decode()
        elif isinstance(state, bytes):
            # bytes对象
            import base64
            state_str = base64.b64encode(state).decode()
        else:
            # 字符串
            state_str = str(state)
        return self.set_setting("ui.dock_state", state_str)

    def _sync_to_main_config(self, key: str, value: Any) -> None:
        """同步设置到主配置对象"""
        try:
            # 同步核心UI配置到主配置对象
            if key.startswith("ui."):
                ui_key = key[3:]  # 移除"ui."前缀
                if hasattr(self.settings.ui, ui_key):
                    setattr(self.settings.ui, ui_key, value)
                    logger.debug(f"已同步UI配置到主配置: {ui_key} = {value}")

            # 同步AI配置到主配置对象
            elif key.startswith("ai."):
                ai_key = key[3:]  # 移除"ai."前缀
                # 映射用户设置键到主配置键
                key_mapping = {
                    "default_provider": "default_provider",
                    "max_tokens": "max_tokens",
                    "temperature": "temperature"
                }
                if ai_key in key_mapping and hasattr(self.settings.ai_service, key_mapping[ai_key]):
                    setattr(self.settings.ai_service, key_mapping[ai_key], value)
                    logger.debug(f"已同步AI配置到主配置: {ai_key} = {value}")

        except Exception as e:
            logger.warning(f"同步配置到主配置失败: {key}, {e}")

    def sync_from_main_config(self) -> bool:
        """从主配置对象同步设置"""
        try:
            # 同步UI配置
            ui_settings = self.settings.ui
            self.set("ui.theme", ui_settings.theme, save_immediately=False)
            self.set("ui.font_family", ui_settings.font_family, save_immediately=False)
            self.set("ui.font_size", ui_settings.font_size, save_immediately=False)
            self.set("ui.auto_save_interval", ui_settings.auto_save_interval, save_immediately=False)
            self.set("ui.recent_projects_count", ui_settings.recent_projects_count, save_immediately=False)

            # 同步AI配置
            ai_settings = self.settings.ai_service
            self.set("ai.default_provider", ai_settings.default_provider, save_immediately=False)
            self.set("ai.max_tokens", ai_settings.max_tokens, save_immediately=False)
            self.set("ai.temperature", ai_settings.temperature, save_immediately=False)
            self.set("ai.timeout", ai_settings.timeout, save_immediately=False)
            self.set("ai.enable_streaming", ai_settings.enable_streaming, save_immediately=False)

            # 同步API密钥（如果已配置）
            if ai_settings.openai_api_key:
                self.set("ai.openai_api_key", ai_settings.openai_api_key, save_immediately=False)
            if ai_settings.deepseek_api_key:
                self.set("ai.deepseek_api_key", ai_settings.deepseek_api_key, save_immediately=False)

            # 同步其他AI配置
            self.set("ai.openai_base_url", ai_settings.openai_base_url, save_immediately=False)
            self.set("ai.openai_model", ai_settings.openai_model, save_immediately=False)
            self.set("ai.deepseek_base_url", ai_settings.deepseek_base_url, save_immediately=False)
            self.set("ai.deepseek_model", ai_settings.deepseek_model, save_immediately=False)

            # 保存所有更改
            success = self.save()
            if success:
                logger.info("已从主配置同步用户设置")
            return success

        except Exception as e:
            logger.error(f"从主配置同步设置失败: {e}")
            return False

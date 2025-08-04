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
from config.settings import Settings

logger = get_logger(__name__)


class SettingsService:
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
        self._user_settings: Dict[str, Any] = {}
        self._settings_file = self.settings.data_dir / "user_settings.json"

        # 加载用户设置
        self._load_user_settings()

        # 迁移设置（添加缺失的字段）
        self._migrate_settings()
    
    def _load_user_settings(self) -> None:
        """加载用户设置"""
        try:
            if self._settings_file.exists():
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 验证数据格式
                if not isinstance(data, dict):
                    raise ValueError("设置文件格式无效：根对象必须是字典")

                self._user_settings = data
                logger.info("用户设置加载成功")
            else:
                # 创建默认设置
                self._user_settings = self._get_default_user_settings()
                self._save_user_settings()
                logger.info("创建默认用户设置")

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            logger.error(f"用户设置文件格式错误: {e}")
            # 尝试修复损坏的设置文件
            self._repair_corrupted_settings()
        except Exception as e:
            logger.error(f"加载用户设置失败: {e}")
            # 尝试修复损坏的设置文件
            self._repair_corrupted_settings()

    def _repair_corrupted_settings(self) -> None:
        """修复损坏的设置文件"""
        try:
            logger.info("尝试修复损坏的设置文件...")

            # 备份损坏的文件
            if self._settings_file.exists():
                backup_file = self._settings_file.with_suffix('.corrupted.bak')
                self._settings_file.rename(backup_file)
                logger.info(f"已备份损坏的设置文件到: {backup_file}")

            # 创建新的默认设置
            self._user_settings = self._get_default_user_settings()
            success = self._save_user_settings()

            if success:
                logger.info("设置文件修复成功，已创建新的默认设置")
            else:
                logger.error("设置文件修复失败")

        except Exception as e:
            logger.error(f"修复设置文件时发生错误: {e}")
            # 最后的备用方案：使用内存中的默认设置
            self._user_settings = self._get_default_user_settings()

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

            merge_settings(self._user_settings, default_settings)

            # 如果有更新，保存设置
            if settings_updated:
                self._save_user_settings()
                logger.info("设置迁移完成，已保存更新")

        except Exception as e:
            logger.error(f"设置迁移失败: {e}")
    
    def _save_user_settings(self) -> bool:
        """保存用户设置"""
        temp_file = None
        try:
            # 验证设置数据的JSON兼容性
            self._validate_settings_for_json()

            self._settings_file.parent.mkdir(parents=True, exist_ok=True)

            # 先写入临时文件，然后重命名，确保原子性操作
            temp_file = self._settings_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._user_settings, f, indent=2, ensure_ascii=False)

            # 验证写入的文件是否有效
            with open(temp_file, 'r', encoding='utf-8') as f:
                json.load(f)  # 验证JSON格式

            # 重命名临时文件为正式文件
            temp_file.replace(self._settings_file)

            logger.debug("用户设置保存成功")
            return True

        except Exception as e:
            logger.error(f"保存用户设置失败: {e}")
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False

    def _validate_settings_for_json(self):
        """验证设置数据是否可以序列化为JSON"""
        def check_value(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    check_value(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    check_value(value, f"{path}[{i}]")
            elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
                # 检测不可序列化的对象
                raise TypeError(f"不可序列化的对象类型 {type(obj)} 在路径: {path}")

        check_value(self._user_settings)
    
    def _get_default_user_settings(self) -> Dict[str, Any]:
        """获取默认用户设置"""
        return {
            "ui": {
                "theme": "light",
                "language": "zh_CN",
                "font_family": "Microsoft YaHei UI",
                "font_size": 12,
                "line_spacing": 1.5,
                "auto_save_interval": 30,
                "show_word_count": True,
                "show_character_count": True,
                "show_reading_time": True,
                "enable_spell_check": True,
                "enable_grammar_check": True,
                "window_state": {
                    "maximized": False,
                    "width": 1400,
                    "height": 900,
                    "x": 100,
                    "y": 100
                },
                "splitter_sizes": [300, 800, 350],
                "recent_projects_count": 10,
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
                "default_provider": "openai",
                "auto_suggestions": True,
                "suggestion_delay": 2000,  # 毫秒
                "max_tokens": 2000,
                "temperature": 0.7,
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
        try:
            keys = key.split('.')
            value = self._user_settings
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"获取设置失败: {key}, {e}")
            return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """设置值"""
        try:
            keys = key.split('.')
            current = self._user_settings
            
            # 导航到父级字典
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # 设置值
            old_value = current.get(keys[-1])
            current[keys[-1]] = value
            
            # 保存设置
            success = self._save_user_settings()
            
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
                # 回滚更改
                if old_value is not None:
                    current[keys[-1]] = old_value
                else:
                    current.pop(keys[-1], None)
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

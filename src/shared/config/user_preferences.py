#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户偏好设置管理器

负责管理用户的个人偏好设置，包括界面选项、提醒设置等。
使用JSON文件存储，支持默认值和类型验证。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from src.shared.utils.logger import get_logger
from .base_config_manager import BaseConfigManager
from src.shared.constants import (
    DEFAULT_FONT_SIZE, DEFAULT_AUTO_SAVE_INTERVAL, DEFAULT_TAB_WIDTH,
    DEFAULT_AI_CREATIVITY_LEVEL, DEFAULT_AI_SUGGESTION_DELAY, DEFAULT_THEME
)

logger = get_logger(__name__)

# 用户偏好设置常量
USER_PREFERENCES_FILE = "user_preferences.json"


class UserPreferences(BaseConfigManager):
    """用户偏好设置管理器"""

    def __init__(self, config_dir: Path):
        """
        初始化用户偏好设置管理器

        Args:
            config_dir: 配置文件目录（必须提供，通常为项目内路径）
        """
        # 调用父类构造函数
        super().__init__(config_dir)

    def get_config_file_name(self) -> str:
        """获取配置文件名"""
        return USER_PREFERENCES_FILE

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "ui": {
                "show_welcome_dialog": True,  # 是否显示欢迎对话框
                "theme": DEFAULT_THEME,       # 主题
                "font_size": DEFAULT_FONT_SIZE, # 字体大小
                "auto_save_interval": DEFAULT_AUTO_SAVE_INTERVAL, # 自动保存间隔（秒）
                "show_line_numbers": True,    # 显示行号
                "word_wrap": True,            # 自动换行
            },
            "editor": {
                "tab_size": DEFAULT_TAB_WIDTH, # Tab大小
                "insert_spaces": True,        # 使用空格代替Tab
                "highlight_current_line": True, # 高亮当前行
                "show_whitespace": False,     # 显示空白字符
            },
            "ai": {
                "auto_suggestions": True,     # 自动建议
                "suggestion_delay": DEFAULT_AI_SUGGESTION_DELAY, # 建议延迟（毫秒）
                "max_tokens": 1000,           # 最大token数
                "temperature": DEFAULT_AI_CREATIVITY_LEVEL, # 温度参数
            },
            "notifications": {
                "show_save_notifications": True,    # 显示保存通知
                "show_ai_notifications": True,      # 显示AI通知
                "show_error_notifications": True,   # 显示错误通知
            },
            "startup": {
                "restore_last_session": True,       # 恢复上次会话
                "show_startup_tips": True,          # 显示启动提示
                "check_updates": True,              # 检查更新
            }
        }

    # 便捷访问方法（保持向后兼容）
    @property
    def preferences(self) -> Dict[str, Any]:
        """获取配置数据（向后兼容）"""
        return self.config_data

    def save_preferences(self) -> bool:
        """保存用户偏好设置（向后兼容）"""
        return self.save()

    def get_ui_preference(self, key: str, default: Any = None) -> Any:
        """获取UI偏好设置"""
        return self.get(f"ui.{key}", default)

    def set_ui_preference(self, key: str, value: Any) -> bool:
        """设置UI偏好设置"""
        return self.set(f"ui.{key}", value)

    def get_editor_preference(self, key: str, default: Any = None) -> Any:
        """获取编辑器偏好设置"""
        return self.get(f"editor.{key}", default)

    def set_editor_preference(self, key: str, value: Any) -> bool:
        """设置编辑器偏好设置"""
        return self.set(f"editor.{key}", value)

    def get_ai_preference(self, key: str, default: Any = None) -> Any:
        """获取AI偏好设置"""
        return self.get(f"ai.{key}", default)

    def set_ai_preference(self, key: str, value: Any) -> bool:
        """设置AI偏好设置"""
        return self.set(f"ai.{key}", value)

    def should_show_welcome_dialog(self) -> bool:
        """是否应该显示欢迎对话框"""
        return self.get_ui_preference("show_welcome_dialog", True)

    def set_show_welcome_dialog(self, show: bool) -> bool:
        """设置是否显示欢迎对话框"""
        return self.set("ui.show_welcome_dialog", show, save_immediately=True)

    def export_preferences(self, file_path: str) -> bool:
        """导出偏好设置到文件（向后兼容）"""
        return self.export_config(Path(file_path))

    def import_preferences(self, file_path: str) -> bool:
        """从文件导入偏好设置（向后兼容）"""
        return self.import_config(Path(file_path))


# 全局实例
_user_preferences = None

def get_user_preferences(config_dir: Path) -> UserPreferences:
    """获取用户偏好设置实例（基于项目配置目录）"""
    global _user_preferences
    if _user_preferences is None:
        _user_preferences = UserPreferences(config_dir)
    return _user_preferences

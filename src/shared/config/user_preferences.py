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

logger = get_logger(__name__)


class UserPreferences:
    """用户偏好设置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化用户偏好设置管理器
        
        Args:
            config_dir: 配置文件目录，如果为None则使用默认目录
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 使用用户主目录下的应用配置目录
            self.config_dir = Path.home() / ".ai_novel_editor"
        
        self.config_file = self.config_dir / "user_preferences.json"
        
        # 默认设置
        self.default_preferences = {
            "ui": {
                "show_welcome_dialog": True,  # 是否显示欢迎对话框
                "theme": "light",             # 主题
                "font_size": 12,              # 字体大小
                "auto_save_interval": 300,    # 自动保存间隔（秒）
                "show_line_numbers": True,    # 显示行号
                "word_wrap": True,            # 自动换行
            },
            "editor": {
                "tab_size": 4,                # Tab大小
                "insert_spaces": True,        # 使用空格代替Tab
                "highlight_current_line": True, # 高亮当前行
                "show_whitespace": False,     # 显示空白字符
            },
            "ai": {
                "auto_suggestions": True,     # 自动建议
                "suggestion_delay": 1000,     # 建议延迟（毫秒）
                "max_tokens": 1000,           # 最大token数
                "temperature": 0.7,           # 温度参数
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
        
        self.preferences = {}
        self._load_preferences()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建配置目录失败: {e}")
            raise
    
    def _load_preferences(self):
        """加载用户偏好设置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_prefs = json.load(f)
                
                # 合并默认设置和用户设置
                self.preferences = self._merge_preferences(self.default_preferences, loaded_prefs)
                logger.debug("用户偏好设置加载成功")
            else:
                # 使用默认设置
                self.preferences = self.default_preferences.copy()
                logger.debug("使用默认偏好设置")
                
        except Exception as e:
            logger.error(f"加载用户偏好设置失败: {e}")
            # 使用默认设置
            self.preferences = self.default_preferences.copy()
    
    def _merge_preferences(self, default: Dict, user: Dict) -> Dict:
        """递归合并默认设置和用户设置"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_preferences(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_preferences(self):
        """保存用户偏好设置"""
        try:
            self._ensure_config_dir()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2, ensure_ascii=False)
            
            logger.debug("用户偏好设置保存成功")
            
        except Exception as e:
            logger.error(f"保存用户偏好设置失败: {e}")
            raise
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取偏好设置值
        
        Args:
            key_path: 设置键路径，使用点号分隔，如 "ui.show_welcome_dialog"
            default: 默认值
            
        Returns:
            设置值
        """
        try:
            keys = key_path.split('.')
            value = self.preferences
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"获取偏好设置失败: {key_path}, {e}")
            return default
    
    def set(self, key_path: str, value: Any):
        """
        设置偏好设置值
        
        Args:
            key_path: 设置键路径，使用点号分隔，如 "ui.show_welcome_dialog"
            value: 设置值
        """
        try:
            keys = key_path.split('.')
            current = self.preferences
            
            # 导航到父级字典
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # 设置值
            current[keys[-1]] = value
            
            logger.debug(f"偏好设置已更新: {key_path} = {value}")
            
        except Exception as e:
            logger.error(f"设置偏好设置失败: {key_path}, {e}")
            raise
    
    def get_ui_preference(self, key: str, default: Any = None) -> Any:
        """获取UI偏好设置"""
        return self.get(f"ui.{key}", default)
    
    def set_ui_preference(self, key: str, value: Any):
        """设置UI偏好设置"""
        self.set(f"ui.{key}", value)
    
    def get_editor_preference(self, key: str, default: Any = None) -> Any:
        """获取编辑器偏好设置"""
        return self.get(f"editor.{key}", default)
    
    def set_editor_preference(self, key: str, value: Any):
        """设置编辑器偏好设置"""
        self.set(f"editor.{key}", value)
    
    def get_ai_preference(self, key: str, default: Any = None) -> Any:
        """获取AI偏好设置"""
        return self.get(f"ai.{key}", default)
    
    def set_ai_preference(self, key: str, value: Any):
        """设置AI偏好设置"""
        self.set(f"ai.{key}", value)
    
    def should_show_welcome_dialog(self) -> bool:
        """是否应该显示欢迎对话框"""
        return self.get_ui_preference("show_welcome_dialog", True)
    
    def set_show_welcome_dialog(self, show: bool):
        """设置是否显示欢迎对话框"""
        self.set_ui_preference("show_welcome_dialog", show)
        # 立即保存设置
        try:
            self.save_preferences()
        except Exception as e:
            logger.error(f"保存欢迎对话框设置失败: {e}")
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        self.preferences = self.default_preferences.copy()
        self.save_preferences()
        logger.info("用户偏好设置已重置为默认值")
    
    def export_preferences(self, file_path: str):
        """导出偏好设置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2, ensure_ascii=False)
            logger.info(f"偏好设置已导出到: {file_path}")
        except Exception as e:
            logger.error(f"导出偏好设置失败: {e}")
            raise
    
    def import_preferences(self, file_path: str):
        """从文件导入偏好设置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_prefs = json.load(f)
            
            # 合并导入的设置
            self.preferences = self._merge_preferences(self.default_preferences, imported_prefs)
            self.save_preferences()
            logger.info(f"偏好设置已从文件导入: {file_path}")
        except Exception as e:
            logger.error(f"导入偏好设置失败: {e}")
            raise


# 全局实例
_user_preferences = None

def get_user_preferences() -> UserPreferences:
    """获取全局用户偏好设置实例"""
    global _user_preferences
    if _user_preferences is None:
        _user_preferences = UserPreferences()
    return _user_preferences

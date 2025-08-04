#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目设置

定义项目的配置设置
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ProjectSettings:
    """项目设置"""
    # 自动保存设置
    auto_save_enabled: bool = True
    auto_save_interval: int = 30  # 秒
    
    # 备份设置
    backup_enabled: bool = True
    backup_interval: int = 3600   # 秒
    backup_count: int = 10        # 保留备份数量
    
    # 编辑器设置
    editor_font_family: str = "Microsoft YaHei"
    editor_font_size: int = 12
    editor_line_spacing: float = 1.2
    editor_word_wrap: bool = True
    editor_show_line_numbers: bool = True
    editor_highlight_current_line: bool = True
    editor_tab_width: int = 4
    editor_auto_indent: bool = True
    
    # 主题设置
    theme_name: str = "default"
    dark_mode: bool = False
    
    # AI设置
    ai_enabled: bool = True
    ai_auto_suggestions: bool = True
    ai_suggestion_delay: int = 1000  # 毫秒
    ai_model_preference: str = "default"
    ai_creativity_level: float = 0.7  # 0.0-1.0
    ai_response_length: str = "medium"  # short, medium, long
    
    # 写作辅助设置
    spell_check_enabled: bool = True
    grammar_check_enabled: bool = True
    auto_complete_enabled: bool = True
    word_count_target_visible: bool = True
    progress_tracking_enabled: bool = True
    
    # 导出设置
    default_export_format: str = "docx"
    export_include_metadata: bool = True
    export_include_statistics: bool = False
    
    # 版本控制设置
    version_control_enabled: bool = False
    auto_commit_enabled: bool = False
    auto_commit_interval: int = 1800  # 秒
    
    # 协作设置
    collaboration_enabled: bool = False
    share_statistics: bool = False
    allow_comments: bool = True
    
    # 自定义设置
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def update_ai_settings(self, **kwargs) -> None:
        """更新AI设置"""
        ai_fields = {
            'ai_enabled', 'ai_auto_suggestions', 'ai_suggestion_delay',
            'ai_model_preference', 'ai_creativity_level', 'ai_response_length'
        }
        
        for key, value in kwargs.items():
            if key in ai_fields and hasattr(self, key):
                setattr(self, key, value)
    
    def update_editor_settings(self, **kwargs) -> None:
        """更新编辑器设置"""
        editor_fields = {
            'editor_font_family', 'editor_font_size', 'editor_line_spacing',
            'editor_word_wrap', 'editor_show_line_numbers', 'editor_highlight_current_line',
            'editor_tab_width', 'editor_auto_indent'
        }
        
        for key, value in kwargs.items():
            if key in editor_fields and hasattr(self, key):
                setattr(self, key, value)
    
    def update_backup_settings(self, **kwargs) -> None:
        """更新备份设置"""
        backup_fields = {
            'backup_enabled', 'backup_interval', 'backup_count'
        }
        
        for key, value in kwargs.items():
            if key in backup_fields and hasattr(self, key):
                setattr(self, key, value)
    
    def set_custom_setting(self, key: str, value: Any) -> None:
        """设置自定义设置"""
        if key and key.strip():
            self.custom_settings[key.strip()] = value
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """获取自定义设置"""
        return self.custom_settings.get(key.strip(), default)
    
    def remove_custom_setting(self, key: str) -> None:
        """移除自定义设置"""
        self.custom_settings.pop(key.strip(), None)
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """获取AI相关设置"""
        return {
            "ai_enabled": self.ai_enabled,
            "ai_auto_suggestions": self.ai_auto_suggestions,
            "ai_suggestion_delay": self.ai_suggestion_delay,
            "ai_model_preference": self.ai_model_preference,
            "ai_creativity_level": self.ai_creativity_level,
            "ai_response_length": self.ai_response_length
        }
    
    def get_editor_settings(self) -> Dict[str, Any]:
        """获取编辑器相关设置"""
        return {
            "editor_font_family": self.editor_font_family,
            "editor_font_size": self.editor_font_size,
            "editor_line_spacing": self.editor_line_spacing,
            "editor_word_wrap": self.editor_word_wrap,
            "editor_show_line_numbers": self.editor_show_line_numbers,
            "editor_highlight_current_line": self.editor_highlight_current_line,
            "editor_tab_width": self.editor_tab_width,
            "editor_auto_indent": self.editor_auto_indent
        }
    
    def get_backup_settings(self) -> Dict[str, Any]:
        """获取备份相关设置"""
        return {
            "backup_enabled": self.backup_enabled,
            "backup_interval": self.backup_interval,
            "backup_count": self.backup_count
        }
    
    def validate(self) -> list[str]:
        """验证设置"""
        errors = []
        
        # 验证时间间隔
        if self.auto_save_interval < 5:
            errors.append("自动保存间隔不能少于5秒")
        elif self.auto_save_interval > 3600:
            errors.append("自动保存间隔不能超过1小时")
        
        if self.backup_interval < 60:
            errors.append("备份间隔不能少于1分钟")
        elif self.backup_interval > 86400:
            errors.append("备份间隔不能超过1天")
        
        # 验证备份数量
        if self.backup_count < 1:
            errors.append("备份数量不能少于1个")
        elif self.backup_count > 100:
            errors.append("备份数量不能超过100个")
        
        # 验证字体大小
        if self.editor_font_size < 8:
            errors.append("编辑器字体大小不能小于8")
        elif self.editor_font_size > 72:
            errors.append("编辑器字体大小不能大于72")
        
        # 验证行间距
        if self.editor_line_spacing < 0.5:
            errors.append("编辑器行间距不能小于0.5")
        elif self.editor_line_spacing > 5.0:
            errors.append("编辑器行间距不能大于5.0")
        
        # 验证Tab宽度
        if self.editor_tab_width < 1:
            errors.append("Tab宽度不能小于1")
        elif self.editor_tab_width > 16:
            errors.append("Tab宽度不能大于16")
        
        # 验证AI创造力水平
        if not 0.0 <= self.ai_creativity_level <= 1.0:
            errors.append("AI创造力水平必须在0.0-1.0之间")
        
        # 验证AI建议延迟
        if self.ai_suggestion_delay < 100:
            errors.append("AI建议延迟不能少于100毫秒")
        elif self.ai_suggestion_delay > 10000:
            errors.append("AI建议延迟不能超过10秒")
        
        return errors
    
    def reset_to_defaults(self) -> None:
        """重置为默认设置"""
        default_settings = ProjectSettings()
        
        # 复制所有默认值，但保留自定义设置
        custom_backup = self.custom_settings.copy()
        
        for field_name, field_value in default_settings.__dict__.items():
            if field_name != 'custom_settings':
                setattr(self, field_name, field_value)
        
        self.custom_settings = custom_backup
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if key == 'custom_settings':
                result[key] = value.copy()
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectSettings':
        """从字典创建设置"""
        # 创建默认设置
        settings = cls()
        
        # 更新字段值
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        return settings
    
    def copy(self) -> 'ProjectSettings':
        """创建副本"""
        return ProjectSettings.from_dict(self.to_dict())
    
    def merge_with(self, other: 'ProjectSettings', prefer_other: bool = True) -> 'ProjectSettings':
        """与另一个设置合并"""
        if prefer_other:
            merged = other.copy()
            # 合并自定义设置
            merged.custom_settings.update(self.custom_settings)
        else:
            merged = self.copy()
            # 合并自定义设置
            merged.custom_settings.update(other.custom_settings)
        
        return merged

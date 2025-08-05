#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快捷键管理器

管理应用程序的快捷键绑定
"""

from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence, QAction

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ShortcutCategory(Enum):
    """快捷键分类"""
    GENERAL = "general"
    FILE = "file"
    EDIT = "edit"
    VIEW = "view"
    AI = "ai"
    TOOLS = "tools"
    HELP = "help"


@dataclass
class ShortcutInfo:
    """快捷键信息"""
    key: str
    sequence: str
    description: str
    category: ShortcutCategory
    action: Optional[Callable] = None
    enabled: bool = True


class ShortcutManager(QObject):
    """快捷键管理器"""
    
    # 信号定义
    shortcut_triggered = pyqtSignal(str)  # shortcut_key
    shortcut_changed = pyqtSignal(str, str)  # shortcut_key, new_sequence
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.parent_widget = parent
        self._shortcuts: Dict[str, ShortcutInfo] = {}
        self._qt_shortcuts: Dict[str, QShortcut] = {}
        self._actions: Dict[str, QAction] = {}
        
        # 初始化默认快捷键
        self._init_default_shortcuts()
        
        logger.debug("快捷键管理器初始化完成")
    
    def _init_default_shortcuts(self):
        """初始化默认快捷键"""
        default_shortcuts = [
            # 文件操作
            ShortcutInfo("new_project", "Ctrl+N", "新建项目", ShortcutCategory.FILE),
            ShortcutInfo("open_project", "Ctrl+O", "打开项目", ShortcutCategory.FILE),
            ShortcutInfo("save", "Ctrl+S", "保存", ShortcutCategory.FILE),
            ShortcutInfo("save_as", "Ctrl+Shift+S", "另存为", ShortcutCategory.FILE),
            ShortcutInfo("import", "Ctrl+I", "导入", ShortcutCategory.FILE),
            ShortcutInfo("export", "Ctrl+E", "导出", ShortcutCategory.FILE),
            ShortcutInfo("quit", "Ctrl+Q", "退出", ShortcutCategory.FILE),
            
            # 编辑操作
            ShortcutInfo("undo", "Ctrl+Z", "撤销", ShortcutCategory.EDIT),
            ShortcutInfo("redo", "Ctrl+Y", "重做", ShortcutCategory.EDIT),
            ShortcutInfo("cut", "Ctrl+X", "剪切", ShortcutCategory.EDIT),
            ShortcutInfo("copy", "Ctrl+C", "复制", ShortcutCategory.EDIT),
            ShortcutInfo("paste", "Ctrl+V", "粘贴", ShortcutCategory.EDIT),
            ShortcutInfo("select_all", "Ctrl+A", "全选", ShortcutCategory.EDIT),
            ShortcutInfo("find", "Ctrl+F", "查找", ShortcutCategory.EDIT),
            ShortcutInfo("replace", "Ctrl+H", "替换", ShortcutCategory.EDIT),
            ShortcutInfo("find_next", "F3", "查找下一个", ShortcutCategory.EDIT),
            ShortcutInfo("find_previous", "Shift+F3", "查找上一个", ShortcutCategory.EDIT),
            
            # 视图操作
            ShortcutInfo("toggle_project_tree", "Ctrl+1", "切换项目树", ShortcutCategory.VIEW),
            ShortcutInfo("toggle_ai_panel", "Ctrl+2", "切换AI面板", ShortcutCategory.VIEW),
            ShortcutInfo("toggle_status_panel", "Ctrl+3", "切换状态面板", ShortcutCategory.VIEW),
            ShortcutInfo("fullscreen", "F11", "全屏", ShortcutCategory.VIEW),
            ShortcutInfo("zoom_in", "Ctrl+=", "放大", ShortcutCategory.VIEW),
            ShortcutInfo("zoom_out", "Ctrl+-", "缩小", ShortcutCategory.VIEW),
            ShortcutInfo("zoom_reset", "Ctrl+0", "重置缩放", ShortcutCategory.VIEW),
            
            # AI操作
            ShortcutInfo("ai_continue", "Ctrl+Shift+C", "AI续写", ShortcutCategory.AI),
            ShortcutInfo("ai_improve", "Ctrl+Shift+I", "AI优化", ShortcutCategory.AI),
            ShortcutInfo("ai_dialogue", "Ctrl+Shift+D", "对话优化", ShortcutCategory.AI),
            ShortcutInfo("ai_scene", "Ctrl+Shift+S", "场景扩展", ShortcutCategory.AI),
            ShortcutInfo("ai_analyze", "Ctrl+Shift+A", "风格分析", ShortcutCategory.AI),
            
            # 工具操作
            ShortcutInfo("word_count", "Ctrl+Shift+W", "字数统计", ShortcutCategory.TOOLS),
            ShortcutInfo("template_manager", "Ctrl+Shift+T", "模板管理器", ShortcutCategory.TOOLS),
            ShortcutInfo("plugin_manager", "Ctrl+Shift+P", "插件管理器", ShortcutCategory.TOOLS),
            ShortcutInfo("settings", "Ctrl+,", "设置", ShortcutCategory.TOOLS),
            ShortcutInfo("new_document", "Ctrl+Shift+N", "新建文档", ShortcutCategory.TOOLS),
            ShortcutInfo("close_document", "Ctrl+W", "关闭文档", ShortcutCategory.TOOLS),
            ShortcutInfo("next_document", "Ctrl+Tab", "下一个文档", ShortcutCategory.TOOLS),
            ShortcutInfo("previous_document", "Ctrl+Shift+Tab", "上一个文档", ShortcutCategory.TOOLS),
            ShortcutInfo("toggle_syntax", "Ctrl+Shift+H", "切换语法高亮", ShortcutCategory.TOOLS),
            
            # 帮助操作
            ShortcutInfo("help", "F1", "帮助", ShortcutCategory.HELP),
            ShortcutInfo("about", "Ctrl+Shift+?", "关于", ShortcutCategory.HELP),
            ShortcutInfo("shortcuts", "Ctrl+?", "快捷键列表", ShortcutCategory.HELP),
        ]
        
        for shortcut in default_shortcuts:
            self._shortcuts[shortcut.key] = shortcut
    
    def register_shortcut(self, key: str, sequence: str, description: str, 
                         category: ShortcutCategory, action: Callable = None) -> bool:
        """注册快捷键"""
        try:
            shortcut_info = ShortcutInfo(key, sequence, description, category, action)
            self._shortcuts[key] = shortcut_info
            
            if self.parent_widget and action:
                self._create_qt_shortcut(key, sequence, action)
            
            logger.debug(f"快捷键已注册: {key} ({sequence})")
            return True
            
        except Exception as e:
            logger.error(f"注册快捷键失败: {key}, {e}")
            return False
    
    def _create_qt_shortcut(self, key: str, sequence: str, action: Callable):
        """创建Qt快捷键"""
        try:
            if key in self._qt_shortcuts:
                # 移除旧的快捷键
                self._qt_shortcuts[key].deleteLater()
                del self._qt_shortcuts[key]
            
            # 创建新的快捷键
            shortcut = QShortcut(QKeySequence(sequence), self.parent_widget)
            shortcut.activated.connect(lambda: self._on_shortcut_activated(key, action))
            
            self._qt_shortcuts[key] = shortcut
            
        except Exception as e:
            logger.error(f"创建Qt快捷键失败: {key}, {e}")
    
    def _on_shortcut_activated(self, key: str, action: Callable):
        """快捷键激活处理"""
        try:
            logger.debug(f"快捷键激活: {key}")
            
            # 发出信号
            self.shortcut_triggered.emit(key)
            
            # 执行动作
            if action:
                action()
                
        except Exception as e:
            logger.error(f"快捷键激活处理失败: {key}, {e}")
    
    def bind_action(self, key: str, action: Callable) -> bool:
        """绑定动作到快捷键"""
        try:
            if key not in self._shortcuts:
                logger.warning(f"快捷键不存在: {key}")
                return False
            
            shortcut_info = self._shortcuts[key]
            shortcut_info.action = action
            
            if self.parent_widget:
                self._create_qt_shortcut(key, shortcut_info.sequence, action)
            
            logger.debug(f"动作已绑定到快捷键: {key}")
            return True
            
        except Exception as e:
            logger.error(f"绑定动作失败: {key}, {e}")
            return False
    
    def change_shortcut(self, key: str, new_sequence: str) -> bool:
        """修改快捷键序列"""
        try:
            if key not in self._shortcuts:
                logger.warning(f"快捷键不存在: {key}")
                return False
            
            old_sequence = self._shortcuts[key].sequence
            self._shortcuts[key].sequence = new_sequence
            
            # 重新创建Qt快捷键
            if self.parent_widget and self._shortcuts[key].action:
                self._create_qt_shortcut(key, new_sequence, self._shortcuts[key].action)
            
            # 发出变更信号
            self.shortcut_changed.emit(key, new_sequence)
            
            logger.info(f"快捷键已修改: {key} {old_sequence} -> {new_sequence}")
            return True
            
        except Exception as e:
            logger.error(f"修改快捷键失败: {key}, {e}")
            return False
    
    def enable_shortcut(self, key: str, enabled: bool = True) -> bool:
        """启用/禁用快捷键"""
        try:
            if key not in self._shortcuts:
                logger.warning(f"快捷键不存在: {key}")
                return False
            
            self._shortcuts[key].enabled = enabled
            
            if key in self._qt_shortcuts:
                self._qt_shortcuts[key].setEnabled(enabled)
            
            logger.debug(f"快捷键状态已更改: {key} -> {'启用' if enabled else '禁用'}")
            return True
            
        except Exception as e:
            logger.error(f"修改快捷键状态失败: {key}, {e}")
            return False
    
    def get_shortcut(self, key: str) -> Optional[ShortcutInfo]:
        """获取快捷键信息"""
        return self._shortcuts.get(key)
    
    def get_shortcuts_by_category(self, category: ShortcutCategory) -> List[ShortcutInfo]:
        """按分类获取快捷键"""
        return [info for info in self._shortcuts.values() if info.category == category]
    
    def get_all_shortcuts(self) -> Dict[str, ShortcutInfo]:
        """获取所有快捷键"""
        return self._shortcuts.copy()
    
    def find_conflicts(self, sequence: str, exclude_key: str = None) -> List[str]:
        """查找快捷键冲突"""
        conflicts = []
        
        for key, info in self._shortcuts.items():
            if key != exclude_key and info.sequence == sequence and info.enabled:
                conflicts.append(key)
        
        return conflicts
    
    def export_shortcuts(self, file_path: str) -> bool:
        """导出快捷键配置"""
        try:
            import json
            
            export_data = {
                "version": "1.0",
                "shortcuts": {}
            }
            
            for key, info in self._shortcuts.items():
                export_data["shortcuts"][key] = {
                    "sequence": info.sequence,
                    "description": info.description,
                    "category": info.category.value,
                    "enabled": info.enabled
                }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"快捷键配置已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出快捷键配置失败: {e}")
            return False
    
    def import_shortcuts(self, file_path: str) -> bool:
        """导入快捷键配置"""
        try:
            import json
            
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "shortcuts" not in import_data:
                logger.error("无效的快捷键配置文件")
                return False
            
            for key, data in import_data["shortcuts"].items():
                if key in self._shortcuts:
                    self._shortcuts[key].sequence = data.get("sequence", self._shortcuts[key].sequence)
                    self._shortcuts[key].enabled = data.get("enabled", True)
                    
                    # 重新创建Qt快捷键
                    if self.parent_widget and self._shortcuts[key].action:
                        self._create_qt_shortcut(key, self._shortcuts[key].sequence, self._shortcuts[key].action)
            
            logger.info(f"快捷键配置已导入: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导入快捷键配置失败: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """重置为默认快捷键"""
        try:
            # 清除现有的Qt快捷键
            for shortcut in self._qt_shortcuts.values():
                shortcut.deleteLater()
            self._qt_shortcuts.clear()
            
            # 重新初始化默认快捷键
            self._shortcuts.clear()
            self._init_default_shortcuts()
            
            # 重新绑定已有的动作
            for key, info in self._shortcuts.items():
                if self.parent_widget and info.action:
                    self._create_qt_shortcut(key, info.sequence, info.action)
            
            logger.info("快捷键已重置为默认配置")
            return True
            
        except Exception as e:
            logger.error(f"重置快捷键失败: {e}")
            return False
    
    def get_shortcut_text(self, key: str) -> str:
        """获取快捷键显示文本"""
        if key in self._shortcuts:
            return self._shortcuts[key].sequence
        return ""
    
    def is_shortcut_enabled(self, key: str) -> bool:
        """检查快捷键是否启用"""
        if key in self._shortcuts:
            return self._shortcuts[key].enabled
        return False
    
    def get_categories(self) -> List[ShortcutCategory]:
        """获取所有分类"""
        return list(ShortcutCategory)
    
    def search_shortcuts(self, query: str) -> List[ShortcutInfo]:
        """搜索快捷键"""
        query = query.lower()
        results = []
        
        for info in self._shortcuts.values():
            if (query in info.description.lower() or 
                query in info.sequence.lower() or 
                query in info.key.lower()):
                results.append(info)
        
        return results

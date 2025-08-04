#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户体验优化服务

提供拖拽支持、快捷键管理、无障碍访问等用户体验优化功能
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QKeySequence, QAction, QDrag
from PyQt6.QtWidgets import QWidget, QApplication

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ShortcutConfig:
    """
    快捷键配置数据类

    定义应用程序快捷键的配置信息。

    Attributes:
        action_name: 动作名称
        key_sequence: 按键序列
        description: 快捷键描述
        category: 快捷键分类
        is_global: 是否为全局快捷键
        is_enabled: 是否启用
    """
    action_name: str
    key_sequence: str
    description: str
    category: str = "general"
    is_global: bool = False
    is_enabled: bool = True


@dataclass
class AccessibilityConfig:
    """
    无障碍配置数据类

    定义应用程序的无障碍访问配置选项。

    Attributes:
        high_contrast: 高对比度模式
        large_fonts: 大字体模式
        screen_reader_support: 屏幕阅读器支持
        keyboard_navigation: 键盘导航
        focus_indicators: 焦点指示器
        reduced_motion: 减少动画效果
        voice_commands: 语音命令支持
    """
    high_contrast: bool = False
    large_fonts: bool = False
    screen_reader_support: bool = False
    keyboard_navigation: bool = True
    focus_indicators: bool = True
    reduced_motion: bool = False
    voice_commands: bool = False


@dataclass
class DragDropConfig:
    """
    拖拽配置数据类

    定义拖拽操作的配置选项。

    Attributes:
        enabled: 是否启用拖拽
        auto_scroll: 自动滚动
        show_preview: 显示预览
        snap_to_grid: 对齐到网格
        animation_duration: 动画持续时间
    """
    enabled: bool = True
    auto_scroll: bool = True
    visual_feedback: bool = True
    drop_zones: List[str] = field(default_factory=list)
    supported_formats: List[str] = field(default_factory=lambda: ["text/plain", "application/json"])


class UXService(QObject):
    """用户体验优化服务"""
    
    # 信号
    shortcut_triggered = pyqtSignal(str)  # 快捷键触发
    drag_started = pyqtSignal(str, object)  # 拖拽开始
    drop_completed = pyqtSignal(str, object, object)  # 拖拽完成
    accessibility_changed = pyqtSignal(str, bool)  # 无障碍设置改变
    
    def __init__(self, data_dir: Path):
        super().__init__()
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置文件
        self.shortcuts_config_file = data_dir / "shortcuts.json"
        self.accessibility_config_file = data_dir / "accessibility.json"
        self.dragdrop_config_file = data_dir / "dragdrop.json"
        
        # 配置
        self.shortcuts: Dict[str, ShortcutConfig] = {}
        self.accessibility = AccessibilityConfig()
        self.dragdrop = DragDropConfig()
        
        # 快捷键动作映射
        self._shortcut_actions: Dict[str, QAction] = {}
        self._shortcut_callbacks: Dict[str, Callable] = {}
        
        # 拖拽状态
        self._drag_data = None
        self._drop_zones: Dict[str, QWidget] = {}
        
        # 无障碍功能
        self._focus_timer = QTimer()
        self._focus_timer.timeout.connect(self._update_focus_indicators)
        
        self._load_configurations()
        self._setup_default_shortcuts()
        
        logger.debug("用户体验优化服务初始化完成")
    
    def _load_configurations(self):
        """加载配置"""
        # 加载快捷键配置
        try:
            if self.shortcuts_config_file.exists():
                with open(self.shortcuts_config_file, 'r', encoding='utf-8') as f:
                    shortcuts_data = json.load(f)

                # 验证数据格式
                if not isinstance(shortcuts_data, dict):
                    logger.warning("快捷键配置文件格式无效")
                    return

                for action_name, config_data in shortcuts_data.items():
                    try:
                        if isinstance(config_data, dict):
                            self.shortcuts[action_name] = ShortcutConfig(**config_data)
                    except TypeError as e:
                        logger.warning(f"跳过无效的快捷键配置 {action_name}: {e}")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"快捷键配置文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载快捷键配置失败: {e}")

        # 加载无障碍配置
        try:
            if self.accessibility_config_file.exists():
                with open(self.accessibility_config_file, 'r', encoding='utf-8') as f:
                    accessibility_data = json.load(f)

                # 验证数据格式
                if isinstance(accessibility_data, dict):
                    try:
                        self.accessibility = AccessibilityConfig(**accessibility_data)
                    except TypeError as e:
                        logger.warning(f"无障碍配置数据格式不兼容: {e}")
                        self.accessibility = AccessibilityConfig()
                else:
                    logger.warning("无障碍配置文件格式无效")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"无障碍配置文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载无障碍配置失败: {e}")

        # 加载拖拽配置
        try:
            if self.dragdrop_config_file.exists():
                with open(self.dragdrop_config_file, 'r', encoding='utf-8') as f:
                    dragdrop_data = json.load(f)

                # 验证数据格式
                if isinstance(dragdrop_data, dict):
                    try:
                        self.dragdrop = DragDropConfig(**dragdrop_data)
                    except TypeError as e:
                        logger.warning(f"拖拽配置数据格式不兼容: {e}")
                        self.dragdrop = DragDropConfig()
                else:
                    logger.warning("拖拽配置文件格式无效")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"拖拽配置文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载拖拽配置失败: {e}")
    
    def _save_configurations(self):
        """保存配置"""
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 保存快捷键配置
        try:
            shortcuts_data = {
                name: asdict(config)
                for name, config in self.shortcuts.items()
            }

            temp_file = self.shortcuts_config_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(shortcuts_data, f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)

                temp_file.replace(self.shortcuts_config_file)

            except Exception:
                if temp_file.exists():
                    temp_file.unlink()
                raise

        except Exception as e:
            logger.error(f"保存快捷键配置失败: {e}")

        # 保存无障碍配置
        try:
            temp_file = self.accessibility_config_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(self.accessibility), f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)

                temp_file.replace(self.accessibility_config_file)

            except Exception:
                if temp_file.exists():
                    temp_file.unlink()
                raise

        except Exception as e:
            logger.error(f"保存无障碍配置失败: {e}")

        # 保存拖拽配置
        try:
            temp_file = self.dragdrop_config_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(self.dragdrop), f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)

                temp_file.replace(self.dragdrop_config_file)

            except Exception:
                if temp_file.exists():
                    temp_file.unlink()
                raise

        except Exception as e:
            logger.error(f"保存拖拽配置失败: {e}")
    
    def _setup_default_shortcuts(self):
        """设置默认快捷键"""
        default_shortcuts = [
            ShortcutConfig("new_project", "Ctrl+N", "新建项目", "project"),
            ShortcutConfig("open_project", "Ctrl+O", "打开项目", "project"),
            ShortcutConfig("save_project", "Ctrl+S", "保存项目", "project"),
            ShortcutConfig("save_as", "Ctrl+Shift+S", "另存为", "project"),
            ShortcutConfig("new_document", "Ctrl+Alt+N", "新建文档", "document"),
            ShortcutConfig("save_document", "Ctrl+D", "保存文档", "document"),
            ShortcutConfig("find", "Ctrl+F", "查找", "edit"),
            ShortcutConfig("replace", "Ctrl+H", "替换", "edit"),
            ShortcutConfig("undo", "Ctrl+Z", "撤销", "edit"),
            ShortcutConfig("redo", "Ctrl+Y", "重做", "edit"),
            ShortcutConfig("copy", "Ctrl+C", "复制", "edit"),
            ShortcutConfig("cut", "Ctrl+X", "剪切", "edit"),
            ShortcutConfig("paste", "Ctrl+V", "粘贴", "edit"),
            ShortcutConfig("select_all", "Ctrl+A", "全选", "edit"),
            ShortcutConfig("zoom_in", "Ctrl++", "放大", "view"),
            ShortcutConfig("zoom_out", "Ctrl+-", "缩小", "view"),
            ShortcutConfig("zoom_reset", "Ctrl+0", "重置缩放", "view"),
            ShortcutConfig("toggle_fullscreen", "F11", "切换全屏", "view"),
            ShortcutConfig("show_ai_panel", "Ctrl+Shift+A", "显示AI面板", "ai"),
            ShortcutConfig("quick_ai_assist", "Ctrl+Space", "快速AI辅助", "ai"),
        ]
        
        for shortcut in default_shortcuts:
            if shortcut.action_name not in self.shortcuts:
                self.shortcuts[shortcut.action_name] = shortcut
    
    def register_shortcut(self, action_name: str, callback: Callable, parent_widget: QWidget = None):
        """注册快捷键"""
        try:
            if action_name not in self.shortcuts:
                logger.warning(f"未找到快捷键配置: {action_name}")
                return
            
            config = self.shortcuts[action_name]
            if not config.is_enabled:
                return
            
            # 创建QAction
            action = QAction(parent_widget or QApplication.instance())
            action.setShortcut(QKeySequence(config.key_sequence))
            action.triggered.connect(lambda: self._handle_shortcut_triggered(action_name))
            
            # 添加到父组件
            if parent_widget:
                parent_widget.addAction(action)
            
            self._shortcut_actions[action_name] = action
            self._shortcut_callbacks[action_name] = callback
            
            logger.debug(f"快捷键已注册: {action_name} ({config.key_sequence})")
            
        except Exception as e:
            logger.error(f"注册快捷键失败: {action_name}, {e}")
    
    def _handle_shortcut_triggered(self, action_name: str):
        """处理快捷键触发"""
        try:
            if action_name in self._shortcut_callbacks:
                callback = self._shortcut_callbacks[action_name]
                callback()
                self.shortcut_triggered.emit(action_name)
                logger.debug(f"快捷键触发: {action_name}")
        except Exception as e:
            logger.error(f"处理快捷键失败: {action_name}, {e}")
    
    def update_shortcut(self, action_name: str, key_sequence: str):
        """更新快捷键"""
        try:
            if action_name in self.shortcuts:
                self.shortcuts[action_name].key_sequence = key_sequence
                
                # 更新已注册的动作
                if action_name in self._shortcut_actions:
                    action = self._shortcut_actions[action_name]
                    action.setShortcut(QKeySequence(key_sequence))
                
                self._save_configurations()
                logger.info(f"快捷键已更新: {action_name} -> {key_sequence}")
        except Exception as e:
            logger.error(f"更新快捷键失败: {action_name}, {e}")
    
    def enable_drag_drop(self, widget: QWidget, zone_name: str):
        """启用拖拽功能"""
        try:
            if not self.dragdrop.enabled:
                return
            
            widget.setAcceptDrops(True)
            self._drop_zones[zone_name] = widget
            
            # 重写拖拽事件处理方法
            original_drag_enter = widget.dragEnterEvent
            original_drop = widget.dropEvent
            original_drag_move = widget.dragMoveEvent
            
            def drag_enter_event(event):
                if self._is_supported_format(event.mimeData()):
                    event.acceptProposedAction()
                    if self.dragdrop.visual_feedback:
                        widget.setStyleSheet("border: 2px dashed #007ACC;")
                else:
                    event.ignore()
            
            def drop_event(event):
                if self._is_supported_format(event.mimeData()):
                    data = self._extract_drop_data(event.mimeData())
                    self.drop_completed.emit(zone_name, data, event.pos())
                    event.acceptProposedAction()
                    
                    if self.dragdrop.visual_feedback:
                        widget.setStyleSheet("")
                else:
                    event.ignore()
            
            def drag_move_event(event):
                if self._is_supported_format(event.mimeData()):
                    event.acceptProposedAction()
                else:
                    event.ignore()
            
            widget.dragEnterEvent = drag_enter_event
            widget.dropEvent = drop_event
            widget.dragMoveEvent = drag_move_event
            
            logger.debug(f"拖拽功能已启用: {zone_name}")
            
        except Exception as e:
            logger.error(f"启用拖拽功能失败: {zone_name}, {e}")
    
    def start_drag(self, widget: QWidget, data: Any, drag_type: str = "text"):
        """开始拖拽"""
        try:
            if not self.dragdrop.enabled:
                return
            
            drag = QDrag(widget)
            mime_data = QMimeData()
            
            if drag_type == "text":
                mime_data.setText(str(data))
            elif drag_type == "json":
                mime_data.setData("application/json", json.dumps(data).encode())
            
            self._drag_data = data
            self.drag_started.emit(drag_type, data)
            
            # 执行拖拽
            drop_action = drag.exec()
            
            logger.debug(f"拖拽开始: {drag_type}")
            
        except Exception as e:
            logger.error(f"开始拖拽失败: {e}")
    
    def _is_supported_format(self, mime_data: QMimeData) -> bool:
        """检查是否支持的格式"""
        for format_type in self.dragdrop.supported_formats:
            if mime_data.hasFormat(format_type):
                return True
        return False
    
    def _extract_drop_data(self, mime_data: QMimeData) -> Any:
        """提取拖拽数据"""
        if mime_data.hasText():
            return mime_data.text()
        elif mime_data.hasFormat("application/json"):
            data = mime_data.data("application/json").data().decode()
            return json.loads(data)
        return None
    
    def update_accessibility_setting(self, setting: str, value: bool):
        """更新无障碍设置"""
        try:
            if hasattr(self.accessibility, setting):
                setattr(self.accessibility, setting, value)
                self._save_configurations()
                self.accessibility_changed.emit(setting, value)
                
                # 应用设置
                self._apply_accessibility_setting(setting, value)
                
                logger.info(f"无障碍设置已更新: {setting} = {value}")
        except Exception as e:
            logger.error(f"更新无障碍设置失败: {setting}, {e}")
    
    def _apply_accessibility_setting(self, setting: str, value: bool):
        """应用无障碍设置"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            if setting == "high_contrast":
                if value:
                    app.setStyleSheet("""
                        QWidget { background-color: black; color: white; }
                        QLineEdit, QTextEdit { background-color: #333; color: white; border: 1px solid white; }
                        QPushButton { background-color: #555; color: white; border: 1px solid white; }
                    """)
                else:
                    app.setStyleSheet("")
            
            elif setting == "large_fonts":
                font = app.font()
                if value:
                    font.setPointSize(font.pointSize() + 2)
                else:
                    font.setPointSize(max(8, font.pointSize() - 2))
                app.setFont(font)
            
            elif setting == "focus_indicators":
                if value:
                    self._focus_timer.start(100)  # 每100ms更新一次焦点指示器
                else:
                    self._focus_timer.stop()
            
        except Exception as e:
            logger.error(f"应用无障碍设置失败: {setting}, {e}")
    
    def _update_focus_indicators(self):
        """更新焦点指示器"""
        try:
            app = QApplication.instance()
            if app and self.accessibility.focus_indicators:
                focused_widget = app.focusWidget()
                if focused_widget:
                    # 添加焦点边框
                    focused_widget.setStyleSheet(
                        focused_widget.styleSheet() + 
                        "border: 2px solid #007ACC; border-radius: 2px;"
                    )
        except Exception as e:
            logger.error(f"更新焦点指示器失败: {e}")
    
    def get_shortcuts_by_category(self, category: str = None) -> Dict[str, ShortcutConfig]:
        """按类别获取快捷键"""
        if category:
            return {
                name: config for name, config in self.shortcuts.items()
                if config.category == category
            }
        return self.shortcuts.copy()
    
    def export_shortcuts(self, file_path: Path):
        """导出快捷键配置"""
        try:
            shortcuts_data = {
                name: asdict(config) 
                for name, config in self.shortcuts.items()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(shortcuts_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"快捷键配置已导出: {file_path}")
            
        except Exception as e:
            logger.error(f"导出快捷键配置失败: {e}")
    
    def import_shortcuts(self, file_path: Path):
        """导入快捷键配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                shortcuts_data = json.load(f)
            
            for name, config_data in shortcuts_data.items():
                self.shortcuts[name] = ShortcutConfig(**config_data)
            
            self._save_configurations()
            logger.info(f"快捷键配置已导入: {file_path}")
            
        except Exception as e:
            logger.error(f"导入快捷键配置失败: {e}")
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        try:
            self.shortcuts.clear()
            self._setup_default_shortcuts()
            self.accessibility = AccessibilityConfig()
            self.dragdrop = DragDropConfig()
            
            self._save_configurations()
            logger.info("设置已重置为默认值")
            
        except Exception as e:
            logger.error(f"重置设置失败: {e}")
    
    def get_ux_report(self) -> Dict[str, Any]:
        """获取用户体验报告"""
        return {
            "shortcuts": {
                "total": len(self.shortcuts),
                "enabled": sum(1 for config in self.shortcuts.values() if config.is_enabled),
                "categories": list(set(config.category for config in self.shortcuts.values()))
            },
            "accessibility": asdict(self.accessibility),
            "drag_drop": asdict(self.dragdrop),
            "active_drop_zones": list(self._drop_zones.keys())
        }

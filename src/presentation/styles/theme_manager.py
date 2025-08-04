#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题管理器

管理应用程序的主题和样式
"""

from enum import Enum
from typing import Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPalette, QColor

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeType(Enum):
    """主题类型"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class ColorScheme:
    """颜色方案"""
    
    def __init__(self, name: str, colors: Dict[str, str]):
        self.name = name
        self.colors = colors
    
    def get_color(self, key: str, default: str = "#000000") -> str:
        """获取颜色"""
        return self.colors.get(key, default)


class ThemeManager(QObject):
    """主题管理器"""
    
    # 信号定义
    theme_changed = pyqtSignal(str)  # theme_name
    
    def __init__(self):
        super().__init__()
        self._current_theme = ThemeType.DARK
        self._color_schemes = {}
        self._custom_styles = {}
        
        # 初始化内置主题
        self._init_builtin_themes()
        
        logger.debug("主题管理器初始化完成")
    
    def _init_builtin_themes(self):
        """初始化内置主题"""
        # 浅色主题
        light_colors = {
            # 主要颜色
            "primary": "#2196F3",
            "primary_dark": "#1976D2",
            "primary_light": "#BBDEFB",
            "secondary": "#FF9800",
            "secondary_dark": "#F57C00",
            "secondary_light": "#FFE0B2",
            
            # 状态颜色
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "info": "#2196F3",
            
            # 背景颜色
            "background": "#FFFFFF",
            "background_secondary": "#F5F6FA",
            "background_tertiary": "#F8F9FA",
            "surface": "#FFFFFF",
            "surface_variant": "#F5F5F5",
            
            # 文本颜色 - 增强对比度
            "text_primary": "#1a1a1a",
            "text_secondary": "#4a4a4a",
            "text_disabled": "#8a8a8a",
            "text_hint": "#6a6a6a",
            
            # 边框颜色
            "border": "#DEE2E6",
            "border_light": "#E9ECEF",
            "border_dark": "#CED4DA",
            "divider": "#E0E0E0",
            
            # 阴影
            "shadow": "rgba(0, 0, 0, 0.1)",
            "shadow_light": "rgba(0, 0, 0, 0.05)",
            "shadow_dark": "rgba(0, 0, 0, 0.2)",
            
            # 特殊颜色
            "accent": "#E91E63",
            "highlight": "#FFF3E0",
            "selection": "#E3F2FD",
            "hover": "#F5F5F5"
        }
        
        # 深色主题
        dark_colors = {
            # 主要颜色
            "primary": "#64B5F6",
            "primary_dark": "#1976D2",
            "primary_light": "#E3F2FD",
            "secondary": "#FFB74D",
            "secondary_dark": "#F57C00",
            "secondary_light": "#FFF3E0",
            
            # 状态颜色
            "success": "#66BB6A",
            "warning": "#FFB74D",
            "error": "#EF5350",
            "info": "#64B5F6",
            
            # 背景颜色 - 优化深色主题
            "background": "#1a1a1a",
            "background_secondary": "#2d2d2d",
            "background_tertiary": "#3a3a3a",
            "surface": "#2d2d2d",
            "surface_variant": "#3a3a3a",
            
            # 文本颜色 - 优化对比度和舒适度
            "text_primary": "#e8e8e8",
            "text_secondary": "#b8b8b8",
            "text_disabled": "#888888",
            "text_hint": "#a0a0a0",
            
            # 边框颜色 - 更柔和的边框
            "border": "#4a4a4a",
            "border_light": "#5a5a5a",
            "border_dark": "#3a3a3a",
            "divider": "#4a4a4a",
            
            # 阴影
            "shadow": "rgba(0, 0, 0, 0.3)",
            "shadow_light": "rgba(0, 0, 0, 0.2)",
            "shadow_dark": "rgba(0, 0, 0, 0.5)",
            
            # 特殊颜色
            "accent": "#F48FB1",
            "highlight": "#3E2723",
            "selection": "#1565C0",
            "hover": "#424242"
        }
        
        # 注册主题
        self._color_schemes[ThemeType.LIGHT.value] = ColorScheme("浅色主题", light_colors)
        self._color_schemes[ThemeType.DARK.value] = ColorScheme("深色主题", dark_colors)
    
    def get_current_theme(self) -> ThemeType:
        """获取当前主题"""
        return self._current_theme
    
    def set_theme(self, theme: ThemeType) -> bool:
        """设置主题"""
        try:
            if theme == self._current_theme:
                return True

            # 应用主题
            success = self._apply_theme(theme)

            if success:
                self._current_theme = theme
                self.theme_changed.emit(theme.value)
                logger.info(f"主题已切换: {theme.value}")
                return True
            else:
                logger.error(f"切换主题失败: {theme.value}")
                return False

        except Exception as e:
            logger.error(f"设置主题失败: {e}")
            return False

    def apply_theme(self, theme_name: str) -> bool:
        """应用主题（兼容性方法）"""
        try:
            # 将字符串转换为ThemeType
            if isinstance(theme_name, str):
                theme_type = ThemeType(theme_name)
            else:
                theme_type = theme_name
            return self.set_theme(theme_type)
        except ValueError:
            logger.error(f"未知的主题名称: {theme_name}")
            return False
    
    def _apply_theme(self, theme: ThemeType) -> bool:
        """应用主题"""
        try:
            # 获取颜色方案
            color_scheme = self._color_schemes.get(theme.value)
            if not color_scheme:
                logger.error(f"未找到主题: {theme.value}")
                return False
            
            # 生成样式表
            stylesheet = self._generate_stylesheet(color_scheme)
            
            # 应用到应用程序
            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)
                
                # 设置调色板
                self._set_palette(color_scheme)
            
            return True
            
        except Exception as e:
            logger.error(f"应用主题失败: {e}")
            return False
    
    def _generate_stylesheet(self, color_scheme: ColorScheme) -> str:
        """生成样式表"""
        colors = color_scheme.colors
        
        stylesheet = f"""
        /* 全局样式 */
        QWidget {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
            font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
            font-size: 11pt;
        }}
        
        /* 主窗口 */
        QMainWindow {{
            background-color: {colors['background_secondary']};
        }}
        
        /* 菜单栏 */
        QMenuBar {{
            background-color: {colors['surface']};
            border-bottom: 1px solid {colors['border']};
            padding: 4px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['hover']};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {colors['primary_light']};
        }}
        
        /* 菜单 */
        QMenu {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 16px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {colors['primary']};
            color: white;
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {colors['border']};
            margin: 4px 8px;
        }}
        
        /* 工具栏 */
        QToolBar {{
            background-color: {colors['surface']};
            border-bottom: 1px solid {colors['border']};
            spacing: 4px;
            padding: 4px;
        }}
        
        QToolBar QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 2px;
        }}
        
        QToolBar QToolButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['border']};
        }}
        
        QToolBar QToolButton:pressed {{
            background-color: {colors['primary_light']};
        }}
        
        /* 状态栏 */
        QStatusBar {{
            background-color: {colors['surface']};
            border-top: 1px solid {colors['border']};
            color: {colors['text_secondary']};
        }}
        
        /* 按钮 */
        QPushButton {{
            background-color: {colors['primary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {colors['primary_dark']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['primary_dark']};
            padding-top: 9px;
            padding-bottom: 7px;
        }}
        
        QPushButton:disabled {{
            background-color: {colors['text_disabled']};
            color: {colors['text_hint']};
        }}
        
        /* 输入框 */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 8px 12px;
            selection-background-color: {colors['selection']};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors['primary']};
            outline: none;
        }}
        
        /* 标签页 */
        QTabWidget::pane {{
            border: 1px solid {colors['border']};
            border-radius: 6px;
            background-color: {colors['surface']};
        }}
        
        QTabBar::tab {{
            background-color: {colors['background_tertiary']};
            border: 1px solid {colors['border']};
            border-bottom: none;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['surface']};
            border-bottom: 1px solid {colors['surface']};
            color: {colors['primary']};
            font-weight: bold;
        }}
        
        QTabBar::tab:hover {{
            background-color: {colors['hover']};
        }}
        
        /* 分割器 */
        QSplitter::handle {{
            background-color: {colors['border']};
            width: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {colors['primary']};
        }}
        
        /* 滚动条 */
        QScrollBar:vertical {{
            background-color: {colors['background_tertiary']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors['text_disabled']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['text_secondary']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        
        /* 进度条 */
        QProgressBar {{
            border: 1px solid {colors['border']};
            border-radius: 6px;
            text-align: center;
            background-color: {colors['background_tertiary']};
        }}
        
        QProgressBar::chunk {{
            background-color: {colors['primary']};
            border-radius: 5px;
        }}
        
        /* 组框 */
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {colors['border']};
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 8px 0 8px;
            color: {colors['primary']};
        }}
        
        /* 列表 */
        QListWidget, QTreeWidget {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            outline: none;
        }}
        
        QListWidget::item, QTreeWidget::item {{
            padding: 6px;
            border-bottom: 1px solid {colors['border_light']};
        }}
        
        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {colors['selection']};
            color: {colors['primary']};
        }}
        
        QListWidget::item:hover, QTreeWidget::item:hover {{
            background-color: {colors['hover']};
        }}
        
        /* 下拉框 */
        QComboBox {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 6px 12px;
        }}
        
        QComboBox:hover {{
            border-color: {colors['primary']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzZDNzU3RCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
        }}
        
        /* 滑块 */
        QSlider::groove:horizontal {{
            border: 1px solid {colors['border']};
            height: 6px;
            background: {colors['background_tertiary']};
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {colors['primary']};
            border: 1px solid {colors['primary_dark']};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        
        QSlider::sub-page:horizontal {{
            background: {colors['primary']};
            border-radius: 3px;
        }}
        """
        
        return stylesheet
    
    def _set_palette(self, color_scheme: ColorScheme):
        """设置调色板"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            palette = QPalette()
            colors = color_scheme.colors
            
            # 设置基本颜色
            palette.setColor(QPalette.ColorRole.Window, QColor(colors['background']))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(colors['text_primary']))
            palette.setColor(QPalette.ColorRole.Base, QColor(colors['surface']))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors['background_tertiary']))
            palette.setColor(QPalette.ColorRole.Text, QColor(colors['text_primary']))
            palette.setColor(QPalette.ColorRole.Button, QColor(colors['surface']))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors['text_primary']))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(colors['selection']))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors['primary']))
            
            app.setPalette(palette)
            
        except Exception as e:
            logger.error(f"设置调色板失败: {e}")
    
    def get_color(self, key: str, default: str = "#000000") -> str:
        """获取当前主题的颜色"""
        color_scheme = self._color_schemes.get(self._current_theme.value)
        if color_scheme:
            return color_scheme.get_color(key, default)
        return default
    
    def register_custom_style(self, name: str, stylesheet: str):
        """注册自定义样式"""
        self._custom_styles[name] = stylesheet
        logger.info(f"自定义样式已注册: {name}")
    
    def apply_custom_style(self, name: str, widget) -> bool:
        """应用自定义样式"""
        try:
            if name in self._custom_styles:
                widget.setStyleSheet(self._custom_styles[name])
                return True
            else:
                logger.warning(f"未找到自定义样式: {name}")
                return False
                
        except Exception as e:
            logger.error(f"应用自定义样式失败: {e}")
            return False
    
    def get_available_themes(self) -> list[str]:
        """获取可用主题列表"""
        return list(self._color_schemes.keys())
    
    def export_theme(self, theme_name: str, file_path: Path) -> bool:
        """导出主题"""
        try:
            color_scheme = self._color_schemes.get(theme_name)
            if not color_scheme:
                return False
            
            theme_data = {
                "name": color_scheme.name,
                "colors": color_scheme.colors,
                "version": "1.0"
            }
            
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"主题已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出主题失败: {e}")
            return False
    
    def import_theme(self, file_path: Path) -> bool:
        """导入主题"""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            if "name" not in theme_data or "colors" not in theme_data:
                logger.error("无效的主题文件格式")
                return False
            
            # 创建颜色方案
            color_scheme = ColorScheme(theme_data["name"], theme_data["colors"])
            
            # 生成主题键
            theme_key = theme_data["name"].lower().replace(" ", "_")
            
            # 注册主题
            self._color_schemes[theme_key] = color_scheme
            
            logger.info(f"主题已导入: {theme_data['name']}")
            return True
            
        except Exception as e:
            logger.error(f"导入主题失败: {e}")
            return False

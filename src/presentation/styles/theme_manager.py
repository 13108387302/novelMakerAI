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
        # 浅色主题（更柔和的浅灰背景、更清晰的文字与层次）
        light_colors = {
            # 主要颜色
            "primary": "#2563EB",          # 蓝 600
            "primary_dark": "#1E40AF",     # 蓝 800
            "primary_light": "#DBEAFE",    # 蓝 100
            "secondary": "#F59E0B",        # 琥珀 500
            "secondary_dark": "#B45309",   # 琥珀 700
            "secondary_light": "#FEF3C7",  # 琥珀 100

            # 状态颜色
            "success": "#16A34A",         # 绿 600
            "warning": "#F59E0B",         # 琥珀 500
            "error": "#DC2626",           # 红 600
            "info": "#2563EB",            # 蓝 600

            # 背景颜色（避免纯白刺眼）
            "background": "#F7F8FA",
            "background_secondary": "#EEF2F7",
            "background_tertiary": "#EDEFF3",
            "surface": "#FFFFFF",
            "surface_variant": "#F4F6F9",

            # 文本颜色 - 增强对比度与可读性
            "text_primary": "#1F2937",     # 灰 800
            "text_secondary": "#4B5563",   # 灰 600
            "text_disabled": "#9CA3AF",    # 灰 400
            "text_hint": "#6B7280",        # 灰 500
            # 兼容旧样式键
            "text": "#1F2937",

            # 边框颜色
            "border": "#D1D5DB",          # 灰 300
            "border_light": "#E5E7EB",     # 灰 200
            "border_dark": "#9CA3AF",      # 灰 400
            "divider": "#E5E7EB",

            # 阴影（更柔和）
            "shadow": "rgba(0, 0, 0, 0.08)",
            "shadow_light": "rgba(0, 0, 0, 0.04)",
            "shadow_dark": "rgba(0, 0, 0, 0.16)",

            # 特殊颜色
            "accent": "#E11D48",          # 玫红 600
            "highlight": "#FFF7ED",       # 浅橙高亮底
            "selection": "#DBEAFE",       # 浅蓝选中
            "hover": "#F3F4F6",            # 灰 100

            # 现代化扩展：用于渐变/悬停
            "hero_start": "#2563EB",       # 顶部横幅渐变起始（蓝 600）
            "hero_end": "#9333EA",         # 顶部横幅渐变结束（紫 600）
            "card_hover": "#F7FAFF"        # 卡片悬停底色（极浅蓝）
        }

        # 深色主题（提升对比与舒适度，减少纯黑纯白）
        dark_colors = {
            # 主要颜色
            "primary": "#60A5FA",          # 蓝 400
            "primary_dark": "#1D4ED8",     # 蓝 700
            "primary_light": "#93C5FD",    # 蓝 300
            "secondary": "#FBBF24",        # 琥珀 400
            "secondary_dark": "#D97706",   # 琥珀 600
            "secondary_light": "#FDE68A",  # 琥珀 200

            # 状态颜色
            "success": "#34D399",         # 绿 400
            "warning": "#FBBF24",         # 琥珀 400
            "error": "#F87171",           # 红 400
            "info": "#60A5FA",            # 蓝 400

            # 背景颜色
            "background": "#0F1115",       # 更深灰蓝，营造沉浸感
            "background_secondary": "#151922",
            "background_tertiary": "#1C2230",
            "surface": "#161B22",
            "surface_variant": "#1D2532",

            # 文本颜色
            "text_primary": "#E5E7EB",     # 灰 200
            "text_secondary": "#9CA3AF",   # 灰 400
            "text_disabled": "#6B7280",    # 灰 500
            "text_hint": "#94A3B8",        # 石板 400
            # 兼容旧样式键
            "text": "#E5E7EB",

            # 边框颜色 - 柔和但清晰
            "border": "#263042",
            "border_light": "#2F3A4E",
            "border_dark": "#1A2231",
            "divider": "#263042",

            # 阴影
            "shadow": "rgba(0, 0, 0, 0.45)",
            "shadow_light": "rgba(0, 0, 0, 0.25)",
            "shadow_dark": "rgba(0, 0, 0, 0.6)",

            # 特殊颜色
            "accent": "#A78BFA",          # 紫 400，提升科技感
            "highlight": "#222B3A",
            "selection": "#1E40AF",       # 蓝 800
            "hover": "#232B3A",

            # 现代化扩展：用于渐变/悬停
            "hero_start": "#1D4ED8",       # 顶部横幅渐变起始（蓝 700）
            "hero_end": "#7C3AED",         # 顶部横幅渐变结束（紫 700）
            "card_hover": "#1A2231"        # 卡片悬停底色（更深）
        }

        # 注册主题
        self._color_schemes[ThemeType.LIGHT.value] = ColorScheme("浅色主题", light_colors)
        self._color_schemes[ThemeType.DARK.value] = ColorScheme("深色主题", dark_colors)

    def get_current_theme(self) -> ThemeType:
        """获取当前主题（可能是 AUTO）"""
        return self._current_theme

    def get_effective_theme(self) -> ThemeType:
        """获取实际应用的主题（考虑 AUTO 的解析结果）"""
        try:
            if self._current_theme == ThemeType.AUTO:
                return self._detect_system_theme()
            return self._current_theme
        except Exception:
            return ThemeType.DARK

    def set_theme(self, theme: ThemeType) -> bool:
        """设置主题
        - 支持 ThemeType.AUTO：根据系统/调色板自动选择浅色或深色再应用
        - 若与当前主题相同，但需要强制重绘，可再次调用以重新应用样式
        """
        try:
            # 将 AUTO 映射为具体主题
            target_theme = theme
            if theme == ThemeType.AUTO:
                target_theme = self._detect_system_theme()

            # 如果目标与当前相同，仍允许重用以确保样式表被应用
            # 但避免无意义日志，因此不提前 return
            success = self._apply_theme(target_theme)
            if success:
                self._current_theme = theme  # 记录用户选择（可能是 AUTO）
                self.theme_changed.emit(theme.value)
                logger.info(f"主题已切换: {theme.value} -> 实际应用: {target_theme.value}")
                return True
            else:
                logger.error(f"切换主题失败: {theme.value}")
                return False

        except Exception as e:
            logger.error(f"设置主题失败: {e}")
            return False

    def _detect_system_theme(self) -> ThemeType:
        """根据当前应用调色板粗略判断应使用的主题（无平台API时的启发式）"""
        try:
            app = QApplication.instance()
            if not app:
                return ThemeType.DARK
            bg = app.palette().color(QPalette.ColorRole.Window)
            r, g, b, _ = bg.getRgb()
            # Rec. 709 亮度
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            return ThemeType.DARK if luminance < 128 else ThemeType.LIGHT
        except Exception:
            return ThemeType.DARK

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

        /* 卡片通用样式（细边） */
        *[card="true"] {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 12px;
            padding: 12px;
        }}

        /* 启动页最近项目卡片效果 */
        #RecentProjectCard {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 12px;
        }}
        #RecentProjectCard:hover {{
            border-color: {colors['primary']};
            background-color: {colors.get('card_hover', colors['background_tertiary'])};
        }}

        /* 启动页顶部横幅（hero） - 渐变、细腻阴影 */
        *[hero="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {colors.get('hero_start', colors['primary_dark'])},
                stop:1 {colors.get('hero_end', colors['secondary'])});
            border: none;
            padding: 20px 16px;
        }}
        *[hero="true"] QLabel {{ color: white; font-weight: 700; letter-spacing: 0.3px; background-color: transparent; }}
        *[hero="true"] QLabel[secondary="true"] {{ color: rgba(255,255,255,0.85); background-color: transparent; }}

        /* 启动页顶部横幅 - 二次强调文字颜色 */

        /* 通用对话框（修复深色主题下的白底区域） */
        QDialog {{
            background-color: {colors['background_secondary']};
        }}
        /* 对话框底部按钮区域（若使用 QDialogButtonBox） */
        QDialogButtonBox {{
            background-color: {colors['surface']};
            border-top: 1px solid {colors['border']};
            padding: 8px;
        }}
        QDialogButtonBox QPushButton {{
            /* 复用全局按钮风格 */
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
            padding: 6px 14px;
        }}
        QDialogButtonBox QPushButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['primary']};
        }}

        *[hero="true"] QLabel[title="true"] {{ color: white; background-color: transparent; }}
        *[hero="true"] QLabel[version="true"] {{ color: rgba(255,255,255,0.85); background-color: transparent; }}

        /* 常用文本语义颜色 */
        QLabel[muted="true"] {{ color: {colors['text_secondary']}; }}
        QLabel[hint="true"] {{ color: {colors['text_hint']}; }}

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
            border-radius: 8px;
            padding: 6px 10px;
            margin: 2px;
        }}

        QToolBar QToolButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['border']};
        }}

        QToolBar QToolButton:pressed {{
            background-color: {colors['primary_light']};
        }}

        /* 工具栏选中/锁定态（例如切换、勾选型按钮） */
        QToolBar QToolButton:checked {{
            background-color: {colors['surface']};
            border: 1px solid {colors['primary']};
            border-top: 2px solid {colors['primary']};
            color: {colors['primary']};
        }}
        QToolBar QToolButton:checked:hover {{
            background-color: {colors['background_tertiary']};
            border-color: {colors['primary_dark']};
            border-top-color: {colors['primary_dark']};
        }}

        /* 状态栏 */
        QStatusBar {{
            background-color: {colors['surface']};
            border-top: 1px solid {colors['border']};
            color: {colors['text_secondary']};
        }}

        /* 按钮 - 默认（中性背景，清晰态反馈，轻微动画）*/
        QPushButton {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['primary']};
        }}

        QPushButton:pressed {{
            background-color: {colors['surface_variant']};
        }}

        QPushButton:disabled {{
            background-color: {colors['background_tertiary']};
            color: {colors['text_disabled']};
            border-color: {colors['border_light']};
        }}

        /* 强调按钮（设置属性 accent="true" 时）*/
        QPushButton[accent="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary']}, stop:1 {colors['secondary']});
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 700;
        }}
        /* 更炫的胶囊型强调按钮（带 fancy 标记） */
        QPushButton[accent="true"][fancy="true"] {{
            border-radius: 24px;
            padding: 12px 18px;
        }}

        QPushButton[accent="true"]:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary_dark']}, stop:1 {colors['secondary_dark']});
        }}

        QPushButton[accent="true"]:pressed {{
            background-color: {colors['primary_dark']};
        }}

        /* 输入框 */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
            padding: 10px 12px;
            color: {colors['text_primary']};
            selection-background-color: {colors['selection']};
            selection-color: {colors['surface']};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors['primary']};
            outline: none;
        }}

        QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
            color: {colors['text_hint']};
        }}

        /* 标签页 */
        QTabWidget::pane {{
            border: 1px solid {colors['border']};
            border-radius: 8px;
            background-color: {colors['surface']};
        }}

        QTabBar::tab {{
            background-color: {colors['background_tertiary']};
            border: 1px solid {colors['border']};
            border-bottom: none;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            color: {colors['text_secondary']};
        }}

        QTabBar::tab:selected {{
            background-color: {colors['surface']};
            border-bottom: 2px solid {colors['primary']};
            color: {colors['primary']};
            font-weight: 700;
        }}

        QTabBar::tab:hover {{
            background-color: {colors['hover']};
            color: {colors['text_primary']};
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
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary']}, stop:1 {colors['secondary']});
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

        /* AI 面板区域特化 */
        #ModernAIWidget {{
            background-color: {colors['background_secondary']};
        }}

        #CardFrame {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 12px;
            padding: 12px;
        }}

        #ModernGroup {{
            border: 1px solid {colors['border']};
            border-radius: 10px;
            margin-top: 8px;
            padding-top: 6px;
        }}

        #StatusIndicator {{
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 6px 10px;
            color: {colors['text_secondary']};
            background-color: {colors['surface']};
        }}
        #StatusIndicator[status="success"] {{ background-color: {colors['success']}; color: white; border-color: {colors['success']}; }}
        #StatusIndicator[status="warning"] {{ background-color: {colors['warning']}; color: white; border-color: {colors['warning']}; }}
        #StatusIndicator[status="error"]   {{ background-color: {colors['error']};   color: white; border-color: {colors['error']}; }}
        #StatusIndicator[status="info"]    {{ background-color: {colors['info']};    color: white; border-color: {colors['info']}; }}

        /* 输出区 */
        #OutputArea {{
            border: 1px solid {colors['border']};
            border-radius: 10px;
            background-color: {colors['surface']};
        }}
        #OutputText {{
            background-color: {colors['surface']};
            border: none;
            color: {colors['text_primary']};
        }}

        /* 列表 */
        QListWidget, QTreeWidget {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            outline: none;
        }}

        QListWidget::item, QTreeWidget::item {{
            padding: 8px 10px;
            border-bottom: 1px solid {colors['border_light']};
            margin: 2px 4px;
            border-radius: 6px;
        }}

        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {colors['selection']};
            color: {colors['primary']};
            border: 1px solid {colors['primary']};
        }}

        QListWidget::item:hover, QTreeWidget::item:hover {{
            background-color: {colors['hover']};
        }}

        /* 下拉框 */
        QComboBox {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 6px 12px;
        }}

        QComboBox:hover {{
            border-color: {colors['primary']};
        }}

        QComboBox:focus {{
            border-color: {colors['primary']};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}

        QComboBox::down-arrow {{
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzk0QTNCOCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
        }}

        /* 复选框与单选框 */
        QCheckBox, QRadioButton {{
            color: {colors['text_primary']};
            spacing: 8px;
        }}
        QCheckBox:disabled, QRadioButton:disabled {{
            color: {colors['text_disabled']};
        }}

        QCheckBox::indicator {{
            width: 18px; height: 18px;
            border: 1px solid {colors['border']};
            border-radius: 4px;
            background-color: {colors['surface']};
        }}
        QCheckBox::indicator:hover {{ border-color: {colors['primary']}; }}
        QCheckBox::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary_dark']};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {colors['background_tertiary']};
            border-color: {colors['border_light']};
        }}

        QRadioButton::indicator {{
            width: 18px; height: 18px;
            border: 1px solid {colors['border']};
            border-radius: 9px;
            background-color: {colors['surface']};
        }}
        QRadioButton::indicator:hover {{ border-color: {colors['primary']}; }}
        QRadioButton::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary_dark']};
        }}
        QRadioButton::indicator:disabled {{
            background-color: {colors['background_tertiary']};
            border-color: {colors['border_light']};
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
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary_light']}, stop:1 {colors['primary']});
            border-radius: 3px;
        }}

        /* 表头（表格/树） */
        QHeaderView::section {{
            background-color: {colors['surface']};
            color: {colors['text_secondary']};
            padding: 6px 10px;
            border: 1px solid {colors['border']};
            border-right: none;
        }}
        QHeaderView::section:first {{
            border-top-left-radius: 8px;
        }}
        QHeaderView::section:last {{
            border-top-right-radius: 8px;
            border-right: 1px solid {colors['border']};
        }}
        QHeaderView::section:hover {{
            background-color: {colors['hover']};
            color: {colors['text_primary']};
        }}
        QHeaderView::section:pressed {{
            background-color: {colors['primary_light']};
            color: {colors['text_primary']};
        }}

        /* 表格/树视图 */
        QTableView, QTreeView {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            gridline-color: {colors['border']};
            selection-background-color: {colors['selection']};
            selection-color: {colors['text_primary']};
            alternate-background-color: {colors['background_tertiary']};
        }}
        QTableView::item:selected, QTreeView::item:selected {{
            background-color: {colors['selection']};
            color: {colors['text_primary']};
        }}
        QTableView::item:hover, QTreeView::item:hover {{
            background-color: {colors['hover']};
        }}

        /* 停靠面板标题 */
        QDockWidget {{
            border: 1px solid {colors['border']};
        }}
        QDockWidget::title {{
            padding: 6px 8px;
            background-color: {colors['surface_variant']};
            color: {colors['text_secondary']};
            border-bottom: 1px solid {colors['border']};
        }}

        /* 工具提示 */
        QToolTip {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 6px 8px;
        }}

        /* 横向滚动条 */
        QScrollBar:horizontal {{
            background-color: {colors['background_tertiary']};
            height: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors['text_disabled']};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['text_secondary']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}

        /* 设置对话框专项优化 */
        #SettingsDialog QTabWidget::pane {{
            border: 1px solid {colors['border']};
            border-radius: 8px;
            background-color: {colors['surface']};
        }}
        #SettingsDialog QTabBar::tab {{
            background-color: {colors['background_tertiary']};
            border: 1px solid {colors['border']};
            border-bottom: none; padding: 8px 14px; margin-right: 2px;
            border-top-left-radius: 8px; border-top-right-radius: 8px;
        }}
        #SettingsDialog QTabBar::tab:selected {{
            background-color: {colors['surface']};
            border-bottom: 2px solid {colors['primary']};
            color: {colors['primary']}; font-weight: 600;
        }}

        /* Word Count Dialog 专用样式，确保深色下可读性 */
        #WordCountDialog QDialog {{
            background-color: {colors['background_secondary']};
        }}
        #WordCountDialog QGroupBox {{
            border: 1px solid {colors['border']};
            border-radius: 8px;
            margin-top: 8px; padding-top: 8px;
        }}
        #WordCountDialog QLabel {{ color: {colors['text_secondary']}; }}
        #WordCountDialog QLabel[title="true"] {{ color: {colors['text_primary']}; font-weight: 600; }}
        #WordCountDialog QProgressBar {{
            border: 1px solid {colors['border']};
            border-radius: 8px; text-align: center;
            background-color: {colors['background_tertiary']};
            color: {colors['text_primary']};
            height: 14px;
        }}
        #WordCountDialog QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary_light']}, stop:1 {colors['primary']});
            border-radius: 7px;
        }}
        #WordCountDialog QPushButton {{
            border-radius: 10px; padding: 8px 16px;
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            color: {colors['text_primary']};
        }}
        #WordCountDialog QPushButton:hover {{ background-color: {colors['hover']}; border-color: {colors['primary']}; }}
        #WordCountDialog QPushButton[accent="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary']}, stop:1 {colors['secondary']});
            color: white; border: none; border-radius: 10px;
        }}
        #SettingsDialog QGroupBox {{
            border: 1px solid {colors['border']}; border-radius: 8px;
            margin-top: 10px; padding-top: 8px;
        }}
        #SettingsDialog QGroupBox::title {{
            subcontrol-origin: margin; left: 8px; padding: 0 8px;
            color: {colors['primary']};
        }}
        /* 快捷键设置面板的样式标签 */
        #SettingsDialog QLabel[kbd="true"] {{
            background-color: {colors['surface_variant']};
            border: 1px solid {colors['border']};
            color: {colors['text_primary']};
            padding: 4px 8px; border-radius: 6px; font-family: Consolas, Menlo, monospace;
        }}
        #SettingsDialog QLabel[hint="true"] {{ color: {colors['text_hint']}; font-style: italic; }}

        #SettingsDialog QLabel {{
            color: {colors['text_secondary']};
        }}
        #SettingsDialog QLineEdit, #SettingsDialog QComboBox, #SettingsDialog QSpinBox, #SettingsDialog QSlider {{
            border-radius: 8px;
        }}
        #SettingsDialog QPushButton[accent=\"true\"], #SettingsDialog QPushButton#apply_btn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary']}, stop:1 {colors['secondary']});
            color: white; border: none; border-radius: 8px; font-weight: 600;
        }}
        #SettingsDialog QPushButton[accent=\"true\"]:hover, #SettingsDialog QPushButton#apply_btn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {colors['primary_dark']}, stop:1 {colors['secondary_dark']});
        }}
        #SettingsDialog QPushButton[accent=\"true\"]:pressed, #SettingsDialog QPushButton#apply_btn:pressed {{
            background-color: {colors['primary_dark']};
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

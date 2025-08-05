#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI面板样式定义

现代化的AI界面样式
"""

# 主题色彩定义
COLORS = {
    # 主色调 - 现代蓝紫渐变
    'primary': '#667eea',
    'primary_hover': '#764ba2',
    'primary_pressed': '#5a67d8',
    
    # 辅助色调
    'secondary': '#f093fb',
    'secondary_hover': '#f5576c',
    
    # 功能色彩
    'success': '#48bb78',
    'warning': '#ed8936',
    'error': '#f56565',
    'info': '#4299e1',
    
    # 中性色
    'background': '#f7fafc',
    'surface': '#ffffff',
    'surface_hover': '#f1f5f9',
    'border': '#e2e8f0',
    'text_primary': '#2d3748',
    'text_secondary': '#718096',
    'text_muted': '#a0aec0',
    
    # 暗色主题
    'dark_background': '#1a202c',
    'dark_surface': '#2d3748',
    'dark_surface_hover': '#4a5568',
    'dark_border': '#4a5568',
    'dark_text_primary': '#f7fafc',
    'dark_text_secondary': '#e2e8f0',
}

# AI面板主样式
AI_PANEL_STYLE = f"""
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
}}

/* 滚动区域样式 */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* 滚动条样式 */
QScrollBar:vertical {{
    background-color: {COLORS['background']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

/* 组框样式 */
QGroupBox {{
    font-size: 14px;
    font-weight: 600;
    color: {COLORS['text_primary']};
    border: 2px solid {COLORS['border']};
    border-radius: 12px;
    margin-top: 8px;
    padding-top: 12px;
    background-color: {COLORS['surface']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px 0 8px;
    background-color: {COLORS['surface']};
    border-radius: 4px;
}}
"""

# 现代化按钮样式
MODERN_BUTTON_STYLE = f"""
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
    text-align: left;
}}

QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {COLORS['primary_hover']}, stop:1 {COLORS['secondary_hover']});
    border: 1px solid {COLORS['primary']};
}}

QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {COLORS['primary_pressed']}, stop:1 {COLORS['primary']});
    border: 2px solid {COLORS['primary_pressed']};
}}

QPushButton:disabled {{
    background-color: {COLORS['text_muted']};
    color: {COLORS['background']};
}}
"""

# 特殊功能按钮样式
SPECIAL_BUTTON_STYLES = {
    'writing': f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff9a9e, stop:1 #fecfef);
        color: #2d3748;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff8a95, stop:1 #fdb5e8);
        border: 1px solid #ff6b7a;
    }}
    """,
    
    'inspiration': f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #a8edea, stop:1 #fed6e3);
        color: #2d3748;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #96e6e1, stop:1 #fcc9dc);
        border: 1px solid #7dd3ce;
    }}
    """,
    
    'optimization': f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffecd2, stop:1 #fcb69f);
        color: #2d3748;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffe4c4, stop:1 #faa085);
        border: 1px solid #ffd700;
    }}
    """,
    
    'analysis': f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d299c2, stop:1 #fef9d7);
        color: #2d3748;
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #c785b5, stop:1 #fef5c7);
        border: 1px solid #b76ba3;
    }}
    """
}

# 状态指示器样式
STATUS_INDICATOR_STYLE = f"""
QLabel {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

QLabel[status="success"] {{
    background-color: {COLORS['success']};
    color: white;
    border-color: {COLORS['success']};
}}

QLabel[status="warning"] {{
    background-color: {COLORS['warning']};
    color: white;
    border-color: {COLORS['warning']};
}}

QLabel[status="error"] {{
    background-color: {COLORS['error']};
    color: white;
    border-color: {COLORS['error']};
}}

QLabel[status="info"] {{
    background-color: {COLORS['info']};
    color: white;
    border-color: {COLORS['info']};
}}
"""

# 输出区域样式
OUTPUT_AREA_STYLE = f"""
QTextEdit {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['primary']};
}}

QTextEdit:focus {{
    border-color: {COLORS['primary']};
}}
"""

# 卡片样式
CARD_STYLE = f"""
QFrame {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 16px;
}}

QFrame:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['primary']};
}}
"""

def get_complete_ai_style():
    """获取完整的AI面板样式"""
    return AI_PANEL_STYLE + MODERN_BUTTON_STYLE + STATUS_INDICATOR_STYLE + OUTPUT_AREA_STYLE + CARD_STYLE

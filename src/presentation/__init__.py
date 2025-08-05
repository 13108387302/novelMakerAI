#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表示层包

表示层负责用户界面和用户交互，包括窗口、对话框、组件和控制器。
遵循MVC模式，确保界面逻辑与业务逻辑分离。

主要组件：
- controllers: 控制器，处理用户交互和业务逻辑协调
- views: 视图，主要窗口和界面布局
- dialogs: 对话框，各种功能对话框
- widgets: 组件，可复用的UI组件
- shortcuts: 快捷键管理
- styles: 样式和主题管理

设计原则：
- 分离界面逻辑和业务逻辑
- 使用信号槽机制进行组件通信
- 提供响应式和用户友好的界面
- 支持主题切换和国际化

版本: 2.0.0
"""

__version__ = "2.0.0"
__description__ = "AI小说编辑器表示层"

# 导出主要组件
try:
    from .controllers.main_controller import MainController
    from .views.main_window import MainWindow

    __all__ = [
        "MainController",
        "MainWindow",
        "__version__",
        "__description__"
    ]
except ImportError:
    # 如果导入失败，只导出版本信息
    __all__ = ["__version__", "__description__"]

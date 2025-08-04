#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块包

这个包提供了AI小说编辑器应用程序的配置管理功能。
包含了应用程序所需的所有配置类和工具函数。

主要组件：
- Settings: 主配置类，整合所有子配置
- DatabaseSettings: 数据库配置
- AIServiceSettings: AI服务配置
- UISettings: 用户界面配置
- LoggingSettings: 日志配置
- PluginSettings: 插件配置
- SecuritySettings: 安全配置

实现方式：
- 使用Pydantic提供强类型配置管理
- 支持环境变量和配置文件
- 提供配置验证和默认值
- 模块化设计便于维护和扩展

使用示例：
    from config.settings import get_settings
    settings = get_settings()
    print(settings.app_name)
"""

# 版本信息
__version__ = "2.0.0"
__author__ = "AI小说编辑器团队"

# 导出主要配置类和函数，方便外部使用
try:
    from .settings import (
        Settings,
        DatabaseSettings,
        AIServiceSettings,
        UISettings,
        LoggingSettings,
        PluginSettings,
        SecuritySettings,
        get_settings,
        reset_settings
    )

    __all__ = [
        "Settings",
        "DatabaseSettings",
        "AIServiceSettings",
        "UISettings",
        "LoggingSettings",
        "PluginSettings",
        "SecuritySettings",
        "get_settings",
        "reset_settings",
        "__version__",
        "__author__"
    ]

except ImportError as e:
    # 如果导入失败，记录错误并只导出版本信息
    import sys
    print(f"警告：配置模块导入失败: {e}", file=sys.stderr)
    print("这可能是由于缺少依赖包导致的，请检查pydantic是否正确安装", file=sys.stderr)
    __all__ = ["__version__", "__author__"]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统

提供统一的日志配置和管理功能
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Any

# Settings 现在需要项目上下文，日志系统使用内置常量
from src.shared.constants import TIME_FORMATS, ENCODING_FORMATS
from platform import system
import os


def _get_user_log_file() -> Path:
    """获取用户级默认日志文件路径（用于未加载项目设置前）"""
    home = Path.home()
    sys_name = system()
    try:
        if sys_name == "Windows":
            base = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
            log_dir = base / "AI_Novel_Editor" / "logs"
        elif sys_name == "Darwin":
            log_dir = home / "Library" / "Logs" / "AI Novel Editor"
        else:
            # Linux: 使用 ~/.cache 作为日志默认位置
            base = Path(os.environ.get("XDG_CACHE_HOME", str(home / ".cache")))
            log_dir = base / "ai-novel-editor" / "logs"
    except Exception:
        log_dir = home / ".ai_novel_editor_app"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "app.log"


# 日志格式常量
CONSOLE_LOG_FORMAT = '%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s'
FILE_LOG_FORMAT = '%(asctime)s | %(name)-20s | %(levelname)-8s | %(funcName)-15s | %(message)s'
CONSOLE_TIME_FORMAT = '%H:%M:%S'
FILE_TIME_FORMAT = TIME_FORMATS['datetime']
DEFAULT_ENCODING = ENCODING_FORMATS['utf8']

# 第三方库日志级别配置
THIRD_PARTY_LOG_LEVELS = {
    'PyQt6': 'WARNING',
    'urllib3': 'WARNING',
    'requests': 'WARNING'
}


class ColoredFormatter(logging.Formatter):
    """
    彩色日志格式化器

    为控制台输出的日志添加ANSI颜色代码，提高日志的可读性。
    不同级别的日志使用不同的颜色显示。

    实现方式：
    - 使用ANSI转义序列为日志级别添加颜色
    - 在格式化时动态修改日志记录的级别名称
    - 支持标准的日志级别颜色映射
    - 自动重置颜色避免影响后续输出

    Attributes:
        COLORS: 日志级别到ANSI颜色代码的映射字典
    """

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }

    def format(self, record):
        """
        格式化日志记录，添加颜色代码

        Args:
            record: 日志记录对象

        Returns:
            str: 格式化后的日志字符串
        """
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )

        return super().format(record)


class ThemeConsoleFilter(logging.Filter):
    """控制台主题相关日志过滤器

    当环境变量 THEME_LOGS_ONLY 为 1/true 时，仅放行：
    - __main__ 中包含 "[Theme]" 的日志
    - src.presentation.styles.theme_manager 的日志
    - src.presentation.views.startup_window 的日志
    - 任意模块的 ERROR/CRITICAL 级别（防止隐藏错误）
    否则不过滤（放行全部）。
    """
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            flag = os.environ.get("THEME_LOGS_ONLY", "").strip().lower()
            if flag not in ("1", "true", "yes", "on"):
                return True

            # 始终放行错误级别
            if record.levelno >= logging.ERROR:
                return True

            name = record.name or ""
            msg = record.getMessage() if hasattr(record, 'getMessage') else record.msg

            if name.startswith("src.presentation.styles.theme_manager"):
                return True
            if name.startswith("src.presentation.views.startup_window"):
                return True
            if name.startswith("__main__") and isinstance(msg, str) and "[Theme]" in msg:
                return True

            return False
        except Exception:
            # 异常时不过滤
            return True


def setup_logging(settings: Optional[Any] = None) -> None:
    """
    设置日志系统

    配置应用程序的日志系统，包括控制台输出和文件输出。
    支持彩色控制台输出和文件轮转。

    实现方式：
    - 配置根日志器的级别和处理器
    - 为控制台输出添加彩色格式化器
    - 配置文件输出和轮转策略
    - 确保日志目录存在
    - 避免重复配置日志系统

    Args:
        settings: 应用程序设置，如果为None则使用默认设置
    """
    if settings is None:
        # 使用用户级默认日志位置（未加载项目时）
        log_level = "INFO"
        log_file = _get_user_log_file()
    else:
        log_level = settings.logging.level
        log_file = settings.log_dir / "app.log"

    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    # 控制台级别：
    # 1) 若设置 CONSOLE_MIN_LEVEL，则使用该级别；
    # 2) 否则若 THEME_LOGS_ONLY/HIDE_INFO 开启，则提升到 WARNING；
    # 3) 默认使用全局 log_level。
    try:
        console_level_env = os.environ.get("CONSOLE_MIN_LEVEL", "").strip().upper()
        truthy = {"1", "true", "yes", "on"}
        if console_level_env:
            console_level = getattr(logging, console_level_env, logging.WARNING)
        elif os.environ.get("THEME_LOGS_ONLY", "").strip().lower() in truthy or \
             os.environ.get("HIDE_INFO", "").strip().lower() in truthy:
            console_level = logging.WARNING
        else:
            console_level = getattr(logging, log_level)
        console_handler.setLevel(console_level)
    except Exception:
        console_handler.setLevel(logging.WARNING)

    # 根据环境变量注入过滤器：只输出主题相关日志
    try:
        console_handler.addFilter(ThemeConsoleFilter())
    except Exception:
        pass

    # 控制台格式化器（带颜色）
    console_formatter = ColoredFormatter(
        CONSOLE_LOG_FORMAT,
        datefmt=CONSOLE_TIME_FORMAT
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器 - 使用覆盖模式保存日志文件
    # 使用传入的日志文件路径，或默认路径
    log_file_path = log_file

    # 使用普通FileHandler，每次启动时覆盖日志文件
    file_handler = logging.FileHandler(
        log_file_path,
        mode='w',  # 覆盖模式
        encoding=DEFAULT_ENCODING
    )
    # 文件只记录警告和错误信息
    file_handler.setLevel(logging.WARNING)

    # 文件格式化器（不带颜色）
    file_formatter = logging.Formatter(
        FILE_LOG_FORMAT,
        datefmt=FILE_TIME_FORMAT
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 设置第三方库的日志级别
    for lib_name, level_name in THIRD_PARTY_LOG_LEVELS.items():
        logging.getLogger(lib_name).setLevel(getattr(logging, level_name))

    # 为AI模块设置DEBUG级别，确保调试信息显示
    ai_modules = [
        'src.application.services.ai_service',
        'src.infrastructure.repositories.ai_service_repository',
        'src.infrastructure.ai_clients.openai_client',
        'src.presentation.widgets.ai_workers',
        'src.presentation.widgets.writing_assistant',
        'src.presentation.widgets.global_ai_panel',
        'src.application.services.ai.streaming_ai_service',
        'src.application.services.ai.content_generation_service',
        'src.application.services.ai.analysis_service',
    ]

    for module_name in ai_modules:
        logging.getLogger(module_name).setLevel(logging.DEBUG)

    logging.info("日志系统初始化完成")
    logging.info(f"📝 日志文件位置: {log_file}")
    logging.info(f"🖥️  控制台日志级别: {log_level}")
    logging.info("⚠️  文件日志级别: WARNING (只记录警告和错误)")
    logging.info("🔍 AI模块调试日志已启用")
    logging.info("ℹ️  每次启动时日志文件将被覆盖，只保留当前运行的日志")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)

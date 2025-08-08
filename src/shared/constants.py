#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序常量

定义应用程序中使用的常量
"""

from pathlib import Path


# 应用程序信息
APP_NAME = "AI小说编辑器"
APP_VERSION = "2.0.0"
APP_AUTHOR = "AI小说编辑器团队"
APP_DESCRIPTION = "基于AI技术的智能小说创作工具"
APP_COPYRIGHT = f"© 2024 {APP_AUTHOR}"

# 文件和目录
DEFAULT_PROJECT_EXTENSION = ".ainovel"
DEFAULT_DOCUMENT_EXTENSION = ".txt"
BACKUP_EXTENSION = ".backup"
TEMP_EXTENSION = ".tmp"

# 支持的文件格式
SUPPORTED_PROJECT_FORMATS = [".ainovel", ".json"]
SUPPORTED_DOCUMENT_FORMATS = [".txt", ".md", ".docx", ".pdf"]
SUPPORTED_EXPORT_FORMATS = [".txt", ".md", ".docx", ".pdf", ".json", ".xlsx"]
SUPPORTED_IMPORT_FORMATS = [".txt", ".md", ".docx", ".json"]

# 文件大小限制（字节）
MAX_PROJECT_SIZE = 100 * 1024 * 1024  # 100MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024   # 10MB
MAX_BACKUP_SIZE = 50 * 1024 * 1024     # 50MB

# 字数限制
MAX_PROJECT_WORD_COUNT = 10000000      # 1000万字
MAX_DOCUMENT_WORD_COUNT = 1000000      # 100万字
MIN_WORD_COUNT_FOR_ANALYSIS = 100      # 分析最少字数

# 默认设置值
DEFAULT_AUTO_SAVE_INTERVAL = 30        # 秒
DEFAULT_BACKUP_INTERVAL = 3600         # 秒
DEFAULT_BACKUP_COUNT = 10              # 个
DEFAULT_FONT_SIZE = 12                 # 像素
DEFAULT_LINE_SPACING = 1.2             # 倍数
DEFAULT_TAB_WIDTH = 4                  # 字符
DEFAULT_WORD_GOAL_DAILY = 1000         # 字
DEFAULT_WORD_GOAL_WEEKLY = 7000        # 字
DEFAULT_WORD_GOAL_MONTHLY = 30000      # 字

# 项目相关常量
DEFAULT_TARGET_WORD_COUNT = 80000      # 默认目标字数
DEFAULT_RECENT_PROJECTS_LIMIT = 10     # 最近项目显示数量
DEFAULT_RECENT_DOCUMENTS_LIMIT = 10    # 最近文档显示数量
DEFAULT_TREND_DAYS = 7                 # 默认趋势分析天数
DEFAULT_PROJECT_VERSION = "1.0.0"     # 默认项目版本
DEFAULT_FORMAT_VERSION = "2.0"        # 默认项目格式版本
COPY_SUFFIX = " - 副本"               # 项目复制后缀

# AI设置默认值
DEFAULT_AI_CREATIVITY_LEVEL = 0.7      # 0.0-1.0
DEFAULT_AI_RESPONSE_LENGTH = "medium"  # short, medium, long
DEFAULT_AI_SUGGESTION_DELAY = 1000     # 毫秒
DEFAULT_AI_MODEL = "default"

# AI服务配置
AI_MAX_CONCURRENT_REQUESTS = 20        # AI最大并发请求数
AI_TIMEOUT_SECONDS = 30.0              # AI请求超时时间（秒）
AI_RETRY_ATTEMPTS = 3                  # AI请求重试次数
AI_HEALTH_CHECK_INTERVAL = 30          # AI健康检查间隔（秒）
AI_MAX_TOKENS = 2000                   # AI最大生成token数
AI_TEMPERATURE = 0.7                   # AI生成温度

# UI设置
DEFAULT_WINDOW_WIDTH = 1600            # 像素
DEFAULT_WINDOW_HEIGHT = 1000           # 像素
MIN_WINDOW_WIDTH = 1200                # 像素
MIN_WINDOW_HEIGHT = 800                # 像素

# UI交互设置
DEFAULT_STATUS_TIMEOUT = 3000          # 状态消息超时时间（毫秒）
UI_UPDATE_DELAY_MS = 200               # UI更新延迟（毫秒）
DOCUMENT_LOAD_DELAY_MS = 50            # 文档加载延迟（毫秒）

# 主题设置
DEFAULT_THEME = "default"
AVAILABLE_THEMES = ["default", "dark", "light", "blue", "green"]

# 语言设置
DEFAULT_LANGUAGE = "zh_CN"
AVAILABLE_LANGUAGES = {
    "zh_CN": "简体中文",
    "zh_TW": "繁体中文", 
    "en_US": "English (US)",
    "en_GB": "English (UK)"
}

# 项目类型默认字数
PROJECT_TYPE_WORD_COUNTS = {
    "novel": 80000,        # 长篇小说
    "short_story": 5000,   # 短篇小说
    "novella": 40000,      # 中篇小说
    "script": 20000,       # 剧本
    "poetry": 2000,        # 诗歌
    "essay": 10000,        # 散文
    "other": 50000         # 其他
}

# 文档类型
DOCUMENT_TYPES = {
    "chapter": "章节",
    "scene": "场景",
    "character": "角色",
    "outline": "大纲",
    "note": "笔记",
    "research": "资料",
    "other": "其他"
}

# 导出模板
EXPORT_TEMPLATES = {
    "simple": "简单模板",
    "professional": "专业模板",
    "academic": "学术模板",
    "creative": "创意模板"
}

# AI任务类型
AI_TASK_TYPES = {
    "continuation": "续写",
    "rewrite": "改写",
    "summarize": "总结",
    "analyze": "分析",
    "translate": "翻译",
    "proofread": "校对",
    "expand": "扩展",
    "compress": "压缩"
}

# 错误代码
ERROR_CODES = {
    "FILE_NOT_FOUND": 1001,
    "PERMISSION_DENIED": 1002,
    "INVALID_FORMAT": 1003,
    "CORRUPTED_FILE": 1004,
    "NETWORK_ERROR": 2001,
    "AI_SERVICE_ERROR": 2002,
    "VALIDATION_ERROR": 3001,
    "BUSINESS_LOGIC_ERROR": 3002,
    "UNKNOWN_ERROR": 9999
}

# 状态码
STATUS_CODES = {
    "SUCCESS": 200,
    "CREATED": 201,
    "ACCEPTED": 202,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "INTERNAL_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503
}

# 正则表达式模式
REGEX_PATTERNS = {
    "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    "url": r'^https?://[^\s/$.?#].[^\s]*$',
    "chinese_char": r'[\u4e00-\u9fff]',
    "english_word": r'[a-zA-Z]+',
    "number": r'\d+',
    "version": r'^\d+\.\d+\.\d+$'
}

# 时间格式
TIME_FORMATS = {
    "datetime": "%Y-%m-%d %H:%M:%S",
    "date": "%Y-%m-%d",
    "time": "%H:%M:%S",
    "timestamp": "%Y%m%d_%H%M%S",
    "iso": "%Y-%m-%dT%H:%M:%S"
}

# 编码格式
ENCODING_FORMATS = {
    "utf8": "UTF-8",
    "gbk": "GBK",
    "gb2312": "GB2312",
    "ascii": "ASCII",
    "latin1": "Latin-1"
}

# 快捷键
SHORTCUTS = {
    "new_project": "Ctrl+N",
    "open_project": "Ctrl+O", 
    "save": "Ctrl+S",
    "save_as": "Ctrl+Shift+S",
    "quit": "Ctrl+Q",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "cut": "Ctrl+X",
    "copy": "Ctrl+C",
    "paste": "Ctrl+V",
    "find": "Ctrl+F",
    "replace": "Ctrl+H",
    "ai_continue": "Ctrl+Shift+C",
    "ai_analyze": "Ctrl+Shift+A",
    "fullscreen": "F11",
    "help": "F1"
}

# 配置文件路径
CONFIG_DIR = Path.home() / ".ainovel"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_DIR = CONFIG_DIR / "logs"
BACKUP_DIR = CONFIG_DIR / "backups"
CACHE_DIR = CONFIG_DIR / "cache"
PLUGINS_DIR = CONFIG_DIR / "plugins"

# 网络设置
DEFAULT_TIMEOUT = 30                   # 秒
MAX_RETRIES = 3                        # 次
RETRY_DELAY = 1                        # 秒

# 性能设置
MAX_UNDO_STEPS = 100                   # 撤销步数
MAX_SEARCH_RESULTS = 1000              # 搜索结果数
MAX_RECENT_FILES = 20                  # 最近文件数
CACHE_EXPIRE_HOURS = 24                # 缓存过期时间
CACHE_EXPIRE_SECONDS = 300             # 缓存过期时间（秒）

# 版本管理设置
VERSION_KEEP_COUNT = 20                # 版本保留数量

# UI操作延迟时间（毫秒）
UI_IMMEDIATE_DELAY = 0                 # 立即执行
UI_SHORT_DELAY = 100                   # 短延迟
UI_MEDIUM_DELAY = 500                  # 中等延迟
UI_LONG_DELAY = 1000                   # 长延迟
UI_REFRESH_DELAY = 300                 # 刷新延迟

# 异步操作超时时间（秒）
ASYNC_SHORT_TIMEOUT = 10               # 短操作超时
ASYNC_MEDIUM_TIMEOUT = 30              # 中等操作超时
ASYNC_LONG_TIMEOUT = 60                # 长操作超时
ASYNC_FILE_TIMEOUT = 120               # 文件操作超时

# 线程池配置
DEFAULT_THREAD_POOL_SIZE = 4           # 默认线程池大小
MAX_THREAD_POOL_SIZE = 8               # 最大线程池大小

# 错误处理配置
SHOW_ERROR_TRACEBACK = False           # 是否显示错误堆栈
ERROR_MESSAGE_MAX_LENGTH = 500         # 错误消息最大长度

# 任务管理配置
MAX_CONCURRENT_TASKS = 10              # 最大并发任务数
TASK_CLEANUP_INTERVAL = 300            # 任务清理间隔（秒）

# 性能优化配置
SMALL_DOCUMENT_THRESHOLD = 10000       # 小文档阈值（字符数）
LARGE_DOCUMENT_THRESHOLD = 100000      # 大文档阈值（字符数）
CHUNK_SIZE_SMALL = 1024                # 小块大小（字节）
CHUNK_SIZE_MEDIUM = 4096               # 中等块大小（字节）
CHUNK_SIZE_LARGE = 8192                # 大块大小（字节）

# 缓存配置优化
CACHE_MAX_SIZE = 1000                  # 缓存最大条目数
CACHE_CLEANUP_THRESHOLD = 0.8          # 缓存清理阈值（80%满时清理）
OBJECT_POOL_SIZE = 50                  # 对象池大小

# 应用程序配置
APP_NAME = "AI小说编辑器 2.0"           # 应用程序名称
APP_VERSION = "2.0.0"                  # 应用程序版本
APP_ORGANIZATION = "AI小说编辑器团队"    # 组织名称

# 启动画面配置
SPLASH_WIDTH = 400                     # 启动画面宽度
SPLASH_HEIGHT = 300                    # 启动画面高度
SPLASH_FONT_FAMILY = "Microsoft YaHei UI"  # 启动画面字体
SPLASH_FONT_SIZE = 12                  # 启动画面字体大小

# 数据目录名称
DIR_PROJECTS = "projects"              # 项目目录
DIR_DOCUMENTS = "documents"            # 文档目录
DIR_CHARACTERS = "characters"          # 角色目录
DIR_WORLDBUILDING = "worldbuilding"    # 世界观目录
DIR_PLOTS = "plots"                    # 情节目录
DIR_VERSIONS = "versions"              # 版本目录
DIR_BACKUPS = "backups"                # 备份目录
DIR_TEMPLATES = "templates"            # 模板目录
DIR_SEARCH_INDEX = "search_index.db"   # 搜索索引文件名

# 文本分析常量
MIN_CONTENT_LENGTH_FOR_SUGGESTIONS = 20    # 建议生成的最小内容长度
MIN_WORD_COUNT_FOR_SUGGESTIONS = 100       # 建议生成的最小字数
MAX_WORD_COUNT_FOR_SHORT_CONTENT = 2000    # 短内容的最大字数
MAX_LINE_LENGTH_THRESHOLD = 100            # 长句子阈值
MIN_DUPLICATE_LENGTH = 10                  # 重复文本的最小长度
MAX_SUGGESTION_COUNT = 10                  # 最大建议数量

# 验证常量
MIN_TITLE_LENGTH = 1                       # 标题最小长度
MAX_TITLE_LENGTH = 200                     # 标题最大长度
MIN_DESCRIPTION_LENGTH = 0                 # 描述最小长度
MAX_DESCRIPTION_LENGTH = 1000              # 描述最大长度
MIN_CONTENT_LENGTH = 0                     # 内容最小长度
MAX_CONTENT_LENGTH = 10000000              # 内容最大长度（10MB文本）

# 搜索常量
DEFAULT_SEARCH_LIMIT = 100                 # 默认搜索结果限制
MAX_SEARCH_RESULTS = 1000                  # 最大搜索结果数
SEARCH_CACHE_TTL = 3600                    # 搜索缓存生存时间（秒）

# 安全设置
MAX_LOGIN_ATTEMPTS = 5                 # 最大登录尝试次数
SESSION_TIMEOUT = 3600                 # 会话超时时间（秒）
PASSWORD_MIN_LENGTH = 8                # 密码最小长度

# 调试设置
DEBUG_MODE = False
VERBOSE_LOGGING = False
ENABLE_PROFILING = False

# 功能开关
FEATURES = {
    "ai_assistant": True,
    "cloud_sync": False,
    "collaboration": False,
    "version_control": False,
    "plugin_system": False,
    "advanced_analytics": False
}

# 统计信息
STATISTICS_RETENTION_DAYS = 365        # 统计数据保留天数
ANALYTICS_BATCH_SIZE = 100             # 分析批处理大小

# 更新设置
CHECK_UPDATES_INTERVAL = 86400         # 检查更新间隔（秒）
AUTO_UPDATE_ENABLED = False            # 自动更新开关

# 帮助和文档
HELP_URL = "https://help.ainovel.com"
DOCUMENTATION_URL = "https://docs.ainovel.com"
SUPPORT_EMAIL = "support@ainovel.com"
FEEDBACK_URL = "https://feedback.ainovel.com"

# 社交媒体
WEBSITE_URL = "https://www.ainovel.com"
GITHUB_URL = "https://github.com/ainovel/editor"
TWITTER_URL = "https://twitter.com/ainovel"

# 许可证信息
LICENSE_TYPE = "MIT"
LICENSE_URL = "https://opensource.org/licenses/MIT"

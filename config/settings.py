#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序配置

使用Pydantic进行配置管理，支持环境变量和配置文件
"""

import os
# threading 导入已移除，不再需要全局锁
from pathlib import Path
from typing import Dict, List, Optional, Any

# 配置文件常量
CONFIG_DIR_NAME = ".novel_editor"
CONFIG_FILE_NAME = "config.json"
TEMP_FILE_SUFFIX = ".tmp"
DEFAULT_ENCODING = "utf-8"
OPENAI_PROVIDER = "openai"
DEEPSEEK_PROVIDER = "deepseek"

try:
    # 尝试导入新版本的pydantic-settings
    from pydantic_settings import BaseSettings
    from pydantic import Field, field_validator
    # 新版本使用field_validator
    PYDANTIC_V2 = True
except ImportError:
    try:
        # 回退到旧版本的pydantic
        from pydantic import BaseSettings, Field, validator as field_validator
        PYDANTIC_V2 = False
    except ImportError:
        # 如果都没有，抛出错误提示安装依赖
        raise ImportError(
            "需要安装pydantic依赖: pip install pydantic pydantic-settings"
        )


class BaseConfigSettings(BaseSettings):
    """
    基础配置类

    提供通用的配置设置，减少重复代码。
    """
    class Config:
        extra = "allow"
        case_sensitive = False


class DatabaseSettings(BaseConfigSettings):
    """
    数据库配置设置类

    管理应用程序的数据库连接配置，包括连接URL、日志设置和连接池参数。
    支持通过环境变量进行配置，环境变量前缀为"DB_"。

    实现方式：
    - 继承Pydantic BaseSettings提供配置验证和环境变量支持
    - 使用Field定义字段的默认值和描述信息
    - 支持SQLite作为默认数据库，可配置为其他数据库
    - 提供连接池配置优化数据库性能

    Attributes:
        url: 数据库连接URL，默认使用SQLite
        echo: 是否输出SQL日志，用于调试
        pool_size: 数据库连接池大小
        max_overflow: 连接池最大溢出数量
    """
    url: str = Field(default="sqlite:///./novel_editor.db", description="数据库连接URL")
    echo: bool = Field(default=False, description="是否输出SQL日志")
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="连接池最大溢出")

    class Config:
        env_prefix = "DB_"


class AIServiceSettings(BaseConfigSettings):
    """
    AI服务配置设置类

    管理各种AI服务提供商的配置信息，包括API密钥、基础URL和模型设置。
    支持多个AI服务提供商，如OpenAI、DeepSeek、Claude等。

    实现方式：
    - 支持通过环境变量配置敏感信息如API密钥
    - 提供合理的默认值确保开箱即用
    - 使用Optional类型支持可选配置
    - 环境变量前缀为"AI_"便于管理

    Attributes:
        openai_api_key: OpenAI API密钥，建议通过环境变量设置
        openai_base_url: OpenAI API基础URL，支持代理或自定义端点
        openai_model: 默认使用的OpenAI模型
    """

    # OpenAI配置
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI API基础URL")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI默认模型")

    # DeepSeek配置
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API密钥")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", description="DeepSeek API基础URL")
    deepseek_model: str = Field(default="deepseek-chat", description="DeepSeek默认模型")

    # 通用AI配置
    default_provider: str = Field(default="deepseek", description="默认AI服务提供商")
    max_tokens: int = Field(default=2000, description="最大生成token数")
    temperature: float = Field(default=0.7, description="生成温度")
    timeout: int = Field(default=120, description="请求超时时间(秒)")
    retry_count: int = Field(default=3, description="重试次数")

    # 输出配置
    enable_streaming: bool = Field(default=True, description="是否启用流式输出")

    @field_validator('default_provider')
    @classmethod
    def validate_provider(cls, v):
        allowed_providers = ['openai', 'deepseek', 'local']
        if v not in allowed_providers:
            raise ValueError(f'Provider must be one of {allowed_providers}')
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v <= 0 or v > 100000:
            raise ValueError('max_tokens must be between 1 and 100000')
        return v

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0 or v > 300:
            raise ValueError('timeout must be between 1 and 300 seconds')
        return v

    @field_validator('retry_count')
    @classmethod
    def validate_retry_count(cls, v):
        if v < 0 or v > 10:
            raise ValueError('retry_count must be between 0 and 10')
        return v

    class Config:
        env_prefix = "AI_"


class UISettings(BaseConfigSettings):
    """
    用户界面配置设置类

    管理应用程序的用户界面相关配置，包括主题、字体、窗口大小和用户体验设置。
    提供界面个性化定制和用户偏好保存功能。

    实现方式：
    - 支持多种主题切换（dark、light等）
    - 提供字体和窗口大小的自定义配置
    - 包含自动保存和最近项目等用户体验功能
    - 使用验证器确保配置值的有效性

    Attributes:
        theme: 界面主题，支持dark/light等
        language: 界面语言，默认中文
        font_family: 字体族，默认微软雅黑
        font_size: 字体大小
        window_width: 默认窗口宽度
        window_height: 默认窗口高度
        auto_save_interval: 自动保存间隔时间
        recent_projects_count: 最近项目显示数量
    """
    theme: str = Field(default="dark", description="界面主题")
    language: str = Field(default="zh_CN", description="界面语言")
    font_family: str = Field(default="Microsoft YaHei UI", description="字体族")
    font_size: int = Field(default=10, description="字体大小")
    window_width: int = Field(default=1400, description="窗口宽度")
    window_height: int = Field(default=900, description="窗口高度")
    auto_save_interval: int = Field(default=30, description="自动保存间隔(秒)")
    recent_projects_count: int = Field(default=10, description="最近项目数量")

    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v):
        allowed_themes = ['light', 'dark', 'auto']
        if v not in allowed_themes:
            raise ValueError(f'Theme must be one of {allowed_themes}')
        return v

    @field_validator('font_size')
    @classmethod
    def validate_font_size(cls, v):
        if not 8 <= v <= 72:
            raise ValueError('Font size must be between 8 and 72')
        return v

    class Config:
        env_prefix = "UI_"


class LoggingSettings(BaseConfigSettings):
    """日志配置"""
    level: str = Field(default="DEBUG", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    file_path: Optional[str] = Field(default=None, description="日志文件路径")
    max_file_size: int = Field(default=10 * 1024 * 1024, description="日志文件最大大小(字节)")
    backup_count: int = Field(default=5, description="日志文件备份数量")

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of {allowed_levels}')
        return v.upper()

    class Config:
        env_prefix = "LOG_"


class PluginSettings(BaseConfigSettings):
    """插件配置"""
    enabled_plugins: List[str] = Field(default_factory=list, description="启用的插件列表")
    plugin_directories: List[str] = Field(default_factory=lambda: ["plugins"], description="插件目录列表")
    auto_load_plugins: bool = Field(default=True, description="是否自动加载插件")

    class Config:
        env_prefix = "PLUGIN_"


class SecuritySettings(BaseConfigSettings):
    """安全配置"""
    encryption_key: Optional[str] = Field(default=None, description="加密密钥")
    use_keyring: bool = Field(default=True, description="是否使用系统密钥环")
    session_timeout: int = Field(default=3600, description="会话超时时间(秒)")

    class Config:
        env_prefix = "SECURITY_"


class Settings(BaseSettings):
    """
    应用程序主配置类

    这是应用程序的核心配置类，整合了所有子模块的配置设置。
    提供统一的配置管理接口，支持环境变量、配置文件和默认值。

    实现方式：
    - 继承Pydantic BaseSettings提供强大的配置管理功能
    - 组合各个子配置类实现模块化配置管理
    - 支持.env文件和环境变量配置
    - 自动创建必要的目录结构
    - 提供配置保存和加载功能

    Attributes:
        app_name: 应用程序名称
        app_version: 应用程序版本号
        debug: 是否启用调试模式
        database: 数据库配置
        ai_service: AI服务配置
        ui: 用户界面配置
        logging: 日志配置
        plugins: 插件配置
        security: 安全配置
        project_root: 项目根目录路径
        data_dir: 数据存储目录路径
        cache_dir: 缓存目录路径
        log_dir: 日志目录路径
    """

    # 应用基本信息
    app_name: str = Field(default="AI小说编辑器", description="应用名称")
    app_version: str = Field(default="2.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")

    # 各模块配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai_service: AIServiceSettings = Field(default_factory=AIServiceSettings)
    ui: UISettings = Field(default_factory=UISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # 路径配置
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.resolve())

    @property
    def data_dir(self) -> Path:
        """数据存储目录"""
        return self.project_root / CONFIG_DIR_NAME

    @property
    def cache_dir(self) -> Path:
        """缓存目录"""
        return self.data_dir / "cache"

    @property
    def log_dir(self) -> Path:
        """日志目录"""
        return self.data_dir / "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False
        extra = "allow"

    def __init__(self, **kwargs):
        """
        初始化Settings配置实例

        调用父类初始化方法并确保必要的目录结构存在。
        自动创建数据目录、缓存目录和日志目录。

        实现方式：
        - 调用BaseSettings的初始化方法处理配置加载
        - 使用mkdir创建目录，parents=True确保父目录也被创建
        - exist_ok=True避免目录已存在时的错误

        Args:
            **kwargs: 传递给父类的配置参数
        """
        super().__init__(**kwargs)
        # 确保必要的目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def save_to_file(self, file_path: Path):
        """
        保存当前配置到JSON文件

        将配置对象序列化为JSON格式并保存到指定文件。
        兼容新旧版本的Pydantic API。

        Args:
            file_path: 保存配置的文件路径

        Raises:
            IOError: 文件写入失败时抛出
        """
        import json

        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 获取配置字典，兼容新旧版本
            if PYDANTIC_V2:
                config_dict = self.model_dump()
            else:
                config_dict = self.dict()

            # 简化的路径转换函数
            def convert_paths(obj):
                if isinstance(obj, dict):
                    return {k: convert_paths(v) for k, v in obj.items()}
                elif isinstance(obj, Path):
                    return str(obj)
                elif isinstance(obj, list):
                    return [convert_paths(item) for item in obj]
                return obj

            config_dict = convert_paths(config_dict)

            # 使用统一文件操作进行原子性写入
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("settings")
            # 线程安全地调用异步保存
            try:
                import asyncio, threading
                asyncio.get_running_loop()
                result_ref = {}
                def runner():
                    try:
                        result_ref['ok'] = asyncio.run(ops.save_json_atomic(file_path, config_dict, create_backup=True))
                    except Exception as e:
                        result_ref['error'] = e
                t = threading.Thread(target=runner, daemon=True)
                t.start(); t.join()
                if 'error' in result_ref:
                    raise result_ref['error']
            except RuntimeError:
                # 无运行中事件循环
                import asyncio
                asyncio.run(ops.save_json_atomic(file_path, config_dict, create_backup=True))

        except Exception as e:
            raise IOError(f"保存配置文件失败: {e}") from e

    @classmethod
    def load_from_file(cls, file_path: Path) -> 'Settings':
        """从文件加载配置"""
        import json

        if not file_path.exists():
            return cls()

        try:
            # 使用统一文件操作进行读取
            from src.shared.utils.file_operations import get_file_operations
            import asyncio
            ops = get_file_operations("settings")
            loop = asyncio.get_event_loop()
            config_dict = loop.run_until_complete(ops.load_json_cached(file_path))
            if not config_dict:
                return cls()
            if not isinstance(config_dict, dict):
                raise ValueError("配置文件格式无效：根对象必须是字典")
            return cls(**config_dict)

        except (ValueError, TypeError) as e:
            # 配置文件损坏，返回默认配置
            print(f"警告：配置文件损坏 ({e})，使用默认配置")
            return cls()
        except Exception as e:
            # 其他错误，也返回默认配置
            print(f"警告：加载配置文件失败 ({e})，使用默认配置")
            return cls()

    def get_ai_config(self, provider: str = None) -> Dict[str, Any]:
        """获取AI服务配置"""
        provider = provider or self.ai_service.default_provider

        if provider == OPENAI_PROVIDER:
            return {
                "api_key": self.ai_service.openai_api_key,
                "base_url": self.ai_service.openai_base_url,
                "model": self.ai_service.openai_model,
                "max_tokens": self.ai_service.max_tokens,
                "temperature": self.ai_service.temperature,
                "timeout": self.ai_service.timeout
            }
        elif provider == DEEPSEEK_PROVIDER:
            return {
                "api_key": self.ai_service.deepseek_api_key,
                "base_url": self.ai_service.deepseek_base_url,
                "model": self.ai_service.deepseek_model,
                "max_tokens": self.ai_service.max_tokens,
                "temperature": self.ai_service.temperature,
                "timeout": self.ai_service.timeout
            }
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

    def validate_ai_config(self) -> List[str]:
        """验证AI配置"""
        errors = []

        if not self.ai_service.openai_api_key and not self.ai_service.deepseek_api_key:
            errors.append("至少需要配置一个AI服务的API密钥")

        if self.ai_service.default_provider == OPENAI_PROVIDER and not self.ai_service.openai_api_key:
            errors.append("默认使用OpenAI但未配置API密钥")

        if self.ai_service.default_provider == DEEPSEEK_PROVIDER and not self.ai_service.deepseek_api_key:
            errors.append("默认使用DeepSeek但未配置API密钥")

        return errors


# 全局单例已移除，现在只支持项目作用域的设置


# ——— 新增：项目作用域的设置/DB辅助函数 ———
_project_settings_cache: dict[str, Settings] = {}


def get_settings_for_project(project_root: Path) -> Settings:
    """按项目根路径加载/缓存配置，存放于项目内 .novel_editor/config.json。"""
    from src.shared.project_context import ProjectPaths, ensure_project_dirs

    root = Path(project_root).resolve()
    key = str(root)
    cached = _project_settings_cache.get(key)
    if cached:
        return cached

    paths = ProjectPaths(root)
    ensure_project_dirs(paths)
    config_file = paths.config_file

    try:
        if config_file.exists():
            settings = Settings.load_from_file(config_file)
        else:
            settings = Settings()
        # 覆盖项目根路径，确保 Settings.data_dir 指向项目内
        try:
            settings.project_root = root
        except Exception:
            pass
        # 保存回项目配置
        settings.save_to_file(config_file)
    except Exception as e:
        print(f"项目设置加载失败，使用默认配置: {e}")
        settings = Settings()
        try:
            settings.project_root = root
        except Exception:
            pass

    _project_settings_cache[key] = settings
    return settings


def reload_settings_for_project(project_root: Path) -> Settings:
    """强制从项目内配置文件重新加载 Settings（绕过缓存）。"""
    global _project_settings_cache
    try:
        root = Path(project_root).resolve()
        key = str(root)
        # 丢弃缓存
        if key in _project_settings_cache:
            try:
                del _project_settings_cache[key]
            except Exception:
                _project_settings_cache.pop(key, None)
        # 重新加载
        return get_settings_for_project(root)
    except Exception as e:
        print(f"⚠️ 重新加载项目配置失败，返回当前默认设置: {e}")
        return get_settings_for_project(project_root)



def db_url_for_project(project_root: Path) -> str:
    """返回项目内 SQLite 数据库 URL（如需数据库）。"""
    from src.shared.project_context import ProjectPaths, ensure_project_dirs

    paths = ProjectPaths(Path(project_root))
    ensure_project_dirs(paths)
    return f"sqlite:///{paths.sqlite_db.as_posix()}"


# reset_settings 函数已移除，现在使用项目作用域的设置


# reload_settings 函数已移除，现在使用项目作用域的设置


def update_ai_provider_for_project(project_root: Path, provider: str) -> bool:
    """
    动态更新项目的AI提供商

    Args:
        project_root: 项目根目录
        provider: 新的提供商名称 ('openai', 'deepseek')

    Returns:
        bool: 是否更新成功
    """
    try:
        settings = get_settings_for_project(project_root)

        # 更新提供商
        old_provider = settings.ai_service.default_provider
        settings.ai_service.default_provider = provider

        # 保存到项目配置文件
        from src.shared.project_context import ProjectPaths, ensure_project_dirs
        paths = ProjectPaths(project_root)
        ensure_project_dirs(paths)
        settings.save_to_file(paths.config_file)

        print(f"🔄 项目AI提供商已从 {old_provider} 更新为 {provider}")

        # 通知AI客户端管理器重新加载配置
        _notify_ai_config_change()

        return True

    except Exception as e:
        print(f"❌ 更新项目AI提供商失败: {e}")
        return False


def _notify_ai_config_change():
    """通知AI相关组件配置已更改"""
    try:
        # AI客户端配置变更通知（新架构会自动处理）
        print("🔄 AI客户端配置已更新")
    except ImportError:
        # 如果模块还没有加载，忽略
        pass
    except Exception as e:
        print(f"⚠️ 通知AI配置更改失败: {e}")

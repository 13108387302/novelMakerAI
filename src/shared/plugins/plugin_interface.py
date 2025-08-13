#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件接口定义

定义插件系统的核心接口和基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import inspect

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class PluginType(Enum):
    """
    插件类型枚举

    定义插件系统支持的不同类型插件。
    用于插件分类和功能识别。

    Values:
        EDITOR: 编辑器插件，扩展编辑器功能
        AI_ASSISTANT: AI助手插件，提供AI辅助功能
        EXPORT: 导出插件，支持不同格式的导出
        IMPORT: 导入插件，支持不同格式的导入
        THEME: 主题插件，提供界面主题
        TOOL: 工具插件，提供实用工具
        WIDGET: UI组件插件，扩展界面组件
        SERVICE: 服务插件，提供后台服务
    """
    EDITOR = "editor"           # 编辑器插件
    AI_ASSISTANT = "ai"         # AI助手插件
    EXPORT = "export"           # 导出插件
    IMPORT = "import"           # 导入插件
    THEME = "theme"             # 主题插件
    TOOL = "tool"               # 工具插件
    WIDGET = "widget"           # UI组件插件
    SERVICE = "service"         # 服务插件


class PluginStatus(Enum):
    """
    插件状态枚举

    定义插件在运行时的不同状态。
    用于插件生命周期管理和状态跟踪。

    Values:
        DISABLED: 禁用状态，插件未激活
        ENABLED: 启用状态，插件正常运行
        ERROR: 错误状态，插件运行异常
        LOADING: 加载中状态，插件正在初始化
    """
    DISABLED = "disabled"       # 禁用
    ENABLED = "enabled"         # 启用
    ERROR = "error"             # 错误
    LOADING = "loading"         # 加载中


@dataclass
class PluginInfo:
    """
    插件信息数据类

    存储插件的元数据信息，包括基本信息、依赖关系和版本要求。

    Attributes:
        id: 插件唯一标识符
        name: 插件显示名称
        version: 插件版本号
        description: 插件描述
        author: 插件作者
        plugin_type: 插件类型
        dependencies: 依赖的其他插件列表
        min_app_version: 最低应用程序版本要求
        max_app_version: 最高应用程序版本要求
        config_schema: 配置模式定义
        entry_point: 插件入口点
    """
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str]
    min_app_version: str
    max_app_version: str = ""
    homepage: str = ""
    license: str = "MIT"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class PluginHook:
    """插件钩子"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.callbacks: List[Callable] = []
    
    def register(self, callback: Callable):
        """注册回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            logger.debug(f"插件钩子 {self.name} 注册回调: {callback.__name__}")
    
    def unregister(self, callback: Callable):
        """取消注册回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.debug(f"插件钩子 {self.name} 取消注册回调: {callback.__name__}")
    
    def execute(self, *args, **kwargs) -> List[Any]:
        """执行所有回调函数"""
        results = []
        for callback in self.callbacks:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"插件钩子 {self.name} 执行回调 {callback.__name__} 失败: {e}")
        return results


class IPlugin(ABC):
    """插件接口"""
    
    def __init__(self):
        self._info: Optional[PluginInfo] = None
        self._status: PluginStatus = PluginStatus.DISABLED
        self._context: Optional['PluginContext'] = None
    
    @property
    def info(self) -> PluginInfo:
        """获取插件信息"""
        if self._info is None:
            self._info = self.get_plugin_info()
        return self._info
    
    @property
    def status(self) -> PluginStatus:
        """获取插件状态"""
        return self._status
    
    @property
    def context(self) -> 'PluginContext':
        """获取插件上下文"""
        return self._context
    
    def set_context(self, context: 'PluginContext'):
        """设置插件上下文"""
        self._context = context
    
    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def activate(self) -> bool:
        """激活插件"""
        pass
    
    @abstractmethod
    def deactivate(self) -> bool:
        """停用插件"""
        pass
    
    @abstractmethod
    def cleanup(self) -> bool:
        """清理插件资源"""
        pass
    
    def get_settings_schema(self) -> Optional[Dict[str, Any]]:
        """获取设置模式（可选）"""
        return None
    
    def get_settings(self) -> Dict[str, Any]:
        """获取插件设置"""
        if self._context:
            return self._context.get_plugin_settings(self.info.id)
        return {}
    
    def set_settings(self, settings: Dict[str, Any]):
        """设置插件配置"""
        if self._context:
            self._context.set_plugin_settings(self.info.id, settings)
    
    def register_hook(self, hook_name: str, callback: Callable):
        """注册钩子回调"""
        if self._context:
            self._context.register_hook(hook_name, callback)
    
    def unregister_hook(self, hook_name: str, callback: Callable):
        """取消注册钩子回调"""
        if self._context:
            self._context.unregister_hook(hook_name, callback)
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """执行钩子"""
        if self._context:
            return self._context.execute_hook(hook_name, *args, **kwargs)
        return []
    
    def get_api(self, service_name: str) -> Any:
        """获取应用程序API"""
        if self._context:
            return self._context.get_api(service_name)
        return None
    
    def log_info(self, message: str):
        """记录信息日志"""
        logger.info(f"[{self.info.id}] {message}")
    
    def log_warning(self, message: str):
        """记录警告日志"""
        logger.warning(f"[{self.info.id}] {message}")
    
    def log_error(self, message: str):
        """记录错误日志"""
        logger.error(f"[{self.info.id}] {message}")


class PluginContext:
    """插件上下文"""

    def __init__(self, app_context: Any):
        self.app_context = app_context
        self._hooks: Dict[str, PluginHook] = {}
        self._plugin_settings: Dict[str, Dict[str, Any]] = {}

    def register_hook(self, hook_name: str, callback: Callable):
        """注册钩子回调"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = PluginHook(hook_name)
        self._hooks[hook_name].register(callback)

    def unregister_hook(self, hook_name: str, callback: Callable):
        """取消注册钩子回调"""
        if hook_name in self._hooks:
            self._hooks[hook_name].unregister(callback)

    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """执行钩子"""
        if hook_name in self._hooks:
            return self._hooks[hook_name].execute(*args, **kwargs)
        return []

    def get_plugin_settings(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件设置"""
        return self._plugin_settings.get(plugin_id, {})

    def set_plugin_settings(self, plugin_id: str, settings: Dict[str, Any]):
        """设置插件配置"""
        self._plugin_settings[plugin_id] = settings

    def get_api(self, service_name: str) -> Any:
        """获取应用程序API"""
        # 这里可以根据service_name返回相应的服务实例
        if hasattr(self.app_context, service_name):
            return getattr(self.app_context, service_name)
        return None

    # ========= 扩展：导出格式注册（供导出类插件调用） =========
    def register_export_format(self, format_name: str, extensions: List[str], plugin: 'IPlugin') -> None:
        """
        允许插件向导入导出服务注册导出处理器。
        每个扩展名（去掉点）将注册为一个 format_type 对应的处理器。
        """
        try:
            # 延迟导入，避免循环依赖
            from src.application.services.import_export.base import BaseFormatHandler, ExportOptions, ImportOptions
            import asyncio

            # 获取服务
            service = None
            try:
                container = getattr(self.app_context, 'container', None)
                if container:
                    from src.application.services.import_export_service import ImportExportService
                    service = container.get(ImportExportService)
            except Exception:
                service = None
            if not service:
                return

            class PluginExportFormatHandler(BaseFormatHandler):
                def __init__(self, svc, plug, fmt_name, exts):
                    super().__init__(svc)
                    self._plugin = plug
                    self._format_name = fmt_name
                    self._extensions = [e if e.startswith('.') else f'.{e}' for e in (exts or [])]

                def get_supported_extensions(self) -> List[str]:
                    return self._extensions

                def get_format_name(self) -> str:
                    return self._format_name

                async def _do_export_project(self, project, output_path, options: ExportOptions) -> bool:
                    # 合并导出参数
                    base_opts = {}
                    try:
                        base_opts = dict(getattr(self._plugin, 'export_options', {}) or {})
                    except Exception:
                        base_opts = {}
                    fmt_opts = {}
                    try:
                        fmt_opts = dict(getattr(options, 'format_options', {}) or {})
                    except Exception:
                        fmt_opts = {}
                    merged = {**base_opts, **fmt_opts}
                    merged.setdefault('encoding', getattr(options, 'output_encoding', 'utf-8'))
                    # 同步方法放入线程池
                    return await asyncio.to_thread(self._plugin.export_project, project, output_path, merged)

                async def _do_export_document(self, document, output_path, options: ExportOptions) -> bool:
                    base_opts = {}
                    try:
                        base_opts = dict(getattr(self._plugin, 'export_options', {}) or {})
                    except Exception:
                        base_opts = {}
                    fmt_opts = {}
                    try:
                        fmt_opts = dict(getattr(options, 'format_options', {}) or {})
                    except Exception:
                        fmt_opts = {}
                    merged = {**base_opts, **fmt_opts}
                    merged.setdefault('encoding', getattr(options, 'output_encoding', 'utf-8'))
                    return await asyncio.to_thread(self._plugin.export_document, document, output_path, merged)

            handler = PluginExportFormatHandler(service, plugin, format_name, extensions)

            # 为每个扩展名注册处理器（去掉点作为键）
            for ext in (extensions or []):
                key = (ext[1:] if ext.startswith('.') else ext).lower()
                try:
                    service.register_format_handler(key, handler)
                except Exception:
                    pass
            # 也尝试用格式名注册（方便显式指定）
            try:
                service.register_format_handler(format_name.lower(), handler)
            except Exception:
                pass
        except Exception as e:
            # 不影响主流程
            import traceback
            logger = get_logger(__name__)
            logger.debug(f"register_export_format 失败: {e}\n{traceback.format_exc()}")


class PluginException(Exception):
    """插件异常"""
    
    def __init__(self, plugin_id: str, message: str, cause: Exception = None):
        self.plugin_id = plugin_id
        self.message = message
        self.cause = cause
        super().__init__(f"Plugin {plugin_id}: {message}")


# 预定义的钩子名称
class PluginHooks:
    """预定义的插件钩子"""
    
    # 应用程序生命周期
    APP_STARTUP = "app_startup"
    APP_SHUTDOWN = "app_shutdown"
    
    # 项目生命周期
    PROJECT_CREATED = "project_created"
    PROJECT_OPENED = "project_opened"
    PROJECT_CLOSED = "project_closed"
    PROJECT_SAVED = "project_saved"
    
    # 文档生命周期
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_OPENED = "document_opened"
    DOCUMENT_CLOSED = "document_closed"
    DOCUMENT_SAVED = "document_saved"
    DOCUMENT_MODIFIED = "document_modified"
    
    # 编辑器事件
    TEXT_CHANGED = "text_changed"
    SELECTION_CHANGED = "selection_changed"
    CURSOR_MOVED = "cursor_moved"
    
    # AI事件
    AI_REQUEST_STARTED = "ai_request_started"
    AI_REQUEST_COMPLETED = "ai_request_completed"
    AI_REQUEST_FAILED = "ai_request_failed"
    
    # UI事件
    MENU_CREATED = "menu_created"
    TOOLBAR_CREATED = "toolbar_created"
    STATUSBAR_CREATED = "statusbar_created"
    
    # 导入导出事件
    EXPORT_STARTED = "export_started"
    EXPORT_COMPLETED = "export_completed"
    IMPORT_STARTED = "import_started"
    IMPORT_COMPLETED = "import_completed"


def plugin_info(**kwargs):
    """插件信息装饰器"""
    def decorator(cls):
        # 将插件信息存储在类属性中
        cls._plugin_info_data = kwargs
        return cls
    return decorator


def hook(hook_name: str):
    """钩子装饰器"""
    def decorator(func):
        func._hook_name = hook_name
        return func
    return decorator


# 专门的插件基类

class EditorPlugin(IPlugin):
    """
    编辑器插件基类

    为编辑器功能扩展提供的专门插件基类。
    """

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（子类必须实现）"""
        pass

    def on_initialize(self) -> bool:
        """初始化插件（子类可重写）"""
        return True

    def on_activate(self) -> bool:
        """激活插件（子类可重写）"""
        return True

    def on_deactivate(self) -> bool:
        """停用插件（子类可重写）"""
        return True

    def on_cleanup(self) -> bool:
        """清理插件（子类可重写）"""
        return True

    # 实现抽象方法
    def initialize(self) -> bool:
        return self.on_initialize()

    def activate(self) -> bool:
        return self.on_activate()

    def deactivate(self) -> bool:
        return self.on_deactivate()

    def cleanup(self) -> bool:
        return self.on_cleanup()


class ExportPlugin(IPlugin):
    """
    导出插件基类

    为导出功能提供的专门插件基类。
    """

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（子类必须实现）"""
        pass

    @abstractmethod
    def export_project(self, project, output_path: Path, options: Dict[str, Any] = None) -> bool:
        """
        导出项目

        Args:
            project: 要导出的项目对象
            output_path: 输出文件路径
            options: 导出选项

        Returns:
            bool: 导出是否成功
        """
        pass

    @abstractmethod
    def export_document(self, document, output_path: Path, options: Dict[str, Any] = None) -> bool:
        """
        导出文档

        Args:
            document: 要导出的文档对象
            output_path: 输出文件路径
            options: 导出选项

        Returns:
            bool: 导出是否成功
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的导出格式

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        pass

    def get_export_options(self) -> Dict[str, Any]:
        """
        获取导出选项配置

        Returns:
            Dict[str, Any]: 导出选项配置
        """
        return {}

    def on_initialize(self) -> bool:
        """初始化插件（子类可重写）"""
        return True

    def on_activate(self) -> bool:
        """激活插件（子类可重写）"""
        return True

    def on_deactivate(self) -> bool:
        """停用插件（子类可重写）"""
        return True

    def on_cleanup(self) -> bool:
        """清理插件（子类可重写）"""
        return True

    # 实现抽象方法
    def initialize(self) -> bool:
        return self.on_initialize()

    def activate(self) -> bool:
        return self.on_activate()

    def deactivate(self) -> bool:
        return self.on_deactivate()

    def cleanup(self) -> bool:
        return self.on_cleanup()


class ImportPlugin(IPlugin):
    """
    导入插件基类

    为导入功能提供的专门插件基类。
    """

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（子类必须实现）"""
        pass

    @abstractmethod
    def import_project(self, input_path: Path, options: Dict[str, Any] = None):
        """
        导入项目

        Args:
            input_path: 输入文件路径
            options: 导入选项

        Returns:
            导入的项目对象或None
        """
        pass

    @abstractmethod
    def import_document(self, input_path: Path, options: Dict[str, Any] = None):
        """
        导入文档

        Args:
            input_path: 输入文件路径
            options: 导入选项

        Returns:
            导入的文档对象或None
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的导入格式

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        pass

    def get_import_options(self) -> Dict[str, Any]:
        """
        获取导入选项配置

        Returns:
            Dict[str, Any]: 导入选项配置
        """
        return {}

    def on_initialize(self) -> bool:
        """初始化插件（子类可重写）"""
        return True

    def on_activate(self) -> bool:
        """激活插件（子类可重写）"""
        return True

    def on_deactivate(self) -> bool:
        """停用插件（子类可重写）"""
        return True

    def on_cleanup(self) -> bool:
        """清理插件（子类可重写）"""
        return True

    # 实现抽象方法
    def initialize(self) -> bool:
        return self.on_initialize()

    def activate(self) -> bool:
        return self.on_activate()

    def deactivate(self) -> bool:
        return self.on_deactivate()

    def cleanup(self) -> bool:
        return self.on_cleanup()


class AIAssistantPlugin(IPlugin):
    """
    AI助手插件基类

    为AI助手功能提供的专门插件基类。
    """

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（子类必须实现）"""
        pass

    @abstractmethod
    def process_request(self, request_type: str, content: str, options: Dict[str, Any] = None) -> str:
        """
        处理AI请求

        Args:
            request_type: 请求类型
            content: 输入内容
            options: 处理选项

        Returns:
            str: 处理结果
        """
        pass

    def get_supported_requests(self) -> List[str]:
        """
        获取支持的请求类型

        Returns:
            List[str]: 支持的请求类型列表
        """
        return []

    def on_initialize(self) -> bool:
        """初始化插件（子类可重写）"""
        return True

    def on_activate(self) -> bool:
        """激活插件（子类可重写）"""
        return True

    def on_deactivate(self) -> bool:
        """停用插件（子类可重写）"""
        return True

    def on_cleanup(self) -> bool:
        """清理插件（子类可重写）"""
        return True

    # 实现抽象方法
    def initialize(self) -> bool:
        return self.on_initialize()

    def activate(self) -> bool:
        return self.on_activate()

    def deactivate(self) -> bool:
        return self.on_deactivate()

    def cleanup(self) -> bool:
        return self.on_cleanup()


# 便捷函数
def create_plugin_info(plugin_id: str, name: str, version: str, description: str,
                      author: str, plugin_type: PluginType, dependencies: List[str] = None,
                      min_app_version: str = "1.0.0", max_app_version: str = "",
                      homepage: str = "", license: str = "MIT", tags: List[str] = None) -> PluginInfo:
    """
    创建插件信息的便捷函数

    Args:
        plugin_id: 插件ID
        name: 插件名称
        version: 版本号
        description: 描述
        author: 作者
        plugin_type: 插件类型
        dependencies: 依赖列表
        min_app_version: 最低应用版本
        max_app_version: 最高应用版本
        homepage: 主页
        license: 许可证
        tags: 标签列表

    Returns:
        PluginInfo: 插件信息对象
    """
    return PluginInfo(
        id=plugin_id,
        name=name,
        version=version,
        description=description,
        author=author,
        plugin_type=plugin_type,
        dependencies=dependencies or [],
        min_app_version=min_app_version,
        max_app_version=max_app_version,
        homepage=homepage,
        license=license,
        tags=tags or []
    )

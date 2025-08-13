#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理器

负责插件的加载、管理和生命周期控制
"""

import os
import sys
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
import traceback

from src.shared.plugins.plugin_interface import (
    IPlugin, PluginInfo, PluginStatus, PluginType, PluginContext,
    PluginException, PluginHooks
)
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class PluginManager:
    """
    插件管理器

    负责插件的发现、加载、管理和生命周期控制。
    提供插件的动态加载、卸载和配置管理功能。

    实现方式：
    - 扫描插件目录发现可用插件
    - 动态加载和实例化插件模块
    - 管理插件的启用/禁用状态
    - 处理插件依赖关系和版本兼容性
    - 提供插件配置的持久化存储
    - 支持插件的热加载和卸载

    Attributes:
        app_context: 应用程序上下文
        plugins_dir: 插件目录路径
        context: 插件上下文对象
        _plugins: 已加载的插件实例字典
        _plugin_modules: 插件模块字典
        _plugin_status: 插件状态字典
        _config: 插件配置字典
    """

    def __init__(self, app_context: Any, plugins_dir: Path = None):
        """
        初始化插件管理器

        Args:
            app_context: 应用程序上下文对象
            plugins_dir: 插件目录路径，默认为"plugins"
        """
        self.app_context = app_context
        self.plugins_dir = plugins_dir or Path("plugins")
        self.plugins_dir.mkdir(exist_ok=True)

        # 插件存储
        self._plugins: Dict[str, IPlugin] = {}
        self._plugin_modules: Dict[str, Any] = {}
        self._plugin_status: Dict[str, PluginStatus] = {}

        # 插件上下文
        self.context = PluginContext(app_context)

        # 插件配置
        self._config_file = self.plugins_dir / "plugins.json"
        self._config = self._load_config()

        logger.info("插件管理器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载插件配置"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载插件配置失败: {e}")
        
        return {
            "enabled_plugins": [],
            "disabled_plugins": [],
            "plugin_settings": {}
        }
    
    def _save_config(self):
        """保存插件配置"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存插件配置失败: {e}")
    
    def discover_plugins(self) -> List[str]:
        """发现插件"""
        discovered = []
        
        try:
            # 扫描插件目录
            for item in self.plugins_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # 检查是否有插件入口文件
                    plugin_file = item / "plugin.py"
                    manifest_file = item / "manifest.json"
                    
                    if plugin_file.exists() or manifest_file.exists():
                        discovered.append(item.name)
                        logger.debug(f"发现插件: {item.name}")
            
            logger.info(f"发现 {len(discovered)} 个插件")
            
        except Exception as e:
            logger.error(f"发现插件失败: {e}")
        
        return discovered
    
    def load_plugin(self, plugin_id: str) -> bool:
        """加载插件"""
        try:
            if plugin_id in self._plugins:
                logger.warning(f"插件 {plugin_id} 已经加载")
                return True
            
            plugin_dir = self.plugins_dir / plugin_id
            if not plugin_dir.exists():
                raise PluginException(plugin_id, "插件目录不存在")
            
            # 加载插件模块
            plugin_module = self._load_plugin_module(plugin_id, plugin_dir)
            if not plugin_module:
                return False
            
            # 创建插件实例
            plugin_instance = self._create_plugin_instance(plugin_id, plugin_module)
            if not plugin_instance:
                return False
            
            # 设置插件上下文
            plugin_instance.set_context(self.context)
            
            # 初始化插件
            if not plugin_instance.initialize():
                raise PluginException(plugin_id, "插件初始化失败")
            
            # 存储插件
            self._plugins[plugin_id] = plugin_instance
            self._plugin_modules[plugin_id] = plugin_module
            self._plugin_status[plugin_id] = PluginStatus.ENABLED
            
            logger.info(f"插件 {plugin_id} 加载成功")
            return True
            
        except Exception as e:
            logger.error(f"加载插件 {plugin_id} 失败: {e}")
            self._plugin_status[plugin_id] = PluginStatus.ERROR
            return False
    
    def _load_plugin_module(self, plugin_id: str, plugin_dir: Path):
        """加载插件模块"""
        try:
            # 尝试加载 plugin.py
            plugin_file = plugin_dir / "plugin.py"
            if plugin_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{plugin_id}",
                    plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"plugins.{plugin_id}"] = module
                spec.loader.exec_module(module)
                return module
            
            # 尝试加载包模块
            if (plugin_dir / "__init__.py").exists():
                sys.path.insert(0, str(self.plugins_dir))
                try:
                    module = importlib.import_module(plugin_id)
                    return module
                finally:
                    sys.path.remove(str(self.plugins_dir))
            
            raise PluginException(plugin_id, "找不到插件入口文件")
            
        except Exception as e:
            logger.error(f"加载插件模块 {plugin_id} 失败: {e}")
            raise
    
    def _create_plugin_instance(self, plugin_id: str, module) -> Optional[IPlugin]:
        """创建插件实例"""
        try:
            # 查找插件类
            plugin_classes = []

            # 查找所有实现了IPlugin接口的类
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and
                    issubclass(obj, IPlugin) and
                    obj != IPlugin):
                    plugin_classes.append((name, obj))

            if not plugin_classes:
                raise PluginException(plugin_id, "找不到插件类")

            # 优先选择具体的插件类（非抽象类）
            plugin_class = None
            for name, cls in plugin_classes:
                # 检查是否为抽象类
                if not getattr(cls, '__abstractmethods__', None):
                    plugin_class = cls
                    logger.debug(f"选择具体插件类: {name}")
                    break

            # 如果没有找到具体类，选择第一个
            if not plugin_class:
                plugin_class = plugin_classes[0][1]
                logger.warning(f"未找到具体插件类，使用: {plugin_classes[0][0]}")

            # 创建实例
            instance = plugin_class()
            return instance

        except Exception as e:
            logger.error(f"创建插件实例 {plugin_id} 失败: {e}")
            raise
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        try:
            if plugin_id not in self._plugins:
                logger.warning(f"插件 {plugin_id} 未加载")
                return True
            
            plugin = self._plugins[plugin_id]
            
            # 停用插件
            if plugin.status == PluginStatus.ENABLED:
                plugin.deactivate()
            
            # 清理插件
            plugin.cleanup()
            
            # 移除插件
            del self._plugins[plugin_id]
            if plugin_id in self._plugin_modules:
                del self._plugin_modules[plugin_id]
            
            self._plugin_status[plugin_id] = PluginStatus.DISABLED
            
            logger.info(f"插件 {plugin_id} 卸载成功")
            return True
            
        except Exception as e:
            logger.error(f"卸载插件 {plugin_id} 失败: {e}")
            return False
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        try:
            if plugin_id not in self._plugins:
                # 先加载插件
                if not self.load_plugin(plugin_id):
                    return False
            
            plugin = self._plugins[plugin_id]
            
            if plugin.status == PluginStatus.ENABLED:
                logger.warning(f"插件 {plugin_id} 已经启用")
                return True
            
            # 激活插件
            if plugin.activate():
                self._plugin_status[plugin_id] = PluginStatus.ENABLED
                
                # 更新配置
                if plugin_id not in self._config["enabled_plugins"]:
                    self._config["enabled_plugins"].append(plugin_id)
                if plugin_id in self._config["disabled_plugins"]:
                    self._config["disabled_plugins"].remove(plugin_id)
                self._save_config()
                
                logger.info(f"插件 {plugin_id} 启用成功")
                return True
            else:
                self._plugin_status[plugin_id] = PluginStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"启用插件 {plugin_id} 失败: {e}")
            self._plugin_status[plugin_id] = PluginStatus.ERROR
            return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        try:
            if plugin_id not in self._plugins:
                logger.warning(f"插件 {plugin_id} 未加载")
                return True
            
            plugin = self._plugins[plugin_id]
            
            if plugin.status != PluginStatus.ENABLED:
                logger.warning(f"插件 {plugin_id} 未启用")
                return True
            
            # 停用插件
            if plugin.deactivate():
                self._plugin_status[plugin_id] = PluginStatus.DISABLED
                
                # 更新配置
                if plugin_id in self._config["enabled_plugins"]:
                    self._config["enabled_plugins"].remove(plugin_id)
                if plugin_id not in self._config["disabled_plugins"]:
                    self._config["disabled_plugins"].append(plugin_id)
                self._save_config()
                
                logger.info(f"插件 {plugin_id} 禁用成功")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"禁用插件 {plugin_id} 失败: {e}")
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)
    
    def get_plugins(self) -> Dict[str, IPlugin]:
        """获取所有插件"""
        return self._plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[IPlugin]:
        """按类型获取插件"""
        return [
            plugin for plugin in self._plugins.values()
            if plugin.info.plugin_type == plugin_type
        ]
    
    def get_plugin_status(self, plugin_id: str) -> PluginStatus:
        """获取插件状态"""
        return self._plugin_status.get(plugin_id, PluginStatus.DISABLED)
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        plugin = self.get_plugin(plugin_id)
        return plugin.info if plugin else None
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """执行钩子"""
        return self.context.execute_hook(hook_name, *args, **kwargs)
    
    def load_all_plugins(self):
        """加载所有插件并按配置启用（未显式禁用的默认启用）"""
        discovered = self.discover_plugins()

        for plugin_id in discovered:
            try:
                loaded = self.load_plugin(plugin_id)

                # 默认策略：未显式放入 disabled 列表的都启用
                if plugin_id in self._config.get("disabled_plugins", []):
                    logger.info(f"插件 {plugin_id} 在禁用列表中，跳过启用")
                    continue
                # 若配置中已启用或未配置，执行启用
                if plugin_id in self._config.get("enabled_plugins", []) or loaded:
                    self.enable_plugin(plugin_id)

            except Exception as e:
                logger.error(f"加载插件 {plugin_id} 时发生错误: {e}")

    def shutdown(self):
        """关闭插件管理器"""
        logger.info("正在关闭插件管理器...")
        
        # 执行关闭钩子
        self.execute_hook(PluginHooks.APP_SHUTDOWN)
        
        # 卸载所有插件
        plugin_ids = list(self._plugins.keys())
        for plugin_id in plugin_ids:
            self.unload_plugin(plugin_id)
        
        logger.info("插件管理器已关闭")
    
    def get_plugin_settings(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件设置"""
        return self._config["plugin_settings"].get(plugin_id, {})
    
    def set_plugin_settings(self, plugin_id: str, settings: Dict[str, Any]):
        """设置插件配置"""
        self._config["plugin_settings"][plugin_id] = settings
        self._save_config()
        
        # 通知插件设置已更改
        plugin = self.get_plugin(plugin_id)
        if plugin:
            plugin.set_settings(settings)

    def install_plugin(self, plugin_path: Path) -> bool:
        """安装插件"""
        try:
            import shutil

            if plugin_path.is_file():
                # 如果是zip文件，解压到插件目录
                if plugin_path.suffix == '.zip':
                    import zipfile
                    with zipfile.ZipFile(plugin_path, 'r') as zip_ref:
                        # 获取插件名称（假设zip文件名就是插件名）
                        plugin_name = plugin_path.stem
                        plugin_dir = self.plugins_dir / plugin_name
                        plugin_dir.mkdir(exist_ok=True)
                        zip_ref.extractall(plugin_dir)

                        logger.info(f"插件 {plugin_name} 安装成功")
                        return True
            elif plugin_path.is_dir():
                # 如果是目录，复制到插件目录
                plugin_name = plugin_path.name
                target_dir = self.plugins_dir / plugin_name

                if target_dir.exists():
                    shutil.rmtree(target_dir)

                shutil.copytree(plugin_path, target_dir)
                logger.info(f"插件 {plugin_name} 安装成功")
                return True

            return False

        except Exception as e:
            logger.error(f"安装插件失败: {e}")
            return False

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        try:
            # 先禁用插件
            self.disable_plugin(plugin_id)

            # 卸载插件
            self.unload_plugin(plugin_id)

            # 删除插件目录
            plugin_dir = self.plugins_dir / plugin_id
            if plugin_dir.exists():
                import shutil
                shutil.rmtree(plugin_dir)

            # 从配置中移除
            if plugin_id in self._config["enabled_plugins"]:
                self._config["enabled_plugins"].remove(plugin_id)
            if plugin_id in self._config["disabled_plugins"]:
                self._config["disabled_plugins"].remove(plugin_id)
            if plugin_id in self._config["plugin_settings"]:
                del self._config["plugin_settings"][plugin_id]

            self._save_config()

            logger.info(f"插件 {plugin_id} 卸载成功")
            return True

        except Exception as e:
            logger.error(f"卸载插件 {plugin_id} 失败: {e}")
            return False

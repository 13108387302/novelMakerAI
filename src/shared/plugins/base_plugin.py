#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件基类

提供插件开发的基础类和工具函数
"""

from typing import Dict, Any, Optional, List
from abc import abstractmethod
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject, pyqtSignal

from src.shared.plugins.plugin_interface import (
    IPlugin, PluginInfo, PluginType, PluginStatus, hook
)
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class BasePlugin(IPlugin):
    """插件基类"""
    
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._activated = False
    
    def initialize(self) -> bool:
        """初始化插件"""
        try:
            if self._initialized:
                return True
            
            self.log_info("正在初始化插件...")
            
            # 执行初始化逻辑
            if self.on_initialize():
                self._initialized = True
                self._status = PluginStatus.DISABLED
                self.log_info("插件初始化成功")
                return True
            else:
                self.log_error("插件初始化失败")
                self._status = PluginStatus.ERROR
                return False
                
        except Exception as e:
            self.log_error(f"插件初始化异常: {e}")
            self._status = PluginStatus.ERROR
            return False
    
    def activate(self) -> bool:
        """激活插件"""
        try:
            if not self._initialized:
                self.log_error("插件未初始化，无法激活")
                return False
            
            if self._activated:
                return True
            
            self.log_info("正在激活插件...")
            
            # 执行激活逻辑
            if self.on_activate():
                self._activated = True
                self._status = PluginStatus.ENABLED
                self.log_info("插件激活成功")
                return True
            else:
                self.log_error("插件激活失败")
                self._status = PluginStatus.ERROR
                return False
                
        except Exception as e:
            self.log_error(f"插件激活异常: {e}")
            self._status = PluginStatus.ERROR
            return False
    
    def deactivate(self) -> bool:
        """停用插件"""
        try:
            if not self._activated:
                return True
            
            self.log_info("正在停用插件...")
            
            # 执行停用逻辑
            if self.on_deactivate():
                self._activated = False
                self._status = PluginStatus.DISABLED
                self.log_info("插件停用成功")
                return True
            else:
                self.log_error("插件停用失败")
                return False
                
        except Exception as e:
            self.log_error(f"插件停用异常: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理插件资源"""
        try:
            self.log_info("正在清理插件资源...")
            
            # 先停用插件
            if self._activated:
                self.deactivate()
            
            # 执行清理逻辑
            if self.on_cleanup():
                self._initialized = False
                self.log_info("插件清理成功")
                return True
            else:
                self.log_error("插件清理失败")
                return False
                
        except Exception as e:
            self.log_error(f"插件清理异常: {e}")
            return False
    
    # 子类需要实现的方法
    def on_initialize(self) -> bool:
        """初始化回调（子类实现）"""
        return True
    
    def on_activate(self) -> bool:
        """激活回调（子类实现）"""
        return True
    
    def on_deactivate(self) -> bool:
        """停用回调（子类实现）"""
        return True
    
    def on_cleanup(self) -> bool:
        """清理回调（子类实现）"""
        return True

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（子类必须实现）"""
        pass


class UIPlugin(BasePlugin):
    """UI插件基类"""
    
    def __init__(self):
        super().__init__()
        self._widgets: List[QWidget] = []
        self._actions: List[QAction] = []
        self._menus: List[QMenu] = []
    
    def add_widget(self, widget: QWidget):
        """添加UI组件"""
        self._widgets.append(widget)
    
    def remove_widget(self, widget: QWidget):
        """移除UI组件"""
        if widget in self._widgets:
            self._widgets.remove(widget)
            widget.deleteLater()
    
    def add_action(self, action: QAction):
        """添加动作"""
        self._actions.append(action)
    
    def remove_action(self, action: QAction):
        """移除动作"""
        if action in self._actions:
            self._actions.remove(action)
            action.deleteLater()
    
    def add_menu(self, menu: QMenu):
        """添加菜单"""
        self._menus.append(menu)
    
    def remove_menu(self, menu: QMenu):
        """移除菜单"""
        if menu in self._menus:
            self._menus.remove(menu)
            menu.deleteLater()
    
    def on_cleanup(self) -> bool:
        """清理UI资源"""
        try:
            # 清理所有UI组件
            for widget in self._widgets[:]:
                self.remove_widget(widget)
            
            for action in self._actions[:]:
                self.remove_action(action)
            
            for menu in self._menus[:]:
                self.remove_menu(menu)
            
            return True
            
        except Exception as e:
            self.log_error(f"清理UI资源失败: {e}")
            return False


class ServicePlugin(BasePlugin):
    """服务插件基类"""
    
    def __init__(self):
        super().__init__()
        self._services: Dict[str, Any] = {}
    
    def register_service(self, name: str, service: Any):
        """注册服务"""
        self._services[name] = service
        self.log_info(f"服务已注册: {name}")
    
    def unregister_service(self, name: str):
        """取消注册服务"""
        if name in self._services:
            del self._services[name]
            self.log_info(f"服务已取消注册: {name}")
    
    def get_service(self, name: str) -> Any:
        """获取服务"""
        return self._services.get(name)
    
    def on_cleanup(self) -> bool:
        """清理服务资源"""
        try:
            # 清理所有服务
            for name in list(self._services.keys()):
                self.unregister_service(name)
            
            return True
            
        except Exception as e:
            self.log_error(f"清理服务资源失败: {e}")
            return False


class EditorPlugin(UIPlugin):
    """编辑器插件基类"""
    
    def __init__(self):
        super().__init__()

    def get_plugin_info(self) -> PluginInfo:
        """获取插件信息（默认实现，子类应该重写）"""
        return create_plugin_info(
            plugin_id=self.__class__.__name__.lower(),
            name=self.__class__.__name__,
            version="1.0.0",
            description="编辑器插件",
            author="Unknown",
            plugin_type=PluginType.EDITOR
        )
    
    def get_editor_service(self):
        """获取编辑器服务"""
        return self.get_api("editor_service")
    
    def get_current_document(self):
        """获取当前文档"""
        editor_service = self.get_editor_service()
        if editor_service:
            return editor_service.get_current_document()
        return None
    
    def get_selected_text(self) -> str:
        """获取选中的文本"""
        editor_service = self.get_editor_service()
        if editor_service:
            return editor_service.get_selected_text()
        return ""
    
    def insert_text(self, text: str):
        """插入文本"""
        editor_service = self.get_editor_service()
        if editor_service:
            editor_service.insert_text(text)
    
    def replace_selected_text(self, text: str):
        """替换选中的文本"""
        editor_service = self.get_editor_service()
        if editor_service:
            editor_service.replace_selected_text(text)


class AIPlugin(BasePlugin):
    """AI插件基类"""
    
    def __init__(self):
        super().__init__()
    
    def get_ai_service(self):
        """获取AI服务"""
        return self.get_api("ai_service")
    
    async def generate_text(self, prompt: str, context: str = "") -> str:
        """生成文本"""
        ai_service = self.get_ai_service()
        if ai_service:
            return await ai_service.generate_text(prompt, context)
        return ""
    
    async def improve_text(self, text: str, instruction: str = "") -> str:
        """改进文本"""
        ai_service = self.get_ai_service()
        if ai_service:
            return await ai_service.improve_text(text, instruction)
        return text


class ExportPlugin(BasePlugin):
    """导出插件基类"""
    
    def __init__(self):
        super().__init__()
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式（子类实现）"""
        return []
    
    def export_document(self, document, file_path: str, options: Dict[str, Any] = None) -> bool:
        """导出文档（子类实现）"""
        return False
    
    def export_project(self, project, file_path: str, options: Dict[str, Any] = None) -> bool:
        """导出项目（子类实现）"""
        return False


class ImportPlugin(BasePlugin):
    """导入插件基类"""
    
    def __init__(self):
        super().__init__()
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式（子类实现）"""
        return []
    
    def import_document(self, file_path: str, options: Dict[str, Any] = None) -> Any:
        """导入文档（子类实现）"""
        return None
    
    def import_project(self, file_path: str, options: Dict[str, Any] = None) -> Any:
        """导入项目（子类实现）"""
        return None


# 插件工具函数
def create_plugin_info(
    plugin_id: str,
    name: str,
    version: str,
    description: str,
    author: str,
    plugin_type: PluginType,
    dependencies: List[str] = None,
    min_app_version: str = "2.0.0",
    **kwargs
) -> PluginInfo:
    """创建插件信息"""
    return PluginInfo(
        id=plugin_id,
        name=name,
        version=version,
        description=description,
        author=author,
        plugin_type=plugin_type,
        dependencies=dependencies or [],
        min_app_version=min_app_version,
        **kwargs
    )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础配置管理器

提供通用的JSON配置文件管理功能，减少重复代码。
支持点号路径访问、默认值管理、原子性保存等功能。
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import threading
import asyncio
from datetime import datetime
from abc import ABC, abstractmethod

from src.shared.utils.logger import get_logger
# CONFIG_DIR 已移除，现在使用项目内配置目录

logger = get_logger(__name__)

# 配置管理器常量
DEFAULT_BACKUP_COUNT = 5
TEMP_FILE_SUFFIX = '.tmp'
BACKUP_DIR_NAME = 'backups'


class BaseConfigManager(ABC):
    """
    基础配置管理器
    
    提供通用的JSON配置文件管理功能，包括：
    - 点号路径访问（如 "ui.theme"）
    - 原子性文件保存
    - 默认值管理和合并
    - 配置验证和错误恢复
    - 导入导出功能
    
    子类需要实现：
    - get_default_config(): 返回默认配置字典
    - get_config_file_name(): 返回配置文件名
    """
    
    def __init__(self, config_dir: Path):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录（必须提供，通常为项目内路径）
        """
        self.config_dir = config_dir
        self.config_file = self.config_dir / self.get_config_file_name()
        
        # 备份目录
        self.backup_dir = self.config_dir / BACKUP_DIR_NAME
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置数据
        self.config_data: Dict[str, Any] = {}
        
        # 加载配置
        self._load_config()
    
    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（子类必须实现）"""
        pass
    
    @abstractmethod
    def get_config_file_name(self) -> str:
        """获取配置文件名（子类必须实现）"""
        pass
    
    def _get_default_config_dir(self) -> Path:
        """获取默认配置目录（已废弃，现在必须显式提供配置目录）"""
        raise RuntimeError("配置目录必须显式提供，不再支持默认配置目录")
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建配置目录失败: {e}")
            raise
    
    def _run_coro_blocking(self, coro):
        """在当前线程安全地运行协程，无论事件循环是否已在运行"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # 没有运行中的事件循环，直接运行
            return asyncio.run(coro)
        # 有运行中的事件循环，改用线程执行避免嵌套循环错误
        result_ref: Dict[str, Any] = {}
        def runner():
            try:
                result_ref['result'] = asyncio.run(coro)
            except Exception as e:
                result_ref['error'] = e
        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join()
        if 'error' in result_ref:
            raise result_ref['error']
        return result_ref.get('result')

    def _load_config(self) -> None:
        """加载配置"""
        try:
            if self.config_file.exists():
                # 统一读取 JSON（线程安全地调用异步实现）
                from src.shared.utils.file_operations import get_file_operations
                ops = get_file_operations("config")
                loaded_config = self._run_coro_blocking(ops.load_json_cached(self.config_file))
                if loaded_config is None:
                    raise ValueError("配置文件读取失败")
                # 验证数据格式
                if not isinstance(loaded_config, dict):
                    raise ValueError("配置文件格式无效：根对象必须是字典")
                # 合并默认配置和用户配置
                self.config_data = self._merge_config(self.get_default_config(), loaded_config)
                logger.debug(f"配置加载成功: {self.config_file}")
            else:
                # 使用默认配置
                self.config_data = self.get_default_config().copy()
                self._save_config()
                logger.debug("使用默认配置并保存")

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
            logger.error(f"配置文件格式错误: {e}")
            self._repair_corrupted_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._repair_corrupted_config()
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """递归合并默认配置和用户配置"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _repair_corrupted_config(self) -> None:
        """修复损坏的配置文件"""
        try:
            logger.info("尝试修复损坏的配置文件...")
            
            # 备份损坏的文件
            if self.config_file.exists():
                backup_file = self.backup_dir / f"{self.get_config_file_name()}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                except Exception as e:
                    logger.warning(f"备份损坏配置失败: {e}")
                logger.info(f"已备份损坏的配置文件到: {backup_file}")

            # 创建新的默认配置
            self.config_data = self.get_default_config().copy()
            success = self._save_config()
            
            if success:
                logger.info("配置文件修复成功，已创建新的默认配置")
            else:
                logger.error("配置文件修复失败")
                
        except Exception as e:
            logger.error(f"修复配置文件时发生错误: {e}")
            # 最后的备用方案：使用内存中的默认配置
            self.config_data = self.get_default_config().copy()
    
    def _save_config(self) -> bool:
        """保存配置"""
        temp_file = None
        try:
            self._ensure_config_dir()

            # 验证配置数据的JSON兼容性
            self._validate_config_for_json()

            # 统一文件操作进行原子写入 + 备份（线程安全地调用异步实现）
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("config")
            ok = self._run_coro_blocking(ops.save_json_atomic(self.config_file, self.config_data, create_backup=True))
            if ok:
                logger.debug(f"配置保存成功: {self.config_file}")
                return True
            return False

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False

    def _validate_config_for_json(self) -> None:
        """验证配置数据是否可以序列化为JSON"""
        def check_value(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    check_value(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    check_value(value, f"{path}[{i}]")
            elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
                # 检测不可序列化的对象
                raise TypeError(f"不可序列化的对象类型 {type(obj)} 在路径: {path}")
        
        check_value(self.config_data)
    
    def _create_backup(self) -> None:
        """创建配置备份"""
        try:
            if self.config_file.exists():
                backup_file = self.backup_dir / f"{self.get_config_file_name()}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                except Exception as e:
                    logger.warning(f"创建配置备份失败: {e}")
                # 清理旧备份（保留最近几个）
                self._cleanup_old_backups(DEFAULT_BACKUP_COUNT)

        except Exception as e:
            logger.warning(f"创建配置备份失败: {e}")
    
    def _cleanup_old_backups(self, keep_count: int) -> None:
        """清理旧备份文件"""
        try:
            pattern = f"{self.get_config_file_name()}.*.bak"
            backup_files = list(self.backup_dir.glob(pattern))
            
            if len(backup_files) > keep_count:
                # 按修改时间排序，删除最旧的文件
                backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                files_to_delete = backup_files[keep_count:]
                
                for backup_file in files_to_delete:
                    try:
                        backup_file.unlink()
                        logger.debug(f"删除旧备份: {backup_file.name}")
                    except Exception as e:
                        logger.warning(f"删除备份文件失败 {backup_file}: {e}")
                        
        except Exception as e:
            logger.warning(f"清理备份文件失败: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，使用点号分隔，如 "ui.theme"
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            keys = key_path.split('.')
            value = self.config_data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"获取配置失败: {key_path}, {e}")
            return default
    
    def set(self, key_path: str, value: Any, save_immediately: bool = True) -> bool:
        """
        设置配置值
        
        Args:
            key_path: 配置键路径，使用点号分隔，如 "ui.theme"
            value: 配置值
            save_immediately: 是否立即保存到文件
            
        Returns:
            bool: 设置成功返回True
        """
        try:
            keys = key_path.split('.')
            current = self.config_data
            
            # 导航到父级字典
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # 设置值
            current[keys[-1]] = value
            
            logger.debug(f"配置已更新: {key_path} = {value}")
            
            # 立即保存（如果需要）
            if save_immediately:
                return self._save_config()
            
            return True
            
        except Exception as e:
            logger.error(f"设置配置失败: {key_path}, {e}")
            return False

    def save(self) -> bool:
        """手动保存配置"""
        return self._save_config()

    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        try:
            self.config_data = self.get_default_config().copy()
            success = self._save_config()
            if success:
                logger.info("配置已重置为默认值")
            return success
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False

    def export_config(self, export_path: Path) -> bool:
        """导出配置到文件"""
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "config_type": self.__class__.__name__,
                "config": self.config_data
            }

            # 统一原子写入导出
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("config_export")
            self._run_coro_blocking(ops.save_json_atomic(export_path, export_data, create_backup=True))

            logger.info(f"配置导出成功: {export_path}")
            return True

        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False

    def import_config(self, import_path: Path, merge_with_defaults: bool = True) -> bool:
        """从文件导入配置"""
        try:
            if not import_path.exists():
                logger.error(f"配置文件不存在: {import_path}")
                return False

            # 统一读取导入 JSON
            from src.shared.utils.file_operations import get_file_operations
            import asyncio
            ops = get_file_operations("config_import")
            loop = asyncio.get_event_loop()
            import_data = loop.run_until_complete(ops.load_json_cached(import_path))
            if import_data is None:
                return False

            # 提取配置数据
            if "config" in import_data:
                imported_config = import_data["config"]
            else:
                # 兼容直接的配置文件格式
                imported_config = import_data

            # 备份当前配置
            backup_path = self.backup_dir / f"{self.get_config_file_name()}.import_backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            self.export_config(backup_path)

            # 导入新配置
            if merge_with_defaults:
                # 与默认配置合并
                self.config_data = self._merge_config(self.get_default_config(), imported_config)
            else:
                # 直接使用导入的配置
                self.config_data = imported_config

            success = self._save_config()

            if success:
                logger.info(f"配置导入成功: {import_path}")
                return True
            else:
                # 恢复备份
                self._load_config()
                logger.error("配置导入失败，已恢复原配置")
                return False

        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "config_file": str(self.config_file),
            "config_dir": str(self.config_dir),
            "backup_dir": str(self.backup_dir),
            "file_exists": self.config_file.exists(),
            "file_size": self.config_file.stat().st_size if self.config_file.exists() else 0,
            "last_modified": datetime.fromtimestamp(self.config_file.stat().st_mtime).isoformat() if self.config_file.exists() else None,
            "config_keys": list(self.config_data.keys()) if isinstance(self.config_data, dict) else []
        }

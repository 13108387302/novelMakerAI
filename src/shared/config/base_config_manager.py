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
from datetime import datetime
from abc import ABC, abstractmethod

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


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
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，如果为None则使用默认目录
        """
        self.config_dir = config_dir or self._get_default_config_dir()
        self.config_file = self.config_dir / self.get_config_file_name()
        
        # 备份目录
        self.backup_dir = self.config_dir / "backups"
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
        """获取默认配置目录"""
        return Path.home() / ".ai_novel_editor"
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建配置目录失败: {e}")
            raise
    
    def _load_config(self) -> None:
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
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
                shutil.copy2(self.config_file, backup_file)
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
            
            # 先写入临时文件，然后重命名，确保原子性操作
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            # 验证写入的文件是否有效
            with open(temp_file, 'r', encoding='utf-8') as f:
                json.load(f)  # 验证JSON格式
            
            # 创建备份（保留最近5个备份）
            self._create_backup()
            
            # 原子性替换
            temp_file.replace(self.config_file)
            
            logger.debug(f"配置保存成功: {self.config_file}")
            return True
            
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
                shutil.copy2(self.config_file, backup_file)
                
                # 清理旧备份（保留最近5个）
                self._cleanup_old_backups(5)
                
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

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

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

            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

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

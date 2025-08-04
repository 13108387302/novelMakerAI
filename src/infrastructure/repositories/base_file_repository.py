#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件仓储基类

提供通用的文件操作功能，减少重复代码
"""

import json
import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, TypeVar, Generic
from datetime import datetime
from abc import ABC, abstractmethod

from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import handle_async_errors, RepositoryError
from src.shared.utils.file_utils import FileManager

logger = get_logger(__name__)

T = TypeVar('T')


class BaseFileRepository(Generic[T], ABC):
    """文件仓储基类"""
    
    def __init__(self, base_path: Optional[Path] = None, entity_name: str = "entity"):
        self.entity_name = entity_name
        self.base_path = base_path or Path.home() / ".novel_editor" / f"{entity_name}s"

        # 使用FileManager进行文件操作
        self.file_manager = FileManager()
        self.file_manager.ensure_directory(self.base_path)

        # 索引文件
        self.index_file = self.base_path / f"{entity_name}s_index.json"
        self._ensure_index_file()

        # 备份目录
        self.backup_path = self.base_path / "backups"
        self.file_manager.ensure_directory(self.backup_path)
    
    def _ensure_index_file(self) -> None:
        """确保索引文件存在"""
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> Dict[str, Any]:
        """加载索引"""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载{self.entity_name}索引失败: {e}")
            return {}
    
    def _save_index(self, index: Dict[str, Any]) -> None:
        """保存索引"""
        temp_file = None
        try:
            # 创建备份
            if self.index_file.exists():
                backup_file = self.backup_path / f"{self.entity_name}s_index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.index_file, backup_file)

                # 清理旧备份（保留最近10个）
                self._cleanup_backups(f"{self.entity_name}s_index_backup_*.json", 10)

            # 使用临时文件确保原子性写入
            temp_file = self.index_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)

            # 验证写入的文件
            with open(temp_file, 'r', encoding='utf-8') as f:
                json.load(f)

            # 原子性替换
            temp_file.replace(self.index_file)

        except Exception as e:
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            logger.error(f"保存{self.entity_name}索引失败: {e}")
            raise RepositoryError(f"保存{self.entity_name}索引失败: {e}")
    
    def _get_entity_path(self, entity_id: str) -> Path:
        """获取实体文件路径"""
        return self.base_path / f"{entity_id}.json"
    
    def _get_entity_dir(self, entity_id: str) -> Path:
        """获取实体目录路径"""
        return self.base_path / entity_id
    
    @handle_async_errors("加载实体文件")
    async def _load_entity_file(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """加载实体文件"""
        entity_path = self._get_entity_path(entity_id)
        
        if not entity_path.exists():
            return None
        
        try:
            def _load():
                with open(entity_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return await asyncio.get_event_loop().run_in_executor(None, _load)
            
        except Exception as e:
            logger.error(f"加载{self.entity_name}文件失败 {entity_id}: {e}")
            raise RepositoryError(f"加载{self.entity_name}文件失败: {e}")
    
    @handle_async_errors("保存实体文件")
    async def _save_entity_file(self, entity_id: str, data: Dict[str, Any]) -> None:
        """保存实体文件"""
        entity_path = self._get_entity_path(entity_id)
        temp_file = entity_path.with_suffix('.tmp')

        try:
            # 创建备份
            if entity_path.exists():
                backup_file = self.backup_path / f"{entity_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                await asyncio.get_event_loop().run_in_executor(None, shutil.copy2, entity_path, backup_file)

                # 清理旧备份
                await asyncio.get_event_loop().run_in_executor(
                    None, self._cleanup_backups, f"{entity_id}_backup_*.json", 5
                )

            # 使用临时文件确保原子性写入
            def _save():
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)

                # 原子性替换
                temp_file.replace(entity_path)

            await asyncio.get_event_loop().run_in_executor(None, _save)

        except Exception as e:
            # 清理临时文件
            if temp_file.exists():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, temp_file.unlink)
                except Exception:
                    pass
            logger.error(f"保存{self.entity_name}文件失败 {entity_id}: {e}")
            raise RepositoryError(f"保存{self.entity_name}文件失败: {e}")
    
    @handle_async_errors("删除实体文件")
    async def _delete_entity_file(self, entity_id: str) -> None:
        """删除实体文件"""
        entity_path = self._get_entity_path(entity_id)
        entity_dir = self._get_entity_dir(entity_id)
        
        try:
            # 创建最终备份
            if entity_path.exists():
                backup_file = self.backup_path / f"{entity_id}_deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                await asyncio.get_event_loop().run_in_executor(None, shutil.copy2, entity_path, backup_file)
                
                # 删除文件
                await asyncio.get_event_loop().run_in_executor(None, entity_path.unlink)
            
            # 删除目录（如果存在且为空）
            if entity_dir.exists() and entity_dir.is_dir():
                try:
                    await asyncio.get_event_loop().run_in_executor(None, entity_dir.rmdir)
                except OSError:
                    # 目录不为空，不删除
                    pass
                    
        except Exception as e:
            logger.error(f"删除{self.entity_name}文件失败 {entity_id}: {e}")
            raise RepositoryError(f"删除{self.entity_name}文件失败: {e}")
    
    def _cleanup_backups(self, pattern: str, keep_count: int) -> None:
        """清理旧备份文件"""
        try:
            backup_files = list(self.backup_path.glob(pattern))
            if len(backup_files) > keep_count:
                # 按修改时间排序，删除最旧的文件
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                for old_file in backup_files[keep_count:]:
                    old_file.unlink()
                    
        except Exception as e:
            logger.warning(f"清理备份文件失败: {e}")
    
    def _update_index_entry(self, entity_id: str, entity_data: Dict[str, Any]) -> None:
        """更新索引条目"""
        index = self._load_index()
        
        # 提取索引信息
        index_info = self._extract_index_info(entity_data)
        index_info.update({
            "id": entity_id,
            "file_path": str(self._get_entity_path(entity_id)),
            "updated_at": datetime.now().isoformat()
        })
        
        index[entity_id] = index_info
        self._save_index(index)
    
    def _remove_index_entry(self, entity_id: str) -> None:
        """移除索引条目"""
        index = self._load_index()
        if entity_id in index:
            del index[entity_id]
            self._save_index(index)
    
    @abstractmethod
    def _extract_index_info(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取索引信息 - 子类实现"""
        pass
    
    @abstractmethod
    async def _entity_to_dict(self, entity: T) -> Dict[str, Any]:
        """实体转字典 - 子类实现"""
        pass
    
    @abstractmethod
    async def _dict_to_entity(self, data: Dict[str, Any]) -> T:
        """字典转实体 - 子类实现"""
        pass
    
    # 通用CRUD操作
    @handle_async_errors("获取实体")
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """根据ID获取实体"""
        data = await self._load_entity_file(entity_id)
        if data:
            return await self._dict_to_entity(data)
        return None
    
    @handle_async_errors("保存实体")
    async def save(self, entity: T) -> T:
        """保存实体"""
        entity_data = await self._entity_to_dict(entity)
        entity_id = entity_data.get("id")
        
        if not entity_id:
            raise RepositoryError(f"{self.entity_name}ID不能为空")
        
        await self._save_entity_file(entity_id, entity_data)
        self._update_index_entry(entity_id, entity_data)
        
        return entity
    
    @handle_async_errors("删除实体")
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        if not await self.exists(entity_id):
            return False
        
        await self._delete_entity_file(entity_id)
        self._remove_index_entry(entity_id)
        
        return True
    
    @handle_async_errors("检查实体存在")
    async def exists(self, entity_id: str) -> bool:
        """检查实体是否存在"""
        return self._get_entity_path(entity_id).exists()
    
    @handle_async_errors("获取所有实体")
    async def get_all(self) -> List[T]:
        """获取所有实体"""
        index = self._load_index()
        entities = []
        
        for entity_id in index.keys():
            entity = await self.get_by_id(entity_id)
            if entity:
                entities.append(entity)
        
        return entities
    
    @handle_async_errors("获取实体数量")
    async def count(self) -> int:
        """获取实体数量"""
        index = self._load_index()
        return len(index)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        index = self._load_index()
        
        total_size = 0
        file_count = 0
        
        for entity_path in self.base_path.glob("*.json"):
            if entity_path != self.index_file:
                total_size += entity_path.stat().st_size
                file_count += 1
        
        return {
            "base_path": str(self.base_path),
            "entity_count": len(index),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "index_file": str(self.index_file),
            "backup_path": str(self.backup_path)
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一文件操作工具

提供统一的文件读写、序列化和缓存功能，减少重复代码
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, List, Iterator
from datetime import datetime

from src.shared.utils.unified_performance import get_performance_manager
from src.shared.constants import MAX_DOCUMENT_SIZE

logger = logging.getLogger(__name__)

T = TypeVar('T')

# 文件操作常量
DEFAULT_ENCODING = 'utf-8'
BACKUP_SUFFIX = '_backup'
TEMP_SUFFIX = '.tmp'
# 读取编码回退顺序（覆盖大部分常见中文与西文编码）
FALLBACK_ENCODINGS: List[str] = ['gbk', 'latin-1', 'cp1252', 'utf-16']


class UnifiedFileOperations:
    """
    统一文件操作工具

    提供标准化的文件读写、序列化和缓存功能。
    减少仓储实现中的重复代码。

    功能：
    - 原子性文件写入
    - 统一的JSON序列化
    - 缓存集成
    - 备份管理
    - 错误处理
    """

    def __init__(self, cache_prefix: str = "file_ops"):
        """
        初始化文件操作工具

        Args:
            cache_prefix: 缓存键前缀
        """
        self.cache_prefix = cache_prefix
        self.performance_manager = get_performance_manager()

    async def save_json_atomic(
        self,
        file_path: Path,
        data: Dict[str, Any],
        create_backup: bool = True,
        cache_key: Optional[str] = None,
        cache_ttl: int = 3600
    ) -> bool:
        """
        原子性保存JSON文件

        Args:
            file_path: 文件路径
            data: 要保存的数据
            create_backup: 是否创建备份
            cache_key: 缓存键（可选）
            cache_ttl: 缓存TTL（秒）

        Returns:
            bool: 保存是否成功
        """
        temp_file = None
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 创建备份
            if create_backup and file_path.exists():
                await self._create_backup(file_path)

            # 使用临时文件确保原子性写入
            temp_file = file_path.with_suffix(TEMP_SUFFIX)

            def _write_file():
                with open(temp_file, 'w', encoding=DEFAULT_ENCODING) as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding=DEFAULT_ENCODING) as f:
                    json.load(f)

                # 原子性替换
                temp_file.replace(file_path)

            await asyncio.get_event_loop().run_in_executor(None, _write_file)

            # 更新缓存
            if cache_key:
                self.performance_manager.cache_set(
                    f"{self.cache_prefix}:{cache_key}",
                    data,
                    ttl=cache_ttl
                )

            logger.debug(f"JSON文件保存成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存JSON文件失败: {file_path}, 错误: {e}")
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False

    async def load_json_cached(
        self,
        file_path: Path,
        cache_key: Optional[str] = None,
        cache_ttl: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """
        加载JSON文件（带缓存）

        Args:
            file_path: 文件路径
            cache_key: 缓存键（可选）
            cache_ttl: 缓存TTL（秒）

        Returns:
            Optional[Dict[str, Any]]: 加载的数据
        """
        try:
            # 尝试从缓存获取
            if cache_key:
                cache_result = self.performance_manager.cache_get(
                    f"{self.cache_prefix}:{cache_key}"
                )
                if cache_result.success:
                    logger.debug(f"从缓存加载JSON: {file_path} (hit)")
                    return cache_result.data
                else:
                    logger.debug(f"从缓存加载JSON: {file_path} (miss)")

            # 检查文件是否存在
            if not file_path.exists():
                return None

            # 从文件加载
            def _read_file():
                with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                    return json.load(f)

            data = await asyncio.get_event_loop().run_in_executor(None, _read_file)

            # 更新缓存
            if cache_key and data:
                self.performance_manager.cache_set(
                    f"{self.cache_prefix}:{cache_key}",
                    data,
                    ttl=cache_ttl
                )

            logger.debug(f"JSON文件加载成功: {file_path}")
            return data
        except Exception as e:
            logger.error(f"加载JSON文件失败: {file_path}, 错误: {e}")
            return None

    async def load_text_safe(
        self,
        file_path: Path,
        max_size_bytes: int = MAX_DOCUMENT_SIZE,
        encodings: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        安全加载文本（带大小限制与编码回退）
        - 先尝试utf-8，失败回退到常见编码
        - 可设置最大读取大小，避免超大文件导致内存压力
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            if file_path.stat().st_size > max_size_bytes:
                logger.warning(f"文件过大: {file_path} size={file_path.stat().st_size} > {max_size_bytes}")
                return None

            try:
                def _read_utf8():
                    with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                        return f.read()
                return await asyncio.get_event_loop().run_in_executor(None, _read_utf8)
            except UnicodeDecodeError:
                pass

            # 逐个编码回退
            for enc in (encodings or FALLBACK_ENCODINGS):
                try:
                    def _read_with_enc():
                        with open(file_path, 'r', encoding=enc) as f:
                            return f.read()
                    return await asyncio.get_event_loop().run_in_executor(None, _read_with_enc)
                except Exception:
                    continue
            logger.error(f"所有编码尝试失败: {file_path}")
            return None
        except Exception as e:
            logger.error(f"安全读取失败: {file_path}, {e}")
            return None

            logger.debug(f"JSON文件加载成功: {file_path}")
            return data

        except Exception as e:
            logger.error(f"加载JSON文件失败: {file_path}, 错误: {e}")
            return None

    async def save_text_atomic(
        self,
        file_path: Path,
        content: str,
        create_backup: bool = True
    ) -> bool:
        """
        原子性保存文本文件

        Args:
            file_path: 文件路径
            content: 文本内容
            create_backup: 是否创建备份

        Returns:
            bool: 保存是否成功
        """
        temp_file = None
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 创建备份
            if create_backup and file_path.exists():
                await self._create_backup(file_path)

            # 使用临时文件确保原子性写入
            temp_file = file_path.with_suffix(TEMP_SUFFIX)

            def _write_file():
                with open(temp_file, 'w', encoding=DEFAULT_ENCODING) as f:
                    f.write(content)

                # 原子性替换
                temp_file.replace(file_path)

            await asyncio.get_event_loop().run_in_executor(None, _write_file)

            logger.debug(f"文本文件保存成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存文本文件失败: {file_path}, 错误: {e}")
            # 清理临时文件
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False

    async def load_text(self, file_path: Path) -> Optional[str]:
        """
        加载文本文件

        Args:
            file_path: 文件路径

        Returns:
            Optional[str]: 文件内容
        """
        try:
            if not file_path.exists():
                return None

            def _read_file():
                with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                    return f.read()

            content = await asyncio.get_event_loop().run_in_executor(None, _read_file)
            logger.debug(f"文本文件加载成功: {file_path}")
            return content

        except Exception as e:
            logger.error(f"加载文本文件失败: {file_path}, 错误: {e}")
            return None

    async def _create_backup(self, file_path: Path) -> None:
        """创建文件备份"""
        try:
            backup_dir = file_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"{file_path.stem}{BACKUP_SUFFIX}_{timestamp}{file_path.suffix}"

            def _copy_file():
                import shutil
                shutil.copy2(file_path, backup_file)

            await asyncio.get_event_loop().run_in_executor(None, _copy_file)
            logger.debug(f"备份创建成功: {backup_file}")

        except Exception as e:
            logger.warning(f"创建备份失败: {e}")

    async def stream_text(self, file_path: Path, chunk_size: int = 8192) -> Optional[Iterator[str]]:
        """
        流式读取文本（带编码回退），返回生成器
        注意：调用方需在事件循环外迭代，或将迭代包装到线程池
        """
        if not file_path.exists() or not file_path.is_file():
            return None
        # 尝试不同编码
        for enc in [DEFAULT_ENCODING] + FALLBACK_ENCODINGS:
            try:
                def _open():
                    return open(file_path, 'r', encoding=enc)
                f = await asyncio.get_event_loop().run_in_executor(None, _open)
                def _iter():
                    with f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                return _iter()
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        logger.error(f"流式读取失败: {file_path}")
        return None

    async def load_lines_safe(
        self,
        file_path: Path,
        start_line: int = 0,
        line_count: int = 1000,
        encodings: Optional[List[str]] = None
    ) -> Optional[List[str]]:
        """
        按行安全读取（带编码回退）
        - 从 start_line 开始读取最多 line_count 行
        - 自动处理换行符，返回不带行尾的文本
        """
        if not file_path.exists() or not file_path.is_file():
            return None
        try:
            for enc in [DEFAULT_ENCODING] + (encodings or FALLBACK_ENCODINGS):
                try:
                    def _read_lines():
                        lines: List[str] = []
                        with open(file_path, 'r', encoding=enc) as f:
                            # 跳过前面的行
                            for _ in range(max(0, start_line)):
                                f.readline()
                            for _ in range(max(0, line_count)):
                                line = f.readline()
                                if not line:
                                    break
                                lines.append(line.rstrip('\n\r'))
                        return lines
                    return await asyncio.get_event_loop().run_in_executor(None, _read_lines)
                except UnicodeDecodeError:
                    continue
            logger.error(f"按行读取失败（编码回退均失败）: {file_path}")
            return None
        except Exception as e:
            logger.error(f"按行读取失败: {file_path}, {e}")
            return None

    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """
        清理缓存

        Args:
            pattern: 缓存键模式（可选）
        """
        try:
            if pattern:
                # 清理匹配模式的缓存
                cache_key = f"{self.cache_prefix}:{pattern}"
                self.performance_manager.cache_delete(cache_key)
            else:
                # 清理所有相关缓存
                # 这里可以扩展为清理所有以cache_prefix开头的缓存
                logger.info(f"清理缓存: {self.cache_prefix}")
        except Exception as e:
            logger.warning(f"清理缓存失败: {e}")


# 全局文件操作实例
_global_file_operations: Optional[UnifiedFileOperations] = None


def get_file_operations(cache_prefix: str = "file_ops") -> UnifiedFileOperations:
    """获取全局文件操作实例"""
    global _global_file_operations
    if _global_file_operations is None:
        _global_file_operations = UnifiedFileOperations(cache_prefix)
    return _global_file_operations

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作工具

提供常用的文件和目录操作功能
"""

import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Iterator
from datetime import datetime
import tempfile
import zipfile
import json

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class FileInfo:
    """
    文件信息类
    
    封装文件的基本信息和元数据。
    
    Attributes:
        path: 文件路径
        name: 文件名
        size: 文件大小（字节）
        created_time: 创建时间
        modified_time: 修改时间
        mime_type: MIME类型
        extension: 文件扩展名
        is_directory: 是否为目录
        hash_md5: MD5哈希值（可选）
    """
    
    def __init__(self, path: Union[str, Path]):
        """
        初始化文件信息
        
        Args:
            path: 文件路径
        """
        self.path = Path(path)
        self.name = self.path.name
        self.extension = self.path.suffix.lower()
        self.is_directory = self.path.is_dir()
        
        if self.path.exists():
            stat = self.path.stat()
            self.size = stat.st_size
            self.created_time = datetime.fromtimestamp(stat.st_ctime)
            self.modified_time = datetime.fromtimestamp(stat.st_mtime)
            self.mime_type = mimetypes.guess_type(str(self.path))[0]
        else:
            self.size = 0
            self.created_time = None
            self.modified_time = None
            self.mime_type = None
        
        self.hash_md5: Optional[str] = None
    
    def calculate_hash(self) -> Optional[str]:
        """计算文件MD5哈希值"""
        if self.is_directory or not self.path.exists():
            return None
        
        try:
            hash_md5 = hashlib.md5()
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            self.hash_md5 = hash_md5.hexdigest()
            return self.hash_md5
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'path': str(self.path),
            'name': self.name,
            'size': self.size,
            'extension': self.extension,
            'is_directory': self.is_directory,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'modified_time': self.modified_time.isoformat() if self.modified_time else None,
            'mime_type': self.mime_type,
            'hash_md5': self.hash_md5
        }


class FileManager:
    """
    文件管理器
    
    提供高级的文件和目录操作功能。
    
    实现方式：
    - 封装常用的文件操作
    - 提供安全的文件操作
    - 支持批量操作
    - 包含完整的错误处理
    - 提供文件搜索和过滤功能
    """
    
    def __init__(self):
        """初始化文件管理器"""
        self.temp_dir = Path(tempfile.gettempdir()) / "ai_novel_editor"
        self.temp_dir.mkdir(exist_ok=True)
    
    def ensure_directory(self, path: Union[str, Path]) -> bool:
        """
        确保目录存在

        Args:
            path: 目录路径

        Returns:
            bool: 操作是否成功
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False

    def safe_read(self, path: Union[str, Path], encoding: str = 'utf-8', max_size_mb: int = 100) -> Optional[str]:
        """
        安全读取文件内容（增强健壮性版本）

        Args:
            path: 文件路径
            encoding: 文件编码
            max_size_mb: 最大文件大小（MB），防止内存溢出

        Returns:
            Optional[str]: 文件内容，失败时返回None
        """
        try:
            # 输入验证
            if not path:
                logger.warning("文件路径为空")
                return None

            file_path = Path(path)

            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return None

            if not file_path.is_file():
                logger.warning(f"路径不是文件: {file_path}")
                return None

            # 检查文件大小
            file_size = file_path.stat().st_size
            max_size_bytes = max_size_mb * 1024 * 1024

            if file_size > max_size_bytes:
                logger.warning(f"文件过大: {file_size / (1024*1024):.1f}MB > {max_size_mb}MB")
                return None

            # 检查文件权限
            if not os.access(file_path, os.R_OK):
                logger.warning(f"文件无读取权限: {file_path}")
                return None

            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                logger.debug(f"文件读取成功: {file_path} ({file_size} bytes)")
                return content

        except UnicodeDecodeError as e:
            logger.error(f"文件编码错误: {e}")
            # 尝试其他编码
            fallback_encodings = ['gbk', 'latin-1', 'cp1252', 'utf-16']
            for fallback_encoding in fallback_encodings:
                try:
                    with open(file_path, 'r', encoding=fallback_encoding) as f:
                        content = f.read()
                        logger.info(f"使用备用编码 {fallback_encoding} 读取成功: {file_path}")
                        return content
                except Exception:
                    continue
            logger.error(f"所有编码尝试失败: {file_path}")
            return None
        except PermissionError as e:
            logger.error(f"文件权限错误: {e}")
            return None
        except OSError as e:
            logger.error(f"文件系统错误: {e}")
            return None
        except MemoryError as e:
            logger.error(f"内存不足，无法读取文件: {e}")
            return None
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None

    def safe_write(self, path: Union[str, Path], content: str, encoding: str = 'utf-8',
                   backup: bool = True, atomic: bool = True) -> bool:
        """
        安全写入文件内容（增强健壮性版本）

        Args:
            path: 文件路径
            content: 要写入的内容
            encoding: 文件编码
            backup: 是否创建备份
            atomic: 是否使用原子写入（先写临时文件再重命名）

        Returns:
            bool: 写入是否成功
        """
        try:
            # 输入验证
            if not path:
                logger.warning("文件路径为空")
                return False

            if content is None:
                logger.warning("写入内容为None")
                return False

            file_path = Path(path)

            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 检查磁盘空间（简单估算）
            try:
                content_size = len(content.encode(encoding))
                free_space = shutil.disk_usage(file_path.parent).free
                if content_size > free_space:
                    logger.error(f"磁盘空间不足: 需要 {content_size} bytes，可用 {free_space} bytes")
                    return False
            except Exception as space_error:
                logger.warning(f"无法检查磁盘空间: {space_error}")

            # 创建备份
            backup_path = None
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                try:
                    shutil.copy2(file_path, backup_path)
                    logger.debug(f"创建备份: {backup_path}")
                except Exception as backup_error:
                    logger.warning(f"创建备份失败: {backup_error}")

            if atomic:
                # 原子写入：先写临时文件再重命名
                temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
                try:
                    with open(temp_path, 'w', encoding=encoding) as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())  # 强制写入磁盘

                    # 原子重命名
                    temp_path.replace(file_path)
                    logger.debug(f"原子写入成功: {file_path}")

                except Exception as write_error:
                    # 清理临时文件
                    if temp_path.exists():
                        temp_path.unlink()
                    raise write_error
            else:
                # 直接写入
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                logger.debug(f"直接写入成功: {file_path}")

            return True

        except PermissionError as e:
            logger.error(f"文件权限错误: {e}")
            return False
        except OSError as e:
            logger.error(f"文件系统错误: {e}")
            return False
        except UnicodeEncodeError as e:
            logger.error(f"编码错误: {e}")
            return False
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            # 尝试恢复备份
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    logger.info(f"已恢复备份: {file_path}")
                except Exception as restore_error:
                    logger.error(f"恢复备份失败: {restore_error}")
            return False
    
    def safe_copy(self, src: Union[str, Path], dst: Union[str, Path], 
                  overwrite: bool = False) -> bool:
        """
        安全复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 复制是否成功
        """
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            if not src_path.exists():
                logger.error(f"源文件不存在: {src_path}")
                return False
            
            if dst_path.exists() and not overwrite:
                logger.warning(f"目标文件已存在: {dst_path}")
                return False
            
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            shutil.copy2(src_path, dst_path)
            logger.debug(f"文件复制成功: {src_path} -> {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件复制失败: {e}")
            return False
    
    def safe_move(self, src: Union[str, Path], dst: Union[str, Path], 
                  overwrite: bool = False) -> bool:
        """
        安全移动文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 移动是否成功
        """
        try:
            src_path = Path(src)
            dst_path = Path(dst)
            
            if not src_path.exists():
                logger.error(f"源文件不存在: {src_path}")
                return False
            
            if dst_path.exists() and not overwrite:
                logger.warning(f"目标文件已存在: {dst_path}")
                return False
            
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(str(src_path), str(dst_path))
            logger.debug(f"文件移动成功: {src_path} -> {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件移动失败: {e}")
            return False
    
    def safe_delete(self, path: Union[str, Path], force: bool = False) -> bool:
        """
        安全删除文件或目录
        
        Args:
            path: 要删除的路径
            force: 是否强制删除（用于目录）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return True
            
            if file_path.is_file():
                file_path.unlink()
                logger.debug(f"文件删除成功: {file_path}")
            elif file_path.is_dir():
                if force:
                    shutil.rmtree(file_path)
                    logger.debug(f"目录删除成功: {file_path}")
                else:
                    file_path.rmdir()  # 只删除空目录
                    logger.debug(f"空目录删除成功: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False
    
    def find_files(self, directory: Union[str, Path], pattern: str = "*", 
                   recursive: bool = True, include_dirs: bool = False) -> List[FileInfo]:
        """
        查找文件
        
        Args:
            directory: 搜索目录
            pattern: 文件名模式（支持通配符）
            recursive: 是否递归搜索
            include_dirs: 是否包含目录
            
        Returns:
            List[FileInfo]: 找到的文件信息列表
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                logger.error(f"目录不存在: {dir_path}")
                return []
            
            files = []
            
            if recursive:
                search_pattern = f"**/{pattern}"
            else:
                search_pattern = pattern
            
            for path in dir_path.glob(search_pattern):
                if path.is_file() or (include_dirs and path.is_dir()):
                    files.append(FileInfo(path))
            
            return files
            
        except Exception as e:
            logger.error(f"文件搜索失败: {e}")
            return []
    
    def get_directory_size(self, directory: Union[str, Path]) -> int:
        """
        获取目录大小
        
        Args:
            directory: 目录路径
            
        Returns:
            int: 目录大小（字节）
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                return 0
            
            total_size = 0
            for path in dir_path.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.error(f"计算目录大小失败: {e}")
            return 0
    
    def create_backup(self, source: Union[str, Path], backup_dir: Union[str, Path] = None) -> Optional[Path]:
        """
        创建备份
        
        Args:
            source: 源文件或目录路径
            backup_dir: 备份目录，默认为临时目录
            
        Returns:
            Optional[Path]: 备份文件路径，失败时返回None
        """
        try:
            source_path = Path(source)
            if not source_path.exists():
                logger.error(f"源路径不存在: {source_path}")
                return None
            
            if backup_dir is None:
                backup_dir = self.temp_dir / "backups"
            
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.name}_{timestamp}"
            
            if source_path.is_file():
                backup_path = backup_dir / f"{backup_name}{source_path.suffix}"
                shutil.copy2(source_path, backup_path)
            else:
                backup_path = backup_dir / f"{backup_name}.zip"
                self._create_zip_backup(source_path, backup_path)
            
            logger.info(f"备份创建成功: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return None
    
    def _create_zip_backup(self, source_dir: Path, backup_path: Path):
        """创建ZIP备份"""
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        清理临时文件
        
        Args:
            max_age_hours: 最大文件年龄（小时）
            
        Returns:
            int: 清理的文件数量
        """
        try:
            if not self.temp_dir.exists():
                return 0
            
            current_time = datetime.now()
            cleaned_count = 0
            
            for file_path in self.temp_dir.rglob('*'):
                if file_path.is_file():
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.total_seconds() > max_age_hours * 3600:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                        except Exception as e:
                            logger.warning(f"删除临时文件失败: {file_path}, {e}")
            
            logger.info(f"清理了 {cleaned_count} 个临时文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
            return 0
    
    def get_file_info(self, path: Union[str, Path]) -> Optional[FileInfo]:
        """
        获取文件信息
        
        Args:
            path: 文件路径
            
        Returns:
            Optional[FileInfo]: 文件信息，失败时返回None
        """
        try:
            return FileInfo(path)
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None


# 便捷函数
def ensure_directory(path: Union[str, Path]) -> bool:
    """确保目录存在的便捷函数"""
    manager = FileManager()
    return manager.ensure_directory(path)


def safe_copy(src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> bool:
    """安全复制文件的便捷函数"""
    manager = FileManager()
    return manager.safe_copy(src, dst, overwrite)


def safe_delete(path: Union[str, Path], force: bool = False) -> bool:
    """安全删除文件的便捷函数"""
    manager = FileManager()
    return manager.safe_delete(path, force)


def find_files(directory: Union[str, Path], pattern: str = "*", recursive: bool = True) -> List[FileInfo]:
    """查找文件的便捷函数"""
    manager = FileManager()
    return manager.find_files(directory, pattern, recursive)

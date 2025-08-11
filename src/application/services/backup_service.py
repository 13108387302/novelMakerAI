#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份服务

提供项目备份和版本控制功能
"""

import os
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.domain.entities.project import Project
from src.domain.entities.document import Document
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.document_repository import IDocumentRepository
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BackupInfo:
    """
    备份信息数据类

    记录项目备份的详细信息，包括备份路径、时间、大小等。

    Attributes:
        id: 备份唯一标识符
        project_id: 关联的项目ID
        backup_path: 备份文件路径
        created_at: 备份创建时间
        size: 备份文件大小（字节）
        description: 备份描述信息
        backup_type: 备份类型（manual/auto/scheduled）
    """
    id: str
    project_id: str
    backup_path: Path
    created_at: datetime
    size: int
    description: str = ""
    backup_type: str = "manual"  # manual, auto, scheduled


@dataclass
class VersionInfo:
    """
    版本信息数据类

    记录文档版本的详细信息，用于版本控制和历史追踪。

    Attributes:
        id: 版本唯一标识符
        document_id: 关联的文档ID
        version_number: 版本号
        content: 版本内容
        created_at: 版本创建时间
        description: 版本描述信息
        author: 版本作者
    """
    id: str
    document_id: str
    version_number: int
    content: str
    created_at: datetime
    description: str = ""
    author: str = ""


class BackupService:
    """
    备份服务

    提供项目备份和文档版本控制功能。
    支持手动备份、自动备份和定时备份。

    实现方式：
    - 使用ZIP格式压缩备份文件
    - 提供文档版本控制和历史管理
    - 支持备份清理和空间管理
    - 提供备份恢复和版本回滚功能

    Attributes:
        project_repository: 项目仓储接口
        document_repository: 文档仓储接口
        backup_dir: 备份存储目录
        versions_dir: 版本存储目录
        max_backups: 最大备份数量
        auto_backup_interval: 自动备份间隔（分钟）
        max_versions_per_document: 每个文档最大版本数
    """

    def __init__(
        self,
        project_repository: IProjectRepository,
        document_repository: IDocumentRepository,
        backup_dir: Path
    ):
        """
        初始化备份服务

        Args:
            project_repository: 项目仓储接口
            document_repository: 文档仓储接口
            backup_dir: 备份存储目录路径
        """
        self.project_repository = project_repository
        self.document_repository = document_repository
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"备份服务初始化: backup_dir={self.backup_dir}")

        # 版本存储目录
        self.versions_dir = backup_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"版本目录: versions_dir={self.versions_dir}")

        # 备份配置
        self.max_backups = 50  # 最大备份数量
        self.auto_backup_interval = 30  # 自动备份间隔（分钟）
        self.max_versions_per_document = 20  # 每个文档最大版本数

        logger.debug("备份服务初始化完成")
    
    async def create_backup(
        self,
        project_id: str,
        description: str = "",
        backup_type: str = "manual"
    ) -> Optional[BackupInfo]:
        """创建项目备份"""
        try:
            logger.info(f"[备份] 开始创建: project_id={project_id}")
            # 获取项目信息
            # 更稳健：优先通过 load 加载（支持自定义路径与索引回退）
            project = await self.project_repository.load(project_id)
            logger.debug(f"[备份] 项目加载结果: exists={bool(project)} title={(getattr(project,'name',None) or getattr(project,'title',None))}")
            if not project:
                logger.error(f"项目不存在: {project_id}")
                return None

            # 获取项目文档（完整加载，包含正文）
            documents = await self.document_repository.list_by_project(project_id)
            logger.info(f"[备份] 文档数量: {len(documents)}")
            full_documents = []
            try:
                for d in documents:
                    try:
                        loaded = await self.document_repository.load(d.id)
                        if loaded:
                            full_documents.append(loaded)
                        else:
                            full_documents.append(d)
                    except Exception:
                        full_documents.append(d)
                logger.info(f"[备份] 完整加载文档数量: {len(full_documents)}")
            except Exception as e:
                logger.warning(f"[备份] 完整加载文档失败，回退使用轻量文档: {e}")
                full_documents = documents

            # 生成备份ID和路径
            backup_id = f"{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / f"{backup_id}.zip"
            logger.info(f"[备份] 目标路径: {backup_path}")

            # 创建备份ZIP文件
            try:
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    # 添加项目信息（将正文一并写入project.json，作为冗余）
                    try:
                        project_data = {
                            "project": project.to_dict() if hasattr(project, 'to_dict') else {},
                            "documents": [doc.to_dict() if hasattr(doc, 'to_dict') else {} for doc in full_documents],
                            "backup_info": {
                                "id": backup_id,
                                "created_at": datetime.now().isoformat(),
                                "description": description,
                                "backup_type": backup_type
                            }
                        }

                        zipf.writestr("project.json", json.dumps(project_data, ensure_ascii=False, indent=2, default=str))
                        logger.info(f"[备份] 写入project.json，包含文档数: {len(project_data.get('documents', []))}")

                    except Exception as e:
                        logger.error(f"序列化项目数据失败: {e}")
                        raise

                    # 添加文档内容（独立正文文件，便于快速恢复）
                    for doc in full_documents:
                        try:
                            content = getattr(doc, 'content', '') or ''
                            doc_filename = f"documents/{doc.id}.txt"
                            zipf.writestr(doc_filename, content)
                            logger.info(f"[备份] 写入文档正文: {doc_filename} len={len(content)}")
                        except Exception as e:
                            logger.warning(f"添加文档内容失败 {getattr(doc,'id','?')}: {e}")
                            continue

            except Exception as e:
                # 清理失败的备份文件
                if backup_path.exists():
                    backup_path.unlink()
                raise

            # 创建备份信息
            backup_info = BackupInfo(
                id=backup_id,
                project_id=project_id,
                backup_path=backup_path,
                created_at=datetime.now(),
                size=backup_path.stat().st_size,
                description=description,
                backup_type=backup_type
            )

            # 清理旧备份
            await self._cleanup_old_backups(project_id)

            logger.info(f"项目备份创建成功: {backup_path}")
            return backup_info

        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return None
    
    async def restore_backup(self, backup_path: Path, target_root_path: Optional[Path] = None) -> Optional[str]:
        """恢复备份"""
        try:
            logger.info(f"[恢复] 开始恢复: path={backup_path}")
            if not backup_path.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return None

            # 验证备份文件
            if not zipfile.is_zipfile(backup_path):
                logger.error(f"无效的备份文件格式: {backup_path}")
                return None

            # 解压备份文件
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # 读取项目信息
                project_json = zipf.read("project.json").decode('utf-8')
                logger.debug(f"[恢复] project.json 大小: {len(project_json)}")
                project_data = json.loads(project_json)
                logger.debug(f"[恢复] 包含文档数: {len(project_data.get('documents', []))}")

                # 恢复项目
                project_dict = project_data["project"]
                try:
                    project = Project.from_dict(project_dict)
                except Exception:
                    # 兼容旧备份格式
                    project = Project(**project_dict)

                # 如果未包含 root_path，则使用目标路径（用于覆盖当前项目目录）
                try:
                    if (not getattr(project, 'root_path', None)) and target_root_path:
                        logger.info(f"[恢复] 设置项目root_path: {target_root_path}")
                        project.root_path = target_root_path
                except Exception as e:
                    logger.debug(f"[恢复] 设置root_path失败: {e}")

                # 保存项目
                await self.project_repository.save(project)

                # 恢复文档（全量回滚：先删除现存中不在备份内的文档，再写入备份中的文档）
                documents_data = project_data.get("documents", [])
                backup_doc_ids = set()
                for d in documents_data:
                    try:
                        if isinstance(d, dict) and d.get("id"):
                            backup_doc_ids.add(d.get("id"))
                    except Exception:
                        continue
                logger.info(f"[恢复] 备份文档IDs: {sorted(list(backup_doc_ids))}")

                # 删除项目中多余的文档（不在备份里的）
                try:
                    # 恢复前清理项目级缓存，确保列出真实文件
                    try:
                        # 优先按项目清理
                        clear_project_fn = getattr(self.document_repository, '_clear_project_cache', None)
                        if callable(clear_project_fn):
                            clear_project_fn(project.id)
                            logger.info(f"[恢复] 已清理项目文档缓存: {project.id}")
                        # 兜底：直接删除统一性能管理器中的特定键
                        pm = getattr(self.document_repository, 'performance_manager', None)
                        cache_prefix = getattr(self.document_repository, '_cache_prefix', 'doc_repo')
                        if pm:
                            pm.cache_delete(f"{cache_prefix}:project_docs:{project.id}")
                            logger.debug(f"[恢复] 已删除缓存键: {cache_prefix}:project_docs:{project.id}")
                    except Exception as ce:
                        logger.debug(f"[恢复] 清理文档缓存失败: {ce}")

                    current_docs = await self.document_repository.list_by_project(project.id)
                    current_ids = [getattr(cd, 'id', None) for cd in (current_docs or [])]
                    logger.info(f"[恢复] 当前项目文档IDs: {current_ids}")
                    for cd in current_docs or []:
                        try:
                            if getattr(cd, 'id', None) and cd.id not in backup_doc_ids:
                                ok = await self.document_repository.delete(cd.id)
                                logger.info(f"[恢复] 删除多余文档: {cd.id} ok={ok}")
                        except Exception as de:
                            logger.warning(f"删除多余文档失败: {getattr(cd, 'id', None)} - {de}")

                    # 目录级别兜底清理：直接扫描 documents 目录与类型子目录
                    try:
                        base_path = getattr(self.document_repository, 'base_path', None)
                        if base_path:
                            logger.info(f"[恢复] 目录清理起点: {base_path}")
                            to_remove = []
                            # 收集所有 .json 和 _content.txt
                            candidates = list(base_path.glob("*.json")) + list(base_path.glob("*_content.txt"))
                            # 类型子目录
                            for sub in [p for p in base_path.iterdir() if p.is_dir()]:
                                candidates += list(sub.glob("*.json")) + list(sub.glob("*_content.txt"))
                            for f in candidates:
                                stem = f.stem.replace("_content", "")
                                if stem and stem not in backup_doc_ids:
                                    to_remove.append(f)
                            for f in to_remove:
                                try:
                                    f.unlink(missing_ok=True)
                                    logger.info(f"[恢复] 目录清理: 删除文件 {f}")
                                except Exception as fe:
                                    logger.warning(f"[恢复] 目录清理失败: {f} - {fe}")
                    except Exception as de:
                        logger.debug(f"[恢复] 目录级别清理失败: {de}")
                except Exception as e:
                    logger.warning(f"获取当前项目文档失败，跳过删除多余文档: {e}")

                # 写入备份中的文档
                for doc_data in documents_data:
                    try:
                        document = Document.from_dict(doc_data)
                    except Exception:
                        document = Document(**doc_data)

                    # 读取文档内容
                    doc_filename = f"documents/{document.id}.txt"
                    try:
                        document.content = zipf.read(doc_filename).decode('utf-8')
                        logger.debug(f"[恢复] 读取正文: {doc_filename} len={len(document.content)}")
                    except KeyError:
                        document.content = document.content or ""
                        logger.debug(f"[恢复] 备份缺少正文文件，使用现有content: {doc_filename}")

                    # 保存文档
                    ok = await self.document_repository.save(document)
                    logger.info(f"[恢复] 写入文档: id={document.id} title={getattr(document,'title','')} ok={ok}")

            logger.info(f"备份恢复成功: {backup_path}")
            return project.id

        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return None
    
    async def list_backups(self, project_id: Optional[str] = None) -> List[BackupInfo]:
        """列出备份"""
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob("*.zip"):
                try:
                    # 解析备份文件名
                    backup_id = backup_file.stem
                    
                    # 如果指定了项目ID，过滤备份
                    if project_id and not backup_id.startswith(project_id):
                        continue
                    
                    # 读取备份信息
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        project_data = json.loads(zipf.read("project.json").decode('utf-8'))
                        backup_data = project_data.get("backup_info", {})
                        
                        backup_info = BackupInfo(
                            id=backup_id,
                            project_id=project_data["project"]["id"],
                            backup_path=backup_file,
                            created_at=datetime.fromisoformat(backup_data.get("created_at", datetime.now().isoformat())),
                            size=backup_file.stat().st_size,
                            description=backup_data.get("description", ""),
                            backup_type=backup_data.get("backup_type", "manual")
                        )

                        backups.append(backup_info)


                except Exception as e:
                    logger.warning(f"读取备份文件失败: {backup_file}, {e}")
                    continue
            
            # 按创建时间排序
            backups.sort(key=lambda x: x.created_at, reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    async def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        try:
            backup_path = self.backup_dir / f"{backup_id}.zip"
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"备份删除成功: {backup_path}")
                return True
            else:
                logger.warning(f"备份文件不存在: {backup_path}")
                return False
                
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return False
    
    async def create_document_version(
        self,
        document_id: str,
        content: str,
        description: str = "",
        author: str = ""
    ) -> Optional[VersionInfo]:
        """创建文档版本"""
        try:
            # 获取现有版本
            versions = await self.list_document_versions(document_id)
            version_number = len(versions) + 1
            
            # 创建版本信息
            version_id = f"{document_id}_v{version_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            version_path = self.versions_dir / f"{version_id}.json"
            
            version_info = VersionInfo(
                id=version_id,
                document_id=document_id,
                version_number=version_number,
                content=content,
                created_at=datetime.now(),
                description=description,
                author=author
            )
            
            # 保存版本文件
            with open(version_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(version_info), f, ensure_ascii=False, indent=2, default=str)
            
            # 清理旧版本
            await self._cleanup_old_versions(document_id)
            
            logger.info(f"文档版本创建成功: {version_path}")
            return version_info
            
        except Exception as e:
            logger.error(f"创建文档版本失败: {e}")
            return None
    
    async def list_document_versions(self, document_id: str) -> List[VersionInfo]:
        """列出文档版本"""
        try:
            versions = []
            
            for version_file in self.versions_dir.glob(f"{document_id}_v*.json"):
                try:
                    with open(version_file, 'r', encoding='utf-8') as f:
                        version_data = json.load(f)
                        
                    # 处理日期时间字段
                    if isinstance(version_data['created_at'], str):
                        version_data['created_at'] = datetime.fromisoformat(version_data['created_at'])
                    
                    version_info = VersionInfo(**version_data)
                    versions.append(version_info)
                    
                except Exception as e:
                    logger.warning(f"读取版本文件失败: {version_file}, {e}")
                    continue
            
            # 按版本号排序
            versions.sort(key=lambda x: x.version_number, reverse=True)
            return versions
            
        except Exception as e:
            logger.error(f"列出文档版本失败: {e}")
            return []
    
    async def restore_document_version(self, version_id: str) -> Optional[str]:
        """恢复文档版本"""
        try:
            version_path = self.versions_dir / f"{version_id}.json"
            if not version_path.exists():
                logger.error(f"版本文件不存在: {version_path}")
                return None
            
            with open(version_path, 'r', encoding='utf-8') as f:
                version_data = json.load(f)
            
            return version_data.get("content", "")
            
        except Exception as e:
            logger.error(f"恢复文档版本失败: {e}")
            return None
    
    async def _cleanup_old_backups(self, project_id: str):
        """清理旧备份"""
        try:
            backups = await self.list_backups(project_id)
            if len(backups) > self.max_backups:
                # 删除最旧的备份
                old_backups = backups[self.max_backups:]
                for backup in old_backups:
                    await self.delete_backup(backup.id)
                    
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
    
    async def _cleanup_old_versions(self, document_id: str):
        """清理旧版本"""
        try:
            versions = await self.list_document_versions(document_id)
            if len(versions) > self.max_versions_per_document:
                # 删除最旧的版本
                old_versions = versions[self.max_versions_per_document:]
                for version in old_versions:
                    version_path = self.versions_dir / f"{version.id}.json"
                    if version_path.exists():
                        version_path.unlink()
                        
        except Exception as e:
            logger.error(f"清理旧版本失败: {e}")
    
    async def auto_backup_check(self, project_id: str) -> bool:
        """检查是否需要自动备份"""
        try:
            backups = await self.list_backups(project_id)
            auto_backups = [b for b in backups if b.backup_type == "auto"]
            
            if not auto_backups:
                return True  # 没有自动备份，需要创建
            
            # 检查最近的自动备份时间
            latest_backup = auto_backups[0]
            time_diff = datetime.now() - latest_backup.created_at
            
            return time_diff.total_seconds() > (self.auto_backup_interval * 60)
            
        except Exception as e:
            logger.error(f"检查自动备份失败: {e}")
            return False

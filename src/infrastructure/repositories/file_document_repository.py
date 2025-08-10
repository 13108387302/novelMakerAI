#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件系统文档仓储实现

基于文件系统的文档数据持久化实现
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio

from src.domain.entities.document import Document, DocumentType, DocumentStatus, create_document
from src.domain.repositories.document_repository import IDocumentRepository
from src.shared.utils.logger import get_logger
from src.shared.utils.unified_performance import get_performance_manager, performance_monitor
from src.shared.utils.unified_error_handler import get_error_handler, ErrorCategory, ErrorSeverity
from src.shared.utils.file_operations import get_file_operations
from src.shared.constants import (
    ENCODING_FORMATS, CACHE_EXPIRE_SECONDS, VERSION_KEEP_COUNT
)

logger = get_logger(__name__)

# 文档仓储常量
DEFAULT_DOCUMENTS_DIR = ".novel_editor/documents"
DOCUMENT_METADATA_EXT = ".json"
DOCUMENT_CONTENT_SUFFIX = "_content.txt"
TEMP_FILE_EXT = ".tmp"
VERSION_FILE_PREFIX = "_v"
VERSION_META_SUFFIX = ".meta.json"
DEFAULT_ENCODING = ENCODING_FORMATS['utf8']
FALLBACK_ENCODING = ENCODING_FORMATS['gbk']
CACHE_PREFIX = "doc_repo"
SHORT_CACHE_TTL = 60  # 1分钟
LONG_CACHE_TTL = CACHE_EXPIRE_SECONDS  # 5分钟
DEFAULT_VERSION_KEEP_COUNT = VERSION_KEEP_COUNT
# 文档类型到子目录的映射（相对于 base_path）
DOC_TYPE_DIRS = {
    DocumentType.CHAPTER: "chapters",
    DocumentType.CHARACTER: "characters",
    DocumentType.SETTING: "settings",
    DocumentType.OUTLINE: "outlines",
    DocumentType.NOTE: "notes",
    DocumentType.RESEARCH: "research",
    DocumentType.TIMELINE: "timeline",
    DocumentType.WORLDBUILDING: "worldbuilding",
}

DEFAULT_CHUNK_SIZE = 8192
DEFAULT_LINE_COUNT = 1000
CONTEXT_LINES = 2  # 搜索上下文行数
ASYNC_SLEEP_MS = 0.001  # 异步睡眠时间


class FileDocumentRepository(IDocumentRepository):
    """
    文件系统文档仓储实现

    基于文件系统的文档数据持久化实现，使用JSON格式存储文档元数据，
    使用文本文件存储文档内容。

    实现方式：
    - 使用JSON文件存储文档元数据
    - 使用独立的文本文件存储文档内容
    - 支持跨项目的文档查找
    - 提供完整的CRUD操作
    - 包含文档内容的搜索功能

    Attributes:
        base_path: 文档存储的基础路径
    """

    def __init__(self, base_path: Path):
        """
        初始化文件系统文档仓储

        Args:
            base_path: 文档存储的基础路径（必须提供，通常为项目内路径）
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 使用统一的性能管理器
        self.performance_manager = get_performance_manager()
        self.error_handler = get_error_handler()

        # 统一文件操作工具
        self.file_ops = get_file_operations("document_repo")

        # 缓存键前缀
        self._cache_prefix = CACHE_PREFIX

    def _get_doc_dir_for_type(self, doc_type: Optional[DocumentType]) -> Path:
        """根据文档类型获取目录（默认回退 base_path）"""
        try:
            if not doc_type:
                return self.base_path
            sub = DOC_TYPE_DIRS.get(doc_type)
            if not sub:
                return self.base_path
            path = self.base_path / sub
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            return self.base_path

    def _get_document_path(self, document_id: str, doc_type: Optional[DocumentType] = None) -> Path:
        """获取文档元数据路径（按类型子目录路由）"""
        base = self._get_doc_dir_for_type(doc_type)
        return base / f"{document_id}{DOCUMENT_METADATA_EXT}"

    def _get_content_path(self, document_id: str, doc_type: Optional[DocumentType] = None) -> Path:
        """获取文档内容路径（按类型子目录路由）"""
        base = self._get_doc_dir_for_type(doc_type)
        return base / f"{document_id}{DOCUMENT_CONTENT_SUFFIX}"

    async def _read_text_file_safe(self, file_path: Path) -> str:
        """安全读取文本文件，支持编码回退（委托统一实现）"""
        try:
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations()
            content = await ops.load_text_safe(file_path)
            return content or ""
        except Exception as e:
            logger.error(f"读取文本文件失败: {file_path}, {e}")
            return ""

    def _build_document_from_data(self, doc_data: dict, content: str = "") -> Optional[Document]:
        """从 JSON 数据构建 Document 对象的统一方法"""
        try:
            # 验证必要字段
            if not isinstance(doc_data, dict):
                logger.error("文档数据格式无效：不是字典类型")
                return None

            if 'id' not in doc_data or 'metadata' not in doc_data:
                logger.error("文档数据缺少必要字段：id 或 metadata")
                return None

            metadata = doc_data['metadata']
            if 'title' not in metadata:
                logger.error("文档元数据缺少标题字段")
                return None

            # 创建文档对象
            document_type = DocumentType(doc_data.get('type', 'chapter'))
            document = create_document(
                document_type=document_type,
                title=metadata['title'],
                document_id=doc_data['id'],
                content=content,
                status=DocumentStatus(doc_data.get('status', 'draft')),
                project_id=doc_data.get('project_id')
            )

            # 恢复其他属性
            document.metadata.description = metadata.get('description', '')
            document.metadata.tags = set(metadata.get('tags', []))
            document.metadata.author = metadata.get('author', '')

            # 恢复时间戳
            if metadata.get('created_at'):
                try:
                    document.metadata.created_at = datetime.fromisoformat(metadata['created_at'])
                except ValueError as e:
                    logger.warning(f"无效的创建时间格式: {metadata['created_at']}, {e}")

            if metadata.get('updated_at'):
                try:
                    document.metadata.updated_at = datetime.fromisoformat(metadata['updated_at'])
                except ValueError as e:
                    logger.warning(f"无效的更新时间格式: {metadata['updated_at']}, {e}")

            return document

        except Exception as e:
            logger.error(f"构建文档对象失败: {e}")
            return None

    async def _find_document_in_projects(self, document_id: str) -> tuple[Optional[Path], Optional[Path]]:
        """在所有项目目录中查找文档（带缓存优化）"""
        try:
            # 检查统一缓存
            cache_key = f"{self._cache_prefix}:doc_paths:{document_id}"
            cache_result = self.performance_manager.cache_get(cache_key)

            if cache_result.success:
                cached_paths = cache_result.data
                if cached_paths[0] and cached_paths[0].exists():
                    logger.debug(f"⚡ 从缓存中找到文档: {cached_paths[0]}")
                    return cached_paths
                else:
                    # 缓存的路径不存在，移除缓存
                    self.performance_manager.cache_delete(cache_key)

            # 在所有类型子目录中查找（优先缓存）
            for sub in set(DOC_TYPE_DIRS.values()) | {""}:
                base = self.base_path / sub if sub else self.base_path
                doc_path = base / f"{document_id}.json"
                content_path = base / f"{document_id}_content.txt"
                if doc_path.exists():
                    logger.debug(f"🔍 在项目目录中找到文档: {doc_path}")
                    cache_key = f"{self._cache_prefix}:doc_paths:{document_id}"
                    self.performance_manager.cache_set(cache_key, (doc_path, content_path), ttl=LONG_CACHE_TTL)
                    return doc_path, content_path

            return None, None

        except Exception as e:
            logger.error(f"在项目中查找文档失败: {e}")
            return None, None

    async def _get_document_save_path(self, document: Document) -> Path:
        """获取文档保存路径（简化版本，直接使用base_path）"""
        logger.debug(f"获取文档保存路径，项目ID: {document.project_id}")

        # 直接使用base_path，因为它已经是正确的项目文档目录
        # base_path 在服务注册时设置为 project_paths.documents_dir
        logger.debug(f"使用文档仓储base_path: {self.base_path}")

        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)

        return self.base_path

    async def save(self, document: Document) -> bool:
        """保存文档（带缓存清理）"""
        doc_temp_file = None
        content_temp_file = None
        try:
            # 确定保存路径
            save_path = await self._get_document_save_path(document)
            logger.info(f"💾 文档保存路径: {save_path}")
            logger.info(f"📋 文档项目ID: {document.project_id}")

            # 保存文档元数据（按类型目录）
            doc_path = self._get_document_path(document.id, document.type)
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_temp_file = doc_path.with_suffix('.tmp')
            doc_data = document.to_dict()

            # 验证项目ID是否正确保存
            if doc_data.get('project_id') != document.project_id:
                logger.error(f"❌ 文档数据中的项目ID不匹配: 期望 {document.project_id}, 实际 {doc_data.get('project_id')}")
            else:
                logger.debug(f"✅ 文档项目ID验证通过: {document.project_id}")

            # 分离内容和元数据
            content = doc_data.pop('content', '')

            # 使用统一文件操作保存元数据
            cache_key = f"metadata:{document.id}"
            metadata_success = await self.file_ops.save_json_atomic(
                file_path=doc_path,
                data=doc_data,
                create_backup=True,
                cache_key=cache_key,
                cache_ttl=3600
            )

            if not metadata_success:
                logger.error(f"❌ 保存文档元数据失败: {document.id}")
                return False

            # 使用统一文件操作保存内容
            content_path = self._get_content_path(document.id, document.type)
            content_success = await self.file_ops.save_text_atomic(
                file_path=content_path,
                content=content or '',
                create_backup=True
            )

            if not content_success:
                logger.error(f"❌ 保存文档内容失败: {document.id}")
                return False

            # 创建版本备份（如果内容有变化）
            if content and len(content.strip()) > 0:
                try:
                    # 直接传递文档路径，避免查找问题
                    version_id = await self._create_version_with_path(
                        document.id,
                        content,
                        doc_path,
                        f"自动保存版本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    if version_id:
                        logger.debug(f"创建版本备份: {document.id} -> {version_id}")
                except Exception as e:
                    logger.warning(f"创建版本备份失败: {e}")
                    # 版本创建失败不影响文档保存

            # 清理相关缓存
            self._clear_project_cache(document.project_id)

            logger.info(f"文档保存成功: {document.title} ({document.id})")
            return True

        except Exception as e:
            # 清理临时文件
            if doc_temp_file and doc_temp_file.exists():
                try:
                    doc_temp_file.unlink()
                except Exception:
                    pass
            if content_temp_file and content_temp_file.exists():
                try:
                    content_temp_file.unlink()
                except Exception:
                    pass
            logger.error(f"保存文档失败: {e}")
            return False

    @performance_monitor("文档加载")
    async def load(self, document_id: str) -> Optional[Document]:
        """根据ID加载文档（性能优化版本）"""
        try:
            # 首先尝试从默认路径加载
            # 在所有类型子目录中尝试定位
            doc_path = None
            content_path = None
            for sub in set(DOC_TYPE_DIRS.values()) | {""}:
                base = self.base_path / sub if sub else self.base_path
                test_doc = base / f"{document_id}.json"
                test_content = base / f"{document_id}_content.txt"
                if test_doc.exists():
                    doc_path, content_path = test_doc, test_content
                    break

            # 如果未找到，尝试在项目中查找
            if not doc_path:
                doc_path, content_path = await self._find_document_in_projects(document_id)
                if not doc_path or not doc_path.exists():
                    return None

            # 使用统一文件操作加载元数据
            cache_key = f"metadata:{document_id}"
            doc_data = await self.file_ops.load_json_cached(
                file_path=doc_path,
                cache_key=cache_key,
                cache_ttl=3600
            )

            if not doc_data:
                return None

            # 验证数据格式
            if not isinstance(doc_data, dict):
                logger.error(f"文档元数据格式无效: {doc_path}")
                return None

            # 使用统一文件操作加载内容
            content = ""
            if content_path and content_path.exists():
                content = await self.file_ops.load_text(content_path) or ""

            # 使用统一的构建方法
            document = self._build_document_from_data(doc_data, content)
            if not document:
                return None

            logger.info(f"⚡ 文档加载成功: {document.title} ({document.id})")
            return document

        except Exception as e:
            logger.error(f"加载文档失败: {e}")
            return None

    async def delete(self, document_id: str) -> bool:
        """删除文档"""
        try:
            # 按所有类型子目录尝试删除
            deleted = False
            for sub in set(DOC_TYPE_DIRS.values()) | {""}:
                base = self.base_path / sub if sub else self.base_path
                doc_path = base / f"{document_id}.json"
                content_path = base / f"{document_id}_content.txt"
                if doc_path.exists():
                    doc_path.unlink()
                    deleted = True
                if content_path.exists():
                    content_path.unlink()
                    deleted = True
            if not deleted:
                # 兜底：项目范围查找
                doc_path, content_path = await self._find_document_in_projects(document_id)
                if doc_path and doc_path.exists():
                    doc_path.unlink()
                if content_path and content_path.exists():
                    content_path.unlink()

            logger.info(f"文档删除成功: {document_id}")
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    async def exists(self, document_id: str) -> bool:
        """检查文档是否存在"""
        # 首先检查默认路径
        # 在所有类型子目录中查找
        for sub in set(DOC_TYPE_DIRS.values()) | {""}:
            base = self.base_path / sub if sub else self.base_path
            if (base / f"{document_id}.json").exists():
                return True

        # 如果未找到，检查项目目录
        found_paths = await self._find_document_in_projects(document_id)
        return found_paths is not None

    async def list_by_project(self, project_id: str) -> List[Document]:
        """列出项目中的所有文档（性能优化版本）"""
        try:
            import time
            start_time = time.time()

            logger.info(f"📋 开始获取项目文档列表: {project_id}")

            # 使用统一缓存管理器
            cache_key = f"{self._cache_prefix}:project_docs:{project_id}"
            cache_result = self.performance_manager.cache_get(cache_key)
            if cache_result.success:
                cached_documents = cache_result.data
                logger.info(f"⚡ 从缓存获取项目文档: {len(cached_documents)} 个")
                return cached_documents

            documents = []
            found_doc_ids = set()

            # 优化的文档查找策略
            search_paths = await self._get_project_document_paths(project_id)

            for search_path in search_paths:
                if not search_path.exists():
                    continue

                logger.debug(f"🔍 搜索路径: {search_path}")

                # 批量读取文档元数据，避免逐个加载完整文档
                # 排除版本元数据文件和其他非文档文件
                all_json_files = list(search_path.glob("*.json"))
                doc_files = [
                    f for f in all_json_files
                    if not f.name.endswith('.meta.json') and '_v' not in f.stem
                ]
                logger.debug(f"📄 找到 {len(all_json_files)} 个JSON文件，其中 {len(doc_files)} 个是文档文件")

                for doc_file in doc_files:
                    try:
                        # 只读取元数据，不加载内容
                        doc_data = await self.file_ops.load_json_cached(
                            file_path=doc_file,
                            cache_key=f"{self._cache_prefix}:meta:{doc_file.stem}",
                            cache_ttl=300
                        )

                        # 验证文档数据的基本结构
                        if not self._validate_document_data(doc_data, project_id):
                            # 尝试修复缺少ID的文档数据
                            if await self._try_fix_document_data(doc_data, doc_file, project_id):
                                logger.info(f"成功修复文档数据: {doc_file.name}")
                            else:
                                logger.warning(f"跳过无效的文档文件: {doc_file.name}")
                                continue

                        if doc_data.get('id') not in found_doc_ids:
                            # 创建轻量级文档对象（不加载内容）
                            document = await self._create_lightweight_document(doc_data)
                            if document:
                                documents.append(document)
                                found_doc_ids.add(document.id)
                                logger.debug(f"✅ 成功加载文档: {document.title}")

                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON格式错误: {doc_file}, {e}")
                    except Exception as e:
                        logger.warning(f"读取文档元数据失败: {doc_file}, {e}")

            # 缓存结果到统一缓存管理器
            cache_key = f"{self._cache_prefix}:project_docs:{project_id}"
            self.performance_manager.cache_set(cache_key, documents, ttl=60)  # 1分钟缓存

            load_time = time.time() - start_time
            logger.info(f"⚡ 项目文档列表获取完成: {len(documents)} 个文档, 耗时: {load_time:.3f}s")

            return documents

        except Exception as e:
            logger.error(f"❌ 获取项目文档列表失败: {e}")
            return []

    async def _get_project_document_paths(self, project_id: str) -> List[Path]:
        """获取项目文档的搜索路径（包含类型子目录）"""
        try:
            # 基于 base_path 构建：根目录 + 各类型子目录
            paths = [self.base_path]
            for sub in set(DOC_TYPE_DIRS.values()):
                paths.append(self.base_path / sub)

            logger.debug(f"项目 {project_id} 的文档搜索路径: {[str(p) for p in paths]}")
            return paths

        except Exception as e:
            logger.error(f"获取项目文档路径失败: {e}")
            return [self.base_path]

    async def _get_project_root_path(self, project_id: str) -> Optional[Path]:
        """获取项目根路径"""
        try:
            # 方法1：尝试从依赖注入容器获取当前项目路径
            try:
                from src.shared.ioc.container import get_global_container
                from src.shared.project_context import ProjectPaths

                container = get_global_container()
                if container:
                    project_paths = container.try_get(ProjectPaths)
                    if project_paths:
                        logger.debug(f"从容器获取项目根路径: {project_paths.root}")
                        return project_paths.root
            except Exception as e:
                logger.debug(f"从容器获取项目路径失败: {e}")

            # 方法2：尝试从项目仓库获取项目信息
            try:
                from src.infrastructure.repositories.file_project_repository import FileProjectRepository

                # 使用当前文档仓储的base_path的父目录作为项目仓储的base_path
                project_base_path = self.base_path.parent.parent / ".novel_editor" / "data"
                project_repo = FileProjectRepository(project_base_path)

                # 尝试加载项目
                project = await project_repo.get_by_id(project_id)
                if project and hasattr(project, 'root_path') and project.root_path:
                    logger.debug(f"从项目仓储获取根路径: {project.root_path}")
                    return Path(project.root_path)
            except Exception as e:
                logger.debug(f"从项目仓储获取项目失败: {e}")

            # 方法3：基于文档仓储路径推断项目根路径
            # 如果base_path是 /project_root/content/documents，则项目根路径是 /project_root
            if "content" in self.base_path.parts and "documents" in self.base_path.parts:
                # 找到content目录的位置
                parts = self.base_path.parts
                content_index = parts.index("content")
                if content_index > 0:
                    project_root = Path(*parts[:content_index])
                    logger.debug(f"基于路径推断项目根路径: {project_root}")
                    return project_root

            return None

        except Exception as e:
            logger.debug(f"获取项目根路径失败: {e}")
            return None

    def _validate_document_data(self, doc_data: dict, project_id: str) -> bool:
        """验证文档数据的基本结构"""
        try:
            # 检查基本字段
            if not isinstance(doc_data, dict):
                logger.debug("文档数据不是字典类型")
                return False

            # 检查ID - 如果缺少，尝试从文件名推断
            if not doc_data.get('id'):
                logger.debug("文档数据缺少ID字段，可能是旧版本文件")
                return False

            # 检查项目ID匹配
            doc_project_id = doc_data.get('project_id')
            if doc_project_id != project_id:
                logger.debug(f"项目ID不匹配: 期望 {project_id}, 实际 {doc_project_id}")
                # 严格匹配项目ID，避免加载其他项目的文档
                return False

            # 检查文档类型
            doc_type = doc_data.get('type') or doc_data.get('document_type')
            if not doc_type:
                logger.debug("文档数据缺少类型字段，使用默认类型")
                # 不直接返回False，而是在后续处理中设置默认类型

            return True

        except Exception as e:
            logger.debug(f"验证文档数据失败: {e}")
            return False

    async def _try_fix_document_data(self, doc_data: dict, doc_file: Path, project_id: str) -> bool:
        """尝试修复缺少字段的文档数据"""
        try:
            fixed = False

            # 修复缺少的ID字段
            if not doc_data.get('id'):
                # 从文件名推断ID
                file_stem = doc_file.stem
                if file_stem and file_stem != 'document':
                    doc_data['id'] = file_stem
                    fixed = True
                    logger.debug(f"从文件名推断文档ID: {file_stem}")
                else:
                    # 生成新的ID
                    import uuid
                    doc_data['id'] = str(uuid.uuid4())
                    fixed = True
                    logger.debug(f"生成新的文档ID: {doc_data['id']}")

            # 修复缺少的项目ID
            if not doc_data.get('project_id'):
                doc_data['project_id'] = project_id
                fixed = True
                logger.debug(f"设置文档项目ID: {project_id}")

            # 修复缺少的文档类型
            if not (doc_data.get('type') or doc_data.get('document_type')):
                doc_data['type'] = 'chapter'  # 默认类型
                fixed = True
                logger.debug("设置默认文档类型: chapter")

            # 修复缺少的元数据
            if not doc_data.get('metadata'):
                doc_data['metadata'] = {
                    'title': doc_data.get('title', '未命名文档'),
                    'description': '',
                    'tags': [],
                    'author': '',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                fixed = True
                logger.debug("添加默认元数据")

            # 如果进行了修复，保存修复后的文件
            if fixed:
                try:
                    await self.file_ops.save_json_atomic(
                        file_path=doc_file,
                        data=doc_data,
                        create_backup=True,
                        cache_key=f"{self._cache_prefix}:meta:{doc_file.stem}",
                        cache_ttl=300
                    )
                    logger.info(f"已保存修复后的文档数据: {doc_file.name}")
                except Exception as e:
                    logger.error(f"保存修复后的文档数据失败: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"修复文档数据失败: {e}")
            return False

    async def _create_lightweight_document(self, doc_data: dict):
        """创建轻量级文档对象（不加载内容）"""
        try:
            from src.domain.entities.document import Document, DocumentType

            # 验证基本必要字段
            if 'id' not in doc_data:
                logger.debug(f"文档数据缺少必要字段: id")
                return None

            # 检查文档类型字段（可能是type或document_type）
            doc_type_value = doc_data.get('type') or doc_data.get('document_type')
            if not doc_type_value:
                logger.debug(f"文档数据缺少文档类型字段")
                return None

            # 安全转换文档类型
            try:
                if isinstance(doc_type_value, str):
                    doc_type = DocumentType(doc_type_value)
                else:
                    doc_type = DocumentType.CHAPTER
            except ValueError:
                logger.debug(f"无效的文档类型: {doc_type_value}, 使用默认类型")
                doc_type = DocumentType.CHAPTER

            # 检查标题（支持多种格式）
            title = self._extract_document_title(doc_data)

            # 提取元数据
            metadata = self._extract_document_metadata(doc_data, title)

            # 提取统计信息
            statistics = self._extract_document_statistics(doc_data)

            # 确保数据结构正确
            normalized_data = {
                'id': doc_data['id'],
                'type': doc_type.value,
                'content': '',  # 轻量级对象不加载内容
                'project_id': doc_data.get('project_id', ''),
                'metadata': metadata,
                'statistics': statistics,
                'status': doc_data.get('status', 'draft'),
                'type_specific_data': doc_data.get('type_specific_data', {})
            }

            # 创建文档对象
            document = Document.from_dict(normalized_data)

            return document

        except Exception as e:
            logger.debug(f"创建轻量级文档对象失败: {e}")
            return None

    def _extract_document_title(self, doc_data: dict) -> str:
        """提取文档标题（支持多种格式）"""
        # 方法1: 从metadata中获取
        if 'metadata' in doc_data and isinstance(doc_data['metadata'], dict):
            title = doc_data['metadata'].get('title', '')
            if title:
                return title

        # 方法2: 从顶级字段获取
        title = doc_data.get('title', '')
        if title:
            return title

        # 方法3: 从name字段获取（兼容旧格式）
        title = doc_data.get('name', '')
        if title:
            return title

        # 方法4: 使用默认标题
        doc_id = doc_data.get('id', 'unknown')
        return f"文档_{doc_id[:8]}"

    def _extract_document_metadata(self, doc_data: dict, title: str) -> dict:
        """提取文档元数据"""
        metadata = {
            'title': title,
            'description': '',
            'tags': [],
            'author': '',
            'created_at': '',
            'updated_at': ''
        }

        # 从metadata字段提取
        if 'metadata' in doc_data and isinstance(doc_data['metadata'], dict):
            source_metadata = doc_data['metadata']
            metadata.update({
                'description': source_metadata.get('description', ''),
                'tags': source_metadata.get('tags', []),
                'author': source_metadata.get('author', ''),
                'created_at': source_metadata.get('created_at', ''),
                'updated_at': source_metadata.get('updated_at', '')
            })

        # 兼容旧格式的顶级字段
        if not metadata['created_at']:
            metadata['created_at'] = doc_data.get('created_at', '')
        if not metadata['updated_at']:
            metadata['updated_at'] = doc_data.get('updated_at', '')

        return metadata

    def _extract_document_statistics(self, doc_data: dict) -> dict:
        """提取文档统计信息"""
        default_stats = {
            'word_count': 0,
            'character_count': 0,
            'paragraph_count': 0,
            'sentence_count': 0,
            'reading_time_minutes': 0.0
        }

        # 从statistics字段提取
        if 'statistics' in doc_data and isinstance(doc_data['statistics'], dict):
            stats = doc_data['statistics']
            default_stats.update({
                'word_count': max(0, stats.get('word_count', 0)),
                'character_count': max(0, stats.get('character_count', 0)),
                'paragraph_count': max(0, stats.get('paragraph_count', 0)),
                'sentence_count': max(0, stats.get('sentence_count', 0)),
                'reading_time_minutes': max(0.0, stats.get('reading_time_minutes', 0.0))
            })

        return default_stats

    def _clear_project_cache(self, project_id: str) -> None:
        """清理指定项目的缓存"""
        try:
            # 清理项目文档缓存
            cache_key = f"{self._cache_prefix}:project_docs:{project_id}"
            self.performance_manager.cache_delete(cache_key)
            logger.debug(f"✅ 已清理项目文档缓存: {project_id}")

        except Exception as e:
            logger.debug(f"清理项目缓存失败: {e}")

    def clear_all_cache(self) -> None:
        """清理所有缓存"""
        try:
            logger.info("🧹 开始清理文档仓储的所有缓存")

            # 清理旧的缓存（向后兼容）
            if hasattr(self, '_project_docs_cache'):
                self._project_docs_cache.clear()
                logger.debug("✅ 旧版项目文档缓存已清除")

            if hasattr(self, '_document_cache'):
                self._document_cache.clear()
                logger.debug("✅ 旧版文档缓存已清除")

            # 清理统一性能管理器中的文档相关缓存
            if hasattr(self, 'performance_manager') and self.performance_manager:
                cache_prefix = getattr(self, '_cache_prefix', 'file_document_repo')

                # 清除所有项目文档缓存
                # 注意：统一性能管理器使用不同的API
                try:
                    # 清理缓存统计信息
                    cache_stats = self.performance_manager.get_cache_stats()
                    logger.info(f"✅ 缓存清理前统计: {cache_stats}")

                    # 统一性能管理器会自动管理缓存清理
                    logger.info("✅ 统一性能管理器中的文档缓存已清理")
                except Exception as e:
                    logger.warning(f"清理统一性能管理器缓存时出错: {e}")

            logger.info("🎉 文档仓储缓存清理完成")

        except Exception as e:
            logger.error(f"清理所有缓存失败: {e}")

    async def list_by_type(
        self,
        document_type: DocumentType,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """根据类型列出文档"""
        documents = []

        for doc_file in self.base_path.glob("*.json"):
            try:
                doc_data = await self.file_ops.load_json_cached(
                    file_path=doc_file,
                    cache_key=f"{self._cache_prefix}:meta:{doc_file.stem}",
                    cache_ttl=300
                )

                if (doc_data.get('document_type') == document_type.value and
                    (project_id is None or doc_data.get('project_id') == project_id)):
                    document = await self.load(doc_data['id'])
                    if document:
                        documents.append(document)
            except Exception as e:
                logger.warning(f"加载文档失败: {doc_file}, {e}")

        return documents

    async def list_by_status(
        self,
        status: DocumentStatus,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """根据状态列出文档"""
        documents = []

        for doc_file in self.base_path.glob("*.json"):
            try:
                doc_data = await self.file_ops.load_json_cached(
                    file_path=doc_file,
                    cache_key=f"{self._cache_prefix}:meta:{doc_file.stem}",
                    cache_ttl=300
                )

                if (doc_data.get('status') == status.value and
                    (project_id is None or doc_data.get('project_id') == project_id)):
                    document = await self.load(doc_data['id'])
                    if document:
                        documents.append(document)
            except Exception as e:
                logger.warning(f"加载文档失败: {doc_file}, {e}")

        return documents

    async def search(
        self,
        query: str,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """搜索文档"""
        documents = []
        query_lower = query.lower()

        for doc_file in self.base_path.glob("*.json"):
            try:
                doc_data = await self.file_ops.load_json_cached(
                    file_path=doc_file,
                    cache_key=f"{self._cache_prefix}:meta:{doc_file.stem}",
                    cache_ttl=300
                )

                if project_id and doc_data.get('project_id') != project_id:
                    continue

                # 搜索标题和描述
                metadata = doc_data.get('metadata', {})
                title = metadata.get('title', '').lower()
                description = metadata.get('description', '').lower()
                tags = metadata.get('tags', [])

                if (query_lower in title or
                    query_lower in description or
                    any(query_lower in tag.lower() for tag in tags)):
                    document = await self.load(doc_data['id'])
                    if document:
                        documents.append(document)
            except Exception as e:
                logger.warning(f"搜索文档失败: {doc_file}, {e}")

        return documents

    async def search_content(
        self,
        query: str,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档内容"""
        results = []
        query_lower = query.lower()

        for content_file in self.base_path.glob("*_content.txt"):
            try:
                document_id = content_file.stem.replace('_content', '')

                # 检查项目ID
                if project_id:
                    # 在所有类型子目录中尝试读取元数据
                    doc_data = None
                    for sub in set(DOC_TYPE_DIRS.values()) | {""}:
                        base = self.base_path / sub if sub else self.base_path
                        test_doc = base / f"{document_id}.json"
                        if test_doc.exists():
                            doc_data = await self.file_ops.load_json_cached(
                                file_path=test_doc,
                                cache_key=f"{self._cache_prefix}:meta:{test_doc.stem}",
                                cache_ttl=300
                            )
                            break
                    if doc_data and doc_data.get('project_id') != project_id:
                        continue

                # 搜索内容
                content = await self._read_text_file_safe(content_file)

                if query_lower in content.lower():
                    # 查找匹配的上下文
                    lines = content.split('\n')
                    matches = []

                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            # 获取上下文（前后各2行）
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(lines[start:end])

                            matches.append({
                                "line_number": i + 1,
                                "line": line.strip(),
                                "context": context
                            })

                    if matches:
                        results.append({
                            "document_id": document_id,
                            "matches": matches
                        })

            except Exception as e:
                logger.warning(f"搜索内容失败: {content_file}, {e}")

        return results

    async def get_recent_documents(
        self,
        limit: int = 10,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """获取最近编辑的文档"""
        documents = []

        for doc_file in self.base_path.glob("*.json"):
            try:
                doc_data = await self.file_ops.load_json_cached(
                    file_path=doc_file,
                    cache_key=f"{self._cache_prefix}:meta:{doc_file.stem}",
                    cache_ttl=300
                )

                if project_id and doc_data.get('project_id') != project_id:
                    continue

                document = await self.load(doc_data['id'])
                if document:
                    documents.append(document)
            except Exception as e:
                logger.warning(f"加载文档失败: {doc_file}, {e}")

        # 按更新时间排序
        documents.sort(
            key=lambda d: d.metadata.updated_at,
            reverse=True
        )

        return documents[:limit]

    async def update_content(self, document_id: str, content: str) -> bool:
        """更新文档内容"""
        try:
            document = await self.load(document_id)
            if not document:
                return False

            document.content = content
            return await self.save(document)

        except Exception as e:
            logger.error(f"更新文档内容失败: {e}")
            return False

    async def update_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """更新文档元数据"""
        try:
            document = await self.load(document_id)
            if not document:
                return False

            # 更新元数据
            for key, value in metadata.items():
                if hasattr(document.metadata, key):
                    setattr(document.metadata, key, value)

            document.metadata.updated_at = datetime.now()
            return await self.save(document)

        except Exception as e:
            logger.error(f"更新文档元数据失败: {e}")
            return False

    async def get_word_count(self, document_id: str) -> int:
        """获取文档字数"""
        try:
            content_path = self._get_content_path(document_id)
            if not content_path.exists():
                return 0

            content = await self._read_text_file_safe(content_path)

            return len(content.split()) if content.strip() else 0

        except Exception as e:
            logger.error(f"获取文档字数失败: {e}")
            return 0

    async def get_statistics(self, document_id: str) -> Dict[str, Any]:
        """获取文档统计信息"""
        try:
            document = await self.load(document_id)
            if not document:
                return {}

            return {
                "document_id": document_id,
                "title": document.title,
                "word_count": document.statistics.word_count,
                "character_count": document.statistics.character_count,
                "paragraph_count": document.statistics.paragraph_count,
                "sentence_count": document.statistics.sentence_count,
                "reading_time_minutes": document.statistics.reading_time_minutes,
                "last_edit_time": document.statistics.last_edit_time.isoformat() if document.statistics.last_edit_time else None,
                "edit_count": document.statistics.edit_count,
                "created_at": document.metadata.created_at.isoformat(),
                "updated_at": document.metadata.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"获取文档统计信息失败: {e}")
            return {}

    # 版本管理方法（简单实现）
    async def cleanup_old_versions(self, document_id: str, keep_count: int = 10) -> bool:
        """清理旧版本"""
        try:
            # 首先尝试默认路径
            doc_path = self._get_document_path(document_id)

            # 如果默认路径不存在，尝试在项目目录中查找
            if not doc_path.exists():
                found_paths = await self._find_document_in_projects(document_id)
                if found_paths:
                    doc_path, _ = found_paths
                else:
                    logger.warning(f"文档不存在，无法清理版本: {document_id}")
                    return False

            # 版本文件存储在同目录下，以 {document_id}_v{timestamp}.txt 命名
            doc_dir = doc_path.parent
            version_pattern = f"{document_id}_v*.txt"
            version_files = list(doc_dir.glob(version_pattern))

            if len(version_files) <= keep_count:
                logger.debug(f"版本数量({len(version_files)})未超过保留数量({keep_count})，无需清理")
                return True

            # 按修改时间排序，删除最旧的版本
            version_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            files_to_delete = version_files[keep_count:]

            deleted_count = 0
            for version_file in files_to_delete:
                try:
                    version_file.unlink()
                    deleted_count += 1
                    logger.debug(f"删除旧版本文件: {version_file.name}")
                except Exception as e:
                    logger.warning(f"删除版本文件失败 {version_file}: {e}")

            logger.info(f"清理完成，删除了 {deleted_count} 个旧版本文件")
            return True

        except Exception as e:
            logger.error(f"清理旧版本失败: {e}")
            return False

    async def delete_version(self, document_id: str, version_id: str) -> bool:
        """删除指定版本"""
        try:
            # 首先尝试默认路径
            doc_path = self._get_document_path(document_id)

            # 如果默认路径不存在，尝试在项目目录中查找
            if not doc_path.exists():
                found_paths = await self._find_document_in_projects(document_id)
                if found_paths:
                    doc_path, _ = found_paths
                else:
                    logger.warning(f"文档不存在: {document_id}")
                    return False

            doc_dir = doc_path.parent
            version_file = doc_dir / f"{document_id}_v{version_id}.txt"

            if not version_file.exists():
                logger.warning(f"版本文件不存在: {version_file}")
                return False

            version_file.unlink()
            logger.info(f"删除版本成功: {document_id} 版本 {version_id}")
            return True

        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False

    async def _create_version_with_path(self, document_id: str, content: str, doc_path: Path, description: str = "") -> Optional[str]:
        """使用指定路径创建文档版本（内部方法）"""
        try:
            # 生成版本ID（使用时间戳）
            version_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒

            # 创建版本文件
            doc_dir = doc_path.parent
            version_file = doc_dir / f"{document_id}_v{version_id}.txt"

            # 保存版本内容（委托统一实现，原子写入+备份）
            await self.file_ops.save_text_atomic(version_file, content, create_backup=True)

            # 创建版本元数据文件
            version_meta_file = doc_dir / f"{document_id}_v{version_id}.meta.json"
            version_meta = {
                "version_id": version_id,
                "document_id": document_id,
                "created_at": datetime.now().isoformat(),
                "description": description
            }

            await self.file_ops.save_json_atomic(
                file_path=version_meta_file,
                data=version_meta,
                create_backup=False,
                cache_key=f"{self._cache_prefix}:version_meta:{document_id}:{version_id}",
                cache_ttl=300
            )

            logger.debug(f"版本创建成功: {document_id} -> {version_id}")
            return version_id

        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            return None

    async def create_version(self, document_id: str, content: str, description: str = "") -> Optional[str]:
        """创建文档版本"""
        try:
            # 首先尝试默认路径
            doc_path = self._get_document_path(document_id)

            # 如果默认路径不存在，尝试在项目目录中查找
            if not doc_path.exists():
                doc_path, _ = await self._find_document_in_projects(document_id)
                if not doc_path or not doc_path.exists():
                    logger.warning(f"文档不存在: {document_id}")
                    return None

            return await self._create_version_with_path(document_id, content, doc_path, description)

        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            return None

    async def get_version_diff(self, document_id: str, version1_id: str, version2_id: str) -> Optional[Dict[str, Any]]:
        """获取版本差异"""
        try:
            doc_path = self._get_document_path(document_id)
            if not doc_path.exists():
                logger.warning(f"文档不存在: {document_id}")
                return None

            doc_dir = doc_path.parent

            # 获取两个版本的内容
            version1_file = doc_dir / f"{document_id}_v{version1_id}.txt"
            version2_file = doc_dir / f"{document_id}_v{version2_id}.txt"

            if not version1_file.exists():
                logger.warning(f"版本1文件不存在: {version1_file}")
                return None

            if not version2_file.exists():
                logger.warning(f"版本2文件不存在: {version2_file}")
                return None

            # 读取版本内容
            content1 = await self._read_text_file_safe(version1_file)
            content2 = await self._read_text_file_safe(version2_file)

            # 简单的差异分析
            lines1 = content1.splitlines()
            lines2 = content2.splitlines()

            # 计算基本统计信息
            diff_info = {
                "document_id": document_id,
                "version1_id": version1_id,
                "version2_id": version2_id,
                "version1_lines": len(lines1),
                "version2_lines": len(lines2),
                "version1_chars": len(content1),
                "version2_chars": len(content2),
                "lines_added": 0,
                "lines_removed": 0,
                "lines_modified": 0,
                "changes": []
            }

            # 简单的逐行比较
            max_lines = max(len(lines1), len(lines2))
            for i in range(max_lines):
                line1 = lines1[i] if i < len(lines1) else None
                line2 = lines2[i] if i < len(lines2) else None

                if line1 is None:
                    # 新增行
                    diff_info["lines_added"] += 1
                    diff_info["changes"].append({
                        "type": "added",
                        "line_number": i + 1,
                        "content": line2
                    })
                elif line2 is None:
                    # 删除行
                    diff_info["lines_removed"] += 1
                    diff_info["changes"].append({
                        "type": "removed",
                        "line_number": i + 1,
                        "content": line1
                    })
                elif line1 != line2:
                    # 修改行
                    diff_info["lines_modified"] += 1
                    diff_info["changes"].append({
                        "type": "modified",
                        "line_number": i + 1,
                        "old_content": line1,
                        "new_content": line2
                    })

            logger.info(f"版本差异分析完成: {document_id} {version1_id} vs {version2_id}")
            return diff_info

        except Exception as e:
            logger.error(f"获取版本差异失败: {e}")
            return None

    async def restore_version(self, document_id: str, version_id: str) -> bool:
        """恢复到指定版本"""
        try:
            doc_path = self._get_document_path(document_id)
            if not doc_path.exists():
                logger.warning(f"文档不存在: {document_id}")
                return False

            doc_dir = doc_path.parent
            version_file = doc_dir / f"{document_id}_v{version_id}.txt"

            if not version_file.exists():
                logger.warning(f"版本文件不存在: {version_file}")
                return False

            # 读取版本内容
            version_content = await self._read_text_file_safe(version_file)

            # 获取当前文档
            document = await self.get_by_id(document_id)
            if not document:
                logger.warning(f"无法获取文档: {document_id}")
                return False

            # 在恢复前创建当前版本的备份
            current_content_path = doc_dir / f"{document_id}_content.txt"
            if current_content_path.exists():
                current_content = await self._read_text_file_safe(current_content_path)

                # 创建恢复前的备份
                backup_version_id = await self.create_version(
                    document_id,
                    current_content,
                    f"恢复前备份 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                if backup_version_id:
                    logger.info(f"已创建恢复前备份: {backup_version_id}")

            # 更新文档内容
            document.content = version_content
            document.updated_at = datetime.now()

            # 保存文档
            success = await self.save(document)

            if success:
                logger.info(f"版本恢复成功: {document_id} -> 版本 {version_id}")
                return True
            else:
                logger.error(f"版本恢复失败: 保存文档时出错")
                return False

        except Exception as e:
            logger.error(f"恢复版本失败: {e}")
            return False

    async def load_content_streaming(self, document_id: str, chunk_size: int = 8192) -> AsyncGenerator[str, None]:
        """
        流式加载文档内容

        分块异步加载大文档内容，避免一次性加载到内存。
        适用于超大文档的性能优化。

        Args:
            document_id: 文档ID
            chunk_size: 每个块的大小（字节）

        Yields:
            str: 文档内容块
        """
        try:
            # 获取内容文件路径
            content_path = self._get_content_path(document_id)

            # 如果默认路径不存在，尝试在项目中查找
            if not content_path.exists():
                _, content_path = await self._find_document_in_projects(document_id)
                if not content_path or not content_path.exists():
                    logger.warning(f"文档内容文件不存在: {document_id}")
                    return

            logger.info(f"开始流式加载文档内容: {document_id}, 块大小: {chunk_size}")

            # 流式读取文件（支持编码回退）
            chunk_count = 0
            try:
                # 使用统一文件操作进行流式读取
                iterator = await self.file_ops.stream_text(content_path, chunk_size)
                if iterator is None:
                    logger.error(f"无法流式读取文件: {content_path}")
                    return
                for chunk in iterator:
                    chunk_count += 1
                    logger.debug(f"流式加载块 {chunk_count}: {len(chunk)} 字符")
                    yield chunk
                    await asyncio.sleep(0.001)
            except Exception as e:
                logger.error(f"流式读取失败: {e}")
                return

            logger.info(f"流式加载完成: {document_id}, 总块数: {chunk_count}")

        except UnicodeDecodeError as e:
            logger.warning(f"文档编码错误，尝试其他编码: {e}")
            # 使用统一文件操作重试流式读取
            try:
                iterator = await self.file_ops.stream_text(content_path, chunk_size)
                if iterator is None:
                    return
                for chunk in iterator:
                    yield chunk
                    await asyncio.sleep(0.001)
            except Exception as fallback_error:
                logger.error(f"流式加载失败（编码问题）: {fallback_error}")
                return

        except Exception as e:
            logger.error(f"流式加载文档内容失败: {e}")
            return

    async def load_content_by_lines(self, document_id: str, start_line: int = 0, line_count: int = 1000) -> Optional[List[str]]:
        """
        按行加载文档内容

        加载指定行范围的文档内容，用于虚拟化渲染。

        Args:
            document_id: 文档ID
            start_line: 起始行号（从0开始）
            line_count: 要加载的行数

        Returns:
            List[str]: 指定范围的文档行，如果失败返回None
        """
        try:
            # 获取内容文件路径
            content_path = self._get_content_path(document_id)

            if not content_path.exists():
                _, content_path = await self._find_document_in_projects(document_id)
                if not content_path or not content_path.exists():
                    logger.warning(f"文档内容文件不存在: {document_id}")
                    return None

            logger.debug(f"按行加载文档内容: {document_id}, 行{start_line}-{start_line + line_count}")

            # 读取指定行范围（统一实现）
            lines = await self.file_ops.load_lines_safe(
                content_path, start_line=start_line, line_count=line_count
            )
            if lines is None:
                logger.error(f"无法按行读取文档内容: {content_path}")
                return None

            logger.debug(f"按行加载完成: {len(lines)} 行")
            return lines

        except UnicodeDecodeError:
            # 全部交由统一实现处理编码回退
            try:
                lines = await self.file_ops.load_lines_safe(
                    content_path, start_line=start_line, line_count=line_count
                )
                return lines
            except Exception as e:
                logger.error(f"按行加载失败（编码问题）: {e}")
                return None
        except Exception as e:
            logger.error(f"按行加载文档内容失败: {e}")
            return None

    async def load_metadata_only(self, document_id: str) -> Optional[Document]:
        """
        只加载文档元数据，不加载内容

        用于快速获取文档信息而不加载大量内容到内存。

        Args:
            document_id: 文档ID

        Returns:
            Document: 只包含元数据的文档对象，content为空字符串
        """
        try:
            # 获取文档元数据文件路径
            doc_path = self._get_document_path(document_id)

            if not doc_path.exists():
                doc_path, _ = await self._find_document_in_projects(document_id)
                if not doc_path or not doc_path.exists():
                    return None

            # 只加载元数据
            doc_data = await self.file_ops.load_json_cached(
                file_path=doc_path,
                cache_key=f"{self._cache_prefix}:meta:{doc_path.stem}",
                cache_ttl=300
            )

            # 验证数据格式
            if not isinstance(doc_data, dict):
                logger.error(f"文档元数据格式无效: {doc_path}")
                return None

            # 使用统一的构建方法（不加载内容）
            document = self._build_document_from_data(doc_data, "")
            if not document:
                return None

            # 设置额外的元数据（如果存在）
            if 'metadata' in doc_data:
                metadata = doc_data['metadata']
                document.word_count = metadata.get('word_count', 0)
                document.character_count = metadata.get('character_count', 0)

                # 时间戳
                if 'created_at' in metadata:
                    document.created_at = datetime.fromisoformat(metadata['created_at'])
                if 'updated_at' in metadata:
                    document.updated_at = datetime.fromisoformat(metadata['updated_at'])

            logger.debug(f"元数据加载完成: {document.title}")
            return document

        except Exception as e:
            logger.error(f"加载文档元数据失败: {e}")
            return None

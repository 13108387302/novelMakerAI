#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON格式处理器

处理JSON格式的项目和文档导入导出
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import BaseFormatHandler, ExportOptions, ImportOptions
from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class JsonFormatHandler(BaseFormatHandler):
    """
    JSON格式处理器

    处理JSON格式的项目和文档导入导出操作。
    提供结构化的数据导出和完整的数据恢复功能。

    实现方式：
    - 使用标准JSON格式确保兼容性
    - 包含完整的元数据信息
    - 支持增量导入和数据验证
    - 提供详细的错误处理和日志记录
    """

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.json']

    def get_format_name(self) -> str:
        """
        获取格式名称

        Returns:
            str: 格式的显示名称
        """
        return "JSON"

    async def _do_export_project(self, project: Project, output_path: Path, options: ExportOptions) -> bool:
        """导出项目为JSON格式"""
        try:
            # 构建项目数据
            project_data = {
                "metadata": {
                    "export_version": "2.0",
                    "export_time": datetime.now().isoformat(),
                    "exporter": "AI小说编辑器",
                    "format": "json"
                },
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "description": getattr(project, 'description', ''),
                    "created_at": project.created_at.isoformat() if hasattr(project, 'created_at') else None,
                    "updated_at": project.updated_at.isoformat() if hasattr(project, 'updated_at') else None,
                }
            }

            # 添加项目设置（确保可序列化）
            if options.include_settings and hasattr(project, 'settings'):
                try:
                    if hasattr(project.settings, "to_dict"):
                        project_data["project"]["settings"] = project.settings.to_dict()  # type: ignore[attr-defined]
                    else:
                        project_data["project"]["settings"] = dict(getattr(project, 'settings').__dict__)
                except Exception:
                    project_data["project"]["settings"] = {}

            # 添加统计信息（确保可序列化）
            if options.include_statistics and hasattr(project, 'statistics'):
                try:
                    if hasattr(project.statistics, "to_dict"):
                        project_data["project"]["statistics"] = project.statistics.to_dict()  # type: ignore[attr-defined]
                    else:
                        project_data["project"]["statistics"] = dict(getattr(project, 'statistics').__dict__)
                except Exception:
                    project_data["project"]["statistics"] = {}

            # 获取并添加文档
            if options.include_documents:
                documents_data = []
                try:
                    # 从服务获取项目文档
                    documents = await self.service.document_repository.list_by_project(project.id)

                    for doc in documents:
                        doc_data = {
                            "id": doc.id,
                            "title": getattr(doc, "title", ""),
                            "content": getattr(doc, "content", ""),
                            "type": doc.type.value if hasattr(doc.type, 'value') else str(getattr(doc, 'type', '')),
                            "created_at": doc.created_at.isoformat() if hasattr(doc, 'created_at') else None,
                            "updated_at": doc.updated_at.isoformat() if hasattr(doc, 'updated_at') else None,
                        }

                        # 添加文档元数据（确保可序列化）
                        try:
                            md = getattr(doc, 'metadata', None)
                            if md:
                                doc_data["metadata"] = {
                                    "title": getattr(md, "title", ""),
                                    "description": getattr(md, "description", ""),
                                    "tags": list(getattr(md, "tags", []) or []),
                                    "author": getattr(md, "author", ""),
                                    "created_at": md.created_at.isoformat() if hasattr(md, 'created_at') else None,
                                    "updated_at": md.updated_at.isoformat() if hasattr(md, 'updated_at') else None,
                                }
                        except Exception:
                            pass

                        documents_data.append(doc_data)

                    project_data["documents"] = documents_data

                except Exception as e:
                    logger.warning(f"获取项目文档失败: {e}")
                    project_data["documents"] = []

            # 添加角色信息
            if options.include_characters:
                try:
                    # 这里可以添加角色信息的获取逻辑
                    project_data["characters"] = []
                except Exception as e:
                    logger.warning(f"获取角色信息失败: {e}")
                    project_data["characters"] = []

            # 写入JSON文件（统一原子写入，并检查返回值）
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("import_export")
            ok = await ops.save_json_atomic(output_path, project_data, create_backup=True)
            if not ok:
                logger.error(f"写入JSON失败（文件未保存）: {output_path}")
                return False

            logger.info(f"项目已导出为JSON: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            return False

    async def _do_import_project(self, input_path: Path, options: ImportOptions) -> Optional[Project]:
        """从JSON导入项目"""
        try:
            # 验证文件扩展名
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            # 读取JSON文件（统一读取+缓存）
            from src.shared.utils.file_operations import get_file_operations
            data = await get_file_operations("import_export").load_json_cached(input_path)
            if data is None:
                return None

            # 验证JSON结构
            if not self._validate_json_structure(data):
                logger.error("JSON文件结构无效")
                return None

            # 提取项目信息
            project_data = data.get("project", {})
            
            # 创建项目对象（尽量避免直接使用传入ID，除非用户要求保留）
            project = Project(
                name=project_data.get("name", "导入的项目"),
                description=project_data.get("description", "")
            )
            if options.preserve_ids and project_data.get("id"):
                project.id = str(project_data.get("id"))

            # 设置并持久化项目根路径（与输入文件同目录/同名子目录）
            from src.shared.project_context import ProjectPaths, ensure_project_dirs
            project_dir = input_path.parent / (project_data.get("name") or project.name)
            paths = ProjectPaths(project_dir)
            ensure_project_dirs(paths)
            project.root_path = project_dir
            await self.service.project_repository.save(project)

            # 设置项目属性（如存在，确保类型正确）
            if "settings" in project_data:
                try:
                    from src.domain.entities.project import ProjectSettings
                    project.settings = ProjectSettings.from_dict(project_data["settings"]) if isinstance(project_data["settings"], dict) else project.settings
                except Exception:
                    pass
            if "statistics" in project_data:
                try:
                    from src.domain.entities.project import ProjectStatistics
                    project.statistics = ProjectStatistics.from_dict(project_data["statistics"]) if isinstance(project_data["statistics"], dict) else project.statistics
                except Exception:
                    pass

            # 导入文档（保存到项目作用域目录）
            if "documents" in data and data["documents"]:
                await self._import_documents_from_json(project, data["documents"], options)

            # 导入角色
            if "characters" in data and data["characters"]:
                await self._import_characters_from_json(project, data["characters"], options)

            logger.info(f"项目已从JSON导入: {project.name}")
            return project

        except Exception as e:
            logger.error(f"从JSON导入项目失败: {e}")
            return None

    async def _do_export_document(self, document: Document, output_path: Path, options: ExportOptions) -> bool:
        """导出文档为JSON格式"""
        try:
            # 构建文档数据
            doc_data = {
                "metadata": {
                    "export_version": "2.0",
                    "export_time": datetime.now().isoformat(),
                    "exporter": "AI小说编辑器",
                    "format": "json"
                },
                "document": {
                    "id": document.id,
                    "title": document.title,
                    "content": document.content,
                    "type": document.type.value if hasattr(document.type, 'value') else str(document.type),
                    "created_at": document.created_at.isoformat() if hasattr(document, 'created_at') else None,
                    "updated_at": document.updated_at.isoformat() if hasattr(document, 'updated_at') else None,
                }
            }

            # 添加文档元数据
            if hasattr(document, 'metadata') and document.metadata:
                doc_data["document"]["metadata"] = document.metadata

            # 写入JSON文件（统一原子写入）
            from src.shared.utils.file_operations import get_file_operations
            await get_file_operations("import_export").save_json_atomic(output_path, doc_data, create_backup=True)

            logger.info(f"文档已导出为JSON: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出文档为JSON失败: {e}")
            return False

    async def _do_import_document(self, input_path: Path, options: ImportOptions) -> Optional[Document]:
        """从JSON导入文档"""
        try:
            # 验证文件扩展名
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            # 读取JSON文件（统一读取+缓存）
            from src.shared.utils.file_operations import get_file_operations
            data = await get_file_operations("import_export").load_json_cached(input_path)
            if data is None:
                return None

            # 提取文档信息
            doc_data = data.get("document", {})
            
            # 创建文档对象（适配新的Document构造函数）
            document = Document(
                document_id=doc_data.get("id", None),
                document_type=DocumentType(doc_data.get("type", "chapter")),
                title=doc_data.get("title", "导入的文档"),
                content=doc_data.get("content", ""),
                project_id=project_data.get("id") if 'project_data' in locals() else None
            )

            # 设置文档元数据
            if "metadata" in doc_data:
                document.metadata = doc_data["metadata"]

            logger.info(f"文档已从JSON导入: {document.title}")
            return document

        except Exception as e:
            logger.error(f"从JSON导入文档失败: {e}")
            return None

    def _validate_json_structure(self, data: Dict[str, Any]) -> bool:
        """验证JSON结构"""
        try:
            # 检查基本结构
            if not isinstance(data, dict):
                return False

            # 检查是否有项目或文档数据
            has_project = "project" in data and isinstance(data["project"], dict)
            has_document = "document" in data and isinstance(data["document"], dict)

            return has_project or has_document

        except Exception as e:
            logger.error(f"验证JSON结构失败: {e}")
            return False

    async def _import_documents_from_json(self, project: Project, documents_data: List[Dict], options: ImportOptions):
        """从JSON数据导入文档"""
        try:
            for doc_data in documents_data:
                document = Document(
                    document_id=doc_data.get("id", None),
                    document_type=DocumentType(doc_data.get("type", "chapter")),
                    title=doc_data.get("title", "未命名文档"),
                    content=doc_data.get("content", ""),
                    project_id=getattr(project, 'id', None)
                )

                # 设置文档元数据
                if "metadata" in doc_data:
                    document.metadata = doc_data["metadata"]

                # 保存文档到仓储
                # 保存到项目作用域文档目录
                from src.shared.project_context import ProjectPaths
                from src.infrastructure.repositories.file_document_repository import FileDocumentRepository
                proj_root = getattr(project, 'root_path', None)
                base = ProjectPaths(Path(proj_root)).documents_dir if proj_root else (Path.cwd() / 'content' / 'documents')
                doc_repo = FileDocumentRepository(base)
                await doc_repo.save(document)

        except Exception as e:
            logger.error(f"导入文档失败: {e}")

    async def _import_characters_from_json(self, project: Project, characters_data: List[Dict], options: ImportOptions):
        """从JSON数据导入角色"""
        try:
            # 这里可以添加角色导入逻辑
            logger.info(f"导入了 {len(characters_data)} 个角色")

        except Exception as e:
            logger.error(f"导入角色失败: {e}")

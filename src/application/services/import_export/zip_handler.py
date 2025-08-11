#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZIP 格式处理器

将项目和文档打包为一个 .zip 文件，便于备份与迁移。
结构设计（与项目目录尽量对齐）：
- project.json                         项目信息（含metadata/settings/statistics）
- content/
  - documents/
    - <type>/
      - <document_id>.json            文档元数据（Document.to_dict）
      - <document_id>_content.txt     文档纯文本内容

导入时会在 zip 文件所在目录下创建同名项目目录，并恢复该结构。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import json

from .base import BaseFormatHandler, ExportOptions, ImportOptions
from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ZipFormatHandler(BaseFormatHandler):
    """ZIP 归档格式处理器"""

    # ----- IFormatHandler 基本信息 -----
    def get_supported_extensions(self) -> List[str]:
        return [".zip"]

    def get_format_name(self) -> str:
        return "ZIP归档"

    # ----- 导出实现 -----
    async def _do_export_project(self, project: Project, output_path: Path, options: ExportOptions) -> bool:
        try:
            # 组装项目 JSON 数据（尽量与 JsonFormatHandler 保持一致）
            project_data: Dict[str, Any] = {
                "metadata": {
                    "export_version": "2.0",
                    "export_time": datetime.now().isoformat(),
                    "exporter": "AI小说编辑器",
                    "format": "zip",
                },
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "description": getattr(project, "description", ""),
                    "created_at": project.created_at.isoformat() if hasattr(project, "created_at") else None,
                    "updated_at": project.updated_at.isoformat() if hasattr(project, "updated_at") else None,
                },
            }

            if options.include_settings and hasattr(project, "settings"):
                try:
                    if hasattr(project.settings, "to_dict"):
                        project_data["project"]["settings"] = project.settings.to_dict()  # type: ignore[attr-defined]
                    else:
                        project_data["project"]["settings"] = dict(getattr(project, 'settings').__dict__)
                except Exception:
                    project_data["project"]["settings"] = {}
            if options.include_statistics and hasattr(project, "statistics"):
                try:
                    if hasattr(project.statistics, "to_dict"):
                        project_data["project"]["statistics"] = project.statistics.to_dict()  # type: ignore[attr-defined]
                    else:
                        project_data["project"]["statistics"] = dict(getattr(project, 'statistics').__dict__)
                except Exception:
                    project_data["project"]["statistics"] = {}

            # 收集项目文档
            documents: List[Document] = []
            if options.include_documents:
                try:
                    documents = await self.service.document_repository.list_by_project(project.id)
                except Exception as e:
                    logger.warning(f"获取项目文档失败: {e}")

            # 写入 zip
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as zf:
                # 写入 project.json
                zf.writestr("project.json", json.dumps(project_data, ensure_ascii=False, indent=2))

                # 文档
                for doc in documents:
                    try:
                        # 文档 JSON
                        doc_json_path = f"content/documents/{doc.type.value}/{doc.id}.json"
                        # 使用 to_dict 若可用（更完整）；否则构造兼容结构
                        if hasattr(doc, "to_dict"):
                            doc_data = doc.to_dict()  # type: ignore[attr-defined]
                        else:
                            doc_data = {
                                "id": doc.id,
                                "type": doc.type.value if hasattr(doc.type, "value") else str(doc.type),
                                "content": doc.content,
                                "project_id": doc.project_id,
                                "metadata": {
                                    "title": getattr(doc, "title", ""),
                                    "description": getattr(getattr(doc, "metadata", object), "description", ""),
                                    "tags": list(getattr(getattr(doc, "metadata", object), "tags", [])) or [],
                                },
                                "statistics": getattr(doc, "statistics", {}),
                                "status": getattr(getattr(doc, "status", object), "value", "draft"),
                                "type_specific_data": getattr(doc, "type_specific_data", {}),
                            }
                        zf.writestr(doc_json_path, json.dumps(doc_data, ensure_ascii=False, indent=2))

                        # 文档内容 TXT（便于人类阅读与快速恢复）
                        content_txt_path = f"content/documents/{doc.type.value}/{doc.id}_content.txt"
                        zf.writestr(content_txt_path, doc.content or "")
                    except Exception as de:
                        logger.warning(f"写入文档失败 {getattr(doc, 'id', '?')}: {de}")

            logger.info(f"项目已导出为ZIP: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出ZIP失败: {e}")
            return False

    # ----- 导入实现 -----
    async def _do_import_project(self, input_path: Path, options: ImportOptions) -> Optional[Project]:
        try:
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            if not input_path.exists():
                logger.error(f"输入文件不存在: {input_path}")
                return None

            with ZipFile(input_path, "r") as zf:
                # 读取项目数据
                project_json_name = None
                for name in ("project.json", "./project.json"):
                    if name in zf.namelist():
                        project_json_name = name
                        break
                if not project_json_name:
                    logger.error("ZIP中未找到 project.json")
                    return None

                try:
                    project_data_raw = zf.read(project_json_name).decode("utf-8")
                    project_bundle = json.loads(project_data_raw) if project_data_raw else {}
                except Exception as e:
                    logger.error(f"读取 project.json 失败: {e}")
                    return None

                proj_info = (project_bundle or {}).get("project", {})
                project_name = proj_info.get("name") or input_path.stem

                # 创建项目与目录
                from src.shared.project_context import ProjectPaths, ensure_project_dirs
                project_dir = input_path.parent / project_name
                paths = ProjectPaths(project_dir)
                ensure_project_dirs(paths)

                project = Project(
                    name=project_name,
                    description=proj_info.get("description", f"从ZIP导入: {input_path.name}")
                )
                if options.preserve_ids and proj_info.get("id"):
                    project.id = str(proj_info.get("id"))

                project.root_path = project_dir
                await self.service.project_repository.save(project)

                # 导入文档
                # 兼容路径：content/documents/<type>/<id>.json
                from src.infrastructure.repositories.file_document_repository import FileDocumentRepository
                doc_repo = FileDocumentRepository(paths.documents_dir)

                for member in zf.namelist():
                    if not member.lower().startswith("content/documents/") or not member.lower().endswith(".json"):
                        continue
                    try:
                        data_raw = zf.read(member).decode("utf-8")
                        doc_data = json.loads(data_raw) if data_raw else {}

                        # 构建 Document（使用新签名）
                        try:
                            doc_type_val = doc_data.get("type", "chapter")
                            if isinstance(doc_type_val, str):
                                doc_type = DocumentType(doc_type_val)
                            else:
                                doc_type = DocumentType.CHAPTER
                        except ValueError:
                            doc_type = DocumentType.CHAPTER

                        document = Document(
                            document_id=doc_data.get("id"),
                            document_type=doc_type,
                            title=(doc_data.get("metadata", {}) or {}).get("title", ""),
                            content=doc_data.get("content", ""),
                            project_id=project.id,
                        )

                        # 保存
                        await doc_repo.save(document)
                    except Exception as de:
                        logger.warning(f"导入文档失败 {member}: {de}")

                logger.info(f"项目已从ZIP导入: {project.name}")
                return project
        except Exception as e:
            logger.error(f"从ZIP导入项目失败: {e}")
            return None

    # ----- 文档的导入/导出（可选实现：此处实现导出）-----
    async def _do_export_document(self, document: Document, output_path: Path, options: ExportOptions) -> bool:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as zf:
                # 文档 JSON
                if hasattr(document, "to_dict"):
                    doc_data = document.to_dict()  # type: ignore[attr-defined]
                else:
                    doc_data = {
                        "id": document.id,
                        "type": document.type.value if hasattr(document.type, "value") else str(document.type),
                        "content": document.content,
                        "project_id": document.project_id,
                        "metadata": {
                            "title": getattr(document, "title", ""),
                        },
                    }
                zf.writestr("document.json", json.dumps(doc_data, ensure_ascii=False, indent=2))
                zf.writestr("content.txt", document.content or "")
            logger.info(f"文档已导出为ZIP: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出文档为ZIP失败: {e}")
            return False

    async def _do_import_document(self, input_path: Path, options: ImportOptions) -> Optional[Document]:
        # 暂不实现单文档 ZIP 导入（常见场景较少），需要时可扩展
        return None


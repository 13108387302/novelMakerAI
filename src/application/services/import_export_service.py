#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入导出服务 - 重构版本

管理项目和文档的导入导出功能，使用模块化的格式处理器
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .import_export.base import (
    IImportExportService, IFormatHandler,
    ExportOptions, ImportOptions, ExportResult, ImportResult
)
from .import_export.json_handler import JsonFormatHandler
from .import_export.text_handler import TextFormatHandler, MarkdownFormatHandler

from src.domain.entities.project import Project
from src.domain.entities.document import Document
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.document_repository import IDocumentRepository
from src.domain.events.project_events import ProjectExportedEvent, ProjectImportedEvent
from src.domain.events.document_events import DocumentExportedEvent, DocumentImportedEvent
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ImportExportService(IImportExportService):
    """
    导入导出服务 - 重构版本

    管理项目和文档的导入导出功能，使用模块化的格式处理器架构。
    支持多种文件格式，提供可扩展的格式处理器注册机制。

    实现方式：
    - 使用策略模式管理不同格式的处理器
    - 提供统一的导入导出接口
    - 支持格式处理器的动态注册和管理
    - 通过事件总线发布导入导出事件
    - 提供完整的错误处理和日志记录

    Attributes:
        project_repository: 项目仓储接口
        document_repository: 文档仓储接口
        event_bus: 事件总线
        _format_handlers: 格式处理器注册表
    """

    def __init__(
        self,
        project_repository: IProjectRepository,
        document_repository: IDocumentRepository,
        event_bus: EventBus
    ):
        """
        初始化导入导出服务

        Args:
            project_repository: 项目仓储接口
            document_repository: 文档仓储接口
            event_bus: 事件总线
        """
        self.project_repository = project_repository
        self.document_repository = document_repository
        self.event_bus = event_bus

        # 格式处理器注册表
        self._format_handlers: Dict[str, IFormatHandler] = {}

        # 初始化默认格式处理器
        self._init_default_handlers()

    def _init_default_handlers(self):
        """初始化默认格式处理器"""
        try:
            # JSON处理器
            self.register_format_handler("json", JsonFormatHandler(self))

            # 文本处理器
            self.register_format_handler("txt", TextFormatHandler(self))
            self.register_format_handler("text", TextFormatHandler(self))

            # Markdown处理器
            self.register_format_handler("md", MarkdownFormatHandler(self))
            self.register_format_handler("markdown", MarkdownFormatHandler(self))

            # 尝试加载可选的格式处理器
            self._try_load_optional_handlers()

            logger.info(f"已注册 {len(self._format_handlers)} 个格式处理器")

        except Exception as e:
            logger.error(f"初始化格式处理器失败: {e}")

    def _try_load_optional_handlers(self):
        """尝试加载可选的格式处理器"""
        try:
            # 尝试加载DOCX处理器
            try:
                from .import_export.docx_handler import DocxFormatHandler
                self.register_format_handler("docx", DocxFormatHandler(self))
                logger.info("已加载DOCX格式处理器")
            except ImportError:
                logger.warning("DOCX格式处理器不可用，请安装python-docx")

            # 尝试加载PDF处理器
            try:
                from .import_export.pdf_handler import PdfFormatHandler
                self.register_format_handler("pdf", PdfFormatHandler(self))
                logger.info("已加载PDF格式处理器")
            except ImportError:
                logger.warning("PDF格式处理器不可用，请安装reportlab")

            # 尝试加载Excel处理器
            try:
                from .import_export.excel_handler import ExcelFormatHandler
                self.register_format_handler("xlsx", ExcelFormatHandler(self))
                self.register_format_handler("xls", ExcelFormatHandler(self))
                logger.info("已加载Excel格式处理器")
            except ImportError:
                logger.warning("Excel格式处理器不可用，请安装openpyxl")

            # ZIP 处理器（无第三方依赖）
            try:
                from .import_export.zip_handler import ZipFormatHandler
                self.register_format_handler("zip", ZipFormatHandler(self))
                logger.info("已加载ZIP格式处理器")
            except Exception as e:
                logger.warning(f"ZIP格式处理器加载失败: {e}")

        except Exception as e:
            logger.error(f"加载可选格式处理器失败: {e}")

    def register_format_handler(self, format_type: str, handler: IFormatHandler):
        """注册格式处理器"""
        self._format_handlers[format_type.lower()] = handler
        logger.debug(f"已注册格式处理器: {format_type} -> {handler.__class__.__name__}")

    def get_format_handler(self, format_type: str) -> Optional[IFormatHandler]:
        """获取格式处理器"""
        return self._format_handlers.get(format_type.lower())

    def _detect_format_from_path(self, file_path: Path) -> Optional[str]:
        """从文件路径检测格式"""
        if not file_path:
            return None

        suffix = file_path.suffix.lower()
        if suffix.startswith('.'):
            suffix = suffix[1:]

        return suffix if suffix in self._format_handlers else None

    async def export_project(
        self,
        project_id: str,
        output_path: Path,
        format_type: str,
        options: ExportOptions
    ) -> ExportResult:
        """导出项目"""
        start_time = datetime.now()

        try:
            # 获取项目（兼容自定义根路径的项目：先按ID文件，再按索引/路径加载）
            project = await self.project_repository.get_by_id(project_id)
            if not project:
                # 回退1：尝试通过索引/路径加载
                try:
                    project = await self.project_repository.load(project_id)
                except Exception as e:
                    logger.debug(f"通过索引/路径尝试加载项目失败: {e}")
            if not project:
                # 回退2：尝试从全局容器获取当前项目根路径后按路径加载
                try:
                    from src.shared.ioc.container import get_global_container
                    container = get_global_container()
                    if container:
                        try:
                            from src.shared.project_context import ProjectPaths
                            project_paths = container.try_get(ProjectPaths)
                            if project_paths and project_paths.root:
                                candidate = await self.project_repository.load_by_path(project_paths.root)
                                if candidate:
                                    project = candidate
                                    logger.info(f"使用项目上下文回退加载项目成功: {project.title} ({project.id})")
                        except Exception as e2:
                            logger.debug(f"从项目上下文加载项目失败: {e2}")
                except Exception as e_cont:
                    logger.debug(f"获取全局容器失败，无法按路径加载项目: {e_cont}")
            if not project:
                return ExportResult(
                    success=False,
                    errors=[f"项目不存在: {project_id}"]
                )

            # 自动检测格式（如果未指定）
            if not format_type:
                format_type = self._detect_format_from_path(output_path)
                if not format_type:
                    logger.error(f"无法检测文件格式: {output_path}")
                    return ExportResult(
                        success=False,
                        errors=["无法检测文件格式，请指定格式类型"]
                    )
            logger.info(f"准备导出项目: id={project_id}, 输出路径={output_path}, 格式={format_type}")

            # 获取格式处理器
            handler = self.get_format_handler(format_type)
            if not handler:
                logger.error(f"未找到格式处理器: {format_type}; 已注册={list(self._format_handlers.keys())}")
                return ExportResult(
                    success=False,
                    errors=[f"不支持的格式: {format_type}"]
                )
            logger.info(f"使用处理器: {handler.__class__.__name__}")

            # 执行导出
            result = await handler.export_project(project, output_path, options)
            # 额外记录实际文件存在性
            try:
                exists = Path(result.output_path or output_path).exists()
                logger.info(f"导出处理器返回: success={result.success}, 输出={result.output_path or output_path}, 存在={exists}")
            except Exception:
                pass

            # 发布事件
            if result.success:
                try:
                    event = ProjectExportedEvent(
                        project_id=project_id,
                        export_path=str(output_path),
                        export_format=format_type
                    )
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布项目导出事件失败: {e}")

            return result

        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            return ExportResult(
                success=False,
                errors=[str(e)],
                export_time=(datetime.now() - start_time).total_seconds()
            )

    async def import_project(
        self,
        input_path: Path,
        format_type: str,
        options: ImportOptions
    ) -> ImportResult:
        """导入项目"""
        start_time = datetime.now()

        try:
            # 验证输入文件
            if not input_path.exists():
                return ImportResult(
                    success=False,
                    errors=[f"文件不存在: {input_path}"]
                )

            # 自动检测格式（如果未指定）
            if not format_type:
                format_type = self._detect_format_from_path(input_path)
                if not format_type:
                    return ImportResult(
                        success=False,
                        errors=["无法检测文件格式，请指定格式类型"]
                    )

            # 获取格式处理器
            handler = self.get_format_handler(format_type)
            if not handler:
                return ImportResult(
                    success=False,
                    errors=[f"不支持的格式: {format_type}"]
                )

            # 执行导入
            result = await handler.import_project(input_path, options)

            # 发布事件
            if result.success:
                try:
                    event = ProjectImportedEvent(
                        import_path=str(input_path),
                        format_type=format_type,
                        import_time=datetime.now()
                    )
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布项目导入事件失败: {e}")

            return result

        except Exception as e:
            logger.error(f"导入项目失败: {e}")
            return ImportResult(
                success=False,
                errors=[str(e)],
                import_time=(datetime.now() - start_time).total_seconds()
            )

    async def export_document(
        self,
        document_id: str,
        output_path: Path,
        format_type: str,
        options: ExportOptions
    ) -> ExportResult:
        """导出文档"""
        start_time = datetime.now()

        try:
            # 获取文档
            document = await self.document_repository.load(document_id)
            if not document:
                return ExportResult(
                    success=False,
                    errors=[f"文档不存在: {document_id}"]
                )

            # 自动检测格式（如果未指定）
            if not format_type:
                format_type = self._detect_format_from_path(output_path)
                if not format_type:
                    return ExportResult(
                        success=False,
                        errors=["无法检测文件格式，请指定格式类型"]
                    )

            # 获取格式处理器
            handler = self.get_format_handler(format_type)
            if not handler:
                return ExportResult(
                    success=False,
                    errors=[f"不支持的格式: {format_type}"]
                )

            # 执行导出
            result = await handler.export_document(document, output_path, options)

            # 发布事件
            if result.success:
                try:
                    event = DocumentExportedEvent(
                        document_id=document_id,
                        export_path=str(output_path),
                        export_format=format_type
                    )
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布文档导出事件失败: {e}")

            return result

        except Exception as e:
            logger.error(f"导出文档失败: {e}")
            return ExportResult(
                success=False,
                errors=[str(e)],
                export_time=(datetime.now() - start_time).total_seconds()
            )

    async def import_document(
        self,
        input_path: Path,
        format_type: str,
        options: ImportOptions
    ) -> ImportResult:
        """导入文档"""
        start_time = datetime.now()

        try:
            # 验证输入文件
            if not input_path.exists():
                return ImportResult(
                    success=False,
                    errors=[f"文件不存在: {input_path}"]
                )

            # 自动检测格式（如果未指定）
            if not format_type:
                format_type = self._detect_format_from_path(input_path)
                if not format_type:
                    return ImportResult(
                        success=False,
                        errors=["无法检测文件格式，请指定格式类型"]
                    )

            # 获取格式处理器
            handler = self.get_format_handler(format_type)
            if not handler:
                return ImportResult(
                    success=False,
                    errors=[f"不支持的格式: {format_type}"]
                )

            # 执行导入
            result = await handler.import_document(input_path, options)

            # 发布事件
            if result.success:
                try:
                    event = DocumentImportedEvent(
                        import_path=str(input_path),
                        format_type=format_type,
                        import_time=datetime.now()
                    )
                    await self.event_bus.publish_async(event)
                except Exception as e:
                    logger.warning(f"发布文档导入事件失败: {e}")
                return result

        except Exception as e:
            logger.error(f"导入文档失败: {e}")
            return ImportResult(
                success=False,
                errors=[str(e)],
                import_time=(datetime.now() - start_time).total_seconds()
            )

    # ========== 新增：列出已注册导出格式，供UI动态构建过滤器 ==========
    def list_export_formats(self) -> list[tuple[str, list[str]]]:
        """
        返回所有已注册格式的 (显示名称, 扩展名列表) 列表。
        显示名称来自处理器的 get_format_name()，扩展名形如 ['.md', '.markdown']。
        """
        formats: list[tuple[str, list[str]]] = []
        try:
            for _, handler in self._format_handlers.items():
                try:
                    name = handler.get_format_name()
                    exts = handler.get_supported_extensions()
                    if name and exts:
                        formats.append((name, exts))
                except Exception:
                    continue
        except Exception:
            pass
        return formats

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的格式"""
        formats = {}

        for format_type, handler in self._format_handlers.items():
            try:
                format_name = handler.get_format_name()
                extensions = handler.get_supported_extensions()
                formats[format_name] = extensions
            except Exception as e:
                logger.warning(f"获取格式信息失败 {format_type}: {e}")

        return formats

    def get_export_formats(self) -> List[str]:
        """获取支持的导出格式"""
        return list(self._format_handlers.keys())

    def get_import_formats(self) -> List[str]:
        """获取支持的导入格式"""
        return list(self._format_handlers.keys())

    def is_format_supported(self, format_type: str) -> bool:
        """检查是否支持指定格式"""
        return format_type.lower() in self._format_handlers

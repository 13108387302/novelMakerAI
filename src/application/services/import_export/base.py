#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入导出基类和接口

定义通用的导入导出接口和基础实现
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.entities.project import Project
from src.domain.entities.document import Document
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExportOptions:
    """
    导出选项配置类

    定义导出操作的各种配置选项，控制导出内容和格式。

    Attributes:
        include_documents: 是否包含文档内容
        include_characters: 是否包含角色信息
        include_settings: 是否包含项目设置
        include_metadata: 是否包含元数据
        include_statistics: 是否包含统计信息
        format_options: 格式特定的选项字典
        custom_template: 自定义模板路径
        output_encoding: 输出文件编码
        compress_output: 是否压缩输出
    """
    include_documents: bool = True
    include_characters: bool = True
    include_settings: bool = True
    include_metadata: bool = True
    include_statistics: bool = True
    format_options: Dict[str, Any] = field(default_factory=dict)
    custom_template: Optional[str] = None
    output_encoding: str = "utf-8"
    compress_output: bool = False


@dataclass
class ImportOptions:
    """
    导入选项配置类

    定义导入操作的各种配置选项，控制导入行为和数据处理。

    Attributes:
        merge_with_existing: 是否与现有数据合并
        overwrite_existing: 是否覆盖现有数据
        preserve_ids: 是否保留原始ID
        validate_content: 是否验证导入内容
        import_encoding: 导入文件编码
        custom_mapping: 自定义字段映射
    """
    merge_with_existing: bool = False
    overwrite_existing: bool = False
    preserve_ids: bool = False
    validate_content: bool = True
    import_encoding: str = "utf-8"
    custom_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    output_path: Optional[Path] = None
    exported_items: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    export_time: float = 0.0
    file_size: int = 0


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    imported_items: List[str] = field(default_factory=list)
    skipped_items: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    import_time: float = 0.0
    # 附加信息（用于后续流程）
    project: Optional[Project] = None
    document: Optional[Document] = None
    project_path: Optional[str] = None


class IFormatHandler(ABC):
    """
    格式处理器接口

    定义所有格式处理器必须实现的方法。
    提供项目和文档的导入导出功能抽象。

    实现方式：
    - 使用抽象基类确保接口一致性
    - 支持异步操作提高性能
    - 提供详细的结果反馈
    - 支持灵活的选项配置
    """

    @abstractmethod
    async def export_project(self, project: Project, output_path: Path, options: ExportOptions) -> ExportResult:
        """
        导出项目到指定格式

        Args:
            project: 要导出的项目实例
            output_path: 输出文件路径
            options: 导出选项配置

        Returns:
            ExportResult: 导出操作结果
        """
        pass

    @abstractmethod
    async def import_project(self, input_path: Path, options: ImportOptions) -> ImportResult:
        """
        从指定格式导入项目

        Args:
            input_path: 输入文件路径
            options: 导入选项配置

        Returns:
            ImportResult: 导入操作结果
        """
        pass

    @abstractmethod
    async def export_document(self, document: Document, output_path: Path, options: ExportOptions) -> ExportResult:
        """
        导出文档到指定格式

        Args:
            document: 要导出的文档实例
            output_path: 输出文件路径
            options: 导出选项配置

        Returns:
            ExportResult: 导出操作结果
        """
        pass

    @abstractmethod
    async def import_document(self, input_path: Path, options: ImportOptions) -> ImportResult:
        """
        从指定格式导入文档

        Args:
            input_path: 输入文件路径
            options: 导入选项配置

        Returns:
            ImportResult: 导入操作结果
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        pass

    @abstractmethod
    def get_format_name(self) -> str:
        """
        获取格式的显示名称

        Returns:
            str: 格式的用户友好名称
        """
        pass


class BaseFormatHandler(IFormatHandler):
    """格式处理器基类"""

    def __init__(self, service: 'IImportExportService'):
        self.service = service
        self.logger = get_logger(self.__class__.__name__)

    async def export_project(self, project: Project, output_path: Path, options: ExportOptions) -> ExportResult:
        """导出项目 - 基础实现"""
        start_time = datetime.now()
        result = ExportResult(success=False)
        
        try:
            # 验证输入
            if not project:
                result.errors.append("项目对象为空")
                return result
                
            if not output_path:
                result.errors.append("输出路径为空")
                return result
                
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 调用具体的导出实现
            success = await self._do_export_project(project, output_path, options)

            if success:
                # 二次校验：处理器报告成功，但文件未生成时视为失败并给出明确错误
                if output_path.exists():
                    result.success = True
                    result.output_path = output_path
                    result.exported_items.append(f"项目: {project.name}")
                    try:
                        result.file_size = output_path.stat().st_size
                    except Exception:
                        result.file_size = 0
                else:
                    result.errors.append("处理器报告成功但未生成文件")
            else:
                result.errors.append("导出失败")

        except Exception as e:
            self.logger.error(f"导出项目失败: {e}")
            result.errors.append(str(e))
            
        finally:
            result.export_time = (datetime.now() - start_time).total_seconds()
            
        return result

    async def import_project(self, input_path: Path, options: ImportOptions) -> ImportResult:
        """导入项目 - 基础实现"""
        start_time = datetime.now()
        result = ImportResult(success=False)
        
        try:
            # 验证输入
            if not input_path or not input_path.exists():
                result.errors.append("输入文件不存在")
                return result
                
            # 调用具体的导入实现
            project = await self._do_import_project(input_path, options)

            if project:
                result.success = True
                # 记录关键结果字段，供控制器层使用
                result.project = project
                if hasattr(project, 'id') and project.id:
                    result.imported_items.append(project.id)
                else:
                    result.imported_items.append(project.name or "")
                # 附带项目路径（若可用）
                if hasattr(project, 'root_path') and project.root_path:
                    result.project_path = str(project.root_path)
            else:
                result.errors.append("导入失败")

        except Exception as e:
            self.logger.error(f"导入项目失败: {e}")
            result.errors.append(str(e))
            
        finally:
            result.import_time = (datetime.now() - start_time).total_seconds()
            
        return result

    async def export_document(self, document: Document, output_path: Path, options: ExportOptions) -> ExportResult:
        """导出文档 - 基础实现"""
        start_time = datetime.now()
        result = ExportResult(success=False)
        
        try:
            # 验证输入
            if not document:
                result.errors.append("文档对象为空")
                return result
                
            if not output_path:
                result.errors.append("输出路径为空")
                return result
                
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 调用具体的导出实现
            success = await self._do_export_document(document, output_path, options)
            
            if success:
                result.success = True
                result.output_path = output_path
                result.exported_items.append(f"文档: {document.title}")
                
                # 计算文件大小
                if output_path.exists():
                    result.file_size = output_path.stat().st_size
                    
            else:
                result.errors.append("导出失败")
                
        except Exception as e:
            self.logger.error(f"导出文档失败: {e}")
            result.errors.append(str(e))
            
        finally:
            result.export_time = (datetime.now() - start_time).total_seconds()
            
        return result

    async def import_document(self, input_path: Path, options: ImportOptions) -> ImportResult:
        """导入文档 - 基础实现"""
        start_time = datetime.now()
        result = ImportResult(success=False)
        
        try:
            # 验证输入
            if not input_path or not input_path.exists():
                result.errors.append("输入文件不存在")
                return result
                
            # 调用具体的导入实现
            document = await self._do_import_document(input_path, options)

            if document:
                result.success = True
                result.document = document
                if hasattr(document, 'id') and document.id:
                    result.imported_items.append(document.id)
                else:
                    result.imported_items.append(document.title or "")
            else:
                result.errors.append("导入失败")

        except Exception as e:
            self.logger.error(f"导入文档失败: {e}")
            result.errors.append(str(e))
            
        finally:
            result.import_time = (datetime.now() - start_time).total_seconds()
            
        return result

    # 抽象方法 - 子类必须实现
    async def _do_export_project(self, project: Project, output_path: Path, options: ExportOptions) -> bool:
        """具体的项目导出实现"""
        raise NotImplementedError

    async def _do_import_project(self, input_path: Path, options: ImportOptions) -> Optional[Project]:
        """具体的项目导入实现"""
        raise NotImplementedError

    async def _do_export_document(self, document: Document, output_path: Path, options: ExportOptions) -> bool:
        """具体的文档导出实现"""
        raise NotImplementedError

    async def _do_import_document(self, input_path: Path, options: ImportOptions) -> Optional[Document]:
        """具体的文档导入实现"""
        raise NotImplementedError

    # 工具方法
    def _validate_file_extension(self, file_path: Path, expected_extensions: List[str]) -> bool:
        """验证文件扩展名"""
        if not file_path:
            return False
            
        file_ext = file_path.suffix.lower()
        return file_ext in [ext.lower() for ext in expected_extensions]

    def _ensure_directory(self, path: Path) -> bool:
        """确保目录存在"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"创建目录失败: {e}")
            return False

    async def _read_file_content(self, file_path: Path, encoding: str = "utf-8") -> Optional[str]:
        """读取文件内容（统一实现，异步）"""
        try:
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("import_export")
            # 异步安全读取（带编码回退）
            return await ops.load_text_safe(file_path)
        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            return None

    async def _write_file_content(self, file_path: Path, content: str, encoding: str = "utf-8") -> bool:
        """写入文件内容（统一原子写入，异步）"""
        try:
            from src.shared.utils.file_operations import get_file_operations
            ops = get_file_operations("import_export")
            return await ops.save_text_atomic(file_path, content, create_backup=True)
        except Exception as e:
            self.logger.error(f"写入文件失败: {e}")
            return False


class IImportExportService(ABC):
    """导入导出服务接口"""

    @abstractmethod
    async def export_project(self, project_id: str, output_path: Path, format_type: str, options: ExportOptions) -> ExportResult:
        """导出项目"""
        pass

    @abstractmethod
    async def import_project(self, input_path: Path, format_type: str, options: ImportOptions) -> ImportResult:
        """导入项目"""
        pass

    @abstractmethod
    async def export_document(self, document_id: str, output_path: Path, format_type: str, options: ExportOptions) -> ExportResult:
        """导出文档"""
        pass

    @abstractmethod
    async def import_document(self, input_path: Path, format_type: str, options: ImportOptions) -> ImportResult:
        """导入文档"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的格式"""
        pass

    @abstractmethod
    def register_format_handler(self, format_type: str, handler: IFormatHandler):
        """注册格式处理器"""
        pass

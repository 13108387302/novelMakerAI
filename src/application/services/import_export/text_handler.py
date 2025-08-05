#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本格式处理器

处理纯文本格式的项目和文档导入导出
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .base import BaseFormatHandler, ExportOptions, ImportOptions
from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class TextFormatHandler(BaseFormatHandler):
    """
    文本格式处理器

    处理纯文本格式的项目和文档导入导出操作。
    提供简洁的文本输出格式，适合阅读和打印。

    实现方式：
    - 使用纯文本格式确保最大兼容性
    - 提供清晰的章节分隔和层次结构
    - 支持自定义文本模板
    - 处理各种文本编码格式
    """

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.txt', '.text']

    def get_format_name(self) -> str:
        """
        获取格式名称

        Returns:
            str: 格式的显示名称
        """
        return "纯文本"

    async def _do_export_project(self, project: Project, output_path: Path, options: ExportOptions) -> bool:
        """导出项目为文本格式"""
        try:
            content_parts = []
            
            # 添加项目标题
            content_parts.append(f"项目: {project.name}")
            content_parts.append("=" * 50)
            content_parts.append("")
            
            # 添加项目描述
            if hasattr(project, 'description') and project.description:
                content_parts.append("项目描述:")
                content_parts.append(project.description)
                content_parts.append("")
            
            # 添加导出信息
            content_parts.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_parts.append("")
            
            # 获取并添加文档内容
            if options.include_documents:
                try:
                    documents = await self.service.document_repository.get_by_project_id(project.id)
                    
                    if documents:
                        content_parts.append("文档内容:")
                        content_parts.append("-" * 30)
                        content_parts.append("")
                        
                        for i, doc in enumerate(documents, 1):
                            content_parts.append(f"{i}. {doc.title}")
                            content_parts.append("-" * len(f"{i}. {doc.title}"))
                            content_parts.append("")
                            content_parts.append(doc.content)
                            content_parts.append("")
                            content_parts.append("")
                            
                except Exception as e:
                    logger.warning(f"获取项目文档失败: {e}")
                    content_parts.append("无法获取文档内容")
                    content_parts.append("")
            
            # 添加统计信息
            if options.include_statistics:
                content_parts.append("统计信息:")
                content_parts.append("-" * 20)
                
                total_chars = sum(len(part) for part in content_parts)
                total_words = sum(len(part.split()) for part in content_parts)
                
                content_parts.append(f"总字符数: {total_chars}")
                content_parts.append(f"总词数: {total_words}")
                content_parts.append("")
            
            # 写入文件
            final_content = "\n".join(content_parts)
            return self._write_file_content(output_path, final_content, options.output_encoding)
            
        except Exception as e:
            logger.error(f"导出文本失败: {e}")
            return False

    async def _do_import_project(self, input_path: Path, options: ImportOptions) -> Optional[Project]:
        """从文本导入项目"""
        try:
            # 验证文件扩展名
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            # 读取文件内容
            content = self._read_file_content(input_path, options.import_encoding)
            if not content:
                logger.error("无法读取文件内容")
                return None

            # 解析内容
            lines = content.split('\n')
            
            # 提取项目名称（假设第一行是项目名）
            project_name = input_path.stem  # 使用文件名作为项目名
            if lines and lines[0].strip():
                first_line = lines[0].strip()
                if first_line.startswith("项目:"):
                    project_name = first_line.replace("项目:", "").strip()
                else:
                    project_name = first_line
            
            # 创建项目
            project = Project(
                id="",  # 将由仓储分配
                name=project_name,
                description=f"从文本文件导入: {input_path.name}"
            )
            
            # 创建单个文档包含所有内容
            document = Document(
                id="",  # 将由仓储分配
                title=f"{project_name} - 内容",
                content=content,
                type=DocumentType.CHAPTER
            )
            
            # 保存文档
            await self.service.document_repository.save(document)
            
            logger.info(f"项目已从文本导入: {project.name}")
            return project
            
        except Exception as e:
            logger.error(f"从文本导入项目失败: {e}")
            return None

    async def _do_export_document(self, document: Document, output_path: Path, options: ExportOptions) -> bool:
        """导出文档为文本格式"""
        try:
            content_parts = []
            
            # 添加文档标题
            content_parts.append(document.title)
            content_parts.append("=" * len(document.title))
            content_parts.append("")
            
            # 添加导出信息
            if options.include_metadata:
                content_parts.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                content_parts.append(f"文档类型: {document.type}")
                content_parts.append("")
            
            # 添加文档内容
            content_parts.append(document.content)
            
            # 写入文件
            final_content = "\n".join(content_parts)
            return self._write_file_content(output_path, final_content, options.output_encoding)
            
        except Exception as e:
            logger.error(f"导出文档为文本失败: {e}")
            return False

    async def _do_import_document(self, input_path: Path, options: ImportOptions) -> Optional[Document]:
        """从文本导入文档"""
        try:
            # 验证文件扩展名
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            # 读取文件内容
            content = self._read_file_content(input_path, options.import_encoding)
            if not content:
                logger.error("无法读取文件内容")
                return None

            # 使用文件名作为文档标题
            title = input_path.stem
            
            # 尝试从内容中提取标题（如果第一行看起来像标题）
            lines = content.split('\n')
            if lines and lines[0].strip() and len(lines[0].strip()) < 100:
                # 如果第一行较短，可能是标题
                potential_title = lines[0].strip()
                if not potential_title.endswith('.') and len(potential_title.split()) < 10:
                    title = potential_title
                    # 移除标题行和可能的分隔线
                    if len(lines) > 1 and lines[1].strip() and all(c in '=-_' for c in lines[1].strip()):
                        content = '\n'.join(lines[2:])
                    else:
                        content = '\n'.join(lines[1:])
            
            # 创建文档
            document = Document(
                id="",  # 将由仓储分配
                title=title,
                content=content.strip(),
                type=DocumentType.CHAPTER
            )
            
            logger.info(f"文档已从文本导入: {document.title}")
            return document
            
        except Exception as e:
            logger.error(f"从文本导入文档失败: {e}")
            return None


class MarkdownFormatHandler(BaseFormatHandler):
    """
    Markdown格式处理器

    处理Markdown格式的项目和文档导入导出操作。
    提供结构化的Markdown输出，支持标准Markdown语法。

    实现方式：
    - 使用标准Markdown语法确保兼容性
    - 提供清晰的层次结构和格式化
    - 支持代码块、表格和链接
    - 适合在线发布和版本控制
    """

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.md', '.markdown']

    def get_format_name(self) -> str:
        """
        获取格式名称

        Returns:
            str: 格式的显示名称
        """
        return "Markdown"

    async def _do_export_project(self, project: Project, output_path: Path, options: ExportOptions) -> bool:
        """导出项目为Markdown格式"""
        try:
            content_parts = []
            
            # 添加项目标题
            content_parts.append(f"# {project.name}")
            content_parts.append("")
            
            # 添加项目描述
            if hasattr(project, 'description') and project.description:
                content_parts.append("## 项目描述")
                content_parts.append("")
                content_parts.append(project.description)
                content_parts.append("")
            
            # 添加导出信息
            content_parts.append("## 导出信息")
            content_parts.append("")
            content_parts.append(f"- **导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_parts.append(f"- **导出工具**: AI小说编辑器")
            content_parts.append("")
            
            # 获取并添加文档内容
            if options.include_documents:
                try:
                    documents = await self.service.document_repository.get_by_project_id(project.id)
                    
                    if documents:
                        content_parts.append("## 文档内容")
                        content_parts.append("")
                        
                        for i, doc in enumerate(documents, 1):
                            content_parts.append(f"### {i}. {doc.title}")
                            content_parts.append("")
                            content_parts.append(doc.content)
                            content_parts.append("")
                            content_parts.append("---")
                            content_parts.append("")
                            
                except Exception as e:
                    logger.warning(f"获取项目文档失败: {e}")
                    content_parts.append("## 文档内容")
                    content_parts.append("")
                    content_parts.append("*无法获取文档内容*")
                    content_parts.append("")
            
            # 写入文件
            final_content = "\n".join(content_parts)
            return self._write_file_content(output_path, final_content, options.output_encoding)
            
        except Exception as e:
            logger.error(f"导出Markdown失败: {e}")
            return False

    async def _do_import_project(self, input_path: Path, options: ImportOptions) -> Optional[Project]:
        """从Markdown导入项目"""
        try:
            # 验证文件扩展名
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            # 读取文件内容
            content = self._read_file_content(input_path, options.import_encoding)
            if not content:
                logger.error("无法读取文件内容")
                return None

            # 解析Markdown内容
            lines = content.split('\n')
            
            # 提取项目名称（查找第一个一级标题）
            project_name = input_path.stem
            for line in lines:
                if line.strip().startswith('# '):
                    project_name = line.strip()[2:].strip()
                    break
            
            # 创建项目
            project = Project(
                id="",
                name=project_name,
                description=f"从Markdown文件导入: {input_path.name}"
            )
            
            # 创建文档包含内容
            document = Document(
                id="",
                title=f"{project_name} - 内容",
                content=content,
                type=DocumentType.CHAPTER
            )
            
            # 保存文档
            await self.service.document_repository.save(document)
            
            logger.info(f"项目已从Markdown导入: {project.name}")
            return project
            
        except Exception as e:
            logger.error(f"从Markdown导入项目失败: {e}")
            return None

    async def _do_export_document(self, document: Document, output_path: Path, options: ExportOptions) -> bool:
        """导出文档为Markdown格式"""
        try:
            content_parts = []
            
            # 添加文档标题
            content_parts.append(f"# {document.title}")
            content_parts.append("")
            
            # 添加元数据
            if options.include_metadata:
                content_parts.append("## 文档信息")
                content_parts.append("")
                content_parts.append(f"- **导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                content_parts.append(f"- **文档类型**: {document.type}")
                content_parts.append("")
                content_parts.append("---")
                content_parts.append("")
            
            # 添加文档内容
            content_parts.append(document.content)
            
            # 写入文件
            final_content = "\n".join(content_parts)
            return self._write_file_content(output_path, final_content, options.output_encoding)
            
        except Exception as e:
            logger.error(f"导出文档为Markdown失败: {e}")
            return False

    async def _do_import_document(self, input_path: Path, options: ImportOptions) -> Optional[Document]:
        """从Markdown导入文档"""
        try:
            # 验证文件扩展名
            if not self._validate_file_extension(input_path, self.get_supported_extensions()):
                logger.error(f"不支持的文件格式: {input_path.suffix}")
                return None

            # 读取文件内容
            content = self._read_file_content(input_path, options.import_encoding)
            if not content:
                logger.error("无法读取文件内容")
                return None

            # 提取标题
            title = input_path.stem
            lines = content.split('\n')
            
            # 查找第一个标题
            for line in lines:
                if line.strip().startswith('# '):
                    title = line.strip()[2:].strip()
                    break
            
            # 创建文档
            document = Document(
                id="",
                title=title,
                content=content.strip(),
                type=DocumentType.CHAPTER
            )
            
            logger.info(f"文档已从Markdown导入: {document.title}")
            return document
            
        except Exception as e:
            logger.error(f"从Markdown导入文档失败: {e}")
            return None

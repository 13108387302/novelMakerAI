#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF格式处理器

处理PDF格式的项目和文档导出（仅支持导出）
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .base import BaseFormatHandler, ExportOptions, ImportOptions
from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

# 检查PDF库是否可用
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.colors import black, blue, red
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("reportlab库不可用，PDF格式处理器将无法正常工作")


class PdfFormatHandler(BaseFormatHandler):
    """
    PDF格式处理器（仅支持导出）

    处理PDF格式的项目和文档导出操作。
    使用ReportLab库生成高质量的PDF文档。

    实现方式：
    - 仅支持导出，不支持从PDF导入
    - 使用ReportLab库生成专业PDF文档
    - 支持中文字体和自定义样式
    - 提供完整的文档结构和格式化

    Note:
        PDF格式由于其特性，不支持导入功能
    """

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.pdf']

    def get_format_name(self) -> str:
        """
        获取格式名称

        Returns:
            str: 格式的显示名称
        """
        return "PDF文档"

    async def _do_export_project(self, project: Project, output_path: Path, options: ExportOptions) -> bool:
        """导出项目为PDF格式"""
        if not PDF_AVAILABLE:
            logger.error("reportlab库不可用，无法导出PDF格式")
            return False
            
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # 获取样式
            styles = getSampleStyleSheet()
            
            # 创建自定义样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # 居中
                textColor=blue
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                textColor=black
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
                firstLineIndent=24  # 首行缩进
            )
            
            # 构建内容
            story = []
            
            # 添加项目标题
            story.append(Paragraph(project.name, title_style))
            story.append(Spacer(1, 20))
            
            # 添加项目描述
            if hasattr(project, 'description') and project.description:
                story.append(Paragraph('项目描述', heading_style))
                story.append(Paragraph(project.description, normal_style))
                story.append(Spacer(1, 20))
            
            # 添加导出信息
            if options.include_metadata:
                story.append(Paragraph('导出信息', heading_style))
                export_info = f"""
                导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
                导出工具: AI小说编辑器<br/>
                格式版本: PDF
                """
                story.append(Paragraph(export_info, normal_style))
                story.append(PageBreak())
            
            # 获取并添加文档内容
            if options.include_documents:
                try:
                    documents = await self.service.document_repository.get_by_project_id(project.id)
                    
                    if documents:
                        story.append(Paragraph('文档内容', heading_style))
                        story.append(Spacer(1, 20))
                        
                        for i, document in enumerate(documents, 1):
                            # 添加文档标题
                            doc_title = f"{i}. {document.title}"
                            story.append(Paragraph(doc_title, heading_style))
                            
                            # 添加文档内容
                            content_paragraphs = document.content.split('\n\n')
                            for paragraph_text in content_paragraphs:
                                if paragraph_text.strip():
                                    # 转义HTML特殊字符
                                    escaped_text = self._escape_html(paragraph_text.strip())
                                    story.append(Paragraph(escaped_text, normal_style))
                            
                            # 添加分页符（除了最后一个文档）
                            if i < len(documents):
                                story.append(PageBreak())
                                
                except Exception as e:
                    logger.warning(f"获取项目文档失败: {e}")
                    story.append(Paragraph("无法获取文档内容", normal_style))
            
            # 添加统计信息
            if options.include_statistics:
                story.append(PageBreak())
                story.append(Paragraph('统计信息', heading_style))
                
                # 计算统计信息
                total_chars = 0
                total_words = 0
                doc_count = 0
                
                try:
                    documents = await self.service.document_repository.get_by_project_id(project.id)
                    doc_count = len(documents)
                    for document in documents:
                        total_chars += len(document.content)
                        total_words += len(document.content.split())
                except:
                    pass
                
                stats_text = f"""
                总字符数: {total_chars:,}<br/>
                总词数: {total_words:,}<br/>
                文档数量: {doc_count}
                """
                story.append(Paragraph(stats_text, normal_style))
            
            # 生成PDF
            doc.build(story)
            
            logger.info(f"项目已导出为PDF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出PDF失败: {e}")
            return False

    async def _do_import_project(self, input_path: Path, options: ImportOptions) -> Optional[Project]:
        """从PDF导入项目（不支持）"""
        logger.warning("PDF格式不支持导入功能")
        return None

    async def _do_export_document(self, document: Document, output_path: Path, options: ExportOptions) -> bool:
        """导出文档为PDF格式"""
        if not PDF_AVAILABLE:
            logger.error("reportlab库不可用，无法导出PDF格式")
            return False
            
        try:
            # 创建PDF文档
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # 获取样式
            styles = getSampleStyleSheet()
            
            # 创建自定义样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                alignment=1,  # 居中
                textColor=blue
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
                firstLineIndent=24  # 首行缩进
            )
            
            # 构建内容
            story = []
            
            # 添加文档标题
            story.append(Paragraph(document.title, title_style))
            story.append(Spacer(1, 20))
            
            # 添加元数据
            if options.include_metadata:
                metadata_style = ParagraphStyle(
                    'Metadata',
                    parent=styles['Normal'],
                    fontSize=10,
                    spaceAfter=12,
                    textColor=red
                )
                
                metadata_text = f"""
                导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
                文档类型: {document.type}<br/>
                导出工具: AI小说编辑器
                """
                story.append(Paragraph(metadata_text, metadata_style))
                story.append(Spacer(1, 20))
            
            # 添加文档内容
            content_paragraphs = document.content.split('\n\n')
            for paragraph_text in content_paragraphs:
                if paragraph_text.strip():
                    # 转义HTML特殊字符
                    escaped_text = self._escape_html(paragraph_text.strip())
                    story.append(Paragraph(escaped_text, normal_style))
            
            # 生成PDF
            doc.build(story)
            
            logger.info(f"文档已导出为PDF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出文档为PDF失败: {e}")
            return False

    async def _do_import_document(self, input_path: Path, options: ImportOptions) -> Optional[Document]:
        """从PDF导入文档（不支持）"""
        logger.warning("PDF格式不支持导入功能")
        return None
        
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;'
        }
        
        for char, escape in replacements.items():
            text = text.replace(char, escape)
            
        return text

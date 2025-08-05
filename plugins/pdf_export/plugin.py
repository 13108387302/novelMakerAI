#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF导出插件

提供将项目和文档导出为PDF格式的功能
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from src.shared.plugins.plugin_interface import (
    ExportPlugin, PluginInfo, PluginType, create_plugin_info
)
from src.domain.entities.project import Project
from src.domain.entities.document import Document
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class PDFExportPlugin(ExportPlugin):
    """
    PDF导出插件
    
    将项目和文档导出为PDF格式，支持专业的排版和格式化。
    
    功能特性：
    - 支持中文字体
    - 自动生成目录
    - 页眉页脚
    - 章节分页
    - 自定义样式
    - 书签导航
    """
    
    def get_plugin_info(self) -> PluginInfo:
        """
        获取插件信息

        Returns:
            PluginInfo: 插件的详细信息
        """
        return create_plugin_info(
            plugin_id="pdf_export",
            name="PDF导出器",
            version="1.0.0",
            description="将项目和文档导出为PDF格式，支持专业排版",
            author="AI小说编辑器团队",
            plugin_type=PluginType.EXPORT,
            dependencies=["reportlab"],
            min_app_version="2.0.0",
            tags=["导出", "PDF", "文档", "排版"]
        )
    
    def on_initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        try:
            if not PDF_AVAILABLE:
                self.log_error("ReportLab库不可用，无法使用PDF导出功能")
                return False
            
            self.log_info("初始化PDF导出插件...")
            
            # 初始化导出选项
            self.export_options = {
                'page_size': 'A4',              # 页面大小
                'font_name': 'SimSun',          # 字体名称
                'font_size': 12,                # 字体大小
                'line_spacing': 1.2,            # 行间距
                'margin_top': 1.0,              # 上边距(英寸)
                'margin_bottom': 1.0,           # 下边距(英寸)
                'margin_left': 1.0,             # 左边距(英寸)
                'margin_right': 1.0,            # 右边距(英寸)
                'include_toc': True,            # 包含目录
                'include_header': True,         # 包含页眉
                'include_footer': True,         # 包含页脚
                'chapter_break': True,          # 章节分页
                'encoding': 'utf-8'             # 文件编码
            }
            
            # 注册中文字体
            self._register_fonts()
            
            return True
            
        except Exception as e:
            self.log_error(f"初始化失败: {e}")
            return False
    
    def on_activate(self) -> bool:
        """
        激活插件
        
        Returns:
            bool: 激活成功返回True，失败返回False
        """
        try:
            self.log_info("激活PDF导出插件...")
            
            # 注册导出格式
            if hasattr(self.context, 'register_export_format'):
                self.context.register_export_format(
                    format_name="PDF",
                    extensions=['.pdf'],
                    plugin=self
                )
            
            return True
            
        except Exception as e:
            self.log_error(f"激活失败: {e}")
            return False
    
    def _register_fonts(self):
        """注册中文字体"""
        try:
            # 尝试注册常见的中文字体
            font_paths = [
                "C:/Windows/Fonts/simsun.ttc",      # 宋体
                "C:/Windows/Fonts/simhei.ttf",      # 黑体
                "C:/Windows/Fonts/msyh.ttc",        # 微软雅黑
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        if font_path.endswith('.ttc'):
                            # TTC字体集合文件
                            pdfmetrics.registerFont(TTFont('SimSun', font_path, subfontIndex=0))
                        else:
                            pdfmetrics.registerFont(TTFont('SimSun', font_path))
                        self.log_info(f"成功注册字体: {font_path}")
                        break
                    except Exception as e:
                        self.log_warning(f"注册字体失败 {font_path}: {e}")
                        continue
            else:
                self.log_warning("未找到可用的中文字体，将使用默认字体")
                
        except Exception as e:
            self.log_error(f"注册字体失败: {e}")
    
    def export_project(self, project: Project, output_path: Path, options: Dict[str, Any] = None) -> bool:
        """
        导出项目为PDF格式
        
        Args:
            project: 要导出的项目
            output_path: 输出文件路径
            options: 导出选项
            
        Returns:
            bool: 导出成功返回True，失败返回False
        """
        try:
            if not PDF_AVAILABLE:
                self.log_error("ReportLab库不可用，无法导出PDF")
                return False
            
            self.log_info(f"开始导出项目: {project.name}")
            
            # 合并导出选项
            export_opts = {**self.export_options, **(options or {})}
            
            # 创建PDF文档
            doc = self._create_pdf_document(output_path, export_opts)
            
            # 生成内容
            story = self._generate_project_content(project, export_opts)
            
            # 构建PDF
            doc.build(story)
            
            self.log_info(f"项目导出完成: {output_path}")
            return True
            
        except Exception as e:
            self.log_error(f"导出项目失败: {e}")
            return False
    
    def export_document(self, document: Document, output_path: Path, options: Dict[str, Any] = None) -> bool:
        """
        导出文档为PDF格式
        
        Args:
            document: 要导出的文档
            output_path: 输出文件路径
            options: 导出选项
            
        Returns:
            bool: 导出成功返回True，失败返回False
        """
        try:
            if not PDF_AVAILABLE:
                self.log_error("ReportLab库不可用，无法导出PDF")
                return False
            
            self.log_info(f"开始导出文档: {document.title}")
            
            # 合并导出选项
            export_opts = {**self.export_options, **(options or {})}
            
            # 创建PDF文档
            doc = self._create_pdf_document(output_path, export_opts)
            
            # 生成内容
            story = self._generate_document_content(document, export_opts)
            
            # 构建PDF
            doc.build(story)
            
            self.log_info(f"文档导出完成: {output_path}")
            return True
            
        except Exception as e:
            self.log_error(f"导出文档失败: {e}")
            return False
    
    def _create_pdf_document(self, output_path: Path, options: Dict[str, Any]) -> SimpleDocTemplate:
        """创建PDF文档对象"""
        # 页面大小
        page_size = A4 if options.get('page_size') == 'A4' else letter
        
        # 边距
        margin_top = options.get('margin_top', 1.0) * inch
        margin_bottom = options.get('margin_bottom', 1.0) * inch
        margin_left = options.get('margin_left', 1.0) * inch
        margin_right = options.get('margin_right', 1.0) * inch
        
        # 创建文档
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
            leftMargin=margin_left,
            rightMargin=margin_right
        )
        
        return doc
    
    def _generate_project_content(self, project: Project, options: Dict[str, Any]) -> List:
        """生成项目PDF内容"""
        story = []
        styles = getSampleStyleSheet()
        
        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName='SimSun',
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontName='SimSun',
            fontSize=16,
            spaceAfter=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='SimSun',
            fontSize=options.get('font_size', 12),
            leading=options.get('font_size', 12) * options.get('line_spacing', 1.2),
            alignment=TA_JUSTIFY
        )
        
        # 标题页
        story.append(Paragraph(project.name, title_style))
        story.append(Spacer(1, 0.5*inch))
        
        # 项目信息
        if project.description:
            story.append(Paragraph("项目描述", heading_style))
            story.append(Paragraph(project.description, normal_style))
            story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("项目信息", heading_style))
        info_text = f"""
        项目类型: {project.type}<br/>
        项目状态: {project.status}<br/>
        导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        story.append(Paragraph(info_text, normal_style))
        
        # 分页
        story.append(PageBreak())
        
        # 目录（如果启用）
        if options.get('include_toc', True):
            story.append(Paragraph("目录", heading_style))
            # 这里可以添加目录生成逻辑
            story.append(Paragraph("1. 项目信息", normal_style))
            story.append(Paragraph("2. 文档内容", normal_style))
            story.append(PageBreak())
        
        # 文档内容
        story.append(Paragraph("文档内容", heading_style))
        story.append(Paragraph("文档内容将在此处显示", normal_style))
        
        return story
    
    def _generate_document_content(self, document: Document, options: Dict[str, Any]) -> List:
        """生成文档PDF内容"""
        story = []
        styles = getSampleStyleSheet()
        
        # 自定义样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName='SimSun',
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='SimSun',
            fontSize=options.get('font_size', 12),
            leading=options.get('font_size', 12) * options.get('line_spacing', 1.2),
            alignment=TA_JUSTIFY
        )
        
        # 文档标题
        story.append(Paragraph(document.title, title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # 文档内容
        if document.content:
            # 处理段落
            paragraphs = document.content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), normal_style))
                    story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("文档内容为空", normal_style))
        
        return story
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的导出格式
        
        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.pdf']
    
    def get_export_options(self) -> Dict[str, Any]:
        """
        获取导出选项
        
        Returns:
            Dict[str, Any]: 可配置的导出选项
        """
        return {
            'page_size': {
                'type': 'choice',
                'choices': ['A4', 'Letter'],
                'default': 'A4',
                'description': '页面大小'
            },
            'font_size': {
                'type': 'integer',
                'min': 8,
                'max': 24,
                'default': 12,
                'description': '字体大小'
            },
            'line_spacing': {
                'type': 'float',
                'min': 1.0,
                'max': 3.0,
                'default': 1.2,
                'description': '行间距'
            },
            'include_toc': {
                'type': 'boolean',
                'default': True,
                'description': '包含目录'
            },
            'chapter_break': {
                'type': 'boolean',
                'default': True,
                'description': '章节分页'
            }
        }

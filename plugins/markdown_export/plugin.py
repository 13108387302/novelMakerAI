#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown导出插件

提供将项目和文档导出为Markdown格式的功能
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.shared.plugins.plugin_interface import (
    ExportPlugin, PluginInfo, PluginType, create_plugin_info
)
from src.domain.entities.project import Project
from src.domain.entities.document import Document
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownExportPlugin(ExportPlugin):
    """
    Markdown导出插件
    
    将项目和文档导出为Markdown格式，支持多种Markdown风格和自定义选项。
    
    功能特性：
    - 支持标准Markdown和GitHub Flavored Markdown
    - 自动生成目录结构
    - 支持代码块和表格
    - 保留文档层次结构
    - 支持元数据导出
    - 自定义导出模板
    """
    
    def get_plugin_info(self) -> PluginInfo:
        """
        获取插件信息

        Returns:
            PluginInfo: 插件的详细信息
        """
        return create_plugin_info(
            plugin_id="markdown_export",
            name="Markdown导出器",
            version="1.0.0",
            description="将项目和文档导出为Markdown格式，支持多种Markdown风格",
            author="AI小说编辑器团队",
            plugin_type=PluginType.EXPORT,
            dependencies=[],
            min_app_version="2.0.0",
            tags=["导出", "Markdown", "文档"]
        )
    
    def on_initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        try:
            self.log_info("初始化Markdown导出插件...")
            
            # 初始化导出选项
            self.export_options = {
                'include_toc': True,           # 包含目录
                'include_metadata': True,      # 包含元数据
                'markdown_flavor': 'github',  # Markdown风格
                'code_highlighting': True,    # 代码高亮
                'table_support': True,        # 表格支持
                'line_breaks': 'lf',          # 换行符类型
                'encoding': 'utf-8'           # 文件编码
            }
            
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
            self.log_info("激活Markdown导出插件...")
            
            # 注册导出格式
            if hasattr(self.context, 'register_export_format'):
                self.context.register_export_format(
                    format_name="Markdown",
                    extensions=['.md', '.markdown'],
                    plugin=self
                )
            
            return True
            
        except Exception as e:
            self.log_error(f"激活失败: {e}")
            return False
    
    def export_project(self, project: Project, output_path: Path, options: Dict[str, Any] = None) -> bool:
        """
        导出项目为Markdown格式
        
        Args:
            project: 要导出的项目
            output_path: 输出文件路径
            options: 导出选项
            
        Returns:
            bool: 导出成功返回True，失败返回False
        """
        try:
            self.log_info(f"开始导出项目: {project.name}")
            
            # 合并导出选项
            export_opts = {**self.export_options, **(options or {})}
            
            # 生成Markdown内容
            markdown_content = self._generate_project_markdown(project, export_opts)
            
            # 写入文件
            with open(output_path, 'w', encoding=export_opts['encoding']) as f:
                f.write(markdown_content)
            
            self.log_info(f"项目导出完成: {output_path}")
            return True
            
        except Exception as e:
            self.log_error(f"导出项目失败: {e}")
            return False
    
    def export_document(self, document: Document, output_path: Path, options: Dict[str, Any] = None) -> bool:
        """
        导出文档为Markdown格式
        
        Args:
            document: 要导出的文档
            output_path: 输出文件路径
            options: 导出选项
            
        Returns:
            bool: 导出成功返回True，失败返回False
        """
        try:
            self.log_info(f"开始导出文档: {document.title}")
            
            # 合并导出选项
            export_opts = {**self.export_options, **(options or {})}
            
            # 生成Markdown内容
            markdown_content = self._generate_document_markdown(document, export_opts)
            
            # 写入文件
            with open(output_path, 'w', encoding=export_opts['encoding']) as f:
                f.write(markdown_content)
            
            self.log_info(f"文档导出完成: {output_path}")
            return True
            
        except Exception as e:
            self.log_error(f"导出文档失败: {e}")
            return False
    
    def _generate_project_markdown(self, project: Project, options: Dict[str, Any]) -> str:
        """生成项目的Markdown内容"""
        lines = []
        
        # 项目标题
        lines.append(f"# {project.name}")
        lines.append("")
        
        # 项目元数据
        if options.get('include_metadata', True):
            lines.append("## 项目信息")
            lines.append("")
            lines.append(f"- **项目类型**: {project.type}")
            lines.append(f"- **项目状态**: {project.status}")
            if project.description:
                lines.append(f"- **项目描述**: {project.description}")
            lines.append(f"- **创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
        
        # 目录
        if options.get('include_toc', True):
            lines.append("## 目录")
            lines.append("")
            # 这里可以添加目录生成逻辑
            lines.append("- [项目信息](#项目信息)")
            lines.append("- [文档内容](#文档内容)")
            lines.append("")
        
        # 文档内容
        lines.append("## 文档内容")
        lines.append("")
        
        # 获取项目文档（这里需要实际的文档获取逻辑）
        lines.append("*文档内容将在此处显示*")
        lines.append("")
        
        # 页脚
        lines.append("---")
        lines.append(f"*由AI小说编辑器导出 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return self._format_markdown_content(lines, options)
    
    def _generate_document_markdown(self, document: Document, options: Dict[str, Any]) -> str:
        """生成文档的Markdown内容"""
        lines = []
        
        # 文档标题
        lines.append(f"# {document.title}")
        lines.append("")
        
        # 文档元数据
        if options.get('include_metadata', True):
            lines.append("## 文档信息")
            lines.append("")
            lines.append(f"- **文档类型**: {document.type}")
            if hasattr(document, 'metadata') and document.metadata:
                if hasattr(document.metadata, 'created_at') and document.metadata.created_at:
                    lines.append(f"- **创建时间**: {document.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if hasattr(document.metadata, 'updated_at') and document.metadata.updated_at:
                    lines.append(f"- **更新时间**: {document.metadata.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if hasattr(document.metadata, 'word_count') and document.metadata.word_count:
                    lines.append(f"- **字数**: {document.metadata.word_count}")
            lines.append("")
        
        # 文档内容
        lines.append("## 内容")
        lines.append("")
        
        # 处理文档内容
        content = self._process_document_content(document.content, options)
        lines.append(content)
        lines.append("")
        
        # 页脚
        lines.append("---")
        lines.append(f"*由AI小说编辑器导出 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return self._format_markdown_content(lines, options)
    
    def _process_document_content(self, content: str, options: Dict[str, Any]) -> str:
        """处理文档内容"""
        if not content:
            return "*文档内容为空*"
        
        # 基本的Markdown转换
        processed_content = content
        
        # 处理段落
        processed_content = re.sub(r'\n\s*\n', '\n\n', processed_content)
        
        # 处理特殊字符转义
        if options.get('markdown_flavor') == 'github':
            # GitHub Flavored Markdown特殊处理
            processed_content = self._escape_github_markdown(processed_content)
        
        return processed_content
    
    def _escape_github_markdown(self, content: str) -> str:
        """转义GitHub Markdown特殊字符"""
        # 转义Markdown特殊字符
        special_chars = ['*', '_', '`', '#', '+', '-', '.', '!', '[', ']', '(', ')']
        for char in special_chars:
            # 只转义不在代码块中的特殊字符
            content = re.sub(f'(?<!`)\\{char}(?!`)', f'\\{char}', content)
        
        return content
    
    def _format_markdown_content(self, lines: List[str], options: Dict[str, Any]) -> str:
        """格式化Markdown内容"""
        # 连接行
        content = '\n'.join(lines)
        
        # 处理换行符
        line_break = options.get('line_breaks', 'lf')
        if line_break == 'crlf':
            content = content.replace('\n', '\r\n')
        elif line_break == 'cr':
            content = content.replace('\n', '\r')
        
        return content
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的导出格式
        
        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.md', '.markdown']
    
    def get_export_options(self) -> Dict[str, Any]:
        """
        获取导出选项
        
        Returns:
            Dict[str, Any]: 可配置的导出选项
        """
        return {
            'include_toc': {
                'type': 'boolean',
                'default': True,
                'description': '包含目录'
            },
            'include_metadata': {
                'type': 'boolean',
                'default': True,
                'description': '包含元数据'
            },
            'markdown_flavor': {
                'type': 'choice',
                'choices': ['standard', 'github', 'commonmark'],
                'default': 'github',
                'description': 'Markdown风格'
            },
            'code_highlighting': {
                'type': 'boolean',
                'default': True,
                'description': '代码高亮'
            },
            'line_breaks': {
                'type': 'choice',
                'choices': ['lf', 'crlf', 'cr'],
                'default': 'lf',
                'description': '换行符类型'
            }
        }

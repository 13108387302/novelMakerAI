#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入导出模块

提供模块化的导入导出功能
"""

from .base import (
    IFormatHandler,
    BaseFormatHandler,
    IImportExportService,
    ExportOptions,
    ImportOptions,
    ExportResult,
    ImportResult
)

from .json_handler import JsonFormatHandler
from .text_handler import TextFormatHandler, MarkdownFormatHandler

# 可选的格式处理器（需要额外依赖）
try:
    from .docx_handler import DocxFormatHandler
    DOCX_HANDLER_AVAILABLE = True
except ImportError:
    DOCX_HANDLER_AVAILABLE = False

try:
    from .pdf_handler import PdfFormatHandler
    PDF_HANDLER_AVAILABLE = True
except ImportError:
    PDF_HANDLER_AVAILABLE = False

try:
    from .excel_handler import ExcelFormatHandler
    EXCEL_HANDLER_AVAILABLE = True
except ImportError:
    EXCEL_HANDLER_AVAILABLE = False

__all__ = [
    # 基础接口和类
    'IFormatHandler',
    'BaseFormatHandler',
    'IImportExportService',
    'ExportOptions',
    'ImportOptions',
    'ExportResult',
    'ImportResult',

    # 格式处理器
    'JsonFormatHandler',
    'TextFormatHandler',
    'MarkdownFormatHandler',
]

# 添加可选的处理器到导出列表
if DOCX_HANDLER_AVAILABLE:
    __all__.append('DocxFormatHandler')

if PDF_HANDLER_AVAILABLE:
    __all__.append('PdfFormatHandler')

if EXCEL_HANDLER_AVAILABLE:
    __all__.append('ExcelFormatHandler')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档仓储接口

定义文档数据访问的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.domain.entities.document import Document, DocumentType, DocumentStatus


class IDocumentRepository(ABC):
    """
    文档仓储接口

    定义文档数据访问的抽象接口，遵循仓储模式。
    提供文档的CRUD操作和多维度查询功能。

    实现方式：
    - 使用抽象基类定义接口契约
    - 支持异步操作提高性能
    - 提供多种查询方式（项目、类型、状态等）
    - 支持文档的完整生命周期管理
    """

    @abstractmethod
    async def save(self, document: Document) -> bool:
        """
        保存文档到存储介质

        Args:
            document: 要保存的文档实例

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        pass

    @abstractmethod
    async def load(self, document_id: str) -> Optional[Document]:
        """
        根据文档ID加载文档

        Args:
            document_id: 文档唯一标识符

        Returns:
            Optional[Document]: 文档实例，不存在时返回None
        """
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """
        删除指定文档

        Args:
            document_id: 文档唯一标识符

        Returns:
            bool: 删除成功返回True，失败返回False
        """
        pass

    @abstractmethod
    async def exists(self, document_id: str) -> bool:
        """
        检查文档是否存在

        Args:
            document_id: 文档唯一标识符

        Returns:
            bool: 存在返回True，不存在返回False
        """
        pass

    @abstractmethod
    async def list_by_project(self, project_id: str) -> List[Document]:
        """
        列出指定项目中的所有文档

        Args:
            project_id: 项目唯一标识符

        Returns:
            List[Document]: 项目中的文档列表
        """
        pass

    @abstractmethod
    async def list_by_type(
        self,
        document_type: DocumentType,
        project_id: Optional[str] = None
    ) -> List[Document]:
        """
        根据文档类型列出文档

        Args:
            document_type: 文档类型
            project_id: 项目ID，可选，用于限制查询范围

        Returns:
            List[Document]: 指定类型的文档列表
        """
        pass
    
    @abstractmethod
    async def list_by_status(
        self, 
        status: DocumentStatus, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """根据状态列出文档"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """搜索文档"""
        pass
    
    @abstractmethod
    async def search_content(
        self, 
        query: str, 
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索文档内容"""
        pass
    
    @abstractmethod
    async def get_recent_documents(
        self, 
        limit: int = 10, 
        project_id: Optional[str] = None
    ) -> List[Document]:
        """获取最近编辑的文档"""
        pass
    
    @abstractmethod
    async def update_content(self, document_id: str, content: str) -> bool:
        """更新文档内容"""
        pass
    
    @abstractmethod
    async def update_metadata(
        self, 
        document_id: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """更新文档元数据"""
        pass
    
    @abstractmethod
    async def get_word_count(self, document_id: str) -> int:
        """获取文档字数"""
        pass
    
    @abstractmethod
    async def get_statistics(self, document_id: str) -> Dict[str, Any]:
        """获取文档统计信息"""
        pass


class IDocumentVersionRepository(ABC):
    """文档版本仓储接口"""

    @abstractmethod
    async def create_version(
        self,
        document_id: str,
        content: str,
        comment: str = ""
    ) -> str:
        """创建文档版本"""
        pass

    @abstractmethod
    async def list_versions(self, document_id: str) -> List[Dict[str, Any]]:
        """列出文档版本"""
        pass

    @abstractmethod
    async def get_version(
        self,
        document_id: str,
        version_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取指定版本"""
        pass

    @abstractmethod
    async def delete_version(self, document_id: str, version_id: str) -> bool:
        """删除文档版本"""
        pass

    @abstractmethod
    async def get_version_diff(
        self,
        document_id: str,
        version1_id: str,
        version2_id: str
    ) -> Dict[str, Any]:
        """获取版本差异"""
        pass

    @abstractmethod
    async def restore_version(
        self,
        document_id: str,
        version_id: str
    ) -> bool:
        """恢复到指定版本"""
        pass

    @abstractmethod
    async def cleanup_old_versions(
        self,
        document_id: str,
        keep_count: int = 10
    ) -> int:
        """清理旧版本"""
        pass


class IDocumentTemplateRepository(ABC):
    """文档模板仓储接口"""
    
    @abstractmethod
    async def list_templates(
        self, 
        document_type: Optional[DocumentType] = None
    ) -> List[Dict[str, Any]]:
        """列出文档模板"""
        pass
    
    @abstractmethod
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取文档模板"""
        pass
    
    @abstractmethod
    async def create_document_from_template(
        self, 
        template_id: str, 
        title: str, 
        project_id: Optional[str] = None
    ) -> Optional[Document]:
        """从模板创建文档"""
        pass
    
    @abstractmethod
    async def save_as_template(
        self, 
        document_id: str, 
        template_name: str, 
        template_description: str
    ) -> bool:
        """将文档保存为模板"""
        pass
    
    @abstractmethod
    async def delete_template(self, template_id: str) -> bool:
        """删除文档模板"""
        pass


class IDocumentExportRepository(ABC):
    """文档导出仓储接口"""
    
    @abstractmethod
    async def export_document(
        self, 
        document_id: str, 
        export_path: Path, 
        export_format: str
    ) -> bool:
        """导出文档"""
        pass
    
    @abstractmethod
    async def export_multiple_documents(
        self, 
        document_ids: List[str], 
        export_path: Path, 
        export_format: str
    ) -> bool:
        """批量导出文档"""
        pass
    
    @abstractmethod
    async def import_document(
        self, 
        import_path: Path, 
        import_format: str, 
        project_id: Optional[str] = None
    ) -> Optional[Document]:
        """导入文档"""
        pass
    
    @abstractmethod
    async def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        pass


class IDocumentAnalysisRepository(ABC):
    """文档分析仓储接口"""
    
    @abstractmethod
    async def save_analysis_result(
        self, 
        document_id: str, 
        analysis_type: str, 
        result: Dict[str, Any]
    ) -> bool:
        """保存分析结果"""
        pass
    
    @abstractmethod
    async def load_analysis_result(
        self, 
        document_id: str, 
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """加载分析结果"""
        pass
    
    @abstractmethod
    async def list_analysis_types(self, document_id: str) -> List[str]:
        """列出文档的分析类型"""
        pass
    
    @abstractmethod
    async def delete_analysis_result(
        self, 
        document_id: str, 
        analysis_type: str
    ) -> bool:
        """删除分析结果"""
        pass
    
    @abstractmethod
    async def get_document_insights(self, document_id: str) -> Dict[str, Any]:
        """获取文档洞察"""
        pass

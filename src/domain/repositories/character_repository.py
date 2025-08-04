#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色仓储接口

定义角色数据访问的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Set

from src.domain.entities.character import Character, CharacterRole, RelationshipType


class ICharacterRepository(ABC):
    """角色仓储接口"""
    
    @abstractmethod
    async def save(self, character: Character) -> bool:
        """保存角色"""
        pass
    
    @abstractmethod
    async def load(self, character_id: str) -> Optional[Character]:
        """根据ID加载角色"""
        pass
    
    @abstractmethod
    async def delete(self, character_id: str) -> bool:
        """删除角色"""
        pass
    
    @abstractmethod
    async def exists(self, character_id: str) -> bool:
        """检查角色是否存在"""
        pass
    
    @abstractmethod
    async def list_by_project(self, project_id: str) -> List[Character]:
        """列出项目中的所有角色"""
        pass
    
    @abstractmethod
    async def list_by_role(
        self, 
        role: CharacterRole, 
        project_id: Optional[str] = None
    ) -> List[Character]:
        """根据角色定位列出角色"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        project_id: Optional[str] = None
    ) -> List[Character]:
        """搜索角色"""
        pass
    
    @abstractmethod
    async def find_by_name(
        self, 
        name: str, 
        project_id: Optional[str] = None
    ) -> Optional[Character]:
        """根据名称查找角色"""
        pass
    
    @abstractmethod
    async def get_character_relationships(
        self, 
        character_id: str
    ) -> Dict[str, Any]:
        """获取角色关系网络"""
        pass
    
    @abstractmethod
    async def get_characters_by_relationship(
        self, 
        character_id: str, 
        relationship_type: RelationshipType
    ) -> List[Character]:
        """根据关系类型获取相关角色"""
        pass
    
    @abstractmethod
    async def update_character_statistics(
        self, 
        character_id: str, 
        statistics: Dict[str, Any]
    ) -> bool:
        """更新角色统计信息"""
        pass


class ICharacterAnalysisRepository(ABC):
    """角色分析仓储接口"""
    
    @abstractmethod
    async def save_analysis_result(
        self, 
        character_id: str, 
        analysis_type: str, 
        result: Dict[str, Any]
    ) -> bool:
        """保存角色分析结果"""
        pass
    
    @abstractmethod
    async def load_analysis_result(
        self, 
        character_id: str, 
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """加载角色分析结果"""
        pass
    
    @abstractmethod
    async def get_character_consistency_report(
        self, 
        character_id: str
    ) -> Dict[str, Any]:
        """获取角色一致性报告"""
        pass
    
    @abstractmethod
    async def get_character_development_timeline(
        self, 
        character_id: str
    ) -> List[Dict[str, Any]]:
        """获取角色发展时间线"""
        pass
    
    @abstractmethod
    async def analyze_character_relationships(
        self, 
        project_id: str
    ) -> Dict[str, Any]:
        """分析项目中的角色关系网络"""
        pass


class ICharacterAppearanceRepository(ABC):
    """角色出场仓储接口"""
    
    @abstractmethod
    async def record_appearance(
        self, 
        character_id: str, 
        document_id: str, 
        chapter_number: Optional[int] = None,
        scene_description: str = "",
        importance: int = 5
    ) -> bool:
        """记录角色出场"""
        pass
    
    @abstractmethod
    async def get_appearances_by_character(
        self, 
        character_id: str
    ) -> List[Dict[str, Any]]:
        """获取角色的所有出场记录"""
        pass
    
    @abstractmethod
    async def get_appearances_by_document(
        self, 
        document_id: str
    ) -> List[Dict[str, Any]]:
        """获取文档中的角色出场记录"""
        pass
    
    @abstractmethod
    async def get_appearances_by_chapter(
        self, 
        project_id: str, 
        chapter_number: int
    ) -> List[Dict[str, Any]]:
        """获取章节中的角色出场记录"""
        pass
    
    @abstractmethod
    async def get_character_appearance_statistics(
        self, 
        character_id: str
    ) -> Dict[str, Any]:
        """获取角色出场统计"""
        pass
    
    @abstractmethod
    async def detect_character_mentions(
        self, 
        document_id: str, 
        content: str
    ) -> List[Dict[str, Any]]:
        """检测文档中的角色提及"""
        pass


class ICharacterTemplateRepository(ABC):
    """角色模板仓储接口"""
    
    @abstractmethod
    async def list_templates(self) -> List[Dict[str, Any]]:
        """列出角色模板"""
        pass
    
    @abstractmethod
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取角色模板"""
        pass
    
    @abstractmethod
    async def create_character_from_template(
        self, 
        template_id: str, 
        character_name: str, 
        project_id: str
    ) -> Optional[Character]:
        """从模板创建角色"""
        pass
    
    @abstractmethod
    async def save_as_template(
        self, 
        character_id: str, 
        template_name: str, 
        template_description: str
    ) -> bool:
        """将角色保存为模板"""
        pass
    
    @abstractmethod
    async def delete_template(self, template_id: str) -> bool:
        """删除角色模板"""
        pass


class ICharacterRelationshipRepository(ABC):
    """角色关系仓储接口"""
    
    @abstractmethod
    async def create_relationship(
        self, 
        character1_id: str, 
        character2_id: str, 
        relationship_type: RelationshipType,
        description: str,
        intensity: int = 5,
        is_mutual: bool = True
    ) -> bool:
        """创建角色关系"""
        pass
    
    @abstractmethod
    async def update_relationship(
        self, 
        character1_id: str, 
        character2_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """更新角色关系"""
        pass
    
    @abstractmethod
    async def delete_relationship(
        self, 
        character1_id: str, 
        character2_id: str
    ) -> bool:
        """删除角色关系"""
        pass
    
    @abstractmethod
    async def get_relationship_network(
        self, 
        project_id: str
    ) -> Dict[str, Any]:
        """获取项目的角色关系网络"""
        pass
    
    @abstractmethod
    async def find_relationship_path(
        self, 
        character1_id: str, 
        character2_id: str
    ) -> List[Dict[str, Any]]:
        """查找角色间的关系路径"""
        pass
    
    @abstractmethod
    async def get_relationship_suggestions(
        self, 
        character_id: str
    ) -> List[Dict[str, Any]]:
        """获取角色关系建议"""
        pass
    
    @abstractmethod
    async def validate_relationship_consistency(
        self, 
        project_id: str
    ) -> List[Dict[str, Any]]:
        """验证角色关系一致性"""
        pass

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色实体

定义小说角色的核心业务逻辑和规则
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable
from uuid import uuid4

# 角色实体常量
DEFAULT_SPECIES = "人类"
MIN_INTENSITY = 1
MAX_INTENSITY = 10
DEFAULT_INTENSITY = 5
MIN_AGE = 0
MAX_AGE = 1000
DEFAULT_RELATIONSHIP_LIMIT = 5


class CharacterRole(Enum):
    """
    角色定位枚举

    定义角色在故事中的重要性和功能定位。
    用于角色管理和故事结构分析。

    Values:
        PROTAGONIST: 主角，故事的核心人物
        DEUTERAGONIST: 第二主角，重要的支持角色
        ANTAGONIST: 反派，与主角对立的角色
        SUPPORTING: 配角，支持主要情节的角色
        MINOR: 次要角色，偶尔出现的角色
        CAMEO: 客串，短暂出现的角色
    """
    PROTAGONIST = "protagonist"       # 主角
    DEUTERAGONIST = "deuteragonist"  # 第二主角
    ANTAGONIST = "antagonist"         # 反派
    SUPPORTING = "supporting"         # 配角
    MINOR = "minor"                   # 次要角色
    CAMEO = "cameo"                   # 客串


class RelationshipType(Enum):
    """
    关系类型枚举

    定义角色之间的关系类型，用于构建角色关系网络。

    Values:
        FAMILY: 家庭关系，血缘或婚姻关系
        ROMANTIC: 恋爱关系，情侣或夫妻关系
        FRIENDSHIP: 友谊关系，朋友关系
        PROFESSIONAL: 工作关系，同事或业务关系
        ENEMY: 敌对关系，敌人或竞争对手
        MENTOR: 师生关系，指导与被指导关系
        ALLY: 盟友关系，合作伙伴关系
        NEUTRAL: 中性关系，无特殊关系
    """
    FAMILY = "family"                 # 家庭关系
    ROMANTIC = "romantic"             # 恋爱关系
    FRIENDSHIP = "friendship"         # 友谊关系
    PROFESSIONAL = "professional"     # 工作关系
    ENEMY = "enemy"                   # 敌对关系
    MENTOR = "mentor"                 # 师生关系
    ALLY = "ally"                     # 盟友关系
    NEUTRAL = "neutral"               # 中性关系


@dataclass
class PhysicalAppearance:
    """
    外貌描述数据类

    记录角色的外貌特征信息，包括身高、体重、发色、眼色等。
    提供添加和管理外貌特征的方法。

    Attributes:
        height: 身高描述
        weight: 体重描述
        hair_color: 发色
        eye_color: 眼色
        skin_tone: 肤色
        build: 体型描述
        distinguishing_features: 显著特征列表
        clothing_style: 服装风格
    """
    height: Optional[str] = None
    weight: Optional[str] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    build: Optional[str] = None
    distinguishing_features: List[str] = field(default_factory=list)
    clothing_style: Optional[str] = None
    
    def add_distinguishing_feature(self, feature: str) -> None:
        """添加特征"""
        if feature.strip() and feature not in self.distinguishing_features:
            self.distinguishing_features.append(feature.strip())
    
    def remove_distinguishing_feature(self, feature: str) -> None:
        """移除特征"""
        if feature in self.distinguishing_features:
            self.distinguishing_features.remove(feature)


@dataclass
class PersonalityTraits:
    """性格特征"""
    core_traits: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    fears: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    
    def add_trait(self, category: str, trait: str) -> None:
        """添加特征"""
        trait = trait.strip()
        if not trait:
            return
        
        trait_list = getattr(self, category, None)
        if isinstance(trait_list, list) and trait not in trait_list:
            trait_list.append(trait)
    
    def remove_trait(self, category: str, trait: str) -> None:
        """移除特征"""
        trait_list = getattr(self, category, None)
        if isinstance(trait_list, list) and trait in trait_list:
            trait_list.remove(trait)


@dataclass
class Background:
    """背景信息"""
    birthplace: Optional[str] = None
    birthdate: Optional[str] = None
    family_background: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    social_status: Optional[str] = None
    significant_events: List[str] = field(default_factory=list)
    
    def add_significant_event(self, event: str) -> None:
        """添加重要事件"""
        if event.strip() and event not in self.significant_events:
            self.significant_events.append(event.strip())


@dataclass
class CharacterRelationship:
    """角色关系"""
    target_character_id: str
    relationship_type: RelationshipType
    description: str
    intensity: int = DEFAULT_INTENSITY  # 关系强度
    is_mutual: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not MIN_INTENSITY <= self.intensity <= MAX_INTENSITY:
            raise ValueError(f"关系强度必须在{MIN_INTENSITY}-{MAX_INTENSITY}之间")


@dataclass
class CharacterAppearance:
    """角色出场记录"""
    document_id: str
    chapter_number: Optional[int] = None
    scene_description: str = ""
    importance: int = DEFAULT_INTENSITY  # 在该场景中的重要性
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CharacterDevelopment:
    """角色发展轨迹"""
    stage: str  # 发展阶段
    description: str
    key_events: List[str] = field(default_factory=list)
    personality_changes: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class Character:
    """
    角色实体

    表示小说中的角色，包含完整的角色信息和行为。
    支持角色关系管理、出场记录、发展轨迹等功能。
    """

    def __init__(
        self,
        character_id: Optional[str] = None,
        name: str = "",
        role: CharacterRole = CharacterRole.SUPPORTING,
        project_id: Optional[str] = None,
        event_publisher: Optional[Callable] = None
    ):
        self.id = character_id or str(uuid4())
        self.name = name
        self.role = role
        self.project_id = project_id
        self._event_publisher = event_publisher
        
        # 基本信息
        self.nickname: Optional[str] = None
        self.age: Optional[int] = None
        self.gender: Optional[str] = None
        self.species: str = DEFAULT_SPECIES
        
        # 详细信息
        self.appearance = PhysicalAppearance()
        self.personality = PersonalityTraits()
        self.background = Background()
        
        # 关系网络
        self._relationships: Dict[str, CharacterRelationship] = {}
        
        # 出场记录
        self._appearances: List[CharacterAppearance] = []
        
        # 发展轨迹
        self._development_stages: List[CharacterDevelopment] = []
        
        # 统计信息
        self.total_appearances: int = 0
        self.total_words_spoken: int = 0
        self.first_appearance_chapter: Optional[int] = None
        self.last_appearance_chapter: Optional[int] = None
        
        # 时间戳
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def _validate_string(self, value: str, field_name: str) -> bool:
        """验证字符串字段"""
        return value and value.strip()

    def _validate_intensity(self, intensity: int) -> bool:
        """验证强度值"""
        return MIN_INTENSITY <= intensity <= MAX_INTENSITY
    
    def update_name(self, new_name: str) -> None:
        """更新角色名称"""
        if not self._validate_string(new_name, "角色名称"):
            raise ValueError("角色名称不能为空")

        old_name = self.name
        self.name = new_name.strip()
        self.updated_at = datetime.now()

        # 通过回调发布事件，避免循环导入
        if self._event_publisher:
            try:
                self._event_publisher("character_name_changed", {
                    "character_id": self.id,
                    "old_name": old_name,
                    "new_name": self.name
                })
            except Exception:
                pass  # 事件发布失败不应影响业务逻辑
    
    def update_role(self, new_role: CharacterRole) -> None:
        """更新角色定位"""
        if new_role == self.role:
            return

        old_role = self.role
        self.role = new_role
        self.updated_at = datetime.now()

        # 通过回调发布事件，避免循环导入
        if self._event_publisher:
            try:
                self._event_publisher("character_role_changed", {
                    "character_id": self.id,
                    "old_role": old_role.value,
                    "new_role": new_role.value
                })
            except Exception:
                pass  # 事件发布失败不应影响业务逻辑
    
    def add_relationship(
        self,
        target_character_id: str,
        relationship_type: RelationshipType,
        description: str,
        intensity: int = DEFAULT_INTENSITY,
        is_mutual: bool = True
    ) -> None:
        """添加角色关系"""
        if not target_character_id or not target_character_id.strip():
            raise ValueError("目标角色ID不能为空")

        if target_character_id == self.id:
            raise ValueError("不能与自己建立关系")

        if not isinstance(relationship_type, RelationshipType):
            raise ValueError("关系类型必须是RelationshipType枚举")

        if not self._validate_intensity(intensity):
            raise ValueError(f"关系强度必须在{MIN_INTENSITY}-{MAX_INTENSITY}之间")

        relationship = CharacterRelationship(
            target_character_id=target_character_id,
            relationship_type=relationship_type,
            description=description.strip() if description else "",
            intensity=intensity,
            is_mutual=is_mutual
        )

        self._relationships[target_character_id] = relationship
        self.updated_at = datetime.now()
    
    def remove_relationship(self, target_character_id: str) -> None:
        """移除角色关系"""
        if target_character_id in self._relationships:
            del self._relationships[target_character_id]
            self.updated_at = datetime.now()
    
    def get_relationship(self, target_character_id: str) -> Optional[CharacterRelationship]:
        """获取与指定角色的关系"""
        return self._relationships.get(target_character_id)
    
    def get_relationships_by_type(self, relationship_type: RelationshipType) -> List[CharacterRelationship]:
        """获取指定类型的所有关系"""
        return [
            rel for rel in self._relationships.values()
            if rel.relationship_type == relationship_type
        ]
    
    def add_appearance(
        self,
        document_id: str,
        chapter_number: Optional[int] = None,
        scene_description: str = "",
        importance: int = DEFAULT_INTENSITY
    ) -> None:
        """添加出场记录"""
        if not document_id or not document_id.strip():
            raise ValueError("文档ID不能为空")

        if not self._validate_intensity(importance):
            raise ValueError(f"重要性值必须在{MIN_INTENSITY}-{MAX_INTENSITY}之间")

        if chapter_number is not None and chapter_number < 0:
            raise ValueError("章节号不能为负数")

        appearance = CharacterAppearance(
            document_id=document_id.strip(),
            chapter_number=chapter_number,
            scene_description=scene_description.strip() if scene_description else "",
            importance=importance
        )

        self._appearances.append(appearance)
        self.total_appearances += 1

        # 更新首次和最后出场章节
        if chapter_number is not None:
            if self.first_appearance_chapter is None or chapter_number < self.first_appearance_chapter:
                self.first_appearance_chapter = chapter_number
            if self.last_appearance_chapter is None or chapter_number > self.last_appearance_chapter:
                self.last_appearance_chapter = chapter_number

        self.updated_at = datetime.now()
    
    def add_development_stage(
        self,
        stage: str,
        description: str,
        key_events: Optional[List[str]] = None,
        personality_changes: Optional[List[str]] = None
    ) -> None:
        """添加发展阶段"""
        development = CharacterDevelopment(
            stage=stage,
            description=description,
            key_events=key_events or [],
            personality_changes=personality_changes or []
        )
        
        self._development_stages.append(development)
        self.updated_at = datetime.now()
    
    def get_appearances_in_chapter(self, chapter_number: int) -> List[CharacterAppearance]:
        """获取在指定章节的出场记录"""
        return [
            app for app in self._appearances
            if app.chapter_number == chapter_number
        ]
    
    def get_development_timeline(self) -> List[CharacterDevelopment]:
        """获取发展时间线"""
        return sorted(self._development_stages, key=lambda d: d.timestamp)
    
    def calculate_relationship_network_size(self) -> int:
        """计算关系网络规模"""
        return len(self._relationships)
    
    def get_most_important_relationships(self, limit: int = DEFAULT_RELATIONSHIP_LIMIT) -> List[CharacterRelationship]:
        """获取最重要的关系"""
        return sorted(
            self._relationships.values(),
            key=lambda r: r.intensity,
            reverse=True
        )[:limit]
    
    def validate(self) -> List[str]:
        """验证角色数据"""
        errors = []

        # 验证基本信息
        if not self._validate_string(self.name, "角色名称"):
            errors.append("角色名称不能为空")

        if self.age is not None and (self.age < MIN_AGE or self.age > MAX_AGE):
            errors.append(f"角色年龄必须在{MIN_AGE}-{MAX_AGE}范围内")

        # 验证关系的一致性
        for target_id, rel in self._relationships.items():
            if not self._validate_intensity(rel.intensity):
                errors.append(f"与角色 {target_id} 的关系强度无效")

            if target_id == self.id:
                errors.append("不能与自己建立关系")

            if not isinstance(rel.relationship_type, RelationshipType):
                errors.append(f"与角色 {target_id} 的关系类型无效")

        # 验证出场记录
        for app in self._appearances:
            if not self._validate_intensity(app.importance):
                errors.append(f"出场记录中的重要性值无效: {app.importance}")

        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "nickname": self.nickname,
            "role": self.role.value,
            "age": self.age,
            "gender": self.gender,
            "species": self.species,
            "project_id": self.project_id,
            "appearance": {
                "height": self.appearance.height,
                "weight": self.appearance.weight,
                "hair_color": self.appearance.hair_color,
                "eye_color": self.appearance.eye_color,
                "skin_tone": self.appearance.skin_tone,
                "build": self.appearance.build,
                "distinguishing_features": self.appearance.distinguishing_features,
                "clothing_style": self.appearance.clothing_style,
            },
            "personality": {
                "core_traits": self.personality.core_traits,
                "strengths": self.personality.strengths,
                "weaknesses": self.personality.weaknesses,
                "fears": self.personality.fears,
                "motivations": self.personality.motivations,
                "values": self.personality.values,
            },
            "background": {
                "birthplace": self.background.birthplace,
                "birthdate": self.background.birthdate,
                "family_background": self.background.family_background,
                "education": self.background.education,
                "occupation": self.background.occupation,
                "social_status": self.background.social_status,
                "significant_events": self.background.significant_events,
            },
            "relationships": {
                char_id: {
                    "target_character_id": rel.target_character_id,
                    "relationship_type": rel.relationship_type.value,
                    "description": rel.description,
                    "intensity": rel.intensity,
                    "is_mutual": rel.is_mutual,
                    "created_at": rel.created_at.isoformat(),
                }
                for char_id, rel in self._relationships.items()
            },
            "appearances": [
                {
                    "document_id": app.document_id,
                    "chapter_number": app.chapter_number,
                    "scene_description": app.scene_description,
                    "importance": app.importance,
                    "timestamp": app.timestamp.isoformat(),
                }
                for app in self._appearances
            ],
            "development_stages": [
                {
                    "stage": dev.stage,
                    "description": dev.description,
                    "key_events": dev.key_events,
                    "personality_changes": dev.personality_changes,
                    "timestamp": dev.timestamp.isoformat(),
                }
                for dev in self._development_stages
            ],
            "statistics": {
                "total_appearances": self.total_appearances,
                "total_words_spoken": self.total_words_spoken,
                "first_appearance_chapter": self.first_appearance_chapter,
                "last_appearance_chapter": self.last_appearance_chapter,
                "relationship_network_size": self.calculate_relationship_network_size(),
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """从字典创建角色"""
        character = cls(
            character_id=data.get("id"),
            name=data.get("name", ""),
            role=CharacterRole(data.get("role", "supporting")),
            project_id=data.get("project_id")
        )
        
        # 基本信息
        character.nickname = data.get("nickname")
        character.age = data.get("age")
        character.gender = data.get("gender")
        character.species = data.get("species", DEFAULT_SPECIES)
        
        # 外貌信息
        appearance_data = data.get("appearance", {})
        character.appearance = PhysicalAppearance(
            height=appearance_data.get("height"),
            weight=appearance_data.get("weight"),
            hair_color=appearance_data.get("hair_color"),
            eye_color=appearance_data.get("eye_color"),
            skin_tone=appearance_data.get("skin_tone"),
            build=appearance_data.get("build"),
            distinguishing_features=appearance_data.get("distinguishing_features", []),
            clothing_style=appearance_data.get("clothing_style"),
        )
        
        # 性格信息
        personality_data = data.get("personality", {})
        character.personality = PersonalityTraits(
            core_traits=personality_data.get("core_traits", []),
            strengths=personality_data.get("strengths", []),
            weaknesses=personality_data.get("weaknesses", []),
            fears=personality_data.get("fears", []),
            motivations=personality_data.get("motivations", []),
            values=personality_data.get("values", []),
        )
        
        # 背景信息
        background_data = data.get("background", {})
        character.background = Background(
            birthplace=background_data.get("birthplace"),
            birthdate=background_data.get("birthdate"),
            family_background=background_data.get("family_background"),
            education=background_data.get("education"),
            occupation=background_data.get("occupation"),
            social_status=background_data.get("social_status"),
            significant_events=background_data.get("significant_events", []),
        )
        
        # 关系信息
        relationships_data = data.get("relationships", {})
        for char_id, rel_data in relationships_data.items():
            try:
                if not isinstance(rel_data, dict):
                    continue

                created_at = datetime.now()
                if "created_at" in rel_data:
                    try:
                        created_at = datetime.fromisoformat(rel_data["created_at"])
                    except (ValueError, TypeError):
                        pass

                character._relationships[char_id] = CharacterRelationship(
                    target_character_id=rel_data.get("target_character_id", ""),
                    relationship_type=RelationshipType(rel_data.get("relationship_type", "neutral")),
                    description=rel_data.get("description", ""),
                    intensity=rel_data.get("intensity", DEFAULT_INTENSITY),
                    is_mutual=rel_data.get("is_mutual", True),
                    created_at=created_at,
                )
            except (ValueError, KeyError, TypeError) as e:
                # 跳过无效的关系数据
                continue
        
        # 出场记录
        appearances_data = data.get("appearances", [])
        for app_data in appearances_data:
            try:
                if not isinstance(app_data, dict):
                    continue

                timestamp = datetime.now()
                if "timestamp" in app_data:
                    try:
                        timestamp = datetime.fromisoformat(app_data["timestamp"])
                    except (ValueError, TypeError):
                        pass

                character._appearances.append(CharacterAppearance(
                    document_id=app_data.get("document_id", ""),
                    chapter_number=app_data.get("chapter_number"),
                    scene_description=app_data.get("scene_description", ""),
                    importance=app_data.get("importance", DEFAULT_INTENSITY),
                    timestamp=timestamp,
                ))
            except (ValueError, KeyError, TypeError):
                # 跳过无效的出场记录
                continue

        # 发展阶段
        development_data = data.get("development_stages", [])
        for dev_data in development_data:
            try:
                if not isinstance(dev_data, dict):
                    continue

                timestamp = datetime.now()
                if "timestamp" in dev_data:
                    try:
                        timestamp = datetime.fromisoformat(dev_data["timestamp"])
                    except (ValueError, TypeError):
                        pass

                character._development_stages.append(CharacterDevelopment(
                    stage=dev_data.get("stage", ""),
                    description=dev_data.get("description", ""),
                    key_events=dev_data.get("key_events", []),
                    personality_changes=dev_data.get("personality_changes", []),
                    timestamp=timestamp,
                ))
            except (ValueError, KeyError, TypeError):
                # 跳过无效的发展阶段数据
                continue
        
        # 统计信息
        stats_data = data.get("statistics", {})
        character.total_appearances = stats_data.get("total_appearances", 0)
        character.total_words_spoken = stats_data.get("total_words_spoken", 0)
        character.first_appearance_chapter = stats_data.get("first_appearance_chapter")
        character.last_appearance_chapter = stats_data.get("last_appearance_chapter")
        
        # 时间戳（安全处理）
        try:
            if data.get("created_at"):
                character.created_at = datetime.fromisoformat(data["created_at"])
        except (ValueError, TypeError):
            pass  # 使用默认时间戳

        try:
            if data.get("updated_at"):
                character.updated_at = datetime.fromisoformat(data["updated_at"])
        except (ValueError, TypeError):
            pass  # 使用默认时间戳
        
        return character

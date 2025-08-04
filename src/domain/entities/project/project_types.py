#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目类型和枚举

定义项目相关的枚举类型
"""

from enum import Enum


class ProjectStatus(Enum):
    """项目状态"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 活跃
    COMPLETED = "completed"   # 完成
    ARCHIVED = "archived"     # 归档
    DELETED = "deleted"       # 已删除

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            self.DRAFT: "草稿",
            self.ACTIVE: "活跃",
            self.COMPLETED: "完成",
            self.ARCHIVED: "归档",
            self.DELETED: "已删除"
        }
        return names.get(self, self.value)

    @property
    def is_active_state(self) -> bool:
        """是否为活跃状态"""
        return self in [self.DRAFT, self.ACTIVE]

    @property
    def is_final_state(self) -> bool:
        """是否为最终状态"""
        return self in [self.COMPLETED, self.ARCHIVED, self.DELETED]


class ProjectType(Enum):
    """项目类型"""
    NOVEL = "novel"           # 长篇小说
    SHORT_STORY = "short_story"  # 短篇小说
    NOVELLA = "novella"       # 中篇小说
    SCRIPT = "script"         # 剧本
    POETRY = "poetry"         # 诗歌
    ESSAY = "essay"           # 散文
    OTHER = "other"           # 其他

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            self.NOVEL: "长篇小说",
            self.SHORT_STORY: "短篇小说",
            self.NOVELLA: "中篇小说",
            self.SCRIPT: "剧本",
            self.POETRY: "诗歌",
            self.ESSAY: "散文",
            self.OTHER: "其他"
        }
        return names.get(self, self.value)

    @property
    def typical_word_count_range(self) -> tuple[int, int]:
        """典型字数范围"""
        ranges = {
            self.NOVEL: (80000, 200000),
            self.SHORT_STORY: (1000, 10000),
            self.NOVELLA: (20000, 80000),
            self.SCRIPT: (15000, 30000),
            self.POETRY: (100, 5000),
            self.ESSAY: (1000, 20000),
            self.OTHER: (0, 1000000)
        }
        return ranges.get(self, (0, 1000000))

    @property
    def default_target_word_count(self) -> int:
        """默认目标字数"""
        min_count, max_count = self.typical_word_count_range
        # 返回范围的中位数
        return (min_count + max_count) // 2


class ProjectPriority(Enum):
    """项目优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            self.LOW: "低",
            self.NORMAL: "普通",
            self.HIGH: "高",
            self.URGENT: "紧急"
        }
        return names.get(self, self.value)

    @property
    def sort_order(self) -> int:
        """排序顺序"""
        orders = {
            self.URGENT: 4,
            self.HIGH: 3,
            self.NORMAL: 2,
            self.LOW: 1
        }
        return orders.get(self, 0)


class ProjectVisibility(Enum):
    """项目可见性"""
    PRIVATE = "private"       # 私有
    SHARED = "shared"         # 共享
    PUBLIC = "public"         # 公开

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            self.PRIVATE: "私有",
            self.SHARED: "共享",
            self.PUBLIC: "公开"
        }
        return names.get(self, self.value)


class ProjectLanguage(Enum):
    """项目语言"""
    ZH_CN = "zh_CN"          # 简体中文
    ZH_TW = "zh_TW"          # 繁体中文
    EN_US = "en_US"          # 美式英语
    EN_GB = "en_GB"          # 英式英语
    JA_JP = "ja_JP"          # 日语
    KO_KR = "ko_KR"          # 韩语
    FR_FR = "fr_FR"          # 法语
    DE_DE = "de_DE"          # 德语
    ES_ES = "es_ES"          # 西班牙语
    RU_RU = "ru_RU"          # 俄语

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            self.ZH_CN: "简体中文",
            self.ZH_TW: "繁体中文",
            self.EN_US: "美式英语",
            self.EN_GB: "英式英语",
            self.JA_JP: "日语",
            self.KO_KR: "韩语",
            self.FR_FR: "法语",
            self.DE_DE: "德语",
            self.ES_ES: "西班牙语",
            self.RU_RU: "俄语"
        }
        return names.get(self, self.value)

    @property
    def is_cjk(self) -> bool:
        """是否为中日韩语言"""
        return self in [self.ZH_CN, self.ZH_TW, self.JA_JP, self.KO_KR]

    @property
    def is_rtl(self) -> bool:
        """是否为从右到左的语言"""
        # 目前支持的语言中没有RTL语言，但为将来扩展预留
        return False


# 常用的项目类型组合
FICTION_TYPES = [ProjectType.NOVEL, ProjectType.SHORT_STORY, ProjectType.NOVELLA]
NON_FICTION_TYPES = [ProjectType.ESSAY, ProjectType.OTHER]
CREATIVE_TYPES = [ProjectType.POETRY, ProjectType.SCRIPT]

# 状态转换规则
VALID_STATUS_TRANSITIONS = {
    ProjectStatus.DRAFT: [ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED, ProjectStatus.DELETED],
    ProjectStatus.ACTIVE: [ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED, ProjectStatus.DELETED],
    ProjectStatus.COMPLETED: [ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED, ProjectStatus.DELETED],
    ProjectStatus.ARCHIVED: [ProjectStatus.ACTIVE, ProjectStatus.DELETED],
    ProjectStatus.DELETED: []  # 删除状态不能转换到其他状态
}


def can_transition_status(from_status: ProjectStatus, to_status: ProjectStatus) -> bool:
    """检查状态转换是否有效"""
    return to_status in VALID_STATUS_TRANSITIONS.get(from_status, [])


def get_next_valid_statuses(current_status: ProjectStatus) -> list[ProjectStatus]:
    """获取当前状态可以转换到的状态列表"""
    return VALID_STATUS_TRANSITIONS.get(current_status, [])

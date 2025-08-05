#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI优先级值对象

定义AI请求的优先级
"""

from enum import Enum
from typing import Dict, Any


class AIPriority(Enum):
    """
    AI请求优先级枚举
    
    定义AI请求的处理优先级
    """
    
    LOW = "low"           # 低优先级
    NORMAL = "normal"     # 普通优先级
    HIGH = "high"         # 高优先级
    URGENT = "urgent"     # 紧急优先级
    CRITICAL = "critical" # 关键优先级
    
    @property
    def weight(self) -> int:
        """获取优先级权重（数值越大优先级越高）"""
        weights = {
            self.LOW: 1,
            self.NORMAL: 2,
            self.HIGH: 3,
            self.URGENT: 4,
            self.CRITICAL: 5
        }
        return weights[self]
    
    @property
    def timeout_multiplier(self) -> float:
        """获取超时时间倍数"""
        multipliers = {
            self.LOW: 0.5,      # 低优先级请求超时时间减半
            self.NORMAL: 1.0,   # 普通优先级使用默认超时时间
            self.HIGH: 1.5,     # 高优先级超时时间增加50%
            self.URGENT: 2.0,   # 紧急请求超时时间翻倍
            self.CRITICAL: 3.0  # 关键请求超时时间三倍
        }
        return multipliers[self]
    
    @property
    def retry_count(self) -> int:
        """获取重试次数"""
        retry_counts = {
            self.LOW: 1,        # 低优先级最多重试1次
            self.NORMAL: 2,     # 普通优先级最多重试2次
            self.HIGH: 3,       # 高优先级最多重试3次
            self.URGENT: 4,     # 紧急请求最多重试4次
            self.CRITICAL: 5    # 关键请求最多重试5次
        }
        return retry_counts[self]
    
    def get_description(self) -> str:
        """获取优先级描述"""
        descriptions = {
            self.LOW: "低优先级",
            self.NORMAL: "普通优先级",
            self.HIGH: "高优先级", 
            self.URGENT: "紧急优先级",
            self.CRITICAL: "关键优先级"
        }
        return descriptions[self]
    
    def get_color(self) -> str:
        """获取优先级对应的颜色"""
        colors = {
            self.LOW: "#808080",      # 灰色
            self.NORMAL: "#0078D4",   # 蓝色
            self.HIGH: "#FF8C00",     # 橙色
            self.URGENT: "#FF4500",   # 红橙色
            self.CRITICAL: "#DC143C"  # 深红色
        }
        return colors[self]
    
    def should_preempt(self, other: 'AIPriority') -> bool:
        """是否应该抢占其他优先级的请求"""
        return self.weight > other.weight
    
    @classmethod
    def from_weight(cls, weight: int) -> 'AIPriority':
        """根据权重获取优先级"""
        weight_mapping = {
            1: cls.LOW,
            2: cls.NORMAL,
            3: cls.HIGH,
            4: cls.URGENT,
            5: cls.CRITICAL
        }
        return weight_mapping.get(weight, cls.NORMAL)
    
    @classmethod
    def from_string(cls, value: str) -> 'AIPriority':
        """从字符串创建优先级"""
        try:
            return cls(value.lower())
        except ValueError:
            # 兼容性处理
            legacy_mapping = {
                'lowest': cls.LOW,
                'low': cls.LOW,
                'normal': cls.NORMAL,
                'medium': cls.NORMAL,
                'high': cls.HIGH,
                'highest': cls.URGENT,
                'urgent': cls.URGENT,
                'critical': cls.CRITICAL,
                'emergency': cls.CRITICAL
            }
            return legacy_mapping.get(value.lower(), cls.NORMAL)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'value': self.value,
            'name': self.name,
            'weight': self.weight,
            'description': self.get_description(),
            'color': self.get_color(),
            'timeout_multiplier': self.timeout_multiplier,
            'retry_count': self.retry_count
        }
    
    def __lt__(self, other: 'AIPriority') -> bool:
        """小于比较（权重小的优先级低）"""
        return self.weight < other.weight
    
    def __le__(self, other: 'AIPriority') -> bool:
        """小于等于比较"""
        return self.weight <= other.weight
    
    def __gt__(self, other: 'AIPriority') -> bool:
        """大于比较（权重大的优先级高）"""
        return self.weight > other.weight
    
    def __ge__(self, other: 'AIPriority') -> bool:
        """大于等于比较"""
        return self.weight >= other.weight
    
    def __str__(self) -> str:
        return f"{self.get_description()}({self.value})"
    
    def __repr__(self) -> str:
        return f"AIPriority.{self.name}"

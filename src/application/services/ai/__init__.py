#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI应用服务模块 - 重构版本

提供AI相关的应用服务，实现业务用例和编排逻辑
遵循DDD架构原则，协调领域服务和基础设施组件

重构后的新架构：
- 核心服务：AI编排服务、提供商服务、功能服务
- 编排服务：请求编排器、响应编排器、工作流编排器
- 集成服务：服务管理器、事件处理器、缓存服务
- 智能化服务：智能化服务、功能注册表、能力匹配器
"""

# 新架构 - 核心服务
try:
    from .core.ai_orchestration_service import AIOrchestrationService
    _new_core_available = True
except ImportError:
    _new_core_available = False
    AIOrchestrationService = None

# 新架构 - 智能化服务
try:
    from .intelligence.ai_intelligence_service import AIIntelligenceService
    from .intelligence.ai_function_registry import ai_function_registry, AIFunctionRegistry
    _new_intelligence_available = True
except ImportError:
    _new_intelligence_available = False
    AIIntelligenceService = None
    ai_function_registry = None
    AIFunctionRegistry = None

# 向后兼容 - 旧版本组件（已删除，仅保留占位符）
_legacy_available = False
LegacyAIServiceManager = None
PerformanceMonitor = None
LegacyAIProviderService = None
UnifiedAIService = None
BaseAIService = None
IAIService = None

# 弃用警告函数
def _warn_deprecated(old_name: str, new_name: str):
    """发出弃用警告"""
    import warnings
    warnings.warn(
        f"{old_name} 已弃用，请使用 {new_name}。"
        f"详见迁移指南: docs/ai_module_migration_guide.md",
        DeprecationWarning,
        stacklevel=3
    )

# 兼容性函数
def get_ai_service(*args, **kwargs):
    """获取AI服务（兼容性函数）"""
    _warn_deprecated("get_ai_service", "AIOrchestrationService")
    if _new_core_available:
        # 如果没有传递配置，创建默认配置
        if not args and not kwargs:
            default_config = {
                'providers': {
                    'deepseek': {
                        'api_key': '',
                        'base_url': 'https://api.deepseek.com/v1',
                        'default_model': 'deepseek-chat'
                    }
                },
                'default_provider': 'deepseek'
            }
            return AIOrchestrationService(default_config)
        else:
            return AIOrchestrationService(*args, **kwargs)
    else:
        raise RuntimeError("AI编排服务不可用，请检查新架构模块安装")

def get_ai_function_registry():
    """获取AI功能注册表（兼容性函数）"""
    _warn_deprecated("get_ai_function_registry", "ai_function_registry")
    if _new_intelligence_available:
        return ai_function_registry
    else:
        raise RuntimeError("AI功能注册表不可用")

# 导出列表
__all__ = []

# 新架构组件
if _new_core_available:
    __all__.extend([
        'AIOrchestrationService'
    ])

if _new_intelligence_available:
    __all__.extend([
        'AIIntelligenceService',
        'ai_function_registry',
        'AIFunctionRegistry'
    ])

# 兼容性函数
__all__.extend([
    'get_ai_service',
    'get_ai_function_registry'
])

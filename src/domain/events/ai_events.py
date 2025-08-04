#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI相关领域事件

定义AI服务交互中的各种事件
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from src.shared.events.event_bus import Event


@dataclass
class AIRequestStartedEvent(Event):
    """
    AI请求开始事件

    当AI服务开始处理请求时触发的领域事件。
    用于跟踪AI请求的生命周期和性能监控。

    Attributes:
        request_id: 请求唯一标识符
        request_type: 请求类型（continuation/dialogue_improvement/scene_expansion等）
        user_id: 用户ID（可选）
        document_id: 关联文档ID（可选）
    """
    request_id: str = ""
    request_type: str = ""  # continuation, dialogue_improvement, scene_expansion, etc.
    user_id: Optional[str] = None
    document_id: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIRequestCompletedEvent(Event):
    """
    AI请求完成事件

    当AI服务成功完成请求时触发的领域事件。
    包含响应内容和性能指标。

    Attributes:
        request_id: 请求唯一标识符
        request_type: 请求类型
        response_text: AI响应文本
        processing_time_ms: 处理时间（毫秒）
        token_count: 令牌数量
    """
    request_id: str = ""
    request_type: str = ""
    response_text: str = ""
    processing_time_ms: int = 0
    token_count: int = 0

    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIRequestFailedEvent(Event):
    """
    AI请求失败事件

    当AI服务请求失败时触发的领域事件。
    包含错误信息和重试次数。

    Attributes:
        request_id: 请求唯一标识符
        request_type: 请求类型
        error_message: 错误消息
        error_code: 错误代码（可选）
        retry_count: 重试次数
    """
    request_id: str = ""
    request_type: str = ""
    error_message: str = ""
    error_code: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIContinuationGeneratedEvent(Event):
    """AI续写生成事件"""
    document_id: str = ""
    original_content: str = ""
    generated_continuation: str = ""
    confidence_score: float = 0.0
    word_count: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIDialogueImprovedEvent(Event):
    """AI对话改进事件"""
    document_id: str = ""
    original_dialogue: str = ""
    improved_dialogue: str = ""
    improvement_type: str = ""  # naturalness, emotion, character_voice, etc.
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AISceneExpandedEvent(Event):
    """AI场景扩展事件"""
    document_id: str = ""
    original_scene: str = ""
    expanded_scene: str = ""
    expansion_focus: str = ""  # description, atmosphere, action, etc.
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIStyleAnalysisCompletedEvent(Event):
    """AI风格分析完成事件"""
    document_id: str = ""
    analysis_result: Dict[str, Any] = None
    style_characteristics: List = None
    recommendations: List = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"
        if self.analysis_result is None:
            self.analysis_result = {}
        if self.style_characteristics is None:
            self.style_characteristics = []
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class AIPlotAnalysisCompletedEvent(Event):
    """AI情节分析完成事件"""
    document_id: str = ""
    plot_structure: Dict[str, Any] = None
    pacing_analysis: Dict[str, Any] = None
    suggestions: List = None

    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"
        if self.plot_structure is None:
            self.plot_structure = {}
        if self.pacing_analysis is None:
            self.pacing_analysis = {}
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class AICharacterAnalysisCompletedEvent(Event):
    """AI角色分析完成事件"""
    character_id: str = ""
    personality_analysis: Dict[str, Any] = None
    development_analysis: Dict[str, Any] = None
    consistency_check: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AISuggestionAcceptedEvent(Event):
    """AI建议被接受事件"""
    suggestion_id: str = ""
    suggestion_type: str = ""
    document_id: str = ""
    accepted_text: str = ""
    user_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AISuggestionRejectedEvent(Event):
    """AI建议被拒绝事件"""
    suggestion_id: str = ""
    suggestion_type: str = ""
    document_id: str = ""
    rejection_reason: Optional[str] = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIModelSwitchedEvent(Event):
    """AI模型切换事件"""
    old_model: str = ""
    new_model: str = ""
    provider: str = ""
    user_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIUsageStatsUpdatedEvent(Event):
    """AI使用统计更新事件"""
    user_id: Optional[str] = None
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    period: str = "daily"  # daily, weekly, monthly
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIFeedbackSubmittedEvent(Event):
    """AI反馈提交事件"""
    request_id: str = ""
    feedback_type: str = ""  # positive, negative, suggestion
    feedback_text: str = ""
    rating: Optional[int] = None  # 1-5 stars
    user_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "feedback_service"


@dataclass
class AIConfigurationChangedEvent(Event):
    """AI配置变更事件"""
    setting_key: str = ""
    old_value: Any = None
    new_value: Any = None
    user_id: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "settings_service"


@dataclass
class AIStreamChunkReceivedEvent(Event):
    """AI流式响应块接收事件"""
    request_id: str = ""
    chunk_text: str = ""
    chunk_index: int = 0
    is_final: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "ai_service"


@dataclass
class AIContextUpdatedEvent(Event):
    """AI上下文更新事件"""
    document_id: str = ""
    context_type: str = ""  # character_info, plot_summary, style_guide, etc.
    context_data: Dict[str, Any] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "context_service"


@dataclass
class AIPromptTemplateUsedEvent(Event):
    """AI提示模板使用事件"""
    template_id: str = ""
    template_name: str = ""
    variables: Dict[str, str] = None
    final_prompt: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.source = "prompt_service"

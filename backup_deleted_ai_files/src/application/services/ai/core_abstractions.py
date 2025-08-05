#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务核心抽象层 - 重构版本

定义AI服务的核心接口和抽象，提供统一的AI功能契约
"""

import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator, List, Protocol, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

try:
    from src.shared.utils.logger import get_logger
    from src.shared.utils.error_handler import ApplicationError
except ImportError:
    # 如果无法导入，使用标准库替代
    import logging
    def get_logger(name):
        return logging.getLogger(name)

    class ApplicationError(Exception):
        """应用程序错误基类"""
        pass

logger = get_logger(__name__)


class AIServiceError(ApplicationError):
    """AI服务错误基类 - 增强版本"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        self.retry_after = retry_after  # 建议重试间隔（秒）
        self.timestamp = datetime.now()

    def is_retryable(self) -> bool:
        """判断错误是否可重试"""
        retryable_codes = {
            'TIMEOUT', 'RATE_LIMIT', 'SERVICE_UNAVAILABLE',
            'NETWORK_ERROR', 'TEMPORARY_FAILURE'
        }
        return self.error_code in retryable_codes

    def get_user_message(self) -> str:
        """获取用户友好的错误消息"""
        user_messages = {
            'TIMEOUT': '请求超时，请检查网络连接后重试',
            'RATE_LIMIT': 'API调用频率过高，请稍后重试',
            'SERVICE_UNAVAILABLE': 'AI服务暂时不可用，请稍后重试',
            'INVALID_API_KEY': 'API密钥无效，请检查配置',
            'QUOTA_EXCEEDED': 'API配额已用完，请检查账户余额',
            'NETWORK_ERROR': '网络连接失败，请检查网络设置'
        }
        return user_messages.get(self.error_code, self.message)


class AICapability(Enum):
    """AI能力枚举 - 扩展版本"""
    # 基础能力
    TEXT_GENERATION = "text_generation"
    TEXT_ANALYSIS = "text_analysis"
    CONVERSATION = "conversation"

    # 内容创作
    CONTENT_CREATION = "content_creation"
    CREATIVE_WRITING = "creative_writing"
    STORY_CONTINUATION = "story_continuation"
    CHARACTER_DEVELOPMENT = "character_development"
    PLOT_GENERATION = "plot_generation"

    # 文本处理
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    REWRITING = "rewriting"
    PROOFREADING = "proofreading"
    STYLE_TRANSFER = "style_transfer"

    # 分析能力
    DOCUMENT_ANALYSIS = "document_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    THEME_ANALYSIS = "theme_analysis"
    CHARACTER_ANALYSIS = "character_analysis"

    # 交互能力
    QUESTION_ANSWERING = "question_answering"
    BRAINSTORMING = "brainstorming"
    WRITING_ASSISTANCE = "writing_assistance"

    # 技术能力
    CODE_GENERATION = "code_generation"
    DATA_EXTRACTION = "data_extraction"


class AIRequestType(Enum):
    """AI请求类型 - 扩展版本"""
    # 基础请求
    GENERATE = "generate"
    ANALYZE = "analyze"
    CHAT = "chat"

    # 文本处理
    TRANSLATE = "translate"
    SUMMARIZE = "summarize"
    REWRITE = "rewrite"
    CONTINUE = "continue"
    IMPROVE = "improve"
    PROOFREAD = "proofread"

    # 创作辅助
    BRAINSTORM = "brainstorm"
    INSPIRE = "inspire"
    DEVELOP_CHARACTER = "develop_character"
    GENERATE_PLOT = "generate_plot"

    # 分析功能
    ANALYZE_STYLE = "analyze_style"
    ANALYZE_THEME = "analyze_theme"
    ANALYZE_CHARACTER = "analyze_character"
    ANALYZE_SENTIMENT = "analyze_sentiment"


class AIRequestPriority(Enum):
    """AI请求优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AIRequest:
    """AI请求数据结构 - 增强版本"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: AIRequestType = AIRequestType.GENERATE
    prompt: str = ""
    context: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    priority: AIRequestPriority = AIRequestPriority.NORMAL
    timeout: Optional[float] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'type': self.type.value,
            'prompt': self.prompt,
            'context': self.context,
            'parameters': self.parameters,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'priority': self.priority.value,
            'timeout': self.timeout,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'stream': self.stream
        }

    def validate(self) -> List[str]:
        """验证请求数据"""
        errors = []

        if not self.prompt.strip():
            errors.append("提示词不能为空")

        if self.max_tokens is not None and self.max_tokens <= 0:
            errors.append("max_tokens必须大于0")

        if self.temperature is not None and not (0 <= self.temperature <= 2):
            errors.append("temperature必须在0-2之间")

        if self.timeout is not None and self.timeout <= 0:
            errors.append("timeout必须大于0")

        return errors

    def is_valid(self) -> bool:
        """检查请求是否有效"""
        return len(self.validate()) == 0


@dataclass
class AIResponse:
    """AI响应数据结构 - 增强版本"""
    request_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    is_complete: bool = True
    error: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'request_id': self.request_id,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'is_complete': self.is_complete,
            'error': self.error,
            'provider': self.provider,
            'model': self.model,
            'usage': self.usage,
            'processing_time': self.processing_time
        }

    def is_success(self) -> bool:
        """检查响应是否成功"""
        return self.error is None and self.content.strip()

    def get_word_count(self) -> int:
        """获取内容字数"""
        return len(self.content.split()) if self.content else 0


class IAIProvider(Protocol):
    """AI提供商接口协议"""
    
    async def generate_text(self, request: AIRequest) -> AIResponse:
        """生成文本"""
        ...
        
    async def generate_text_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        ...
        
    async def is_available(self) -> bool:
        """检查可用性"""
        ...
        
    def get_capabilities(self) -> List[AICapability]:
        """获取支持的能力"""
        ...
        
    def get_name(self) -> str:
        """获取提供商名称"""
        ...


class IAIService(ABC):
    """AI服务核心接口"""
    
    @abstractmethod
    async def process_request(self, request: AIRequest) -> AIResponse:
        """处理AI请求"""
        pass
        
    @abstractmethod
    async def process_request_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """流式处理AI请求"""
        pass
        
    @abstractmethod
    async def check_service_availability(self) -> bool:
        """检查服务可用性"""
        pass
        
    @abstractmethod
    def get_supported_capabilities(self) -> List[AICapability]:
        """获取支持的能力"""
        pass
        
    @abstractmethod
    async def cancel_request(self, request_id: str) -> bool:
        """取消请求"""
        pass
        
    @abstractmethod
    def get_active_requests(self) -> List[str]:
        """获取活跃请求列表"""
        pass


class IAIServiceManager(ABC):
    """AI服务管理器接口"""
    
    @abstractmethod
    def register_provider(self, provider: IAIProvider) -> None:
        """注册AI提供商"""
        pass
        
    @abstractmethod
    def get_provider(self, name: str) -> Optional[IAIProvider]:
        """获取AI提供商"""
        pass
        
    @abstractmethod
    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        pass
        
    @abstractmethod
    async def route_request(self, request: AIRequest, provider_name: Optional[str] = None) -> AIResponse:
        """路由请求到合适的提供商"""
        pass


class IAIFunctionModule(ABC):
    """AI功能模块接口"""
    
    @abstractmethod
    def get_module_name(self) -> str:
        """获取模块名称"""
        pass
        
    @abstractmethod
    def get_supported_request_types(self) -> List[AIRequestType]:
        """获取支持的请求类型"""
        pass
        
    @abstractmethod
    async def process(self, request: AIRequest) -> AIResponse:
        """处理请求"""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """检查模块是否可用"""
        pass


class AIServiceEvents(QObject):
    """AI服务事件信号"""
    
    # 请求相关信号
    request_started = pyqtSignal(str)  # request_id
    request_completed = pyqtSignal(str, str)  # request_id, content
    request_failed = pyqtSignal(str, str)  # request_id, error
    request_cancelled = pyqtSignal(str)  # request_id
    
    # 流式响应信号
    stream_started = pyqtSignal(str)  # request_id
    stream_chunk_received = pyqtSignal(str, str)  # request_id, chunk
    stream_completed = pyqtSignal(str)  # request_id
    stream_error = pyqtSignal(str, str)  # request_id, error
    
    # 服务状态信号
    service_status_changed = pyqtSignal(str, bool)  # service_name, is_available
    provider_registered = pyqtSignal(str)  # provider_name
    provider_unregistered = pyqtSignal(str)  # provider_name


@dataclass
class AIServiceConfig:
    """AI服务配置"""
    default_provider: str = "openai"
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    retry_attempts: int = 3
    enable_caching: bool = True
    cache_ttl: int = 3600
    log_requests: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'default_provider': self.default_provider,
            'max_concurrent_requests': self.max_concurrent_requests,
            'request_timeout': self.request_timeout,
            'retry_attempts': self.retry_attempts,
            'enable_caching': self.enable_caching,
            'cache_ttl': self.cache_ttl,
            'log_requests': self.log_requests
        }


class AIRequestBuilder:
    """AI请求构建器"""
    
    def __init__(self):
        self._request = AIRequest()
    
    def with_type(self, request_type: AIRequestType) -> 'AIRequestBuilder':
        """设置请求类型"""
        self._request.type = request_type
        return self
    
    def with_prompt(self, prompt: str) -> 'AIRequestBuilder':
        """设置提示词"""
        self._request.prompt = prompt
        return self
    
    def with_context(self, context: str) -> 'AIRequestBuilder':
        """设置上下文"""
        self._request.context = context
        return self
    
    def with_parameter(self, key: str, value: Any) -> 'AIRequestBuilder':
        """添加参数"""
        self._request.parameters[key] = value
        return self

    def with_parameters(self, parameters: Dict[str, Any]) -> 'AIRequestBuilder':
        """批量添加参数（兼容性方法）"""
        if parameters:
            self._request.parameters.update(parameters)
        return self

    def with_metadata(self, key: str, value: Any) -> 'AIRequestBuilder':
        """添加元数据"""
        self._request.metadata[key] = value
        return self
    
    def build(self) -> AIRequest:
        """构建请求"""
        return self._request

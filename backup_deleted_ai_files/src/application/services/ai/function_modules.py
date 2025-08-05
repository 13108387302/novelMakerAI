#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI功能模块 - 重构版本

提供模块化的AI功能实现
"""

from abc import ABC
from typing import List, Dict, Any, Optional
from datetime import datetime

from .core_abstractions import (
    IAIFunctionModule, IAIProvider, AIRequest, AIResponse, 
    AIRequestType, AICapability, AIServiceError
)
try:
    from src.shared.utils.logger import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class BaseFunctionModule(IAIFunctionModule):
    """AI功能模块基类"""
    
    def __init__(self, name: str, provider: IAIProvider):
        self.name = name
        self.provider = provider
        self._is_available = True
    
    def get_module_name(self) -> str:
        """获取模块名称"""
        return self.name
    
    def is_available(self) -> bool:
        """检查模块是否可用"""
        return self._is_available and self.provider is not None
    
    async def process(self, request: AIRequest) -> AIResponse:
        """处理请求 - 基础实现"""
        if not self.is_available():
            raise AIServiceError(f"功能模块 {self.name} 不可用")
        
        if request.type not in self.get_supported_request_types():
            raise AIServiceError(f"功能模块 {self.name} 不支持请求类型 {request.type}")
        
        # 预处理请求
        processed_request = await self._preprocess_request(request)
        
        # 调用提供商
        response = await self.provider.generate_text(processed_request)
        
        # 后处理响应
        return await self._postprocess_response(response, request)
    
    async def _preprocess_request(self, request: AIRequest) -> AIRequest:
        """预处理请求 - 子类可重写"""
        return request
    
    async def _postprocess_response(self, response: AIResponse, original_request: AIRequest) -> AIResponse:
        """后处理响应 - 子类可重写"""
        return response


class ConversationModule(BaseFunctionModule):
    """对话功能模块"""
    
    def __init__(self, provider: IAIProvider):
        super().__init__("conversation", provider)
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
    
    def get_supported_request_types(self) -> List[AIRequestType]:
        """获取支持的请求类型"""
        return [AIRequestType.CHAT]
    
    async def _preprocess_request(self, request: AIRequest) -> AIRequest:
        """预处理对话请求"""
        # 获取会话ID
        session_id = request.metadata.get('session_id', 'default')
        
        # 构建对话历史
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        history = self.conversation_history[session_id]
        
        # 构建完整的对话上下文
        context_parts = []
        if request.context:
            context_parts.append(f"背景信息: {request.context}")
        
        if history:
            context_parts.append("对话历史:")
            for msg in history[-5:]:  # 只保留最近5轮对话
                context_parts.append(f"用户: {msg['user']}")
                context_parts.append(f"助手: {msg['assistant']}")
        
        context_parts.append(f"用户: {request.prompt}")
        
        # 更新请求
        request.prompt = "请作为一个专业的写作助手回答用户的问题。"
        request.context = "\n".join(context_parts)
        
        return request
    
    async def _postprocess_response(self, response: AIResponse, original_request: AIRequest) -> AIResponse:
        """后处理对话响应"""
        # 保存对话历史
        session_id = original_request.metadata.get('session_id', 'default')
        
        if session_id in self.conversation_history:
            self.conversation_history[session_id].append({
                'user': original_request.prompt,
                'assistant': response.content
            })
            
            # 限制历史长度
            if len(self.conversation_history[session_id]) > 20:
                self.conversation_history[session_id] = self.conversation_history[session_id][-20:]
        
        return response
    
    def clear_conversation_history(self, session_id: str = None) -> None:
        """清除对话历史"""
        if session_id:
            self.conversation_history.pop(session_id, None)
        else:
            self.conversation_history.clear()


class ContentGenerationModule(BaseFunctionModule):
    """内容生成功能模块"""
    
    def __init__(self, provider: IAIProvider):
        super().__init__("content_generation", provider)
    
    def get_supported_request_types(self) -> List[AIRequestType]:
        """获取支持的请求类型"""
        return [
            AIRequestType.GENERATE,
            AIRequestType.CONTINUE,
            AIRequestType.REWRITE,
            AIRequestType.IMPROVE
        ]
    
    async def _preprocess_request(self, request: AIRequest) -> AIRequest:
        """预处理内容生成请求"""
        # 根据请求类型调整提示词
        if request.type == AIRequestType.CONTINUE:
            request.prompt = self._build_continue_prompt(request.prompt, request.context)
        elif request.type == AIRequestType.REWRITE:
            request.prompt = self._build_rewrite_prompt(request.prompt, request.context)
        elif request.type == AIRequestType.IMPROVE:
            request.prompt = self._build_improve_prompt(request.prompt, request.context)
        
        return request
    
    def _build_continue_prompt(self, content: str, context: str) -> str:
        """构建续写提示词"""
        return f"""请为以下内容进行自然流畅的续写：

背景信息：{context}

现有内容：
{content}

请续写内容，保持风格一致，情节自然发展："""
    
    def _build_rewrite_prompt(self, content: str, context: str) -> str:
        """构建改写提示词"""
        style_requirement = context or "保持原意但改进表达"
        return f"""请改写以下内容，要求：{style_requirement}

原文：
{content}

改写后的内容："""
    
    def _build_improve_prompt(self, content: str, context: str) -> str:
        """构建改进提示词"""
        improvement_focus = context or "提升文字质量和表达效果"
        return f"""请改进以下内容，重点关注：{improvement_focus}

原文：
{content}

改进后的内容："""


class AnalysisModule(BaseFunctionModule):
    """分析功能模块"""
    
    def __init__(self, provider: IAIProvider):
        super().__init__("analysis", provider)
    
    def get_supported_request_types(self) -> List[AIRequestType]:
        """获取支持的请求类型"""
        return [AIRequestType.ANALYZE, AIRequestType.SUMMARIZE]
    
    async def _preprocess_request(self, request: AIRequest) -> AIRequest:
        """预处理分析请求"""
        if request.type == AIRequestType.ANALYZE:
            analysis_type = request.metadata.get('analysis_type', 'general')
            request.prompt = self._build_analysis_prompt(request.prompt, analysis_type)
        elif request.type == AIRequestType.SUMMARIZE:
            request.prompt = self._build_summarize_prompt(request.prompt)
        
        return request
    
    def _build_analysis_prompt(self, content: str, analysis_type: str) -> str:
        """构建分析提示词"""
        analysis_prompts = {
            'character': "请分析以下内容中的角色特征、性格发展和角色关系：",
            'plot': "请分析以下内容的情节结构、冲突设置和发展脉络：",
            'theme': "请分析以下内容的主题思想、象征意义和深层含义：",
            'style': "请分析以下内容的写作风格、语言特色和表达技巧：",
            'general': "请对以下内容进行全面分析："
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts['general'])
        return f"""{prompt}

内容：
{content}

分析结果："""
    
    def _build_summarize_prompt(self, content: str) -> str:
        """构建摘要提示词"""
        return f"""请为以下内容生成简洁准确的摘要：

内容：
{content}

摘要："""


class TranslationModule(BaseFunctionModule):
    """翻译功能模块"""
    
    def __init__(self, provider: IAIProvider):
        super().__init__("translation", provider)
    
    def get_supported_request_types(self) -> List[AIRequestType]:
        """获取支持的请求类型"""
        return [AIRequestType.TRANSLATE]
    
    async def _preprocess_request(self, request: AIRequest) -> AIRequest:
        """预处理翻译请求"""
        source_lang = request.metadata.get('source_language', '自动检测')
        target_lang = request.metadata.get('target_language', '中文')
        
        request.prompt = f"""请将以下文本从{source_lang}翻译为{target_lang}：

原文：
{request.prompt}

译文："""
        
        return request


class FunctionModuleFactory:
    """功能模块工厂"""
    
    @staticmethod
    def create_module(module_type: str, provider: IAIProvider) -> IAIFunctionModule:
        """创建功能模块"""
        modules = {
            'conversation': ConversationModule,
            'content_generation': ContentGenerationModule,
            'analysis': AnalysisModule,
            'translation': TranslationModule
        }
        
        module_class = modules.get(module_type)
        if not module_class:
            raise AIServiceError(f"不支持的功能模块类型: {module_type}")
        
        return module_class(provider)
    
    @staticmethod
    def get_available_module_types() -> List[str]:
        """获取可用的模块类型"""
        return ['conversation', 'content_generation', 'analysis', 'translation']

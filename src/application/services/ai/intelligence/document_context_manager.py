#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档上下文管理器

负责管理AI组件与文档编辑器之间的上下文同步，
提供实时的文档内容分析和智能建议。

Author: AI小说编辑器团队
Date: 2025-08-08
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from .deep_context_analyzer import DeepContextAnalyzer, WritingContext
from src.shared.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class DocumentContextInfo:
    """文档上下文信息"""
    document_id: str
    content: str
    selected_text: str
    cursor_position: int
    last_updated: datetime
    analysis_result: Optional[WritingContext] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class DocumentContextManager:
    """
    文档上下文管理器
    
    功能：
    1. 监听文档内容变化
    2. 实时分析文档上下文
    3. 为AI组件提供最新的上下文信息
    4. 生成智能写作建议
    5. 管理多文档的上下文状态
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.context_analyzer = DeepContextAnalyzer()
        
        # 文档上下文缓存
        self._document_contexts: Dict[str, DocumentContextInfo] = {}
        self._context_lock = Lock()
        
        # AI组件注册表
        self._ai_components: Dict[str, Any] = {}
        self._update_callbacks: List[Callable] = []
        
        # 配置参数
        self.auto_analysis_enabled = True
        self.min_content_length = 50
        self.analysis_debounce_ms = 1000  # 防抖延迟
        
        logger.info("文档上下文管理器初始化完成")
    
    def register_ai_component(self, component_id: str, component: Any) -> None:
        """注册AI组件"""
        self._ai_components[component_id] = component
        logger.debug(f"AI组件已注册: {component_id}")
        
        # 如果有现有上下文，立即更新组件
        if self._document_contexts:
            self._update_ai_component(component_id, component)
    
    def unregister_ai_component(self, component_id: str) -> None:
        """注销AI组件"""
        if component_id in self._ai_components:
            del self._ai_components[component_id]
            logger.debug(f"AI组件已注销: {component_id}")
    
    def add_update_callback(self, callback: Callable) -> None:
        """添加上下文更新回调"""
        self._update_callbacks.append(callback)
    
    def update_document_context(
        self,
        document_id: str,
        content: str,
        selected_text: str = "",
        cursor_position: int = 0
    ) -> None:
        """更新文档上下文"""
        with self._context_lock:
            # 创建或更新上下文信息
            context_info = DocumentContextInfo(
                document_id=document_id,
                content=content,
                selected_text=selected_text,
                cursor_position=cursor_position,
                last_updated=datetime.now()
            )
            
            self._document_contexts[document_id] = context_info
            logger.debug(f"文档上下文已更新: {document_id}, 内容长度: {len(content)}")
        
        # 异步分析上下文
        if self.auto_analysis_enabled and len(content) >= self.min_content_length:
            self._analyze_context_async(document_id)
        
        # 通知所有AI组件
        self._notify_ai_components(document_id)
        
        # 执行回调
        for callback in self._update_callbacks:
            try:
                callback(document_id, context_info)
            except Exception as e:
                logger.error(f"上下文更新回调执行失败: {e}")
    
    def get_document_context(self, document_id: str) -> Optional[DocumentContextInfo]:
        """获取文档上下文"""
        with self._context_lock:
            return self._document_contexts.get(document_id)
    
    def get_current_context(self) -> Optional[DocumentContextInfo]:
        """获取当前活动文档的上下文"""
        with self._context_lock:
            if not self._document_contexts:
                return None
            
            # 返回最近更新的文档上下文
            latest_context = max(
                self._document_contexts.values(),
                key=lambda x: x.last_updated
            )
            return latest_context
    
    def analyze_document_context(self, document_id: str) -> Optional[WritingContext]:
        """分析文档上下文"""
        context_info = self.get_document_context(document_id)
        if not context_info:
            return None
        
        try:
            analysis_result = self.context_analyzer.analyze_content(context_info.content)
            
            # 更新缓存
            with self._context_lock:
                if document_id in self._document_contexts:
                    self._document_contexts[document_id].analysis_result = analysis_result
            
            logger.info(f"文档上下文分析完成: {document_id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"文档上下文分析失败: {e}")
            return None
    
    def generate_writing_suggestions(self, document_id: str) -> List[str]:
        """生成写作建议"""
        context_info = self.get_document_context(document_id)
        if not context_info:
            return []
        
        suggestions = []
        
        try:
            # 基于内容长度的建议
            content_length = len(context_info.content)
            if content_length < 100:
                suggestions.append("💡 可以添加更多的背景描述或人物介绍")
            elif content_length > 2000:
                suggestions.append("📝 内容较长，可以考虑分段或添加小标题")
            
            # 基于选中文本的建议
            if context_info.selected_text:
                selected_length = len(context_info.selected_text)
                if selected_length < 50:
                    suggestions.append("🔍 可以对选中文本进行扩展描述")
                else:
                    suggestions.append("✨ 可以对选中文本进行润色优化")
            
            # 基于分析结果的建议
            if context_info.analysis_result:
                analysis = context_info.analysis_result
                
                # 角色相关建议
                if len(analysis.character_analysis) == 0:
                    suggestions.append("👥 可以添加更多角色描述和对话")
                elif len(analysis.character_analysis) > 5:
                    suggestions.append("🎭 角色较多，注意保持各角色的独特性")
                
                # 情感基调建议
                if analysis.emotional_tone.value == "neutral":
                    suggestions.append("🎨 可以增强情感表达，让文字更有感染力")
                
                # 场景设定建议
                if not analysis.scene_setting.location:
                    suggestions.append("🏞️ 可以添加更多场景和环境描述")
            
            # 更新缓存
            with self._context_lock:
                if document_id in self._document_contexts:
                    self._document_contexts[document_id].suggestions = suggestions
            
            logger.debug(f"生成写作建议: {document_id}, {len(suggestions)} 条建议")
            
        except Exception as e:
            logger.error(f"生成写作建议失败: {e}")
        
        return suggestions
    
    def clear_document_context(self, document_id: str) -> None:
        """清除文档上下文"""
        with self._context_lock:
            if document_id in self._document_contexts:
                del self._document_contexts[document_id]
                logger.debug(f"文档上下文已清除: {document_id}")
    
    def _analyze_context_async(self, document_id: str) -> None:
        """异步分析上下文"""
        import threading
        
        def analyze():
            try:
                self.analyze_document_context(document_id)
                self.generate_writing_suggestions(document_id)
            except Exception as e:
                logger.error(f"异步上下文分析失败: {e}")
        
        thread = threading.Thread(target=analyze, daemon=True)
        thread.start()
    
    def _notify_ai_components(self, document_id: str) -> None:
        """通知所有AI组件上下文更新"""
        context_info = self.get_document_context(document_id)
        if not context_info:
            return
        
        for component_id, component in self._ai_components.items():
            try:
                self._update_ai_component(component_id, component, context_info)
            except Exception as e:
                logger.error(f"更新AI组件失败 {component_id}: {e}")
    
    def _update_ai_component(self, component_id: str, component: Any, context_info: Optional[DocumentContextInfo] = None) -> None:
        """更新单个AI组件"""
        if not context_info:
            context_info = self.get_current_context()
        
        if not context_info:
            return
        
        try:
            # 尝试不同的更新方法
            if hasattr(component, 'set_document_context'):
                component.set_document_context(
                    context_info.content,
                    doc_type="chapter",
                    metadata={'id': context_info.document_id}
                )
            elif hasattr(component, 'set_context'):
                component.set_context(context_info.content, context_info.selected_text)
            
            # 设置选中文本
            if hasattr(component, 'set_selected_text'):
                component.set_selected_text(context_info.selected_text)
            
            logger.debug(f"AI组件上下文已更新: {component_id}")
            
        except Exception as e:
            logger.error(f"更新AI组件上下文失败 {component_id}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._context_lock:
            return {
                'total_documents': len(self._document_contexts),
                'registered_components': len(self._ai_components),
                'update_callbacks': len(self._update_callbacks),
                'auto_analysis_enabled': self.auto_analysis_enabled
            }

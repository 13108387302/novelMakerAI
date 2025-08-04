#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析AI服务

专门处理文本分析功能
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from .base_ai_service import BaseAIService
from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisService(BaseAIService):
    """分析AI服务"""
    
    def __init__(
        self,
        ai_repository: IAIServiceRepository,
        event_bus: EventBus
    ):
        super().__init__(ai_repository, event_bus)
        
    async def _do_generate_text(self, prompt: str, context: str = "") -> str:
        """具体的文本生成实现"""
        return await self.ai_repository.generate_text(prompt, context)
        
    async def analyze_style(
        self,
        text: str,
        analysis_aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析文本风格"""
        try:
            request_id = self._generate_request_id()
            
            # 构建风格分析提示词
            prompt = self._build_style_analysis_prompt(text, analysis_aspects)
            
            # 执行分析
            response = await self._execute_request(request_id, prompt)
            
            # 解析分析结果
            analysis_result = self._parse_style_analysis(response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"风格分析失败: {e}")
            raise
            
    async def analyze_plot(
        self,
        text: str,
        analysis_type: str = "structure"
    ) -> Dict[str, Any]:
        """分析情节结构"""
        try:
            request_id = self._generate_request_id()
            
            # 构建情节分析提示词
            prompt = self._build_plot_analysis_prompt(text, analysis_type)
            
            # 执行分析
            response = await self._execute_request(request_id, prompt)
            
            # 解析分析结果
            analysis_result = self._parse_plot_analysis(response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"情节分析失败: {e}")
            raise
            
    async def analyze_characters(
        self,
        text: str,
        focus_characters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析角色特征"""
        try:
            request_id = self._generate_request_id()
            
            # 构建角色分析提示词
            prompt = self._build_character_analysis_prompt(text, focus_characters)
            
            # 执行分析
            response = await self._execute_request(request_id, prompt)
            
            # 解析分析结果
            analysis_result = self._parse_character_analysis(response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"角色分析失败: {e}")
            raise
            
    async def analyze_themes(
        self,
        text: str,
        theme_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析主题内容"""
        try:
            request_id = self._generate_request_id()
            
            # 构建主题分析提示词
            prompt = self._build_theme_analysis_prompt(text, theme_categories)
            
            # 执行分析
            response = await self._execute_request(request_id, prompt)
            
            # 解析分析结果
            analysis_result = self._parse_theme_analysis(response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"主题分析失败: {e}")
            raise
            
    async def analyze_readability(
        self,
        text: str,
        target_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析可读性"""
        try:
            request_id = self._generate_request_id()
            
            # 构建可读性分析提示词
            prompt = self._build_readability_analysis_prompt(text, target_audience)
            
            # 执行分析
            response = await self._execute_request(request_id, prompt)
            
            # 解析分析结果
            analysis_result = self._parse_readability_analysis(response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"可读性分析失败: {e}")
            raise
            
    async def generate_summary(
        self,
        text: str,
        summary_type: str = "brief",
        max_length: Optional[int] = None
    ) -> str:
        """生成文本摘要"""
        try:
            request_id = self._generate_request_id()
            
            # 构建摘要生成提示词
            prompt = self._build_summary_prompt(text, summary_type, max_length)
            
            # 执行生成
            response = await self._execute_request(request_id, prompt)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            raise
            
    def _build_style_analysis_prompt(
        self, 
        text: str, 
        analysis_aspects: Optional[List[str]] = None
    ) -> str:
        """构建风格分析提示词"""
        default_aspects = [
            "语言风格", "句式特点", "词汇选择", "修辞手法", "语调特征"
        ]
        
        aspects = analysis_aspects or default_aspects
        aspects_str = "、".join(aspects)
        
        prompt = f"""请分析以下文本的写作风格，重点关注：{aspects_str}。

请按以下格式提供分析结果：
1. 整体风格特征：
2. 语言特点：
3. 句式分析：
4. 词汇特色：
5. 修辞手法：
6. 改进建议：

分析文本：
{text}

分析结果："""
        
        return prompt
        
    def _build_plot_analysis_prompt(self, text: str, analysis_type: str) -> str:
        """构建情节分析提示词"""
        type_prompts = {
            "structure": "请分析文本的情节结构，包括开端、发展、高潮、结局等",
            "conflict": "请分析文本中的冲突类型和发展过程",
            "pacing": "请分析文本的节奏控制和情节推进速度",
            "tension": "请分析文本的紧张感营造和悬念设置"
        }
        
        analysis_desc = type_prompts.get(analysis_type, type_prompts["structure"])
        
        prompt = f"""{analysis_desc}。

请按以下格式提供分析结果：
1. 情节概述：
2. 结构分析：
3. 关键转折点：
4. 节奏评价：
5. 优点总结：
6. 改进建议：

分析文本：
{text}

分析结果："""
        
        return prompt
        
    def _build_character_analysis_prompt(
        self, 
        text: str, 
        focus_characters: Optional[List[str]] = None
    ) -> str:
        """构建角色分析提示词"""
        prompt = "请分析文本中的角色特征和人物塑造。"
        
        if focus_characters:
            characters_str = "、".join(focus_characters)
            prompt += f"重点关注以下角色：{characters_str}。"
            
        prompt += f"""

请按以下格式提供分析结果：
1. 主要角色列表：
2. 角色性格特征：
3. 角色关系分析：
4. 人物发展轨迹：
5. 塑造手法评价：
6. 改进建议：

分析文本：
{text}

分析结果："""
        
        return prompt
        
    def _build_theme_analysis_prompt(
        self, 
        text: str, 
        theme_categories: Optional[List[str]] = None
    ) -> str:
        """构建主题分析提示词"""
        prompt = "请分析文本的主题内容和思想表达。"
        
        if theme_categories:
            categories_str = "、".join(theme_categories)
            prompt += f"重点关注以下主题类别：{categories_str}。"
            
        prompt += f"""

请按以下格式提供分析结果：
1. 主要主题：
2. 次要主题：
3. 主题表达方式：
4. 思想深度评价：
5. 现实意义：
6. 改进建议：

分析文本：
{text}

分析结果："""
        
        return prompt
        
    def _build_readability_analysis_prompt(
        self, 
        text: str, 
        target_audience: Optional[str] = None
    ) -> str:
        """构建可读性分析提示词"""
        prompt = "请分析文本的可读性和阅读体验。"
        
        if target_audience:
            prompt += f"目标读者群体：{target_audience}。"
            
        prompt += f"""

请按以下格式提供分析结果：
1. 可读性等级：
2. 语言难度：
3. 句子复杂度：
4. 词汇难度：
5. 阅读流畅度：
6. 改进建议：

分析文本：
{text}

分析结果："""
        
        return prompt
        
    def _build_summary_prompt(
        self, 
        text: str, 
        summary_type: str, 
        max_length: Optional[int] = None
    ) -> str:
        """构建摘要生成提示词"""
        type_prompts = {
            "brief": "请生成简洁的摘要，突出主要内容",
            "detailed": "请生成详细的摘要，包含重要细节",
            "key_points": "请提取文本的关键要点",
            "abstract": "请生成学术风格的摘要"
        }
        
        summary_desc = type_prompts.get(summary_type, type_prompts["brief"])
        
        prompt = f"{summary_desc}。"
        
        if max_length:
            prompt += f"摘要长度不超过{max_length}字。"
            
        prompt += f"""

原文：
{text}

摘要："""
        
        return prompt
        
    def _parse_style_analysis(self, response: str) -> Dict[str, Any]:
        """解析风格分析结果"""
        # 简单的解析实现，实际可以更复杂
        return {
            "raw_analysis": response,
            "analysis_type": "style",
            "timestamp": datetime.now().isoformat()
        }
        
    def _parse_plot_analysis(self, response: str) -> Dict[str, Any]:
        """解析情节分析结果"""
        return {
            "raw_analysis": response,
            "analysis_type": "plot",
            "timestamp": datetime.now().isoformat()
        }
        
    def _parse_character_analysis(self, response: str) -> Dict[str, Any]:
        """解析角色分析结果"""
        return {
            "raw_analysis": response,
            "analysis_type": "character",
            "timestamp": datetime.now().isoformat()
        }
        
    def _parse_theme_analysis(self, response: str) -> Dict[str, Any]:
        """解析主题分析结果"""
        return {
            "raw_analysis": response,
            "analysis_type": "theme",
            "timestamp": datetime.now().isoformat()
        }
        
    def _parse_readability_analysis(self, response: str) -> Dict[str, Any]:
        """解析可读性分析结果"""
        return {
            "raw_analysis": response,
            "analysis_type": "readability",
            "timestamp": datetime.now().isoformat()
        }
        
    def get_supported_features(self) -> list[str]:
        """获取支持的功能"""
        base_features = super().get_supported_features()
        analysis_features = [
            "style_analysis",
            "plot_analysis", 
            "character_analysis",
            "theme_analysis",
            "readability_analysis",
            "text_summarization"
        ]
        return base_features + analysis_features

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容生成AI服务

专门处理各种内容生成功能
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .base_ai_service import BaseAIService
from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.domain.events.ai_events import (
    AIContinuationGeneratedEvent, AIDialogueImprovedEvent, AISceneExpandedEvent
)
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ContentGenerationService(BaseAIService):
    """内容生成AI服务"""
    
    def __init__(
        self,
        ai_repository: IAIServiceRepository,
        event_bus: EventBus
    ):
        super().__init__(ai_repository, event_bus)
        
    async def _do_generate_text(self, prompt: str, context: str = "") -> str:
        """具体的文本生成实现"""
        return await self.ai_repository.generate_text(prompt, context)
        
    async def generate_continuation(
        self,
        content: str,
        context: str = "",
        style_requirements: Optional[str] = None,
        length_requirement: Optional[str] = None
    ) -> str:
        """生成续写内容"""
        try:
            request_id = self._generate_request_id()
            
            # 构建续写提示词
            prompt = self._build_continuation_prompt(
                content, context, style_requirements, length_requirement
            )
            
            # 执行生成
            response = await self._execute_request(request_id, prompt, context)
            
            # 发布续写生成事件
            await self.event_bus.publish(AIContinuationGeneratedEvent(
                content=content[:100] + "..." if len(content) > 100 else content,
                continuation=response[:100] + "..." if len(response) > 100 else response,
                timestamp=datetime.now()
            ))
            
            return response
            
        except Exception as e:
            logger.error(f"生成续写失败: {e}")
            raise
            
    async def improve_dialogue(
        self,
        dialogue: str,
        improvement_type: str = "natural",
        character_info: Optional[str] = None
    ) -> str:
        """改进对话"""
        try:
            request_id = self._generate_request_id()
            
            # 构建对话改进提示词
            prompt = self._build_dialogue_improvement_prompt(
                dialogue, improvement_type, character_info
            )
            
            # 执行生成
            response = await self._execute_request(request_id, prompt)
            
            # 发布对话改进事件
            await self.event_bus.publish(AIDialogueImprovedEvent(
                original_dialogue=dialogue[:100] + "..." if len(dialogue) > 100 else dialogue,
                improved_dialogue=response[:100] + "..." if len(response) > 100 else response,
                improvement_type=improvement_type,
                timestamp=datetime.now()
            ))
            
            return response
            
        except Exception as e:
            logger.error(f"改进对话失败: {e}")
            raise
            
    async def expand_scene(
        self,
        scene: str,
        expansion_focus: str = "atmosphere",
        setting_info: Optional[str] = None
    ) -> str:
        """扩展场景描写"""
        try:
            request_id = self._generate_request_id()
            
            # 构建场景扩展提示词
            prompt = self._build_scene_expansion_prompt(
                scene, expansion_focus, setting_info
            )
            
            # 执行生成
            response = await self._execute_request(request_id, prompt)
            
            # 发布场景扩展事件
            await self.event_bus.publish(AISceneExpandedEvent(
                original_scene=scene[:100] + "..." if len(scene) > 100 else scene,
                expanded_scene=response[:100] + "..." if len(response) > 100 else response,
                expansion_focus=expansion_focus,
                timestamp=datetime.now()
            ))
            
            return response
            
        except Exception as e:
            logger.error(f"扩展场景失败: {e}")
            raise
            
    async def generate_character_description(
        self,
        character_name: str,
        character_traits: Optional[str] = None,
        story_context: Optional[str] = None,
        description_style: str = "detailed"
    ) -> str:
        """生成角色描述"""
        try:
            request_id = self._generate_request_id()
            
            # 构建角色描述提示词
            prompt = self._build_character_description_prompt(
                character_name, character_traits, story_context, description_style
            )
            
            # 执行生成
            response = await self._execute_request(request_id, prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"生成角色描述失败: {e}")
            raise
            
    async def generate_plot_outline(
        self,
        story_theme: str,
        genre: Optional[str] = None,
        target_length: Optional[str] = None,
        key_elements: Optional[str] = None
    ) -> str:
        """生成情节大纲"""
        try:
            request_id = self._generate_request_id()
            
            # 构建情节大纲提示词
            prompt = self._build_plot_outline_prompt(
                story_theme, genre, target_length, key_elements
            )
            
            # 执行生成
            response = await self._execute_request(request_id, prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"生成情节大纲失败: {e}")
            raise
            
    def _build_continuation_prompt(
        self, 
        content: str, 
        context: str, 
        style_requirements: Optional[str] = None,
        length_requirement: Optional[str] = None
    ) -> str:
        """构建续写提示词"""
        base_prompt = """请为以下小说内容生成自然流畅的续写。要求：
1. 保持原有的写作风格和语调
2. 情节发展要合理自然
3. 人物性格要保持一致
4. 语言要生动有趣"""

        if style_requirements:
            base_prompt += f"\n5. 风格要求：{style_requirements}"
            
        if length_requirement:
            base_prompt += f"\n6. 长度要求：{length_requirement}"
            
        if context:
            base_prompt += f"\n\n背景信息：\n{context}"
            
        base_prompt += f"\n\n需要续写的内容：\n{content}\n\n续写内容："
        
        return base_prompt
        
    def _build_dialogue_improvement_prompt(
        self, 
        dialogue: str, 
        improvement_type: str,
        character_info: Optional[str] = None
    ) -> str:
        """构建对话改进提示词"""
        prompts = {
            "natural": "请让对话更加自然流畅，符合日常交流习惯",
            "emotional": "请增强对话的情感表达，让人物情感更加丰富",
            "dramatic": "请增加对话的戏剧张力，让冲突更加突出",
            "humorous": "请为对话增加幽默元素，让交流更加轻松有趣",
            "formal": "请让对话更加正式得体，适合正式场合",
            "casual": "请让对话更加随意轻松，适合日常交流"
        }
        
        improvement_desc = prompts.get(improvement_type, prompts["natural"])
        
        prompt = f"请改进以下对话，{improvement_desc}。"
        
        if character_info:
            prompt += f"\n\n角色信息：\n{character_info}"
            
        prompt += f"\n\n原对话：\n{dialogue}\n\n改进后的对话："
        
        return prompt
        
    def _build_scene_expansion_prompt(
        self, 
        scene: str, 
        expansion_focus: str,
        setting_info: Optional[str] = None
    ) -> str:
        """构建场景扩展提示词"""
        prompts = {
            "atmosphere": "请重点描写场景的氛围和情调",
            "visual": "请重点描写场景的视觉细节",
            "sensory": "请重点描写场景的感官体验（视觉、听觉、嗅觉等）",
            "emotional": "请重点描写场景对人物情感的影响",
            "action": "请重点描写场景中的动作和活动",
            "environment": "请重点描写场景的环境特征"
        }
        
        focus_desc = prompts.get(expansion_focus, prompts["atmosphere"])
        
        prompt = f"请扩展以下场景描写，{focus_desc}，让场景更加生动具体。"
        
        if setting_info:
            prompt += f"\n\n背景设定：\n{setting_info}"
            
        prompt += f"\n\n原场景：\n{scene}\n\n扩展后的场景："
        
        return prompt
        
    def _build_character_description_prompt(
        self,
        character_name: str,
        character_traits: Optional[str] = None,
        story_context: Optional[str] = None,
        description_style: str = "detailed"
    ) -> str:
        """构建角色描述提示词"""
        style_prompts = {
            "detailed": "请提供详细的角色描述，包括外貌、性格、背景等",
            "brief": "请提供简洁的角色描述，突出主要特征",
            "psychological": "请重点描述角色的心理特征和内在世界",
            "physical": "请重点描述角色的外貌和身体特征",
            "behavioral": "请重点描述角色的行为习惯和表现方式"
        }
        
        style_desc = style_prompts.get(description_style, style_prompts["detailed"])
        
        prompt = f"请为角色'{character_name}'创建描述。{style_desc}。"
        
        if character_traits:
            prompt += f"\n\n角色特征：\n{character_traits}"
            
        if story_context:
            prompt += f"\n\n故事背景：\n{story_context}"
            
        prompt += f"\n\n角色描述："
        
        return prompt
        
    def _build_plot_outline_prompt(
        self,
        story_theme: str,
        genre: Optional[str] = None,
        target_length: Optional[str] = None,
        key_elements: Optional[str] = None
    ) -> str:
        """构建情节大纲提示词"""
        prompt = f"请为主题为'{story_theme}'的故事创建情节大纲。"
        
        if genre:
            prompt += f"\n类型：{genre}"
            
        if target_length:
            prompt += f"\n目标长度：{target_length}"
            
        if key_elements:
            prompt += f"\n关键元素：{key_elements}"
            
        prompt += "\n\n请提供结构清晰的情节大纲，包括：\n"
        prompt += "1. 故事背景设定\n"
        prompt += "2. 主要角色介绍\n"
        prompt += "3. 情节发展脉络\n"
        prompt += "4. 高潮和转折点\n"
        prompt += "5. 结局安排\n\n"
        prompt += "情节大纲："
        
        return prompt
        
    def get_supported_features(self) -> list[str]:
        """获取支持的功能"""
        base_features = super().get_supported_features()
        content_features = [
            "continuation_generation",
            "dialogue_improvement", 
            "scene_expansion",
            "character_description",
            "plot_outline",
            "style_adaptation",
            "length_control"
        ]
        return base_features + content_features

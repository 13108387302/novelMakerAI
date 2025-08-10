#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IAIServiceRepository 适配器

将领域仓储接口适配到新架构 AIOrchestrationService，
以保持向后兼容并降低耦合。
"""

from typing import Optional, Dict, Any, AsyncGenerator

from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.application.services.ai.core.ai_orchestration_service import AIOrchestrationService


class AIServiceRepositoryAdapter(IAIServiceRepository):
    """将仓储接口委托给 AIOrchestrationService 的适配器"""

    def __init__(self, orchestration_service: AIOrchestrationService):
        self._svc = orchestration_service

    async def generate_text(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        return await self._svc.generate_text(
            prompt=prompt,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model
        )

    async def generate_text_stream(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._svc.generate_text_stream(
            prompt=prompt,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        ):
            yield chunk

    async def analyze_text(
        self,
        text: str,
        analysis_type: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._svc.analyze_text(text=text, analysis_type=analysis_type, model=model)

    async def improve_text(
        self,
        text: str,
        improvement_type: str,
        instructions: str = "",
        model: Optional[str] = None
    ) -> str:
        return await self._svc.improve_text(
            text=text,
            improvement_type=improvement_type,
            instructions=instructions,
            model=model,
        )


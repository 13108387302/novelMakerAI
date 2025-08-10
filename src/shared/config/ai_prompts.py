#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 提示模板配置

集中管理分析与改写的提示词构造，避免重复实现，便于统一调整。
"""
from __future__ import annotations
from typing import Dict


def build_analysis_prompt(text: str, analysis_type: str) -> str:
    analysis_map: Dict[str, str] = {
        "style": "从风格、语气、句式多样性、修辞手法等角度分析下面文本，并给出要点列表和建议。",
        "emotion": "识别文本中的情绪与情感强度，指出触发情绪的句段，并给出改进建议。",
        "structure": "分析文本结构（开端/发展/高潮/结尾）、段落组织与逻辑连贯性，并提出优化建议。",
    }
    header = analysis_map.get(analysis_type, "给出全面的文本分析与建议。")
    return f"""你是经验丰富的中文写作编辑。{header}
请尽量以结构化JSON输出，字段包含: summary, strengths, weaknesses, suggestions。

文本：\n{text}\n"""


def build_improve_prompt(text: str, improvement_type: str, instructions: str) -> str:
    goals: Dict[str, str] = {
        "refine": "润色语言，使其更流畅、自然，保持原意。",
        "concise": "在不改变含义的前提下更简洁凝练。",
        "expand": "在保留风格的前提下扩展细节与画面感。",
        "formal": "语气更正式、规范。",
        "creative": "提升文学性与意象，增强表达的感染力。",
    }
    goal = goals.get(improvement_type, goals["refine"]) 
    extra = f"特定指令：{instructions}\n" if instructions else ""
    return f"""你是专业中文编辑，请按目标改写文本。
目标：{goal}
{extra}
请仅输出改写后的文本，不要包含其他说明。

原文：\n{text}\n"""


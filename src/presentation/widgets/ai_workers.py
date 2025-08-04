#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI工作线程模块

包含各种AI任务的工作线程实现
"""

import asyncio
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from src.infrastructure.ai_clients.openai_client import get_ai_client_manager
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class AITaskType(Enum):
    """AI任务类型"""
    # 全局分析类
    PROJECT_ANALYSIS = "project_analysis"
    OUTLINE_GENERATION = "outline_generation"
    CHARACTER_ANALYSIS = "character_analysis"
    PLOT_DEVELOPMENT = "plot_development"
    STYLE_ANALYSIS = "style_analysis"
    CONTENT_OPTIMIZATION = "content_optimization"
    
    # 写作助手类
    WRITING_CONTINUATION = "writing_continuation"
    DIALOGUE_IMPROVEMENT = "dialogue_improvement"
    SCENE_EXPANSION = "scene_expansion"
    
    # 内容工具类
    TEXT_REWRITING = "text_rewriting"
    CONTENT_EXPANSION = "content_expansion"
    CONTENT_SUMMARIZATION = "content_summarization"
    GRAMMAR_CHECK = "grammar_check"
    CHARACTER_GENERATION = "character_generation"
    SCENE_GENERATION = "scene_generation"
    PLOT_POINT_GENERATION = "plot_point_generation"
    DIALOGUE_GENERATION = "dialogue_generation"
    STYLE_CONVERSION = "style_conversion"
    INSPIRATION_GENERATION = "inspiration_generation"


@dataclass
class AITaskConfig:
    """AI任务配置"""
    task_type: AITaskType
    title: str
    description: str
    icon: str
    prompt_template: str = ""
    max_tokens: int = 2000
    temperature: float = 0.7


class RealTimeAIWorker(QThread):
    """实时AI任务工作线程"""

    task_completed = pyqtSignal(str)
    task_failed = pyqtSignal(str)
    chunk_received = pyqtSignal(str)

    def __init__(self, prompt: str, context: str = "", max_tokens: int = 1000, temperature: float = 0.7):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._is_cancelled = False

    def run(self):
        """运行AI任务（优化版本）"""
        loop = None
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步任务
            loop.run_until_complete(self._execute_task())

        except Exception as e:
            logger.error(f"AI任务执行失败: {e}")
            self.task_failed.emit(str(e))
        finally:
            # 确保事件循环正确关闭
            if loop and not loop.is_closed():
                try:
                    # 取消所有未完成的任务
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()

                    # 等待任务取消完成
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception as cleanup_error:
                    logger.warning(f"清理AI任务时出错: {cleanup_error}")
                finally:
                    loop.close()

    async def _execute_task(self):
        """异步执行任务"""
        try:
            ai_client = get_ai_client_manager()
            accumulated_response = ""

            # 使用流式生成
            async for chunk in ai_client.stream_generate(
                prompt=self.prompt,
                context=self.context,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            ):
                if self._is_cancelled:
                    break

                accumulated_response += chunk
                self.chunk_received.emit(chunk)

            if not self._is_cancelled:
                self.task_completed.emit(accumulated_response)

        except Exception as e:
            logger.error(f"AI任务异步执行失败: {e}")
            self.task_failed.emit(str(e))

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True


class AITaskWorker(QThread):
    """AI任务工作线程"""

    chunk_received = pyqtSignal(str)
    task_completed = pyqtSignal(str)
    task_failed = pyqtSignal(str)

    def __init__(self, prompt: str, task_config: AITaskConfig):
        super().__init__()
        self.prompt = prompt
        self.task_config = task_config
        self._is_cancelled = False

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True

    def run(self):
        """执行AI任务"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 运行异步任务
                loop.run_until_complete(self._execute_task())
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"AI任务执行失败: {e}")
            self.task_failed.emit(str(e))

    async def _execute_task(self):
        """异步执行任务"""
        try:
            ai_client = get_ai_client_manager()
            accumulated_response = ""

            # 使用流式生成
            async for chunk in ai_client.stream_generate(
                prompt=self.prompt,
                max_tokens=self.task_config.max_tokens,
                temperature=self.task_config.temperature
            ):
                if self._is_cancelled:
                    break

                accumulated_response += chunk
                self.chunk_received.emit(chunk)

            if not self._is_cancelled:
                self.task_completed.emit(accumulated_response)

        except Exception as e:
            logger.error(f"AI任务异步执行失败: {e}")
            self.task_failed.emit(str(e))


class StreamingAIWorker(QThread):
    """流式AI工作线程 - 用于实时写作助手"""

    chunk_received = pyqtSignal(str)
    response_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, prompt: str, context: str = "", max_tokens: int = 1000, temperature: float = 0.7):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._stop_requested = False
        self._accumulated_response = ""

    def run(self):
        """运行流式AI请求"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步流式响应
            loop.run_until_complete(self._stream_response())

        except Exception as e:
            logger.error(f"流式AI请求失败: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()

    async def _stream_response(self):
        """流式响应处理"""
        try:
            ai_client = get_ai_client_manager()

            async for chunk in ai_client.stream_generate(
                prompt=self.prompt,
                context=self.context,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            ):
                if self._stop_requested:
                    break

                self._accumulated_response += chunk
                self.chunk_received.emit(chunk)

                # 模拟进度更新
                progress = min(len(self._accumulated_response) // 10, 100)
                self.progress_updated.emit(progress)

            if not self._stop_requested:
                self.response_completed.emit(self._accumulated_response)

        except Exception as e:
            logger.error(f"流式响应处理失败: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        """停止流式生成"""
        self._stop_requested = True


def create_task_configs() -> dict[AITaskType, AITaskConfig]:
    """创建AI任务配置"""
    return {
        # 全局分析类
        AITaskType.PROJECT_ANALYSIS: AITaskConfig(
            task_type=AITaskType.PROJECT_ANALYSIS,
            title="项目分析",
            description="深度分析项目结构、内容质量、角色关系和情节发展",
            icon="🔍",
            prompt_template="""
作为专业的小说编辑，请对以下项目进行全面深度分析：

{project_content}

请从以下维度进行分析：
1. 整体结构和架构
2. 角色塑造和发展
3. 情节设计和节奏
4. 语言风格和表达
5. 主题深度和意义
6. 读者体验和吸引力
7. 改进建议和优化方向

请提供详细、专业的分析报告。
""",
            max_tokens=3000,
            temperature=0.3
        ),
        
        AITaskType.OUTLINE_GENERATION: AITaskConfig(
            task_type=AITaskType.OUTLINE_GENERATION,
            title="大纲生成",
            description="基于现有内容生成详细的故事大纲",
            icon="📋",
            prompt_template="""
基于以下项目内容，生成详细的故事大纲：

{project_content}

请生成包含以下要素的大纲：
1. 主要情节线
2. 关键转折点
3. 角色发展弧线
4. 章节结构建议
5. 冲突设置
6. 高潮和结局安排

请确保大纲逻辑清晰，结构完整。
""",
            max_tokens=2500,
            temperature=0.4
        ),
        
        # 写作助手类
        AITaskType.WRITING_CONTINUATION: AITaskConfig(
            task_type=AITaskType.WRITING_CONTINUATION,
            title="续写内容",
            description="基于当前内容智能续写",
            icon="✍️",
            prompt_template="""
请基于以下内容进行自然的续写：

{content}

续写要求：
1. 保持原有的写作风格和语调
2. 确保情节连贯性
3. 保持角色性格一致
4. 推进故事发展
5. 语言流畅自然

请续写300-500字的内容。
""",
            max_tokens=800,
            temperature=0.7
        ),
        
        # 内容工具类
        AITaskType.TEXT_REWRITING: AITaskConfig(
            task_type=AITaskType.TEXT_REWRITING,
            title="改写优化",
            description="改写和优化文本内容",
            icon="🔄",
            prompt_template="""
请对以下文本进行改写和优化：

{content}

优化要求：
1. 提升语言表达的准确性和生动性
2. 增强文本的可读性和流畅性
3. 保持原意不变
4. 优化句式结构
5. 增强感染力

请提供改写后的版本。
""",
            max_tokens=1000,
            temperature=0.6
        )
    }

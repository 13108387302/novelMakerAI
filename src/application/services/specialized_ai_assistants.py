#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专属AI助手系统 - 重构版本

为不同类型的文档提供专门的AI助手和功能，使用配置驱动的方式减少重复代码
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.application.services.ai_service import AIService
from src.shared.utils.logger import get_logger
from src.shared.utils.error_handler import handle_async_errors, ApplicationError

logger = get_logger(__name__)


class DocumentType(Enum):
    """文档类型枚举"""
    CHAPTER = "chapter"
    CHARACTER = "character"
    SETTING = "setting"
    OUTLINE = "outline"
    NOTE = "note"
    PLOT = "plot"


@dataclass
class AIPromptTemplate:
    """AI提示词模板"""
    name: str
    template: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def format(self, **kwargs) -> str:
        """格式化模板"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ApplicationError(f"模板参数缺失: {e}")


@dataclass
class AssistantConfig:
    """助手配置"""
    document_type: DocumentType
    name: str
    description: str
    prompt_templates: Dict[str, AIPromptTemplate] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    
    def add_template(self, template: AIPromptTemplate):
        """添加模板"""
        self.prompt_templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[AIPromptTemplate]:
        """获取模板"""
        return self.prompt_templates.get(name)


class StreamingAIAssistant(QThread):
    """流式AI助手基类"""
    
    # 信号定义
    chunk_received = pyqtSignal(str)  # 接收到的文本块
    response_completed = pyqtSignal(str)  # 完整响应
    error_occurred = pyqtSignal(str)  # 错误信息
    progress_updated = pyqtSignal(int)  # 进度更新 (0-100)
    
    def __init__(self, ai_service: AIService, config: AssistantConfig):
        super().__init__()
        self.ai_service = ai_service
        self.config = config
        self._stop_requested = False
        self._current_task = None
        
    def run(self):
        """运行AI助手任务"""
        loop = None
        try:
            if self._current_task:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._execute_task())
        except Exception as e:
            logger.error(f"AI助手任务执行失败: {e}")
            self.error_occurred.emit(str(e))
        finally:
            if loop and not loop.is_closed():
                try:
                    # 取消所有待处理的任务
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        for task in pending:
                            if not task.done():
                                task.cancel()
                        # 等待任务取消完成
                        try:
                            loop.run_until_complete(
                                asyncio.wait_for(
                                    asyncio.gather(*pending, return_exceptions=True),
                                    timeout=2.0
                                )
                            )
                        except asyncio.TimeoutError:
                            logger.warning("等待任务取消超时")
                    loop.close()
                except Exception as e:
                    logger.warning(f"清理事件循环失败: {e}")
    
    @handle_async_errors("AI助手任务执行")
    async def _execute_task(self):
        """执行AI任务"""
        if not self._current_task:
            return
            
        task_type, prompt, context = self._current_task
        
        try:
            # 使用流式生成
            accumulated_response = ""
            chunk_count = 0
            
            async for chunk in self.ai_service.generate_text_stream(prompt, context):
                if self._stop_requested:
                    break
                    
                accumulated_response += chunk
                self.chunk_received.emit(chunk)
                
                chunk_count += 1
                if chunk_count % 5 == 0:  # 每5个块更新一次进度
                    progress = min(90, chunk_count * 2)
                    self.progress_updated.emit(progress)
            
            if not self._stop_requested:
                self.progress_updated.emit(100)
                self.response_completed.emit(accumulated_response)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def start_task(self, task_type: str, prompt: str, context: str = ""):
        """开始AI任务"""
        if self.isRunning():
            self.stop_task()
            if not self.wait(3000):  # 等待3秒
                logger.warning("停止AI任务超时，强制终止")
                self.terminate()
                self.wait()

        self._current_task = (task_type, prompt, context)
        self._stop_requested = False
        self.start()
    
    def stop_task(self):
        """停止AI任务"""
        self._stop_requested = True
    
    def get_capabilities(self) -> List[str]:
        """获取助手能力"""
        return self.config.capabilities.copy()
    
    def has_capability(self, capability: str) -> bool:
        """检查是否有指定能力"""
        return capability in self.config.capabilities


class SpecializedAIManager:
    """专属AI管理器"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self._assistants: Dict[DocumentType, StreamingAIAssistant] = {}
        self._configs: Dict[DocumentType, AssistantConfig] = {}
        
        # 初始化配置
        self._init_configs()
        
    def _init_configs(self):
        """初始化助手配置"""
        # 章节助手配置
        chapter_config = AssistantConfig(
            document_type=DocumentType.CHAPTER,
            name="章节助手",
            description="专门协助章节写作的AI助手",
            capabilities=["续写", "改写", "扩展", "压缩", "风格调整"]
        )
        
        # 添加章节模板
        chapter_config.add_template(AIPromptTemplate(
            name="续写",
            template="请为以下章节内容生成自然流畅的续写：\n\n{content}\n\n续写内容：",
            description="章节续写模板"
        ))

        chapter_config.add_template(AIPromptTemplate(
            name="continuation",
            template="请为以下章节内容生成自然流畅的续写：\n\n{content}\n\n续写内容：",
            description="章节续写模板（英文名）"
        ))
        
        chapter_config.add_template(AIPromptTemplate(
            name="改写",
            template="请改写以下章节内容，{style_requirement}：\n\n{content}\n\n改写后的内容：",
            description="章节改写模板",
            parameters={"style_requirement": "保持原意但改进表达"}
        ))
        
        self._configs[DocumentType.CHAPTER] = chapter_config
        
        # 角色助手配置
        character_config = AssistantConfig(
            document_type=DocumentType.CHARACTER,
            name="角色助手",
            description="专门协助角色设定的AI助手",
            capabilities=["角色分析", "性格描述", "背景设定", "关系分析"]
        )
        
        character_config.add_template(AIPromptTemplate(
            name="角色分析",
            template="请分析以下角色的性格特征和发展轨迹：\n\n{character_info}\n\n分析结果：",
            description="角色分析模板"
        ))

        character_config.add_template(AIPromptTemplate(
            name="character_analysis",
            template="请分析以下角色的性格特征和发展轨迹：\n\n{character_info}\n\n分析结果：",
            description="角色分析模板（英文名）"
        ))
        
        self._configs[DocumentType.CHARACTER] = character_config
        
        # 设定助手配置
        setting_config = AssistantConfig(
            document_type=DocumentType.SETTING,
            name="设定助手", 
            description="专门协助世界观设定的AI助手",
            capabilities=["世界观构建", "场景描述", "背景设定", "氛围营造"]
        )
        
        setting_config.add_template(AIPromptTemplate(
            name="场景描述",
            template="请详细描述以下场景，注重{focus_aspect}：\n\n{scene_info}\n\n场景描述：",
            description="场景描述模板",
            parameters={"focus_aspect": "氛围营造"}
        ))
        
        self._configs[DocumentType.SETTING] = setting_config
        
        # 大纲助手配置
        outline_config = AssistantConfig(
            document_type=DocumentType.OUTLINE,
            name="大纲助手",
            description="专门协助情节大纲的AI助手", 
            capabilities=["情节规划", "结构分析", "冲突设计", "节奏控制"]
        )
        
        outline_config.add_template(AIPromptTemplate(
            name="情节规划",
            template="请为以下故事主题制定详细的情节大纲：\n\n主题：{theme}\n类型：{genre}\n\n情节大纲：",
            description="情节规划模板"
        ))
        
        self._configs[DocumentType.OUTLINE] = outline_config
        
        # 笔记助手配置
        note_config = AssistantConfig(
            document_type=DocumentType.NOTE,
            name="笔记助手",
            description="专门协助笔记整理的AI助手",
            capabilities=["内容整理", "要点提取", "分类归纳", "总结概括"]
        )
        
        note_config.add_template(AIPromptTemplate(
            name="内容整理",
            template="请整理以下笔记内容，提取关键信息：\n\n{notes}\n\n整理后的内容：",
            description="笔记整理模板"
        ))
        
        self._configs[DocumentType.NOTE] = note_config
    
    def get_assistant(self, document_type: DocumentType) -> Optional[StreamingAIAssistant]:
        """获取指定类型的助手"""
        if document_type not in self._assistants:
            config = self._configs.get(document_type)
            if config:
                self._assistants[document_type] = StreamingAIAssistant(self.ai_service, config)
        
        return self._assistants.get(document_type)
    
    def get_config(self, document_type: DocumentType) -> Optional[AssistantConfig]:
        """获取助手配置"""
        return self._configs.get(document_type)
    
    def get_available_types(self) -> List[DocumentType]:
        """获取可用的文档类型"""
        return list(self._configs.keys())
    
    def execute_task(self, document_type: DocumentType, task_type: str,
                    task_data: Dict[str, Any]) -> Optional[StreamingAIAssistant]:
        """执行AI任务"""
        assistant = self.get_assistant(document_type)
        if not assistant:
            logger.error(f"未找到文档类型 {document_type} 的助手")
            return None

        config = self.get_config(document_type)
        template = config.get_template(task_type)

        if not template:
            logger.error(f"未找到任务类型 {task_type} 的模板")
            return None

        try:
            # 格式化提示词
            prompt = template.format(**task_data)

            # 启动任务
            assistant.start_task(task_type, prompt)

            return assistant

        except Exception as e:
            logger.error(f"执行AI任务失败: {e}")
            return None

    async def execute_task_async(self, document_type: DocumentType, task_type: str,
                               task_data: Dict[str, Any]) -> Optional[str]:
        """异步执行AI任务并返回结果"""
        try:
            assistant = self.execute_task(document_type, task_type, task_data)
            if not assistant:
                return None

            # 等待任务完成（简单实现）
            import time
            timeout = 30  # 30秒超时
            start_time = time.time()

            while assistant.isRunning() and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)

            if assistant.isRunning():
                logger.warning(f"AI任务超时: {task_type}")
                assistant.stop_task()
                return None

            # 这里应该有获取结果的方法，暂时返回成功标志
            return "任务执行完成"

        except Exception as e:
            logger.error(f"异步执行AI任务失败: {e}")
            return None
    
    def stop_all_tasks(self):
        """停止所有任务"""
        for assistant in self._assistants.values():
            if assistant.isRunning():
                assistant.stop_task()
                if not assistant.wait(3000):  # 等待3秒
                    logger.warning("停止AI助手超时，强制终止")
                    assistant.terminate()
                    assistant.wait()
    
    def get_assistant_status(self) -> Dict[DocumentType, bool]:
        """获取所有助手的状态"""
        status = {}
        for doc_type, assistant in self._assistants.items():
            status[doc_type] = assistant.isRunning()
        return status

    def cleanup(self):
        """清理所有资源"""
        try:
            self.stop_all_tasks()
            for assistant in self._assistants.values():
                assistant.deleteLater()
            self._assistants.clear()
            logger.info("专门化AI助手管理器清理完成")
        except Exception as e:
            logger.error(f"清理专门化AI助手失败: {e}")

    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except Exception:
            pass

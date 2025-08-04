#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI助手管理器

为每个文档标签页管理独立的AI助手实例
"""

import asyncio
from typing import Dict, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import QWidget

from src.application.services.ai_service import AIService
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentAIAssistant(QObject):
    """
    文档专属AI助手

    为每个文档提供独立的AI助手实例，管理文档相关的AI操作。
    支持续写、改写、分析等多种AI功能，并提供状态管理和请求取消功能。

    实现方式：
    - 继承QObject提供信号槽机制
    - 维护文档ID和AI服务的关联
    - 提供忙碌状态检查和请求管理
    - 使用异步方法处理AI请求
    - 发出信号通知UI更新

    Attributes:
        document_id: 关联的文档ID
        ai_service: AI服务实例
        _is_busy: 当前是否有正在处理的请求
        _current_request: 当前正在执行的请求任务

    Signals:
        response_ready: AI响应就绪信号(请求类型, 响应内容)
        error_occurred: 错误发生信号(请求类型, 错误信息)
        progress_updated: 进度更新信号(请求类型, 进度百分比)
    """

    # 信号定义
    response_ready = pyqtSignal(str, str)  # request_type, response
    error_occurred = pyqtSignal(str, str)  # request_type, error
    progress_updated = pyqtSignal(str, int)  # request_type, progress

    def __init__(self, document_id: str, ai_service: AIService, parent=None):
        """
        初始化文档AI助手

        创建与特定文档关联的AI助手实例。

        Args:
            document_id: 文档的唯一标识符
            ai_service: AI服务实例
            parent: 父QObject，用于内存管理
        """
        super().__init__(parent)
        self.document_id = document_id
        self.ai_service = ai_service
        self._is_busy = False
        self._current_request = None

        logger.info(f"为文档 {document_id} 创建AI助手")
    
    @property
    def is_busy(self) -> bool:
        """
        检查AI助手是否忙碌

        返回当前AI助手是否正在处理请求的状态。

        Returns:
            bool: True表示正在处理请求，False表示空闲
        """
        return self._is_busy

    def cancel_current_request(self):
        """
        取消当前正在执行的AI请求

        如果有正在执行的请求，将其取消并重置忙碌状态。
        用于用户主动取消或切换文档时的清理操作。

        实现方式：
        - 检查当前请求是否存在且未完成
        - 调用asyncio任务的cancel方法
        - 重置忙碌状态标志
        - 记录取消操作的日志
        """
        if self._current_request and not self._current_request.done():
            self._current_request.cancel()
            self._is_busy = False
            logger.info(f"取消文档 {self.document_id} 的AI请求")

    async def request_continuation(self, context: str, selected_text: str = "") -> None:
        """
        请求AI续写内容

        基于提供的上下文和可选的选中文本，请求AI生成续写内容。

        实现方式：
        - 检查助手是否忙碌，避免并发请求
        - 构建包含上下文和选中文本的提示
        - 创建异步任务执行AI请求
        - 发出进度和结果信号
        - 处理异常情况并重置状态

        Args:
            context: 文档上下文内容
            selected_text: 用户选中的文本（可选）

        Note:
            如果助手正忙，会发出错误信号而不执行请求
        """
        if self._is_busy:
            self.error_occurred.emit("continuation", "AI助手正在处理其他请求")
            return
        
        try:
            self._is_busy = True
            self.progress_updated.emit("continuation", 0)
            
            # 构建续写提示
            prompt = f"请基于以下内容进行续写：\n\n{context}"
            if selected_text:
                prompt += f"\n\n特别关注这部分内容：{selected_text}"
            
            # 发送AI请求
            self._current_request = asyncio.create_task(
                self.ai_service.generate_text(prompt)
            )
            
            response = await self._current_request
            
            if response:
                self.response_ready.emit("continuation", response)
                logger.info(f"文档 {self.document_id} AI续写完成")
            else:
                self.error_occurred.emit("continuation", "AI服务返回空响应")
                
        except asyncio.CancelledError:
            logger.info(f"文档 {self.document_id} AI续写请求被取消")
        except Exception as e:
            logger.error(f"文档 {self.document_id} AI续写失败: {e}")
            self.error_occurred.emit("continuation", str(e))
        finally:
            self._is_busy = False
            self._current_request = None

    async def continue_writing(self, context: str, selected_text: str = "") -> None:
        """
        续写内容（request_continuation的别名方法）

        Args:
            context: 文档上下文内容
            selected_text: 用户选中的文本（可选）
        """
        await self.request_continuation(context, selected_text)
    
    async def improve_text(self, text: str, improvement_type: str = "general") -> None:
        """改进文本"""
        if self._is_busy:
            self.error_occurred.emit("improve", "AI助手正在处理其他请求")
            return
        
        try:
            self._is_busy = True
            self.progress_updated.emit("improve", 0)
            
            # 构建改进提示
            improvement_prompts = {
                "general": "请改进以下文本，使其更加流畅和生动：",
                "dialogue": "请优化以下对话，使其更加自然和有趣：",
                "scene": "请扩展以下场景描述，使其更加详细和生动：",
                "style": "请分析以下文本的写作风格并提供改进建议："
            }
            
            prompt = improvement_prompts.get(improvement_type, improvement_prompts["general"])
            prompt += f"\n\n{text}"
            
            # 发送AI请求
            self._current_request = asyncio.create_task(
                self.ai_service.generate_text(prompt)
            )
            
            response = await self._current_request
            
            if response:
                self.response_ready.emit("improve", response)
                logger.info(f"文档 {self.document_id} AI改进完成")
            else:
                self.error_occurred.emit("improve", "AI服务返回空响应")
                
        except asyncio.CancelledError:
            logger.info(f"文档 {self.document_id} AI改进请求被取消")
        except Exception as e:
            logger.error(f"文档 {self.document_id} AI改进失败: {e}")
            self.error_occurred.emit("improve", str(e))
        finally:
            self._is_busy = False
            self._current_request = None
    
    async def analyze_style(self, text: str) -> None:
        """分析写作风格"""
        if self._is_busy:
            self.error_occurred.emit("analyze", "AI助手正在处理其他请求")
            return
        
        try:
            self._is_busy = True
            self.progress_updated.emit("analyze", 0)
            
            prompt = f"请分析以下文本的写作风格，包括语言特点、叙述方式、情感色彩等：\n\n{text}"
            
            # 发送AI请求
            self._current_request = asyncio.create_task(
                self.ai_service.generate_text(prompt)
            )
            
            response = await self._current_request
            
            if response:
                self.response_ready.emit("analyze", response)
                logger.info(f"文档 {self.document_id} AI风格分析完成")
            else:
                self.error_occurred.emit("analyze", "AI服务返回空响应")
                
        except asyncio.CancelledError:
            logger.info(f"文档 {self.document_id} AI风格分析请求被取消")
        except Exception as e:
            logger.error(f"文档 {self.document_id} AI风格分析失败: {e}")
            self.error_occurred.emit("analyze", str(e))
        finally:
            self._is_busy = False
            self._current_request = None


class AIAssistantManager(QObject):
    """
    AI助手管理器

    管理多个文档的AI助手实例，提供助手的创建、获取、移除和清理功能。
    确保每个文档都有独立的AI助手，避免请求冲突。

    实现方式：
    - 维护文档ID到AI助手的映射字典
    - 提供助手生命周期管理方法
    - 确保助手的正确创建和清理
    - 支持批量操作和状态查询

    Attributes:
        ai_service: 共享的AI服务实例
        _assistants: 文档ID到AI助手的映射字典
    """

    def __init__(self, ai_service: AIService, parent=None):
        """
        初始化AI助手管理器

        Args:
            ai_service: AI服务实例，将被所有助手共享
            parent: 父QObject，用于内存管理
        """
        super().__init__(parent)
        self.ai_service = ai_service
        self._assistants: Dict[str, DocumentAIAssistant] = {}

        logger.info("AI助手管理器初始化完成")

    def create_assistant(self, document_id: str) -> DocumentAIAssistant:
        """
        为指定文档创建AI助手

        如果助手已存在则返回现有实例，否则创建新的助手实例。

        Args:
            document_id: 文档的唯一标识符

        Returns:
            DocumentAIAssistant: 文档的AI助手实例
        """
        if document_id in self._assistants:
            logger.warning(f"文档 {document_id} 的AI助手已存在")
            return self._assistants[document_id]

        assistant = DocumentAIAssistant(document_id, self.ai_service, self)
        self._assistants[document_id] = assistant

        logger.info(f"为文档 {document_id} 创建AI助手成功")
        return assistant

    def get_assistant(self, document_id: str) -> Optional[DocumentAIAssistant]:
        """
        获取指定文档的AI助手

        Args:
            document_id: 文档的唯一标识符

        Returns:
            Optional[DocumentAIAssistant]: AI助手实例，如果不存在则返回None
        """
        return self._assistants.get(document_id)

    def remove_assistant(self, document_id: str) -> bool:
        """
        移除指定文档的AI助手

        取消助手的当前请求并从管理器中移除。

        Args:
            document_id: 文档的唯一标识符

        Returns:
            bool: 移除成功返回True，助手不存在返回False
        """
        if document_id not in self._assistants:
            return False
        
        assistant = self._assistants[document_id]
        
        # 取消当前请求
        assistant.cancel_current_request()
        
        # 移除助手
        del self._assistants[document_id]
        
        logger.info(f"移除文档 {document_id} 的AI助手")
        return True
    
    def get_active_assistants(self) -> Dict[str, DocumentAIAssistant]:
        """获取所有活跃的AI助手"""
        return self._assistants.copy()
    
    def cancel_all_requests(self):
        """取消所有AI请求"""
        for assistant in self._assistants.values():
            assistant.cancel_current_request()
        
        logger.info("取消所有AI请求")
    
    def cleanup(self):
        """清理资源"""
        self.cancel_all_requests()
        self._assistants.clear()
        logger.info("AI助手管理器清理完成")


class AIRequestExecutor(QObject):
    """AI请求执行器 - 在单独线程中执行AI请求"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop = None
        self._thread = None
        self._is_running = False

    def start(self):
        """启动执行器"""
        if self._is_running:
            logger.warning("AI请求执行器已在运行")
            return

        if self._thread and self._thread.isRunning():
            logger.warning("线程已在运行")
            return

        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._setup_event_loop)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

        logger.info("AI请求执行器启动")

    def stop(self):
        """停止执行器"""
        if not self._is_running:
            return

        self._is_running = False

        if self._loop and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except RuntimeError:
                # 循环可能已经停止
                pass

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(5000):  # 等待5秒
                logger.warning("线程停止超时，强制终止")
                self._thread.terminate()
                self._thread.wait()

        logger.info("AI请求执行器停止")

    def _setup_event_loop(self):
        """设置事件循环"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._is_running = True
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"设置事件循环失败: {e}")
        finally:
            self._is_running = False

    def _on_thread_finished(self):
        """线程结束处理"""
        self._is_running = False
        if self._loop and not self._loop.is_closed():
            self._loop.close()
        logger.debug("AI请求执行器线程结束")

    def execute_async(self, coro):
        """执行异步协程"""
        if not self._is_running:
            logger.error("执行器未运行")
            return None

        if not self._loop:
            logger.error("事件循环未初始化")
            return None

        if not self._thread or not self._thread.isRunning():
            logger.error("执行线程未运行")
            return None

        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future
        except Exception as e:
            logger.error(f"执行异步协程失败: {e}")
            return None

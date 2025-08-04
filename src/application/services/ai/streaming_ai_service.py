#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式AI服务

处理流式AI文本生成功能
"""

import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal

from .base_ai_service import BaseAIService, AIServiceError
from src.domain.repositories.ai_service_repository import IAIServiceRepository
from src.shared.events.event_bus import EventBus
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class StreamingAIWorker(QThread):
    """流式AI工作线程"""

    # 信号定义
    chunk_received = pyqtSignal(str)  # 接收到的文本块
    response_completed = pyqtSignal(str)  # 完整响应
    error_occurred = pyqtSignal(str)  # 错误信息
    progress_updated = pyqtSignal(int)  # 进度更新

    def __init__(self, ai_repository: IAIServiceRepository, prompt: str, context: str = ""):
        super().__init__()
        self.ai_repository = ai_repository
        self.prompt = prompt
        self.context = context
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
            logger.error(f"流式AI工作线程错误: {e}")
            self.error_occurred.emit(str(e))
        finally:
            # 清理事件循环
            try:
                loop.close()
            except:
                pass

    async def _stream_response(self):
        """流式响应处理"""
        try:
            chunk_count = 0
            async for chunk in self.ai_repository.generate_text_stream(self.prompt, self.context):
                if self._stop_requested:
                    break
                    
                if chunk:
                    self._accumulated_response += chunk
                    self.chunk_received.emit(chunk)
                    
                    chunk_count += 1
                    # 每10个块更新一次进度
                    if chunk_count % 10 == 0:
                        self.progress_updated.emit(min(90, chunk_count))
                        
            if not self._stop_requested:
                self.progress_updated.emit(100)
                self.response_completed.emit(self._accumulated_response)
                
        except Exception as e:
            logger.error(f"流式响应处理错误: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        """停止流式生成"""
        self._stop_requested = True


class StreamingAIService(BaseAIService):
    """流式AI服务"""
    
    # 流式生成信号
    streaming_started = pyqtSignal()
    streaming_stopped = pyqtSignal()
    chunk_received = pyqtSignal(str)
    streaming_completed = pyqtSignal(str)
    streaming_error = pyqtSignal(str)
    streaming_progress = pyqtSignal(int)
    
    def __init__(
        self,
        ai_repository: IAIServiceRepository,
        event_bus: EventBus
    ):
        super().__init__(ai_repository, event_bus)
        
        # 流式生成状态
        self._current_worker: Optional[StreamingAIWorker] = None
        self._is_streaming = False
        
    async def _do_generate_text(self, prompt: str, context: str = "") -> str:
        """具体的文本生成实现"""
        return await self.ai_repository.generate_text(prompt, context)
        
    async def generate_text_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """流式生成文本"""
        try:
            async for chunk in self.ai_repository.generate_text_stream(prompt, context):
                yield chunk
        except Exception as e:
            logger.error(f"流式文本生成失败: {e}")
            raise AIServiceError(f"流式文本生成失败: {e}")
            
    def start_streaming(self, prompt: str, context: str = "") -> bool:
        """开始流式生成"""
        try:
            if self._is_streaming:
                logger.warning("已有流式生成在进行中")
                return False
                
            # 创建工作线程
            self._current_worker = StreamingAIWorker(self.ai_repository, prompt, context)
            
            # 连接信号
            self._current_worker.chunk_received.connect(self._on_chunk_received)
            self._current_worker.response_completed.connect(self._on_streaming_completed)
            self._current_worker.error_occurred.connect(self._on_streaming_error)
            self._current_worker.progress_updated.connect(self._on_progress_updated)
            self._current_worker.finished.connect(self._on_worker_finished)
            
            # 启动线程
            self._current_worker.start()
            self._is_streaming = True
            
            # 发出开始信号
            self.streaming_started.emit()
            
            logger.info("流式AI生成已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动流式生成失败: {e}")
            self.streaming_error.emit(str(e))
            return False
            
    def stop_streaming(self):
        """停止流式生成"""
        try:
            if self._current_worker and self._current_worker.isRunning():
                self._current_worker.stop()
                self._current_worker.wait(3000)  # 等待最多3秒
                
                if self._current_worker.isRunning():
                    self._current_worker.terminate()
                    self._current_worker.wait(1000)
                    
            self._cleanup_worker()
            
        except Exception as e:
            logger.error(f"停止流式生成失败: {e}")
            
    def is_streaming(self) -> bool:
        """检查是否正在流式生成"""
        return self._is_streaming and self._current_worker is not None and self._current_worker.isRunning()
        
    def _on_chunk_received(self, chunk: str):
        """处理接收到的文本块"""
        self.chunk_received.emit(chunk)
        
    def _on_streaming_completed(self, response: str):
        """处理流式生成完成"""
        self.streaming_completed.emit(response)
        logger.info("流式AI生成完成")
        
    def _on_streaming_error(self, error: str):
        """处理流式生成错误"""
        self.streaming_error.emit(error)
        logger.error(f"流式AI生成错误: {error}")
        
    def _on_progress_updated(self, progress: int):
        """处理进度更新"""
        self.streaming_progress.emit(progress)
        
    def _on_worker_finished(self):
        """处理工作线程完成"""
        self._cleanup_worker()
        
    def _cleanup_worker(self):
        """清理工作线程"""
        if self._current_worker:
            self._current_worker.deleteLater()
            self._current_worker = None

        self._is_streaming = False
        self.streaming_stopped.emit()

    def __del__(self):
        """析构函数 - 确保资源清理"""
        try:
            self.stop_streaming()
        except Exception as e:
            # 在析构函数中不应该抛出异常
            pass
        
    def get_streaming_status(self) -> dict:
        """获取流式生成状态"""
        return {
            "is_streaming": self.is_streaming(),
            "worker_active": self._current_worker is not None and self._current_worker.isRunning(),
            "worker_state": self._current_worker.state().name if self._current_worker else "None"
        }
        
    def get_supported_features(self) -> list[str]:
        """获取支持的功能"""
        base_features = super().get_supported_features()
        streaming_features = [
            "streaming_generation",
            "streaming_control",
            "progress_tracking",
            "real_time_output"
        ]
        return base_features + streaming_features
        
    # 便捷方法
    async def generate_streaming_continuation(self, content: str, context: str = "") -> bool:
        """生成流式续写"""
        prompt = f"请为以下内容生成自然流畅的续写：\n\n{content}"
        return self.start_streaming(prompt, context)
        
    async def generate_streaming_dialogue_improvement(self, dialogue: str) -> bool:
        """生成流式对话优化"""
        prompt = f"请优化以下对话，使其更加自然生动：\n\n{dialogue}"
        return self.start_streaming(prompt)
        
    async def generate_streaming_scene_expansion(self, scene: str) -> bool:
        """生成流式场景扩展"""
        prompt = f"请扩展以下场景的描写，增加更多细节和氛围：\n\n{scene}"
        return self.start_streaming(prompt)
        
    def __del__(self):
        """析构函数"""
        try:
            self.stop_streaming()
        except:
            pass

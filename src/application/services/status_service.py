#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态服务 - 收集和管理应用程序的真实状态数据
"""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from src.shared.utils.logger import get_logger
from src.domain.entities.project import Project
from src.domain.entities.document import Document

logger = get_logger(__name__)


class StatusService(QObject):
    """状态服务 - 收集真实的应用程序状态数据"""
    
    # 信号定义
    status_updated = pyqtSignal(dict)  # 状态更新信号
    performance_warning = pyqtSignal(str)  # 性能警告信号
    
    def __init__(self):
        super().__init__()
        
        # 会话开始时间
        self.session_start_time = datetime.now()
        
        # 统计数据
        self.statistics = {
            "total_words": 0,
            "total_documents": 0,
            "session_words": 0,
            "ai_requests": 0,
            "ai_success_count": 0,
            "ai_error_count": 0,
            "last_save_time": None,
            "documents_opened": 0,
            "projects_opened": 0
        }
        
        # 性能数据
        self.performance_data = {
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "response_times": [],
            "error_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 当前状态
        self.current_project: Optional[Project] = None
        self.current_document: Optional[Document] = None
        self.ai_status = "空闲"
        
        # 更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._collect_system_data)
        self.update_timer.start(5000)  # 每5秒更新一次
        
        logger.info("状态服务初始化完成")
    
    def _collect_system_data(self):
        """收集系统数据（优化版本，避免阻塞）"""
        try:
            # 收集内存使用率
            memory = psutil.virtual_memory()
            self.performance_data["memory_usage"] = memory.percent

            # 优化的CPU使用率收集（避免阻塞）
            # 使用非阻塞方式获取CPU使用率
            if not hasattr(self, '_last_cpu_times'):
                # 第一次调用，初始化CPU时间
                self._last_cpu_times = psutil.cpu_times()
                self._last_cpu_check = time.time()
                # 使用一个合理的初始值
                self.performance_data["cpu_usage"] = 5.0
            else:
                # 计算CPU使用率
                current_cpu_times = psutil.cpu_times()
                current_time = time.time()

                time_delta = current_time - self._last_cpu_check
                if time_delta > 0:
                    # 计算CPU使用率
                    total_delta = sum(current_cpu_times) - sum(self._last_cpu_times)
                    idle_delta = current_cpu_times.idle - self._last_cpu_times.idle

                    if total_delta > 0:
                        cpu_percent = max(0, min(100, (1 - idle_delta / total_delta) * 100))
                        self.performance_data["cpu_usage"] = cpu_percent

                    # 更新记录
                    self._last_cpu_times = current_cpu_times
                    self._last_cpu_check = current_time

            # 检查性能警告
            if memory.percent > 80:
                self.performance_warning.emit(f"内存使用率过高: {memory.percent:.1f}%")

            cpu_usage = self.performance_data.get("cpu_usage", 0)
            if cpu_usage > 90:
                self.performance_warning.emit(f"CPU使用率过高: {cpu_usage:.1f}%")

            if self.performance_data["cpu_usage"] > 80:
                self.performance_warning.emit(f"CPU使用率过高: {self.performance_data['cpu_usage']:.1f}%")

            # 发送状态更新信号
            self.status_updated.emit(self.get_all_statistics())

        except Exception as e:
            logger.error(f"收集系统数据失败: {e}")
            # 使用默认值
            self.performance_data["memory_usage"] = 25.0
            self.performance_data["cpu_usage"] = 10.0
    
    def set_current_project(self, project: Optional[Project]):
        """设置当前项目"""
        self.current_project = project
        if project:
            self.statistics["projects_opened"] += 1
            logger.info(f"当前项目设置为: {project.name}")

        # 立即发送状态更新信号
        self.status_updated.emit(self.get_all_statistics())

    def set_current_document(self, document: Optional[Document]):
        """设置当前文档"""
        self.current_document = document
        if document:
            self.statistics["documents_opened"] += 1
            logger.info(f"当前文档设置为: {document.title}")

        # 立即发送状态更新信号
        self.status_updated.emit(self.get_all_statistics())
    
    def update_project_statistics(self, documents: List[Document]):
        """更新项目统计数据（优先使用实体统计，回退到内容统计）"""
        try:
            total_words = 0
            total_docs = len(documents)

            for doc in documents:
                # 优先使用实体自带统计（更准确/更快）
                try:
                    stats = getattr(doc, 'statistics', None)
                    if stats and getattr(stats, 'word_count', None) is not None:
                        total_words += int(stats.word_count)
                        continue
                except Exception:
                    pass
                # 回退：基于内容粗略统计（去除空白）
                try:
                    content = getattr(doc, 'content', None) or ""
                    if content:
                        words = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
                        total_words += words
                except Exception:
                    pass

            self.statistics["total_words"] = total_words
            self.statistics["total_documents"] = total_docs

            logger.debug(f"项目统计更新: {total_docs} 个文档, {total_words} 字")

            # 立即发送状态更新信号
            self.status_updated.emit(self.get_all_statistics())

        except Exception as e:
            logger.error(f"更新项目统计失败: {e}")

    def record_document_save(self, document: Document):
        """记录文档保存"""
        self.statistics["last_save_time"] = datetime.now()
        logger.info(f"文档保存记录: {document.title}")

        # 立即发送状态更新信号
        self.status_updated.emit(self.get_all_statistics())

    def record_ai_request(self, success: bool = True, response_time: float = 0):
        """记录AI请求"""
        self.statistics["ai_requests"] += 1

        if success:
            self.statistics["ai_success_count"] += 1
        else:
            self.statistics["ai_error_count"] += 1
            self.performance_data["error_count"] += 1

        if response_time > 0:
            self.performance_data["response_times"].append(response_time)
            # 只保留最近100次的响应时间
            if len(self.performance_data["response_times"]) > 100:
                self.performance_data["response_times"] = self.performance_data["response_times"][-100:]

        logger.debug(f"AI请求记录: 成功={success}, 响应时间={response_time:.3f}s")

        # 立即发送状态更新信号
        self.status_updated.emit(self.get_all_statistics())

    def record_session_words(self, words_added: int):
        """记录会话中新增的字数"""
        self.statistics["session_words"] += words_added
        logger.debug(f"会话字数增加: {words_added}")

        # 立即发送状态更新信号
        self.status_updated.emit(self.get_all_statistics())

    def set_ai_status(self, status: str):
        """设置AI状态"""
        self.ai_status = status
        logger.debug(f"AI状态更新: {status}")

        # 立即发送状态更新信号
        self.status_updated.emit(self.get_all_statistics())
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.performance_data["cache_hits"] += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.performance_data["cache_misses"] += 1
    
    def get_session_duration(self) -> timedelta:
        """获取会话持续时间"""
        return datetime.now() - self.session_start_time
    
    def get_ai_success_rate(self) -> float:
        """获取AI成功率"""
        total_requests = self.statistics["ai_requests"]
        if total_requests == 0:
            return 100.0
        return (self.statistics["ai_success_count"] / total_requests) * 100
    
    def get_average_response_time(self) -> float:
        """获取平均响应时间"""
        response_times = self.performance_data["response_times"]
        if not response_times:
            return 0.0
        return sum(response_times) / len(response_times)
    
    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total_cache_requests = self.performance_data["cache_hits"] + self.performance_data["cache_misses"]
        if total_cache_requests == 0:
            return 0.0
        return (self.performance_data["cache_hits"] / total_cache_requests) * 100
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """获取所有统计数据"""
        session_duration = self.get_session_duration()
        
        return {
            # 基础统计
            "total_words": self.statistics["total_words"],
            "total_documents": self.statistics["total_documents"],
            "session_words": self.statistics["session_words"],
            
            # AI统计
            "ai_requests": self.statistics["ai_requests"],
            "ai_success_rate": self.get_ai_success_rate(),
            "ai_avg_response_time": self.get_average_response_time(),
            
            # 会话信息
            "session_duration_minutes": int(session_duration.total_seconds() / 60),
            "last_save": self._format_last_save_time(),
            "documents_opened": self.statistics["documents_opened"],
            "projects_opened": self.statistics["projects_opened"],
            
            # 性能数据
            "memory_usage": self.performance_data["memory_usage"],
            "cpu_usage": self.performance_data["cpu_usage"],
            "error_count": self.performance_data["error_count"],
            "cache_hit_rate": self.get_cache_hit_rate(),
            "cache_size_mb": self._estimate_cache_size(),
            
            # 当前状态
            "current_project": self.current_project.name if self.current_project else "未打开",
            "current_document": self.current_document.title if self.current_document else "未打开",
            "ai_status": self.ai_status
        }
    
    def _format_last_save_time(self) -> str:
        """格式化最后保存时间"""
        if not self.statistics["last_save_time"]:
            return "从未"
        
        now = datetime.now()
        diff = now - self.statistics["last_save_time"]
        
        if diff.total_seconds() < 60:
            return "刚刚"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}分钟前"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}小时前"
        else:
            return self.statistics["last_save_time"].strftime("%Y-%m-%d %H:%M")
    
    def _estimate_cache_size(self) -> float:
        """估算缓存大小（MB）"""
        # 这里可以根据实际的缓存实现来计算
        # 暂时返回一个估算值
        total_requests = self.performance_data["cache_hits"] + self.performance_data["cache_misses"]
        return total_requests * 0.1  # 假设每个缓存项约0.1MB
    
    def reset_session_statistics(self):
        """重置会话统计"""
        self.session_start_time = datetime.now()
        self.statistics["session_words"] = 0
        self.statistics["documents_opened"] = 0
        self.statistics["projects_opened"] = 0
        logger.info("会话统计已重置")
    
    def cleanup(self):
        """清理资源"""
        if self.update_timer.isActive():
            self.update_timer.stop()
        logger.info("状态服务清理完成")

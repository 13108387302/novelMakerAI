"""
文档预加载服务

智能预加载相邻文档和常用文档，提升用户体验和响应速度。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import asyncio
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

from src.domain.entities.document import Document
from src.domain.repositories.document_repository import IDocumentRepository
from src.shared.utils.logger import get_logger
from src.shared.utils.cache_manager import get_cache_manager

logger = get_logger(__name__)


@dataclass
class PreloadRequest:
    """预加载请求"""
    document_id: str
    priority: int = 1  # 1=低, 2=中, 3=高
    reason: str = ""
    requested_at: datetime = field(default_factory=datetime.now)


@dataclass
class PreloadStats:
    """预加载统计"""
    total_requests: int = 0
    successful_preloads: int = 0
    failed_preloads: int = 0
    cache_hits: int = 0
    avg_preload_time: float = 0.0
    memory_saved: int = 0  # 节省的内存（字节）


class DocumentPreloader:
    """
    文档预加载器
    
    智能预加载文档内容，提升用户体验：
    1. 相邻文档预加载：预加载当前文档前后的文档
    2. 常用文档预加载：基于访问频率预加载热门文档
    3. 智能预测：基于用户行为模式预测可能访问的文档
    4. 内存管理：控制预加载的内存使用，避免内存溢出
    """
    
    def __init__(self, document_repository: IDocumentRepository):
        self.document_repository = document_repository
        self.cache_manager = get_cache_manager()
        
        # 预加载队列和状态
        self.preload_queue = asyncio.Queue()
        self.preloading_documents: Set[str] = set()
        self.preloaded_documents: Dict[str, Document] = {}
        
        # 访问统计
        self.access_history = deque(maxlen=1000)  # 最近1000次访问记录
        self.access_frequency: Dict[str, int] = defaultdict(int)
        self.access_patterns: Dict[str, List[str]] = defaultdict(list)  # 文档ID -> 后续访问的文档列表
        
        # 配置
        self.max_preloaded_documents = 10  # 最大预加载文档数
        self.preload_timeout = 30.0  # 预加载超时时间
        self.adjacent_preload_count = 2  # 相邻文档预加载数量
        
        # 统计信息
        self.stats = PreloadStats()
        
        # 启动预加载工作线程
        self._preload_task = None
        self._start_preload_worker()
        
        logger.info("文档预加载器初始化完成")
    
    def _start_preload_worker(self):
        """启动预加载工作线程"""
        if self._preload_task is None or self._preload_task.done():
            self._preload_task = asyncio.create_task(self._preload_worker())
            logger.debug("预加载工作线程已启动")
    
    async def _preload_worker(self):
        """预加载工作线程"""
        while True:
            try:
                # 从队列获取预加载请求
                request = await asyncio.wait_for(self.preload_queue.get(), timeout=1.0)
                
                # 执行预加载
                await self._execute_preload(request)
                
                # 标记任务完成
                self.preload_queue.task_done()
                
            except asyncio.TimeoutError:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"预加载工作线程错误: {e}")
                await asyncio.sleep(1.0)  # 错误后等待1秒
    
    async def _execute_preload(self, request: PreloadRequest):
        """执行预加载"""
        try:
            if request.document_id in self.preloading_documents:
                logger.debug(f"文档已在预加载中: {request.document_id}")
                return
            
            if request.document_id in self.preloaded_documents:
                logger.debug(f"文档已预加载: {request.document_id}")
                self.stats.cache_hits += 1
                return
            
            self.preloading_documents.add(request.document_id)
            start_time = time.time()
            
            logger.info(f"开始预加载文档: {request.document_id} (原因: {request.reason})")
            
            # 检查内存使用
            if len(self.preloaded_documents) >= self.max_preloaded_documents:
                self._cleanup_old_preloads()
            
            # 加载文档元数据
            document = await asyncio.wait_for(
                self.document_repository.load_metadata_only(request.document_id),
                timeout=self.preload_timeout
            )
            
            if document:
                # 存储预加载的文档
                self.preloaded_documents[request.document_id] = document
                
                # 更新统计
                preload_time = time.time() - start_time
                self.stats.successful_preloads += 1
                self.stats.avg_preload_time = (
                    (self.stats.avg_preload_time * (self.stats.successful_preloads - 1) + preload_time) 
                    / self.stats.successful_preloads
                )
                
                logger.info(f"预加载完成: {request.document_id}, 耗时: {preload_time:.3f}秒")
            else:
                logger.warning(f"预加载失败，文档不存在: {request.document_id}")
                self.stats.failed_preloads += 1
            
        except asyncio.TimeoutError:
            logger.warning(f"预加载超时: {request.document_id}")
            self.stats.failed_preloads += 1
        except Exception as e:
            logger.error(f"预加载执行失败: {request.document_id}, {e}")
            self.stats.failed_preloads += 1
        finally:
            self.preloading_documents.discard(request.document_id)
            self.stats.total_requests += 1
    
    def _cleanup_old_preloads(self):
        """清理旧的预加载文档"""
        if len(self.preloaded_documents) < self.max_preloaded_documents:
            return
        
        # 按访问时间排序，移除最久未访问的文档
        sorted_docs = sorted(
            self.preloaded_documents.items(),
            key=lambda item: getattr(item[1], 'last_accessed', datetime.min)
        )
        
        # 移除最旧的文档
        docs_to_remove = len(self.preloaded_documents) - self.max_preloaded_documents + 1
        for i in range(docs_to_remove):
            doc_id, doc = sorted_docs[i]
            del self.preloaded_documents[doc_id]
            logger.debug(f"清理预加载文档: {doc.title}")
    
    async def preload_adjacent_documents(self, current_doc_id: str, project_id: str):
        """预加载相邻文档"""
        try:
            # 获取项目中的文档列表
            documents = await self.document_repository.list_by_project(project_id)
            if not documents:
                return
            
            # 找到当前文档的位置
            current_index = next((i for i, doc in enumerate(documents) if doc.id == current_doc_id), -1)
            
            if current_index >= 0:
                # 预加载前后各N个文档
                start_index = max(0, current_index - self.adjacent_preload_count)
                end_index = min(len(documents), current_index + self.adjacent_preload_count + 1)
                
                for i in range(start_index, end_index):
                    if i != current_index:  # 跳过当前文档
                        doc_id = documents[i].id
                        await self.request_preload(
                            doc_id, 
                            priority=2, 
                            reason=f"相邻文档预加载 (距离: {abs(i - current_index)})"
                        )
                
                logger.info(f"已请求预加载相邻文档: {end_index - start_index - 1} 个")
            
        except Exception as e:
            logger.error(f"预加载相邻文档失败: {e}")
    
    async def preload_frequent_documents(self, limit: int = 5):
        """预加载常用文档"""
        try:
            # 获取访问频率最高的文档
            frequent_docs = sorted(
                self.access_frequency.items(),
                key=lambda item: item[1],
                reverse=True
            )[:limit]
            
            for doc_id, frequency in frequent_docs:
                if doc_id not in self.preloaded_documents:
                    await self.request_preload(
                        doc_id,
                        priority=3,
                        reason=f"常用文档预加载 (访问次数: {frequency})"
                    )
            
            logger.info(f"已请求预加载常用文档: {len(frequent_docs)} 个")
            
        except Exception as e:
            logger.error(f"预加载常用文档失败: {e}")
    
    async def request_preload(self, document_id: str, priority: int = 1, reason: str = ""):
        """请求预加载文档"""
        try:
            request = PreloadRequest(
                document_id=document_id,
                priority=priority,
                reason=reason
            )
            
            await self.preload_queue.put(request)
            logger.debug(f"预加载请求已添加: {document_id} (优先级: {priority})")
            
        except Exception as e:
            logger.error(f"添加预加载请求失败: {e}")
    
    def record_document_access(self, document_id: str):
        """记录文档访问"""
        try:
            # 记录访问历史
            self.access_history.append((document_id, datetime.now()))
            
            # 更新访问频率
            self.access_frequency[document_id] += 1
            
            # 更新访问模式（记录访问序列）
            if len(self.access_history) >= 2:
                prev_doc_id = self.access_history[-2][0]
                if prev_doc_id != document_id:  # 不同文档
                    self.access_patterns[prev_doc_id].append(document_id)
                    
                    # 限制模式历史长度
                    if len(self.access_patterns[prev_doc_id]) > 10:
                        self.access_patterns[prev_doc_id] = self.access_patterns[prev_doc_id][-10:]
            
            logger.debug(f"记录文档访问: {document_id}")
            
        except Exception as e:
            logger.error(f"记录文档访问失败: {e}")
    
    def get_preloaded_document(self, document_id: str) -> Optional[Document]:
        """获取预加载的文档"""
        document = self.preloaded_documents.get(document_id)
        if document:
            # 更新最后访问时间
            document.last_accessed = datetime.now()
            logger.debug(f"命中预加载缓存: {document.title}")
        
        return document
    
    def get_stats(self) -> PreloadStats:
        """获取预加载统计"""
        return self.stats
    
    async def shutdown(self):
        """关闭预加载器"""
        try:
            # 停止工作线程
            if self._preload_task and not self._preload_task.done():
                self._preload_task.cancel()
                try:
                    await self._preload_task
                except asyncio.CancelledError:
                    pass
            
            # 清理预加载的文档
            self.preloaded_documents.clear()
            
            logger.info("文档预加载器已关闭")
            
        except Exception as e:
            logger.error(f"关闭预加载器失败: {e}")


# 全局预加载器实例
_document_preloader = None

def get_document_preloader(document_repository: IDocumentRepository = None) -> DocumentPreloader:
    """获取全局文档预加载器"""
    global _document_preloader
    if _document_preloader is None and document_repository:
        _document_preloader = DocumentPreloader(document_repository)
    return _document_preloader

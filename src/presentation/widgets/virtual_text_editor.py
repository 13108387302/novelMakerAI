"""
虚拟化文本编辑器

实现大文档的虚拟化渲染，只加载和渲染可见区域的内容，
大幅提升大文档的加载速度和内存使用效率。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import asyncio
import time
import weakref
from typing import Dict, List, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from PyQt6.QtWidgets import QTextEdit, QScrollBar, QApplication
from PyQt6.QtCore import QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QTextCursor, QTextDocument, QFont

from src.shared.utils.logger import get_logger
from src.domain.entities.document import Document

logger = get_logger(__name__)


@dataclass
class ViewportInfo:
    """视口信息"""
    start_line: int = 0
    end_line: int = 0
    total_lines: int = 0
    visible_lines: int = 0
    scroll_position: float = 0.0


@dataclass
class LineCache:
    """行缓存"""
    lines: Dict[int, str]  # 行号 -> 行内容
    loaded_ranges: List[Tuple[int, int]]  # 已加载的行范围
    max_cached_lines: int = 2000  # 最大缓存行数

    def __post_init__(self):
        if not hasattr(self, 'lines'):
            self.lines = {}
        if not hasattr(self, 'loaded_ranges'):
            self.loaded_ranges = []


@dataclass
class PageInfo:
    """分页信息"""
    page_number: int = 0
    total_pages: int = 0
    lines_per_page: int = 1000
    current_page_start_line: int = 0
    current_page_end_line: int = 0


@dataclass
class LoadingProgress:
    """加载进度信息"""
    current_chunk: int = 0
    total_chunks: int = 0
    loaded_lines: int = 0
    total_lines: int = 0
    progress_percentage: float = 0.0


class VirtualTextEditor(QTextEdit):
    """
    虚拟化文本编辑器
    
    专为大文档设计的高性能文本编辑器，实现以下特性：
    1. 虚拟化渲染：只渲染可见区域的内容
    2. 智能缓存：缓存最近访问的文本行
    3. 流式加载：支持大文档的分块异步加载
    4. 内存优化：使用弱引用管理大对象
    5. 性能监控：实时监控加载和渲染性能
    """
    
    # 信号定义
    loading_progress = pyqtSignal(int, int)  # current, total
    loading_completed = pyqtSignal(float)    # load_time
    viewport_changed = pyqtSignal(int, int)  # start_line, end_line
    page_changed = pyqtSignal(int, int)      # current_page, total_pages
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 虚拟化配置
        self.viewport_size = 1000  # 视口大小（行数）
        self.buffer_size = 200     # 缓冲区大小（视口外的额外行数）
        self.chunk_size = 100      # 每次加载的行数
        
        # 文档信息
        self._document_ref = None  # 使用弱引用
        self._total_lines = 0
        self._current_viewport = ViewportInfo()
        
        # 缓存系统
        self._line_cache = LineCache()
        self._content_cache = {}  # 内容块缓存

        # 分页系统
        self._page_info = PageInfo()
        self._enable_pagination = True  # 是否启用分页
        self._lines_per_page = 1000     # 每页行数
        
        # 加载状态
        self._is_loading = False
        self._load_progress = 0
        self._load_start_time = 0
        
        # 性能监控
        self._performance_stats = {
            'load_times': [],
            'render_times': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # 设置滚动条连接
        self._setup_scroll_connections()
        
        # 延迟加载定时器
        self._load_timer = QTimer()
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._delayed_load_viewport)
        
        logger.debug("虚拟化文本编辑器初始化完成")
    
    def _setup_scroll_connections(self):
        """设置滚动条连接"""
        # 连接垂直滚动条
        v_scrollbar = self.verticalScrollBar()
        v_scrollbar.valueChanged.connect(self._on_scroll_changed)
        
        # 连接文档大小变化
        self.document().documentLayout().documentSizeChanged.connect(self._on_document_size_changed)
    
    def load_document_virtual(self, document: Document) -> None:
        """
        虚拟化加载文档
        
        Args:
            document: 要加载的文档对象
        """
        try:
            self._load_start_time = time.time()
            self._is_loading = True
            
            # 使用弱引用存储文档
            self._document_ref = weakref.ref(document)
            
            # 计算总行数
            self._total_lines = document.content.count('\n') + 1 if document.content else 1
            self._current_viewport.total_lines = self._total_lines
            
            logger.info(f"开始虚拟化加载文档: {document.title} ({self._total_lines} 行)")
            
            # 清理旧缓存
            self._clear_cache()
            
            # 判断加载策略
            if self._total_lines <= 500:  # 小文档直接加载
                self._load_small_document_direct(document)
            else:  # 大文档使用虚拟化加载
                self._load_large_document_virtual(document)
                
        except Exception as e:
            logger.error(f"虚拟化文档加载失败: {e}")
            self._is_loading = False
            raise
    
    def _load_small_document_direct(self, document: Document):
        """直接加载小文档"""
        try:
            self.setPlainText(document.content)
            self._cache_all_lines(document.content)
            
            load_time = time.time() - self._load_start_time
            self._performance_stats['load_times'].append(load_time)
            
            self._is_loading = False
            self.loading_completed.emit(load_time)
            
            logger.info(f"小文档直接加载完成: {load_time:.3f}秒")
            
        except Exception as e:
            logger.error(f"小文档加载失败: {e}")
            self._is_loading = False
            raise
    
    def _load_large_document_virtual(self, document: Document):
        """虚拟化加载大文档"""
        try:
            # 初始化视口
            self._current_viewport.start_line = 0
            self._current_viewport.end_line = min(self.viewport_size, self._total_lines)
            self._current_viewport.visible_lines = self._current_viewport.end_line
            
            # 异步加载初始视口
            QTimer.singleShot(0, lambda: self._load_viewport_async(0, self.viewport_size))
            
        except Exception as e:
            logger.error(f"大文档虚拟化加载失败: {e}")
            self._is_loading = False
            raise
    
    def _cache_all_lines(self, content: str):
        """缓存所有行（用于小文档）"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            self._line_cache.lines[i] = line
        
        self._line_cache.loaded_ranges = [(0, len(lines) - 1)]
        logger.debug(f"缓存所有行完成: {len(lines)} 行")
    
    def _clear_cache(self):
        """清理缓存"""
        self._line_cache.lines.clear()
        self._line_cache.loaded_ranges.clear()
        self._content_cache.clear()
        logger.debug("缓存已清理")
    
    def _load_viewport_async(self, start_line: int, line_count: int):
        """异步加载视口内容"""
        try:
            document = self._get_document()
            if not document:
                logger.error("文档引用已失效")
                return
            
            # 获取视口内容
            viewport_content = self._get_viewport_content(document, start_line, line_count)
            
            # 设置内容
            self.setPlainText(viewport_content)
            
            # 更新视口信息
            self._current_viewport.start_line = start_line
            self._current_viewport.end_line = min(start_line + line_count, self._total_lines)
            
            # 发射信号
            self.viewport_changed.emit(self._current_viewport.start_line, self._current_viewport.end_line)
            
            # 完成加载
            if not self._is_loading:
                return
                
            load_time = time.time() - self._load_start_time
            self._performance_stats['load_times'].append(load_time)
            
            self._is_loading = False
            self.loading_completed.emit(load_time)
            
            logger.info(f"视口加载完成: 行{start_line}-{self._current_viewport.end_line}, 耗时{load_time:.3f}秒")
            
        except Exception as e:
            logger.error(f"异步视口加载失败: {e}")
            self._is_loading = False
    
    def _get_document(self) -> Optional[Document]:
        """获取文档对象"""
        if self._document_ref:
            return self._document_ref()
        return None
    
    def _get_viewport_content(self, document: Document, start_line: int, line_count: int) -> str:
        """获取视口内容"""
        try:
            # 检查缓存
            cache_key = f"{start_line}:{line_count}"
            if cache_key in self._content_cache:
                self._performance_stats['cache_hits'] += 1
                return self._content_cache[cache_key]
            
            self._performance_stats['cache_misses'] += 1
            
            # 分割文档内容为行
            all_lines = document.content.split('\n')
            
            # 获取指定范围的行
            end_line = min(start_line + line_count, len(all_lines))
            viewport_lines = all_lines[start_line:end_line]
            
            # 缓存行内容
            for i, line in enumerate(viewport_lines):
                line_number = start_line + i
                self._line_cache.lines[line_number] = line
            
            # 更新已加载范围
            self._update_loaded_ranges(start_line, end_line - 1)
            
            # 生成视口内容
            viewport_content = '\n'.join(viewport_lines)
            
            # 缓存内容块
            self._content_cache[cache_key] = viewport_content
            
            # 限制缓存大小
            if len(self._content_cache) > 10:
                # 移除最旧的缓存项
                oldest_key = next(iter(self._content_cache))
                del self._content_cache[oldest_key]
            
            return viewport_content
            
        except Exception as e:
            logger.error(f"获取视口内容失败: {e}")
            return ""
    
    def _update_loaded_ranges(self, start_line: int, end_line: int):
        """更新已加载范围"""
        new_range = (start_line, end_line)
        
        # 合并重叠的范围
        merged_ranges = []
        for existing_range in self._line_cache.loaded_ranges:
            if self._ranges_overlap(new_range, existing_range):
                # 合并范围
                new_range = (
                    min(new_range[0], existing_range[0]),
                    max(new_range[1], existing_range[1])
                )
            else:
                merged_ranges.append(existing_range)
        
        merged_ranges.append(new_range)
        self._line_cache.loaded_ranges = merged_ranges
    
    def _ranges_overlap(self, range1: Tuple[int, int], range2: Tuple[int, int]) -> bool:
        """检查两个范围是否重叠"""
        return not (range1[1] < range2[0] or range2[1] < range1[0])
    
    def _on_scroll_changed(self, value: int):
        """滚动位置变化处理"""
        if self._is_loading:
            return
        
        # 计算当前可见的行范围
        visible_start_line = self._calculate_visible_start_line(value)
        
        # 检查是否需要加载新的视口
        if self._needs_viewport_update(visible_start_line):
            # 延迟加载，避免频繁滚动时的重复加载
            self._load_timer.stop()
            self._load_timer.start(100)  # 100ms延迟
    
    def _calculate_visible_start_line(self, scroll_value: int) -> int:
        """计算可见区域的起始行"""
        # 这是一个简化的计算，实际实现需要考虑行高等因素
        total_scroll_range = self.verticalScrollBar().maximum()
        if total_scroll_range == 0:
            return 0
        
        scroll_ratio = scroll_value / total_scroll_range
        visible_start_line = int(scroll_ratio * self._total_lines)
        
        return max(0, min(visible_start_line, self._total_lines - 1))
    
    def _needs_viewport_update(self, visible_start_line: int) -> bool:
        """检查是否需要更新视口"""
        # 如果可见区域超出当前缓存范围，需要更新
        buffer_start = max(0, self._current_viewport.start_line - self.buffer_size)
        buffer_end = min(self._total_lines, self._current_viewport.end_line + self.buffer_size)
        
        return visible_start_line < buffer_start or visible_start_line > buffer_end
    
    def _delayed_load_viewport(self):
        """延迟加载视口"""
        if self._is_loading:
            return
        
        # 计算新的视口范围
        current_scroll = self.verticalScrollBar().value()
        visible_start_line = self._calculate_visible_start_line(current_scroll)
        
        # 计算加载范围（包含缓冲区）
        load_start = max(0, visible_start_line - self.buffer_size)
        load_end = min(self._total_lines, visible_start_line + self.viewport_size + self.buffer_size)
        
        # 异步加载新视口
        self._load_viewport_async(load_start, load_end - load_start)
    
    def _on_document_size_changed(self):
        """文档大小变化处理"""
        # 重新计算总行数
        current_content = self.toPlainText()
        self._total_lines = current_content.count('\n') + 1
        self._current_viewport.total_lines = self._total_lines
        
        logger.debug(f"文档大小变化: {self._total_lines} 行")
    
    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        stats = self._performance_stats.copy()
        
        if stats['load_times']:
            stats['avg_load_time'] = sum(stats['load_times']) / len(stats['load_times'])
            stats['max_load_time'] = max(stats['load_times'])
            stats['min_load_time'] = min(stats['load_times'])
        
        if stats['cache_hits'] + stats['cache_misses'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])
        
        return stats
    
    def get_viewport_info(self) -> ViewportInfo:
        """获取当前视口信息"""
        return self._current_viewport
    
    def is_loading(self) -> bool:
        """是否正在加载"""
        return self._is_loading
    
    def clear_cache(self):
        """清理缓存（公共接口）"""
        self._clear_cache()
        logger.info("虚拟化编辑器缓存已清理")

    def enable_pagination(self, enabled: bool = True, lines_per_page: int = 1000):
        """启用/禁用分页模式"""
        self._enable_pagination = enabled
        self._lines_per_page = lines_per_page

        if enabled:
            self._update_pagination_info()
            logger.info(f"分页模式已启用: {lines_per_page} 行/页")
        else:
            logger.info("分页模式已禁用")

    def _update_pagination_info(self):
        """更新分页信息"""
        if not self._enable_pagination:
            return

        self._page_info.lines_per_page = self._lines_per_page
        self._page_info.total_pages = max(1, (self._total_lines + self._lines_per_page - 1) // self._lines_per_page)

        # 计算当前页
        current_line = self._current_viewport.start_line
        self._page_info.page_number = current_line // self._lines_per_page

        # 计算当前页的行范围
        self._page_info.current_page_start_line = self._page_info.page_number * self._lines_per_page
        self._page_info.current_page_end_line = min(
            self._page_info.current_page_start_line + self._lines_per_page,
            self._total_lines
        )

        logger.debug(f"分页信息更新: 第{self._page_info.page_number + 1}/{self._page_info.total_pages}页")

    def goto_page(self, page_number: int):
        """跳转到指定页"""
        if not self._enable_pagination:
            logger.warning("分页模式未启用")
            return

        if page_number < 0 or page_number >= self._page_info.total_pages:
            logger.warning(f"页码超出范围: {page_number}")
            return

        # 计算目标行
        target_line = page_number * self._lines_per_page

        # 加载目标页内容
        self._load_viewport_async(target_line, self._lines_per_page)

        # 更新分页信息
        self._page_info.page_number = page_number
        self._update_pagination_info()

        # 发射页面变化信号
        self.page_changed.emit(page_number, self._page_info.total_pages)

        logger.info(f"跳转到第{page_number + 1}页")

    def next_page(self):
        """下一页"""
        if self._enable_pagination and self._page_info.page_number < self._page_info.total_pages - 1:
            self.goto_page(self._page_info.page_number + 1)

    def previous_page(self):
        """上一页"""
        if self._enable_pagination and self._page_info.page_number > 0:
            self.goto_page(self._page_info.page_number - 1)

    def get_page_info(self) -> PageInfo:
        """获取分页信息"""
        return self._page_info

    def load_document_with_pagination(self, document: Document, lines_per_page: int = 1000):
        """使用分页模式加载文档"""
        try:
            # 启用分页
            self.enable_pagination(True, lines_per_page)

            # 加载文档
            self.load_document_virtual(document)

            logger.info(f"分页模式加载文档: {document.title}, {lines_per_page} 行/页")

        except Exception as e:
            logger.error(f"分页模式加载失败: {e}")
            # 回退到普通虚拟化加载
            self.enable_pagination(False)
            self.load_document_virtual(document)


class VirtualTextEditorManager:
    """
    虚拟化文本编辑器管理器

    管理多个虚拟化编辑器实例，提供统一的接口和资源管理。
    """

    def __init__(self):
        self._editors: Dict[str, VirtualTextEditor] = {}
        self._memory_monitor = None
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._periodic_cleanup)
        self._cleanup_timer.start(300000)  # 5分钟清理一次

        logger.debug("虚拟化编辑器管理器初始化完成")

    def create_editor(self, document_id: str, parent=None) -> VirtualTextEditor:
        """创建虚拟化编辑器"""
        if document_id in self._editors:
            logger.warning(f"编辑器已存在: {document_id}")
            return self._editors[document_id]

        editor = VirtualTextEditor(parent)
        self._editors[document_id] = editor

        # 连接性能监控信号
        editor.loading_completed.connect(
            lambda load_time: self._on_editor_load_completed(document_id, load_time)
        )

        logger.info(f"创建虚拟化编辑器: {document_id}")
        return editor

    def remove_editor(self, document_id: str):
        """移除编辑器"""
        if document_id in self._editors:
            editor = self._editors[document_id]
            editor.clear_cache()
            del self._editors[document_id]
            logger.info(f"移除虚拟化编辑器: {document_id}")

    def get_editor(self, document_id: str) -> Optional[VirtualTextEditor]:
        """获取编辑器"""
        return self._editors.get(document_id)

    def _on_editor_load_completed(self, document_id: str, load_time: float):
        """编辑器加载完成处理"""
        logger.info(f"编辑器加载完成: {document_id}, 耗时: {load_time:.3f}秒")

        # 记录性能数据
        if hasattr(self, '_performance_tracker'):
            self._performance_tracker.record_load_time(document_id, load_time)

    def _periodic_cleanup(self):
        """定期清理"""
        try:
            # 清理未使用的编辑器缓存
            for document_id, editor in list(self._editors.items()):
                if not editor.isVisible():
                    # 如果编辑器不可见，清理其缓存
                    editor.clear_cache()

            logger.debug("定期缓存清理完成")

        except Exception as e:
            logger.error(f"定期清理失败: {e}")

    def get_total_memory_usage(self) -> int:
        """获取总内存使用量（估算）"""
        total_memory = 0

        for editor in self._editors.values():
            # 估算编辑器内存使用
            cache_size = len(editor._line_cache.lines) * 100  # 假设每行平均100字节
            content_cache_size = sum(len(content) for content in editor._content_cache.values())
            total_memory += cache_size + content_cache_size

        return total_memory

    def optimize_memory_usage(self):
        """优化内存使用"""
        try:
            total_memory = self.get_total_memory_usage()

            if total_memory > 50 * 1024 * 1024:  # 超过50MB
                logger.info(f"内存使用过高({total_memory/1024/1024:.1f}MB)，开始优化")

                # 清理最久未使用的编辑器缓存
                for editor in self._editors.values():
                    if not editor.hasFocus():
                        editor.clear_cache()

                logger.info("内存优化完成")

        except Exception as e:
            logger.error(f"内存优化失败: {e}")


# 全局管理器实例
_virtual_editor_manager = None

def get_virtual_editor_manager() -> VirtualTextEditorManager:
    """获取全局虚拟化编辑器管理器"""
    global _virtual_editor_manager
    if _virtual_editor_manager is None:
        _virtual_editor_manager = VirtualTextEditorManager()
    return _virtual_editor_manager

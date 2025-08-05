#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态面板组件

显示应用程序状态、日志和统计信息
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QLabel, QProgressBar, QListWidget, QListWidgetItem, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from src.shared.utils.logger import get_logger
from src.application.services.status_service import StatusService
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = get_logger(__name__)


class LogItem:
    """日志项"""
    
    def __init__(self, level: str, message: str, timestamp: datetime = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()


class StatusPanelWidget(QWidget):
    """状态面板组件 - 使用真实数据"""

    # 信号定义
    log_cleared = pyqtSignal()

    def __init__(self, status_service: Optional[StatusService] = None):
        super().__init__()

        # 状态服务
        self.status_service = status_service or StatusService()

        # 日志存储
        self._log_items: List[LogItem] = []
        self._max_log_items = 1000

        # 当前统计数据
        self._current_stats = {}

        self._setup_ui()
        self._setup_connections()

        logger.debug("状态面板组件初始化完成")

    def _create_compact_group(self, title: str):
        """创建紧凑的组框"""
        group = QGroupBox(title)
        group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(3)
        layout.setContentsMargins(6, 6, 6, 6)
        return group, layout

    def _create_compact_label(self, text: str):
        """创建紧凑的标签"""
        label = QLabel(text)
        label.setStyleSheet("font-size: 11px;")
        return label
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)  # 减少边距
        layout.setSpacing(4)  # 减少间距

        # 设置面板的尺寸限制
        self.setMinimumWidth(250)  # 最小宽度
        self.setMaximumWidth(350)  # 最大宽度
        self.resize(280, self.height())  # 默认宽度280px
        
        # 标签页组件
        self.tab_widget = QTabWidget()
        # 使用主题样式并设置紧凑尺寸
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                padding: 4px 8px;
                margin: 1px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #e3f2fd;
            }
        """)
        
        # 创建各个标签页
        self._create_status_tab()
        self._create_log_tab()
        self._create_statistics_tab()
        self._create_performance_tab()
        
        layout.addWidget(self.tab_widget)
    
    def _create_status_tab(self):
        """创建状态标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)  # 减少间距
        layout.setContentsMargins(4, 4, 4, 4)  # 添加紧凑边距
        
        # 系统状态组
        system_group = QGroupBox("🖥️ 系统状态")
        system_group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; }")
        system_layout = QVBoxLayout(system_group)
        system_layout.setSpacing(3)  # 紧凑间距
        system_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        # 应用状态
        self.app_status_label = QLabel("🟢 应用程序: 正常运行")
        self.app_status_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        system_layout.addWidget(self.app_status_label)

        # AI服务状态
        self.ai_status_label = QLabel("🟢 AI服务: 连接正常")
        self.ai_status_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        system_layout.addWidget(self.ai_status_label)

        # 数据库状态
        self.db_status_label = QLabel("🟡 数据库: 文件模式")
        self.db_status_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        system_layout.addWidget(self.db_status_label)
        
        layout.addWidget(system_group)
        
        # 当前活动组
        activity_group = QGroupBox("📋 当前活动")
        activity_layout = QVBoxLayout(activity_group)
        activity_layout.setSpacing(3)  # 紧凑间距
        activity_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        self.current_project_label = QLabel("项目: 未打开")
        self.current_project_label.setStyleSheet("font-size: 11px;")
        activity_layout.addWidget(self.current_project_label)

        self.current_document_label = QLabel("文档: 未打开")
        self.current_document_label.setStyleSheet("font-size: 11px;")
        activity_layout.addWidget(self.current_document_label)

        self.ai_activity_label = QLabel("AI状态: 空闲")
        self.ai_activity_label.setStyleSheet("font-size: 11px;")
        activity_layout.addWidget(self.ai_activity_label)
        
        layout.addWidget(activity_group)
        
        # 内存使用
        memory_group = QGroupBox("💾 资源使用")
        memory_layout = QVBoxLayout(memory_group)
        memory_layout.setSpacing(3)  # 紧凑间距
        memory_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximumHeight(16)  # 限制高度
        self.memory_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 3px;
                text-align: center;
                background-color: #f8f9fa;
                height: 14px;
                font-size: 10px;
            }

            QProgressBar::chunk {
                background-color: #17a2b8;
                border-radius: 2px;
            }
        """)
        memory_layout.addWidget(QLabel("内存使用:"))
        memory_layout.addWidget(self.memory_progress)
        
        layout.addWidget(memory_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "📊 状态")
    
    def _create_log_tab(self):
        """创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(4)  # 减少间距
        layout.setContentsMargins(4, 4, 4, 4)  # 紧凑边距
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        # 日志级别过滤
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["全部", "错误", "警告", "信息", "调试"])
        self.log_level_combo.currentTextChanged.connect(self._filter_logs)
        toolbar_layout.addWidget(QLabel("级别:"))
        toolbar_layout.addWidget(self.log_level_combo)
        
        toolbar_layout.addStretch()
        
        # 清空日志按钮
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        clear_btn.clicked.connect(self.clear_logs)
        toolbar_layout.addWidget(clear_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 日志列表
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
            }
            
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #e9ecef;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        layout.addWidget(self.log_list)
        
        self.tab_widget.addTab(tab, "📝 日志")
    
    def _create_statistics_tab(self):
        """创建统计标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)  # 减少间距
        layout.setContentsMargins(4, 4, 4, 4)  # 紧凑边距
        
        # 写作统计组
        writing_group = QGroupBox("✍️ 写作统计")
        writing_layout = QVBoxLayout(writing_group)
        writing_layout.setSpacing(3)  # 紧凑间距
        writing_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        self.total_words_label = QLabel("总字数: 0")
        writing_layout.addWidget(self.total_words_label)
        
        self.total_docs_label = QLabel("文档数量: 0")
        writing_layout.addWidget(self.total_docs_label)
        
        self.session_words_label = QLabel("本次会话: 0 字")
        writing_layout.addWidget(self.session_words_label)
        
        layout.addWidget(writing_group)
        
        # AI使用统计组
        ai_group = QGroupBox("🤖 AI使用统计")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(3)  # 紧凑间距
        ai_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        self.ai_requests_label = QLabel("总请求数: 0")
        ai_layout.addWidget(self.ai_requests_label)
        
        self.ai_success_rate_label = QLabel("成功率: 100%")
        ai_layout.addWidget(self.ai_success_rate_label)
        
        self.ai_avg_time_label = QLabel("平均响应时间: 0ms")
        ai_layout.addWidget(self.ai_avg_time_label)
        
        layout.addWidget(ai_group)
        
        # 会话统计组
        session_group = QGroupBox("⏱️ 会话统计")
        session_layout = QVBoxLayout(session_group)
        session_layout.setSpacing(3)  # 紧凑间距
        session_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        self.session_time_label = QLabel("会话时长: 0分钟")
        session_layout.addWidget(self.session_time_label)
        
        self.last_save_label = QLabel("最后保存: 从未")
        session_layout.addWidget(self.last_save_label)
        
        layout.addWidget(session_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "📈 统计")
    
    def _create_performance_tab(self):
        """创建性能标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)  # 减少间距
        layout.setContentsMargins(4, 4, 4, 4)  # 紧凑边距
        
        # 性能指标组
        performance_group = QGroupBox("⚡ 性能指标")
        performance_layout = QVBoxLayout(performance_group)
        performance_layout.setSpacing(3)  # 紧凑间距
        performance_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        # CPU使用率
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("CPU使用率:"))
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximumHeight(16)  # 限制高度
        self.cpu_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 3px;
                text-align: center;
                background-color: #f8f9fa;
                height: 14px;
                font-size: 10px;
            }

            QProgressBar::chunk {
                background-color: #fd7e14;
                border-radius: 2px;
            }
        """)
        cpu_layout.addWidget(self.cpu_progress)
        performance_layout.addLayout(cpu_layout)
        
        # 响应时间
        self.response_time_label = QLabel("平均响应时间: 0ms")
        performance_layout.addWidget(self.response_time_label)
        
        # 错误率
        self.error_rate_label = QLabel("错误率: 0%")
        performance_layout.addWidget(self.error_rate_label)
        
        layout.addWidget(performance_group)
        
        # 缓存统计组
        cache_group = QGroupBox("🗄️ 缓存统计")
        cache_layout = QVBoxLayout(cache_group)
        cache_layout.setSpacing(3)  # 紧凑间距
        cache_layout.setContentsMargins(6, 6, 6, 6)  # 紧凑边距
        
        self.cache_hit_rate_label = QLabel("缓存命中率: 0%")
        cache_layout.addWidget(self.cache_hit_rate_label)
        
        self.cache_size_label = QLabel("缓存大小: 0 MB")
        cache_layout.addWidget(self.cache_size_label)
        
        layout.addWidget(cache_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "⚡ 性能")
    
    def _setup_connections(self):
        """设置信号连接"""
        try:
            # 连接状态服务信号
            if self.status_service:
                self.status_service.status_updated.connect(self._on_status_updated)
                self.status_service.performance_warning.connect(self._on_performance_warning)

            logger.debug("状态面板信号连接完成")

        except Exception as e:
            logger.error(f"设置状态面板信号连接失败: {e}")
    
    def _on_status_updated(self, stats: Dict[str, Any]):
        """处理状态更新"""
        try:
            self._current_stats = stats
            self._update_all_displays()
        except Exception as e:
            logger.error(f"处理状态更新失败: {e}")

    def _on_performance_warning(self, message: str):
        """处理性能警告"""
        self.add_log("WARNING", f"性能警告: {message}")

    def _update_all_displays(self):
        """更新所有显示"""
        try:
            stats = self._current_stats

            # 更新状态标签页
            self._update_status_display(stats)

            # 更新统计标签页
            self._update_statistics_display(stats)

            # 更新性能标签页
            self._update_performance_display(stats)

        except Exception as e:
            logger.error(f"更新显示失败: {e}")

    def _update_status_display(self, stats: Dict[str, Any]):
        """更新状态显示"""
        # 更新当前活动
        if "current_project" in stats:
            self.current_project_label.setText(f"项目: {stats['current_project']}")

        if "current_document" in stats:
            self.current_document_label.setText(f"文档: {stats['current_document']}")

        if "ai_status" in stats:
            self.ai_activity_label.setText(f"AI状态: {stats['ai_status']}")

        # 更新资源使用
        if "memory_usage" in stats:
            self.memory_progress.setValue(int(stats["memory_usage"]))

    def _update_statistics_display(self, stats: Dict[str, Any]):
        """更新统计显示"""
        # 写作统计
        if "total_words" in stats:
            self.total_words_label.setText(f"总字数: {stats['total_words']:,}")

        if "total_documents" in stats:
            self.total_docs_label.setText(f"文档数量: {stats['total_documents']}")

        if "session_words" in stats:
            self.session_words_label.setText(f"本次会话: {stats['session_words']} 字")

        # AI统计
        if "ai_requests" in stats:
            self.ai_requests_label.setText(f"总请求数: {stats['ai_requests']}")

        if "ai_success_rate" in stats:
            self.ai_success_rate_label.setText(f"成功率: {stats['ai_success_rate']:.1f}%")

        if "ai_avg_response_time" in stats:
            avg_time_ms = stats['ai_avg_response_time'] * 1000
            self.ai_avg_time_label.setText(f"平均响应时间: {avg_time_ms:.0f}ms")

        # 会话统计
        if "session_duration_minutes" in stats:
            self.session_time_label.setText(f"会话时长: {stats['session_duration_minutes']}分钟")

        if "last_save" in stats:
            self.last_save_label.setText(f"最后保存: {stats['last_save']}")

    def _update_performance_display(self, stats: Dict[str, Any]):
        """更新性能显示"""
        # CPU使用率
        if "cpu_usage" in stats:
            self.cpu_progress.setValue(int(stats["cpu_usage"]))

        # 响应时间
        if "ai_avg_response_time" in stats:
            avg_time_ms = stats['ai_avg_response_time'] * 1000
            self.response_time_label.setText(f"平均响应时间: {avg_time_ms:.0f}ms")

        # 错误率
        if "error_count" in stats and "ai_requests" in stats:
            total_requests = stats["ai_requests"]
            error_rate = (stats["error_count"] / max(total_requests, 1)) * 100
            self.error_rate_label.setText(f"错误率: {error_rate:.1f}%")

        # 缓存统计
        if "cache_hit_rate" in stats:
            self.cache_hit_rate_label.setText(f"缓存命中率: {stats['cache_hit_rate']:.1f}%")

        if "cache_size_mb" in stats:
            self.cache_size_label.setText(f"缓存大小: {stats['cache_size_mb']:.1f} MB")
    
    def add_log(self, level: str, message: str):
        """添加日志"""
        try:
            # 创建日志项
            log_item = LogItem(level, message)
            self._log_items.append(log_item)
            
            # 限制日志数量
            if len(self._log_items) > self._max_log_items:
                self._log_items = self._log_items[-self._max_log_items:]
            
            # 更新显示
            self._refresh_log_display()
            
        except Exception as e:
            logger.error(f"添加日志失败: {e}")
    
    def _refresh_log_display(self):
        """刷新日志显示"""
        try:
            self.log_list.clear()
            
            # 获取过滤级别
            filter_level = self.log_level_combo.currentText()
            
            # 级别颜色映射
            level_colors = {
                "ERROR": "#dc3545",
                "WARNING": "#ffc107",
                "INFO": "#17a2b8",
                "DEBUG": "#6c757d"
            }
            
            for log_item in self._log_items:
                # 应用过滤
                if filter_level != "全部":
                    level_map = {"错误": "ERROR", "警告": "WARNING", "信息": "INFO", "调试": "DEBUG"}
                    if log_item.level != level_map.get(filter_level, ""):
                        continue
                
                # 创建列表项
                timestamp = log_item.timestamp.strftime("%H:%M:%S")
                text = f"[{timestamp}] [{log_item.level}] {log_item.message}"
                
                item = QListWidgetItem(text)
                
                # 设置颜色
                color = level_colors.get(log_item.level, "#000000")
                item.setForeground(QColor(color))
                
                self.log_list.addItem(item)
            
            # 滚动到底部
            self.log_list.scrollToBottom()
            
        except Exception as e:
            logger.error(f"刷新日志显示失败: {e}")
    
    def _filter_logs(self, level: str):
        """过滤日志"""
        self._refresh_log_display()
    
    def clear_logs(self):
        """清空日志"""
        self._log_items.clear()
        self.log_list.clear()
        self.log_cleared.emit()
    
    def set_project(self, project):
        """设置当前项目"""
        if self.status_service:
            self.status_service.set_current_project(project)

    def set_document(self, document):
        """设置当前文档"""
        if self.status_service:
            self.status_service.set_current_document(document)

    def update_project_statistics(self, documents: List):
        """更新项目统计"""
        if self.status_service:
            self.status_service.update_project_statistics(documents)

    def record_document_save(self, document):
        """记录文档保存"""
        if self.status_service:
            self.status_service.record_document_save(document)

    def record_ai_request(self, success: bool = True, response_time: float = 0):
        """记录AI请求"""
        if self.status_service:
            self.status_service.record_ai_request(success, response_time)

    def record_session_words(self, words_added: int):
        """记录会话字数"""
        if self.status_service:
            self.status_service.record_session_words(words_added)

    def set_ai_status(self, status: str):
        """设置AI状态"""
        if self.status_service:
            self.status_service.set_ai_status(status)

        # 更新AI服务状态显示
        if "错误" in status or "失败" in status:
            self.ai_status_label.setText("🔴 AI服务: 连接异常")
            self.ai_status_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        else:
            self.ai_status_label.setText("🟢 AI服务: 连接正常")
            self.ai_status_label.setStyleSheet("font-weight: bold; color: #28a745;")

    def get_status_service(self) -> Optional[StatusService]:
        """获取状态服务"""
        return self.status_service

    # 保留旧的方法以兼容现有代码
    def update_project_status(self, project_name: str):
        """更新项目状态（兼容方法）"""
        self.current_project_label.setText(f"项目: {project_name}")

    def update_document_status(self, document_name: str):
        """更新文档状态（兼容方法）"""
        self.current_document_label.setText(f"文档: {document_name}")

    def update_ai_status(self, status: str):
        """更新AI状态（兼容方法）"""
        self.set_ai_status(status)

    def update_statistics(self, stats: Dict[str, Any]):
        """更新统计信息（兼容方法）"""
        self._current_stats.update(stats)
        self._update_all_displays()
    
    def show_performance_warning(self, message: str):
        """显示性能警告"""
        self.add_log("WARNING", f"性能警告: {message}")
    
    def show_error(self, message: str):
        """显示错误"""
        self.add_log("ERROR", message)
    
    def show_info(self, message: str):
        """显示信息"""
        self.add_log("INFO", message)

    def cleanup(self):
        """清理资源"""
        try:
            if self.status_service:
                self.status_service.cleanup()
            logger.debug("状态面板清理完成")
        except Exception as e:
            logger.error(f"状态面板清理失败: {e}")

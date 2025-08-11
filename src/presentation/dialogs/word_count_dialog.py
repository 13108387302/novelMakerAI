#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字数统计对话框

显示详细的字数统计信息
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QWidget, QLabel, QProgressBar, QGroupBox, QTableWidget,
    QTableWidgetItem, QPushButton, QTextEdit, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QThreadPool
from PyQt6.QtGui import QFont
from ._stats_loader import StatsTask
# 图表功能暂时禁用，需要安装PyQt6-Charts
# from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet

from src.shared.utils.logger import get_logger
from typing import Dict, List, Any
import re
from datetime import datetime, timedelta

logger = get_logger(__name__)


class WordCountDialog(QDialog):
    """字数统计对话框"""

    def __init__(self, project_service, document_service, parent=None):
        super().__init__(parent)
        self.project_service = project_service
        # 全局线程池用于后台任务，避免单独QThread生命周期问题
        self._thread_pool = QThreadPool.globalInstance()
        self._pending_task = None

        self.document_service = document_service
        self._setup_ui()
        self._load_statistics()

        # 定时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_statistics)
        self.update_timer.start(5000)  # 每5秒更新一次

        # 全局线程池用于后台任务，避免单独QThread生命周期问题
        self._thread_pool = QThreadPool.globalInstance()
        self._pending_task = None

        logger.debug("字数统计对话框初始化完成")

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("字数统计")
        self.setModal(False)
        self.resize(700, 500)

        # 主布局
        layout = QVBoxLayout(self)

        # 标签页
        self.tab_widget = QTabWidget()

        # 创建各个标签页
        self._create_overview_tab()
        self._create_documents_tab()
        self._create_progress_tab()
        self._create_analysis_tab()

        layout.addWidget(self.tab_widget)

        # 按钮区域
        self._create_buttons()
        layout.addLayout(self.buttons_layout)

        # 应用样式
        self._apply_styles()

    def _create_overview_tab(self):
        """创建概览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 总体统计
        overview_group = QGroupBox("总体统计")
        overview_layout = QGridLayout(overview_group)

        # 总字数
        overview_layout.addWidget(QLabel("总字数:"), 0, 0)
        self.total_words_label = QLabel("0")
        self.total_words_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        # 使用主题颜色
        self.total_words_label.setStyleSheet("")
        overview_layout.addWidget(self.total_words_label, 0, 1)

        # 总字符数
        overview_layout.addWidget(QLabel("总字符数:"), 1, 0)
        self.total_chars_label = QLabel("0")
        self.total_chars_label.setFont(QFont("Arial", 14))
        overview_layout.addWidget(self.total_chars_label, 1, 1)

        # 文档数量
        overview_layout.addWidget(QLabel("文档数量:"), 2, 0)
        self.doc_count_label = QLabel("0")
        self.doc_count_label.setFont(QFont("Arial", 14))
        overview_layout.addWidget(self.doc_count_label, 2, 1)

        # 平均每文档字数
        overview_layout.addWidget(QLabel("平均每文档:"), 3, 0)
        self.avg_words_label = QLabel("0")
        self.avg_words_label.setFont(QFont("Arial", 14))
        overview_layout.addWidget(self.avg_words_label, 3, 1)

        layout.addWidget(overview_group)

        # 目标进度
        progress_group = QGroupBox("目标进度")
        progress_layout = QVBoxLayout(progress_group)

        # 进度条
        self.progress_bar = QProgressBar()
        # 使用主题样式
        self.progress_bar.setStyleSheet("")
        progress_layout.addWidget(self.progress_bar)

        # 进度信息
        progress_info_layout = QHBoxLayout()

        self.current_progress_label = QLabel("当前: 0 字")
        progress_info_layout.addWidget(self.current_progress_label)

        progress_info_layout.addStretch()

        self.target_label = QLabel("目标: 80,000 字")
        progress_info_layout.addWidget(self.target_label)

        progress_layout.addLayout(progress_info_layout)

        # 预计完成时间
        self.estimated_completion_label = QLabel("预计完成时间: 计算中...")
        progress_layout.addWidget(self.estimated_completion_label)

        layout.addWidget(progress_group)

        # 今日统计
        today_group = QGroupBox("今日统计")
        today_layout = QGridLayout(today_group)

        today_layout.addWidget(QLabel("今日新增字数:"), 0, 0)
        self.today_words_label = QLabel("0")
        self.today_words_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        # 使用主题颜色
        self.today_words_label.setStyleSheet("")
        today_layout.addWidget(self.today_words_label, 0, 1)

        today_layout.addWidget(QLabel("今日写作时间:"), 1, 0)
        self.today_time_label = QLabel("0 分钟")
        today_layout.addWidget(self.today_time_label, 1, 1)

        layout.addWidget(today_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "📊 概览")

    def _create_documents_tab(self):
        """创建文档统计标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 文档列表
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(5)
        self.documents_table.setHorizontalHeaderLabels([
            "文档名称", "类型", "字数", "字符数", "最后修改"
        ])

        # 设置列宽
        header = self.documents_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.documents_table)

        self.tab_widget.addTab(tab, "📄 文档")

    def _create_progress_tab(self):
        """创建进度标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 写作历史
        history_group = QGroupBox("写作历史")
        history_layout = QVBoxLayout(history_group)

        # 这里可以添加图表显示写作历史
        self.history_text = QTextEdit()
        self.history_text.setMaximumHeight(150)
        self.history_text.setReadOnly(True)
        self.history_text.setText("写作历史数据将在这里显示...")
        history_layout.addWidget(self.history_text)

        layout.addWidget(history_group)

        # 写作速度
        speed_group = QGroupBox("写作速度分析")
        speed_layout = QGridLayout(speed_group)

        speed_layout.addWidget(QLabel("平均每小时:"), 0, 0)
        self.words_per_hour_label = QLabel("0 字/小时")
        speed_layout.addWidget(self.words_per_hour_label, 0, 1)

        speed_layout.addWidget(QLabel("平均每天:"), 1, 0)
        self.words_per_day_label = QLabel("0 字/天")
        speed_layout.addWidget(self.words_per_day_label, 1, 1)

        speed_layout.addWidget(QLabel("最高单日:"), 2, 0)
        self.max_daily_words_label = QLabel("0 字")
        speed_layout.addWidget(self.max_daily_words_label, 2, 1)

        layout.addWidget(speed_group)

        # 目标分析
        target_group = QGroupBox("目标分析")
        target_layout = QGridLayout(target_group)

        target_layout.addWidget(QLabel("完成百分比:"), 0, 0)
        self.completion_percentage_label = QLabel("0%")
        target_layout.addWidget(self.completion_percentage_label, 0, 1)

        target_layout.addWidget(QLabel("剩余字数:"), 1, 0)
        self.remaining_words_label = QLabel("80,000 字")
        target_layout.addWidget(self.remaining_words_label, 1, 1)

        target_layout.addWidget(QLabel("按当前速度需要:"), 2, 0)
        self.estimated_days_label = QLabel("计算中...")
        target_layout.addWidget(self.estimated_days_label, 2, 1)

        layout.addWidget(target_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "📈 进度")

    def _create_analysis_tab(self):
        """创建分析标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 文本分析
        analysis_group = QGroupBox("文本分析")
        analysis_layout = QGridLayout(analysis_group)

        analysis_layout.addWidget(QLabel("平均句长:"), 0, 0)
        self.avg_sentence_length_label = QLabel("0 字")
        analysis_layout.addWidget(self.avg_sentence_length_label, 0, 1)

        analysis_layout.addWidget(QLabel("平均段长:"), 1, 0)
        self.avg_paragraph_length_label = QLabel("0 字")
        analysis_layout.addWidget(self.avg_paragraph_length_label, 1, 1)

        analysis_layout.addWidget(QLabel("句子数量:"), 2, 0)
        self.sentence_count_label = QLabel("0")
        analysis_layout.addWidget(self.sentence_count_label, 2, 1)

        analysis_layout.addWidget(QLabel("段落数量:"), 3, 0)
        self.paragraph_count_label = QLabel("0")
        analysis_layout.addWidget(self.paragraph_count_label, 3, 1)

        layout.addWidget(analysis_group)

        # 词频分析
        frequency_group = QGroupBox("词频分析")
        frequency_layout = QVBoxLayout(frequency_group)

        self.frequency_text = QTextEdit()
        self.frequency_text.setMaximumHeight(200)
        self.frequency_text.setReadOnly(True)
        self.frequency_text.setText("词频分析结果将在这里显示...")
        frequency_layout.addWidget(self.frequency_text)

        layout.addWidget(frequency_group)

        # 可读性分析
        readability_group = QGroupBox("可读性分析")
        readability_layout = QGridLayout(readability_group)

        readability_layout.addWidget(QLabel("可读性评分:"), 0, 0)
        self.readability_score_label = QLabel("0.0")
        readability_layout.addWidget(self.readability_score_label, 0, 1)

        readability_layout.addWidget(QLabel("难度等级:"), 1, 0)
        self.difficulty_level_label = QLabel("未知")
        readability_layout.addWidget(self.difficulty_level_label, 1, 1)

        readability_layout.addWidget(QLabel("目标读者:"), 2, 0)
        self.target_audience_label = QLabel("未知")
        readability_layout.addWidget(self.target_audience_label, 2, 1)

        readability_layout.addWidget(QLabel("词汇丰富度:"), 3, 0)
        self.vocabulary_richness_label = QLabel("0.0%")
        readability_layout.addWidget(self.vocabulary_richness_label, 3, 1)

        layout.addWidget(readability_group)

        # 改进建议
        suggestions_group = QGroupBox("改进建议")
        suggestions_layout = QVBoxLayout(suggestions_group)

        self.suggestions_text = QTextEdit()
        self.suggestions_text.setMaximumHeight(120)
        self.suggestions_text.setReadOnly(True)
        self.suggestions_text.setText("分析完成后将显示改进建议...")
        suggestions_layout.addWidget(self.suggestions_text)

        layout.addWidget(suggestions_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "🔍 分析")

    def _create_buttons(self):
        """创建按钮"""
        self.buttons_layout = QHBoxLayout()

        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._load_statistics)
        self.buttons_layout.addWidget(self.refresh_btn)

        # 导出按钮
        self.export_btn = QPushButton("📊 导出报告")
        self.export_btn.clicked.connect(self._export_report)
        self.buttons_layout.addWidget(self.export_btn)

        self.buttons_layout.addStretch()

        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.close_btn)

    def _apply_styles(self):
        """
        应用样式 - 使用主题管理器

        为字数统计对话框应用统一的主题样式。
        """
        try:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f8f9fa;
                    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                }

                QTabWidget::pane {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    background-color: white;
                    margin-top: 10px;
                }

                QTabWidget::tab-bar {
                    alignment: center;
                }

                QTabBar::tab {
                    background-color: #e9ecef;
                    color: #495057;
                    border: 1px solid #dee2e6;
                    border-bottom: none;
                    border-radius: 8px 8px 0 0;
                    padding: 10px 20px;
                    margin-right: 2px;
                    font-weight: 500;
                }

                QTabBar::tab:selected {
                    background-color: white;
                    color: #007bff;
                    border-color: #007bff;
                    border-bottom: 2px solid white;
                }

                QTabBar::tab:hover:!selected {
                    background-color: #f8f9fa;
                    color: #007bff;
                }

                QTreeWidget {
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    background-color: white;
                    alternate-background-color: #f8f9fa;
                    gridline-color: #e9ecef;
                    font-size: 12px;
                }

                QTreeWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #f1f3f4;
                }

                QTreeWidget::item:selected {
                    background-color: #007bff;
                    color: white;
                }

                QTreeWidget::item:hover {
                    background-color: #e3f2fd;
                }

                QTreeWidget::header {
                    background-color: #f8f9fa;
                    border: none;
                    border-bottom: 2px solid #dee2e6;
                    font-weight: bold;
                    color: #495057;
                }

                QTreeWidget::header::section {
                    padding: 10px;
                    border-right: 1px solid #dee2e6;
                }

                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 12px;
                    font-weight: 500;
                    min-width: 80px;
                }

                QPushButton:hover {
                    background-color: #0056b3;
                }

                QPushButton:pressed {
                    background-color: #004085;
                }

                QPushButton#refresh_btn {
                    background-color: #28a745;
                }

                QPushButton#refresh_btn:hover {
                    background-color: #1e7e34;
                }

                QPushButton#export_btn {
                    background-color: #17a2b8;
                }

                QPushButton#export_btn:hover {
                    background-color: #117a8b;
                }

                QPushButton#close_btn {
                    background-color: #6c757d;
                }

                QPushButton#close_btn:hover {
                    background-color: #545b62;
                }

                QLabel {
                    color: #495057;
                    font-size: 12px;
                }

                QLabel[class="title"] {
                    font-size: 16px;
                    font-weight: bold;
                    color: #212529;
                    margin-bottom: 10px;
                }

                QLabel[class="subtitle"] {
                    font-size: 14px;
                    font-weight: 500;
                    color: #6c757d;
                    margin-bottom: 5px;
                }
            """)

            # 设置按钮ID以应用特定样式
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setObjectName("refresh_btn")
            if hasattr(self, 'export_btn'):
                self.export_btn.setObjectName("export_btn")
            if hasattr(self, 'close_btn'):
                self.close_btn.setObjectName("close_btn")

            logger.debug("字数统计对话框样式应用完成")

        except Exception as e:
            logger.error(f"应用字数统计对话框样式失败: {e}")

    def _load_statistics(self):
        """加载统计数据"""
        try:
            # 获取当前项目
            if not self.project_service.has_current_project:
                return

            project = self.project_service.current_project

            # 使用后台线程加载，避免阻塞UI，也避免事件循环问题
            self._start_loader(project)

        except Exception as e:
            logger.error(f"加载统计数据失败: {e}")


    def _start_loader(self, project):
        # 若上一个任务尚未完成，不能重复提交，避免数据错乱
        if self._pending_task is not None:
            return
        task = StatsTask(self.document_service, project)
        self._pending_task = task
        task.signals.finished.connect(self._on_stats_loaded)
        task.signals.failed.connect(self._on_stats_failed)
        # 任务完成后清理占位引用
        def _clear_pending(*args, **kwargs):
            self._pending_task = None
        task.signals.finished.connect(_clear_pending)
        task.signals.failed.connect(_clear_pending)
        self._thread_pool.start(task)



    def _on_stats_loaded(self, project, documents):
        try:
            # 计算总体统计
            total_words = sum(getattr(doc.statistics, 'word_count', 0) for doc in documents)
            total_chars = sum(getattr(doc.statistics, 'character_count', 0) for doc in documents)
            doc_count = len(documents)
            avg_words = total_words // doc_count if doc_count > 0 else 0

            # 更新UI
            self.total_words_label.setText(f"{total_words:,}")
            self.total_chars_label.setText(f"{total_chars:,}")
            self.doc_count_label.setText(str(doc_count))
            self.avg_words_label.setText(f"{avg_words:,}")

            # 更新进度
            target_words = project.metadata.target_word_count
            progress = min(100, (total_words / target_words * 100)) if target_words > 0 else 0
            self.progress_bar.setValue(int(progress))
            self.current_progress_label.setText(f"当前: {total_words:,} 字")
            self.target_label.setText(f"目标: {target_words:,} 字")
            self.completion_percentage_label.setText(f"{progress:.1f}%")
            self.remaining_words_label.setText(f"{max(0, target_words - total_words):,} 字")

            # 更新文档表格
            self._update_documents_table(documents)

            # 计算文本分析
            self._calculate_text_analysis(documents)
        except Exception as e:
            logger.error(f"更新统计UI失败: {e}")

    def _on_stats_failed(self, message: str):
        logger.error(f"异步加载统计数据失败: {message}")

    async def _load_statistics_async(self, project):
        """异步加载统计数据"""
        try:
            # 获取所有文档
            documents = await self.document_service.list_documents_by_project(project.id)

            # 计算总体统计
            total_words = sum(doc.statistics.word_count for doc in documents)
            total_chars = sum(doc.statistics.character_count for doc in documents)
            doc_count = len(documents)
            avg_words = total_words // doc_count if doc_count > 0 else 0

            # 更新UI
            self.total_words_label.setText(f"{total_words:,}")
            self.total_chars_label.setText(f"{total_chars:,}")
            self.doc_count_label.setText(str(doc_count))
            self.avg_words_label.setText(f"{avg_words:,}")

            # 更新进度
            target_words = project.metadata.target_word_count
            progress = min(100, (total_words / target_words * 100)) if target_words > 0 else 0
            self.progress_bar.setValue(int(progress))
            self.current_progress_label.setText(f"当前: {total_words:,} 字")
            self.target_label.setText(f"目标: {target_words:,} 字")
            self.completion_percentage_label.setText(f"{progress:.1f}%")
            self.remaining_words_label.setText(f"{max(0, target_words - total_words):,} 字")

            # 更新文档表格
            self._update_documents_table(documents)

            # 计算文本分析
            self._calculate_text_analysis(documents)

        except Exception as e:
            logger.error(f"异步加载统计数据失败: {e}")

    def _update_documents_table(self, documents):
        """更新文档表格"""
        try:
            self.documents_table.setRowCount(len(documents))

            for i, doc in enumerate(documents):
                # 文档名称
                self.documents_table.setItem(i, 0, QTableWidgetItem(doc.title))

                # 文档类型
                type_names = {
                    "chapter": "章节",
                    "character": "角色",
                    "setting": "设定",
                    "outline": "大纲",
                    "note": "笔记"
                }
                # 兼容新实体属性名：Document.type 为枚举
                type_value = doc.type.value if hasattr(doc, 'type') and hasattr(doc.type, 'value') else str(getattr(doc, 'type', ''))
                doc_type = type_names.get(type_value, type_value)
                self.documents_table.setItem(i, 1, QTableWidgetItem(doc_type))

                # 字数
                word_item = QTableWidgetItem(f"{doc.statistics.word_count:,}")
                word_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.documents_table.setItem(i, 2, word_item)

                # 字符数
                char_item = QTableWidgetItem(f"{doc.statistics.character_count:,}")
                char_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.documents_table.setItem(i, 3, char_item)

                # 最后修改时间（来自元数据）
                try:
                    modified_dt = getattr(getattr(doc, 'metadata', object), 'updated_at', None)
                    modified_time = modified_dt.strftime("%Y-%m-%d %H:%M") if modified_dt else ""
                except Exception:
                    modified_time = ""
                self.documents_table.setItem(i, 4, QTableWidgetItem(modified_time))

        except Exception as e:
            logger.error(f"更新文档表格失败: {e}")

    def _calculate_text_analysis(self, documents):
        """计算文本分析"""
        try:
            all_content = ""
            for doc in documents:
                if (getattr(getattr(doc, 'type', object), 'value', '') == "chapter"):
                    all_content += doc.content + "\n"

            if not all_content.strip():
                return

            # 计算句子数量
            sentences = re.split(r'[。！？.!?]', all_content)
            sentence_count = len([s for s in sentences if s.strip()])

            # 计算段落数量
            paragraphs = [p for p in all_content.split('\n') if p.strip()]
            paragraph_count = len(paragraphs)

            # 计算平均长度
            total_words = sum(len(doc.content) for doc in documents if (getattr(getattr(doc, 'type', object), 'value', '') == "chapter"))
            avg_sentence_length = total_words // sentence_count if sentence_count > 0 else 0
            avg_paragraph_length = total_words // paragraph_count if paragraph_count > 0 else 0

            # 更新UI
            self.sentence_count_label.setText(str(sentence_count))
            self.paragraph_count_label.setText(str(paragraph_count))
            self.avg_sentence_length_label.setText(f"{avg_sentence_length} 字")
            self.avg_paragraph_length_label.setText(f"{avg_paragraph_length} 字")

        except Exception as e:
            logger.error(f"计算文本分析失败: {e}")

    def _update_statistics(self):
        """定时更新统计"""
        self._load_statistics()

    def _export_report(self):
        """导出统计报告"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出统计报告",
                f"字数统计报告_{datetime.now().strftime('%Y%m%d')}.txt",
                "文本文件 (*.txt);;HTML文件 (*.html)"
            )

            if file_path:
                self._generate_report(file_path)

        except Exception as e:
            logger.error(f"导出报告失败: {e}")

    def _generate_report(self, file_path: str):
        """生成统计报告"""
        try:
            report_content = f"""
字数统计报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 总体统计 ===
总字数: {self.total_words_label.text()}
总字符数: {self.total_chars_label.text()}
文档数量: {self.doc_count_label.text()}
平均每文档: {self.avg_words_label.text()}

=== 目标进度 ===
当前进度: {self.current_progress_label.text()}
目标字数: {self.target_label.text()}
完成百分比: {self.completion_percentage_label.text()}
剩余字数: {self.remaining_words_label.text()}

=== 文本分析 ===
句子数量: {self.sentence_count_label.text()}
段落数量: {self.paragraph_count_label.text()}
平均句长: {self.avg_sentence_length_label.text()}
平均段长: {self.avg_paragraph_length_label.text()}

---
由AI小说编辑器 2.0 生成
            """.strip()

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "导出成功", f"统计报告已保存到:\n{file_path}")

        except Exception as e:
            logger.error(f"生成报告失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        try:
            self.update_timer.stop()
        except Exception:
            pass
        # 无需显式停止线程池任务；通过 _pending_task 引用防重入
        self._pending_task = None
        event.accept()

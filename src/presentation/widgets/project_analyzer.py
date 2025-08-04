#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目分析组件

提供全面的项目分析功能，包括内容分析、角色分析、情节分析等
"""

from typing import Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QFrame, QScrollArea, QTabWidget, QTreeWidget, 
    QTreeWidgetItem, QProgressBar, QComboBox, QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

try:
    from src.presentation.widgets.ai_workers import AITaskWorker, AITaskConfig, AITaskType, create_task_configs
except ImportError:
    try:
        from .ai_workers import AITaskWorker, AITaskConfig, AITaskType, create_task_configs
    except ImportError:
        # 创建占位符类
        from enum import Enum
        from PyQt6.QtCore import QObject

        class AITaskType(Enum):
            ANALYZE_STRUCTURE = "analyze_structure"
            ANALYZE_CHARACTERS = "analyze_characters"
            ANALYZE_PLOT = "analyze_plot"

        class AITaskConfig:
            def __init__(self, task_type, prompt, **kwargs):
                self.task_type = task_type
                self.prompt = prompt
                self.__dict__.update(kwargs)

        class AITaskWorker(QObject):
            def __init__(self, ai_service=None):
                super().__init__()
                self.ai_service = ai_service

        def create_task_configs():
            return []
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ProjectAnalyzerWidget(QWidget):
    """
    项目分析组件

    提供全面的项目分析功能，包括内容分析、角色分析、情节分析等。
    使用AI技术对项目进行深度分析，为创作提供有价值的洞察。

    实现方式：
    - 使用标签页组织不同类型的分析
    - 集成AI服务进行智能分析
    - 提供可视化的分析结果展示
    - 支持分析结果的导出和保存
    - 实时更新项目统计信息

    Attributes:
        ai_service: AI服务实例
        current_project: 当前分析的项目
        project_documents: 项目文档数据
        current_worker: 当前执行的AI任务工作器
        task_configs: AI任务配置列表

    Signals:
        status_updated: 状态更新信号(status_message)
        analysis_completed: 分析完成信号(analysis_type, results)
    """

    # 信号定义
    status_updated = pyqtSignal(str)
    analysis_completed = pyqtSignal(str, str)  # 分析类型, 结果

    def __init__(self, ai_service, parent=None):
        """
        初始化项目分析器

        Args:
            ai_service: AI服务实例，用于智能分析
            parent: 父组件
        """
        super().__init__(parent)
        self.ai_service = ai_service
        self.current_project = None
        self.project_documents: Dict[str, Any] = {}
        self.current_worker: Optional[AITaskWorker] = None
        self.task_configs = create_task_configs()

        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("🔍 项目深度分析")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 创建分析功能区域
        self._create_analysis_controls(layout)
        
        # 创建结果显示区域
        self._create_results_area(layout)
        
    def _create_analysis_controls(self, layout):
        """创建分析控制区域"""
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        controls_layout = QVBoxLayout(controls_frame)
        
        # 分析类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("分析类型:"))
        
        self.analysis_type_combo = QComboBox()
        analysis_types = [
            ("project_analysis", "🔍 项目全面分析"),
            ("character_analysis", "👥 角色深度分析"),
            ("plot_analysis", "📖 情节结构分析"),
            ("style_analysis", "✍️ 写作风格分析"),
            ("content_optimization", "⚡ 内容优化建议"),
            ("outline_generation", "📋 大纲生成")
        ]
        
        for value, text in analysis_types:
            self.analysis_type_combo.addItem(text, value)
            
        type_layout.addWidget(self.analysis_type_combo)
        type_layout.addStretch()
        
        controls_layout.addLayout(type_layout)
        
        # 分析按钮组
        buttons_layout = QHBoxLayout()
        
        self.start_analysis_btn = QPushButton("🚀 开始分析")
        self.start_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        buttons_layout.addWidget(self.start_analysis_btn)
        
        self.stop_analysis_btn = QPushButton("⏹️ 停止分析")
        self.stop_analysis_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_analysis_btn)
        
        buttons_layout.addStretch()
        
        # 导出按钮
        self.export_report_btn = QPushButton("📄 导出报告")
        buttons_layout.addWidget(self.export_report_btn)
        
        controls_layout.addLayout(buttons_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.analysis_status = QLabel("准备就绪")
        self.analysis_status.setStyleSheet("color: #666; font-style: italic;")
        controls_layout.addWidget(self.analysis_status)
        
        layout.addWidget(controls_frame)
        
    def _create_results_area(self, layout):
        """创建结果显示区域"""
        # 创建标签页
        self.results_tab = QTabWidget()
        
        # 分析结果标签页
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        self.analysis_result.setPlaceholderText("分析结果将显示在这里...")
        self.results_tab.addTab(self.analysis_result, "📊 分析结果")
        
        # 改进建议标签页
        self.improvement_suggestions = QTextEdit()
        self.improvement_suggestions.setReadOnly(True)
        self.improvement_suggestions.setPlaceholderText("改进建议将显示在这里...")
        self.results_tab.addTab(self.improvement_suggestions, "💡 改进建议")
        
        # 项目统计标签页
        self.project_stats = self._create_project_stats_widget()
        self.results_tab.addTab(self.project_stats, "📈 项目统计")
        
        layout.addWidget(self.results_tab)
        
    def _create_project_stats_widget(self) -> QWidget:
        """创建项目统计组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 统计信息树
        self.stats_tree = QTreeWidget()
        self.stats_tree.setHeaderLabels(["项目", "统计信息"])
        layout.addWidget(self.stats_tree)
        
        # 刷新统计按钮
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.clicked.connect(self._refresh_project_stats)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        
        layout.addLayout(refresh_layout)
        
        return widget
        
    def _setup_connections(self):
        """设置信号连接"""
        self.start_analysis_btn.clicked.connect(self._start_analysis)
        self.stop_analysis_btn.clicked.connect(self._stop_analysis)
        self.export_report_btn.clicked.connect(self._export_analysis_report)
        
    def set_project(self, project, documents: Dict[str, Any]):
        """设置当前项目"""
        self.current_project = project
        self.project_documents = documents
        self._refresh_project_stats()
        self.analysis_status.setText(f"项目已加载: {project.name if project else '无'}")
        
    def _start_analysis(self):
        """开始分析"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先加载项目")
            return
            
        if self.current_worker and self.current_worker.isRunning():
            return
            
        # 获取选择的分析类型
        analysis_type = self.analysis_type_combo.currentData()
        task_type = AITaskType(analysis_type)
        
        # 获取任务配置
        config = self.task_configs.get(task_type)
        if not config:
            QMessageBox.warning(self, "错误", "未找到分析配置")
            return
            
        # 收集项目内容
        project_content = self._collect_project_content()
        if not project_content:
            QMessageBox.warning(self, "警告", "项目内容为空")
            return
            
        # 构建提示词
        prompt = config.prompt_template.format(project_content=project_content)
        
        # 创建工作线程
        self.current_worker = AITaskWorker(prompt, config)
        self.current_worker.chunk_received.connect(self._on_analysis_chunk_received)
        self.current_worker.task_completed.connect(self._on_analysis_completed)
        self.current_worker.task_failed.connect(self._on_analysis_failed)
        
        # 更新UI状态
        self.start_analysis_btn.setEnabled(False)
        self.stop_analysis_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.analysis_status.setText(f"正在进行{config.title}...")
        
        # 清空结果区域
        self.analysis_result.clear()
        
        # 启动分析
        self.current_worker.start()
        
    def _stop_analysis(self):
        """停止分析"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
            
        self._reset_ui_state()
        self.analysis_status.setText("分析已停止")
        
    def _on_analysis_chunk_received(self, chunk: str):
        """处理分析流式响应块"""
        cursor = self.analysis_result.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.analysis_result.setTextCursor(cursor)
        
    def _on_analysis_completed(self, result: str):
        """分析完成处理"""
        self._reset_ui_state()
        self.analysis_status.setText("分析完成")
        
        # 发送完成信号
        analysis_type = self.analysis_type_combo.currentText()
        self.analysis_completed.emit(analysis_type, result)
        
        # 如果是项目分析，尝试提取改进建议
        if "项目全面分析" in analysis_type:
            self._extract_improvement_suggestions(result)
            
    def _on_analysis_failed(self, error: str):
        """分析失败处理"""
        self._reset_ui_state()
        self.analysis_status.setText(f"分析失败: {error}")
        self.analysis_result.setText(f"分析失败: {error}")
        
    def _extract_improvement_suggestions(self, analysis_result: str):
        """从分析结果中提取改进建议"""
        import re

        lines = analysis_result.split('\n')
        suggestions = []

        # 多种模式匹配建议内容
        suggestion_patterns = [
            r'建议[:：]\s*(.*)',
            r'改进[:：]\s*(.*)',
            r'优化[:：]\s*(.*)',
            r'提升[:：]\s*(.*)',
            r'推荐[:：]\s*(.*)',
            r'可以[:：]\s*(.*)',
            r'应该[:：]\s*(.*)',
            r'需要[:：]\s*(.*)',
            r'^\d+[\.、]\s*(.*建议.*|.*改进.*|.*优化.*)',
            r'^[•·-]\s*(.*建议.*|.*改进.*|.*优化.*)',
        ]

        # 关键词段落识别
        suggestion_keywords = [
            '建议', '改进', '优化', '提升', '推荐', '可以', '应该', '需要',
            '不足', '问题', '缺陷', '弱点', '改善', '完善', '加强', '增强'
        ]

        # 第一步：直接模式匹配
        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in suggestion_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    suggestion = match.group(1).strip() if match.groups() else line
                    if suggestion and len(suggestion) > 5:  # 过滤太短的建议
                        suggestions.append(f"• {suggestion}")

        # 第二步：段落级别分析
        if not suggestions:
            current_paragraph = []
            in_suggestion_context = False

            for line in lines:
                line = line.strip()
                if not line:
                    if current_paragraph and in_suggestion_context:
                        paragraph_text = ' '.join(current_paragraph)
                        if len(paragraph_text) > 20:  # 过滤太短的段落
                            suggestions.append(f"• {paragraph_text}")
                    current_paragraph = []
                    in_suggestion_context = False
                    continue

                # 检查是否包含建议关键词
                contains_keywords = any(keyword in line for keyword in suggestion_keywords)

                if contains_keywords:
                    in_suggestion_context = True
                    current_paragraph.append(line)
                elif in_suggestion_context:
                    current_paragraph.append(line)
                else:
                    current_paragraph = []

            # 处理最后一个段落
            if current_paragraph and in_suggestion_context:
                paragraph_text = ' '.join(current_paragraph)
                if len(paragraph_text) > 20:
                    suggestions.append(f"• {paragraph_text}")

        # 第三步：智能提取（如果前面都没找到）
        if not suggestions:
            # 寻找包含动词的句子，这些通常是建议
            action_verbs = ['增加', '减少', '调整', '修改', '删除', '添加', '强化', '弱化', '重写', '重构']

            for line in lines:
                line = line.strip()
                if any(verb in line for verb in action_verbs) and len(line) > 15:
                    suggestions.append(f"• {line}")

        # 去重和格式化
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            # 简单的去重逻辑
            key = suggestion.lower().replace('•', '').strip()[:50]
            if key not in seen and len(key) > 10:
                seen.add(key)
                unique_suggestions.append(suggestion)

        # 限制建议数量
        if len(unique_suggestions) > 10:
            unique_suggestions = unique_suggestions[:10]
            unique_suggestions.append("• ...")

        if unique_suggestions:
            formatted_suggestions = '\n'.join(unique_suggestions)
            self.improvement_suggestions.setText(formatted_suggestions)
        else:
            self.improvement_suggestions.setText(
                "未能从分析结果中提取到具体的改进建议。\n\n"
                "建议：\n"
                "• 检查分析结果的格式和内容\n"
                "• 确保AI分析包含明确的改进建议\n"
                "• 可以手动查看完整分析结果获取更多信息"
            )
            
    def _reset_ui_state(self):
        """重置UI状态"""
        self.start_analysis_btn.setEnabled(True)
        self.stop_analysis_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
    def _collect_project_content(self) -> str:
        """收集项目内容"""
        if not self.project_documents:
            return ""
            
        content_parts = []
        
        # 添加项目基本信息
        if self.current_project:
            content_parts.append(f"项目名称: {self.current_project.name}")
            content_parts.append(f"项目描述: {getattr(self.current_project, 'description', '无')}")
            content_parts.append("")
            
        # 添加文档内容
        for doc_id, doc_data in self.project_documents.items():
            if isinstance(doc_data, dict):
                title = doc_data.get('title', f'文档{doc_id}')
                content = doc_data.get('content', '')
            else:
                title = f'文档{doc_id}'
                content = str(doc_data)
                
            if content.strip():
                content_parts.append(f"=== {title} ===")
                content_parts.append(content)
                content_parts.append("")
                
        return '\n'.join(content_parts)
        
    def _refresh_project_stats(self):
        """刷新项目统计"""
        self.stats_tree.clear()
        
        if not self.current_project or not self.project_documents:
            return
            
        # 项目基本信息
        project_item = QTreeWidgetItem(["项目信息", ""])
        self.stats_tree.addTopLevelItem(project_item)
        
        # 项目名称
        name_item = QTreeWidgetItem(["项目名称", self.current_project.name])
        project_item.addChild(name_item)
        
        # 文档统计
        docs_item = QTreeWidgetItem(["文档统计", ""])
        self.stats_tree.addTopLevelItem(docs_item)
        
        total_chars = 0
        total_words = 0
        doc_count = len(self.project_documents)
        
        for doc_id, doc_data in self.project_documents.items():
            if isinstance(doc_data, dict):
                content = doc_data.get('content', '')
                title = doc_data.get('title', f'文档{doc_id}')
            else:
                content = str(doc_data)
                title = f'文档{doc_id}'
                
            char_count = len(content)
            word_count = len(content.split())
            
            total_chars += char_count
            total_words += word_count
            
            doc_item = QTreeWidgetItem([title, f"{char_count}字, {word_count}词"])
            docs_item.addChild(doc_item)
            
        # 总计
        summary_item = QTreeWidgetItem(["总计", f"{doc_count}个文档, {total_chars}字, {total_words}词"])
        docs_item.addChild(summary_item)
        
        # 展开所有项目
        self.stats_tree.expandAll()
        
    def _export_analysis_report(self):
        """导出分析报告"""
        if not self.analysis_result.toPlainText().strip():
            QMessageBox.warning(self, "警告", "没有分析结果可导出")
            return
            
        # 选择保存文件
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出分析报告",
            f"分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            "Markdown文件 (*.md);;文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not file_path:
            return
            
        try:
            # 生成报告内容
            report_content = self._generate_report_content()
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            QMessageBox.information(self, "成功", f"报告已导出到: {file_path}")
            self.status_updated.emit(f"报告已导出: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            
    def _generate_report_content(self) -> str:
        """生成报告内容"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        analysis_type = self.analysis_type_combo.currentText()
        
        content = f"""# 项目分析报告

## 基本信息
- **生成时间**: {timestamp}
- **分析类型**: {analysis_type}
- **项目名称**: {self.current_project.name if self.current_project else '未知'}

## 分析结果

{self.analysis_result.toPlainText()}

## 改进建议

{self.improvement_suggestions.toPlainText()}

---
*此报告由AI小说编辑器自动生成*
"""
        return content
        
    def cleanup(self):
        """清理资源"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()

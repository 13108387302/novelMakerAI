#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局AI面板 - 重构版本

简化的主面板，作为各个AI组件的容器
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QFrame, QPushButton, QGridLayout, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# 添加项目根目录到Python路径
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 创建简单的占位符组件（避免复杂的导入问题）

class WritingAssistantWidget(QWidget):
    """
    写作助手组件

    提供AI写作辅助功能的组件。

    Signals:
        text_applied: 文本应用信号
        status_updated: 状态更新信号
    """
    text_applied = pyqtSignal(str)
    status_updated = pyqtSignal(str)

    def __init__(self, ai_service=None):
        """
        初始化写作助手组件

        Args:
            ai_service: AI服务实例（可选）
        """
        super().__init__()
        self.ai_service = ai_service
        self._setup_ui()

    def _setup_ui(self):
        """设置用户界面"""
        from PyQt6.QtWidgets import QTextEdit, QGridLayout

        layout = QVBoxLayout()

        # 标题
        title = QLabel("✍️ 写作助手")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 输入区域
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("请输入需要处理的文本...")
        self.input_text.setMaximumHeight(100)
        layout.addWidget(QLabel("输入文本:"))
        layout.addWidget(self.input_text)

        # 功能按钮
        button_layout = QGridLayout()

        self.inspiration_btn = QPushButton("💡 灵感生成")
        self.polish_btn = QPushButton("✨ 文本润色")
        self.style_btn = QPushButton("🎨 风格转换")
        self.grammar_btn = QPushButton("📝 语法检查")

        button_layout.addWidget(self.inspiration_btn, 0, 0)
        button_layout.addWidget(self.polish_btn, 0, 1)
        button_layout.addWidget(self.style_btn, 1, 0)
        button_layout.addWidget(self.grammar_btn, 1, 1)

        layout.addLayout(button_layout)

        # 输出区域
        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("AI响应将显示在这里...")
        self.output_text.setReadOnly(True)
        layout.addWidget(QLabel("AI响应:"))
        layout.addWidget(self.output_text)

        # 连接信号
        self.inspiration_btn.clicked.connect(self.generate_inspiration)
        self.polish_btn.clicked.connect(self.polish_text)
        self.style_btn.clicked.connect(self.convert_style)
        self.grammar_btn.clicked.connect(self.check_grammar)

        self.setLayout(layout)

    def generate_inspiration(self):
        """生成灵感"""
        self.output_text.setPlainText("正在生成灵感...")
        self.status_updated.emit("生成灵感中...")
        # 这里可以调用AI服务

    def polish_text(self):
        """润色文本"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要润色的文本")
            return
        self.output_text.setPlainText("正在润色文本...")
        self.status_updated.emit("润色文本中...")

    def convert_style(self):
        """转换风格"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要转换风格的文本")
            return
        self.output_text.setPlainText("正在转换风格...")
        self.status_updated.emit("转换风格中...")

    def check_grammar(self):
        """检查语法"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要检查的文本")
            return
        self.output_text.setPlainText("正在检查语法...")
        self.status_updated.emit("检查语法中...")

    def cleanup(self):
        """
        清理资源

        释放组件占用的资源。
        """
        pass

class ProjectAnalyzerWidget(QWidget):
    analysis_completed = pyqtSignal(str, str)
    status_updated = pyqtSignal(str)

    def __init__(self, ai_service=None):
        super().__init__()
        self.ai_service = ai_service
        self._setup_ui()

    def _setup_ui(self):
        """设置用户界面"""
        from PyQt6.QtWidgets import QTextEdit, QGridLayout, QScrollArea

        layout = QVBoxLayout()

        # 标题
        title = QLabel("📊 项目分析器")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 分析功能按钮
        button_layout = QGridLayout()

        self.plot_analysis_btn = QPushButton("📖 情节分析")
        self.character_analysis_btn = QPushButton("👤 角色分析")
        self.theme_analysis_btn = QPushButton("🎭 主题分析")
        self.structure_analysis_btn = QPushButton("🏗️ 结构分析")

        button_layout.addWidget(self.plot_analysis_btn, 0, 0)
        button_layout.addWidget(self.character_analysis_btn, 0, 1)
        button_layout.addWidget(self.theme_analysis_btn, 1, 0)
        button_layout.addWidget(self.structure_analysis_btn, 1, 1)

        layout.addLayout(button_layout)

        # 结果显示区域
        self.results_area = QTextEdit()
        self.results_area.setPlaceholderText("分析结果将显示在这里...")
        self.results_area.setReadOnly(True)
        layout.addWidget(QLabel("分析结果:"))
        layout.addWidget(self.results_area)

        # 连接信号
        self.plot_analysis_btn.clicked.connect(self.analyze_plot)
        self.character_analysis_btn.clicked.connect(self.analyze_characters)
        self.theme_analysis_btn.clicked.connect(self.analyze_themes)
        self.structure_analysis_btn.clicked.connect(self.analyze_structure)

        self.setLayout(layout)

    def analyze_plot(self):
        """分析情节"""
        self.results_area.setPlainText("正在分析情节结构...")
        self.status_updated.emit("分析情节中...")

    def analyze_characters(self):
        """分析角色"""
        self.results_area.setPlainText("正在分析角色关系...")
        self.status_updated.emit("分析角色中...")

    def analyze_themes(self):
        """分析主题"""
        self.results_area.setPlainText("正在分析主题内容...")
        self.status_updated.emit("分析主题中...")

    def analyze_structure(self):
        """分析结构"""
        self.results_area.setPlainText("正在分析文档结构...")
        self.status_updated.emit("分析结构中...")

    def cleanup(self):
        """清理资源"""
        pass

class ContentToolsWidget(QWidget):
    text_applied = pyqtSignal(str)
    tool_applied = pyqtSignal(str, str)
    status_updated = pyqtSignal(str)

    def __init__(self, ai_service=None):
        super().__init__()
        self.ai_service = ai_service
        self._setup_ui()

    def _setup_ui(self):
        """设置用户界面"""
        from PyQt6.QtWidgets import QTextEdit, QGridLayout, QTabWidget

        layout = QVBoxLayout()

        # 标题
        title = QLabel("🛠️ 内容工具箱")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 工具标签页
        self.tools_tab = QTabWidget()

        # 文本处理工具
        text_tools = self._create_text_tools()
        self.tools_tab.addTab(text_tools, "📝 文本处理")

        # 格式工具
        format_tools = self._create_format_tools()
        self.tools_tab.addTab(format_tools, "📋 格式工具")

        # 实用工具
        utility_tools = self._create_utility_tools()
        self.tools_tab.addTab(utility_tools, "🔧 实用工具")

        layout.addWidget(self.tools_tab)

        # 输入输出区域
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("请输入需要处理的文本...")
        self.input_text.setMaximumHeight(80)
        layout.addWidget(QLabel("输入文本:"))
        layout.addWidget(self.input_text)

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("处理结果将显示在这里...")
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(80)
        layout.addWidget(QLabel("处理结果:"))
        layout.addWidget(self.output_text)

        self.setLayout(layout)

    def _create_text_tools(self):
        """创建文本处理工具"""
        widget = QWidget()
        layout = QGridLayout()

        # 文本清理工具
        self.clean_btn = QPushButton("🧹 文本清理")
        self.clean_btn.setToolTip("清理多余空格、换行等")
        self.clean_btn.clicked.connect(self.clean_text)
        layout.addWidget(self.clean_btn, 0, 0)

        # 繁简转换
        self.convert_btn = QPushButton("🔄 繁简转换")
        self.convert_btn.setToolTip("繁体简体互转")
        self.convert_btn.clicked.connect(self.convert_text)
        layout.addWidget(self.convert_btn, 0, 1)

        # 标点规范
        self.punctuation_btn = QPushButton("📍 标点规范")
        self.punctuation_btn.setToolTip("规范标点符号")
        self.punctuation_btn.clicked.connect(self.normalize_punctuation)
        layout.addWidget(self.punctuation_btn, 1, 0)

        # 段落整理
        self.paragraph_btn = QPushButton("📄 段落整理")
        self.paragraph_btn.setToolTip("整理段落结构")
        self.paragraph_btn.clicked.connect(self.organize_paragraphs)
        layout.addWidget(self.paragraph_btn, 1, 1)

        widget.setLayout(layout)
        return widget

    def _create_format_tools(self):
        """创建格式工具"""
        widget = QWidget()
        layout = QGridLayout()

        # 标题生成
        self.title_btn = QPushButton("📰 标题生成")
        self.title_btn.setToolTip("为内容生成标题")
        self.title_btn.clicked.connect(self.generate_title)
        layout.addWidget(self.title_btn, 0, 0)

        # 摘要生成
        self.summary_btn = QPushButton("📋 摘要生成")
        self.summary_btn.setToolTip("生成内容摘要")
        self.summary_btn.clicked.connect(self.generate_summary)
        layout.addWidget(self.summary_btn, 0, 1)

        # 关键词提取
        self.keywords_btn = QPushButton("🏷️ 关键词提取")
        self.keywords_btn.setToolTip("提取关键词")
        self.keywords_btn.clicked.connect(self.extract_keywords)
        layout.addWidget(self.keywords_btn, 1, 0)

        # 大纲生成
        self.outline_btn = QPushButton("📝 大纲生成")
        self.outline_btn.setToolTip("生成内容大纲")
        self.outline_btn.clicked.connect(self.generate_outline)
        layout.addWidget(self.outline_btn, 1, 1)

        widget.setLayout(layout)
        return widget

    def _create_utility_tools(self):
        """创建实用工具"""
        widget = QWidget()
        layout = QGridLayout()

        # 字数统计
        self.count_btn = QPushButton("📊 字数统计")
        self.count_btn.setToolTip("统计字数、段落数等")
        self.count_btn.clicked.connect(self.count_words)
        layout.addWidget(self.count_btn, 0, 0)

        # 重复检查
        self.duplicate_btn = QPushButton("🔍 重复检查")
        self.duplicate_btn.setToolTip("检查重复内容")
        self.duplicate_btn.clicked.connect(self.check_duplicates)
        layout.addWidget(self.duplicate_btn, 0, 1)

        # 术语管理
        self.terms_btn = QPushButton("📚 术语管理")
        self.terms_btn.setToolTip("管理专业术语")
        self.terms_btn.clicked.connect(self.manage_terms)
        layout.addWidget(self.terms_btn, 1, 0)

        # 文本对比
        self.compare_btn = QPushButton("⚖️ 文本对比")
        self.compare_btn.setToolTip("对比两段文本")
        self.compare_btn.clicked.connect(self.compare_texts)
        layout.addWidget(self.compare_btn, 1, 1)

        widget.setLayout(layout)
        return widget

    # 文本处理工具方法
    def clean_text(self):
        """清理文本"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要清理的文本")
            return

        # 简单的文本清理
        cleaned = text.strip()
        cleaned = ' '.join(cleaned.split())  # 清理多余空格
        cleaned = cleaned.replace('\n\n\n', '\n\n')  # 清理多余换行

        self.output_text.setPlainText(cleaned)
        self.status_updated.emit("文本清理完成")

    def convert_text(self):
        """繁简转换"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要转换的文本")
            return

        self.output_text.setPlainText("繁简转换功能需要配置转换库")
        self.status_updated.emit("繁简转换中...")

    def normalize_punctuation(self):
        """标点规范"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要规范的文本")
            return

        # 简单的标点规范
        normalized = text.replace('，。', '。').replace('。，', '。')
        normalized = normalized.replace('？！', '！').replace('！？', '！')

        self.output_text.setPlainText(normalized)
        self.status_updated.emit("标点规范完成")

    def organize_paragraphs(self):
        """整理段落"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入需要整理的文本")
            return

        # 简单的段落整理
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        organized = '\n\n'.join(paragraphs)

        self.output_text.setPlainText(organized)
        self.status_updated.emit("段落整理完成")

    # 格式工具方法
    def generate_title(self):
        """生成标题"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入内容")
            return

        self.output_text.setPlainText("正在生成标题...")
        self.status_updated.emit("生成标题中...")
        # 这里可以调用AI服务

    def generate_summary(self):
        """生成摘要"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入内容")
            return

        self.output_text.setPlainText("正在生成摘要...")
        self.status_updated.emit("生成摘要中...")

    def extract_keywords(self):
        """提取关键词"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入内容")
            return

        self.output_text.setPlainText("正在提取关键词...")
        self.status_updated.emit("提取关键词中...")

    def generate_outline(self):
        """生成大纲"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入内容")
            return

        self.output_text.setPlainText("正在生成大纲...")
        self.status_updated.emit("生成大纲中...")

    # 实用工具方法
    def count_words(self):
        """字数统计"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入文本")
            return

        char_count = len(text)
        word_count = len(text.split())
        line_count = len(text.split('\n'))
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])

        stats = f"""字符数: {char_count}
词数: {word_count}
行数: {line_count}
段落数: {paragraph_count}"""

        self.output_text.setPlainText(stats)
        self.status_updated.emit("统计完成")

    def check_duplicates(self):
        """检查重复"""
        text = self.input_text.toPlainText()
        if not text.strip():
            self.output_text.setPlainText("请先输入文本")
            return

        self.output_text.setPlainText("正在检查重复内容...")
        self.status_updated.emit("检查重复中...")

    def manage_terms(self):
        """术语管理"""
        self.output_text.setPlainText("术语管理功能开发中...")
        self.status_updated.emit("术语管理")

    def compare_texts(self):
        """文本对比"""
        self.output_text.setPlainText("文本对比功能开发中...")
        self.status_updated.emit("文本对比")

    def cleanup(self):
        """清理资源"""
        pass

# 简单的日志记录器
try:
    from src.shared.utils.logger import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class ComprehensiveGlobalAIPanel(QWidget):
    """
    综合全局AI面板 - 重构版本

    提供完整的AI功能面板，包含写作助手、项目分析等多个AI组件。
    使用标签页组织不同的AI功能模块。

    实现方式：
    - 使用QTabWidget组织多个AI功能组件
    - 提供统一的信号接口
    - 支持组件的动态加载和卸载
    - 包含完整的资源管理和清理机制

    Attributes:
        ai_service: AI服务实例
        tab_widget: 标签页组件
        writing_assistant: 写作助手组件
        project_analyzer: 项目分析组件

    Signals:
        text_applied: 文本应用到编辑器信号
        status_updated: 状态更新信号
    """

    # 信号定义
    text_applied = pyqtSignal(str)  # 文本应用到编辑器
    status_updated = pyqtSignal(str)  # 状态更新
    
    def __init__(self, ai_service, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.current_project = None
        self.project_documents: Dict[str, Any] = {}
        
        # 子组件
        self.writing_assistant: Optional[WritingAssistantWidget] = None
        self.project_analyzer: Optional[ProjectAnalyzerWidget] = None
        self.content_tools: Optional[ContentToolsWidget] = None
        
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题区域
        self._create_header(layout)
        
        # 主要内容区域 - 使用标签页
        self.main_tabs = QTabWidget()
        
        # 写作助手标签页
        self.writing_assistant = WritingAssistantWidget(self.ai_service)
        self.main_tabs.addTab(self.writing_assistant, "🤖 写作助手")
        
        # 项目分析标签页 - 使用完整版本
        try:
            from src.presentation.widgets.project_analyzer import ProjectAnalyzerWidget as FullProjectAnalyzer
            self.project_analyzer = FullProjectAnalyzer(self.ai_service)
        except ImportError:
            # 如果导入失败，使用占位符版本
            self.project_analyzer = ProjectAnalyzerWidget(self.ai_service)
        self.main_tabs.addTab(self.project_analyzer, "🔍 项目分析")
        
        # 内容工具标签页
        self.content_tools = ContentToolsWidget(self.ai_service)
        self.main_tabs.addTab(self.content_tools, "🛠️ 内容工具")
        
        layout.addWidget(self.main_tabs)
        
        # 状态栏
        self._create_status_bar(layout)
        
    def _create_header(self, layout):
        """创建头部区域"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        
        # 主标题
        title_label = QLabel("🤖 AI写作助手中心")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("集成写作助手、项目分析和内容工具的综合AI平台")
        subtitle_label.setFont(QFont("Arial", 10))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; font-style: italic;")
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_frame)
        
    def _create_status_bar(self, layout):
        """创建状态栏"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        # 项目状态
        self.project_status_label = QLabel("项目: 未加载")
        self.project_status_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.project_status_label)
        
        status_layout.addStretch()
        
        # 操作状态
        self.operation_status_label = QLabel("就绪")
        self.operation_status_label.setStyleSheet("color: #2e8b57;")
        status_layout.addWidget(self.operation_status_label)
        
        # 快速操作按钮
        self.quick_clear_btn = QPushButton("🗑️ 清空所有")
        self.quick_clear_btn.setToolTip("清空所有输入和输出内容")
        status_layout.addWidget(self.quick_clear_btn)
        
        layout.addWidget(status_frame)
        
    def _setup_connections(self):
        """设置信号连接"""
        # 连接子组件信号
        if self.writing_assistant:
            self.writing_assistant.text_applied.connect(self.text_applied.emit)
            self.writing_assistant.status_updated.connect(self._update_status)
            
        if self.project_analyzer:
            self.project_analyzer.status_updated.connect(self._update_status)
            self.project_analyzer.analysis_completed.connect(self._on_analysis_completed)
            
        if self.content_tools:
            self.content_tools.text_applied.connect(self.text_applied.emit)
            self.content_tools.status_updated.connect(self._update_status)
            
        # 快速操作
        self.quick_clear_btn.clicked.connect(self._clear_all_content)
        
        # 标签页切换
        self.main_tabs.currentChanged.connect(self._on_tab_changed)
        
    def set_project(self, project, documents: Dict[str, Any]):
        """设置当前项目"""
        self.current_project = project
        self.project_documents = documents
        
        # 更新项目状态
        project_name = project.name if project else "未知项目"
        self.project_status_label.setText(f"项目: {project_name}")
        
        # 通知子组件
        if self.project_analyzer:
            self.project_analyzer.set_project(project, documents)
            
        logger.info(f"AI面板已加载项目: {project_name}")
        
    def _update_status(self, message: str):
        """更新状态"""
        self.operation_status_label.setText(message)
        self.status_updated.emit(message)
        
    def _on_analysis_completed(self, analysis_type: str, result: str):
        """分析完成处理"""
        self._update_status(f"{analysis_type}完成")
        logger.info(f"分析完成: {analysis_type}")
        
    def _clear_all_content(self):
        """清空所有内容"""
        try:
            # 清空写作助手
            if self.writing_assistant:
                if hasattr(self.writing_assistant, 'writing_editor'):
                    self.writing_assistant.writing_editor.clear()
                if hasattr(self.writing_assistant, 'chat_display'):
                    self.writing_assistant.chat_display.clear()
                if hasattr(self.writing_assistant, 'traditional_input'):
                    self.writing_assistant.traditional_input.clear()
                if hasattr(self.writing_assistant, 'traditional_output'):
                    self.writing_assistant.traditional_output.clear()
                    
            # 清空项目分析
            if self.project_analyzer:
                if hasattr(self.project_analyzer, 'analysis_result'):
                    self.project_analyzer.analysis_result.clear()
                if hasattr(self.project_analyzer, 'improvement_suggestions'):
                    self.project_analyzer.improvement_suggestions.clear()
                    
            # 清空内容工具
            if self.content_tools:
                if hasattr(self.content_tools, 'tool_input'):
                    self.content_tools.tool_input.clear()
                if hasattr(self.content_tools, 'tool_output'):
                    self.content_tools.tool_output.clear()
                    
            self._update_status("所有内容已清空")
            
        except Exception as e:
            logger.error(f"清空内容失败: {e}")
            self._update_status(f"清空失败: {e}")
            
    def _on_tab_changed(self, index: int):
        """标签页切换处理"""
        tab_names = ["写作助手", "项目分析", "内容工具"]
        if 0 <= index < len(tab_names):
            self._update_status(f"切换到{tab_names[index]}")
            
    def get_current_tab_name(self) -> str:
        """获取当前标签页名称"""
        current_index = self.main_tabs.currentIndex()
        tab_names = ["写作助手", "项目分析", "内容工具"]
        return tab_names[current_index] if 0 <= current_index < len(tab_names) else "未知"
        
    def switch_to_writing_assistant(self):
        """切换到写作助手"""
        self.main_tabs.setCurrentIndex(0)
        
    def switch_to_project_analyzer(self):
        """切换到项目分析"""
        self.main_tabs.setCurrentIndex(1)
        
    def switch_to_content_tools(self):
        """切换到内容工具"""
        self.main_tabs.setCurrentIndex(2)
        
    def get_writing_assistant(self) -> Optional[WritingAssistantWidget]:
        """获取写作助手组件"""
        return self.writing_assistant
        
    def get_project_analyzer(self) -> Optional[ProjectAnalyzerWidget]:
        """获取项目分析组件"""
        return self.project_analyzer
        
    def get_content_tools(self) -> Optional[ContentToolsWidget]:
        """获取内容工具组件"""
        return self.content_tools
        
    def cleanup(self):
        """清理资源"""
        try:
            # 清理子组件
            if self.writing_assistant:
                self.writing_assistant.cleanup()
                
            if self.project_analyzer:
                self.project_analyzer.cleanup()
                
            if self.content_tools:
                self.content_tools.cleanup()
                
            logger.info("AI面板资源清理完成")
            
        except Exception as e:
            logger.error(f"AI面板资源清理失败: {e}")
            
    def __del__(self):
        """析构函数"""
        self.cleanup()


# 为了向后兼容，保留原来的类名
GlobalAIPanel = ComprehensiveGlobalAIPanel

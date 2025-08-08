#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局AI面板

提供全局AI功能面板
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QScrollArea, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from .intelligent_ai_panel import IntelligentAIPanel
from ..components.modern_ai_widget import ModernAIWidget

logger = logging.getLogger(__name__)


class GlobalAIPanel(ModernAIWidget):
    """
    现代化全局AI面板

    提供全局AI功能，包括基础对话、翻译、摘要等功能，
    以及小说创作相关的高级功能。
    """

    def __init__(self, parent=None, settings_service=None):
        """
        初始化全局AI面板

        Args:
            parent: 父组件
            settings_service: 设置服务
        """
        super().__init__(parent, settings_service)
        self._setup_global_ui()

        # 初始化智能化功能（保持兼容性）
        try:
            self._setup_intelligent_features()
        except Exception as e:
            logger.warning(f"智能化功能初始化失败: {e}")
        
    def _setup_global_ui(self):
        """设置现代化全局UI"""
        # 获取或创建主布局
        if self.layout():
            main_layout = self.layout()
            # 清空现有布局
            while main_layout.count():
                child = main_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        else:
            main_layout = QVBoxLayout(self)

        main_layout.setSpacing(4)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # 创建滚动内容组件
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(6, 6, 6, 6)

        # 创建状态指示器
        self.status_indicator = self.create_status_indicator("AI助手就绪", "success")
        content_layout.addWidget(self.status_indicator)

        # 创建功能区域（重新设计）
        self._create_modern_functions_section(content_layout)

        # 创建聊天界面
        self._create_chat_section(content_layout)

        # 创建输出区域
        self._create_modern_output_section(content_layout)

        # 创建设置区域（移到底部）
        self._create_modern_settings_section(content_layout)

        # 添加弹性空间
        content_layout.addStretch()

        # 设置滚动区域
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        logger.info("现代化全局AI面板UI设置完成")

    def _create_modern_functions_section(self, parent_layout):
        """创建现代化功能区域"""
        from PyQt6.QtWidgets import QGridLayout, QFrame

        # 创建功能组框
        functions_group = self.create_group_box("🤖 AI功能")
        functions_layout = QGridLayout()
        functions_layout.setSpacing(8)
        functions_layout.setContentsMargins(12, 12, 12, 12)

        # 定义功能按钮 - 使用网格布局，每行3个按钮
        buttons_data = [
            ("💬 对话", "与AI进行自由对话", self._on_global_chat),
            ("🌐 翻译", "翻译选中的文字", self._on_global_translate),
            ("📝 摘要", "生成内容摘要", self._on_global_summary),
            ("✍️ 续写", "智能续写内容", self._on_smart_continue),
            ("🎭 角色", "角色分析", self._on_character_analysis),
            ("📊 分析", "情节分析", self._on_plot_analysis),
        ]

        # 创建按钮并添加到网格布局
        for i, (text, tooltip, callback) in enumerate(buttons_data):
            button = self.create_modern_button(text, "", "default", tooltip, callback)
            button.setMinimumHeight(40)
            button.setMaximumHeight(40)
            row = i // 3
            col = i % 3
            functions_layout.addWidget(button, row, col)

        functions_group.setLayout(functions_layout)
        parent_layout.addWidget(functions_group)

    def _create_chat_section(self, parent_layout):
        """创建聊天区域"""
        # 创建聊天组框
        chat_group = self.create_group_box("💬 AI智能对话")
        chat_layout = QVBoxLayout()
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(8)

        # 创建聊天界面
        chat_interface = self.create_chat_interface()
        chat_layout.addWidget(chat_interface)

        chat_group.setLayout(chat_layout)
        parent_layout.addWidget(chat_group)

    def _create_modern_output_section(self, parent_layout):
        """创建现代化输出区域"""
        output_group = self.create_group_box("💭 AI响应")
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(8, 8, 8, 8)

        # 创建输出文本区域
        self.output_area = self.create_output_area("AI的回复将显示在这里...")
        # 设置合理的高度范围
        self.output_area.setMinimumHeight(120)
        self.output_area.setMaximumHeight(250)
        output_layout.addWidget(self.output_area)

        output_group.setLayout(output_layout)
        parent_layout.addWidget(output_group)

    def _create_modern_settings_section(self, parent_layout):
        """创建现代化设置区域"""
        from PyQt6.QtWidgets import QCheckBox, QHBoxLayout

        settings_group = self.create_group_box("⚙️ 设置")
        settings_layout = QHBoxLayout()
        settings_layout.setContentsMargins(12, 8, 12, 8)

        # 流式输出开关
        self.streaming_checkbox = QCheckBox("启用流式输出")
        self.streaming_checkbox.setToolTip("启用后，AI响应将实时显示，提供更好的用户体验")
        self.streaming_checkbox.setChecked(self._get_streaming_preference())
        self.streaming_checkbox.stateChanged.connect(self._on_streaming_changed)

        settings_layout.addWidget(self.streaming_checkbox)
        settings_layout.addStretch()

        settings_group.setLayout(settings_layout)
        settings_group.setMaximumHeight(50)  # 限制高度
        parent_layout.addWidget(settings_group)








    def _on_global_chat(self):
        """处理全局对话"""
        # 如果有聊天界面，聚焦到输入框
        if hasattr(self, 'chat_input'):
            self.chat_input.setFocus()
            self.show_status("请在下方输入框中输入您的问题", "info")
        else:
            # 回退到原有方式
            self.show_status("准备AI对话...", "info")

            # 构建对话提示
            prompt = "你好！我是你的AI写作助手，有什么可以帮助你的吗？"
            if self.document_context:
                prompt = f"基于当前文档内容，我可以为你提供写作建议。当前文档内容：\n\n{self.document_context[:500]}...\n\n有什么可以帮助你的吗？"

            options = {
                'function_id': 'global_chat',
                'execution_mode': 'INTERACTIVE',
                'context': self.document_context,
                'selected_text': self.selected_text
            }

            self.execute_ai_request("ai_chat", prompt, options)

    def _on_global_translate(self):
        """处理全局翻译"""
        if not self.selected_text:
            self.show_status("请先选择要翻译的文字", "error")
            return

        prompt = f"请将以下文字翻译成中文：\n\n{self.selected_text}"
        options = {
            'function_id': 'global_translate',
            'execution_mode': 'AUTO_SELECTION',
            'context': self.document_context,
            'selected_text': self.selected_text
        }

        self.show_status("智能翻译中...", "info")
        self.execute_ai_request("translate", prompt, options)

    def _on_global_summary(self):
        """处理全局摘要"""
        target_text = self.selected_text if self.selected_text else self.document_context
        if not target_text:
            self.show_status("无内容可用于生成摘要", "error")
            return

        if self.selected_text:
            prompt = f"请为以下选中文字生成摘要：\n\n{self.selected_text}"
        else:
            prompt = f"请为以下文档内容生成摘要：\n\n{self.document_context[-2000:]}"  # 取最后2000字符

        options = {
            'function_id': 'global_summary',
            'execution_mode': 'HYBRID',
            'context': self.document_context,
            'selected_text': self.selected_text
        }

        self.show_status("生成摘要中...", "info")
        self.execute_ai_request("summary", prompt, options)

    def _on_service_diagnosis(self):
        """AI服务诊断"""
        self.show_status("正在诊断AI服务...", "info")
        try:
            diagnosis_report = self.get_ai_service_diagnosis()
            self._display_ai_response(diagnosis_report)
            self.show_status("AI服务诊断完成", "success")
        except Exception as e:
            error_msg = f"诊断失败: {str(e)}"
            self._display_ai_response(error_msg)
            self.show_status("诊断失败", "error")
            logger.error(f"AI服务诊断失败: {e}")

    # 新增的现代化回调方法
    def _on_outline_generation(self):
        """大纲生成"""
        self.show_status("正在生成大纲...", "info")
        self.execute_ai_request("outline_generation", "生成小说大纲", {"type": "outline"})

    def _on_character_creation(self):
        """人物设定"""
        self.show_status("正在创建人物设定...", "info")
        self.execute_ai_request("character_creation", "创建角色设定", {"type": "character"})

    def _on_worldbuilding(self):
        """世界观构建"""
        self.show_status("正在构建世界观...", "info")
        self.execute_ai_request("worldbuilding", "构建世界观", {"type": "worldbuilding"})

    def _on_smart_naming(self):
        """智能命名"""
        self.show_status("正在生成名字...", "info")
        self.execute_ai_request("smart_naming", "生成角色名字", {"type": "naming"})

    def _on_plot_analysis(self):
        """情节分析"""
        self.show_status("正在分析情节...", "info")
        self.execute_ai_request("plot_analysis", "分析情节结构", {"type": "plot_analysis"})

    def _on_pacing_analysis(self):
        """节奏分析"""
        self.show_status("正在分析节奏...", "info")
        self.execute_ai_request("pacing_analysis", "分析故事节奏", {"type": "pacing_analysis"})

    def _on_theme_analysis(self):
        """主题挖掘"""
        self.show_status("正在挖掘主题...", "info")
        self.execute_ai_request("theme_analysis", "挖掘作品主题", {"type": "theme_analysis"})

    def _on_style_analysis(self):
        """风格分析"""
        self.show_status("正在分析风格...", "info")
        self.execute_ai_request("style_analysis", "分析写作风格", {"type": "style_analysis"})

    def _setup_intelligent_features(self):
        """设置智能化功能（保持兼容性）"""
        try:
            # 尝试初始化智能化功能
            pass
        except Exception as e:
            logger.warning(f"智能化功能初始化失败: {e}")

    def _create_novel_tools(self, layout):
        """创建小说创作工具"""
        # 小说创作工具组
        novel_group = QGroupBox("📚 小说创作工具")
        novel_layout = QVBoxLayout(novel_group)

        # 创作助手按钮
        self._create_creation_buttons(novel_layout)

        # 分析工具按钮
        self._create_analysis_buttons(novel_layout)

        # 添加到主布局
        layout.addWidget(novel_group)

    def _create_creation_buttons(self, layout):
        """创建创作助手按钮"""
        # 第一行：大纲和人物
        row1_layout = QHBoxLayout()

        outline_btn = QPushButton("📋 大纲生成")
        outline_btn.setToolTip("根据主题生成小说大纲")
        outline_btn.clicked.connect(self._on_generate_outline)
        row1_layout.addWidget(outline_btn)

        character_btn = QPushButton("👤 人物设定")
        character_btn.setToolTip("创建详细的角色设定")
        character_btn.clicked.connect(self._on_create_character)
        row1_layout.addWidget(character_btn)

        layout.addLayout(row1_layout)

        # 第二行：世界观和名字
        row2_layout = QHBoxLayout()

        worldview_btn = QPushButton("🌍 世界观构建")
        worldview_btn.setToolTip("构建小说的世界观设定")
        worldview_btn.clicked.connect(self._on_build_worldview)
        row2_layout.addWidget(worldview_btn)

        naming_btn = QPushButton("🏷️ 智能命名")
        naming_btn.setToolTip("为角色、地点等生成合适的名字")
        naming_btn.clicked.connect(self._on_generate_names)
        row2_layout.addWidget(naming_btn)

        layout.addLayout(row2_layout)

    def _create_analysis_buttons(self, layout):
        """创建分析工具按钮"""
        # 第一行：情节和节奏
        row1_layout = QHBoxLayout()

        plot_analysis_btn = QPushButton("📊 情节分析")
        plot_analysis_btn.setToolTip("分析整体情节结构")
        plot_analysis_btn.clicked.connect(self._on_analyze_plot)
        row1_layout.addWidget(plot_analysis_btn)

        pace_btn = QPushButton("⏱️ 节奏分析")
        pace_btn.setToolTip("分析故事节奏和起伏")
        pace_btn.clicked.connect(self._on_analyze_pace)
        row1_layout.addWidget(pace_btn)

        layout.addLayout(row1_layout)

        # 第二行：主题和风格
        row2_layout = QHBoxLayout()

        theme_btn = QPushButton("🎭 主题挖掘")
        theme_btn.setToolTip("挖掘和分析作品主题")
        theme_btn.clicked.connect(self._on_analyze_theme)
        row2_layout.addWidget(theme_btn)

        style_analysis_btn = QPushButton("🎨 风格分析")
        style_analysis_btn.setToolTip("分析写作风格特点")
        style_analysis_btn.clicked.connect(self._on_analyze_style)
        row2_layout.addWidget(style_analysis_btn)

        layout.addLayout(row2_layout)

    # === 创作助手功能 ===
    def _on_generate_outline(self):
        """生成大纲"""
        self.show_status("正在生成大纲...", "info")

        prompt = """请帮我生成一个小说大纲。请提供以下信息：

1. 小说类型（如：都市、玄幻、悬疑等）
2. 主要主题或想法
3. 预期字数

我将根据您的输入生成详细的章节大纲，包括：
- 故事背景设定
- 主要角色介绍
- 情节发展脉络
- 各章节要点"""

        self._display_ai_response(f"[大纲生成]\n\n{prompt}")

    def _on_create_character(self):
        """创建人物设定"""
        self.show_status("正在创建人物设定...", "info")

        prompt = """请帮我创建详细的角色设定。请提供：

1. 角色基本信息（姓名、年龄、职业等）
2. 角色在故事中的作用
3. 性格特点要求

我将为您生成包含以下内容的完整角色档案：
- 外貌描述
- 性格特征
- 背景故事
- 行为习惯
- 语言风格
- 成长轨迹"""

        self._display_ai_response(f"[人物设定]\n\n{prompt}")

    def _on_build_worldview(self):
        """构建世界观"""
        self.show_status("正在构建世界观...", "info")

        prompt = """请帮我构建小说的世界观设定。请告诉我：

1. 故事类型和背景时代
2. 特殊设定需求
3. 重要的世界规则

我将为您创建包含以下内容的世界观：
- 地理环境
- 社会结构
- 文化背景
- 历史沿革
- 特殊规则（如魔法体系、科技水平等）
- 重要组织机构"""

        self._display_ai_response(f"[世界观构建]\n\n{prompt}")

    def _on_generate_names(self):
        """智能命名"""
        self.show_status("正在生成名字...", "info")

        prompt = """请帮我生成合适的名字。请告诉我：

1. 需要命名的对象类型（人物、地点、组织等）
2. 故事背景和风格
3. 特殊要求

我将为您提供：
- 多个候选名字
- 名字的含义解释
- 适用场景说明
- 文化背景考虑"""

        self._display_ai_response(f"[智能命名]\n\n{prompt}")

    # === 分析工具功能 ===
    def _on_analyze_plot(self):
        """情节分析"""
        if not self.document_context:
            self.show_status("请先打开文档", "warning")
            return

        self.show_status("正在分析情节...", "info")

        prompt = f"""请分析以下小说内容的情节结构：

内容：
{self.document_context[-2000:] if len(self.document_context) > 2000 else self.document_context}

请从以下角度分析：
1. 情节发展阶段（开端、发展、高潮、结局）
2. 主要冲突和矛盾
3. 情节转折点
4. 悬念设置
5. 改进建议"""

        self._display_ai_response(f"[情节分析]\n\n{prompt}")

    def _on_analyze_pace(self):
        """节奏分析"""
        if not self.document_context:
            self.show_status("请先打开文档", "warning")
            return

        self.show_status("正在分析节奏...", "info")

        prompt = f"""请分析以下内容的故事节奏：

内容：
{self.document_context[-1500:] if len(self.document_context) > 1500 else self.document_context}

分析要点：
1. 节奏快慢变化
2. 紧张感营造
3. 情感起伏
4. 信息密度
5. 节奏优化建议"""

        self._display_ai_response(f"[节奏分析]\n\n{prompt}")

    def _on_analyze_theme(self):
        """主题挖掘"""
        if not self.document_context:
            self.show_status("请先打开文档", "warning")
            return

        self.show_status("正在挖掘主题...", "info")

        prompt = f"""请深入挖掘以下内容的主题：

内容：
{self.document_context[-2000:] if len(self.document_context) > 2000 else self.document_context}

分析内容：
1. 核心主题识别
2. 次要主题分析
3. 主题表达方式
4. 价值观体现
5. 主题深化建议"""

        self._display_ai_response(f"[主题挖掘]\n\n{prompt}")

    def _on_analyze_style(self):
        """风格分析"""
        if not self.document_context:
            self.show_status("请先打开文档", "warning")
            return

        self.show_status("正在分析风格...", "info")

        prompt = f"""请分析以下内容的写作风格：

内容：
{self.document_context[-1000:] if len(self.document_context) > 1000 else self.document_context}

分析维度：
1. 语言特色
2. 叙述方式
3. 描写手法
4. 情感表达
5. 风格特点总结"""

        self._display_ai_response(f"[风格分析]\n\n{prompt}")

    def create_group_box(self, title: str):
        """创建分组框"""
        from PyQt6.QtWidgets import QGroupBox
        group_box = QGroupBox(title)
        return group_box

    def add_to_layout(self, widget):
        """添加组件到布局"""
        if hasattr(self, 'layout') and self.layout():
            self.layout().addWidget(widget)



    def _on_streaming_changed(self, state):
        """流式输出开关变化"""
        try:
            if self.settings_service:
                self.settings_service.set('ai.enable_streaming', state == 2)  # 2 = Qt.CheckState.Checked
                logger.info(f"流式输出设置已更新: {state == 2}")
            else:
                # 回退到全局容器获取
                from src.shared.ioc.container import get_container
                from src.application.services.settings_service import SettingsService
                container = get_container()
                if container:
                    settings_service = container.get(SettingsService)
                    settings_service.set('ai.enable_streaming', state == 2)
                    logger.info(f"流式输出设置已更新: {state == 2}")
                else:
                    logger.warning("全局容器未初始化，无法保存设置")
        except Exception as e:
            logger.error(f"更新流式输出设置失败: {e}")

    def _on_smart_continue(self):
        """智能续写"""
        self.show_status("正在智能续写...", "info")
        self.execute_ai_request("smart_continue", "智能续写内容", {"type": "continue"})

    def _on_character_analysis(self):
        """角色分析"""
        self.show_status("正在分析角色...", "info")
        self.execute_ai_request("character_analysis", "分析角色特征", {"type": "character_analysis"})

    def _display_ai_response(self, content: str):
        """显示AI响应（重写父类方法）"""
        # 调用父类方法
        super()._display_ai_response(content)

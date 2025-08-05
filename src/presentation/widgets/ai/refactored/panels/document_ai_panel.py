#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档AI面板

提供文档相关的AI功能面板
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

from .intelligent_ai_panel import IntelligentAIPanel
from ..components.modern_ai_widget import ModernAIWidget

logger = logging.getLogger(__name__)


class DocumentAIPanel(ModernAIWidget):
    """
    现代化文档AI面板

    提供文档相关的AI功能，专注于小说写作辅助
    """

    def __init__(self, parent=None, settings_service=None):
        """
        初始化文档AI面板

        Args:
            parent: 父组件
            settings_service: 设置服务
        """
        super().__init__(parent, settings_service)
        self._document_id = None
        self._document_type = None
        self._setup_document_ui()

        # 初始化智能化功能（保持兼容性）
        try:
            self._setup_intelligent_features()
        except Exception as e:
            logger.warning(f"智能化功能初始化失败: {e}")
        
    def _setup_document_ui(self):
        """设置现代化文档UI"""
        # 创建文档信息区域
        self._create_document_info_section()

        # 创建小说写作助手组
        self._create_writing_assistant_group()

        # 创建创作灵感组
        self._create_inspiration_group()

        # 创建文本优化组
        self._create_optimization_group()

        # 创建输出区域
        self._create_document_output_section()

        # 添加弹性空间
        self.add_stretch()

        logger.info("现代化文档AI面板UI设置完成")

    def _create_document_info_section(self):
        """创建文档信息区域"""
        group = self.create_modern_group("文档信息", "📄")
        layout = QVBoxLayout(group)

        # 创建状态指示器
        self.status_indicator = self.create_status_indicator("文档AI就绪", "info")
        layout.addWidget(self.status_indicator)

        # 文档信息标签
        self.doc_id_label = QLabel("文档: 未设置")
        self.doc_id_label.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.doc_id_label)

        self.doc_type_label = QLabel("类型: 未知")
        self.doc_type_label.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(self.doc_type_label)

        self.add_to_layout(group)

    def _create_writing_assistant_group(self):
        """创建小说写作助手组"""
        group = self.create_modern_group("小说写作助手", "✍️")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 第一行：续写和扩展
        row1_buttons = [
            self.create_modern_button(
                "智能续写", "📝", "writing",
                "基于当前内容智能续写下一段",
                self._on_smart_continue
            ),
            self.create_modern_button(
                "内容扩展", "📖", "writing",
                "扩展选中段落，增加细节描述",
                self._on_content_expand
            )
        ]
        layout.addLayout(self.create_button_row(row1_buttons))

        # 第二行：对话和场景
        row2_buttons = [
            self.create_modern_button(
                "对话生成", "💬", "writing",
                "为角色生成符合性格的对话",
                self._on_dialogue_generation
            ),
            self.create_modern_button(
                "场景描写", "🎭", "writing",
                "生成生动的场景和环境描写",
                self._on_scene_description
            )
        ]
        layout.addLayout(self.create_button_row(row2_buttons))

        self.add_to_layout(group)

    def _create_inspiration_group(self):
        """创建创作灵感组"""
        group = self.create_modern_group("创作灵感", "💡")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 第一行：情节和转折
        row1_buttons = [
            self.create_modern_button(
                "情节建议", "🎬", "inspiration",
                "根据当前剧情提供发展建议",
                self._on_plot_suggestion
            ),
            self.create_modern_button(
                "剧情转折", "🌪️", "inspiration",
                "为故事添加意想不到的转折",
                self._on_plot_twist
            )
        ]
        layout.addLayout(self.create_button_row(row1_buttons))

        # 第二行：角色和冲突
        row2_buttons = [
            self.create_modern_button(
                "角色发展", "👥", "inspiration",
                "分析角色性格，建议发展方向",
                self._on_character_development
            ),
            self.create_modern_button(
                "冲突设计", "⚔️", "inspiration",
                "设计角色间的冲突和矛盾",
                self._on_conflict_design
            )
        ]
        layout.addLayout(self.create_button_row(row2_buttons))

        self.add_to_layout(group)

    def _create_optimization_group(self):
        """创建文本优化组"""
        group = self.create_modern_group("文本优化", "🎨")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # 第一行：润色和风格
        row1_buttons = [
            self.create_modern_button(
                "语言润色", "✨", "optimization",
                "优化文字表达，提升文学性",
                self._on_language_polish
            ),
            self.create_modern_button(
                "风格调整", "🎨", "optimization",
                "调整文本风格和语调",
                self._on_style_adjustment
            )
        ]
        layout.addLayout(self.create_button_row(row1_buttons))

        # 第二行：结构和逻辑
        row2_buttons = [
            self.create_modern_button(
                "结构优化", "🏗️", "optimization",
                "优化段落结构和逻辑",
                self._on_structure_optimization
            ),
            self.create_modern_button(
                "逻辑检查", "🔍", "optimization",
                "检查情节逻辑和前后一致性",
                self._on_logic_check
            )
        ]
        layout.addLayout(self.create_button_row(row2_buttons))

        self.add_to_layout(group)

    def _create_document_output_section(self):
        """创建文档输出区域"""
        group = self.create_modern_group("AI建议", "💭")
        layout = QVBoxLayout(group)

        # 创建输出文本区域
        self.output_area = self.create_output_area("AI的写作建议将显示在这里...")
        layout.addWidget(self.output_area)

        self.add_to_layout(group)

    def set_document_info(self, document_id: str, document_type: str = "chapter"):
        """
        设置文档信息
        
        Args:
            document_id: 文档ID
            document_type: 文档类型
        """
        self._document_id = document_id
        self._document_type = document_type
        
        # 更新显示
        self.doc_id_label.setText(f"文档ID: {document_id}")
        self.doc_type_label.setText(f"文档类型: {document_type}")
        
        logger.info(f"文档AI面板已设置文档信息: {document_id} ({document_type})")
        
    def get_document_id(self) -> Optional[str]:
        """获取文档ID"""
        return self._document_id
        
    def get_document_type(self) -> Optional[str]:
        """获取文档类型"""
        return self._document_type

    def _setup_novel_writing_features(self, layout):
        """设置小说写作专业功能"""
        # 小说写作工具组
        writing_group = QGroupBox("✍️ 小说写作助手")
        writing_layout = QVBoxLayout(writing_group)

        # 创建功能按钮
        self._create_writing_buttons(writing_layout)

        # 添加到布局
        layout.addWidget(writing_group)

        # 创作灵感组
        inspiration_group = QGroupBox("💡 创作灵感")
        inspiration_layout = QVBoxLayout(inspiration_group)

        # 创建灵感按钮
        self._create_inspiration_buttons(inspiration_layout)

        # 添加到布局
        layout.addWidget(inspiration_group)

        # 文本优化组
        optimization_group = QGroupBox("🎨 文本优化")
        optimization_layout = QVBoxLayout(optimization_group)

        # 创建优化按钮
        self._create_optimization_buttons(optimization_layout)

        # 添加到布局
        layout.addWidget(optimization_group)

    def _create_writing_buttons(self, layout):
        """创建写作功能按钮"""
        # 第一行：续写和扩展
        row1_layout = QHBoxLayout()

        continue_btn = QPushButton("📝 智能续写")
        continue_btn.setToolTip("基于当前内容智能续写下一段")
        continue_btn.clicked.connect(self._on_continue_writing)
        row1_layout.addWidget(continue_btn)

        expand_btn = QPushButton("📖 内容扩展")
        expand_btn.setToolTip("扩展选中段落，增加细节描述")
        expand_btn.clicked.connect(self._on_expand_content)
        row1_layout.addWidget(expand_btn)

        layout.addLayout(row1_layout)

        # 第二行：对话和描写
        row2_layout = QHBoxLayout()

        dialogue_btn = QPushButton("💬 对话生成")
        dialogue_btn.setToolTip("为角色生成符合性格的对话")
        dialogue_btn.clicked.connect(self._on_generate_dialogue)
        row2_layout.addWidget(dialogue_btn)

        description_btn = QPushButton("🎭 场景描写")
        description_btn.setToolTip("生成生动的场景和环境描写")
        description_btn.clicked.connect(self._on_generate_description)
        row2_layout.addWidget(description_btn)

        layout.addLayout(row2_layout)

    def _create_inspiration_buttons(self, layout):
        """创建灵感功能按钮"""
        # 第一行：情节和转折
        row1_layout = QHBoxLayout()

        plot_btn = QPushButton("🎬 情节建议")
        plot_btn.setToolTip("根据当前剧情提供发展建议")
        plot_btn.clicked.connect(self._on_suggest_plot)
        row1_layout.addWidget(plot_btn)

        twist_btn = QPushButton("🌪️ 剧情转折")
        twist_btn.setToolTip("为故事添加意想不到的转折")
        twist_btn.clicked.connect(self._on_suggest_twist)
        row1_layout.addWidget(twist_btn)

        layout.addLayout(row1_layout)

        # 第二行：角色和冲突
        row2_layout = QHBoxLayout()

        character_btn = QPushButton("👥 角色发展")
        character_btn.setToolTip("分析角色性格，建议发展方向")
        character_btn.clicked.connect(self._on_develop_character)
        row2_layout.addWidget(character_btn)

        conflict_btn = QPushButton("⚔️ 冲突设计")
        conflict_btn.setToolTip("设计角色间的冲突和矛盾")
        conflict_btn.clicked.connect(self._on_design_conflict)
        row2_layout.addWidget(conflict_btn)

        layout.addLayout(row2_layout)

    def _create_optimization_buttons(self, layout):
        """创建优化功能按钮"""
        # 第一行：语言和风格
        row1_layout = QHBoxLayout()

        polish_btn = QPushButton("✨ 语言润色")
        polish_btn.setToolTip("优化文字表达，提升文学性")
        polish_btn.clicked.connect(self._on_polish_language)
        row1_layout.addWidget(polish_btn)

        style_btn = QPushButton("🎨 风格调整")
        style_btn.setToolTip("调整文本风格和语调")
        style_btn.clicked.connect(self._on_adjust_style)
        row1_layout.addWidget(style_btn)

        layout.addLayout(row1_layout)

        # 第二行：结构和逻辑
        row2_layout = QHBoxLayout()

        structure_btn = QPushButton("🏗️ 结构优化")
        structure_btn.setToolTip("优化段落结构和逻辑")
        structure_btn.clicked.connect(self._on_optimize_structure)
        row2_layout.addWidget(structure_btn)

        consistency_btn = QPushButton("🔍 逻辑检查")
        consistency_btn.setToolTip("检查情节逻辑和前后一致性")
        consistency_btn.clicked.connect(self._on_check_consistency)
        row2_layout.addWidget(consistency_btn)

        layout.addLayout(row2_layout)

    # === 写作功能处理函数 ===
    def _on_continue_writing(self):
        """智能续写"""
        if not self.document_context:
            self.show_status("请先打开文档", "warning")
            return

        # 获取最后500字作为上下文
        context = self.document_context[-500:] if len(self.document_context) > 500 else self.document_context

        prompt = f"""请基于以下小说内容，自然地续写下一段：

当前内容：
{context}

要求：
1. 保持文风一致
2. 情节发展自然
3. 字数控制在200-300字
4. 注意人物性格的连贯性"""

        self.show_status("正在智能续写...", "info")
        self._execute_ai_request("智能续写", prompt)

    def _on_expand_content(self):
        """内容扩展"""
        if not self.selected_text:
            self.show_status("请先选择要扩展的文本", "warning")
            return

        prompt = f"""请扩展以下文本内容，增加细节描述和情感表达：

原文：
{self.selected_text}

要求：
1. 保持原意不变
2. 增加生动的细节描述
3. 丰富情感表达
4. 扩展后字数增加50%-100%"""

        self.show_status("正在扩展内容...", "info")
        self._execute_ai_request("内容扩展", prompt)

    def _on_generate_dialogue(self):
        """对话生成"""
        context = self.selected_text or self.document_context[-300:]
        if not context:
            self.show_status("请提供上下文或选择相关文本", "warning")
            return

        prompt = f"""基于以下情境，为角色生成符合性格的对话：

情境：
{context}

要求：
1. 对话要符合角色性格
2. 推进情节发展
3. 语言自然流畅
4. 包含适当的动作和心理描写"""

        self.show_status("正在生成对话...", "info")
        self._execute_ai_request("对话生成", prompt)

    def _on_generate_description(self):
        """场景描写"""
        context = self.selected_text or self.document_context[-200:]
        if not context:
            self.show_status("请提供场景信息", "warning")
            return

        prompt = f"""基于以下内容，生成生动的场景描写：

场景信息：
{context}

要求：
1. 运用五感描写
2. 营造氛围感
3. 突出环境特色
4. 与情节氛围相符"""

        self.show_status("正在生成场景描写...", "info")
        self._execute_ai_request("场景描写", prompt)

    # === 灵感功能处理函数 ===
    def _on_suggest_plot(self):
        """情节建议"""
        context = self.document_context[-800:] if len(self.document_context) > 800 else self.document_context
        if not context:
            self.show_status("请先打开文档", "warning")
            return

        prompt = f"""基于当前小说内容，提供3个情节发展建议：

当前内容：
{context}

请分析：
1. 当前情节发展状态
2. 可能的发展方向
3. 每个建议的优缺点
4. 推荐的最佳选择"""

        self.show_status("正在分析情节...", "info")
        self._execute_ai_request("情节建议", prompt)

    def _on_suggest_twist(self):
        """剧情转折"""
        context = self.document_context[-600:] if len(self.document_context) > 600 else self.document_context
        if not context:
            self.show_status("请先打开文档", "warning")
            return

        prompt = f"""为以下小说内容设计意想不到的剧情转折：

当前内容：
{context}

要求：
1. 转折要合理且出人意料
2. 符合前文铺垫
3. 能推动情节发展
4. 提供2-3个不同的转折方案"""

        self.show_status("正在设计剧情转折...", "info")
        self._execute_ai_request("剧情转折", prompt)

    def _on_develop_character(self):
        """角色发展"""
        context = self.document_context[-500:] if len(self.document_context) > 500 else self.document_context
        if not context:
            self.show_status("请先打开文档", "warning")
            return

        prompt = f"""分析以下内容中的角色，并提供发展建议：

内容：
{context}

请分析：
1. 主要角色的性格特点
2. 角色关系和互动
3. 角色成长空间
4. 发展建议和方向"""

        self.show_status("正在分析角色...", "info")
        self._execute_ai_request("角色发展", prompt)

    def _on_design_conflict(self):
        """冲突设计"""
        context = self.document_context[-400:] if len(self.document_context) > 400 else self.document_context
        if not context:
            self.show_status("请先打开文档", "warning")
            return

        prompt = f"""基于以下内容，设计角色间的冲突：

内容：
{context}

要求：
1. 冲突要有合理动机
2. 符合角色性格
3. 能推动情节发展
4. 提供解决方案的可能性"""

        self.show_status("正在设计冲突...", "info")
        self._execute_ai_request("冲突设计", prompt)

    # === 优化功能处理函数 ===
    def _on_polish_language(self):
        """语言润色"""
        if not self.selected_text:
            self.show_status("请先选择要润色的文本", "warning")
            return

        prompt = f"""请润色以下文本，提升文学性和表达力：

原文：
{self.selected_text}

要求：
1. 保持原意不变
2. 优化词汇选择
3. 改善句式结构
4. 增强文学美感"""

        self.show_status("正在润色语言...", "info")
        self._execute_ai_request("语言润色", prompt)

    def _on_adjust_style(self):
        """风格调整"""
        if not self.selected_text:
            self.show_status("请先选择要调整的文本", "warning")
            return

        prompt = f"""请调整以下文本的风格，使其更适合小说表达：

原文：
{self.selected_text}

请提供以下风格版本：
1. 古典文学风格
2. 现代都市风格
3. 悬疑紧张风格
4. 温馨治愈风格"""

        self.show_status("正在调整风格...", "info")
        self._execute_ai_request("风格调整", prompt)

    def _on_optimize_structure(self):
        """结构优化"""
        text = self.selected_text or self.document_context[-1000:]
        if not text:
            self.show_status("请提供要优化的文本", "warning")
            return

        prompt = f"""请优化以下文本的结构和逻辑：

原文：
{text}

要求：
1. 优化段落划分
2. 改善逻辑顺序
3. 增强连贯性
4. 突出重点内容"""

        self.show_status("正在优化结构...", "info")
        self._execute_ai_request("结构优化", prompt)

    def _on_check_consistency(self):
        """逻辑检查"""
        context = self.document_context[-1500:] if len(self.document_context) > 1500 else self.document_context
        if not context:
            self.show_status("请先打开文档", "warning")
            return

        prompt = f"""请检查以下内容的逻辑一致性：

内容：
{context}

检查项目：
1. 情节逻辑是否合理
2. 角色行为是否一致
3. 时间线是否清晰
4. 前后文是否矛盾
5. 提供修改建议"""

        self.show_status("正在检查逻辑...", "info")
        self._execute_ai_request("逻辑检查", prompt)

    # 新增的现代化回调方法
    def _on_smart_continue(self):
        """智能续写"""
        self.show_status("正在智能续写...", "info")
        self.execute_ai_request("smart_continue", "智能续写内容", {"type": "continue"})

    def _on_content_expand(self):
        """内容扩展"""
        self.show_status("正在扩展内容...", "info")
        self.execute_ai_request("content_expand", "扩展选中内容", {"type": "expand"})

    def _on_dialogue_generation(self):
        """对话生成"""
        self.show_status("正在生成对话...", "info")
        self.execute_ai_request("dialogue_generation", "生成角色对话", {"type": "dialogue"})

    def _on_scene_description(self):
        """场景描写"""
        self.show_status("正在描写场景...", "info")
        self.execute_ai_request("scene_description", "生成场景描写", {"type": "scene"})

    def _on_plot_suggestion(self):
        """情节建议"""
        self.show_status("正在分析情节...", "info")
        self.execute_ai_request("plot_suggestion", "提供情节建议", {"type": "plot_suggestion"})

    def _on_plot_twist(self):
        """剧情转折"""
        self.show_status("正在设计转折...", "info")
        self.execute_ai_request("plot_twist", "设计剧情转折", {"type": "plot_twist"})

    def _on_character_development(self):
        """角色发展"""
        self.show_status("正在分析角色...", "info")
        self.execute_ai_request("character_development", "分析角色发展", {"type": "character_dev"})

    def _on_conflict_design(self):
        """冲突设计"""
        self.show_status("正在设计冲突...", "info")
        self.execute_ai_request("conflict_design", "设计角色冲突", {"type": "conflict"})

    def _on_language_polish(self):
        """语言润色"""
        self.show_status("正在润色语言...", "info")
        self.execute_ai_request("language_polish", "润色文字表达", {"type": "polish"})

    def _on_style_adjustment(self):
        """风格调整"""
        self.show_status("正在调整风格...", "info")
        self.execute_ai_request("style_adjustment", "调整文本风格", {"type": "style"})

    def _on_structure_optimization(self):
        """结构优化"""
        self.show_status("正在优化结构...", "info")
        self.execute_ai_request("structure_optimization", "优化段落结构", {"type": "structure"})

    def _on_logic_check(self):
        """逻辑检查"""
        self.show_status("正在检查逻辑...", "info")
        self.execute_ai_request("logic_check", "检查情节逻辑", {"type": "logic"})

    def _setup_intelligent_features(self):
        """设置智能化功能（保持兼容性）"""
        try:
            # 尝试初始化智能化功能
            pass
        except Exception as e:
            logger.warning(f"智能化功能初始化失败: {e}")

    def _execute_ai_request(self, function_name: str, prompt: str):
        """执行AI请求（兼容旧版本方法）"""
        # 调用新版本的execute_ai_request方法
        self.execute_ai_request(function_name, prompt, {"type": function_name})

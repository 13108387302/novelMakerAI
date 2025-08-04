#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容工具组件

提供各种AI内容处理工具，如续写、改写、扩展、总结等
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QFrame, QScrollArea, QGridLayout, QSplitter,
    QComboBox, QSpinBox, QSlider, QCheckBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

try:
    from src.presentation.widgets.ai_workers import AITaskWorker, AITaskConfig, AITaskType
except ImportError:
    try:
        from .ai_workers import AITaskWorker, AITaskConfig, AITaskType
    except ImportError:
        # 创建占位符类（完善版本）
        from enum import Enum
        from typing import Optional, Any, Dict
        from PyQt6.QtCore import QObject, pyqtSignal

        class AITaskType(Enum):
            """AI任务类型枚举"""
            IMPROVE_TEXT = "improve_text"
            EXPAND_CONTENT = "expand_content"
            SUMMARIZE = "summarize"
            GENERATE_CHARACTER = "generate_character"
            GENERATE_SCENE = "generate_scene"
            GENERATE_PLOT = "generate_plot"

        class AITaskConfig:
            """AI任务配置类"""
            def __init__(self, task_type: AITaskType, prompt: str, **kwargs: Any) -> None:
                self.task_type = task_type
                self.prompt = prompt
                self.context = kwargs.get('context', '')
                self.max_length = kwargs.get('max_length', 1000)
                self.temperature = kwargs.get('temperature', 0.7)
                self.__dict__.update(kwargs)

        class AITaskWorker(QObject):
            """AI任务工作器占位符类"""

            # 信号定义
            task_completed = pyqtSignal(str)
            task_failed = pyqtSignal(str)
            task_progress = pyqtSignal(str)

            def __init__(self, ai_service: Optional[Any] = None) -> None:
                super().__init__()
                self.ai_service = ai_service

            def start_task(self, config: AITaskConfig) -> None:
                """启动AI任务（占位符实现）"""
                self.task_progress.emit("AI服务不可用，使用占位符响应")
                # 模拟任务完成
                placeholder_response = f"[占位符响应] 任务类型: {config.task_type.value}\n提示词: {config.prompt[:100]}..."
                self.task_completed.emit(placeholder_response)
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ContentToolsWidget(QWidget):
    """内容工具组件"""
    
    # 信号定义
    text_applied = pyqtSignal(str)  # 文本应用到编辑器
    status_updated = pyqtSignal(str)  # 状态更新
    
    def __init__(self, ai_service, parent=None):
        super().__init__(parent)
        self.ai_service = ai_service
        self.current_worker: Optional[AITaskWorker] = None
        
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("🛠️ AI内容工具箱")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 创建工具标签页
        self.tools_tab = QTabWidget()
        
        # 文本处理工具
        self.text_tools_tab = self._create_text_tools_tab()
        self.tools_tab.addTab(self.text_tools_tab, "📝 文本处理")
        
        # 创作生成工具
        self.generation_tools_tab = self._create_generation_tools_tab()
        self.tools_tab.addTab(self.generation_tools_tab, "✨ 创作生成")
        
        # 风格转换工具
        self.style_tools_tab = self._create_style_tools_tab()
        self.tools_tab.addTab(self.style_tools_tab, "🎨 风格转换")
        
        layout.addWidget(self.tools_tab)
        
        # 输入输出区域
        self._create_io_area(layout)
        
    def _create_text_tools_tab(self) -> QWidget:
        """创建文本处理工具标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具按钮网格
        tools_frame = QFrame()
        tools_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tools_layout = QGridLayout(tools_frame)
        
        # 定义文本处理工具
        text_tools = [
            ("continue_writing", "✍️ 续写内容", "基于现有内容智能续写"),
            ("rewrite_content", "🔄 改写优化", "改写和优化文本表达"),
            ("expand_content", "📈 扩展内容", "扩展和丰富文本内容"),
            ("summarize_content", "📋 内容总结", "提取关键信息并总结"),
            ("improve_dialogue", "💬 优化对话", "改进对话的自然度和表现力"),
            ("check_grammar", "✅ 语法检查", "检查并修正语法错误")
        ]
        
        # 创建工具按钮
        for i, (tool_id, title, description) in enumerate(text_tools):
            btn = QPushButton(title)
            btn.setToolTip(description)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, tid=tool_id: self._execute_text_tool(tid))
            
            row = i // 2
            col = i % 2
            tools_layout.addWidget(btn, row, col)
            
        layout.addWidget(tools_frame)
        
        return widget
        
    def _create_generation_tools_tab(self) -> QWidget:
        """创建创作生成工具标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具按钮网格
        tools_frame = QFrame()
        tools_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tools_layout = QGridLayout(tools_frame)
        
        # 定义创作生成工具
        generation_tools = [
            ("generate_character", "👤 生成角色", "创建新的角色设定"),
            ("generate_scene", "🏞️ 生成场景", "创建场景描述"),
            ("generate_plot_point", "📖 生成情节点", "创建新的情节发展点"),
            ("generate_dialogue", "💭 生成对话", "创建角色间的对话"),
            ("get_inspiration", "💡 获取灵感", "获取创作灵感和想法"),
            ("generate_outline", "📋 生成大纲", "创建故事大纲")
        ]
        
        # 创建工具按钮
        for i, (tool_id, title, description) in enumerate(generation_tools):
            btn = QPushButton(title)
            btn.setToolTip(description)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, tid=tool_id: self._execute_generation_tool(tid))
            
            row = i // 2
            col = i % 2
            tools_layout.addWidget(btn, row, col)
            
        layout.addWidget(tools_frame)
        
        return widget
        
    def _create_style_tools_tab(self) -> QWidget:
        """创建风格转换工具标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 风格选择
        style_frame = QFrame()
        style_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        style_layout = QVBoxLayout(style_frame)
        
        style_layout.addWidget(QLabel("选择目标风格:"))
        
        self.style_combo = QComboBox()
        styles = [
            ("formal", "正式文学风格"),
            ("casual", "轻松随意风格"),
            ("poetic", "诗意优美风格"),
            ("dramatic", "戏剧化风格"),
            ("humorous", "幽默风趣风格"),
            ("suspense", "悬疑紧张风格"),
            ("romantic", "浪漫温馨风格"),
            ("action", "动作冒险风格")
        ]
        
        for value, text in styles:
            self.style_combo.addItem(text, value)
            
        style_layout.addWidget(self.style_combo)
        
        # 转换按钮
        convert_btn = QPushButton("🎨 转换风格")
        convert_btn.setMinimumHeight(50)
        convert_btn.clicked.connect(self._convert_style)
        style_layout.addWidget(convert_btn)
        
        layout.addWidget(style_frame)
        
        return widget
        
    def _create_io_area(self, layout):
        """创建输入输出区域"""
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 输入区域
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        input_layout.addWidget(QLabel("📝 输入内容:"))
        self.tool_input = QTextEdit()
        self.tool_input.setPlaceholderText("在这里输入需要处理的内容...")
        self.tool_input.setMinimumHeight(200)
        input_layout.addWidget(self.tool_input)
        
        # 参数设置
        params_frame = QFrame()
        params_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        params_layout = QVBoxLayout(params_frame)
        
        # 创意度设置
        creativity_layout = QHBoxLayout()
        creativity_layout.addWidget(QLabel("创意度:"))
        
        self.creativity_slider = QSlider(Qt.Orientation.Horizontal)
        self.creativity_slider.setRange(0, 100)
        self.creativity_slider.setValue(70)
        creativity_layout.addWidget(self.creativity_slider)
        
        self.creativity_label = QLabel("0.7")
        creativity_layout.addWidget(self.creativity_label)
        
        params_layout.addLayout(creativity_layout)
        
        # 输出长度设置
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("输出长度:"))
        
        self.length_spin = QSpinBox()
        self.length_spin.setRange(100, 3000)
        self.length_spin.setValue(500)
        self.length_spin.setSuffix(" 字")
        length_layout.addWidget(self.length_spin)
        
        params_layout.addLayout(length_layout)
        
        input_layout.addWidget(params_frame)
        
        splitter.addWidget(input_widget)
        
        # 输出区域
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        output_layout.addWidget(QLabel("📄 处理结果:"))
        self.tool_output = QTextEdit()
        self.tool_output.setReadOnly(True)
        self.tool_output.setPlaceholderText("处理结果将显示在这里...")
        output_layout.addWidget(self.tool_output)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.copy_result_btn = QPushButton("📋 复制结果")
        self.apply_result_btn = QPushButton("✅ 应用到编辑器")
        self.clear_results_btn = QPushButton("🗑️ 清空")
        
        action_layout.addWidget(self.copy_result_btn)
        action_layout.addWidget(self.apply_result_btn)
        action_layout.addWidget(self.clear_results_btn)
        action_layout.addStretch()
        
        output_layout.addLayout(action_layout)
        
        splitter.addWidget(output_widget)
        splitter.setSizes([1, 1])
        
        layout.addWidget(splitter)
        
    def _setup_connections(self):
        """设置信号连接"""
        # 参数控制
        self.creativity_slider.valueChanged.connect(self._update_creativity_label)
        
        # 操作按钮
        self.copy_result_btn.clicked.connect(self._copy_result)
        self.apply_result_btn.clicked.connect(self._apply_result)
        self.clear_results_btn.clicked.connect(self._clear_results)
        
    def _update_creativity_label(self, value: int):
        """更新创意度标签"""
        creativity = value / 100.0
        self.creativity_label.setText(f"{creativity:.1f}")
        
    def _execute_text_tool(self, tool_id: str):
        """执行文本处理工具"""
        input_text = self.tool_input.toPlainText().strip()
        if not input_text:
            self.status_updated.emit("请先输入要处理的内容")
            return
            
        # 根据工具类型创建提示词
        prompts = {
            "continue_writing": f"""
请基于以下内容进行自然的续写：

{input_text}

续写要求：
1. 保持原有的写作风格和语调
2. 确保情节连贯性
3. 推进故事发展
4. 语言流畅自然

请续写约{self.length_spin.value()}字的内容。
""",
            "rewrite_content": f"""
请对以下文本进行改写和优化：

{input_text}

优化要求：
1. 提升语言表达的准确性和生动性
2. 增强文本的可读性和流畅性
3. 保持原意不变
4. 优化句式结构
5. 增强感染力
""",
            "expand_content": f"""
请对以下内容进行扩展和丰富：

{input_text}

扩展要求：
1. 增加细节描述
2. 丰富情感表达
3. 完善场景设定
4. 保持风格一致
5. 目标长度约{self.length_spin.value()}字
""",
            "summarize_content": f"""
请对以下内容进行总结：

{input_text}

总结要求：
1. 提取关键信息
2. 保持逻辑清晰
3. 语言简洁明了
4. 突出重点内容
""",
            "improve_dialogue": f"""
请优化以下对话内容：

{input_text}

优化要求：
1. 增强对话的自然度
2. 突出角色个性
3. 改进语言表达
4. 增强戏剧效果
""",
            "check_grammar": f"""
请检查并修正以下文本的语法错误：

{input_text}

检查要求：
1. 修正语法错误
2. 改进句式结构
3. 统一标点符号
4. 保持原意不变
"""
        }
        
        prompt = prompts.get(tool_id, f"请处理以下内容：\n\n{input_text}")
        self._execute_ai_task(prompt, f"正在{self._get_tool_name(tool_id)}...")
        
    def _execute_generation_tool(self, tool_id: str):
        """执行创作生成工具"""
        context = self.tool_input.toPlainText().strip()
        
        # 根据工具类型创建提示词
        prompts = {
            "generate_character": f"""
请创建一个新的角色设定。

{f"参考背景：{context}" if context else ""}

角色设定应包括：
1. 基本信息（姓名、年龄、外貌）
2. 性格特点
3. 背景故事
4. 能力特长
5. 人际关系
6. 角色动机

请创建一个丰富立体的角色。
""",
            "generate_scene": f"""
请创建一个场景描述。

{f"场景要求：{context}" if context else ""}

场景描述应包括：
1. 环境设定
2. 氛围营造
3. 感官细节
4. 情绪渲染
5. 象征意义

请创建一个生动的场景。
""",
            "generate_plot_point": f"""
请创建一个新的情节发展点。

{f"故事背景：{context}" if context else ""}

情节点应包括：
1. 事件描述
2. 角色反应
3. 冲突设置
4. 转折意义
5. 后续影响

请创建一个引人入胜的情节点。
""",
            "generate_dialogue": f"""
请创建角色间的对话。

{f"对话背景：{context}" if context else ""}

对话要求：
1. 符合角色性格
2. 推进情节发展
3. 自然流畅
4. 富有张力
5. 体现关系

请创建精彩的对话。
""",
            "get_inspiration": f"""
请提供创作灵感和想法。

{f"创作方向：{context}" if context else ""}

灵感内容应包括：
1. 创意概念
2. 情节想法
3. 角色灵感
4. 场景构思
5. 主题思考

请提供富有创意的灵感。
""",
            "generate_outline": f"""
请创建故事大纲。

{f"故事设定：{context}" if context else ""}

大纲应包括：
1. 主要情节线
2. 关键转折点
3. 角色发展弧线
4. 章节结构
5. 冲突设置
6. 高潮和结局

请创建完整的故事大纲。
"""
        }
        
        prompt = prompts.get(tool_id, f"请根据以下要求进行创作：\n\n{context}")
        self._execute_ai_task(prompt, f"正在{self._get_tool_name(tool_id)}...")
        
    def _convert_style(self):
        """转换文本风格"""
        input_text = self.tool_input.toPlainText().strip()
        if not input_text:
            self.status_updated.emit("请先输入要转换的内容")
            return
            
        target_style = self.style_combo.currentText()
        
        prompt = f"""
请将以下文本转换为{target_style}：

{input_text}

转换要求：
1. 保持原意不变
2. 调整语言风格
3. 适应目标风格特点
4. 保持内容完整性
5. 增强风格特色

请提供转换后的版本。
"""
        
        self._execute_ai_task(prompt, f"正在转换为{target_style}...")
        
    def _execute_ai_task(self, prompt: str, status_message: str):
        """执行AI任务"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
            
        # 创建任务配置
        config = AITaskConfig(
            task_type=AITaskType.TEXT_REWRITING,
            title="内容处理",
            description="处理用户输入的内容",
            icon="🛠️",
            max_tokens=self.length_spin.value() + 500,
            temperature=self.creativity_slider.value() / 100.0
        )
        
        self.current_worker = AITaskWorker(prompt, config)
        self.current_worker.chunk_received.connect(self._on_tool_chunk_received)
        self.current_worker.task_completed.connect(self._on_tool_completed)
        self.current_worker.task_failed.connect(self._on_tool_failed)
        self.current_worker.start()
        
        self.tool_output.setText(status_message)
        self.status_updated.emit(status_message)
        
    def _on_tool_chunk_received(self, chunk: str):
        """处理工具流式响应"""
        current_text = self.tool_output.toPlainText()
        if "正在" in current_text and "..." in current_text:
            self.tool_output.setText(chunk)
        else:
            self.tool_output.setText(current_text + chunk)
            
    def _on_tool_completed(self, result: str):
        """工具处理完成"""
        self.tool_output.setText(result)
        self.status_updated.emit("处理完成")
        
    def _on_tool_failed(self, error: str):
        """工具处理失败"""
        self.tool_output.setText(f"处理失败: {error}")
        self.status_updated.emit(f"处理失败: {error}")
        
    def _get_tool_name(self, tool_id: str) -> str:
        """获取工具名称"""
        names = {
            "continue_writing": "续写内容",
            "rewrite_content": "改写优化",
            "expand_content": "扩展内容",
            "summarize_content": "内容总结",
            "improve_dialogue": "优化对话",
            "check_grammar": "语法检查",
            "generate_character": "生成角色",
            "generate_scene": "生成场景",
            "generate_plot_point": "生成情节点",
            "generate_dialogue": "生成对话",
            "get_inspiration": "获取灵感",
            "generate_outline": "生成大纲"
        }
        return names.get(tool_id, "处理内容")
        
    def _copy_result(self):
        """复制结果"""
        text = self.tool_output.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self.status_updated.emit("结果已复制到剪贴板")
            
    def _apply_result(self):
        """应用结果到编辑器"""
        text = self.tool_output.toPlainText()
        if text:
            self.text_applied.emit(text)
            self.status_updated.emit("结果已应用到编辑器")
            
    def _clear_results(self):
        """清空结果"""
        self.tool_input.clear()
        self.tool_output.clear()
        
    def cleanup(self):
        """清理资源"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI功能模块 - 重构版本

定义各种AI功能的抽象和具体实现，支持模块化扩展
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import re
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import pyqtSignal

from src.application.services.ai.core_abstractions import AIRequest, AIRequestType, AIRequestBuilder
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class AIFunctionCategory(Enum):
    """AI功能分类"""
    WRITING = "writing"  # 写作辅助
    ANALYSIS = "analysis"  # 内容分析
    OPTIMIZATION = "optimization"  # 内容优化
    TRANSLATION = "translation"  # 翻译
    CREATIVE = "creative"  # 创意生成
    UTILITY = "utility"  # 实用工具


class AIExecutionMode(Enum):
    """AI功能执行模式"""
    AUTO_CONTEXT = "auto_context"  # 自动基于上下文执行，无需用户输入
    AUTO_SELECTION = "auto_selection"  # 自动基于选中文字执行
    MANUAL_INPUT = "manual_input"  # 需要用户手动输入
    HYBRID = "hybrid"  # 混合模式，可自动也可手动


@dataclass
class AIFunctionMetadata:
    """AI功能元数据"""
    id: str
    name: str
    description: str
    category: AIFunctionCategory
    icon: str
    tooltip: str
    requires_input: bool = True
    requires_context: bool = False
    supports_streaming: bool = True
    estimated_time: int = 5  # 预估处理时间（秒）
    execution_mode: AIExecutionMode = AIExecutionMode.MANUAL_INPUT  # 执行模式
    auto_trigger_conditions: List[str] = None  # 自动触发条件
    min_context_length: int = 0  # 最小上下文长度
    smart_description: str = ""  # 智能化描述


class AIFunctionModule(ABC):
    """AI功能模块基类"""

    def __init__(self, metadata: AIFunctionMetadata):
        self.metadata = metadata
        self._enabled = True

    @abstractmethod
    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        """构建AI请求"""
        pass

    @abstractmethod
    def get_prompt_template(self) -> str:
        """获取提示词模板"""
        pass

    def can_auto_execute(self, context: str = "", selected_text: str = "") -> bool:
        """判断是否可以自动执行"""
        if self.metadata.execution_mode == AIExecutionMode.MANUAL_INPUT:
            return False
        elif self.metadata.execution_mode == AIExecutionMode.AUTO_CONTEXT:
            return len(context) >= self.metadata.min_context_length
        elif self.metadata.execution_mode == AIExecutionMode.AUTO_SELECTION:
            return len(selected_text) > 0
        elif self.metadata.execution_mode == AIExecutionMode.HYBRID:
            return len(context) >= self.metadata.min_context_length or len(selected_text) > 0
        return False

    def build_auto_request(self, context: str = "", selected_text: str = "", parameters: Dict[str, Any] = None) -> Optional[AIRequest]:
        """构建自动执行的AI请求"""
        if not self.can_auto_execute(context, selected_text):
            return None

        # 根据执行模式选择输入文本
        if self.metadata.execution_mode == AIExecutionMode.AUTO_CONTEXT:
            input_text = self._extract_auto_input_from_context(context)
        elif self.metadata.execution_mode == AIExecutionMode.AUTO_SELECTION:
            input_text = selected_text
        elif self.metadata.execution_mode == AIExecutionMode.HYBRID:
            input_text = selected_text if selected_text else self._extract_auto_input_from_context(context)
        else:
            return None

        return self.build_request(input_text, context, parameters)

    def _extract_auto_input_from_context(self, context: str) -> str:
        """从上下文中提取自动输入文本（子类可重写）"""
        return context
    
    def is_enabled(self) -> bool:
        """检查功能是否启用"""
        return self._enabled
    
    def set_enabled(self, enabled: bool):
        """设置功能启用状态"""
        self._enabled = enabled
    
    def validate_input(self, input_text: str, context: str = "") -> tuple[bool, str]:
        """验证输入"""
        if self.metadata.requires_input and not input_text.strip():
            return False, "请输入需要处理的内容"
        
        if self.metadata.requires_context and not context.strip():
            return False, "此功能需要文档上下文"
        
        return True, ""


# 具体功能模块实现

class WritingInspirationModule(AIFunctionModule):
    """写作灵感模块 - 针对小说创作优化"""

    def __init__(self):
        metadata = AIFunctionMetadata(
            id="writing_inspiration",
            name="写作灵感",
            description="基于当前文档内容自动生成写作灵感和创意建议",
            category=AIFunctionCategory.CREATIVE,
            icon="💡",
            tooltip="智能分析文档内容，自动生成写作灵感",
            requires_input=False,  # 不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=10,
            execution_mode=AIExecutionMode.AUTO_CONTEXT,  # 自动基于上下文执行
            min_context_length=50,  # 最少需要50字符的上下文
            smart_description="自动分析当前文档内容，生成针对性的写作灵感和创意建议"
        )
        super().__init__(metadata)

    def get_prompt_template(self) -> str:
        return """你是一位专业的小说创作顾问，请智能分析以下文档内容，自动生成针对性的写作灵感和创意建议。

【文档内容分析】
{context}

【智能分析任务】
请自动分析文档内容，并提供以下方面的专业建议：

1. **内容特征识别**
   - 自动识别文档的类型（章节、大纲、角色设定等）
   - 分析当前的写作风格和语言特点
   - 识别主要角色、场景和情节元素

2. **情节发展灵感**
   - 基于现有内容，提供3-5个情节发展方向
   - 识别潜在的冲突点和戏剧张力
   - 建议情节转折和高潮设计

3. **角色发展建议**
   - 分析现有角色的性格特点和发展潜力
   - 建议角色关系的深化和冲突设计
   - 提供角色成长弧线的创作思路

4. **场景和氛围创意**
   - 基于现有场景，建议氛围营造技巧
   - 提供场景扩展和细节丰富的方向
   - 建议环境描写的创新角度

5. **主题深化方向**
   - 识别文档中的潜在主题元素
   - 建议主题表达的创新方式
   - 提供主题升华的具体路径

6. **下一步创作建议**
   - 基于当前进度，建议下一步的创作重点
   - 提供具体的写作任务和目标
   - 建议创作节奏和结构安排

【输出要求】
- 请根据文档内容的实际情况，提供针对性的建议
- 确保建议具体可操作，符合小说创作的专业标准
- 如果文档内容较少，重点提供起步和发展建议
- 如果文档内容丰富，重点提供深化和优化建议"""
    
    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        # 对于智能化模式，直接使用上下文作为分析对象
        prompt = self.get_prompt_template().format(
            context=context or "无文档内容"
        )

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.GENERATE) \
            .with_parameters(parameters or {}) \
            .build()

    def _extract_auto_input_from_context(self, context: str) -> str:
        """从上下文中提取用于灵感生成的关键信息"""
        # 对于写作灵感，我们使用整个上下文
        return context


class ContinueWritingModule(AIFunctionModule):
    """智能续写模块 - 专业小说续写"""

    def __init__(self):
        metadata = AIFunctionMetadata(
            id="continue_writing",
            name="智能续写",
            description="自动感知文档末尾内容，基于上下文和写作风格智能续写",
            category=AIFunctionCategory.WRITING,
            icon="✍️",
            tooltip="自动分析文档内容，智能续写下一段落",
            requires_input=False,  # 不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=15,
            execution_mode=AIExecutionMode.AUTO_CONTEXT,  # 自动基于上下文执行
            min_context_length=100,  # 最少需要100字符的上下文
            smart_description="自动分析文档末尾内容和整体风格，智能续写下一段落"
        )
        super().__init__(metadata)

    def get_prompt_template(self) -> str:
        return """你是一位专业的小说作家，请智能分析以下文档内容，自动续写下一段落。

【文档内容分析】
{context}

【智能续写任务】
请自动分析文档内容，并进行高质量的续写：

1. **内容分析**
   - 自动识别文档的当前进度和内容特点
   - 分析文档末尾的情节发展状态
   - 识别主要角色、场景和情感基调

2. **风格识别**
   - 自动分析原文的写作风格和语言特色
   - 识别叙述视角和时态特点
   - 分析对话风格和人物语言特点

3. **情节续写**
   - 基于文档末尾内容，自然承接情节发展
   - 保持故事节奏和逻辑的连贯性
   - 推进情节或深化角色刻画

4. **质量要求**
   - 提供300-500字的高质量续写内容
   - 保持与原文完全一致的风格和基调
   - 包含适当的环境描写、心理描写或对话
   - 确保语言生动、情节合理

【续写策略】
- 如果文档末尾是对话，可以继续对话或转入叙述
- 如果文档末尾是叙述，可以推进情节或转入对话
- 如果文档末尾是场景描写，可以加入角色行动或心理活动
- 确保续写内容与前文形成自然的衔接

请直接提供续写内容，无需额外说明或分析。"""
    
    def build_request(
        self, 
        input_text: str, 
        context: str = "", 
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        prompt = self.get_prompt_template().format(
            input_text=input_text, 
            context=context
        )
        
        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.CONTINUE) \
            .with_parameters(parameters or {}) \
            .build()


class TextOptimizationModule(AIFunctionModule):
    """文本优化模块 - 专业小说文本优化"""

    def __init__(self):
        metadata = AIFunctionMetadata(
            id="text_optimization",
            name="文本优化",
            description="智能优化选中文字或输入文本的表达、风格和可读性",
            category=AIFunctionCategory.OPTIMIZATION,
            icon="✨",
            tooltip="自动优化选中文字，或手动输入文字进行优化",
            requires_input=False,  # 可以不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=12,
            execution_mode=AIExecutionMode.HYBRID,  # 混合模式
            min_context_length=10,  # 最少需要10字符
            smart_description="优先优化选中文字，也支持手动输入文字进行优化"
        )
        super().__init__(metadata)

    def get_prompt_template(self) -> str:
        return """你是一位专业的小说编辑，请对以下文本进行深度优化。

【原始文本】
{input_text}

【文档上下文】
{context}

【优化标准】
请按照专业小说编辑的标准进行全面优化：

1. **语言表达优化**
   - 提升语言的准确性和精确性
   - 消除冗余和重复表达
   - 增强语言的节奏感和韵律美

2. **文学技巧提升**
   - 优化修辞手法的运用
   - 增强描写的生动性和感染力
   - 改进叙述的层次感和深度

3. **风格一致性**
   - 保持与整体作品风格的一致性
   - 确保语言风格符合文本类型
   - 维持作者的独特声音

4. **可读性改进**
   - 优化句式结构，避免过长或过短
   - 改善段落组织和逻辑流畅性
   - 增强文本的吸引力和可读性

5. **技术细节**
   - 修正语法、标点和用词错误
   - 统一术语和表达方式
   - 确保时态和人称的一致性

【输出要求】
- 直接提供优化后的文本
- 保持原文的核心意思和情感基调
- 确保优化后的文本更加专业和精彩
- 不要添加解释或说明，只输出优化结果"""
    
    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        prompt = self.get_prompt_template().format(
            input_text=input_text,
            context=context or "无额外上下文信息"
        )

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.IMPROVE) \
            .with_parameters(parameters or {}) \
            .build()


class ContentAnalysisModule(AIFunctionModule):
    """内容分析模块 - 专业小说文本分析"""

    def __init__(self):
        metadata = AIFunctionMetadata(
            id="content_analysis",
            name="内容分析",
            description="智能分析选中文字或整个文档的结构、风格、主题等专业要素",
            category=AIFunctionCategory.ANALYSIS,
            icon="🔍",
            tooltip="自动分析选中文字或整个文档，提供专业分析报告",
            requires_input=False,  # 可以不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=15,
            execution_mode=AIExecutionMode.HYBRID,  # 混合模式
            min_context_length=50,  # 最少需要50字符
            smart_description="优先分析选中文字，也可以分析整个文档内容"
        )
        super().__init__(metadata)

    def get_prompt_template(self) -> str:
        return """你是一位专业的文学评论家和小说编辑，请对以下小说文本进行深度专业分析。

【分析文本】
{input_text}

【文档上下文】
{context}

【分析框架】
请从以下专业维度进行全面分析：

## 1. 叙事结构分析
- **叙述视角**：分析人称使用和视角选择的效果
- **时间结构**：分析时间线的组织和节奏控制
- **情节架构**：分析起承转合的结构完整性
- **章节布局**：评估段落和章节的组织逻辑

## 2. 文学技巧评估
- **描写技巧**：分析场景、人物、心理描写的质量
- **对话艺术**：评估对话的真实性和推进作用
- **修辞运用**：分析比喻、象征等修辞手法的效果
- **语言节奏**：评估句式变化和语言韵律

## 3. 角色塑造分析
- **人物刻画**：分析角色的立体性和真实感
- **性格展现**：评估角色性格的一致性和发展
- **关系动态**：分析人物关系的复杂性和变化
- **对话特色**：评估角色语言的个性化程度

## 4. 主题深度挖掘
- **核心主题**：识别和分析文本的主要主题
- **象征意义**：挖掘隐含的象征和寓意
- **情感基调**：分析整体的情感氛围和基调
- **价值观念**：评估作品传达的价值观和思想

## 5. 风格特色识别
- **语言风格**：分析作者的语言特色和风格倾向
- **文体特征**：识别文本的文体类型和特点
- **创新元素**：发现独特的创作手法和创新点
- **影响因素**：分析可能的文学影响和借鉴

## 6. 专业改进建议
- **结构优化**：提供叙事结构的改进建议
- **技巧提升**：建议文学技巧的改进方向
- **风格完善**：提供风格统一和完善的建议
- **读者体验**：从读者角度提供改进建议

【输出要求】
请提供结构化的专业分析报告，确保分析深入、客观、具有建设性。"""
    
    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        prompt = self.get_prompt_template().format(
            input_text=input_text,
            context=context or "无额外上下文信息"
        )

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.ANALYZE) \
            .with_parameters(parameters or {}) \
            .build()


class ContentSummaryModule(AIFunctionModule):
    """内容总结模块"""
    
    def __init__(self):
        metadata = AIFunctionMetadata(
            id="content_summary",
            name="内容总结",
            description="智能总结选中文字或整个文档的主要内容和要点",
            category=AIFunctionCategory.ANALYSIS,
            icon="📝",
            tooltip="自动总结选中文字或整个文档的核心内容",
            requires_input=False,  # 不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=10,
            execution_mode=AIExecutionMode.HYBRID,  # 混合模式
            min_context_length=100,  # 最少需要100字符
            smart_description="优先总结选中文字，也可以总结整个文档内容"
        )
        super().__init__(metadata)
    
    def get_prompt_template(self) -> str:
        return """你是一位专业的文本分析师，请智能分析并总结以下内容。

【待总结内容】
{context}

【智能总结任务】
请根据内容的特点和类型，提供专业的总结：

1. **内容识别**
   - 自动识别内容类型（小说章节、角色设定、大纲等）
   - 分析内容的主要特征和结构
   - 识别关键信息和核心要素

2. **智能总结策略**
   - 如果是小说章节：总结情节发展、角色动态、场景变化
   - 如果是角色设定：总结角色特征、背景、关系网络
   - 如果是大纲：总结结构框架、主要节点、逻辑关系
   - 如果是其他内容：提取核心观点和关键信息

3. **总结要求**
   - 保持逻辑清晰，层次分明
   - 突出重点内容和关键信息
   - 语言简洁明了，易于理解
   - 长度适中，涵盖主要要点

4. **输出格式**
   - 提供结构化的总结内容
   - 使用适当的标题和分点
   - 确保总结的完整性和准确性

请根据内容的实际情况，提供针对性的专业总结。"""
    
    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        # 对于智能化总结，优先使用选中文字，其次使用整个上下文
        content_to_summarize = input_text if input_text else context
        prompt = self.get_prompt_template().format(context=content_to_summarize)

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.SUMMARIZE) \
            .with_parameters(parameters or {}) \
            .build()

    def _extract_auto_input_from_context(self, context: str) -> str:
        """从上下文中提取用于总结的内容"""
        # 对于总结，我们使用整个上下文
        return context


class TranslationModule(AIFunctionModule):
    """翻译模块"""
    
    def __init__(self):
        metadata = AIFunctionMetadata(
            id="translation",
            name="智能翻译",
            description="智能检测语言并翻译选中文字，支持中英文互译",
            category=AIFunctionCategory.TRANSLATION,
            icon="🌐",
            tooltip="自动检测语言并翻译选中文字",
            requires_input=False,  # 不需要用户输入
            requires_context=False,
            supports_streaming=True,
            estimated_time=8,
            execution_mode=AIExecutionMode.AUTO_SELECTION,  # 自动基于选中文字执行
            min_context_length=0,  # 不需要最小上下文
            smart_description="自动检测选中文字的语言并进行智能翻译"
        )
        super().__init__(metadata)
    
    def get_prompt_template(self) -> str:
        return """你是一位专业的翻译专家，请智能分析并翻译以下文本。

【待翻译文本】
{input_text}

【智能翻译任务】
请按照以下步骤进行智能翻译：

1. **语言检测**
   - 自动识别原文的语言类型
   - 分析文本的语言特征和风格
   - 确定最适合的目标语言

2. **翻译策略**
   - 如果是中文：翻译为自然流畅的英文
   - 如果是英文：翻译为地道准确的中文
   - 如果是其他语言：翻译为中文
   - 保持原文的语言风格和文体特色

3. **翻译要求**
   - 准确传达原文的完整含义
   - 语言表达自然流畅，符合目标语言习惯
   - 保持原文的情感色彩和语言风格
   - 注意文化差异，进行适当的本土化处理
   - 对于专业术语，提供准确的对应翻译

4. **特殊处理**
   - 如果是小说文本：保持文学性和可读性
   - 如果是对话：保持口语化和自然性
   - 如果是描述性文字：保持生动性和画面感
   - 如果是技术性内容：确保术语的准确性

请直接提供翻译结果，无需额外说明。"""
    
    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        # 对于智能翻译，直接使用选中的文字进行翻译
        prompt = self.get_prompt_template().format(input_text=input_text)

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.TRANSLATE) \
            .with_parameters(parameters or {}) \
            .build()

    def _extract_auto_input_from_context(self, context: str) -> str:
        """从上下文中提取用于翻译的内容"""
        # 对于翻译，我们通常只翻译选中的文字
        return context


class AIFunctionRegistry:
    """AI功能注册表"""
    
    def __init__(self):
        self._modules: Dict[str, AIFunctionModule] = {}
        self._categories: Dict[AIFunctionCategory, List[AIFunctionModule]] = {}
        
        # 注册默认功能模块
        self._register_default_modules()
    
    def _register_default_modules(self):
        """注册默认功能模块"""
        default_modules = [
            WritingInspirationModule(),
            ContinueWritingModule(),
            TextOptimizationModule(),
            ContentAnalysisModule(),
            ContentSummaryModule(),
            TranslationModule(),
            DialogueOptimizationModule(),
            SceneExpansionModule()
        ]

        for module in default_modules:
            self.register_module(module)
    
    def register_module(self, module: AIFunctionModule):
        """注册功能模块"""
        self._modules[module.metadata.id] = module
        
        category = module.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(module)
        
        logger.debug(f"注册AI功能模块: {module.metadata.name}")
    
    def get_module(self, module_id: str) -> Optional[AIFunctionModule]:
        """获取功能模块"""
        return self._modules.get(module_id)
    
    def get_modules_by_category(self, category: AIFunctionCategory) -> List[AIFunctionModule]:
        """按分类获取功能模块"""
        return self._categories.get(category, [])
    
    def get_all_modules(self) -> List[AIFunctionModule]:
        """获取所有功能模块"""
        return list(self._modules.values())

    def get_all_functions(self) -> List[AIFunctionModule]:
        """获取所有功能模块（别名方法，为了兼容性）"""
        return self.get_all_modules()

    def get_enabled_modules(self) -> List[AIFunctionModule]:
        """获取启用的功能模块"""
        return [module for module in self._modules.values() if module.is_enabled()]


class DialogueOptimizationModule(AIFunctionModule):
    """对话优化模块 - 专业小说对话优化"""

    def __init__(self):
        metadata = AIFunctionMetadata(
            id="dialogue_optimization",
            name="对话优化",
            description="智能优化选中的对话文字，提升真实感和表现力",
            category=AIFunctionCategory.OPTIMIZATION,
            icon="💬",
            tooltip="自动优化选中的对话内容，提升戏剧效果",
            requires_input=False,  # 不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=10,
            execution_mode=AIExecutionMode.AUTO_SELECTION,  # 自动基于选中文字执行
            min_context_length=0,  # 不需要最小上下文
            smart_description="自动优化选中的对话文字，提升对话的真实感和戏剧效果"
        )
        super().__init__(metadata)

    def get_prompt_template(self) -> str:
        return """你是一位专业的对话写作专家，请优化以下小说对话内容。

【原始对话】
{input_text}

【文档上下文】
{context}

【对话优化标准】
请按照专业小说对话写作标准进行优化：

1. **真实性提升**
   - 确保对话符合角色的年龄、身份、性格
   - 体现角色的教育背景和社会地位
   - 反映角色的情感状态和心理变化

2. **个性化表达**
   - 为每个角色建立独特的说话方式
   - 体现角色的语言习惯和口头禅
   - 区分不同角色的语言风格

3. **戏剧效果**
   - 增强对话的冲突性和张力
   - 通过对话推进情节发展
   - 在对话中埋下伏笔和线索

4. **潜台词运用**
   - 增加对话的层次感和深度
   - 通过言外之意表达复杂情感
   - 运用暗示和隐喻增强表现力

5. **技术细节**
   - 优化对话标签和动作描写
   - 平衡对话与叙述的比例
   - 确保对话节奏的流畅性

【输出要求】
直接提供优化后的对话内容，保持原有的情节框架，但显著提升对话质量。"""

    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        prompt = self.get_prompt_template().format(
            input_text=input_text,
            context=context or "无额外上下文信息"
        )

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.IMPROVE) \
            .with_parameters(parameters or {}) \
            .build()


class SceneExpansionModule(AIFunctionModule):
    """场景扩展模块 - 专业场景描写扩展"""

    def __init__(self):
        metadata = AIFunctionMetadata(
            id="scene_expansion",
            name="场景扩展",
            description="智能扩展选中的场景描写，增强代入感和视觉效果",
            category=AIFunctionCategory.WRITING,
            icon="🎬",
            tooltip="自动扩展选中的场景描写，增强氛围营造",
            requires_input=False,  # 不需要用户输入
            requires_context=True,
            supports_streaming=True,
            estimated_time=12,
            execution_mode=AIExecutionMode.AUTO_SELECTION,  # 自动基于选中文字执行
            min_context_length=0,  # 不需要最小上下文
            smart_description="自动扩展选中的场景描写，增强视觉效果和氛围营造"
        )
        super().__init__(metadata)

    def get_prompt_template(self) -> str:
        return """你是一位专业的场景描写专家，请扩展和丰富以下小说场景。

【原始场景】
{input_text}

【文档上下文】
{context}

【场景扩展标准】
请按照专业小说场景描写标准进行扩展：

1. **视觉层次构建**
   - 从远景到近景的层次描写
   - 突出重要的视觉元素
   - 运用色彩和光影效果

2. **感官体验丰富**
   - 融入听觉、嗅觉、触觉描写
   - 创造立体的感官体验
   - 通过感官细节增强真实感

3. **氛围营造**
   - 根据情节需要营造相应氛围
   - 运用环境烘托人物情感
   - 创造符合故事基调的环境

4. **象征意义融入**
   - 通过环境暗示情节发展
   - 运用象征手法深化主题
   - 让场景服务于故事表达

5. **动态描写**
   - 描写环境中的动态元素
   - 体现时间的流逝和变化
   - 增强场景的生命力

【输出要求】
提供扩展后的场景描写，保持原有框架但显著丰富细节和层次。"""

    def build_request(
        self,
        input_text: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> AIRequest:
        # 对于智能续写，直接使用上下文进行分析和续写
        prompt = self.get_prompt_template().format(
            context=context or "无文档内容"
        )

        return AIRequestBuilder() \
            .with_prompt(prompt) \
            .with_context(context) \
            .with_type(AIRequestType.GENERATE) \
            .with_parameters(parameters or {}) \
            .build()

    def _extract_auto_input_from_context(self, context: str) -> str:
        """从上下文中提取续写的起始点（通常是文档末尾）"""
        # 对于续写，我们使用整个上下文来分析风格和内容
        return context


# 全局功能注册表实例
ai_function_registry = AIFunctionRegistry()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
写作模板服务

提供各种写作模板和模板管理功能
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateCategory(Enum):
    """
    模板分类枚举

    定义不同类型的写作模板分类。

    Values:
        NOVEL: 小说模板
        SHORT_STORY: 短篇小说模板
        ESSAY: 散文模板
        POETRY: 诗歌模板
        SCRIPT: 剧本模板
        CHARACTER: 角色模板
        SCENE: 场景模板
        DIALOGUE: 对话模板
        OUTLINE: 大纲模板
        CUSTOM: 自定义模板
    """
    NOVEL = "novel"
    SHORT_STORY = "short_story"
    ESSAY = "essay"
    POETRY = "poetry"
    SCRIPT = "script"
    CHARACTER = "character"
    SCENE = "scene"
    DIALOGUE = "dialogue"
    OUTLINE = "outline"
    CUSTOM = "custom"


@dataclass
class TemplateVariable:
    """
    模板变量数据类

    定义模板中可替换的变量信息。

    Attributes:
        name: 变量名称
        description: 变量描述
        default_value: 默认值
        required: 是否必填
        variable_type: 变量类型（text/number/date/choice）
    """
    name: str
    description: str
    default_value: str = ""
    required: bool = False
    variable_type: str = "text"  # text, number, date, choice


@dataclass
class WritingTemplate:
    """
    写作模板数据类

    定义完整的写作模板信息，包括内容、变量和元数据。

    Attributes:
        id: 模板唯一标识符
        name: 模板名称
        description: 模板描述
        category: 模板分类
        content: 模板内容
        variables: 模板变量列表
        tags: 模板标签
        author: 模板作者
        created_at: 创建时间
        updated_at: 更新时间
        usage_count: 使用次数
        is_builtin: 是否为内置模板
    """
    id: str
    name: str
    description: str
    category: TemplateCategory
    content: str
    variables: List[TemplateVariable]
    tags: List[str]
    author: str = "系统"
    version: str = "1.0"
    created_at: str = ""
    is_builtin: bool = True


class TemplateService:
    """写作模板服务"""
    
    def __init__(self, templates_dir: Path = None):
        self.templates_dir = templates_dir or Path("templates")
        self.templates_dir.mkdir(exist_ok=True)
        
        self._templates: Dict[str, WritingTemplate] = {}
        self._load_builtin_templates()
        self._load_custom_templates()
        
        logger.debug("写作模板服务初始化完成")
    
    def _load_builtin_templates(self):
        """加载内置模板"""
        try:
            # 小说章节模板
            novel_chapter = WritingTemplate(
                id="novel_chapter",
                name="小说章节模板",
                description="标准的小说章节结构模板",
                category=TemplateCategory.NOVEL,
                content="""# 第{chapter_number}章 {chapter_title}

{scene_setting}

{opening_paragraph}

---

## 主要情节

{main_plot}

---

## 对话部分

{dialogue_section}

---

## 结尾

{ending_paragraph}

---

**字数统计**: 约 {target_words} 字
**关键词**: {keywords}
""",
                variables=[
                    TemplateVariable("chapter_number", "章节号", "1", True, "number"),
                    TemplateVariable("chapter_title", "章节标题", "", True),
                    TemplateVariable("scene_setting", "场景设定", "时间、地点、环境描述"),
                    TemplateVariable("opening_paragraph", "开头段落", "引人入胜的开头"),
                    TemplateVariable("main_plot", "主要情节", "本章的核心情节发展"),
                    TemplateVariable("dialogue_section", "对话部分", "人物对话和互动"),
                    TemplateVariable("ending_paragraph", "结尾段落", "本章结尾，为下章做铺垫"),
                    TemplateVariable("target_words", "目标字数", "3000", False, "number"),
                    TemplateVariable("keywords", "关键词", "用逗号分隔的关键词")
                ],
                tags=["小说", "章节", "结构化"]
            )
            
            # 人物设定模板
            character_template = WritingTemplate(
                id="character_profile",
                name="人物设定模板",
                description="详细的人物角色设定模板",
                category=TemplateCategory.CHARACTER,
                content="""# {character_name} - 人物设定

## 基本信息
- **姓名**: {character_name}
- **年龄**: {age}
- **性别**: {gender}
- **职业**: {occupation}
- **出生地**: {birthplace}

## 外貌特征
{appearance_description}

## 性格特点
### 主要性格
{main_personality}

### 性格优点
{personality_strengths}

### 性格缺点
{personality_weaknesses}

## 背景故事
{background_story}

## 人际关系
{relationships}

## 目标与动机
{goals_and_motivations}

## 成长弧线
{character_arc}

## 经典台词
{signature_quotes}

## 备注
{additional_notes}
""",
                variables=[
                    TemplateVariable("character_name", "角色姓名", "", True),
                    TemplateVariable("age", "年龄", "", True, "number"),
                    TemplateVariable("gender", "性别", "男", False, "choice"),
                    TemplateVariable("occupation", "职业", ""),
                    TemplateVariable("birthplace", "出生地", ""),
                    TemplateVariable("appearance_description", "外貌描述", "详细描述角色的外貌特征"),
                    TemplateVariable("main_personality", "主要性格", "核心性格特征"),
                    TemplateVariable("personality_strengths", "性格优点", "角色的积极特质"),
                    TemplateVariable("personality_weaknesses", "性格缺点", "角色的消极特质或弱点"),
                    TemplateVariable("background_story", "背景故事", "角色的成长经历和重要事件"),
                    TemplateVariable("relationships", "人际关系", "与其他角色的关系"),
                    TemplateVariable("goals_and_motivations", "目标与动机", "角色的追求和驱动力"),
                    TemplateVariable("character_arc", "成长弧线", "角色在故事中的变化和成长"),
                    TemplateVariable("signature_quotes", "经典台词", "角色的标志性话语"),
                    TemplateVariable("additional_notes", "备注", "其他重要信息")
                ],
                tags=["人物", "角色", "设定"]
            )
            
            # 场景描写模板
            scene_template = WritingTemplate(
                id="scene_description",
                name="场景描写模板",
                description="生动的场景描写结构模板",
                category=TemplateCategory.SCENE,
                content="""# {scene_name}

## 基本信息
- **时间**: {time_setting}
- **地点**: {location}
- **天气**: {weather}
- **氛围**: {atmosphere}

## 视觉描写
{visual_description}

## 听觉描写
{auditory_description}

## 嗅觉描写
{olfactory_description}

## 触觉描写
{tactile_description}

## 情感氛围
{emotional_atmosphere}

## 象征意义
{symbolic_meaning}

## 在情节中的作用
{plot_function}
""",
                variables=[
                    TemplateVariable("scene_name", "场景名称", "", True),
                    TemplateVariable("time_setting", "时间设定", "具体时间或时间段"),
                    TemplateVariable("location", "地点", "详细的地理位置"),
                    TemplateVariable("weather", "天气", "天气状况"),
                    TemplateVariable("atmosphere", "氛围", "整体氛围感觉"),
                    TemplateVariable("visual_description", "视觉描写", "看到的景象和细节"),
                    TemplateVariable("auditory_description", "听觉描写", "声音和音效"),
                    TemplateVariable("olfactory_description", "嗅觉描写", "气味和香味"),
                    TemplateVariable("tactile_description", "触觉描写", "触感和质感"),
                    TemplateVariable("emotional_atmosphere", "情感氛围", "场景传达的情感"),
                    TemplateVariable("symbolic_meaning", "象征意义", "场景的深层含义"),
                    TemplateVariable("plot_function", "情节作用", "场景在故事中的功能")
                ],
                tags=["场景", "描写", "环境"]
            )
            
            # 对话模板
            dialogue_template = WritingTemplate(
                id="dialogue_structure",
                name="对话结构模板",
                description="自然流畅的对话写作模板",
                category=TemplateCategory.DIALOGUE,
                content="""# {dialogue_title}

## 对话背景
- **参与者**: {participants}
- **场景**: {scene_context}
- **目的**: {dialogue_purpose}
- **情绪基调**: {emotional_tone}

## 对话内容

### 开场
{opening_lines}

### 主体对话
{main_dialogue}

### 冲突/转折
{conflict_or_turning_point}

### 结尾
{closing_lines}

## 对话技巧说明
- **语言特色**: {language_style}
- **节奏控制**: {pacing_notes}
- **潜台词**: {subtext}
- **动作描写**: {action_descriptions}

## 效果评估
{effectiveness_notes}
""",
                variables=[
                    TemplateVariable("dialogue_title", "对话标题", "", True),
                    TemplateVariable("participants", "参与者", "对话的角色"),
                    TemplateVariable("scene_context", "场景背景", "对话发生的环境"),
                    TemplateVariable("dialogue_purpose", "对话目的", "这段对话要达成什么"),
                    TemplateVariable("emotional_tone", "情绪基调", "对话的整体情感色彩"),
                    TemplateVariable("opening_lines", "开场白", "对话的开始部分"),
                    TemplateVariable("main_dialogue", "主体对话", "对话的核心内容"),
                    TemplateVariable("conflict_or_turning_point", "冲突/转折", "对话中的冲突或转折点"),
                    TemplateVariable("closing_lines", "结尾", "对话的结束部分"),
                    TemplateVariable("language_style", "语言特色", "角色的说话风格"),
                    TemplateVariable("pacing_notes", "节奏控制", "对话的节奏安排"),
                    TemplateVariable("subtext", "潜台词", "对话的隐含意思"),
                    TemplateVariable("action_descriptions", "动作描写", "对话中的动作和表情"),
                    TemplateVariable("effectiveness_notes", "效果评估", "对话的预期效果")
                ],
                tags=["对话", "交流", "人物互动"]
            )
            
            # 故事大纲模板
            outline_template = WritingTemplate(
                id="story_outline",
                name="故事大纲模板",
                description="完整的故事结构大纲模板",
                category=TemplateCategory.OUTLINE,
                content="""# {story_title} - 故事大纲

## 基本信息
- **类型**: {genre}
- **目标字数**: {target_word_count}
- **预计章节**: {estimated_chapters}
- **主题**: {main_theme}

## 故事概要
{story_summary}

## 主要角色
{main_characters}

## 三幕结构

### 第一幕：建立 (25%)
{act_one_setup}

### 第二幕：对抗 (50%)
{act_two_confrontation}

### 第三幕：解决 (25%)
{act_three_resolution}

## 关键情节点
1. **开场钩子**: {opening_hook}
2. **激励事件**: {inciting_incident}
3. **第一个转折点**: {plot_point_one}
4. **中点**: {midpoint}
5. **第二个转折点**: {plot_point_two}
6. **高潮**: {climax}
7. **结局**: {resolution}

## 子情节
{subplots}

## 主题探索
{theme_exploration}

## 写作计划
{writing_schedule}
""",
                variables=[
                    TemplateVariable("story_title", "故事标题", "", True),
                    TemplateVariable("genre", "类型", "小说类型"),
                    TemplateVariable("target_word_count", "目标字数", "80000", False, "number"),
                    TemplateVariable("estimated_chapters", "预计章节", "20", False, "number"),
                    TemplateVariable("main_theme", "主题", "故事的核心主题"),
                    TemplateVariable("story_summary", "故事概要", "一段话概括整个故事"),
                    TemplateVariable("main_characters", "主要角色", "主要角色列表"),
                    TemplateVariable("act_one_setup", "第一幕", "故事建立阶段"),
                    TemplateVariable("act_two_confrontation", "第二幕", "冲突对抗阶段"),
                    TemplateVariable("act_three_resolution", "第三幕", "问题解决阶段"),
                    TemplateVariable("opening_hook", "开场钩子", "吸引读者的开头"),
                    TemplateVariable("inciting_incident", "激励事件", "推动故事的关键事件"),
                    TemplateVariable("plot_point_one", "第一转折点", "第一幕结尾的重大转折"),
                    TemplateVariable("midpoint", "中点", "故事中间的重要转折"),
                    TemplateVariable("plot_point_two", "第二转折点", "第二幕结尾的转折"),
                    TemplateVariable("climax", "高潮", "故事的最高潮部分"),
                    TemplateVariable("resolution", "结局", "故事的结束"),
                    TemplateVariable("subplots", "子情节", "次要情节线"),
                    TemplateVariable("theme_exploration", "主题探索", "如何表达主题"),
                    TemplateVariable("writing_schedule", "写作计划", "写作时间安排")
                ],
                tags=["大纲", "结构", "规划"]
            )
            
            # 添加到模板字典
            templates = [novel_chapter, character_template, scene_template, dialogue_template, outline_template]
            for template in templates:
                self._templates[template.id] = template
            
            logger.info(f"内置模板加载完成，共 {len(templates)} 个模板")
            
        except Exception as e:
            logger.error(f"加载内置模板失败: {e}")
    
    def _load_custom_templates(self):
        """加载自定义模板"""
        try:
            custom_templates_file = self.templates_dir / "custom_templates.json"
            if custom_templates_file.exists():
                with open(custom_templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 验证数据格式
                if not isinstance(data, dict):
                    logger.warning("自定义模板文件格式无效")
                    return

                templates_data = data.get('templates', [])
                if not isinstance(templates_data, list):
                    logger.warning("自定义模板数据格式无效")
                    return

                loaded_count = 0
                for template_data in templates_data:
                    template = self._dict_to_template(template_data)
                    if template:
                        self._templates[template.id] = template
                        loaded_count += 1

                logger.info(f"自定义模板加载完成，共 {loaded_count} 个模板")

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"自定义模板文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载自定义模板失败: {e}")
    
    def _dict_to_template(self, data: dict) -> Optional[WritingTemplate]:
        """字典转模板对象"""
        try:
            # 验证必需字段
            required_fields = ['id', 'name', 'description', 'category', 'content']
            for field in required_fields:
                if field not in data:
                    logger.error(f"模板数据缺少必需字段: {field}")
                    return None

            # 验证并转换变量
            variables = []
            for var_data in data.get('variables', []):
                if isinstance(var_data, dict):
                    try:
                        variables.append(TemplateVariable(**var_data))
                    except TypeError as e:
                        logger.warning(f"跳过无效的变量数据: {e}")
                        continue
                else:
                    logger.warning(f"跳过非字典类型的变量数据: {type(var_data)}")

            # 验证分类
            try:
                category = TemplateCategory(data['category'])
            except ValueError:
                logger.error(f"无效的模板分类: {data['category']}")
                return None

            return WritingTemplate(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                category=category,
                content=data['content'],
                variables=variables,
                tags=data.get('tags', []) if isinstance(data.get('tags'), list) else [],
                author=data.get('author', '用户'),
                version=data.get('version', '1.0'),
                created_at=data.get('created_at', ''),
                is_builtin=data.get('is_builtin', False)
            )
        except Exception as e:
            logger.error(f"模板数据转换失败: {e}")
            return None
    
    def get_template(self, template_id: str) -> Optional[WritingTemplate]:
        """获取模板"""
        return self._templates.get(template_id)
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[WritingTemplate]:
        """按分类获取模板"""
        return [t for t in self._templates.values() if t.category == category]
    
    def get_all_templates(self) -> List[WritingTemplate]:
        """获取所有模板"""
        return list(self._templates.values())
    
    def search_templates(self, query: str) -> List[WritingTemplate]:
        """搜索模板"""
        query = query.lower()
        results = []
        
        for template in self._templates.values():
            if (query in template.name.lower() or 
                query in template.description.lower() or
                any(query in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return results
    
    def apply_template(self, template_id: str, variables: Dict[str, str]) -> Optional[str]:
        """应用模板"""
        try:
            template = self.get_template(template_id)
            if not template:
                logger.warning(f"模板不存在: {template_id}")
                return None

            content = template.content

            # 验证必需变量
            missing_required = []
            for var in template.variables:
                if var.required and var.name not in variables:
                    if not var.default_value:
                        missing_required.append(var.name)

            if missing_required:
                logger.error(f"缺少必需变量: {missing_required}")
                return None

            # 替换变量（安全替换，避免无限递归）
            for var in template.variables:
                value = variables.get(var.name, var.default_value)
                # 确保值是字符串类型
                if value is None:
                    value = ""
                else:
                    value = str(value)

                placeholder = "{" + var.name + "}"
                content = content.replace(placeholder, value)

            return content

        except Exception as e:
            logger.error(f"应用模板失败: {e}")
            return None
    
    def create_custom_template(self, template: WritingTemplate) -> bool:
        """创建自定义模板"""
        try:
            template.is_builtin = False
            self._templates[template.id] = template
            
            # 保存到文件
            self._save_custom_templates()
            
            logger.info(f"自定义模板创建成功: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"创建自定义模板失败: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            template = self._templates.get(template_id)
            if not template:
                return False
            
            if template.is_builtin:
                logger.warning(f"不能删除内置模板: {template_id}")
                return False
            
            del self._templates[template_id]
            self._save_custom_templates()
            
            logger.info(f"模板删除成功: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            return False
    
    def _save_custom_templates(self):
        """保存自定义模板"""
        try:
            custom_templates = [t for t in self._templates.values() if not t.is_builtin]

            data = {
                'version': '1.0',
                'templates': [asdict(t) for t in custom_templates]
            }

            custom_templates_file = self.templates_dir / "custom_templates.json"

            # 确保目录存在
            custom_templates_file.parent.mkdir(parents=True, exist_ok=True)

            # 使用临时文件确保原子性写入
            temp_file = custom_templates_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # 验证写入的文件
                with open(temp_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # 验证JSON格式

                # 原子性替换
                temp_file.replace(custom_templates_file)

            except Exception:
                # 清理临时文件
                if temp_file.exists():
                    temp_file.unlink()
                raise

        except Exception as e:
            logger.error(f"保存自定义模板失败: {e}")
    
    def export_template(self, template_id: str, file_path: Path) -> bool:
        """导出模板"""
        try:
            template = self.get_template(template_id)
            if not template:
                return False
            
            data = asdict(template)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模板导出成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            return False
    
    def import_template(self, file_path: Path) -> bool:
        """导入模板"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            template = self._dict_to_template(data)
            if template:
                return self.create_custom_template(template)
            
            return False
            
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            return False
    
    def get_categories(self) -> List[TemplateCategory]:
        """获取所有分类"""
        return list(TemplateCategory)
    
    def validate_template(self, template: WritingTemplate) -> List[str]:
        """验证模板"""
        errors = []
        
        if not template.id:
            errors.append("模板ID不能为空")
        
        if not template.name:
            errors.append("模板名称不能为空")
        
        if not template.content:
            errors.append("模板内容不能为空")
        
        # 检查变量引用
        for var in template.variables:
            placeholder = "{" + var.name + "}"
            if placeholder not in template.content:
                errors.append(f"模板内容中未使用变量: {var.name}")
        
        return errors

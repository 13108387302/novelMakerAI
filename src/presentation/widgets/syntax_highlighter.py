#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语法高亮器

为文本编辑器提供语法高亮功能
"""

import re
from typing import Dict, List, Tuple
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextDocument, QTextCharFormat, QColor, QFont

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class NovelSyntaxHighlighter(QSyntaxHighlighter):
    """
    小说语法高亮器

    为小说文本提供专门的语法高亮功能，包括对话、章节标题、
    人物名称、场景描述等元素的高亮显示。

    实现方式：
    - 继承QSyntaxHighlighter提供高亮功能
    - 使用正则表达式匹配不同的文本元素
    - 为不同元素定义不同的格式样式
    - 支持中英文混合文本的高亮
    - 提供自定义规则的添加和移除功能

    Attributes:
        _highlighting_rules: 高亮规则列表，包含正则表达式和格式
        _custom_rules: 用户自定义的高亮规则
        _enabled: 是否启用语法高亮
    """

    def __init__(self, document: QTextDocument):
        """
        初始化小说语法高亮器

        Args:
            document: 要应用高亮的文档对象
        """
        super().__init__(document)
        self._highlighting_rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._custom_rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._enabled = True
        self._setup_highlighting_rules()

        logger.debug("小说语法高亮器初始化完成")

    def _setup_highlighting_rules(self):
        """
        设置默认的高亮规则

        定义小说文本中常见元素的高亮规则，包括：
        - 对话文本（中英文引号）
        - 章节标题
        - Markdown格式标题
        - 强调文本
        - 特殊标记
        """
        # 清空现有规则
        self._highlighting_rules.clear()
        
        # 对话高亮
        dialogue_format = QTextCharFormat()
        dialogue_format.setForeground(QColor("#2E8B57"))  # 海绿色
        dialogue_format.setFontItalic(True)
        
        # 中文对话（引号）
        dialogue_pattern = QRegularExpression(r'"[^"]*"')
        self._highlighting_rules.append((dialogue_pattern, dialogue_format))
        
        # 英文对话
        dialogue_pattern_en = QRegularExpression(r'"[^"]*"')
        self._highlighting_rules.append((dialogue_pattern_en, dialogue_format))
        
        # 章节标题高亮
        chapter_format = QTextCharFormat()
        chapter_format.setForeground(QColor("#1E90FF"))  # 道奇蓝
        chapter_format.setFontWeight(QFont.Weight.Bold)
        chapter_format.setFontPointSize(16)
        
        chapter_pattern = QRegularExpression(r'^第[一二三四五六七八九十\d]+章.*$', 
                                           QRegularExpression.PatternOption.MultilineOption)
        self._highlighting_rules.append((chapter_pattern, chapter_format))
        
        # Markdown标题高亮
        markdown_h1_format = QTextCharFormat()
        markdown_h1_format.setForeground(QColor("#FF6347"))  # 番茄红
        markdown_h1_format.setFontWeight(QFont.Weight.Bold)
        markdown_h1_format.setFontPointSize(18)
        
        markdown_h1_pattern = QRegularExpression(r'^# .*$', 
                                                QRegularExpression.PatternOption.MultilineOption)
        self._highlighting_rules.append((markdown_h1_pattern, markdown_h1_format))
        
        markdown_h2_format = QTextCharFormat()
        markdown_h2_format.setForeground(QColor("#FF7F50"))  # 珊瑚色
        markdown_h2_format.setFontWeight(QFont.Weight.Bold)
        markdown_h2_format.setFontPointSize(16)
        
        markdown_h2_pattern = QRegularExpression(r'^## .*$', 
                                                QRegularExpression.PatternOption.MultilineOption)
        self._highlighting_rules.append((markdown_h2_pattern, markdown_h2_format))
        
        markdown_h3_format = QTextCharFormat()
        markdown_h3_format.setForeground(QColor("#FFA500"))  # 橙色
        markdown_h3_format.setFontWeight(QFont.Weight.Bold)
        markdown_h3_format.setFontPointSize(14)
        
        markdown_h3_pattern = QRegularExpression(r'^### .*$', 
                                                QRegularExpression.PatternOption.MultilineOption)
        self._highlighting_rules.append((markdown_h3_pattern, markdown_h3_format))
        
        # 强调文本高亮
        emphasis_format = QTextCharFormat()
        emphasis_format.setForeground(QColor("#8B4513"))  # 马鞍棕
        emphasis_format.setFontWeight(QFont.Weight.Bold)
        
        # 粗体
        bold_pattern = QRegularExpression(r'\*\*[^*]+\*\*')
        self._highlighting_rules.append((bold_pattern, emphasis_format))
        
        # 斜体
        italic_format = QTextCharFormat()
        italic_format.setForeground(QColor("#9932CC"))  # 深兰花紫
        italic_format.setFontItalic(True)
        
        italic_pattern = QRegularExpression(r'\*[^*]+\*')
        self._highlighting_rules.append((italic_pattern, italic_format))
        
        # 人名高亮（常见中文姓氏开头）
        name_format = QTextCharFormat()
        name_format.setForeground(QColor("#4169E1"))  # 皇家蓝
        name_format.setFontWeight(QFont.Weight.Bold)
        
        name_pattern = QRegularExpression(r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}')
        self._highlighting_rules.append((name_pattern, name_format))
        
        # 时间表达式高亮
        time_format = QTextCharFormat()
        time_format.setForeground(QColor("#DC143C"))  # 深红色
        time_format.setBackground(QColor("#FFF8DC"))  # 玉米丝色背景
        
        time_pattern = QRegularExpression(r'[上下]午|早上|中午|晚上|深夜|凌晨|黄昏|傍晚|夜里|半夜')
        self._highlighting_rules.append((time_pattern, time_format))
        
        # 地点高亮
        place_format = QTextCharFormat()
        place_format.setForeground(QColor("#228B22"))  # 森林绿
        place_format.setBackground(QColor("#F0FFF0"))  # 蜜瓜色背景
        
        place_pattern = QRegularExpression(r'[在到从][一-龯]*[市县区镇村街路巷院楼房间屋厅堂室]|[一-龯]*[山河湖海岛桥园林寺庙教堂医院学校公司酒店餐厅咖啡厅]')
        self._highlighting_rules.append((place_pattern, place_format))
        
        # 情感词汇高亮
        emotion_format = QTextCharFormat()
        emotion_format.setForeground(QColor("#FF1493"))  # 深粉色
        emotion_format.setFontItalic(True)
        
        emotion_pattern = QRegularExpression(r'[高兴|开心|快乐|愉快|兴奋|激动|喜悦|欣喜|愤怒|生气|恼火|暴怒|愤慨|悲伤|难过|伤心|痛苦|绝望|沮丧|失望|害怕|恐惧|紧张|焦虑|担心|惊讶|震惊|吃惊|困惑|疑惑|好奇|羡慕|嫉妒|感动|温暖|幸福|满足|平静|安详]')
        self._highlighting_rules.append((emotion_pattern, emotion_format))
        
        # 动作词汇高亮
        action_format = QTextCharFormat()
        action_format.setForeground(QColor("#FF8C00"))  # 深橙色
        action_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        
        action_pattern = QRegularExpression(r'[走|跑|跳|飞|游|爬|站|坐|躺|蹲|看|听|说|笑|哭|喊|叫|吃|喝|睡|醒|想|思考|回忆|梦见|拿|放|扔|抓|握|推|拉|打|踢|抱|亲|吻|摸|碰|撞|击|刺|砍|切|写|画|读|唱|跳舞|奔跑|行走|停止|开始|结束|继续|离开|到达|进入|出去|上升|下降|转身|回头|点头|摇头|挥手|鼓掌|拍手|敲门|开门|关门|打开|关闭]')
        self._highlighting_rules.append((action_pattern, action_format))
        
        # 注释高亮（以//或#开头的行）
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))  # 灰色
        comment_format.setFontItalic(True)
        
        comment_pattern = QRegularExpression(r'^[//|#].*$', 
                                           QRegularExpression.PatternOption.MultilineOption)
        self._highlighting_rules.append((comment_pattern, comment_format))
        
        # 特殊标记高亮（TODO, NOTE, FIXME等）
        special_format = QTextCharFormat()
        special_format.setForeground(QColor("#FFFFFF"))  # 白色
        special_format.setBackground(QColor("#FF0000"))  # 红色背景
        special_format.setFontWeight(QFont.Weight.Bold)
        
        special_pattern = QRegularExpression(r'\b(TODO|FIXME|NOTE|HACK|XXX|BUG)\b')
        self._highlighting_rules.append((special_pattern, special_format))
        
        logger.info(f"语法高亮规则设置完成，共 {len(self._highlighting_rules)} 条规则")
    
    def highlightBlock(self, text: str):
        """
        高亮文本块

        对传入的文本块应用所有高亮规则，包括默认规则和自定义规则。
        这是QSyntaxHighlighter的核心方法，会被自动调用。

        实现方式：
        - 遍历所有高亮规则
        - 使用正则表达式匹配文本
        - 为匹配的文本应用相应的格式
        - 处理多行块和特殊格式
        - 提供完整的错误处理

        Args:
            text: 要高亮的文本块
        """
        if not self._enabled:
            return

        try:
            # 应用所有高亮规则
            for pattern, format_obj in self._highlighting_rules:
                match_iterator = pattern.globalMatch(text)
                while match_iterator.hasNext():
                    match = match_iterator.next()
                    start = match.capturedStart()
                    length = match.capturedLength()
                    self.setFormat(start, length, format_obj)

            # 应用自定义规则
            for pattern, format_obj in self._custom_rules:
                match_iterator = pattern.globalMatch(text)
                while match_iterator.hasNext():
                    match = match_iterator.next()
                    start = match.capturedStart()
                    length = match.capturedLength()
                    self.setFormat(start, length, format_obj)

            # 处理多行注释或特殊块
            self._highlight_multiline_blocks(text)

        except Exception as e:
            logger.error(f"语法高亮处理失败: {e}")
    
    def _highlight_multiline_blocks(self, text: str):
        """
        处理多行高亮块

        处理跨越多行的特殊格式，如代码块、引用块等。
        使用状态机来跟踪多行块的开始和结束。

        Args:
            text: 当前文本块
        """
        try:
            # 代码块高亮（```包围的内容）
            code_format = QTextCharFormat()
            code_format.setForeground(QColor("#000080"))  # 海军蓝
            code_format.setBackground(QColor("#F5F5F5"))  # 白烟色背景
            code_format.setFontFamily("Consolas")
            
            # 查找代码块
            start_pattern = QRegularExpression(r'```')
            start_match = start_pattern.match(text)
            
            if start_match.hasMatch():
                start_index = start_match.capturedStart()
                # 查找结束标记
                end_match = start_pattern.match(text, start_index + 3)
                if end_match.hasMatch():
                    end_index = end_match.capturedEnd()
                    self.setFormat(start_index, end_index - start_index, code_format)
            
        except Exception as e:
            logger.error(f"多行块高亮处理失败: {e}")
    
    def update_theme(self, is_dark_theme: bool):
        """更新主题"""
        try:
            if is_dark_theme:
                self._setup_dark_theme_rules()
            else:
                self._setup_highlighting_rules()
            
            # 重新高亮整个文档
            self.rehighlight()
            
            logger.info(f"语法高亮主题已更新: {'深色' if is_dark_theme else '浅色'}")
            
        except Exception as e:
            logger.error(f"更新语法高亮主题失败: {e}")
    
    def _setup_dark_theme_rules(self):
        """设置深色主题规则"""
        # 清空现有规则
        self._highlighting_rules.clear()
        
        # 对话高亮（深色主题）
        dialogue_format = QTextCharFormat()
        dialogue_format.setForeground(QColor("#98FB98"))  # 淡绿色
        dialogue_format.setFontItalic(True)
        
        dialogue_pattern = QRegularExpression(r'"[^"]*"')
        self._highlighting_rules.append((dialogue_pattern, dialogue_format))
        
        # 章节标题高亮（深色主题）
        chapter_format = QTextCharFormat()
        chapter_format.setForeground(QColor("#87CEEB"))  # 天蓝色
        chapter_format.setFontWeight(QFont.Weight.Bold)
        chapter_format.setFontPointSize(16)
        
        chapter_pattern = QRegularExpression(r'^第[一二三四五六七八九十\d]+章.*$', 
                                           QRegularExpression.PatternOption.MultilineOption)
        self._highlighting_rules.append((chapter_pattern, chapter_format))
        
        # 其他规则也需要调整颜色以适应深色主题...
        # 这里只展示几个关键的，实际应用中需要调整所有颜色
        
        logger.info("深色主题语法高亮规则设置完成")
    
    def add_custom_rule(self, pattern: str, color: str, bold: bool = False, italic: bool = False):
        """添加自定义高亮规则"""
        try:
            custom_format = QTextCharFormat()
            custom_format.setForeground(QColor(color))
            
            if bold:
                custom_format.setFontWeight(QFont.Weight.Bold)
            if italic:
                custom_format.setFontItalic(True)
            
            custom_pattern = QRegularExpression(pattern)
            self._highlighting_rules.append((custom_pattern, custom_format))
            
            # 重新高亮
            self.rehighlight()
            
            logger.info(f"自定义高亮规则已添加: {pattern}")
            
        except Exception as e:
            logger.error(f"添加自定义高亮规则失败: {e}")
    
    def remove_custom_rules(self):
        """移除所有自定义规则"""
        try:
            # 重新设置默认规则
            self._setup_highlighting_rules()
            self.rehighlight()
            
            logger.info("自定义高亮规则已清除")
            
        except Exception as e:
            logger.error(f"清除自定义高亮规则失败: {e}")
    
    def set_enabled(self, enabled: bool):
        """启用/禁用语法高亮"""
        try:
            if enabled:
                self._setup_highlighting_rules()
            else:
                self._highlighting_rules.clear()
            
            self.rehighlight()
            
            logger.info(f"语法高亮已{'启用' if enabled else '禁用'}")
            
        except Exception as e:
            logger.error(f"设置语法高亮状态失败: {e}")


class MarkdownSyntaxHighlighter(QSyntaxHighlighter):
    """Markdown语法高亮器"""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._highlighting_rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self._setup_markdown_rules()
        
        logger.debug("Markdown语法高亮器初始化完成")
    
    def _setup_markdown_rules(self):
        """设置Markdown高亮规则"""
        # 标题
        for i in range(1, 7):
            header_format = QTextCharFormat()
            header_format.setForeground(QColor("#2E8B57"))
            header_format.setFontWeight(QFont.Weight.Bold)
            header_format.setFontPointSize(18 - i)
            
            header_pattern = QRegularExpression(f"^{'#' * i} .*$", 
                                              QRegularExpression.PatternOption.MultilineOption)
            self._highlighting_rules.append((header_pattern, header_format))
        
        # 粗体
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Weight.Bold)
        bold_pattern = QRegularExpression(r'\*\*[^*]+\*\*')
        self._highlighting_rules.append((bold_pattern, bold_format))
        
        # 斜体
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        italic_pattern = QRegularExpression(r'\*[^*]+\*')
        self._highlighting_rules.append((italic_pattern, italic_format))
        
        # 代码
        code_format = QTextCharFormat()
        code_format.setForeground(QColor("#8B4513"))
        code_format.setBackground(QColor("#F5F5F5"))
        code_format.setFontFamily("Consolas")
        code_pattern = QRegularExpression(r'`[^`]+`')
        self._highlighting_rules.append((code_pattern, code_format))
        
        # 链接
        link_format = QTextCharFormat()
        link_format.setForeground(QColor("#0000EE"))
        link_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        link_pattern = QRegularExpression(r'\[([^\]]+)\]\(([^)]+)\)')
        self._highlighting_rules.append((link_pattern, link_format))
    
    def highlightBlock(self, text: str):
        """高亮文本块"""
        for pattern, format_obj in self._highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, format_obj)

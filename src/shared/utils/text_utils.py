#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理工具

提供常用的文本处理和分析功能
"""

import re
import unicodedata
from typing import List, Dict, Tuple, Optional, Set, Union
from collections import Counter
from dataclasses import dataclass

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextStatistics:
    """
    文本统计信息
    
    包含文本的各种统计数据，如字符数、词数、段落数等。
    
    Attributes:
        char_count: 字符数（包含空格）
        char_count_no_spaces: 字符数（不含空格）
        word_count: 词数
        sentence_count: 句子数
        paragraph_count: 段落数
        line_count: 行数
        chinese_char_count: 中文字符数
        english_word_count: 英文单词数
        punctuation_count: 标点符号数
        reading_time_minutes: 预估阅读时间（分钟）
    """
    char_count: int = 0
    char_count_no_spaces: int = 0
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    line_count: int = 0
    chinese_char_count: int = 0
    english_word_count: int = 0
    punctuation_count: int = 0
    reading_time_minutes: float = 0.0


class TextProcessor:
    """
    文本处理器
    
    提供各种文本处理和分析功能，包括统计、格式化、清理等。
    
    实现方式：
    - 使用正则表达式进行文本匹配和处理
    - 支持中英文混合文本处理
    - 提供多种文本统计指标
    - 包含文本格式化和清理功能
    - 支持自定义处理规则
    """
    
    # 中文字符范围
    CHINESE_CHAR_PATTERN = re.compile(r'[\u4e00-\u9fff]')
    
    # 英文单词模式
    ENGLISH_WORD_PATTERN = re.compile(r'\b[a-zA-Z]+\b')
    
    # 句子分隔符
    SENTENCE_SEPARATORS = re.compile(r'[.!?。！？；;]')
    
    # 段落分隔符
    PARAGRAPH_SEPARATOR = re.compile(r'\n\s*\n')
    
    # 标点符号
    PUNCTUATION_PATTERN = re.compile(r'[^\w\s]', re.UNICODE)
    
    def __init__(self):
        """初始化文本处理器"""
        self.reading_speed_cpm = 300  # 每分钟阅读字符数（中文）
        self.reading_speed_wpm = 200  # 每分钟阅读单词数（英文）
    
    def analyze_text(self, text: str) -> TextStatistics:
        """
        分析文本统计信息
        
        对输入文本进行全面的统计分析，包括字符数、词数、句子数等。
        
        Args:
            text: 要分析的文本
            
        Returns:
            TextStatistics: 文本统计信息对象
        """
        if not text:
            return TextStatistics()
        
        try:
            stats = TextStatistics()
            
            # 基本统计
            stats.char_count = len(text)
            stats.char_count_no_spaces = len(text.replace(' ', '').replace('\t', '').replace('\n', ''))
            stats.line_count = len(text.splitlines())
            
            # 段落统计
            paragraphs = self.PARAGRAPH_SEPARATOR.split(text.strip())
            stats.paragraph_count = len([p for p in paragraphs if p.strip()])
            
            # 中文字符统计
            chinese_chars = self.CHINESE_CHAR_PATTERN.findall(text)
            stats.chinese_char_count = len(chinese_chars)
            
            # 英文单词统计
            english_words = self.ENGLISH_WORD_PATTERN.findall(text)
            stats.english_word_count = len(english_words)
            
            # 总词数（中文字符 + 英文单词）
            stats.word_count = stats.chinese_char_count + stats.english_word_count
            
            # 句子统计
            sentences = self.SENTENCE_SEPARATORS.split(text)
            stats.sentence_count = len([s for s in sentences if s.strip()])
            
            # 标点符号统计
            punctuation_marks = self.PUNCTUATION_PATTERN.findall(text)
            stats.punctuation_count = len(punctuation_marks)
            
            # 预估阅读时间
            stats.reading_time_minutes = self._calculate_reading_time(
                stats.chinese_char_count, stats.english_word_count
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"文本分析失败: {e}")
            return TextStatistics()
    
    def _calculate_reading_time(self, chinese_chars: int, english_words: int) -> float:
        """计算预估阅读时间"""
        chinese_time = chinese_chars / self.reading_speed_cpm
        english_time = english_words / self.reading_speed_wpm
        return chinese_time + english_time
    
    def clean_text(self, text: str, options: Dict[str, bool] = None) -> str:
        """
        清理文本
        
        根据指定选项清理文本中的多余空格、换行符等。
        
        Args:
            text: 要清理的文本
            options: 清理选项字典
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return text
        
        if options is None:
            options = {
                'remove_extra_spaces': True,
                'remove_extra_newlines': True,
                'trim_lines': True,
                'normalize_quotes': True,
                'remove_empty_lines': True
            }
        
        try:
            cleaned_text = text
            
            # 移除多余空格
            if options.get('remove_extra_spaces', True):
                cleaned_text = re.sub(r' +', ' ', cleaned_text)
            
            # 移除多余换行符
            if options.get('remove_extra_newlines', True):
                cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
            
            # 修剪行首行尾空格
            if options.get('trim_lines', True):
                lines = cleaned_text.splitlines()
                cleaned_text = '\n'.join(line.strip() for line in lines)
            
            # 标准化引号
            if options.get('normalize_quotes', True):
                cleaned_text = self._normalize_quotes(cleaned_text)
            
            # 移除空行
            if options.get('remove_empty_lines', True):
                lines = cleaned_text.splitlines()
                cleaned_text = '\n'.join(line for line in lines if line.strip())
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"文本清理失败: {e}")
            return text
    
    def _normalize_quotes(self, text: str) -> str:
        """标准化引号"""
        # 将各种引号统一为标准引号
        quote_map = {
            '"': '"',  # 左双引号
            '"': '"',  # 右双引号
            ''': "'",  # 左单引号
            ''': "'",  # 右单引号
            '「': '"',  # 日式左引号
            '」': '"',  # 日式右引号
        }
        
        for old_quote, new_quote in quote_map.items():
            text = text.replace(old_quote, new_quote)
        
        return text
    
    def format_text(self, text: str, format_options: Dict[str, any] = None) -> str:
        """
        格式化文本
        
        根据指定选项格式化文本，包括段落缩进、行间距等。
        
        Args:
            text: 要格式化的文本
            format_options: 格式化选项
            
        Returns:
            str: 格式化后的文本
        """
        if not text:
            return text
        
        if format_options is None:
            format_options = {
                'paragraph_indent': '    ',  # 段落缩进
                'line_spacing': 1,           # 行间距（额外空行数）
                'max_line_length': 0,        # 最大行长度（0表示不限制）
                'capitalize_sentences': False # 句首大写
            }
        
        try:
            formatted_text = text
            
            # 段落缩进
            indent = format_options.get('paragraph_indent', '')
            if indent:
                paragraphs = self.PARAGRAPH_SEPARATOR.split(formatted_text)
                indented_paragraphs = []
                for para in paragraphs:
                    if para.strip():
                        lines = para.splitlines()
                        indented_lines = [indent + line if line.strip() else line for line in lines]
                        indented_paragraphs.append('\n'.join(indented_lines))
                formatted_text = '\n\n'.join(indented_paragraphs)
            
            # 行间距
            line_spacing = format_options.get('line_spacing', 1)
            if line_spacing > 1:
                extra_newlines = '\n' * (line_spacing - 1)
                formatted_text = formatted_text.replace('\n', '\n' + extra_newlines)
            
            # 行长度限制
            max_length = format_options.get('max_line_length', 0)
            if max_length > 0:
                formatted_text = self._wrap_lines(formatted_text, max_length)
            
            # 句首大写
            if format_options.get('capitalize_sentences', False):
                formatted_text = self._capitalize_sentences(formatted_text)
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"文本格式化失败: {e}")
            return text
    
    def _wrap_lines(self, text: str, max_length: int) -> str:
        """换行处理"""
        lines = text.splitlines()
        wrapped_lines = []
        
        for line in lines:
            if len(line) <= max_length:
                wrapped_lines.append(line)
            else:
                # 简单的换行处理
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= max_length:
                        current_line += (" " + word) if current_line else word
                    else:
                        if current_line:
                            wrapped_lines.append(current_line)
                        current_line = word
                if current_line:
                    wrapped_lines.append(current_line)
        
        return '\n'.join(wrapped_lines)
    
    def _capitalize_sentences(self, text: str) -> str:
        """句首大写"""
        # 简单的句首大写处理
        sentences = self.SENTENCE_SEPARATORS.split(text)
        capitalized_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
            capitalized_sentences.append(sentence)
        
        return '. '.join(capitalized_sentences)
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[Tuple[str, int]]:
        """
        提取关键词
        
        从文本中提取最常见的关键词。
        
        Args:
            text: 要分析的文本
            max_keywords: 最大关键词数量
            
        Returns:
            List[Tuple[str, int]]: 关键词和频次的列表
        """
        if not text:
            return []
        
        try:
            # 移除标点符号
            cleaned_text = self.PUNCTUATION_PATTERN.sub(' ', text)
            
            # 提取中文字符和英文单词
            chinese_chars = self.CHINESE_CHAR_PATTERN.findall(cleaned_text)
            english_words = self.ENGLISH_WORD_PATTERN.findall(cleaned_text.lower())
            
            # 合并所有词汇
            all_words = chinese_chars + english_words
            
            # 过滤停用词（简单版本）
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', 
                         'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            
            filtered_words = [word for word in all_words if word not in stop_words and len(word) > 1]
            
            # 统计词频
            word_counts = Counter(filtered_words)
            
            # 返回最常见的关键词
            return word_counts.most_common(max_keywords)
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []
    
    def find_duplicates(self, text: str, min_length: int = 10) -> List[Tuple[str, List[int]]]:
        """
        查找重复文本
        
        查找文本中重复出现的片段。
        
        Args:
            text: 要分析的文本
            min_length: 最小重复片段长度
            
        Returns:
            List[Tuple[str, List[int]]]: 重复文本和位置列表
        """
        if not text or len(text) < min_length * 2:
            return []
        
        try:
            duplicates = []
            text_length = len(text)
            
            # 查找重复片段
            for i in range(text_length - min_length + 1):
                for j in range(i + min_length, text_length - min_length + 1):
                    # 检查从位置i和j开始的片段是否相同
                    match_length = 0
                    while (i + match_length < j and 
                           j + match_length < text_length and
                           text[i + match_length] == text[j + match_length]):
                        match_length += 1
                    
                    if match_length >= min_length:
                        duplicate_text = text[i:i + match_length]
                        # 查找所有出现位置
                        positions = []
                        start = 0
                        while True:
                            pos = text.find(duplicate_text, start)
                            if pos == -1:
                                break
                            positions.append(pos)
                            start = pos + 1
                        
                        if len(positions) > 1:
                            duplicates.append((duplicate_text, positions))
            
            # 去重并按长度排序
            unique_duplicates = {}
            for dup_text, positions in duplicates:
                if dup_text not in unique_duplicates:
                    unique_duplicates[dup_text] = positions
            
            result = list(unique_duplicates.items())
            result.sort(key=lambda x: len(x[0]), reverse=True)
            
            return result[:10]  # 返回前10个最长的重复片段
            
        except Exception as e:
            logger.error(f"查找重复文本失败: {e}")
            return []


# 全局文本处理器实例（单例模式）
_global_text_processor: Optional[TextProcessor] = None


def get_text_processor() -> TextProcessor:
    """获取全局文本处理器实例"""
    global _global_text_processor
    if _global_text_processor is None:
        _global_text_processor = TextProcessor()
    return _global_text_processor


# 统一的便捷函数工厂
def process_text(text: str, operation: str, **options) -> Union[str, TextStatistics, List]:
    """
    统一的文本处理便捷函数

    Args:
        text: 要处理的文本
        operation: 操作类型 ('analyze', 'clean', 'format', 'extract_keywords', 'find_duplicates')
        **options: 操作选项

    Returns:
        Union[str, TextStatistics, List]: 处理结果
    """
    processor = get_text_processor()

    if operation == 'analyze':
        return processor.analyze_text(text)
    elif operation == 'clean':
        return processor.clean_text(text, options)
    elif operation == 'format':
        return processor.format_text(text, options)
    elif operation == 'extract_keywords':
        max_keywords = options.get('max_keywords', 10)
        return processor.extract_keywords(text, max_keywords)
    elif operation == 'find_duplicates':
        min_length = options.get('min_length', 10)
        return processor.find_duplicates(text, min_length)
    else:
        raise ValueError(f"不支持的操作类型: {operation}")


# 保留向后兼容的便捷函数
def analyze_text(text: str) -> TextStatistics:
    """分析文本统计信息的便捷函数"""
    return process_text(text, 'analyze')


def clean_text(text: str, **options) -> str:
    """清理文本的便捷函数"""
    return process_text(text, 'clean', **options)


def format_text(text: str, **options) -> str:
    """格式化文本的便捷函数"""
    return process_text(text, 'format', **options)


def extract_keywords(text: str, max_keywords: int = 10) -> List[Tuple[str, int]]:
    """提取关键词的便捷函数"""
    processor = TextProcessor()
    return processor.extract_keywords(text, max_keywords)




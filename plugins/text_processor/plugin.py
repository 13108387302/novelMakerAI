#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理插件

提供基础的文本处理功能
"""

import re
from typing import Dict, Any, List
from PyQt6.QtWidgets import QMenu, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from src.shared.plugins.base_plugin import EditorPlugin, create_plugin_info
from src.shared.plugins.plugin_interface import PluginType, PluginInfo, hook, PluginHooks


class TextProcessorPlugin(EditorPlugin):
    """
    文本处理插件

    提供基础的文本处理功能，包括格式化、统计、转换等实用工具。
    集成到编辑器菜单中，为用户提供便捷的文本操作功能。

    实现方式：
    - 继承EditorPlugin基类
    - 提供多种文本处理功能
    - 集成到编辑器的菜单系统
    - 支持选中文本的批量处理
    - 提供文本统计和分析功能

    功能特性：
    - 文本格式化（去除多余空格、标准化段落等）
    - 文本统计（字数、段落数、句子数等）
    - 大小写转换
    - 文本替换和清理
    - 段落重排和格式化
    """

    def get_plugin_info(self) -> PluginInfo:
        """
        获取插件信息

        Returns:
            PluginInfo: 插件的详细信息
        """
        return create_plugin_info(
            plugin_id="text_processor",
            name="文本处理器",
            version="1.0.0",
            description="提供基础的文本处理功能，如格式化、统计、转换等",
            author="AI小说编辑器团队",
            plugin_type=PluginType.TOOL,
            dependencies=[],
            min_app_version="2.0.0",
            tags=["文本", "处理", "工具"]
        )

    def on_initialize(self) -> bool:
        """
        初始化插件

        执行插件的初始化逻辑，准备插件运行环境。

        Returns:
            bool: 初始化成功返回True，失败返回False
        """
        try:
            self.log_info("初始化文本处理插件...")
            return True
        except Exception as e:
            self.log_error(f"初始化失败: {e}")
            return False

    def on_activate(self) -> bool:
        """
        激活插件

        激活插件功能，创建菜单项和工具栏按钮。

        Returns:
            bool: 激活成功返回True，失败返回False
        """
        try:
            self.log_info("激活文本处理插件...")

            # 创建菜单和动作
            self._create_menu()
            
            # 注册钩子
            self.register_hook(PluginHooks.MENU_CREATED, self._on_menu_created)
            
            return True
        except Exception as e:
            self.log_error(f"激活失败: {e}")
            return False
    
    def on_deactivate(self) -> bool:
        """停用插件"""
        try:
            self.log_info("停用文本处理插件...")
            
            # 取消注册钩子
            self.unregister_hook(PluginHooks.MENU_CREATED, self._on_menu_created)
            
            return True
        except Exception as e:
            self.log_error(f"停用失败: {e}")
            return False
    
    def _create_menu(self):
        """创建菜单"""
        try:
            # 获取主窗口
            main_window = self.get_api("main_window")
            if not main_window:
                self.log_warning("无法获取主窗口")
                return
            
            # 创建文本处理菜单
            menubar = main_window.menuBar()
            text_menu = menubar.addMenu("文本处理(&X)")
            self.add_menu(text_menu)
            
            # 格式化子菜单
            format_menu = text_menu.addMenu("格式化")
            
            # 移除多余空行
            remove_empty_lines_action = QAction("移除多余空行", main_window)
            remove_empty_lines_action.triggered.connect(self._remove_empty_lines)
            format_menu.addAction(remove_empty_lines_action)
            self.add_action(remove_empty_lines_action)
            
            # 统一段落格式
            format_paragraphs_action = QAction("统一段落格式", main_window)
            format_paragraphs_action.triggered.connect(self._format_paragraphs)
            format_menu.addAction(format_paragraphs_action)
            self.add_action(format_paragraphs_action)
            
            # 修正标点符号
            fix_punctuation_action = QAction("修正标点符号", main_window)
            fix_punctuation_action.triggered.connect(self._fix_punctuation)
            format_menu.addAction(fix_punctuation_action)
            self.add_action(fix_punctuation_action)
            
            text_menu.addSeparator()
            
            # 转换子菜单
            convert_menu = text_menu.addMenu("转换")
            
            # 繁简转换
            to_simplified_action = QAction("转换为简体中文", main_window)
            to_simplified_action.triggered.connect(self._to_simplified)
            convert_menu.addAction(to_simplified_action)
            self.add_action(to_simplified_action)
            
            to_traditional_action = QAction("转换为繁体中文", main_window)
            to_traditional_action.triggered.connect(self._to_traditional)
            convert_menu.addAction(to_traditional_action)
            self.add_action(to_traditional_action)
            
            text_menu.addSeparator()
            
            # 统计功能
            word_frequency_action = QAction("词频统计", main_window)
            word_frequency_action.triggered.connect(self._word_frequency)
            text_menu.addAction(word_frequency_action)
            self.add_action(word_frequency_action)
            
            readability_action = QAction("可读性分析", main_window)
            readability_action.triggered.connect(self._readability_analysis)
            text_menu.addAction(readability_action)
            self.add_action(readability_action)
            
            self.log_info("文本处理菜单创建完成")
            
        except Exception as e:
            self.log_error(f"创建菜单失败: {e}")
    
    def _remove_empty_lines(self):
        """移除多余空行"""
        try:
            text = self.get_selected_text()
            if not text:
                current_doc = self.get_current_document()
                if current_doc:
                    text = current_doc.content
                else:
                    QMessageBox.warning(None, "提示", "请选择文本或打开文档")
                    return
            
            # 移除多余空行（保留单个空行）
            processed_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            
            if text != processed_text:
                if self.get_selected_text():
                    self.replace_selected_text(processed_text)
                else:
                    # 替换整个文档内容（通过编辑器服务，保证UI同步）
                    self.set_content(processed_text)

                QMessageBox.information(None, "完成", "已移除多余空行")
            else:
                QMessageBox.information(None, "提示", "文本中没有多余的空行")
                
        except Exception as e:
            self.log_error(f"移除空行失败: {e}")
            QMessageBox.critical(None, "错误", f"处理失败: {e}")
    
    def _format_paragraphs(self):
        """统一段落格式"""
        try:
            text = self.get_selected_text()
            if not text:
                current_doc = self.get_current_document()
                if current_doc:
                    text = current_doc.content
                else:
                    QMessageBox.warning(None, "提示", "请选择文本或打开文档")
                    return
            
            # 统一段落格式：每段开头缩进两个空格
            lines = text.split('\n')
            processed_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # 如果不是以空格开头，添加两个空格缩进
                    if not line.startswith('  '):
                        line = '  ' + line
                processed_lines.append(line)
            
            processed_text = '\n'.join(processed_lines)
            
            if text != processed_text:
                if self.get_selected_text():
                    self.replace_selected_text(processed_text)
                else:
                    # 替换整个文档内容（通过编辑器服务，保证UI同步）
                    self.set_content(processed_text)

                QMessageBox.information(None, "完成", "已统一段落格式")
            else:
                QMessageBox.information(None, "提示", "段落格式已经统一")
                
        except Exception as e:
            self.log_error(f"格式化段落失败: {e}")
            QMessageBox.critical(None, "错误", f"处理失败: {e}")
    
    def _fix_punctuation(self):
        """修正标点符号"""
        try:
            text = self.get_selected_text()
            if not text:
                current_doc = self.get_current_document()
                if current_doc:
                    text = current_doc.content
                else:
                    QMessageBox.warning(None, "提示", "请选择文本或打开文档")
                    return
            
            # 修正常见的标点符号问题
            processed_text = text
            
            # 修正引号
            processed_text = re.sub(r'"([^"]*)"', r'"\1"', processed_text)
            processed_text = re.sub(r"'([^']*)'", "'\1'", processed_text)
            
            # 修正省略号
            processed_text = re.sub(r'\.{3,}', '……', processed_text)
            
            # 修正破折号
            processed_text = re.sub(r'--+', '——', processed_text)
            
            if text != processed_text:
                if self.get_selected_text():
                    self.replace_selected_text(processed_text)
                else:
                    current_doc = self.get_current_document()
                    if current_doc:
                        current_doc.content = processed_text
                
                QMessageBox.information(None, "完成", "已修正标点符号")
            else:
                QMessageBox.information(None, "提示", "标点符号无需修正")
                
        except Exception as e:
            self.log_error(f"修正标点符号失败: {e}")
            QMessageBox.critical(None, "错误", f"处理失败: {e}")
    
    def _to_simplified(self):
        """转换为简体中文"""
        QMessageBox.information(None, "功能开发中", "繁简转换功能正在开发中")
    
    def _to_traditional(self):
        """转换为繁体中文"""
        QMessageBox.information(None, "功能开发中", "繁简转换功能正在开发中")
    
    def _word_frequency(self):
        """词频统计"""
        try:
            text = self.get_selected_text()
            if not text:
                current_doc = self.get_current_document()
                if current_doc:
                    text = current_doc.content
                else:
                    QMessageBox.warning(None, "提示", "请选择文本或打开文档")
                    return
            
            # 简单的词频统计
            import collections
            
            # 移除标点符号和空白字符
            clean_text = re.sub(r'[^\w\s]', '', text)
            words = clean_text.split()
            
            # 统计词频
            word_freq = collections.Counter(words)
            
            # 显示前10个高频词
            top_words = word_freq.most_common(10)
            
            result = "词频统计结果（前10个）:\n\n"
            for word, count in top_words:
                result += f"{word}: {count}\n"
            
            QMessageBox.information(None, "词频统计", result)
            
        except Exception as e:
            self.log_error(f"词频统计失败: {e}")
            QMessageBox.critical(None, "错误", f"统计失败: {e}")
    
    def _readability_analysis(self):
        """可读性分析"""
        try:
            text = self.get_selected_text()
            if not text:
                current_doc = self.get_current_document()
                if current_doc:
                    text = current_doc.content
                else:
                    QMessageBox.warning(None, "提示", "请选择文本或打开文档")
                    return
            
            # 简单的可读性分析
            char_count = len(text)
            word_count = len(text.split())
            sentence_count = len(re.findall(r'[。！？.!?]', text))
            paragraph_count = len([p for p in text.split('\n') if p.strip()])
            
            avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
            avg_chars_per_word = char_count / word_count if word_count > 0 else 0
            
            result = f"""可读性分析结果:

字符数: {char_count:,}
词数: {word_count:,}
句子数: {sentence_count:,}
段落数: {paragraph_count:,}

平均每句词数: {avg_words_per_sentence:.1f}
平均每词字符数: {avg_chars_per_word:.1f}

可读性评估:
{'简单' if avg_words_per_sentence < 15 else '中等' if avg_words_per_sentence < 25 else '复杂'}
"""
            
            QMessageBox.information(None, "可读性分析", result)
            
        except Exception as e:
            self.log_error(f"可读性分析失败: {e}")
            QMessageBox.critical(None, "错误", f"分析失败: {e}")
    
    @hook(PluginHooks.MENU_CREATED)
    def _on_menu_created(self, menu_bar):
        """菜单创建钩子"""
        self.log_info("主菜单已创建，文本处理菜单已添加")


# 插件入口点
def create_plugin():
    """创建插件实例"""
    return TextProcessorPlugin()

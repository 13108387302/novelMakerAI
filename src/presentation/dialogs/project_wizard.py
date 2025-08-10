#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目创建向导

引导用户创建新项目
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QGroupBox, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from src.domain.entities.project import ProjectType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ProjectInfoPage(QWizardPage):
    """
    项目信息页面

    项目创建向导的第一页，收集项目的基本信息。
    包括项目名称、类型、作者等基础信息。

    Attributes:
        name_edit: 项目名称输入框
        type_combo: 项目类型下拉框
        author_edit: 作者输入框
        description_edit: 项目描述输入框
    """

    def __init__(self):
        """
        初始化项目信息页面
        """
        super().__init__()
        self.setTitle("项目基本信息")
        self.setSubTitle("请填写项目的基本信息")
        
        layout = QVBoxLayout(self)
        
        # 项目信息组
        info_group = QGroupBox("项目信息")
        info_layout = QGridLayout(info_group)
        
        # 项目名称
        info_layout.addWidget(QLabel("项目名称 *:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入项目名称...")
        info_layout.addWidget(self.name_edit, 0, 1)
        
        # 项目类型
        info_layout.addWidget(QLabel("项目类型:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["小说", "散文", "诗歌", "剧本", "其他"])
        info_layout.addWidget(self.type_combo, 1, 1)
        
        # 作者
        info_layout.addWidget(QLabel("作者:"), 2, 0)
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("输入作者姓名...")
        info_layout.addWidget(self.author_edit, 2, 1)
        
        # 类型
        info_layout.addWidget(QLabel("类型:"), 3, 0)
        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("如：科幻、言情、悬疑...")
        info_layout.addWidget(self.genre_edit, 3, 1)
        
        layout.addWidget(info_group)
        
        # 项目描述
        desc_group = QGroupBox("项目描述")
        desc_layout = QVBoxLayout(desc_group)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(120)
        self.description_edit.setPlaceholderText("简要描述你的项目内容、主题或创作想法...")
        desc_layout.addWidget(self.description_edit)
        
        layout.addWidget(desc_group)
        
        # 注册字段
        self.registerField("name*", self.name_edit)
        self.registerField("type", self.type_combo, "currentText")
        self.registerField("author", self.author_edit)
        self.registerField("genre", self.genre_edit)
        self.registerField("description", self.description_edit, "plainText")
    
    def validatePage(self):
        """验证页面"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "请输入项目名称")
            return False
        return True


class ProjectSettingsPage(QWizardPage):
    """项目设置页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("项目设置")
        self.setSubTitle("配置项目的详细设置")
        
        layout = QVBoxLayout(self)
        
        # 目标设置
        target_group = QGroupBox("创作目标")
        target_layout = QGridLayout(target_group)
        
        target_layout.addWidget(QLabel("目标字数:"), 0, 0)
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(1000, 10000000)
        self.word_count_spin.setValue(80000)
        self.word_count_spin.setSuffix(" 字")
        target_layout.addWidget(self.word_count_spin, 0, 1)
        
        target_layout.addWidget(QLabel("预计章节数:"), 1, 0)
        self.chapter_count_spin = QSpinBox()
        self.chapter_count_spin.setRange(1, 1000)
        self.chapter_count_spin.setValue(20)
        self.chapter_count_spin.setSuffix(" 章")
        target_layout.addWidget(self.chapter_count_spin, 1, 1)
        
        layout.addWidget(target_group)
        
        # 项目选项
        options_group = QGroupBox("项目选项")
        options_layout = QVBoxLayout(options_group)
        
        self.auto_backup_check = QCheckBox("启用自动备份")
        self.auto_backup_check.setChecked(True)
        options_layout.addWidget(self.auto_backup_check)
        
        self.version_control_check = QCheckBox("启用版本控制")
        self.version_control_check.setChecked(True)
        options_layout.addWidget(self.version_control_check)
        
        self.ai_assistance_check = QCheckBox("启用AI写作助手")
        self.ai_assistance_check.setChecked(True)
        options_layout.addWidget(self.ai_assistance_check)
        
        layout.addWidget(options_group)
        
        # 存储位置
        storage_group = QGroupBox("存储位置")
        storage_layout = QGridLayout(storage_group)
        
        storage_layout.addWidget(QLabel("项目文件夹:"), 0, 0)
        self.location_edit = QLineEdit()
        self.location_edit.setReadOnly(True)
        storage_layout.addWidget(self.location_edit, 0, 1)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse_location)
        storage_layout.addWidget(self.browse_btn, 0, 2)

        # 添加提示标签
        hint_label = QLabel("💡 默认在当前目录下的 projects 文件夹中创建项目")
        hint_label.setStyleSheet("color: #666; font-size: 12px;")
        storage_layout.addWidget(hint_label, 1, 0, 1, 3)

        layout.addWidget(storage_group)
        
        # 设置默认位置为当前工作目录
        import os
        current_dir = os.getcwd()
        # 在当前目录下创建一个projects子目录
        default_location = os.path.join(current_dir, "projects")

        # 确保projects目录存在
        try:
            os.makedirs(default_location, exist_ok=True)
            logger.info(f"默认项目目录已创建: {default_location}")
        except Exception as e:
            logger.warning(f"创建默认项目目录失败: {e}")
            # 如果创建失败，回退到用户文档目录
            default_location = os.path.join(os.path.expanduser("~"), "Documents", "AI小说编辑器")
            try:
                os.makedirs(default_location, exist_ok=True)
            except Exception as e2:
                logger.error(f"创建备用项目目录也失败: {e2}")

        self.location_edit.setText(default_location)
        
        # 注册字段
        self.registerField("word_count", self.word_count_spin)
        self.registerField("chapter_count", self.chapter_count_spin)
        self.registerField("auto_backup", self.auto_backup_check)
        self.registerField("version_control", self.version_control_check)
        self.registerField("ai_assistance", self.ai_assistance_check)
        self.registerField("location", self.location_edit)
    
    def _browse_location(self):
        """浏览存储位置"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择项目存储位置",
            self.location_edit.text()
        )
        if folder:
            self.location_edit.setText(folder)


class ProjectTemplatePage(QWizardPage):
    """项目模板页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("选择项目模板")
        self.setSubTitle("选择一个项目模板来快速开始")
        
        layout = QVBoxLayout(self)
        
        # 模板列表
        self.template_list = QListWidget()
        self.template_list.setMaximumHeight(200)
        
        # 添加模板
        templates = [
            ("空白项目", "从零开始创建项目"),
            ("长篇小说", "包含章节结构的长篇小说模板"),
            ("短篇小说", "适合短篇小说创作的模板"),
            ("散文集", "散文创作模板"),
            ("剧本", "戏剧剧本创作模板"),
            ("诗歌集", "诗歌创作模板")
        ]
        
        for name, desc in templates:
            item = QListWidgetItem(f"{name}\n{desc}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.template_list.addItem(item)
        
        # 默认选择第一个
        self.template_list.setCurrentRow(0)
        
        layout.addWidget(QLabel("可用模板:"))
        layout.addWidget(self.template_list)
        
        # 模板预览
        preview_group = QGroupBox("模板预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setReadOnly(True)
        self.preview_text.setText("选择一个模板查看详细信息...")
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # 连接信号
        self.template_list.currentItemChanged.connect(self._on_template_changed)
        
        # 注册字段
        self.registerField("template", self.template_list, "currentItem")
    
    def _on_template_changed(self, current, previous):
        """模板选择变化"""
        if current:
            template_name = current.data(Qt.ItemDataRole.UserRole)
            
            previews = {
                "空白项目": "创建一个空白项目，你可以自由组织结构。",
                "长篇小说": "包含以下结构：\n• 人物设定\n• 大纲\n• 第一章\n• 第二章\n• ...",
                "短篇小说": "包含以下结构：\n• 故事大纲\n• 正文\n• 后记",
                "散文集": "包含以下结构：\n• 序言\n• 散文一\n• 散文二\n• ...",
                "剧本": "包含以下结构：\n• 人物表\n• 第一幕\n• 第二幕\n• ...",
                "诗歌集": "包含以下结构：\n• 序言\n• 诗歌一\n• 诗歌二\n• ..."
            }
            
            self.preview_text.setText(previews.get(template_name, "模板预览"))


class ProjectSummaryPage(QWizardPage):
    """项目摘要页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("确认项目信息")
        self.setSubTitle("请确认项目信息，然后点击完成创建项目")
        
        layout = QVBoxLayout(self)
        
        # 摘要信息
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def initializePage(self):
        """初始化页面"""
        # 收集所有信息
        wizard = self.wizard()
        
        name = wizard.field("name")
        project_type = wizard.field("type")
        author = wizard.field("author")
        genre = wizard.field("genre")
        description = wizard.field("description")
        word_count = wizard.field("word_count")
        chapter_count = wizard.field("chapter_count")
        location = wizard.field("location")
        
        # 生成摘要
        summary = f"""
<h3>项目摘要</h3>

<b>基本信息:</b>
• 项目名称: {name}
• 项目类型: {project_type}
• 作者: {author or '未设置'}
• 类型: {genre or '未设置'}

<b>创作目标:</b>
• 目标字数: {word_count:,} 字
• 预计章节: {chapter_count} 章

<b>存储位置:</b>
{location}

<b>项目描述:</b>
{description or '无描述'}

<b>启用功能:</b>
• 自动备份: {'是' if wizard.field('auto_backup') else '否'}
• 版本控制: {'是' if wizard.field('version_control') else '否'}
• AI助手: {'是' if wizard.field('ai_assistance') else '否'}
        """
        
        self.summary_text.setHtml(summary.strip())


class ProjectWizard(QWizard):
    """
    项目创建向导

    引导用户创建新项目的向导对话框。
    分步骤收集项目信息，包括基本信息、设置和模板选择。

    实现方式：
    - 使用QWizard提供分步向导界面
    - 包含多个向导页面收集不同信息
    - 提供项目信息验证和预览
    - 支持项目模板和预设配置
    - 完成后发出项目创建信号

    Attributes:
        info_page: 项目信息页面
        settings_page: 项目设置页面
        template_page: 模板选择页面
        summary_page: 信息摘要页面

    Signals:
        project_created: 项目创建信号(项目信息字典)
    """

    # 信号定义
    project_created = pyqtSignal(dict)  # 项目信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建项目向导")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(600, 500)
        
        # 添加页面
        self.addPage(ProjectInfoPage())
        self.addPage(ProjectSettingsPage())
        self.addPage(ProjectTemplatePage())
        self.addPage(ProjectSummaryPage())
        
        # 设置按钮文本
        self.setButtonText(QWizard.WizardButton.NextButton, "下一步 >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< 上一步")
        self.setButtonText(QWizard.WizardButton.FinishButton, "创建项目")
        self.setButtonText(QWizard.WizardButton.CancelButton, "取消")
        
        # 应用样式
        self._apply_styles()
        
        logger.debug("项目创建向导初始化完成")
    
    def _apply_styles(self):
        """
        应用样式 - 使用主题管理器

        为项目向导应用统一的主题样式，确保界面美观一致。
        """
        try:
            # 基础样式
            self.setStyleSheet("""
                QWizard {
                    background-color: #f5f5f5;
                    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                }

                QWizardPage {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    margin: 10px;
                    padding: 20px;
                }

                QLabel {
                    color: #333;
                    font-size: 12px;
                }

                QLineEdit, QTextEdit, QComboBox, QSpinBox {
                    border: 2px solid #ddd;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 12px;
                    background-color: white;
                    color: #333;
                    selection-background-color: #4CAF50;
                    selection-color: white;
                }

                QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                    border-color: #4CAF50;
                    outline: none;
                    color: #111;
                }

                QLineEdit::placeholder, QTextEdit::placeholder {
                    color: #999;
                }

                QCheckBox {
                    font-size: 12px;
                    color: #333;
                    spacing: 8px;
                }

                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #ddd;
                    border-radius: 3px;
                    background-color: white;
                }

                QCheckBox::indicator:checked {
                    background-color: #4CAF50;
                    border-color: #4CAF50;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
                }

                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    font-size: 12px;
                    font-weight: bold;
                }

                QPushButton:hover {
                    background-color: #45a049;
                }

                QPushButton:pressed {
                    background-color: #3d8b40;
                }

                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }

                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 10px;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #4CAF50;
                }

                QListWidget {
                    border: 2px solid #ddd;
                    border-radius: 4px;
                    background-color: white;
                    alternate-background-color: #f9f9f9;
                }

                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #eee;
                }

                QListWidget::item:selected {
                    background-color: #4CAF50;
                    color: white;
                }

                QListWidget::item:hover {
                    background-color: #e8f5e8;
                }
            """)

            logger.debug("项目向导样式应用完成")

        except Exception as e:
            logger.error(f"应用项目向导样式失败: {e}")
    
    def accept(self):
        """完成向导"""
        try:
            # 收集项目信息
            project_info = {
                "name": self.field("name"),
                "type": self.field("type"),
                "author": self.field("author"),
                "genre": self.field("genre"),
                "description": self.field("description"),
                "word_count": self.field("word_count"),
                "chapter_count": self.field("chapter_count"),
                "location": self.field("location"),
                "auto_backup": self.field("auto_backup"),
                "version_control": self.field("version_control"),
                "ai_assistance": self.field("ai_assistance"),
                "template": self.field("template").data(Qt.ItemDataRole.UserRole) if self.field("template") else "空白项目"
            }
            
            # 发出项目创建信号
            self.project_created.emit(project_info)
            
            # 关闭向导
            super().accept()
            
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            QMessageBox.critical(self, "创建失败", f"项目创建失败: {e}")
    
    def get_project_type(self, type_name: str) -> ProjectType:
        """获取项目类型"""
        type_map = {
            "小说": ProjectType.NOVEL,
            "散文": ProjectType.ESSAY,
            "诗歌": ProjectType.POETRY,
            "剧本": ProjectType.SCRIPT,
            "其他": ProjectType.OTHER
        }
        return type_map.get(type_name, ProjectType.NOVEL)

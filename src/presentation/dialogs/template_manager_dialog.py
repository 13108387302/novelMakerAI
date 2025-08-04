#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板管理对话框

管理和使用写作模板
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QListWidget, QListWidgetItem, QGroupBox, QSplitter, QScrollArea,
    QMessageBox, QFileDialog, QFormLayout, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from src.application.services.template_service import TemplateService, WritingTemplate, TemplateCategory, TemplateVariable
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateVariableWidget(QWidget):
    """模板变量输入组件"""
    
    def __init__(self, variable: TemplateVariable):
        super().__init__()
        self.variable = variable
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签
        label_text = self.variable.description
        if self.variable.required:
            label_text += " *"
        
        label = QLabel(label_text)
        if self.variable.required:
            label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)
        
        # 输入控件
        if self.variable.variable_type == "number":
            self.input_widget = QSpinBox()
            self.input_widget.setRange(0, 999999)
            if self.variable.default_value.isdigit():
                self.input_widget.setValue(int(self.variable.default_value))
        elif self.variable.variable_type == "choice":
            self.input_widget = QComboBox()
            # 这里可以根据需要添加选项
            self.input_widget.addItems(["男", "女", "其他"])
            if self.variable.default_value:
                index = self.input_widget.findText(self.variable.default_value)
                if index >= 0:
                    self.input_widget.setCurrentIndex(index)
        else:
            if len(self.variable.default_value) > 50:
                self.input_widget = QTextEdit()
                self.input_widget.setMaximumHeight(100)
                self.input_widget.setPlainText(self.variable.default_value)
            else:
                self.input_widget = QLineEdit()
                self.input_widget.setText(self.variable.default_value)
                self.input_widget.setPlaceholderText(self.variable.description)
        
        layout.addWidget(self.input_widget)
    
    def get_value(self) -> str:
        """获取输入值"""
        if isinstance(self.input_widget, QLineEdit):
            return self.input_widget.text()
        elif isinstance(self.input_widget, QTextEdit):
            return self.input_widget.toPlainText()
        elif isinstance(self.input_widget, QSpinBox):
            return str(self.input_widget.value())
        elif isinstance(self.input_widget, QComboBox):
            return self.input_widget.currentText()
        return ""


class TemplatePreviewWidget(QWidget):
    """模板预览组件"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("📋 模板预览")
        title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 预览文本
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        # 使用主题样式
        self.preview_text.setStyleSheet("")
        layout.addWidget(self.preview_text)
    
    def update_preview(self, content: str):
        """更新预览内容"""
        self.preview_text.setPlainText(content)


class TemplateManagerDialog(QDialog):
    """模板管理对话框"""
    
    # 信号定义
    template_applied = pyqtSignal(str)  # 应用的模板内容
    
    def __init__(self, template_service: TemplateService, parent=None):
        super().__init__(parent)
        self.template_service = template_service
        self.current_template: WritingTemplate = None
        self.variable_widgets = {}
        self._setup_ui()
        self._load_templates()
        
        logger.debug("模板管理对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("📝 写作模板管理器")
        self.setModal(True)
        self.resize(1000, 700)
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：模板列表
        left_widget = self._create_template_list()
        splitter.addWidget(left_widget)
        
        # 右侧：模板详情和应用
        right_widget = self._create_template_details()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        # 按钮区域
        self._create_buttons()
        layout.addLayout(self.buttons_layout)
        
        # 应用样式
        self._apply_styles()
    
    def _create_template_list(self) -> QWidget:
        """创建模板列表"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("📚 模板库")
        title_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 分类筛选
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("全部", None)
        for category in TemplateCategory:
            category_names = {
                TemplateCategory.NOVEL: "📖 小说",
                TemplateCategory.SHORT_STORY: "📄 短篇",
                TemplateCategory.ESSAY: "📝 散文",
                TemplateCategory.POETRY: "🎭 诗歌",
                TemplateCategory.SCRIPT: "🎬 剧本",
                TemplateCategory.CHARACTER: "👤 人物",
                TemplateCategory.SCENE: "🏞️ 场景",
                TemplateCategory.DIALOGUE: "💬 对话",
                TemplateCategory.OUTLINE: "📋 大纲",
                TemplateCategory.CUSTOM: "🔧 自定义"
            }
            self.category_combo.addItem(category_names.get(category, category.value), category)
        
        self.category_combo.currentTextChanged.connect(self._filter_templates)
        filter_layout.addWidget(self.category_combo)
        
        layout.addLayout(filter_layout)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词搜索模板...")
        self.search_edit.textChanged.connect(self._search_templates)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # 模板列表
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        layout.addWidget(self.template_list)
        
        # 管理按钮
        manage_layout = QHBoxLayout()
        
        self.new_template_btn = QPushButton("➕ 新建")
        self.new_template_btn.clicked.connect(self._create_new_template)
        manage_layout.addWidget(self.new_template_btn)
        
        self.import_btn = QPushButton("📥 导入")
        self.import_btn.clicked.connect(self._import_template)
        manage_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.clicked.connect(self._export_template)
        manage_layout.addWidget(self.export_btn)
        
        layout.addLayout(manage_layout)
        
        return widget
    
    def _create_template_details(self) -> QWidget:
        """创建模板详情"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 模板信息标签页
        info_tab = self._create_info_tab()
        self.tab_widget.addTab(info_tab, "ℹ️ 模板信息")
        
        # 变量设置标签页
        variables_tab = self._create_variables_tab()
        self.tab_widget.addTab(variables_tab, "⚙️ 变量设置")
        
        # 预览标签页
        preview_tab = self._create_preview_tab()
        self.tab_widget.addTab(preview_tab, "👁️ 预览")
        
        layout.addWidget(self.tab_widget)
        
        return widget
    
    def _create_info_tab(self) -> QWidget:
        """创建信息标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 模板信息
        info_group = QGroupBox("模板信息")
        info_layout = QFormLayout(info_group)
        
        self.template_name_label = QLabel("-")
        info_layout.addRow("名称:", self.template_name_label)
        
        self.template_description_label = QLabel("-")
        self.template_description_label.setWordWrap(True)
        info_layout.addRow("描述:", self.template_description_label)
        
        self.template_category_label = QLabel("-")
        info_layout.addRow("分类:", self.template_category_label)
        
        self.template_author_label = QLabel("-")
        info_layout.addRow("作者:", self.template_author_label)
        
        self.template_tags_label = QLabel("-")
        self.template_tags_label.setWordWrap(True)
        info_layout.addRow("标签:", self.template_tags_label)
        
        layout.addWidget(info_group)
        
        # 模板内容
        content_group = QGroupBox("模板内容")
        content_layout = QVBoxLayout(content_group)
        
        self.template_content_text = QTextEdit()
        self.template_content_text.setReadOnly(True)
        self.template_content_text.setMaximumHeight(200)
        content_layout.addWidget(self.template_content_text)
        
        layout.addWidget(content_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_variables_tab(self) -> QWidget:
        """创建变量标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 说明
        help_label = QLabel("💡 填写模板变量，然后点击'生成预览'查看效果")
        help_label.setStyleSheet("font-style: italic; padding: 8px;")
        layout.addWidget(help_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.variables_widget = QWidget()
        self.variables_layout = QVBoxLayout(self.variables_widget)
        self.variables_layout.addStretch()
        
        scroll_area.setWidget(self.variables_widget)
        layout.addWidget(scroll_area)
        
        # 生成预览按钮
        preview_btn = QPushButton("🔄 生成预览")
        preview_btn.clicked.connect(self._generate_preview)
        layout.addWidget(preview_btn)
        
        return tab
    
    def _create_preview_tab(self) -> QWidget:
        """创建预览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.preview_widget = TemplatePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        return tab
    
    def _create_buttons(self):
        """创建按钮"""
        self.buttons_layout = QHBoxLayout()
        
        # 应用按钮
        self.apply_btn = QPushButton("✅ 应用模板")
        # 使用主题样式
        self.apply_btn.setStyleSheet("")
        self.apply_btn.clicked.connect(self._apply_template)
        self.apply_btn.setEnabled(False)
        self.buttons_layout.addWidget(self.apply_btn)
        
        self.buttons_layout.addStretch()
        
        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除")
        # 使用主题样式
        self.delete_btn.setStyleSheet("")
        self.delete_btn.clicked.connect(self._delete_template)
        self.delete_btn.setEnabled(False)
        self.buttons_layout.addWidget(self.delete_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.close_btn)
    
    def _apply_styles(self):
        """应用样式 - 使用主题管理器"""
        # 移除硬编码样式，使用主题管理器
        pass
    
    def _load_templates(self):
        """加载模板列表"""
        try:
            self.template_list.clear()
            templates = self.template_service.get_all_templates()
            
            for template in templates:
                item = QListWidgetItem()
                
                # 设置显示文本
                icon = "🔧" if not template.is_builtin else "📋"
                item.setText(f"{icon} {template.name}")
                item.setData(Qt.ItemDataRole.UserRole, template.id)
                
                # 设置工具提示
                item.setToolTip(f"{template.description}\n标签: {', '.join(template.tags)}")
                
                self.template_list.addItem(item)
            
            logger.info(f"模板列表加载完成，共 {len(templates)} 个模板")
            
        except Exception as e:
            logger.error(f"加载模板列表失败: {e}")
    
    def _filter_templates(self):
        """筛选模板"""
        try:
            category = self.category_combo.currentData()
            
            if category is None:
                templates = self.template_service.get_all_templates()
            else:
                templates = self.template_service.get_templates_by_category(category)
            
            self.template_list.clear()
            for template in templates:
                item = QListWidgetItem()
                icon = "🔧" if not template.is_builtin else "📋"
                item.setText(f"{icon} {template.name}")
                item.setData(Qt.ItemDataRole.UserRole, template.id)
                item.setToolTip(f"{template.description}\n标签: {', '.join(template.tags)}")
                self.template_list.addItem(item)
            
        except Exception as e:
            logger.error(f"筛选模板失败: {e}")
    
    def _search_templates(self):
        """搜索模板"""
        try:
            query = self.search_edit.text().strip()
            
            if not query:
                self._filter_templates()
                return
            
            templates = self.template_service.search_templates(query)
            
            self.template_list.clear()
            for template in templates:
                item = QListWidgetItem()
                icon = "🔧" if not template.is_builtin else "📋"
                item.setText(f"{icon} {template.name}")
                item.setData(Qt.ItemDataRole.UserRole, template.id)
                item.setToolTip(f"{template.description}\n标签: {', '.join(template.tags)}")
                self.template_list.addItem(item)
            
        except Exception as e:
            logger.error(f"搜索模板失败: {e}")
    
    def _on_template_selected(self, current, previous):
        """模板选择变化"""
        try:
            if not current:
                self.current_template = None
                self._clear_template_details()
                return
            
            template_id = current.data(Qt.ItemDataRole.UserRole)
            self.current_template = self.template_service.get_template(template_id)
            
            if self.current_template:
                self._update_template_details()
                self.apply_btn.setEnabled(True)
                self.delete_btn.setEnabled(not self.current_template.is_builtin)
            
        except Exception as e:
            logger.error(f"处理模板选择失败: {e}")
    
    def _update_template_details(self):
        """更新模板详情"""
        if not self.current_template:
            return
        
        try:
            # 更新信息标签页
            self.template_name_label.setText(self.current_template.name)
            self.template_description_label.setText(self.current_template.description)
            
            category_names = {
                TemplateCategory.NOVEL: "📖 小说",
                TemplateCategory.SHORT_STORY: "📄 短篇",
                TemplateCategory.ESSAY: "📝 散文",
                TemplateCategory.POETRY: "🎭 诗歌",
                TemplateCategory.SCRIPT: "🎬 剧本",
                TemplateCategory.CHARACTER: "👤 人物",
                TemplateCategory.SCENE: "🏞️ 场景",
                TemplateCategory.DIALOGUE: "💬 对话",
                TemplateCategory.OUTLINE: "📋 大纲",
                TemplateCategory.CUSTOM: "🔧 自定义"
            }
            self.template_category_label.setText(
                category_names.get(self.current_template.category, self.current_template.category.value)
            )
            
            self.template_author_label.setText(self.current_template.author)
            self.template_tags_label.setText(", ".join(self.current_template.tags))
            self.template_content_text.setPlainText(self.current_template.content)
            
            # 更新变量标签页
            self._update_variables_tab()
            
        except Exception as e:
            logger.error(f"更新模板详情失败: {e}")
    
    def _update_variables_tab(self):
        """更新变量标签页"""
        try:
            # 清空现有变量组件
            for widget in self.variable_widgets.values():
                widget.deleteLater()
            self.variable_widgets.clear()
            
            # 创建新的变量组件
            for variable in self.current_template.variables:
                widget = TemplateVariableWidget(variable)
                self.variable_widgets[variable.name] = widget
                
                # 插入到布局中（在stretch之前）
                self.variables_layout.insertWidget(
                    self.variables_layout.count() - 1, 
                    widget
                )
            
        except Exception as e:
            logger.error(f"更新变量标签页失败: {e}")
    
    def _clear_template_details(self):
        """清空模板详情"""
        self.template_name_label.setText("-")
        self.template_description_label.setText("-")
        self.template_category_label.setText("-")
        self.template_author_label.setText("-")
        self.template_tags_label.setText("-")
        self.template_content_text.clear()
        
        # 清空变量组件
        for widget in self.variable_widgets.values():
            widget.deleteLater()
        self.variable_widgets.clear()
        
        self.apply_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
    
    def _generate_preview(self):
        """生成预览"""
        try:
            if not self.current_template:
                return
            
            # 收集变量值
            variables = {}
            for var_name, widget in self.variable_widgets.items():
                variables[var_name] = widget.get_value()
            
            # 应用模板
            content = self.template_service.apply_template(self.current_template.id, variables)
            
            if content:
                self.preview_widget.update_preview(content)
                self.tab_widget.setCurrentIndex(2)  # 切换到预览标签页
            
        except Exception as e:
            logger.error(f"生成预览失败: {e}")
            QMessageBox.warning(self, "预览失败", f"生成预览失败: {e}")
    
    def _apply_template(self):
        """应用模板"""
        try:
            if not self.current_template:
                return
            
            # 收集变量值
            variables = {}
            for var_name, widget in self.variable_widgets.items():
                variables[var_name] = widget.get_value()
            
            # 验证必填变量
            for variable in self.current_template.variables:
                if variable.required and not variables.get(variable.name, "").strip():
                    QMessageBox.warning(self, "验证失败", f"请填写必填项: {variable.description}")
                    return
            
            # 应用模板
            content = self.template_service.apply_template(self.current_template.id, variables)
            
            if content:
                self.template_applied.emit(content)
                QMessageBox.information(self, "应用成功", "模板已应用到编辑器")
                self.close()
            else:
                QMessageBox.warning(self, "应用失败", "模板应用失败")
            
        except Exception as e:
            logger.error(f"应用模板失败: {e}")
            QMessageBox.critical(self, "应用失败", f"模板应用失败: {e}")
    
    def _create_new_template(self):
        """
        创建新模板

        打开新建模板对话框，允许用户创建自定义模板。
        """
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit, QComboBox, QPushButton, QDialogButtonBox

            dialog = QDialog(self)
            dialog.setWindowTitle("创建新模板")
            dialog.setModal(True)
            dialog.resize(500, 600)

            layout = QVBoxLayout(dialog)

            # 表单布局
            form_layout = QFormLayout()

            # 模板基本信息
            name_edit = QLineEdit()
            name_edit.setPlaceholderText("输入模板名称...")
            form_layout.addRow("模板名称:", name_edit)

            description_edit = QLineEdit()
            description_edit.setPlaceholderText("输入模板描述...")
            form_layout.addRow("模板描述:", description_edit)

            category_combo = QComboBox()
            category_combo.addItems(["小说", "散文", "诗歌", "剧本", "其他"])
            form_layout.addRow("模板类别:", category_combo)

            # 模板内容
            content_edit = QTextEdit()
            content_edit.setPlaceholderText("输入模板内容...\n\n可以使用以下变量：\n{title} - 文档标题\n{author} - 作者名称\n{date} - 当前日期\n{project_name} - 项目名称")
            content_edit.setMinimumHeight(300)
            form_layout.addRow("模板内容:", content_edit)

            layout.addLayout(form_layout)

            # 按钮
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 创建模板
                template_data = {
                    "name": name_edit.text().strip(),
                    "description": description_edit.text().strip(),
                    "category": category_combo.currentText(),
                    "content": content_edit.toPlainText(),
                    "variables": ["title", "author", "date", "project_name"],
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0"
                }

                if not template_data["name"]:
                    QMessageBox.warning(self, "创建失败", "请输入模板名称")
                    return

                if not template_data["content"]:
                    QMessageBox.warning(self, "创建失败", "请输入模板内容")
                    return

                # 保存模板
                success = self.template_service.create_template(template_data)
                if success:
                    self._load_templates()
                    QMessageBox.information(self, "创建成功", "模板创建成功")
                else:
                    QMessageBox.warning(self, "创建失败", "模板创建失败")

        except Exception as e:
            logger.error(f"创建新模板失败: {e}")
            QMessageBox.critical(self, "创建失败", f"模板创建失败: {e}")
    
    def _import_template(self):
        """导入模板"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "导入模板",
                "",
                "JSON文件 (*.json)"
            )
            
            if file_path:
                from pathlib import Path
                success = self.template_service.import_template(Path(file_path))
                if success:
                    self._load_templates()
                    QMessageBox.information(self, "导入成功", "模板导入成功")
                else:
                    QMessageBox.warning(self, "导入失败", "模板导入失败")
            
        except Exception as e:
            logger.error(f"导入模板失败: {e}")
            QMessageBox.critical(self, "导入失败", f"模板导入失败: {e}")
    
    def _export_template(self):
        """导出模板"""
        try:
            if not self.current_template:
                QMessageBox.warning(self, "导出失败", "请先选择要导出的模板")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出模板",
                f"{self.current_template.name}.json",
                "JSON文件 (*.json)"
            )
            
            if file_path:
                from pathlib import Path
                success = self.template_service.export_template(self.current_template.id, Path(file_path))
                if success:
                    QMessageBox.information(self, "导出成功", f"模板已导出到: {file_path}")
                else:
                    QMessageBox.warning(self, "导出失败", "模板导出失败")
            
        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            QMessageBox.critical(self, "导出失败", f"模板导出失败: {e}")
    
    def _delete_template(self):
        """删除模板"""
        try:
            if not self.current_template or self.current_template.is_builtin:
                return
            
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除模板 '{self.current_template.name}' 吗？\n此操作不可撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.template_service.delete_template(self.current_template.id)
                if success:
                    self._load_templates()
                    QMessageBox.information(self, "删除成功", "模板删除成功")
                else:
                    QMessageBox.warning(self, "删除失败", "模板删除失败")
            
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            QMessageBox.critical(self, "删除失败", f"模板删除失败: {e}")

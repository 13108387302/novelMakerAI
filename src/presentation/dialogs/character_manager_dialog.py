#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色管理对话框

提供完整的角色管理功能
"""

from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QLabel, QGroupBox, QTabWidget,
    QWidget, QMessageBox, QInputDialog, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.domain.entities.character import Character, CharacterRole, RelationshipType
from src.application.services.character_service import CharacterService
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class CharacterManagerDialog(QDialog):
    """角色管理对话框"""
    
    # 信号定义
    character_created = pyqtSignal(str)  # character_id
    character_updated = pyqtSignal(str)  # character_id
    character_deleted = pyqtSignal(str)  # character_id
    
    def __init__(self, character_service: CharacterService, parent=None):
        super().__init__(parent)
        self.character_service = character_service
        self.current_character: Optional[Character] = None
        self._setup_ui()
        self._setup_connections()
        self._load_characters()
        
        logger.debug("角色管理对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("角色管理")
        self.setModal(False)
        self.resize(900, 600)
        
        # 主布局
        layout = QHBoxLayout(self)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：角色列表
        self._create_character_list(splitter)
        
        # 右侧：角色详情
        self._create_character_details(splitter)
        
        # 设置分割器比例
        splitter.setSizes([300, 600])
    
    def _create_character_list(self, parent):
        """创建角色列表"""
        # 左侧容器
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 标题和按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("📚 角色列表")
        title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 新建按钮
        self.new_btn = QPushButton("➕ 新建")
        self.new_btn.clicked.connect(self._create_new_character)
        header_layout.addWidget(self.new_btn)
        
        left_layout.addLayout(header_layout)
        
        # 角色列表
        self.character_list = QListWidget()
        self.character_list.currentItemChanged.connect(self._on_character_selected)
        left_layout.addWidget(self.character_list)
        
        # 列表操作按钮
        list_buttons_layout = QHBoxLayout()
        
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.clicked.connect(self._delete_character)
        self.delete_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.delete_btn)
        
        list_buttons_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._load_characters)
        list_buttons_layout.addWidget(self.refresh_btn)
        
        left_layout.addLayout(list_buttons_layout)
        
        parent.addWidget(left_widget)
    
    def _create_character_details(self, parent):
        """创建角色详情"""
        # 右侧容器
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 标签页
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)
        
        # 基本信息标签页
        self._create_basic_info_tab()
        
        # 关系网络标签页
        self._create_relationships_tab()
        
        # 详细描述标签页
        self._create_description_tab()
        
        # 底部按钮
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save_character)
        self.save_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_btn)
        
        buttons_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)
        
        right_layout.addLayout(buttons_layout)
        
        parent.addWidget(right_widget)
    
    def _create_basic_info_tab(self):
        """创建基本信息标签页"""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # 基本信息
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._on_data_changed)
        layout.addRow("姓名:", self.name_edit)
        
        self.age_spin = QSpinBox()
        self.age_spin.setRange(0, 200)
        self.age_spin.valueChanged.connect(self._on_data_changed)
        layout.addRow("年龄:", self.age_spin)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value for role in CharacterRole])
        self.role_combo.currentTextChanged.connect(self._on_data_changed)
        layout.addRow("角色定位:", self.role_combo)
        
        self.gender_edit = QLineEdit()
        self.gender_edit.textChanged.connect(self._on_data_changed)
        layout.addRow("性别:", self.gender_edit)
        
        self.occupation_edit = QLineEdit()
        self.occupation_edit.textChanged.connect(self._on_data_changed)
        layout.addRow("职业:", self.occupation_edit)
        
        # 外貌特征
        self.appearance_edit = QTextEdit()
        self.appearance_edit.setMaximumHeight(100)
        self.appearance_edit.textChanged.connect(self._on_data_changed)
        layout.addRow("外貌特征:", self.appearance_edit)
        
        # 性格特点
        self.personality_edit = QTextEdit()
        self.personality_edit.setMaximumHeight(100)
        self.personality_edit.textChanged.connect(self._on_data_changed)
        layout.addRow("性格特点:", self.personality_edit)
        
        self.tab_widget.addTab(tab, "📋 基本信息")
    
    def _create_relationships_tab(self):
        """创建关系网络标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 关系列表
        relationships_group = QGroupBox("👥 角色关系")
        relationships_layout = QVBoxLayout(relationships_group)
        
        self.relationships_list = QListWidget()
        relationships_layout.addWidget(self.relationships_list)
        
        # 关系操作按钮
        rel_buttons_layout = QHBoxLayout()
        
        add_rel_btn = QPushButton("➕ 添加关系")
        add_rel_btn.clicked.connect(self._add_relationship)
        rel_buttons_layout.addWidget(add_rel_btn)
        
        edit_rel_btn = QPushButton("✏️ 编辑关系")
        edit_rel_btn.clicked.connect(self._edit_relationship)
        rel_buttons_layout.addWidget(edit_rel_btn)
        
        remove_rel_btn = QPushButton("🗑️ 删除关系")
        remove_rel_btn.clicked.connect(self._remove_relationship)
        rel_buttons_layout.addWidget(remove_rel_btn)
        
        rel_buttons_layout.addStretch()
        
        relationships_layout.addLayout(rel_buttons_layout)
        layout.addWidget(relationships_group)
        
        # 关系图可视化（占位）
        viz_group = QGroupBox("🕸️ 关系图")
        viz_layout = QVBoxLayout(viz_group)
        
        viz_placeholder = QLabel("关系图可视化功能开发中...")
        viz_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viz_placeholder.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
        viz_layout.addWidget(viz_placeholder)
        
        layout.addWidget(viz_group)
        
        self.tab_widget.addTab(tab, "🕸️ 关系网络")
    
    def _create_description_tab(self):
        """创建详细描述标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 背景故事
        background_group = QGroupBox("📖 背景故事")
        background_layout = QVBoxLayout(background_group)
        
        self.background_edit = QTextEdit()
        self.background_edit.textChanged.connect(self._on_data_changed)
        background_layout.addWidget(self.background_edit)
        
        layout.addWidget(background_group)
        
        # 角色目标
        goals_group = QGroupBox("🎯 角色目标")
        goals_layout = QVBoxLayout(goals_group)
        
        self.goals_edit = QTextEdit()
        self.goals_edit.textChanged.connect(self._on_data_changed)
        goals_layout.addWidget(self.goals_edit)
        
        layout.addWidget(goals_group)
        
        # 备注
        notes_group = QGroupBox("📝 备注")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.textChanged.connect(self._on_data_changed)
        notes_layout.addWidget(self.notes_edit)
        
        layout.addWidget(notes_group)
        
        self.tab_widget.addTab(tab, "📝 详细描述")
    
    def _setup_connections(self):
        """设置信号连接"""
        pass
    
    def _load_characters(self):
        """加载角色列表"""
        try:
            self.character_list.clear()
            # 这里需要从角色服务获取角色列表
            # characters = await self.character_service.get_all_characters()
            # 暂时使用空列表
            characters = []
            
            for character in characters:
                item = QListWidgetItem(f"👤 {character.name}")
                item.setData(Qt.ItemDataRole.UserRole, character.id)
                self.character_list.addItem(item)
                
        except Exception as e:
            logger.error(f"加载角色列表失败: {e}")
            QMessageBox.warning(self, "错误", f"加载角色列表失败: {str(e)}")
    
    def _on_character_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """角色选择变化"""
        if current:
            character_id = current.data(Qt.ItemDataRole.UserRole)
            self._load_character_details(character_id)
            self.delete_btn.setEnabled(True)
        else:
            self._clear_character_details()
            self.delete_btn.setEnabled(False)
    
    def _load_character_details(self, character_id: str):
        """加载角色详情"""
        try:
            # 这里需要从角色服务获取角色详情
            # character = await self.character_service.get_character(character_id)
            # 暂时创建一个示例角色
            character = None
            
            if character:
                self.current_character = character
                self._populate_character_form(character)
                self.save_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"加载角色详情失败: {e}")
            QMessageBox.warning(self, "错误", f"加载角色详情失败: {str(e)}")
    
    def _populate_character_form(self, character: Character):
        """填充角色表单"""
        self.name_edit.setText(character.name)
        self.age_spin.setValue(character.age or 0)
        self.role_combo.setCurrentText(character.role.value)
        self.gender_edit.setText(character.gender or "")
        self.occupation_edit.setText(character.occupation or "")
        self.appearance_edit.setPlainText(character.appearance or "")
        self.personality_edit.setPlainText(character.personality or "")
        self.background_edit.setPlainText(character.background or "")
        self.goals_edit.setPlainText(character.goals or "")
        self.notes_edit.setPlainText(character.notes or "")
        
        # 加载关系列表
        self._load_relationships()
    
    def _load_relationships(self):
        """加载关系列表"""
        self.relationships_list.clear()
        if self.current_character:
            relationships = self.current_character.get_relationships()
            for rel in relationships:
                item_text = f"{rel.relationship_type.value} - 强度: {rel.intensity}"
                if rel.description:
                    item_text += f" ({rel.description})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, rel)
                self.relationships_list.addItem(item)
    
    def _clear_character_details(self):
        """清空角色详情"""
        self.current_character = None
        self.name_edit.clear()
        self.age_spin.setValue(0)
        self.role_combo.setCurrentIndex(0)
        self.gender_edit.clear()
        self.occupation_edit.clear()
        self.appearance_edit.clear()
        self.personality_edit.clear()
        self.background_edit.clear()
        self.goals_edit.clear()
        self.notes_edit.clear()
        self.relationships_list.clear()
        self.save_btn.setEnabled(False)
    
    def _on_data_changed(self):
        """数据变化处理"""
        self.save_btn.setEnabled(True)
    
    def _create_new_character(self):
        """创建新角色"""
        name, ok = QInputDialog.getText(self, "新建角色", "角色姓名:")
        if ok and name.strip():
            try:
                # 创建新角色
                character = Character(
                    name=name.strip(),
                    role=CharacterRole.SUPPORTING
                )
                
                # 这里需要保存到角色服务
                # character_id = await self.character_service.create_character(character)
                
                # 刷新列表
                self._load_characters()
                
                # 发出信号
                # self.character_created.emit(character_id)
                
                QMessageBox.information(self, "成功", f"角色 '{name}' 创建成功！")
                
            except Exception as e:
                logger.error(f"创建角色失败: {e}")
                QMessageBox.warning(self, "错误", f"创建角色失败: {str(e)}")
    
    def _save_character(self):
        """保存角色"""
        if not self.current_character:
            return
        
        try:
            # 更新角色信息
            self.current_character.name = self.name_edit.text()
            self.current_character.age = self.age_spin.value() if self.age_spin.value() > 0 else None
            self.current_character.role = CharacterRole(self.role_combo.currentText())
            self.current_character.gender = self.gender_edit.text()
            self.current_character.occupation = self.occupation_edit.text()
            self.current_character.appearance = self.appearance_edit.toPlainText()
            self.current_character.personality = self.personality_edit.toPlainText()
            self.current_character.background = self.background_edit.toPlainText()
            self.current_character.goals = self.goals_edit.toPlainText()
            self.current_character.notes = self.notes_edit.toPlainText()
            
            # 保存到角色服务
            # await self.character_service.update_character(self.current_character)
            
            self.save_btn.setEnabled(False)
            self.character_updated.emit(self.current_character.id)
            
            QMessageBox.information(self, "成功", "角色信息保存成功！")
            
        except Exception as e:
            logger.error(f"保存角色失败: {e}")
            QMessageBox.warning(self, "错误", f"保存角色失败: {str(e)}")
    
    def _delete_character(self):
        """删除角色"""
        current_item = self.character_list.currentItem()
        if not current_item:
            return
        
        character_id = current_item.data(Qt.ItemDataRole.UserRole)
        character_name = current_item.text().replace("👤 ", "")
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除角色 '{character_name}' 吗？\n\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从角色服务删除
                # await self.character_service.delete_character(character_id)
                
                # 刷新列表
                self._load_characters()
                self._clear_character_details()
                
                # 发出信号
                self.character_deleted.emit(character_id)
                
                QMessageBox.information(self, "成功", f"角色 '{character_name}' 删除成功！")
                
            except Exception as e:
                logger.error(f"删除角色失败: {e}")
                QMessageBox.warning(self, "错误", f"删除角色失败: {str(e)}")
    
    def _add_relationship(self):
        """添加关系"""
        # TODO: 实现添加关系功能
        QMessageBox.information(self, "提示", "添加关系功能开发中...")
    
    def _edit_relationship(self):
        """编辑关系"""
        # TODO: 实现编辑关系功能
        QMessageBox.information(self, "提示", "编辑关系功能开发中...")
    
    def _remove_relationship(self):
        """删除关系"""
        # TODO: 实现删除关系功能
        QMessageBox.information(self, "提示", "删除关系功能开发中...")

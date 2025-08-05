#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目树组件

显示项目结构和文档层次
"""

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox,
    QInputDialog, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from src.domain.entities.project import Project
from src.domain.entities.document import Document, DocumentType
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ProjectTreeWidget(QTreeWidget):
    """项目树组件"""
    
    # 信号定义
    document_selected = pyqtSignal(str)  # 文档选择
    project_selected = pyqtSignal(str)   # 项目选择
    document_create_requested = pyqtSignal(str, str)  # 请求创建文档 (类型, 父项目ID)
    document_delete_requested = pyqtSignal(str)  # 请求删除文档
    document_rename_requested = pyqtSignal(str, str)  # 请求重命名文档
    document_copy_requested = pyqtSignal(str, str)  # 请求复制文档 (文档ID, 新名称)
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._setup_context_menu()
        self._current_project: Optional[Project] = None
        self._documents: list[Document] = []
        
        logger.debug("项目树组件初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        # 设置标题
        self.setHeaderLabel("📁 项目结构")
        
        # 设置选择模式
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        
        # 连接信号
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # 使用主题样式 - 移除硬编码的白色背景
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid;
                border-radius: 6px;
                font-size: 11pt;
                outline: none;
            }

            QTreeWidget::item {
                padding: 6px 4px;
                min-height: 24px;
            }

            QTreeWidget::branch {
                width: 16px;
            }
        """)
    
    def _setup_context_menu(self):
        """设置右键菜单"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def load_project(self, project: Project, documents: list[Document] = None):
        """加载项目到树中（性能优化版本）"""
        try:
            import time
            start_time = time.time()

            logger.info(f"🌳 项目树开始加载项目: {project.title}")
            logger.info(f"📄 文档数量: {len(documents) if documents else 0}")

            # 检查是否是重复加载同一个项目
            is_reload = (self._current_project and
                        self._current_project.id == project.id and
                        documents is not None and len(documents) > 0)

            if is_reload:
                logger.info(f"🔄 重新加载项目文档: {project.title}")
                # 只清理文档，保留项目结构
                self._clear_documents_only()
            else:
                # 完全重新加载项目结构
                self._load_project_structure_fast(project)

            # 如果有文档，延迟加载文档内容
            if documents:
                self._schedule_document_loading(documents)
            else:
                self._finalize_empty_project_loading()

            load_time = time.time() - start_time
            logger.info(f"⚡ 项目树加载完成: {project.title}, 耗时: {load_time:.3f}s")

        except Exception as e:
            logger.error(f"❌ 加载项目树失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    def _clear_documents_only(self):
        """只清理文档，保留项目结构"""
        try:
            if not self._category_items:
                return

            # 清理每个分类下的文档
            for category_item in self._category_items.values():
                # 移除所有子项（文档）
                while category_item.childCount() > 0:
                    category_item.removeChild(category_item.child(0))

                # 重置分类显示
                category_name = category_item.text(0).split(' (')[0]  # 移除计数
                category_item.setText(0, f"{category_name} (0)")
                category_item.setExpanded(False)

            self._documents = []
            logger.debug("🧹 已清理项目树中的文档")

        except Exception as e:
            logger.error(f"❌ 清理文档失败: {e}")

    def _load_project_structure_fast(self, project: Project):
        """快速加载项目基本结构"""
        try:
            self.clear()
            self._current_project = project
            self._documents = []

            # 创建项目根节点
            project_item = QTreeWidgetItem([f"📚 {project.title}"])
            project_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "project",
                "id": project.id,
                "object": project
            })
            self.addTopLevelItem(project_item)

            # 创建基本分类节点（不包含文档）
            categories = [
                (DocumentType.CHAPTER, "📖 章节"),
                (DocumentType.CHARACTER, "👥 角色"),
                (DocumentType.SETTING, "🌍 设定"),
                (DocumentType.OUTLINE, "📋 大纲"),
                (DocumentType.NOTE, "📝 笔记")
            ]

            self._category_items = {}
            for doc_type, category_name in categories:
                category_item = QTreeWidgetItem([f"{category_name} (加载中...)"])
                category_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "category",
                    "document_type": doc_type,
                    "project_id": project.id
                })
                project_item.addChild(category_item)
                self._category_items[doc_type] = category_item

            # 展开项目节点
            project_item.setExpanded(True)

            logger.debug(f"✅ 项目基本结构已创建: {project.title}")

        except Exception as e:
            logger.error(f"❌ 快速加载项目结构失败: {e}")

    def _schedule_document_loading(self, documents: list[Document]):
        """调度文档加载"""
        try:
            from PyQt6.QtCore import QTimer

            self._documents = documents

            # 分批加载文档，避免UI阻塞
            batch_size = 10  # 每批处理10个文档
            batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]

            logger.info(f"📦 将 {len(documents)} 个文档分为 {len(batches)} 批加载")

            def load_batch(batch_index):
                if batch_index < len(batches):
                    batch = batches[batch_index]
                    self._load_document_batch(batch)

                    # 调度下一批
                    if batch_index + 1 < len(batches):
                        QTimer.singleShot(10, lambda: load_batch(batch_index + 1))  # 10ms间隔
                    else:
                        # 所有批次完成
                        self._finalize_document_loading()

            # 开始加载第一批
            QTimer.singleShot(50, lambda: load_batch(0))  # 50ms延迟开始

        except Exception as e:
            logger.error(f"❌ 调度文档加载失败: {e}")

    def _load_document_batch(self, documents: list[Document]):
        """加载一批文档"""
        try:
            # 按类型分组
            categories = {
                DocumentType.CHAPTER: [],
                DocumentType.CHARACTER: [],
                DocumentType.SETTING: [],
                DocumentType.OUTLINE: [],
                DocumentType.NOTE: []
            }

            for document in documents:
                if document.type in categories:
                    categories[document.type].append(document)

            # 添加文档到对应分类
            for doc_type, docs in categories.items():
                if docs and doc_type in self._category_items:
                    category_item = self._category_items[doc_type]
                    for document in sorted(docs, key=lambda d: d.title):
                        self._add_document_item(category_item, document)

            logger.debug(f"✅ 已加载文档批次: {len(documents)} 个文档")

        except Exception as e:
            logger.error(f"❌ 加载文档批次失败: {e}")

    def _finalize_document_loading(self):
        """完成文档加载"""
        try:
            # 更新分类节点标题，显示实际文档数量
            categories = {
                DocumentType.CHAPTER: "📖 章节",
                DocumentType.CHARACTER: "👥 角色",
                DocumentType.SETTING: "🌍 设定",
                DocumentType.OUTLINE: "📋 大纲",
                DocumentType.NOTE: "📝 笔记"
            }

            expanded_categories = 0
            for doc_type, category_name in categories.items():
                if doc_type in self._category_items:
                    category_item = self._category_items[doc_type]
                    doc_count = category_item.childCount()
                    category_item.setText(0, f"{category_name} ({doc_count})")

                    # 展开有内容的分类
                    if doc_count > 0:
                        category_item.setExpanded(True)
                        expanded_categories += 1

            logger.info(f"✅ 项目树文档加载完成: {self._current_project.title}")
            logger.info(f"   📊 统计: {len(self._documents)} 个文档, {expanded_categories} 个分类展开")

        except Exception as e:
            logger.error(f"❌ 完成文档加载失败: {e}")

    def _finalize_empty_project_loading(self):
        """完成空项目加载"""
        try:
            # 更新分类节点标题，显示0个文档
            categories = {
                DocumentType.CHAPTER: "📖 章节",
                DocumentType.CHARACTER: "👥 角色",
                DocumentType.SETTING: "🌍 设定",
                DocumentType.OUTLINE: "📋 大纲",
                DocumentType.NOTE: "📝 笔记"
            }

            for doc_type, category_name in categories.items():
                if doc_type in self._category_items:
                    category_item = self._category_items[doc_type]
                    category_item.setText(0, f"{category_name} (0)")

            logger.info(f"✅ 空项目加载完成: {self._current_project.title}")

        except Exception as e:
            logger.error(f"❌ 完成空项目加载失败: {e}")
    
    def _add_document_item(self, parent_item: QTreeWidgetItem, document: Document):
        """添加文档项"""
        # 选择图标
        icons = {
            DocumentType.CHAPTER: "📄",
            DocumentType.CHARACTER: "👤",
            DocumentType.SETTING: "🏛️",
            DocumentType.OUTLINE: "📊",
            DocumentType.NOTE: "📝"
        }
        
        icon = icons.get(document.type, "📄")
        
        # 创建文档项
        doc_item = QTreeWidgetItem([f"{icon} {document.title}"])
        doc_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "document",
            "id": document.id,
            "object": document
        })
        
        # 添加状态指示
        try:
            if hasattr(document, 'statistics') and document.statistics.word_count > 0:
                doc_item.setText(0, f"{icon} {document.title} ({document.statistics.word_count} 字)")
        except AttributeError as e:
            logger.warning(f"文档统计信息访问失败: {e}, 文档: {document.title}")
            # 使用默认显示
            doc_item.setText(0, f"{icon} {document.title}")
        
        parent_item.addChild(doc_item)
        return doc_item
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """处理项目点击"""
        try:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                return
            
            if data["type"] == "document":
                self.document_selected.emit(data["id"])
            elif data["type"] == "project":
                self.project_selected.emit(data["id"])
                
        except Exception as e:
            logger.error(f"处理项目点击失败: {e}")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """处理双击事件"""
        try:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                return
            
            if data["type"] == "document":
                self.document_selected.emit(data["id"])
            elif data["type"] == "category":
                # 切换展开状态
                item.setExpanded(not item.isExpanded())
                
        except Exception as e:
            logger.error(f"处理双击事件失败: {e}")
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        try:
            item = self.itemAt(position)
            if not item:
                return
            
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data:
                return
            
            menu = QMenu(self)
            
            if data["type"] == "category":
                # 分类节点菜单
                self._create_category_menu(menu, data)
            elif data["type"] == "document":
                # 文档节点菜单
                self._create_document_menu(menu, data)
            elif data["type"] == "project":
                # 项目节点菜单
                self._create_project_menu(menu, data)
            
            if menu.actions():
                menu.exec(self.mapToGlobal(position))
                
        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}")
    
    def _create_category_menu(self, menu: QMenu, data: dict):
        """创建分类菜单"""
        doc_type = data["document_type"]
        project_id = data["project_id"]
        
        # 新建文档
        create_action = QAction(f"新建{self._get_document_type_name(doc_type)}", self)
        create_action.triggered.connect(
            lambda: self.document_create_requested.emit(doc_type.value, project_id)
        )
        menu.addAction(create_action)
    
    def _create_document_menu(self, menu: QMenu, data: dict):
        """创建文档菜单"""
        document_id = data["id"]
        
        # 打开
        open_action = QAction("打开", self)
        open_action.triggered.connect(lambda: self.document_selected.emit(document_id))
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        # 重命名
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self._rename_document(document_id))
        menu.addAction(rename_action)
        
        # 复制
        duplicate_action = QAction("复制", self)
        duplicate_action.triggered.connect(lambda: self._duplicate_document(document_id))
        menu.addAction(duplicate_action)
        
        menu.addSeparator()
        
        # 删除
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_document(document_id))
        menu.addAction(delete_action)
    
    def _create_project_menu(self, menu: QMenu, data: dict):
        """创建项目菜单"""
        # 项目属性
        properties_action = QAction("项目属性", self)
        properties_action.triggered.connect(self._show_project_properties)
        menu.addAction(properties_action)
        
        menu.addSeparator()
        
        # 刷新
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self._refresh_project)
        menu.addAction(refresh_action)
    
    def _get_document_type_name(self, doc_type: DocumentType) -> str:
        """获取文档类型名称"""
        names = {
            DocumentType.CHAPTER: "章节",
            DocumentType.CHARACTER: "角色",
            DocumentType.SETTING: "设定",
            DocumentType.OUTLINE: "大纲",
            DocumentType.NOTE: "笔记"
        }
        return names.get(doc_type, "文档")
    
    def _rename_document(self, document_id: str):
        """重命名文档"""
        try:
            # 找到对应的文档
            document = next((doc for doc in self._documents if doc.id == document_id), None)
            if not document:
                return
            
            new_name, ok = QInputDialog.getText(
                self,
                "重命名文档",
                "新名称:",
                text=document.title
            )
            
            if ok and new_name.strip():
                self.document_rename_requested.emit(document_id, new_name.strip())
                
        except Exception as e:
            logger.error(f"重命名文档失败: {e}")
    
    def _duplicate_document(self, document_id: str):
        """复制文档"""
        try:
            # 找到对应的文档
            document = next((doc for doc in self._documents if doc.id == document_id), None)
            if not document:
                return
            
            new_name, ok = QInputDialog.getText(
                self,
                "复制文档",
                "副本名称:",
                text=f"{document.title} - 副本"
            )
            
            if ok and new_name.strip():
                # 发出复制文档信号
                self.document_copy_requested.emit(document_id, new_name.strip())
                logger.info(f"请求复制文档: {document_id} -> {new_name}")
                
        except Exception as e:
            logger.error(f"复制文档失败: {e}")
    
    def _delete_document(self, document_id: str):
        """删除文档"""
        try:
            # 找到对应的文档
            document = next((doc for doc in self._documents if doc.id == document_id), None)
            if not document:
                return
            
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除文档 '{document.title}' 吗？\n\n此操作无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.document_delete_requested.emit(document_id)
                
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
    
    def _show_project_properties(self):
        """显示项目属性"""
        if self._current_project:
            try:
                from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QPushButton, QHBoxLayout

                # 创建项目属性对话框
                dialog = QDialog(self)
                dialog.setWindowTitle("项目属性")
                dialog.setModal(True)
                dialog.resize(400, 300)

                layout = QVBoxLayout(dialog)

                # 项目信息表单
                form_layout = QFormLayout()

                # 基本信息
                form_layout.addRow("项目名称:", QLabel(self._current_project.title))
                form_layout.addRow("项目类型:", QLabel(self._current_project.project_type.value))
                form_layout.addRow("项目状态:", QLabel(self._current_project.status.value))
                form_layout.addRow("作者:", QLabel(self._current_project.author or "未设置"))
                form_layout.addRow("描述:", QLabel(self._current_project.description or "无"))

                # 统计信息
                form_layout.addRow("总字数:", QLabel(str(self._current_project.statistics.total_words)))
                form_layout.addRow("总字符数:", QLabel(str(self._current_project.statistics.total_characters)))
                form_layout.addRow("目标字数:", QLabel(str(self._current_project.metadata.target_word_count)))
                form_layout.addRow("完成进度:", QLabel(f"{self._current_project.progress_percentage:.1f}%"))

                # 时间信息
                form_layout.addRow("创建时间:", QLabel(self._current_project.created_at.strftime('%Y-%m-%d %H:%M:%S')))
                form_layout.addRow("更新时间:", QLabel(self._current_project.updated_at.strftime('%Y-%m-%d %H:%M:%S')))
                if self._current_project.last_opened_at:
                    form_layout.addRow("最后打开:", QLabel(self._current_project.last_opened_at.strftime('%Y-%m-%d %H:%M:%S')))

                # 路径信息
                if self._current_project.root_path:
                    form_layout.addRow("项目路径:", QLabel(str(self._current_project.root_path)))

                layout.addLayout(form_layout)

                # 按钮
                button_layout = QHBoxLayout()
                close_btn = QPushButton("关闭")
                close_btn.clicked.connect(dialog.close)
                button_layout.addStretch()
                button_layout.addWidget(close_btn)
                layout.addLayout(button_layout)

                # 显示对话框
                dialog.exec()

            except Exception as e:
                logger.error(f"显示项目属性对话框失败: {e}")
                # 回退到简单消息框
                QMessageBox.information(
                    self,
                    "项目属性",
                    f"项目: {self._current_project.title}\n"
                    f"类型: {self._current_project.project_type.value}\n"
                    f"状态: {self._current_project.status.value}\n"
                    f"创建时间: {self._current_project.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"总字数: {self._current_project.statistics.total_words}"
                )
    
    def _refresh_project(self):
        """刷新项目"""
        if self._current_project:
            try:
                # 重新加载项目数据
                # 发出项目选择信号，让控制器重新加载项目
                self.project_selected.emit(self._current_project.id)

                # 清空当前树内容并重新构建
                self.clear()
                self.load_project(self._current_project, self._documents)

                logger.info(f"项目刷新完成: {self._current_project.title}")

            except Exception as e:
                logger.error(f"刷新项目失败: {e}")
                QMessageBox.warning(self, "刷新失败", f"刷新项目时发生错误：{e}")
    
    def add_document(self, document: Document):
        """添加新文档到树中（优化版本）"""
        try:
            logger.info(f"🌳 开始添加新文档到项目树: {document.title}")

            # 检查文档是否已存在
            if any(doc.id == document.id for doc in self._documents):
                logger.debug(f"文档已存在，跳过添加: {document.title}")
                return

            # 添加到文档列表
            self._documents.append(document)

            # 找到对应的分类节点
            category_found = False
            for i in range(self.topLevelItemCount()):
                project_item = self.topLevelItem(i)
                for j in range(project_item.childCount()):
                    category_item = project_item.child(j)
                    data = category_item.data(0, Qt.ItemDataRole.UserRole)

                    if (data and data["type"] == "category" and
                        data.get("document_type") == document.type):

                        # 添加文档项
                        self._add_document_item(category_item, document)

                        # 更新分类节点标题显示文档数量
                        doc_count = category_item.childCount()
                        category_name = self._get_category_name(document.type)
                        category_item.setText(0, f"{category_name} ({doc_count})")

                        # 展开分类节点
                        category_item.setExpanded(True)

                        category_found = True
                        logger.info(f"✅ 文档已添加到分类 {category_name}: {document.title}")
                        break

                if category_found:
                    break

            if not category_found:
                logger.warning(f"⚠️ 未找到文档类型对应的分类节点: {document.type}")

        except Exception as e:
            logger.error(f"❌ 添加文档到项目树失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _get_category_name(self, document_type: DocumentType) -> str:
        """获取分类名称"""
        category_names = {
            DocumentType.CHAPTER: "📖 章节",
            DocumentType.CHARACTER: "👥 角色",
            DocumentType.SETTING: "🌍 设定",
            DocumentType.OUTLINE: "📋 大纲",
            DocumentType.NOTE: "📝 笔记"
        }
        return category_names.get(document_type, "📄 其他")
    
    def remove_document(self, document_id: str):
        """从树中移除文档"""
        try:
            # 从文档列表中移除
            self._documents = [doc for doc in self._documents if doc.id != document_id]
            
            # 从树中移除
            for i in range(self.topLevelItemCount()):
                project_item = self.topLevelItem(i)
                for j in range(project_item.childCount()):
                    category_item = project_item.child(j)
                    for k in range(category_item.childCount()):
                        doc_item = category_item.child(k)
                        data = doc_item.data(0, Qt.ItemDataRole.UserRole)
                        
                        if data and data["type"] == "document" and data["id"] == document_id:
                            category_item.removeChild(doc_item)
                            logger.info(f"文档已从项目树移除: {document_id}")
                            return
                            
        except Exception as e:
            logger.error(f"从项目树移除文档失败: {e}")
    
    def update_document(self, document: Document):
        """更新文档显示"""
        try:
            # 更新文档列表
            for i, doc in enumerate(self._documents):
                if doc.id == document.id:
                    self._documents[i] = document
                    break
            
            # 更新树中的显示
            for i in range(self.topLevelItemCount()):
                project_item = self.topLevelItem(i)
                for j in range(project_item.childCount()):
                    category_item = project_item.child(j)
                    for k in range(category_item.childCount()):
                        doc_item = category_item.child(k)
                        data = doc_item.data(0, Qt.ItemDataRole.UserRole)
                        
                        if data and data["type"] == "document" and data["id"] == document.id:
                            # 更新显示文本
                            icon = {
                                DocumentType.CHAPTER: "📄",
                                DocumentType.CHARACTER: "👤",
                                DocumentType.SETTING: "🏛️",
                                DocumentType.OUTLINE: "📊",
                                DocumentType.NOTE: "📝"
                            }.get(document.type, "📄")
                            
                            try:
                                if hasattr(document, 'statistics') and document.statistics.word_count > 0:
                                    doc_item.setText(0, f"{icon} {document.title} ({document.statistics.word_count} 字)")
                                else:
                                    doc_item.setText(0, f"{icon} {document.title}")
                            except AttributeError as e:
                                logger.warning(f"文档统计信息访问失败: {e}, 文档: {document.title}")
                                doc_item.setText(0, f"{icon} {document.title}")
                            
                            # 更新数据
                            data["object"] = document
                            doc_item.setData(0, Qt.ItemDataRole.UserRole, data)
                            
                            logger.debug(f"文档显示已更新: {document.title}")
                            return
                            
        except Exception as e:
            logger.error(f"更新文档显示失败: {e}")

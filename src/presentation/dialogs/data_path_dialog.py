#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据路径选择对话框

允许用户选择数据存储路径
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class DataPathDialog(QDialog):
    """数据路径选择对话框"""
    
    path_selected = pyqtSignal(str)  # 路径选择信号
    
    def __init__(self, parent=None, current_path: Optional[Path] = None):
        super().__init__(parent)
        self.current_path = current_path
        self.selected_path: Optional[Path] = None
        
        self.setWindowTitle("选择数据存储路径")
        self.setModal(True)
        self.resize(600, 300)
        
        self._setup_ui()
        self._setup_connections()
        
        # 如果有当前路径，显示它
        if current_path:
            self.path_edit.setText(str(current_path))
    
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择数据存储路径")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文本
        info_label = QLabel(
            "请选择用于存储项目文件、文档和配置的目录。\n"
            "建议选择一个专门的文件夹，程序会在其中创建必要的子目录。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(info_label)
        
        # 路径选择区域
        path_layout = QHBoxLayout()
        
        path_label = QLabel("存储路径:")
        path_layout.addWidget(path_label)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择或输入数据存储路径...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.setFixedWidth(80)
        path_layout.addWidget(self.browse_button)
        
        layout.addLayout(path_layout)
        
        # 选项
        self.create_folder_checkbox = QCheckBox("如果目录不存在，自动创建")
        self.create_folder_checkbox.setChecked(True)
        layout.addWidget(self.create_folder_checkbox)
        
        # 预览信息
        preview_label = QLabel("将创建以下目录结构:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        layout.addWidget(preview_label)
        
        self.preview_text = QLabel()
        self.preview_text.setStyleSheet(
            "background-color: #f5f5f5; "
            "border: 1px solid #ddd; "
            "padding: 10px; "
            "font-family: monospace; "
            "margin-bottom: 20px;"
        )
        self.preview_text.setWordWrap(True)
        layout.addWidget(self.preview_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedWidth(80)
        button_layout.addWidget(self.cancel_button)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.setFixedWidth(80)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # 更新预览
        self._update_preview()
    
    def _setup_connections(self):
        """设置信号连接"""
        self.browse_button.clicked.connect(self._browse_path)
        self.path_edit.textChanged.connect(self._update_preview)
        self.ok_button.clicked.connect(self._accept)
        self.cancel_button.clicked.connect(self.reject)
    
    def _browse_path(self):
        """浏览路径"""
        try:
            current_path = self.path_edit.text() or str(Path.home())
            
            path = QFileDialog.getExistingDirectory(
                self,
                "选择数据存储目录",
                current_path
            )
            
            if path:
                self.path_edit.setText(path)
                
        except Exception as e:
            logger.error(f"浏览路径失败: {e}")
            QMessageBox.warning(self, "错误", f"浏览路径失败: {e}")
    
    def _update_preview(self):
        """更新预览信息"""
        try:
            path_text = self.path_edit.text().strip()
            if not path_text:
                self.preview_text.setText("请选择一个路径")
                return
            
            base_path = Path(path_text)
            
            preview = f"""
{base_path}/
├── projects/          # 项目文件
├── documents/         # 文档文件
├── cache/            # 缓存文件
├── logs/             # 日志文件
├── backups/          # 备份文件
├── exports/          # 导出文件
└── config.json       # 配置文件
            """.strip()
            
            self.preview_text.setText(preview)
            
        except Exception as e:
            self.preview_text.setText(f"路径预览失败: {e}")
    
    def _accept(self):
        """确认选择"""
        try:
            path_text = self.path_edit.text().strip()
            if not path_text:
                QMessageBox.warning(self, "警告", "请选择一个路径")
                return
            
            selected_path = Path(path_text)
            
            # 检查路径是否有效
            try:
                selected_path = selected_path.resolve()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无效的路径: {e}")
                return
            
            # 检查是否需要创建目录
            if not selected_path.exists():
                if self.create_folder_checkbox.isChecked():
                    try:
                        selected_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        QMessageBox.warning(self, "错误", f"无法创建目录: {e}")
                        return
                else:
                    QMessageBox.warning(self, "警告", "选择的目录不存在，请勾选自动创建选项或选择已存在的目录")
                    return
            
            # 检查是否有写入权限
            if not selected_path.is_dir():
                QMessageBox.warning(self, "错误", "选择的路径不是一个目录")
                return
            
            try:
                # 测试写入权限
                test_file = selected_path / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"没有写入权限: {e}")
                return
            
            self.selected_path = selected_path
            self.path_selected.emit(str(selected_path))
            self.accept()
            
        except Exception as e:
            logger.error(f"确认路径选择失败: {e}")
            QMessageBox.critical(self, "错误", f"确认路径选择失败: {e}")
    
    def get_selected_path(self) -> Optional[Path]:
        """获取选择的路径"""
        return self.selected_path


def show_data_path_dialog(parent=None, current_path: Optional[Path] = None) -> Optional[Path]:
    """显示数据路径选择对话框"""
    dialog = DataPathDialog(parent, current_path)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_path()
    return None

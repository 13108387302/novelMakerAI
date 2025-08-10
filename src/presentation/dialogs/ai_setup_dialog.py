#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务设置对话框

帮助用户配置AI服务，启用真实的AI辅助功能
"""

import os
import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QTabWidget,
    QWidget, QGroupBox, QComboBox, QCheckBox, QMessageBox,
    QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap

logger = logging.getLogger(__name__)

# AI设置对话框现在需要项目上下文


class AIConnectionTestWorker(QThread):
    """AI连接测试工作线程"""

    test_completed = pyqtSignal(str, bool, str)  # provider, success, message

    def __init__(self, provider: str, api_key: str, base_url: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url

    def run(self):
        """测试AI服务连接"""
        try:
            if self.provider == "openai":
                success, message = self._test_openai()
            elif self.provider == "deepseek":
                success, message = self._test_deepseek()
            else:
                success, message = False, "不支持的AI服务提供商"

            self.test_completed.emit(self.provider, success, message)

        except Exception as e:
            self.test_completed.emit(self.provider, False, f"测试失败: {str(e)}")

    def _test_openai(self):
        """测试OpenAI连接"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            # 发送一个简单的测试请求
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )

            if response.choices:
                return True, "OpenAI连接成功！"
            else:
                return False, "OpenAI响应为空"

        except Exception as e:
            return False, f"OpenAI连接失败: {str(e)}"

    def _test_deepseek(self):
        """测试DeepSeek连接"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            # 发送一个简单的测试请求
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )

            if response.choices:
                return True, "DeepSeek连接成功！"
            else:
                return False, "DeepSeek响应为空"

        except Exception as e:
            return False, f"DeepSeek连接失败: {str(e)}"


class AISetupDialog(QDialog):
    """AI服务设置对话框"""

    settings_updated = pyqtSignal()

    def __init__(self, parent=None, settings=None, settings_service=None):
        super().__init__(parent)
        # 可选注入 Settings 与 SettingsService
        self.settings = settings
        self.settings_service = settings_service
        self.test_worker = None

        self.setWindowTitle("AI服务设置 - 启用真实AI响应")
        self.setModal(True)
        self.resize(600, 500)

        self._setup_ui()
        # 优先从 SettingsService 载入，否则回退到 Settings
        self._load_current_settings()
        self._connect_signals()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题区域
        self._create_header(layout)

        # 主要内容
        self.tab_widget = QTabWidget()

        # OpenAI配置标签页
        self._create_openai_tab()

        # DeepSeek配置标签页
        self._create_deepseek_tab()

        # 高级设置标签页
        self._create_advanced_tab()

        layout.addWidget(self.tab_widget)

        # 按钮区域
        self._create_buttons(layout)

    def _create_header(self, layout):
        """创建头部"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QVBoxLayout(header_frame)

        # 标题
        title_label = QLabel("🤖 AI服务配置")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)

        # 说明
        desc_label = QLabel("配置真实的AI服务API密钥，启用完整的AI功能")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #666; font-style: italic;")
        header_layout.addWidget(desc_label)

        layout.addWidget(header_frame)

    def _create_openai_tab(self):
        """创建OpenAI配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # API密钥配置
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)

        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("sk-...")
        api_layout.addRow("API密钥:", self.openai_api_key)

        self.openai_base_url = QLineEdit()
        self.openai_base_url.setPlaceholderText("https://api.openai.com/v1")
        api_layout.addRow("基础URL:", self.openai_base_url)

        self.openai_model = QComboBox()
        self.openai_model.addItems([
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-4o"
        ])
        api_layout.addRow("模型:", self.openai_model)

        layout.addWidget(api_group)

        # 测试连接
        test_layout = QHBoxLayout()
        self.openai_test_btn = QPushButton("🔍 测试连接")
        self.openai_test_result = QLabel("未测试")
        test_layout.addWidget(self.openai_test_btn)
        test_layout.addWidget(self.openai_test_result)
        test_layout.addStretch()
        layout.addLayout(test_layout)

        # 获取API密钥说明
        help_group = QGroupBox("如何获取API密钥")
        help_layout = QVBoxLayout(help_group)

        help_text = QTextEdit()
        help_text.setMaximumHeight(100)
        help_text.setHtml("""
        <p>1. 访问 <a href="https://platform.openai.com/api-keys">OpenAI API Keys</a></p>
        <p>2. 登录你的OpenAI账户</p>
        <p>3. 点击 "Create new secret key"</p>
        <p>4. 复制生成的API密钥并粘贴到上方</p>
        """)
        help_text.setReadOnly(True)
        help_layout.addWidget(help_text)

        layout.addWidget(help_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "🔵 OpenAI")

    def _create_deepseek_tab(self):
        """创建DeepSeek配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # API密钥配置
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)

        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_api_key.setPlaceholderText("sk-...")
        api_layout.addRow("API密钥:", self.deepseek_api_key)

        self.deepseek_base_url = QLineEdit()
        self.deepseek_base_url.setPlaceholderText("https://api.deepseek.com/v1")
        api_layout.addRow("基础URL:", self.deepseek_base_url)

        self.deepseek_model = QComboBox()
        self.deepseek_model.addItems([
            "deepseek-chat",
            "deepseek-coder"
        ])
        api_layout.addRow("模型:", self.deepseek_model)

        layout.addWidget(api_group)

        # 测试连接
        test_layout = QHBoxLayout()
        self.deepseek_test_btn = QPushButton("🔍 测试连接")
        self.deepseek_test_result = QLabel("未测试")
        test_layout.addWidget(self.deepseek_test_btn)
        test_layout.addWidget(self.deepseek_test_result)
        test_layout.addStretch()
        layout.addLayout(test_layout)

        # 获取API密钥说明
        help_group = QGroupBox("如何获取API密钥")
        help_layout = QVBoxLayout(help_group)

        help_text = QTextEdit()
        help_text.setMaximumHeight(100)
        help_text.setHtml("""
        <p>1. 访问 <a href="https://platform.deepseek.com/api_keys">DeepSeek API Keys</a></p>
        <p>2. 登录你的DeepSeek账户</p>
        <p>3. 点击 "创建API密钥"</p>
        <p>4. 复制生成的API密钥并粘贴到上方</p>
        """)
        help_text.setReadOnly(True)
        help_layout.addWidget(help_text)

        layout.addWidget(help_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "🟢 DeepSeek")

    def _create_advanced_tab(self):
        """创建高级设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 通用设置
        general_group = QGroupBox("通用设置")
        general_layout = QFormLayout(general_group)

        self.default_provider = QComboBox()
        self.default_provider.addItems(["openai", "deepseek"])
        general_layout.addRow("默认提供商:", self.default_provider)

        self.max_tokens = QLineEdit()
        self.max_tokens.setPlaceholderText("2000")
        general_layout.addRow("最大Token数:", self.max_tokens)

        self.temperature = QLineEdit()
        self.temperature.setPlaceholderText("0.7")
        general_layout.addRow("生成温度:", self.temperature)

        self.timeout = QLineEdit()
        self.timeout.setPlaceholderText("30")
        general_layout.addRow("超时时间(秒):", self.timeout)

        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout(output_group)

        self.enable_streaming = QCheckBox("启用流式输出")
        self.enable_streaming.setToolTip("启用后，AI响应将实时显示，提供更好的用户体验")
        output_layout.addRow("", self.enable_streaming)

        layout.addWidget(general_group)
        layout.addWidget(output_group)

        # 环境变量设置
        env_group = QGroupBox("环境变量设置")
        env_layout = QVBoxLayout(env_group)

        env_info = QLabel("你也可以通过环境变量配置AI服务：")
        env_layout.addWidget(env_info)

        env_text = QTextEdit()
        env_text.setMaximumHeight(150)
        env_text.setPlainText("""
# 在 .env 文件中设置：
AI_OPENAI_API_KEY=your-openai-key
AI_DEEPSEEK_API_KEY=your-deepseek-key
AI_DEFAULT_PROVIDER=openai
        """.strip())
        env_text.setReadOnly(True)
        env_layout.addWidget(env_text)

        layout.addWidget(env_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "⚙️ 高级设置")

    def _create_buttons(self, layout):
        """创建按钮"""
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("💾 保存设置")
        self.save_btn.setDefault(True)

        self.cancel_btn = QPushButton("❌ 取消")

        self.test_all_btn = QPushButton("🧪 测试所有连接")

        button_layout.addWidget(self.test_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _load_current_settings(self):
        """加载当前设置（仅通过 SettingsService）"""
        try:
            if self.settings_service is None:
                logger.warning("AI设置对话框缺少 SettingsService，上下文为空")
                return
            ss = self.settings_service
            get = ss.get
            self.openai_api_key.setText(get('ai.openai_api_key') or "")
            self.openai_base_url.setText(get('ai.openai_base_url', 'https://api.openai.com/v1'))
            self.openai_model.setCurrentText(get('ai.openai_model', 'gpt-3.5-turbo'))

            self.deepseek_api_key.setText(get('ai.deepseek_api_key') or "")
            self.deepseek_base_url.setText(get('ai.deepseek_base_url', 'https://api.deepseek.com/v1'))
            self.deepseek_model.setCurrentText(get('ai.deepseek_model', 'deepseek-chat'))

            self.default_provider.setCurrentText(get('ai.default_provider', 'deepseek'))
            self.max_tokens.setText(str(get('ai.max_tokens', 2000)))
            self.temperature.setText(str(get('ai.temperature', 0.7)))
            self.timeout.setText(str(get('ai.timeout', 30)))
            self.enable_streaming.setChecked(bool(get('ai.enable_streaming', True)))
        except Exception as e:
            logger.warning(f"AI设置加载出现异常: {e}")

    def _connect_signals(self):
        """连接信号"""
        self.save_btn.clicked.connect(self._save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        self.test_all_btn.clicked.connect(self._test_all_connections)

        self.openai_test_btn.clicked.connect(lambda: self._test_connection("openai"))
        self.deepseek_test_btn.clicked.connect(lambda: self._test_connection("deepseek"))

    def _test_connection(self, provider: str):
        """测试单个连接"""
        if provider == "openai":
            api_key = self.openai_api_key.text().strip()
            base_url = self.openai_base_url.text().strip()
            result_label = self.openai_test_result
        else:
            api_key = self.deepseek_api_key.text().strip()
            base_url = self.deepseek_base_url.text().strip()
            result_label = self.deepseek_test_result

        if not api_key:
            result_label.setText("❌ 请先输入API密钥")
            result_label.setStyleSheet("color: red;")
            return

        result_label.setText("🔄 测试中...")
        result_label.setStyleSheet("color: blue;")

        self.test_worker = AIConnectionTestWorker(provider, api_key, base_url)
        self.test_worker.test_completed.connect(self._on_test_completed)
        self.test_worker.start()

    def _test_all_connections(self):
        """测试所有连接"""
        if self.openai_api_key.text().strip():
            self._test_connection("openai")

        if self.deepseek_api_key.text().strip():
            self._test_connection("deepseek")

    def _on_test_completed(self, provider: str, success: bool, message: str):
        """测试完成回调"""
        if provider == "openai":
            result_label = self.openai_test_result
        else:
            result_label = self.deepseek_test_result

        if success:
            result_label.setText(f"✅ {message}")
            result_label.setStyleSheet("color: green;")
        else:
            result_label.setText(f"❌ {message}")
            result_label.setStyleSheet("color: red;")

    def _save_settings(self):
        """保存设置（仅通过 SettingsService）"""
        try:
            if self.settings_service is None:
                QMessageBox.warning(self, "无法保存", "缺少设置服务（SettingsService），请重启应用或检查项目上下文。")
                return

            ss = self.settings_service
            updates = {
                'openai_api_key': self.openai_api_key.text().strip() or None,
                'openai_base_url': self.openai_base_url.text().strip(),
                'openai_model': self.openai_model.currentText(),
                'deepseek_api_key': self.deepseek_api_key.text().strip() or None,
                'deepseek_base_url': self.deepseek_base_url.text().strip(),
                'deepseek_model': self.deepseek_model.currentText(),
                'default_provider': self.default_provider.currentText(),
                'max_tokens': int(self.max_tokens.text() or '2000'),
                'temperature': float(self.temperature.text() or '0.7'),
                'timeout': int(self.timeout.text() or '30'),
                'enable_streaming': self.enable_streaming.isChecked(),
            }
            try:
                ss.update_ai_settings(updates)
            except Exception:
                for k, v in updates.items():
                    ss.set_setting(f"ai.{k}", v)

            # 发射更新信号并提示
            self.settings_updated.emit()
            QMessageBox.information(self, "成功", "AI服务设置已保存并立即生效！")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败：{str(e)}")

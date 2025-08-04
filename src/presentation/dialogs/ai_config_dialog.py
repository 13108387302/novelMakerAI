#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI配置对话框

专门用于配置AI服务的对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QGridLayout, QLabel, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QSlider, QCheckBox, QPushButton,
    QTextEdit, QMessageBox, QProgressBar, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QIcon

from config.settings import Settings
from src.application.services.settings_service import SettingsService
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class AITestWorker(QThread):
    """AI连接测试工作线程"""
    
    test_completed = pyqtSignal(bool, str)  # 成功/失败, 消息
    
    def __init__(self, provider: str, config: dict):
        super().__init__()
        self.provider = provider
        self.config = config
    
    def run(self):
        """运行连接测试"""
        try:
            import asyncio
            
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行测试
            result = loop.run_until_complete(self._test_connection())
            loop.close()
            
            if result:
                self.test_completed.emit(True, "连接测试成功！AI服务正常工作。")
            else:
                self.test_completed.emit(False, "连接测试失败，请检查配置。")
                
        except Exception as e:
            self.test_completed.emit(False, f"连接测试出错: {str(e)}")
    
    async def _test_connection(self):
        """测试AI连接"""
        try:
            if self.provider.lower() == "openai":
                return await self._test_openai()
            elif self.provider.lower() == "deepseek":
                return await self._test_deepseek()
            else:
                return False
        except Exception as e:
            logger.error(f"AI连接测试失败: {e}")
            return False
    
    async def _test_openai(self):
        """测试OpenAI连接"""
        try:
            import openai

            # 验证API密钥格式
            api_key = self.config.get("api_key", "").strip()
            if not api_key:
                logger.error("OpenAI API密钥为空")
                return False

            if not api_key.startswith("sk-"):
                logger.error("OpenAI API密钥格式不正确")
                return False

            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=self.config.get("base_url", "https://api.openai.com/v1"),
                timeout=10.0  # 设置超时
            )

            response = await client.chat.completions.create(
                model=self.config.get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0.1
            )

            return bool(response.choices and len(response.choices) > 0)

        except Exception as e:
            logger.error(f"OpenAI测试失败: {e}")
            return False
    
    async def _test_deepseek(self):
        """测试DeepSeek连接"""
        try:
            import openai

            # 验证API密钥格式
            api_key = self.config.get("api_key", "").strip()
            if not api_key:
                logger.error("DeepSeek API密钥为空")
                return False

            if not api_key.startswith("sk-"):
                logger.error("DeepSeek API密钥格式不正确")
                return False

            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=self.config.get("base_url", "https://api.deepseek.com/v1"),
                timeout=10.0  # 设置超时
            )

            response = await client.chat.completions.create(
                model=self.config.get("model", "deepseek-chat"),
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0.1
            )

            return bool(response.choices and len(response.choices) > 0)

        except Exception as e:
            logger.error(f"DeepSeek测试失败: {e}")
            return False


class AIConfigDialog(QDialog):
    """AI配置对话框"""
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, settings_service: SettingsService, parent=None):
        super().__init__(parent)
        self.settings_service = settings_service
        self.test_worker = None
        
        self._setup_ui()
        self._load_current_settings()
        self._setup_connections()
        
        logger.info("AI配置对话框初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("AI助手配置")
        self.setFixedSize(600, 700)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("🤖 AI助手配置")
        title_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("padding: 10px; color: #2196F3;")
        layout.addWidget(title_label)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # OpenAI配置标签页
        self._create_openai_tab()
        
        # DeepSeek配置标签页
        self._create_deepseek_tab()
        
        # 通用设置标签页
        self._create_general_tab()
        
        # 高级设置标签页
        self._create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Shape.Box)
        status_layout = QHBoxLayout(self.status_frame)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(6)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.status_frame)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("🔍 测试连接")
        self.test_btn.clicked.connect(self._test_connection)
        button_layout.addWidget(self.test_btn)
        
        button_layout.addStretch()
        
        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.clicked.connect(self._reset_settings)
        button_layout.addWidget(self.reset_btn)
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save_settings)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _create_openai_tab(self):
        """创建OpenAI配置标签页"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # OpenAI基本配置
        basic_group = QGroupBox("🔑 基本配置")
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("API密钥:"), 0, 0)
        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key_edit.setPlaceholderText("sk-...")
        basic_layout.addWidget(self.openai_api_key_edit, 0, 1)
        
        basic_layout.addWidget(QLabel("API基础URL:"), 1, 0)
        self.openai_base_url_edit = QLineEdit()
        self.openai_base_url_edit.setText("https://api.openai.com/v1")
        basic_layout.addWidget(self.openai_base_url_edit, 1, 1)
        
        basic_layout.addWidget(QLabel("模型:"), 2, 0)
        self.openai_model_combo = QComboBox()
        self.openai_model_combo.addItems([
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o"
        ])
        basic_layout.addWidget(self.openai_model_combo, 2, 1)
        
        layout.addWidget(basic_group)
        
        # OpenAI高级配置
        advanced_group = QGroupBox("⚙️ 高级配置")
        advanced_layout = QGridLayout(advanced_group)
        
        advanced_layout.addWidget(QLabel("最大Token数:"), 0, 0)
        self.openai_max_tokens_spin = QSpinBox()
        self.openai_max_tokens_spin.setRange(100, 8000)
        self.openai_max_tokens_spin.setValue(2000)
        advanced_layout.addWidget(self.openai_max_tokens_spin, 0, 1)
        
        advanced_layout.addWidget(QLabel("创造性 (Temperature):"), 1, 0)
        temp_layout = QHBoxLayout()
        self.openai_temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.openai_temperature_slider.setRange(0, 200)
        self.openai_temperature_slider.setValue(70)
        self.openai_temperature_label = QLabel("0.7")
        temp_layout.addWidget(self.openai_temperature_slider)
        temp_layout.addWidget(self.openai_temperature_label)
        advanced_layout.addLayout(temp_layout, 1, 1)
        
        advanced_layout.addWidget(QLabel("请求超时(秒):"), 2, 0)
        self.openai_timeout_spin = QSpinBox()
        self.openai_timeout_spin.setRange(5, 120)
        self.openai_timeout_spin.setValue(30)
        advanced_layout.addWidget(self.openai_timeout_spin, 2, 1)
        
        layout.addWidget(advanced_group)

        layout.addStretch()

        # 将内容设置到滚动区域
        scroll_area.setWidget(tab)
        self.tab_widget.addTab(scroll_area, "🔵 OpenAI")
    
    def _create_deepseek_tab(self):
        """创建DeepSeek配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # DeepSeek基本配置
        basic_group = QGroupBox("🔑 基本配置")
        basic_layout = QGridLayout(basic_group)
        
        basic_layout.addWidget(QLabel("API密钥:"), 0, 0)
        self.deepseek_api_key_edit = QLineEdit()
        self.deepseek_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_api_key_edit.setPlaceholderText("sk-...")
        basic_layout.addWidget(self.deepseek_api_key_edit, 0, 1)
        
        basic_layout.addWidget(QLabel("API基础URL:"), 1, 0)
        self.deepseek_base_url_edit = QLineEdit()
        self.deepseek_base_url_edit.setText("https://api.deepseek.com/v1")
        basic_layout.addWidget(self.deepseek_base_url_edit, 1, 1)
        
        basic_layout.addWidget(QLabel("模型:"), 2, 0)
        self.deepseek_model_combo = QComboBox()
        self.deepseek_model_combo.addItems([
            "deepseek-chat",
            "deepseek-coder"
        ])
        basic_layout.addWidget(self.deepseek_model_combo, 2, 1)
        
        layout.addWidget(basic_group)
        
        # DeepSeek高级配置
        advanced_group = QGroupBox("⚙️ 高级配置")
        advanced_layout = QGridLayout(advanced_group)
        
        advanced_layout.addWidget(QLabel("最大Token数:"), 0, 0)
        self.deepseek_max_tokens_spin = QSpinBox()
        self.deepseek_max_tokens_spin.setRange(100, 8000)
        self.deepseek_max_tokens_spin.setValue(2000)
        advanced_layout.addWidget(self.deepseek_max_tokens_spin, 0, 1)
        
        advanced_layout.addWidget(QLabel("创造性 (Temperature):"), 1, 0)
        temp_layout = QHBoxLayout()
        self.deepseek_temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.deepseek_temperature_slider.setRange(0, 200)
        self.deepseek_temperature_slider.setValue(70)
        self.deepseek_temperature_label = QLabel("0.7")
        temp_layout.addWidget(self.deepseek_temperature_slider)
        temp_layout.addWidget(self.deepseek_temperature_label)
        advanced_layout.addLayout(temp_layout, 1, 1)
        
        advanced_layout.addWidget(QLabel("请求超时(秒):"), 2, 0)
        self.deepseek_timeout_spin = QSpinBox()
        self.deepseek_timeout_spin.setRange(5, 120)
        self.deepseek_timeout_spin.setValue(30)
        advanced_layout.addWidget(self.deepseek_timeout_spin, 2, 1)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "🟢 DeepSeek")
    
    def _create_general_tab(self):
        """创建通用设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 默认提供商
        provider_group = QGroupBox("🎯 默认设置")
        provider_layout = QGridLayout(provider_group)
        
        provider_layout.addWidget(QLabel("默认AI提供商:"), 0, 0)
        self.default_provider_combo = QComboBox()
        self.default_provider_combo.addItems(["OpenAI", "DeepSeek"])
        provider_layout.addWidget(self.default_provider_combo, 0, 1)
        
        provider_layout.addWidget(QLabel("重试次数:"), 1, 0)
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(1, 10)
        self.retry_count_spin.setValue(3)
        provider_layout.addWidget(self.retry_count_spin, 1, 1)
        
        layout.addWidget(provider_group)
        
        # AI功能设置
        features_group = QGroupBox("🚀 功能设置")
        features_layout = QVBoxLayout(features_group)
        
        self.auto_suggestions_check = QCheckBox("启用自动建议")
        self.auto_suggestions_check.setChecked(True)
        features_layout.addWidget(self.auto_suggestions_check)
        
        self.cache_responses_check = QCheckBox("缓存AI响应")
        self.cache_responses_check.setChecked(True)
        features_layout.addWidget(self.cache_responses_check)
        
        self.stream_mode_check = QCheckBox("启用流式输出")
        self.stream_mode_check.setChecked(True)
        features_layout.addWidget(self.stream_mode_check)
        
        layout.addWidget(features_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "⚙️ 通用")
    
    def _create_advanced_tab(self):
        """创建高级设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 性能设置
        performance_group = QGroupBox("⚡ 性能设置")
        performance_layout = QGridLayout(performance_group)
        
        performance_layout.addWidget(QLabel("并发请求数:"), 0, 0)
        self.concurrent_requests_spin = QSpinBox()
        self.concurrent_requests_spin.setRange(1, 10)
        self.concurrent_requests_spin.setValue(3)
        performance_layout.addWidget(self.concurrent_requests_spin, 0, 1)
        
        performance_layout.addWidget(QLabel("请求间隔(毫秒):"), 1, 0)
        self.request_interval_spin = QSpinBox()
        self.request_interval_spin.setRange(0, 5000)
        self.request_interval_spin.setValue(100)
        performance_layout.addWidget(self.request_interval_spin, 1, 1)
        
        layout.addWidget(performance_group)
        
        # 调试设置
        debug_group = QGroupBox("🐛 调试设置")
        debug_layout = QVBoxLayout(debug_group)
        
        self.debug_mode_check = QCheckBox("启用调试模式")
        debug_layout.addWidget(self.debug_mode_check)
        
        self.log_requests_check = QCheckBox("记录AI请求日志")
        debug_layout.addWidget(self.log_requests_check)
        
        self.show_tokens_check = QCheckBox("显示Token使用情况")
        debug_layout.addWidget(self.show_tokens_check)
        
        layout.addWidget(debug_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "🔧 高级")
    
    def _setup_connections(self):
        """设置信号连接"""
        # 温度滑块连接
        self.openai_temperature_slider.valueChanged.connect(
            lambda v: self.openai_temperature_label.setText(f"{v/100:.1f}")
        )
        self.deepseek_temperature_slider.valueChanged.connect(
            lambda v: self.deepseek_temperature_label.setText(f"{v/100:.1f}")
        )
    
    def _load_current_settings(self):
        """加载当前设置"""
        try:
            # 加载OpenAI设置
            self.openai_api_key_edit.setText(
                self.settings_service.get_setting("ai.openai_api_key", "")
            )
            self.openai_base_url_edit.setText(
                self.settings_service.get_setting("ai.openai_base_url", "https://api.openai.com/v1")
            )
            self.openai_model_combo.setCurrentText(
                self.settings_service.get_setting("ai.openai_model", "gpt-3.5-turbo")
            )
            
            # 加载DeepSeek设置
            self.deepseek_api_key_edit.setText(
                self.settings_service.get_setting("ai.deepseek_api_key", "")
            )
            self.deepseek_base_url_edit.setText(
                self.settings_service.get_setting("ai.deepseek_base_url", "https://api.deepseek.com/v1")
            )
            
            # 加载通用设置
            default_provider = self.settings_service.get_setting("ai.default_provider", "openai")
            if default_provider.lower() == "openai":
                self.default_provider_combo.setCurrentText("OpenAI")
            else:
                self.default_provider_combo.setCurrentText("DeepSeek")
            
            # 加载其他设置
            self.openai_max_tokens_spin.setValue(
                self.settings_service.get_setting("ai.max_tokens", 2000)
            )
            temperature = self.settings_service.get_setting("ai.temperature", 0.7)
            self.openai_temperature_slider.setValue(int(temperature * 100))
            
            logger.info("AI配置加载完成")
            
        except Exception as e:
            logger.error(f"加载AI配置失败: {e}")
    
    def _save_settings(self):
        """保存设置"""
        try:
            # 保存OpenAI设置
            self.settings_service.set_setting("ai.openai_api_key", self.openai_api_key_edit.text())
            self.settings_service.set_setting("ai.openai_base_url", self.openai_base_url_edit.text())
            self.settings_service.set_setting("ai.openai_model", self.openai_model_combo.currentText())
            
            # 保存DeepSeek设置
            self.settings_service.set_setting("ai.deepseek_api_key", self.deepseek_api_key_edit.text())
            self.settings_service.set_setting("ai.deepseek_base_url", self.deepseek_base_url_edit.text())
            self.settings_service.set_setting("ai.deepseek_model", self.deepseek_model_combo.currentText())
            
            # 保存通用设置
            provider = "openai" if self.default_provider_combo.currentText() == "OpenAI" else "deepseek"
            self.settings_service.set_setting("ai.default_provider", provider)
            
            # 保存参数设置
            self.settings_service.set_setting("ai.max_tokens", self.openai_max_tokens_spin.value())
            self.settings_service.set_setting("ai.temperature", self.openai_temperature_slider.value() / 100.0)
            self.settings_service.set_setting("ai.timeout", self.openai_timeout_spin.value())
            self.settings_service.set_setting("ai.retry_count", self.retry_count_spin.value())
            
            # 保存功能设置
            self.settings_service.set_setting("ai.auto_suggestions", self.auto_suggestions_check.isChecked())
            self.settings_service.set_setting("ai.cache_responses", self.cache_responses_check.isChecked())
            self.settings_service.set_setting("ai.stream_mode", self.stream_mode_check.isChecked())
            
            self.config_changed.emit()
            
            QMessageBox.information(self, "保存成功", "AI配置已保存成功！")
            self.accept()
            
        except Exception as e:
            logger.error(f"保存AI配置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存AI配置失败：{str(e)}")
    
    def _reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置所有AI配置到默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 重置为默认值
            self.openai_api_key_edit.clear()
            self.openai_base_url_edit.setText("https://api.openai.com/v1")
            self.openai_model_combo.setCurrentText("gpt-3.5-turbo")
            self.deepseek_api_key_edit.clear()
            self.deepseek_base_url_edit.setText("https://api.deepseek.com/v1")
            self.default_provider_combo.setCurrentText("OpenAI")
            self.openai_max_tokens_spin.setValue(2000)
            self.openai_temperature_slider.setValue(70)
            self.openai_timeout_spin.setValue(30)
            self.retry_count_spin.setValue(3)
            
            logger.info("AI配置已重置")
    
    def _test_connection(self):
        """测试AI连接"""
        try:
            # 获取当前选择的提供商
            provider = self.default_provider_combo.currentText().lower()
            
            if provider == "openai":
                config = {
                    "api_key": self.openai_api_key_edit.text(),
                    "base_url": self.openai_base_url_edit.text(),
                    "model": self.openai_model_combo.currentText()
                }
                if not config["api_key"]:
                    QMessageBox.warning(self, "配置错误", "请先输入OpenAI API密钥")
                    return
            else:
                config = {
                    "api_key": self.deepseek_api_key_edit.text(),
                    "base_url": self.deepseek_base_url_edit.text(),
                    "model": self.deepseek_model_combo.currentText()
                }
                if not config["api_key"]:
                    QMessageBox.warning(self, "配置错误", "请先输入DeepSeek API密钥")
                    return
            
            # 开始测试
            self.status_label.setText("正在测试连接...")
            self.status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.test_btn.setEnabled(False)
            
            # 创建测试工作线程
            self.test_worker = AITestWorker(provider, config)
            self.test_worker.test_completed.connect(self._on_test_completed)
            self.test_worker.start()
            
        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            QMessageBox.critical(self, "测试失败", f"测试连接时出错：{str(e)}")
    
    def _on_test_completed(self, success: bool, message: str):
        """测试完成回调"""
        self.progress_bar.setVisible(False)
        self.test_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("连接测试成功")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            QMessageBox.information(self, "测试成功", message)
        else:
            self.status_label.setText("连接测试失败")
            self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            QMessageBox.warning(self, "测试失败", message)
        
        # 3秒后恢复默认状态
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("就绪"),
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        ))

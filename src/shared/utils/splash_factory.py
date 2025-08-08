#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动画面工厂

提供统一的启动画面创建和管理功能，减少重复的UI操作代码。
"""

from typing import List, Optional
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

from src.shared.utils.logger import get_logger
from src.shared.constants import (
    APP_NAME, SPLASH_WIDTH, SPLASH_HEIGHT, 
    SPLASH_FONT_FAMILY, SPLASH_FONT_SIZE
)

logger = get_logger(__name__)


class SplashScreenManager:
    """
    启动画面管理器
    
    提供统一的启动画面创建、消息显示和生命周期管理。
    """
    
    def __init__(self, app: QApplication):
        """
        初始化启动画面管理器
        
        Args:
            app: Qt应用程序实例
        """
        self.app = app
        self.splash: Optional[QSplashScreen] = None
        self._message_queue: List[str] = []
        
        logger.debug("启动画面管理器初始化完成")
    
    def create_splash(self) -> QSplashScreen:
        """
        创建启动画面
        
        Returns:
            QSplashScreen: 配置好的启动画面实例
        """
        # 创建启动画面背景
        pixmap = QPixmap(SPLASH_WIDTH, SPLASH_HEIGHT)
        pixmap.fill(Qt.GlobalColor.white)
        
        # 创建启动画面
        self.splash = QSplashScreen(pixmap)
        self.splash.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        )
        
        # 设置字体
        font = QFont(SPLASH_FONT_FAMILY, SPLASH_FONT_SIZE)
        self.splash.setFont(font)
        
        # 显示初始消息
        self.splash.showMessage(
            f"🤖 {APP_NAME}\n\n正在启动...",
            Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.black
        )
        
        logger.debug("启动画面创建完成")
        return self.splash
    
    def show_message(self, message: str, process_events: bool = True) -> None:
        """
        显示启动消息
        
        Args:
            message: 要显示的消息
            process_events: 是否处理事件循环
        """
        if self.splash:
            self.splash.showMessage(
                message,
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                Qt.GlobalColor.black
            )
            
            if process_events:
                self.app.processEvents()
            
            logger.debug(f"显示启动消息: {message}")
        else:
            logger.warning(f"启动画面未创建，无法显示消息: {message}")
    
    def show_progress_messages(self, messages: List[str], delay_between: int = 100) -> None:
        """
        按顺序显示多个进度消息
        
        Args:
            messages: 消息列表
            delay_between: 消息间延迟时间（毫秒）
        """
        if not self.splash:
            logger.warning("启动画面未创建，无法显示进度消息")
            return
        
        for i, message in enumerate(messages):
            if i == 0:
                # 立即显示第一个消息
                self.show_message(message)
            else:
                # 延迟显示后续消息
                QTimer.singleShot(
                    delay_between * i,
                    lambda msg=message: self.show_message(msg)
                )
    
    def close_splash(self, delay: int = 0) -> None:
        """
        关闭启动画面
        
        Args:
            delay: 延迟关闭时间（毫秒）
        """
        if self.splash:
            if delay > 0:
                QTimer.singleShot(delay, self._do_close_splash)
            else:
                self._do_close_splash()
        else:
            logger.warning("启动画面未创建，无法关闭")
    
    def _do_close_splash(self) -> None:
        """执行启动画面关闭"""
        if self.splash:
            try:
                self.splash.close()
                self.splash = None
                logger.debug("启动画面已关闭")
            except Exception as e:
                logger.error(f"关闭启动画面失败: {e}")
    
    def is_active(self) -> bool:
        """
        检查启动画面是否活跃
        
        Returns:
            bool: 启动画面是否活跃
        """
        return self.splash is not None and self.splash.isVisible()


class InitializationStepManager:
    """
    初始化步骤管理器
    
    管理应用程序初始化过程中的步骤和消息显示。
    """
    
    def __init__(self, splash_manager: SplashScreenManager):
        """
        初始化步骤管理器
        
        Args:
            splash_manager: 启动画面管理器
        """
        self.splash_manager = splash_manager
        self.steps = []
        self.current_step = 0
        
        logger.debug("初始化步骤管理器创建完成")
    
    def add_step(self, name: str, message: str, action: callable) -> None:
        """
        添加初始化步骤
        
        Args:
            name: 步骤名称
            message: 显示消息
            action: 执行动作
        """
        self.steps.append({
            'name': name,
            'message': message,
            'action': action
        })
        logger.debug(f"添加初始化步骤: {name}")
    
    def execute_steps(self) -> bool:
        """
        执行所有初始化步骤
        
        Returns:
            bool: 所有步骤是否成功执行
        """
        logger.info(f"开始执行 {len(self.steps)} 个初始化步骤")
        
        for i, step in enumerate(self.steps):
            self.current_step = i
            
            # 显示步骤消息
            self.splash_manager.show_message(step['message'])
            
            try:
                # 执行步骤动作
                logger.debug(f"执行步骤: {step['name']}")
                result = step['action']()
                
                # 检查执行结果
                if result is False:
                    logger.error(f"初始化步骤失败: {step['name']}")
                    return False
                
                logger.debug(f"步骤完成: {step['name']}")
                
            except Exception as e:
                logger.error(f"执行步骤 '{step['name']}' 时发生异常: {e}")
                return False
        
        logger.info("所有初始化步骤执行完成")
        return True
    
    def get_progress(self) -> float:
        """
        获取当前进度
        
        Returns:
            float: 进度百分比 (0.0 - 1.0)
        """
        if not self.steps:
            return 0.0
        return self.current_step / len(self.steps)


def create_standard_initialization_steps(app_instance) -> List[dict]:
    """
    创建标准的初始化步骤列表
    
    Args:
        app_instance: 应用程序实例
        
    Returns:
        List[dict]: 初始化步骤列表
    """
    return [
        {
            'name': 'core_components',
            'message': '初始化核心组件...',
            'action': app_instance._initialize_core_components
        },
        {
            'name': 'dependencies',
            'message': '注册服务依赖...',
            'action': app_instance._register_dependencies
        },
        {
            'name': 'services',
            'message': '初始化应用服务...',
            'action': app_instance._initialize_services
        },
        {
            'name': 'ui',
            'message': '创建用户界面...',
            'action': app_instance._create_ui
        },
        {
            'name': 'theme',
            'message': '应用主题样式...',
            'action': lambda: app_instance._apply_theme() or True
        },
        {
            'name': 'async_loop',
            'message': '设置异步事件循环...',
            'action': lambda: app_instance._setup_async_loop() or True
        },
        {
            'name': 'complete',
            'message': '启动完成！',
            'action': lambda: True
        }
    ]


def create_splash_and_execute_steps(app: QApplication, app_instance) -> bool:
    """
    创建启动画面并执行初始化步骤的便捷函数
    
    Args:
        app: Qt应用程序实例
        app_instance: 应用程序实例
        
    Returns:
        bool: 初始化是否成功
    """
    # 创建启动画面管理器
    splash_manager = SplashScreenManager(app)
    
    # 创建并显示启动画面
    splash = splash_manager.create_splash()
    splash.show()
    app.processEvents()
    
    try:
        # 创建步骤管理器
        step_manager = InitializationStepManager(splash_manager)
        
        # 添加标准初始化步骤
        steps = create_standard_initialization_steps(app_instance)
        for step in steps:
            step_manager.add_step(step['name'], step['message'], step['action'])
        
        # 执行所有步骤
        success = step_manager.execute_steps()
        
        if success:
            # 延迟关闭启动画面
            from src.shared.constants import UI_LONG_DELAY
            splash_manager.close_splash(UI_LONG_DELAY)
        else:
            # 立即关闭启动画面
            splash_manager.close_splash()
        
        return success
        
    except Exception as e:
        logger.error(f"初始化过程中发生异常: {e}")
        splash_manager.close_splash()
        return False

"""
个性化界面适配器

基于用户习惯和偏好，智能调整界面布局、主题和功能配置。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import json
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPalette, QColor

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class UITheme(Enum):
    """界面主题"""
    LIGHT = "light"                      # 浅色主题
    DARK = "dark"                        # 深色主题
    AUTO = "auto"                        # 自动切换
    SEPIA = "sepia"                      # 护眼模式
    HIGH_CONTRAST = "high_contrast"      # 高对比度


class LayoutMode(Enum):
    """布局模式"""
    COMPACT = "compact"                  # 紧凑布局
    COMFORTABLE = "comfortable"          # 舒适布局
    SPACIOUS = "spacious"               # 宽松布局
    CUSTOM = "custom"                   # 自定义布局


class InteractionStyle(Enum):
    """交互风格"""
    MINIMAL = "minimal"                  # 极简风格
    STANDARD = "standard"               # 标准风格
    RICH = "rich"                       # 丰富风格
    PROFESSIONAL = "professional"       # 专业风格


@dataclass
class UserBehavior:
    """用户行为数据"""
    action: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0               # 操作持续时间
    frequency: int = 1                  # 操作频率


@dataclass
class UIPreferences:
    """界面偏好设置"""
    theme: UITheme = UITheme.AUTO
    layout_mode: LayoutMode = LayoutMode.COMFORTABLE
    interaction_style: InteractionStyle = InteractionStyle.STANDARD
    font_size: int = 12
    line_spacing: float = 1.5
    sidebar_width: int = 250
    panel_positions: Dict[str, str] = field(default_factory=dict)
    toolbar_visible: bool = True
    status_bar_visible: bool = True
    auto_hide_panels: bool = False
    animation_enabled: bool = True
    sound_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 转换枚举值
        result['theme'] = self.theme.value
        result['layout_mode'] = self.layout_mode.value
        result['interaction_style'] = self.interaction_style.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIPreferences':
        """从字典创建"""
        # 转换枚举值
        if 'theme' in data:
            data['theme'] = UITheme(data['theme'])
        if 'layout_mode' in data:
            data['layout_mode'] = LayoutMode(data['layout_mode'])
        if 'interaction_style' in data:
            data['interaction_style'] = InteractionStyle(data['interaction_style'])
        
        return cls(**data)


@dataclass
class UsagePattern:
    """使用模式"""
    pattern_name: str
    actions: List[str]
    frequency: int
    avg_duration: float
    time_of_day: List[int]              # 使用时间段
    confidence: float                   # 模式置信度


class PersonalizedUIAdapter(QObject):
    """
    个性化界面适配器
    
    提供智能的界面个性化功能：
    1. 用户行为分析：跟踪和分析用户操作习惯
    2. 智能主题切换：根据时间和环境自动调整主题
    3. 布局优化：基于使用频率调整界面布局
    4. 个性化推荐：推荐合适的功能和设置
    5. 自适应界面：根据屏幕大小和分辨率调整
    6. 使用模式识别：识别用户的工作模式
    """
    
    # 信号定义
    theme_changed = pyqtSignal(str)                    # 主题变更
    layout_changed = pyqtSignal(str)                   # 布局变更
    preferences_updated = pyqtSignal(dict)             # 偏好更新
    recommendation_available = pyqtSignal(str, str)    # 推荐可用
    
    def __init__(self, config_path: Path):
        super().__init__()

        # 配置路径（必须提供，通常为项目内路径）
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 用户偏好
        self.preferences = self._load_preferences()
        
        # 行为跟踪
        self.behavior_history: List[UserBehavior] = []
        self.max_behavior_history = 10000
        
        # 使用统计
        self.usage_stats = defaultdict(int)
        self.feature_usage = defaultdict(list)
        self.session_start_time = datetime.now()
        
        # 模式识别
        self.usage_patterns: List[UsagePattern] = []
        self.current_pattern: Optional[UsagePattern] = None
        
        # 自动调整
        self.auto_adjustment_enabled = True
        self.adjustment_timer = QTimer()
        self.adjustment_timer.timeout.connect(self._periodic_adjustment)
        self.adjustment_timer.start(300000)  # 5分钟检查一次
        
        # 推荐系统
        self.recommendation_callbacks: List[Callable[[str, str], None]] = []
        
        # 界面组件引用
        self.main_window: Optional[QWidget] = None
        self.registered_widgets: Dict[str, QWidget] = {}
        
        logger.info("个性化界面适配器初始化完成")
    
    def _load_preferences(self) -> UIPreferences:
        """加载用户偏好"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return UIPreferences.from_dict(data)
            else:
                logger.info("使用默认界面偏好")
                return UIPreferences()
                
        except Exception as e:
            logger.error(f"加载界面偏好失败: {e}")
            return UIPreferences()
    
    def _save_preferences(self):
        """保存用户偏好"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.preferences.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug("界面偏好已保存")
            
        except Exception as e:
            logger.error(f"保存界面偏好失败: {e}")
    
    def register_main_window(self, main_window: QWidget):
        """注册主窗口"""
        self.main_window = main_window
        self._apply_current_preferences()
        logger.info("主窗口已注册")
    
    def register_widget(self, widget_id: str, widget: QWidget):
        """注册界面组件"""
        self.registered_widgets[widget_id] = widget
        logger.debug(f"界面组件已注册: {widget_id}")
    
    def track_user_action(self, action: str, context: Dict[str, Any] = None, duration: float = 0.0):
        """跟踪用户操作"""
        try:
            behavior = UserBehavior(
                action=action,
                timestamp=datetime.now(),
                context=context or {},
                duration=duration
            )
            
            self.behavior_history.append(behavior)
            
            # 限制历史记录大小
            if len(self.behavior_history) > self.max_behavior_history:
                self.behavior_history = self.behavior_history[-self.max_behavior_history:]
            
            # 更新使用统计
            self.usage_stats[action] += 1
            self.feature_usage[action].append(datetime.now())
            
            # 分析使用模式
            self._analyze_usage_patterns()
            
            logger.debug(f"用户操作已跟踪: {action}")
            
        except Exception as e:
            logger.error(f"跟踪用户操作失败: {e}")
    
    def _analyze_usage_patterns(self):
        """分析使用模式"""
        try:
            if len(self.behavior_history) < 50:  # 需要足够的数据
                return
            
            # 分析最近的行为模式
            recent_behaviors = self.behavior_history[-100:]
            
            # 按时间段分组
            time_groups = defaultdict(list)
            for behavior in recent_behaviors:
                hour = behavior.timestamp.hour
                time_groups[hour].append(behavior.action)
            
            # 识别高频操作序列
            action_sequences = []
            for i in range(len(recent_behaviors) - 2):
                sequence = [
                    recent_behaviors[i].action,
                    recent_behaviors[i+1].action,
                    recent_behaviors[i+2].action
                ]
                action_sequences.append(tuple(sequence))
            
            # 统计序列频率
            sequence_counts = Counter(action_sequences)
            
            # 识别新的使用模式
            for sequence, count in sequence_counts.most_common(5):
                if count >= 3:  # 至少重复3次
                    pattern_name = f"pattern_{hash(sequence) % 1000}"
                    
                    # 检查是否已存在
                    existing = any(p.pattern_name == pattern_name for p in self.usage_patterns)
                    if not existing:
                        pattern = UsagePattern(
                            pattern_name=pattern_name,
                            actions=list(sequence),
                            frequency=count,
                            avg_duration=0.0,
                            time_of_day=[datetime.now().hour],
                            confidence=min(count / 10, 1.0)
                        )
                        self.usage_patterns.append(pattern)
                        
                        logger.info(f"识别到新的使用模式: {pattern_name}")
            
        except Exception as e:
            logger.error(f"分析使用模式失败: {e}")
    
    def _periodic_adjustment(self):
        """定期调整"""
        try:
            if not self.auto_adjustment_enabled:
                return
            
            # 自动主题切换
            self._auto_adjust_theme()
            
            # 布局优化
            self._optimize_layout()
            
            # 生成推荐
            self._generate_recommendations()
            
        except Exception as e:
            logger.error(f"定期调整失败: {e}")
    
    def _auto_adjust_theme(self):
        """自动调整主题"""
        try:
            if self.preferences.theme != UITheme.AUTO:
                return
            
            current_hour = datetime.now().hour
            
            # 根据时间自动切换主题
            if 6 <= current_hour <= 18:
                new_theme = UITheme.LIGHT
            else:
                new_theme = UITheme.DARK
            
            # 检查是否需要切换
            current_theme_name = getattr(self, '_current_applied_theme', None)
            if current_theme_name != new_theme.value:
                self._apply_theme(new_theme)
                self._current_applied_theme = new_theme.value
                logger.info(f"自动切换主题: {new_theme.value}")
            
        except Exception as e:
            logger.error(f"自动调整主题失败: {e}")
    
    def _optimize_layout(self):
        """优化布局"""
        try:
            # 基于使用频率调整界面元素位置
            if not self.usage_stats:
                return
            
            # 获取最常用的功能
            top_actions = sorted(self.usage_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 生成布局建议
            layout_suggestions = []
            for action, count in top_actions:
                if count > 10:  # 使用频率较高
                    if 'ai' in action.lower():
                        layout_suggestions.append("将AI面板设置为默认显示")
                    elif 'save' in action.lower():
                        layout_suggestions.append("将保存按钮放在更显眼的位置")
                    elif 'search' in action.lower():
                        layout_suggestions.append("启用快速搜索功能")
            
            # 应用布局建议（这里简化处理）
            if layout_suggestions:
                logger.info(f"布局优化建议: {layout_suggestions}")
            
        except Exception as e:
            logger.error(f"优化布局失败: {e}")
    
    def _generate_recommendations(self):
        """生成个性化推荐"""
        try:
            recommendations = []
            
            # 基于使用时间的推荐
            session_duration = (datetime.now() - self.session_start_time).total_seconds() / 60
            if session_duration > 60:  # 使用超过1小时
                recommendations.append(("休息提醒", "您已连续使用1小时，建议适当休息"))
            
            # 基于使用模式的推荐
            if self.current_pattern:
                if 'write' in self.current_pattern.actions:
                    recommendations.append(("写作模式", "检测到您在专注写作，是否启用专注模式？"))
            
            # 基于功能使用的推荐
            ai_usage = self.usage_stats.get('ai_request', 0)
            if ai_usage > 20:
                recommendations.append(("AI功能", "您经常使用AI功能，可以设置快捷键提高效率"))
            
            # 发送推荐
            for title, content in recommendations:
                self.recommendation_available.emit(title, content)
                
                # 通知回调
                for callback in self.recommendation_callbacks:
                    try:
                        callback(title, content)
                    except Exception as e:
                        logger.error(f"推荐回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
    
    def _apply_current_preferences(self):
        """应用当前偏好设置"""
        try:
            if not self.main_window:
                return
            
            # 应用主题
            self._apply_theme(self.preferences.theme)
            
            # 应用布局
            self._apply_layout(self.preferences.layout_mode)
            
            # 应用字体设置
            self._apply_font_settings()
            
            # 发出偏好更新信号
            self.preferences_updated.emit(self.preferences.to_dict())
            
        except Exception as e:
            logger.error(f"应用偏好设置失败: {e}")
    
    def _apply_theme(self, theme: UITheme):
        """应用主题"""
        try:
            if not self.main_window:
                return
            
            app = QApplication.instance()
            if not app:
                return
            
            # 根据主题设置调色板
            palette = QPalette()
            
            if theme == UITheme.DARK:
                # 深色主题
                palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
                palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
                
            elif theme == UITheme.SEPIA:
                # 护眼模式
                palette.setColor(QPalette.ColorRole.Window, QColor(248, 243, 227))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(101, 67, 33))
                palette.setColor(QPalette.ColorRole.Base, QColor(255, 250, 240))
                palette.setColor(QPalette.ColorRole.Text, QColor(101, 67, 33))
                
            else:
                # 浅色主题（默认）
                palette = app.style().standardPalette()
            
            app.setPalette(palette)
            self.theme_changed.emit(theme.value)
            
            logger.debug(f"主题已应用: {theme.value}")
            
        except Exception as e:
            logger.error(f"应用主题失败: {e}")
    
    def _apply_layout(self, layout_mode: LayoutMode):
        """应用布局模式"""
        try:
            # 这里可以根据布局模式调整间距、大小等
            spacing_map = {
                LayoutMode.COMPACT: 4,
                LayoutMode.COMFORTABLE: 8,
                LayoutMode.SPACIOUS: 16,
                LayoutMode.CUSTOM: self.preferences.line_spacing * 4
            }
            
            spacing = spacing_map.get(layout_mode, 8)
            
            # 应用到注册的组件
            for widget_id, widget in self.registered_widgets.items():
                if hasattr(widget, 'layout') and widget.layout():
                    widget.layout().setSpacing(spacing)
            
            self.layout_changed.emit(layout_mode.value)
            logger.debug(f"布局模式已应用: {layout_mode.value}")
            
        except Exception as e:
            logger.error(f"应用布局模式失败: {e}")
    
    def _apply_font_settings(self):
        """应用字体设置"""
        try:
            if not self.main_window:
                return
            
            # 设置全局字体大小
            app = QApplication.instance()
            if app:
                font = app.font()
                font.setPointSize(self.preferences.font_size)
                app.setFont(font)
            
            logger.debug(f"字体设置已应用: {self.preferences.font_size}pt")
            
        except Exception as e:
            logger.error(f"应用字体设置失败: {e}")
    
    def update_preference(self, key: str, value: Any):
        """更新偏好设置"""
        try:
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
                self._save_preferences()
                self._apply_current_preferences()
                logger.info(f"偏好设置已更新: {key} = {value}")
            else:
                logger.warning(f"未知的偏好设置: {key}")
                
        except Exception as e:
            logger.error(f"更新偏好设置失败: {e}")
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        try:
            session_duration = (datetime.now() - self.session_start_time).total_seconds() / 60
            
            return {
                'session_duration_minutes': session_duration,
                'total_actions': sum(self.usage_stats.values()),
                'top_actions': dict(sorted(self.usage_stats.items(), key=lambda x: x[1], reverse=True)[:10]),
                'usage_patterns_count': len(self.usage_patterns),
                'behavior_history_size': len(self.behavior_history),
                'current_theme': self.preferences.theme.value,
                'current_layout': self.preferences.layout_mode.value
            }
            
        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return {}
    
    def add_recommendation_callback(self, callback: Callable[[str, str], None]):
        """添加推荐回调"""
        self.recommendation_callbacks.append(callback)
    
    def enable_auto_adjustment(self, enabled: bool):
        """启用/禁用自动调整"""
        self.auto_adjustment_enabled = enabled
        logger.info(f"自动调整: {'启用' if enabled else '禁用'}")
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        try:
            self.preferences = UIPreferences()
            self._save_preferences()
            self._apply_current_preferences()
            logger.info("界面设置已重置为默认值")
            
        except Exception as e:
            logger.error(f"重置设置失败: {e}")
    
    def export_preferences(self, file_path: Path) -> bool:
        """导出偏好设置"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.preferences.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"偏好设置已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出偏好设置失败: {e}")
            return False
    
    def import_preferences(self, file_path: Path) -> bool:
        """导入偏好设置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.preferences = UIPreferences.from_dict(data)
                self._save_preferences()
                self._apply_current_preferences()
            logger.info(f"偏好设置已导入: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导入偏好设置失败: {e}")
            return False


# 全局个性化适配器实例
_global_ui_adapter = None

def get_ui_adapter() -> PersonalizedUIAdapter:
    """获取全局个性化适配器"""
    global _global_ui_adapter
    if _global_ui_adapter is None:
        _global_ui_adapter = PersonalizedUIAdapter()
    return _global_ui_adapter

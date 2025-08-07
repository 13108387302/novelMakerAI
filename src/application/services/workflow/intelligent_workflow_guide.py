"""
智能工作流引导系统

提供智能的写作流程引导、任务管理和创作进度跟踪。

Author: AI小说编辑器团队
Date: 2025-08-06
"""

import json
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowStage(Enum):
    """工作流阶段"""
    PLANNING = "planning"                # 规划阶段
    OUTLINING = "outlining"              # 大纲阶段
    DRAFTING = "drafting"                # 初稿阶段
    REVISING = "revising"                # 修改阶段
    EDITING = "editing"                  # 编辑阶段
    POLISHING = "polishing"              # 润色阶段
    REVIEWING = "reviewing"              # 审阅阶段
    PUBLISHING = "publishing"            # 发布阶段


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"                          # 低优先级
    MEDIUM = "medium"                    # 中优先级
    HIGH = "high"                        # 高优先级
    URGENT = "urgent"                    # 紧急


class TaskStatus(Enum):
    """任务状态"""
    NOT_STARTED = "not_started"          # 未开始
    IN_PROGRESS = "in_progress"          # 进行中
    PAUSED = "paused"                    # 暂停
    COMPLETED = "completed"              # 已完成
    CANCELLED = "cancelled"              # 已取消


@dataclass
class WorkflowTask:
    """工作流任务"""
    task_id: str
    title: str
    description: str
    stage: WorkflowStage
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.NOT_STARTED
    estimated_duration: int = 60         # 预估时长（分钟）
    actual_duration: int = 0             # 实际时长（分钟）
    dependencies: List[str] = field(default_factory=list)  # 依赖任务
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0                # 进度百分比 (0-1)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 转换枚举和日期
        result['stage'] = self.stage.value
        result['priority'] = self.priority.value
        result['status'] = self.status.value
        result['created_at'] = self.created_at.isoformat()
        result['started_at'] = self.started_at.isoformat() if self.started_at else None
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowTask':
        """从字典创建"""
        # 转换枚举和日期
        data['stage'] = WorkflowStage(data['stage'])
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        
        return cls(**data)


@dataclass
class WorkflowTemplate:
    """工作流模板"""
    template_id: str
    name: str
    description: str
    stages: List[WorkflowStage]
    default_tasks: List[Dict[str, Any]]
    estimated_total_time: int = 0        # 总预估时间（小时）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['stages'] = [stage.value for stage in self.stages]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowTemplate':
        """从字典创建"""
        data['stages'] = [WorkflowStage(stage) for stage in data['stages']]
        return cls(**data)


@dataclass
class WritingSession:
    """写作会话"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    words_written: int = 0
    tasks_completed: List[str] = field(default_factory=list)
    focus_score: float = 0.0             # 专注度评分 (0-1)
    productivity_score: float = 0.0      # 生产力评分 (0-1)
    notes: str = ""


class IntelligentWorkflowGuide(QObject):
    """
    智能工作流引导系统
    
    提供全面的写作流程管理功能：
    1. 工作流模板：预定义的写作流程模板
    2. 任务管理：智能任务创建、分配和跟踪
    3. 进度监控：实时跟踪写作进度和效率
    4. 智能建议：基于进度和习惯的流程建议
    5. 时间管理：番茄钟、专注模式等时间管理工具
    6. 成就系统：激励用户完成写作目标
    """
    
    # 信号定义
    task_created = pyqtSignal(str)                    # 任务创建
    task_updated = pyqtSignal(str, str)               # 任务更新
    stage_changed = pyqtSignal(str, str)              # 阶段变更
    milestone_reached = pyqtSignal(str, str)          # 里程碑达成
    suggestion_available = pyqtSignal(str, str)       # 建议可用
    
    def __init__(self, config_path: Optional[Path] = None):
        super().__init__()
        
        # 配置路径
        self.config_path = config_path or Path.home() / ".ai_novel_editor" / "workflow.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 任务管理
        self.tasks: Dict[str, WorkflowTask] = {}
        self.current_stage = WorkflowStage.PLANNING
        self.active_tasks: List[str] = []
        
        # 工作流模板
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.current_template: Optional[WorkflowTemplate] = None
        
        # 会话管理
        self.writing_sessions: List[WritingSession] = []
        self.current_session: Optional[WritingSession] = None
        
        # 进度跟踪
        self.daily_goals = {
            'words': 1000,
            'tasks': 3,
            'time_minutes': 120
        }
        self.progress_history: Dict[str, List[float]] = defaultdict(list)  # 日期 -> 进度列表
        
        # 智能建议
        self.suggestion_callbacks: List[Callable[[str, str], None]] = []
        self.last_suggestion_time = datetime.now()
        
        # 定时器
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_timer.start(60000)  # 每分钟更新一次
        
        # 加载数据
        self._load_workflow_data()
        self._load_default_templates()
        
        logger.info("智能工作流引导系统初始化完成")
    
    def _load_workflow_data(self):
        """加载工作流数据"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 加载任务
                    if 'tasks' in data:
                        for task_data in data['tasks']:
                            task = WorkflowTask.from_dict(task_data)
                            self.tasks[task.task_id] = task
                    
                    # 加载模板
                    if 'templates' in data:
                        for template_data in data['templates']:
                            template = WorkflowTemplate.from_dict(template_data)
                            self.templates[template.template_id] = template
                    
                    # 加载其他设置
                    if 'current_stage' in data:
                        self.current_stage = WorkflowStage(data['current_stage'])
                    if 'daily_goals' in data:
                        self.daily_goals.update(data['daily_goals'])
                    
                logger.info("工作流数据加载完成")
            else:
                logger.info("使用默认工作流配置")
                
        except Exception as e:
            logger.error(f"加载工作流数据失败: {e}")
    
    def _save_workflow_data(self):
        """保存工作流数据"""
        try:
            data = {
                'tasks': [task.to_dict() for task in self.tasks.values()],
                'templates': [template.to_dict() for template in self.templates.values()],
                'current_stage': self.current_stage.value,
                'daily_goals': self.daily_goals,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("工作流数据已保存")
            
        except Exception as e:
            logger.error(f"保存工作流数据失败: {e}")
    
    def _load_default_templates(self):
        """加载默认工作流模板"""
        try:
            # 小说创作模板
            novel_template = WorkflowTemplate(
                template_id="novel_writing",
                name="小说创作流程",
                description="完整的小说创作工作流程",
                stages=[
                    WorkflowStage.PLANNING,
                    WorkflowStage.OUTLINING,
                    WorkflowStage.DRAFTING,
                    WorkflowStage.REVISING,
                    WorkflowStage.EDITING,
                    WorkflowStage.POLISHING
                ],
                default_tasks=[
                    {
                        'title': '确定主题和类型',
                        'description': '明确小说的主题思想和文体类型',
                        'stage': 'planning',
                        'priority': 'high',
                        'estimated_duration': 120
                    },
                    {
                        'title': '角色设定',
                        'description': '创建主要角色的背景和性格设定',
                        'stage': 'planning',
                        'priority': 'high',
                        'estimated_duration': 180
                    },
                    {
                        'title': '世界观构建',
                        'description': '构建故事发生的世界观和背景设定',
                        'stage': 'planning',
                        'priority': 'medium',
                        'estimated_duration': 150
                    },
                    {
                        'title': '制作大纲',
                        'description': '制作详细的章节大纲',
                        'stage': 'outlining',
                        'priority': 'high',
                        'estimated_duration': 240
                    },
                    {
                        'title': '初稿写作',
                        'description': '按照大纲完成初稿写作',
                        'stage': 'drafting',
                        'priority': 'high',
                        'estimated_duration': 1800  # 30小时
                    }
                ],
                estimated_total_time=40
            )
            
            # 短篇创作模板
            short_story_template = WorkflowTemplate(
                template_id="short_story",
                name="短篇小说创作",
                description="短篇小说的快速创作流程",
                stages=[
                    WorkflowStage.PLANNING,
                    WorkflowStage.DRAFTING,
                    WorkflowStage.REVISING,
                    WorkflowStage.POLISHING
                ],
                default_tasks=[
                    {
                        'title': '构思核心冲突',
                        'description': '确定短篇的核心冲突和转折点',
                        'stage': 'planning',
                        'priority': 'high',
                        'estimated_duration': 60
                    },
                    {
                        'title': '快速写作',
                        'description': '一气呵成完成初稿',
                        'stage': 'drafting',
                        'priority': 'high',
                        'estimated_duration': 180
                    }
                ],
                estimated_total_time=8
            )
            
            self.templates[novel_template.template_id] = novel_template
            self.templates[short_story_template.template_id] = short_story_template
            
            logger.info("默认工作流模板加载完成")
            
        except Exception as e:
            logger.error(f"加载默认模板失败: {e}")
    
    def create_task(self, title: str, description: str, stage: WorkflowStage, 
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   estimated_duration: int = 60, tags: List[str] = None) -> str:
        """创建任务"""
        try:
            task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
            
            task = WorkflowTask(
                task_id=task_id,
                title=title,
                description=description,
                stage=stage,
                priority=priority,
                estimated_duration=estimated_duration,
                tags=tags or []
            )
            
            self.tasks[task_id] = task
            self._save_workflow_data()
            
            self.task_created.emit(task_id)
            logger.info(f"任务已创建: {title}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return ""
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """更新任务状态"""
        try:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            old_status = task.status
            task.status = status
            
            # 更新时间戳
            if status == TaskStatus.IN_PROGRESS and old_status == TaskStatus.NOT_STARTED:
                task.started_at = datetime.now()
            elif status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
                task.progress = 1.0
                
                # 计算实际时长
                if task.started_at:
                    duration = (task.completed_at - task.started_at).total_seconds() / 60
                    task.actual_duration = int(duration)
            
            self._save_workflow_data()
            self.task_updated.emit(task_id, status.value)
            
            # 检查是否达成里程碑
            self._check_milestones()
            
            logger.info(f"任务状态已更新: {task.title} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False
    
    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """更新任务进度"""
        try:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.progress = max(0.0, min(1.0, progress))
            
            # 如果进度达到100%，自动标记为完成
            if task.progress >= 1.0 and task.status != TaskStatus.COMPLETED:
                self.update_task_status(task_id, TaskStatus.COMPLETED)
            
            self._save_workflow_data()
            logger.debug(f"任务进度已更新: {task.title} -> {progress:.1%}")
            
            return True
            
        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")
            return False
    
    def start_writing_session(self) -> str:
        """开始写作会话"""
        try:
            session_id = f"session_{int(datetime.now().timestamp() * 1000)}"
            
            session = WritingSession(
                session_id=session_id,
                start_time=datetime.now()
            )
            
            self.current_session = session
            self.writing_sessions.append(session)
            
            logger.info(f"写作会话已开始: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"开始写作会话失败: {e}")
            return ""
    
    def end_writing_session(self, words_written: int = 0, notes: str = "") -> bool:
        """结束写作会话"""
        try:
            if not self.current_session:
                return False
            
            self.current_session.end_time = datetime.now()
            self.current_session.words_written = words_written
            self.current_session.notes = notes
            
            # 计算会话统计
            session_duration = (self.current_session.end_time - self.current_session.start_time).total_seconds() / 60
            
            if session_duration > 0:
                # 计算生产力评分
                words_per_minute = words_written / session_duration
                self.current_session.productivity_score = min(words_per_minute / 10, 1.0)  # 假设10字/分钟为满分
                
                # 计算专注度评分（简化版本）
                self.current_session.focus_score = 0.8  # 默认值，实际可以基于更多数据计算
            
            logger.info(f"写作会话已结束: {words_written}字, {session_duration:.1f}分钟")
            
            self.current_session = None
            self._save_workflow_data()
            
            return True
            
        except Exception as e:
            logger.error(f"结束写作会话失败: {e}")
            return False
    
    def apply_template(self, template_id: str) -> bool:
        """应用工作流模板"""
        try:
            if template_id not in self.templates:
                return False
            
            template = self.templates[template_id]
            self.current_template = template
            
            # 创建模板中的默认任务
            for task_data in template.default_tasks:
                self.create_task(
                    title=task_data['title'],
                    description=task_data['description'],
                    stage=WorkflowStage(task_data['stage']),
                    priority=TaskPriority(task_data.get('priority', 'medium')),
                    estimated_duration=task_data.get('estimated_duration', 60)
                )
            
            # 设置当前阶段为第一个阶段
            if template.stages:
                self.current_stage = template.stages[0]
                self.stage_changed.emit(self.current_stage.value, template.name)
            
            logger.info(f"工作流模板已应用: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"应用工作流模板失败: {e}")
            return False
    
    def _update_progress(self):
        """更新进度（定时调用）"""
        try:
            # 检查当前阶段的任务完成情况
            current_stage_tasks = [task for task in self.tasks.values() if task.stage == self.current_stage]
            
            if current_stage_tasks:
                completed_tasks = [task for task in current_stage_tasks if task.status == TaskStatus.COMPLETED]
                stage_progress = len(completed_tasks) / len(current_stage_tasks)
                
                # 如果当前阶段完成度超过80%，建议进入下一阶段
                if stage_progress > 0.8:
                    self._suggest_next_stage()
            
            # 检查每日目标
            self._check_daily_goals()
            
            # 生成智能建议
            self._generate_workflow_suggestions()
            
        except Exception as e:
            logger.error(f"更新进度失败: {e}")
    
    def _suggest_next_stage(self):
        """建议进入下一阶段"""
        try:
            if not self.current_template:
                return
            
            current_index = self.current_template.stages.index(self.current_stage)
            if current_index < len(self.current_template.stages) - 1:
                next_stage = self.current_template.stages[current_index + 1]
                
                suggestion_title = "阶段进展建议"
                suggestion_content = f"当前{self.current_stage.value}阶段进展良好，建议进入{next_stage.value}阶段"
                
                self.suggestion_available.emit(suggestion_title, suggestion_content)
                
                # 通知回调
                for callback in self.suggestion_callbacks:
                    try:
                        callback(suggestion_title, suggestion_content)
                    except Exception as e:
                        logger.error(f"建议回调执行失败: {e}")
            
        except Exception as e:
            logger.error(f"建议下一阶段失败: {e}")
    
    def _check_daily_goals(self):
        """检查每日目标"""
        try:
            today = datetime.now().date()
            
            # 统计今日完成的任务
            today_completed_tasks = [
                task for task in self.tasks.values()
                if (task.completed_at and task.completed_at.date() == today)
            ]
            
            # 统计今日写作字数
            today_sessions = [
                session for session in self.writing_sessions
                if session.start_time.date() == today
            ]
            today_words = sum(session.words_written for session in today_sessions)
            
            # 检查目标完成情况
            goals_status = {
                'tasks': len(today_completed_tasks) >= self.daily_goals['tasks'],
                'words': today_words >= self.daily_goals['words']
            }
            
            # 如果达成目标，发出里程碑信号
            if all(goals_status.values()):
                self.milestone_reached.emit("daily_goals", "今日目标已达成！")
            
        except Exception as e:
            logger.error(f"检查每日目标失败: {e}")
    
    def _check_milestones(self):
        """检查里程碑"""
        try:
            # 检查任务完成里程碑
            completed_tasks = [task for task in self.tasks.values() if task.status == TaskStatus.COMPLETED]
            
            milestone_counts = [10, 25, 50, 100]
            for count in milestone_counts:
                if len(completed_tasks) == count:
                    self.milestone_reached.emit("task_milestone", f"恭喜！您已完成{count}个任务")
                    break
            
            # 检查写作字数里程碑
            total_words = sum(session.words_written for session in self.writing_sessions)
            word_milestones = [1000, 5000, 10000, 50000, 100000]
            
            for milestone in word_milestones:
                if total_words >= milestone:
                    # 检查是否是新达成的里程碑
                    previous_total = total_words - (self.current_session.words_written if self.current_session else 0)
                    if previous_total < milestone:
                        self.milestone_reached.emit("word_milestone", f"恭喜！您已写作{milestone}字")
                        break
            
        except Exception as e:
            logger.error(f"检查里程碑失败: {e}")
    
    def _generate_workflow_suggestions(self):
        """生成工作流建议"""
        try:
            # 限制建议频率
            if (datetime.now() - self.last_suggestion_time).total_seconds() < 1800:  # 30分钟
                return
            
            suggestions = []
            
            # 基于任务状态的建议
            overdue_tasks = [
                task for task in self.tasks.values()
                if (task.status == TaskStatus.IN_PROGRESS and 
                    task.started_at and 
                    (datetime.now() - task.started_at).total_seconds() > task.estimated_duration * 60 * 1.5)
            ]
            
            if overdue_tasks:
                suggestions.append(("任务管理", f"有{len(overdue_tasks)}个任务超时，建议重新评估时间安排"))
            
            # 基于写作会话的建议
            if self.current_session:
                session_duration = (datetime.now() - self.current_session.start_time).total_seconds() / 60
                if session_duration > 90:  # 超过90分钟
                    suggestions.append(("休息提醒", "您已连续写作90分钟，建议适当休息"))
            
            # 发送建议
            for title, content in suggestions:
                self.suggestion_available.emit(title, content)
                self.last_suggestion_time = datetime.now()
                break  # 一次只发送一个建议
            
        except Exception as e:
            logger.error(f"生成工作流建议失败: {e}")
    
    def get_current_tasks(self, stage: Optional[WorkflowStage] = None) -> List[WorkflowTask]:
        """获取当前任务"""
        try:
            tasks = list(self.tasks.values())
            
            if stage:
                tasks = [task for task in tasks if task.stage == stage]
            
            # 按优先级和创建时间排序
            priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
            tasks.sort(key=lambda t: (priority_order.get(t.priority.value, 4), t.created_at))
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取当前任务失败: {e}")
            return []
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        try:
            total_tasks = len(self.tasks)
            completed_tasks = len([task for task in self.tasks.values() if task.status == TaskStatus.COMPLETED])
            in_progress_tasks = len([task for task in self.tasks.values() if task.status == TaskStatus.IN_PROGRESS])
            
            total_words = sum(session.words_written for session in self.writing_sessions)
            total_time = sum(
                (session.end_time - session.start_time).total_seconds() / 60
                for session in self.writing_sessions
                if session.end_time
            )
            
            return {
                'current_stage': self.current_stage.value,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'completion_rate': completed_tasks / max(total_tasks, 1),
                'total_words': total_words,
                'total_time_minutes': total_time,
                'daily_goals': self.daily_goals,
                'active_template': self.current_template.name if self.current_template else None
            }
            
        except Exception as e:
            logger.error(f"获取进度摘要失败: {e}")
            return {}
    
    def set_daily_goal(self, goal_type: str, value: int):
        """设置每日目标"""
        if goal_type in self.daily_goals:
            self.daily_goals[goal_type] = value
            self._save_workflow_data()
            logger.info(f"每日目标已更新: {goal_type} = {value}")
    
    def add_suggestion_callback(self, callback: Callable[[str, str], None]):
        """添加建议回调"""
        self.suggestion_callbacks.append(callback)
    
    def advance_to_stage(self, stage: WorkflowStage) -> bool:
        """推进到指定阶段"""
        try:
            old_stage = self.current_stage
            self.current_stage = stage
            self._save_workflow_data()
            
            self.stage_changed.emit(stage.value, old_stage.value)
            logger.info(f"工作流阶段已推进: {old_stage.value} -> {stage.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"推进工作流阶段失败: {e}")
            return False


# 全局工作流引导实例
_global_workflow_guide = None

def get_workflow_guide() -> IntelligentWorkflowGuide:
    """获取全局工作流引导"""
    global _global_workflow_guide
    if _global_workflow_guide is None:
        _global_workflow_guide = IntelligentWorkflowGuide()
    return _global_workflow_guide

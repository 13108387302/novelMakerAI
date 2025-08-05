#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动执行处理器

提供AI功能的自动执行逻辑
"""

import logging
from typing import Optional, Dict, Any, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class AutoExecutionHandler(QObject):
    """
    自动执行处理器
    
    提供AI功能的自动执行逻辑，支持条件触发和智能调度
    """
    
    # 信号
    auto_execution_triggered = pyqtSignal(str, dict)  # 自动执行触发信号
    execution_completed = pyqtSignal(str, bool)  # 执行完成信号
    
    def __init__(self, parent=None):
        """
        初始化自动执行处理器
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._rules: List[Dict[str, Any]] = []
        self._enabled = True
        self._execution_queue: List[Dict[str, Any]] = []
        self._processing = False
        
        # 创建定时器用于处理队列
        self._queue_timer = QTimer()
        self._queue_timer.timeout.connect(self._process_queue)
        self._queue_timer.start(1000)  # 每秒检查一次队列
        
    def add_rule(self, rule_id: str, condition: Callable[[Dict[str, Any]], bool], 
                 action: str, priority: int = 0, delay: int = 0):
        """
        添加自动执行规则
        
        Args:
            rule_id: 规则ID
            condition: 条件函数
            action: 执行的操作
            priority: 优先级（数字越大优先级越高）
            delay: 延迟执行时间（秒）
        """
        rule = {
            'id': rule_id,
            'condition': condition,
            'action': action,
            'priority': priority,
            'delay': delay,
            'enabled': True
        }
        
        self._rules.append(rule)
        # 按优先级排序
        self._rules.sort(key=lambda x: x['priority'], reverse=True)
        
        logger.debug(f"自动执行规则已添加: {rule_id}")
        
    def remove_rule(self, rule_id: str):
        """
        移除自动执行规则
        
        Args:
            rule_id: 规则ID
        """
        self._rules = [rule for rule in self._rules if rule['id'] != rule_id]
        logger.debug(f"自动执行规则已移除: {rule_id}")
        
    def enable_rule(self, rule_id: str, enabled: bool = True):
        """
        启用/禁用规则
        
        Args:
            rule_id: 规则ID
            enabled: 是否启用
        """
        for rule in self._rules:
            if rule['id'] == rule_id:
                rule['enabled'] = enabled
                logger.debug(f"规则 {rule_id} {'启用' if enabled else '禁用'}")
                break
                
    def check_conditions(self, context: Dict[str, Any]):
        """
        检查条件并触发自动执行
        
        Args:
            context: 上下文数据
        """
        if not self._enabled:
            return
            
        try:
            for rule in self._rules:
                if not rule['enabled']:
                    continue
                    
                # 检查条件
                if rule['condition'](context):
                    # 添加到执行队列
                    execution_item = {
                        'rule_id': rule['id'],
                        'action': rule['action'],
                        'context': context.copy(),
                        'delay': rule['delay'],
                        'timestamp': self._get_current_timestamp()
                    }
                    
                    self._execution_queue.append(execution_item)
                    logger.debug(f"自动执行已排队: {rule['id']}")
                    
        except Exception as e:
            logger.error(f"检查自动执行条件失败: {e}")
            
    def _process_queue(self):
        """处理执行队列"""
        if self._processing or not self._execution_queue:
            return
            
        self._processing = True
        
        try:
            current_time = self._get_current_timestamp()
            ready_items = []
            
            # 找出准备执行的项目
            for item in self._execution_queue[:]:
                if current_time - item['timestamp'] >= item['delay']:
                    ready_items.append(item)
                    self._execution_queue.remove(item)
                    
            # 执行准备好的项目
            for item in ready_items:
                self._execute_item(item)
                
        except Exception as e:
            logger.error(f"处理执行队列失败: {e}")
        finally:
            self._processing = False
            
    def _execute_item(self, item: Dict[str, Any]):
        """
        执行队列项目
        
        Args:
            item: 执行项目
        """
        try:
            rule_id = item['rule_id']
            action = item['action']
            context = item['context']
            
            # 发射自动执行信号
            self.auto_execution_triggered.emit(action, context)
            
            # 发射完成信号
            self.execution_completed.emit(rule_id, True)
            
            logger.info(f"自动执行完成: {rule_id} -> {action}")
            
        except Exception as e:
            logger.error(f"执行项目失败: {item.get('rule_id', 'unknown')}, {e}")
            self.execution_completed.emit(item.get('rule_id', 'unknown'), False)
            
    def _get_current_timestamp(self) -> float:
        """获取当前时间戳"""
        import time
        return time.time()
        
    def set_enabled(self, enabled: bool):
        """
        设置是否启用自动执行
        
        Args:
            enabled: 是否启用
        """
        self._enabled = enabled
        logger.info(f"自动执行处理器 {'启用' if enabled else '禁用'}")
        
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
        
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self._execution_queue)
        
    def clear_queue(self):
        """清空执行队列"""
        self._execution_queue.clear()
        logger.debug("执行队列已清空")
        
    def get_rules(self) -> List[Dict[str, Any]]:
        """获取所有规则"""
        return [rule.copy() for rule in self._rules]

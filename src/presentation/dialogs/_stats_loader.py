#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable

class StatsSignals(QObject):
    finished = pyqtSignal(object, list)  # project, documents
    failed = pyqtSignal(str)

class StatsTask(QRunnable):
    """使用全局线程池的任务，避免对话框销毁时QThread未退出的问题"""
    def __init__(self, document_service, project):
        super().__init__()
        self._document_service = document_service
        self._project = project
        self.signals = StatsSignals()

    def run(self):
        try:
            import asyncio
            if self._project is None:
                self.signals.failed.emit("项目为空")
                return
            documents = asyncio.run(self._document_service.list_documents_by_project(self._project.id))
            self.signals.finished.emit(self._project, documents)
        except Exception as e:
            self.signals.failed.emit(str(e))


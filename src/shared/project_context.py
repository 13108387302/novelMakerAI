#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目上下文与路径服务

提供基于“项目根目录”的统一路径约定，避免到处散落的 Path.home() 或
相对应用目录的硬编码路径，从而实现基于项目文件夹的松耦合编辑器模式。

最小可用：仅定义 ProjectPaths，并不改变现有调用；后续通过依赖注入
将各仓储/服务切换为使用 ProjectPaths 下的子目录。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """
    项目路径集合（无副作用，不负责创建目录）

    约定目录结构（渐进式演进）：
    - root/                          项目根目录
      - .novel_editor/               项目隐藏配置区（沿用现有常量名，后续可平滑迁移到 .novel/）
        - config.json                项目配置（Settings 持久化）
        - data/                      通用数据区
          - sqlite/novel.db         每项目 SQLite（可选）
          - indexes/                二级索引
        - cache/                     项目缓存
        - logs/                      项目日志（可选）
      - content/
        - documents/                 文档内容与元数据（仓储可指向此处）
        - media/                     媒体资源
        - meta/                      各类元数据
      - backups/                     备份输出（可选）
    """

    root: Path

    @property
    def hidden_dir(self) -> Path:
        return self.root / ".novel_editor"

    @property
    def config_dir(self) -> Path:
        return self.hidden_dir

    @property
    def config_file(self) -> Path:
        return self.hidden_dir / "config.json"

    @property
    def data_dir(self) -> Path:
        return self.hidden_dir / "data"

    @property
    def sqlite_dir(self) -> Path:
        return self.data_dir / "sqlite"

    @property
    def sqlite_db(self) -> Path:
        return self.sqlite_dir / "novel.db"

    @property
    def indexes_dir(self) -> Path:
        return self.data_dir / "indexes"

    @property
    def cache_dir(self) -> Path:
        return self.hidden_dir / "cache"

    @property
    def logs_dir(self) -> Path:
        return self.hidden_dir / "logs"

    @property
    def log_dir(self) -> Path:
        """日志目录（别名，兼容性）"""
        return self.logs_dir

    @property
    def content_dir(self) -> Path:
        return self.root / "content"

    @property
    def documents_dir(self) -> Path:
        return self.content_dir / "documents"

    @property
    def media_dir(self) -> Path:
        return self.content_dir / "media"

    @property
    def meta_dir(self) -> Path:
        return self.content_dir / "meta"

    @property
    def backups_dir(self) -> Path:
        return self.root / "backups"


def ensure_project_dirs(paths: ProjectPaths) -> None:
    """按需创建常用目录（幂等）。"""
    for p in [
        paths.hidden_dir,
        paths.data_dir,
        paths.sqlite_dir,
        paths.indexes_dir,
        paths.cache_dir,
        paths.logs_dir,
        paths.content_dir,
        paths.documents_dir,
        paths.media_dir,
        paths.meta_dir,
        paths.backups_dir,
    ]:
        p.mkdir(parents=True, exist_ok=True)


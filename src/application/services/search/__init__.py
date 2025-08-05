#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索模块

提供搜索相关的所有功能
"""

from .search_models import (
    SearchMatch,
    SearchResult,
    SearchOptions,
    SearchHistoryItem,
    SearchStatistics,
    SearchQuery,
    SearchResultSet,
    SearchFilter,
    IndexStatus,
    SearchException,
    IndexException,
    SearchTimeoutException,
    IndexCorruptedException
)

from .search_index import SearchIndex
from .search_service_refactored import SearchService

__all__ = [
    # 数据模型
    'SearchMatch',
    'SearchResult', 
    'SearchOptions',
    'SearchHistoryItem',
    'SearchStatistics',
    'SearchQuery',
    'SearchResultSet',
    'SearchFilter',
    'IndexStatus',
    
    # 异常
    'SearchException',
    'IndexException', 
    'SearchTimeoutException',
    'IndexCorruptedException',
    
    # 核心类
    'SearchIndex',
    'SearchService'
]

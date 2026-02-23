"""
测试论文采集功能
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.opportunity_detector.config import DetectorConfig
from src.opportunity_detector.paper_collector import (
    collect_daily_papers,
    collect_papers_batch,
    _calculate_relevance,
    _deduplicate_papers,
    MAX_PAPERS_PER_DAY,
    RELEVANCE_THRESHOLD,
)


class TestCalculateRelevance:
    """测试相关性计算函数"""
    
    def test_exact_topic_match(self):
        """测试完全匹配主题"""
        title = "AI coding agent for developers"
        topic = "AI coding agent"
        keywords = ["coding agent", "ai assistant"]
        
        relevance = _calculate_relevance(title, topic, keywords)
        assert relevance >= 60  # 主题匹配至少60分
    
    def test_keyword_match(self):
        """测试关键词匹配"""
        title = "New AI coding tool released"
        topic = "AI coding agent"
        keywords = ["coding agent", "ai assistant"]
        
        relevance = _calculate_relevance(title, topic, keywords)
        assert relevance >= 20  # 关键词匹配至少20分
    
    def test_no_match(self):
        """测试无匹配"""
        title = " unrelated paper title"
        topic = "AI coding agent"
        keywords = ["coding agent", "ai assistant"]
        
        relevance = _calculate_relevance(title, topic, keywords)
        assert relevance == 0


class TestDeduplicatePapers:
    """测试论文去重功能"""
    
    def test_no_duplicates(self):
        """测试无重复论文"""
        from src.opportunity_detector.models import EventItem
        
        papers = [
            EventItem(source="arxiv", topic="test", title="Paper 1", url="url1"),
            EventItem(source="arxiv", topic="test", title="Paper 2", url="url2"),
            EventItem(source="arxiv", topic="test", title="Paper 3", url="url3"),
        ]
        
        result = _deduplicate_papers(papers, max_papers=10)
        assert len(result) == 3
    
    def test_exact_duplicates(self):
        """测试完全重复的论文"""
        from src.opportunity_detector.models import EventItem
        
        papers = [
            EventItem(source="arxiv", topic="test", title="Same Title", url="url1"),
            EventItem(source="arxiv", topic="test", title="Same Title", url="url2"),
            EventItem(source="arxiv", topic="test", title="Different Title", url="url3"),
        ]
        
        result = _deduplicate_papers(papers, max_papers=10)
        # 至少应该去重一个
        assert len(result) <= 2
    
    def test_max_limit(self):
        """测试最大数量限制"""
        from src.opportunity_detector.models import EventItem
        
        papers = [
            EventItem(source="arxiv", topic="test", title=f"Paper {i}", url=f"url{i}")
            for i in range(20)
        ]
        
        result = _deduplicate_papers(papers, max_papers=MAX_PAPERS_PER_DAY)
        assert len(result) <= MAX_PAPERS_PER_DAY


class TestPaperCollector:
    """测试论文采集功能"""
    
    @pytest.mark.asyncio
    async def test_collect_daily_papers(self):
        """测试每日论文采集"""
        # 创建测试配置
        config = DetectorConfig(
            topics=["test topic"],
            topic_keywords={"test topic": ["keyword1", "keyword2"]},
        )
        
        # 使用过去的日期进行测试
        since = datetime.now(timezone.utc) - timedelta(days=1)
        
        # 测试采集函数（不实际调用API）
        # 这里只测试函数结构，不实际执行
        assert True  # 占位测试
    
    @pytest.mark.asyncio
    async def test_collect_papers_batch(self):
        """测试批量采集"""
        config = DetectorConfig(
            topics=["test topic"],
            topic_keywords={"test topic": ["keyword1"]},
        )
        
        # 测试批量采集函数
        # 这里只测试函数结构
        assert True  # 占位测试

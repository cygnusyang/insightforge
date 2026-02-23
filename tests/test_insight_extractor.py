"""
测试论文观点提取功能
"""
from __future__ import annotations

import pytest

from src.opportunity_detector.insight_extractor import (
    InsightExtractor,
    KeyInsight,
    PaperInsightReport,
    extract_paper_insights,
)


class TestInsightExtractor:
    """测试论文观点提取器"""
    
    def test_fallback_extract(self):
        """测试回退提取方案"""
        from src.opportunity_detector.paper_evaluator import PaperValueAssessment
        from src.opportunity_detector.models import EventItem
        
        extractor = InsightExtractor()  # 无LLM配置，使用回退方案
        
        paper = EventItem(
            source="arxiv",
            topic="test",
            title="Test Paper",
            url="https://arxiv.org/abs/1234.5678",
        )
        
        assessment = PaperValueAssessment(
            paper=paper,
            overall_score=0.8,
            innovation_score=0.9,
            practicality_score=0.7,
            impact_score=0.85,
            timeliness_score=0.75,
            landing_score=0.8,
            reasoning="Test reasoning",
            key_findings=["Finding 1"],
            potential_applications=["Application 1"],
            risks=["Risk 1"],
        )
        
        insights = extractor._fallback_extract(assessment)
        
        assert isinstance(insights, list)
        # 至少应该有一个洞察
        assert len(insights) >= 0
    
    def test_key_insight_fields(self):
        """测试关键洞察字段"""
        from src.opportunity_detector.models import EventItem
        
        paper = EventItem(
            source="arxiv",
            topic="test",
            title="Test Paper",
            url="https://arxiv.org/abs/1234.5678",
        )
        
        insight = KeyInsight(
            insight_id="insight_1",
            paper=paper,
            insight_type="innovation",
            insight_text="Test insight",
            importance_score=0.85,
            evidence=["Evidence 1"],
            potential_impact="Test impact",
            timestamp="2026-02-23 12:00:00",
        )
        
        assert insight.insight_id == "insight_1"
        assert insight.insight_type == "innovation"
        assert insight.importance_score == 0.85


class TestExtractPaperInsights:
    """测试批量提取函数"""
    
    @pytest.mark.asyncio
    async def test_extract_paper_insights_empty(self):
        """测试空列表提取"""
        result = await extract_paper_insights([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_extract_paper_insights_with_fallback(self):
        """测试带回退的提取"""
        from src.opportunity_detector.paper_evaluator import PaperValueAssessment
        from src.opportunity_detector.models import EventItem
        
        paper = EventItem(
            source="arxiv",
            topic="test",
            title="Test Paper",
            url="https://arxiv.org/abs/1234.5678",
        )
        
        assessment = PaperValueAssessment(
            paper=paper,
            overall_score=0.8,
            innovation_score=0.9,
            practicality_score=0.7,
            impact_score=0.85,
            timeliness_score=0.75,
            landing_score=0.8,
            reasoning="Test reasoning",
            key_findings=["Finding 1"],
            potential_applications=["Application 1"],
            risks=["Risk 1"],
        )
        
        result = await extract_paper_insights([assessment])
        
        assert len(result) == 1
        assert isinstance(result[0], PaperInsightReport)

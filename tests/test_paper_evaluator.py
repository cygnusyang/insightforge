"""
测试论文价值评估功能
"""
from __future__ import annotations

import pytest

from src.opportunity_detector.paper_evaluator import (
    PaperEvaluator,
    PaperValueAssessment,
    evaluate_papers,
)


class TestPaperEvaluator:
    """测试论文价值评估器"""
    
    def test_fallback_evaluate(self):
        """测试回退评估方案"""
        from src.opportunity_detector.models import EventItem
        
        evaluator = PaperEvaluator()  # 无LLM配置，使用回退方案
        
        paper = EventItem(
            source="arxiv",
            topic="test",
            title="A Novel Approach to AI Coding",
            url="https://arxiv.org/abs/1234.5678",
            meta={
                "summary": "We propose a novel method for AI coding that improves efficiency.",
                "authors": ["Author1", "Author2"],
                "categories": ["cs.AI"],
            },
        )
        
        assessment = evaluator._fallback_evaluate(paper)
        
        assert assessment.paper == paper
        assert 0 <= assessment.overall_score <= 1
        assert 0 <= assessment.innovation_score <= 1
        assert 0 <= assessment.practicality_score <= 1
        assert 0 <= assessment.impact_score <= 1
    
    def test_assessment_fields(self):
        """测试评估结果字段"""
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
            key_findings=["Finding 1", "Finding 2"],
            potential_applications=["Application 1"],
            risks=["Risk 1"],
        )
        
        assert assessment.overall_score == 0.8
        assert assessment.innovation_score == 0.9
        assert len(assessment.key_findings) == 2


class TestEvaluatePapers:
    """测试批量评估函数"""
    
    @pytest.mark.asyncio
    async def test_evaluate_papers_empty(self):
        """测试空列表评估"""
        result = await evaluate_papers([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_evaluate_papers_with_fallback(self):
        """测试带回退的评估"""
        from src.opportunity_detector.models import EventItem
        
        papers = [
            EventItem(
                source="arxiv",
                topic="test",
                title="Test Paper",
                url="https://arxiv.org/abs/1234.5678",
            ),
        ]
        
        result = await evaluate_papers(papers)
        
        assert len(result) == 1
        assert isinstance(result[0], PaperValueAssessment)

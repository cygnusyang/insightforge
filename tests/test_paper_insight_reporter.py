"""
测试论文洞察报告生成器
"""
from __future__ import annotations

import pytest
from datetime import datetime

from src.opportunity_detector.paper_insight_reporter import (
    PaperInsightReporter,
    generate_paper_insight_report,
)


class TestPaperInsightReporter:
    """测试论文洞察报告生成器"""
    
    def test_generate_daily_report_empty(self):
        """测试空报告生成"""
        reporter = PaperInsightReporter()
        
        reports = []
        report = reporter.generate_daily_report(reports, date=datetime(2026, 2, 23))
        
        assert "每日论文洞察报告" in report
        assert "今日分析论文数量：0篇" in report
    
    def test_generate_daily_report_with_data(self):
        """测试带数据的报告生成"""
        from src.opportunity_detector.paper_evaluator import PaperValueAssessment
        from src.opportunity_detector.insight_extractor import KeyInsight, PaperInsightReport
        from src.opportunity_detector.models import EventItem
        
        reporter = PaperInsightReporter()
        
        # 创建测试数据
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
        
        report = PaperInsightReport(
            topic="test",
            paper=paper,
            assessment=assessment,
            key_insights=[insight],
            summary="Test summary",
            timestamp="2026-02-23 12:00:00",
        )
        
        result = reporter.generate_daily_report([report], date=datetime(2026, 2, 23))
        
        assert "每日论文洞察报告" in result
        assert "Test Paper" in result
        assert "Test insight" in result
    
    def test_save_report(self):
        """测试报告保存"""
        reporter = PaperInsightReporter(output_dir="outputs/test_paper_insights")
        
        reports = []
        path = reporter.save_report(reports, date=datetime(2026, 2, 23))
        
        assert path.exists()
        assert path.suffix == ".md"
        
        # 清理测试文件
        path.unlink()
        reporter.output_dir.rmdir()  # 删除空目录
    
    def test_report_structure(self):
        """测试报告结构"""
        reporter = PaperInsightReporter()
        
        reports = []
        report = reporter.generate_daily_report(reports, date=datetime(2026, 2, 23))
        
        # 检查必需的章节
        assert "## 执行摘要" in report
        assert "## 详细论文列表" in report

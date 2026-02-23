"""
论文洞察报告生成器 - 生成每日论文洞察报告
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import EventItem
from .paper_evaluator import PaperValueAssessment
from .insight_extractor import KeyInsight, PaperInsightReport

logger = logging.getLogger(__name__)


class PaperInsightReporter:
    """论文洞察报告生成器"""
    
    def __init__(self, output_dir: str | Path = "outputs/paper_insights"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(
        self,
        reports: List[PaperInsightReport],
        date: Optional[datetime] = None,
    ) -> str:
        """
        生成每日论文洞察报告
        
        Args:
            reports: 论文洞察报告列表
            date: 报告日期，默认为今天
            
        Returns:
            str: Markdown格式的报告内容
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        # 统计信息
        total_papers = len(reports)
        high_value_papers = [r for r in reports if r.assessment.overall_score >= 0.7]
        medium_value_papers = [r for r in reports if 0.5 <= r.assessment.overall_score < 0.7]
        low_value_papers = [r for r in reports if r.assessment.overall_score < 0.5]
        
        # 提取所有洞察
        all_insights = []
        for report in reports:
            all_insights.extend(report.key_insights)
        
        # 按重要性排序
        all_insights.sort(key=lambda x: x.importance_score, reverse=True)
        
        # 生成报告
        lines = []
        lines.append(f"# 每日论文洞察报告（{date_str}）")
        lines.append("")
        lines.append("## 执行摘要")
        lines.append("")
        lines.append(f"- **今日分析论文数量**：{total_papers}篇")
        lines.append(f"- **高价值论文**（评分≥0.7）：{len(high_value_papers)}篇")
        lines.append(f"- **中价值论文**（评分0.5-0.7）：{len(medium_value_papers)}篇")
        lines.append(f"- **低价值论文**（评分<0.5）：{len(low_value_papers)}篇")
        lines.append(f"- **总洞察数量**：{len(all_insights)}条")
        lines.append("")
        
        # 生成研究方向统计
        if reports:
            topics = set(r.topic for r in reports)
            lines.append(f"- **研究方向**：{', '.join(topics)}")
        
        lines.append("")
        
        # 最有价值洞察（Top 5）
        top_insights = all_insights[:5]
        if top_insights:
            lines.append("## 最有价值洞察（Top 5）")
            lines.append("")
            
            for i, insight in enumerate(top_insights, 1):
                lines.append(f"### {i}. {insight.insight_text}")
                lines.append("")
                lines.append(f"- **来源论文**：[{insight.paper.title}]({insight.paper.url})")
                lines.append(f"- **洞察类型**：{insight.insight_type}")
                lines.append(f"- **重要性评分**：{insight.importance_score:.2f}")
                lines.append(f"- **潜在影响**：{insight.potential_impact}")
                lines.append("")
        
        # 详细论文列表
        lines.append("## 详细论文列表")
        lines.append("")
        
        # 按评分排序
        sorted_reports = sorted(reports, key=lambda r: r.assessment.overall_score, reverse=True)
        
        for report in sorted_reports:
            lines.append(f"### {report.paper.title}")
            lines.append("")
            lines.append(f"- **评分**：{report.assessment.overall_score:.2f}")
            lines.append(f"- **创新性**：{report.assessment.innovation_score:.2f}")
            lines.append(f"- **实用性**：{report.assessment.practicality_score:.2f}")
            lines.append(f"- **影响力**：{report.assessment.impact_score:.2f}")
            lines.append(f"- **可落地性**：{report.assessment.landing_score:.2f}")
            lines.append(f"- **摘要**：{report.summary}")
            lines.append("")
        
        # 附录：所有洞察
        if all_insights:
            lines.append("## 附录：所有洞察")
            lines.append("")
            
            for i, insight in enumerate(all_insights, 1):
                lines.append(f"{i}. **[{insight.insight_type}]** {insight.insight_text}")
                lines.append(f"   - 来源：{insight.paper.title}")
                lines.append(f"   - 评分：{insight.importance_score:.2f}")
                lines.append("")
        
        return "\n".join(lines)
    
    def save_report(
        self,
        reports: List[PaperInsightReport],
        filename: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> Path:
        """
        保存报告到文件
        
        Args:
            reports: 论文洞察报告列表
            filename: 文件名，默认为 paper_insights_YYYY-MM-DD.md
            date: 报告日期
            
        Returns:
            Path: 保存的文件路径
        """
        if filename is None:
            if date is None:
                date = datetime.now()
            filename = f"paper_insights_{date.strftime('%Y-%m-%d')}.md"
        
        report_content = self.generate_daily_report(reports, date)
        
        output_path = self.output_dir / filename
        output_path.write_text(report_content, encoding="utf-8")
        
        logger.info(f"报告已保存到：{output_path}")
        return output_path


def generate_paper_insight_report(
    reports: List[PaperInsightReport],
    output_dir: str | Path = "outputs/paper_insights",
    date: Optional[datetime] = None,
) -> Path:
    """
    便捷函数：生成并保存论文洞察报告
    
    Args:
        reports: 论文洞察报告列表
        output_dir: 输出目录
        date: 报告日期
        
    Returns:
        Path: 保存的文件路径
    """
    reporter = PaperInsightReporter(output_dir)
    return reporter.save_report(reports, date=date)

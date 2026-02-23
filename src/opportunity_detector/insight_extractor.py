"""
论文观点提取器 - 从高价值论文中提取最有价值的观点
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .llm import LlmConfig, load_ollama_from_env, ollama_best_effort
from .models import EventItem
from .paper_evaluator import PaperValueAssessment

logger = logging.getLogger(__name__)


@dataclass
class KeyInsight:
    """关键洞察"""
    insight_id: str  # 洞察唯一标识
    paper: EventItem  # 来源论文
    insight_type: str  # 洞察类型（methodology, finding, application, etc.）
    insight_text: str  # 洞察内容
    importance_score: float  # 重要性评分（0-1）
    evidence: List[str]  # 支持证据
    potential_impact: str  # 潜在影响
    timestamp: str  # 提取时间


@dataclass
class PaperInsightReport:
    """论文洞察报告"""
    topic: str  # 主题
    paper: EventItem  # 来源论文
    assessment: PaperValueAssessment  # 评估结果
    key_insights: List[KeyInsight]  # 关键洞察
    summary: str  # 摘要
    timestamp: str  # 生成时间


class InsightExtractor:
    """论文观点提取器"""
    
    def __init__(self, llm_config: Optional[LlmConfig] = None):
        self.llm_config = llm_config or load_ollama_from_env()
    
    async def extract_insights(self, assessment: PaperValueAssessment) -> List[KeyInsight]:
        """
        从论文评估结果中提取关键洞察
        
        Args:
            assessment: 论文评估结果
            
        Returns:
            List[KeyInsight]: 关键洞察列表
        """
        try:
            if not self.llm_config:
                return self._fallback_extract(assessment)
            
            prompt = self._build_prompt(assessment)
            response = await self._call_llm(prompt)
            insights = self._parse_response(response, assessment)
            
            return insights
            
        except Exception as e:
            logger.error(f"观点提取失败: {e}, 使用回退方案")
            return self._fallback_extract(assessment)
    
    async def extract_insights_batch(self, assessments: List[PaperValueAssessment]) -> List[PaperInsightReport]:
        """
        批量提取论文洞察
        
        Args:
            assessments: 论文评估结果列表
            
        Returns:
            List[PaperInsightReport]: 洞察报告列表
        """
        reports = []
        for assessment in assessments:
            insights = await self.extract_insights(assessment)
            report = PaperInsightReport(
                topic=assessment.paper.topic,
                paper=assessment.paper,
                assessment=assessment,
                key_insights=insights,
                summary=self._generate_summary(assessment, insights),
                timestamp=self._get_timestamp()
            )
            reports.append(report)
        return reports
    
    def _build_prompt(self, assessment: PaperValueAssessment) -> str:
        """构建提取提示词"""
        title = assessment.paper.title
        abstract = ((assessment.paper.meta or {}).get("summary", "") or "") or ""
        reasoning = assessment.reasoning
        key_findings = "\n".join(assessment.key_findings) if assessment.key_findings else "无"
        applications = "\n".join(assessment.potential_applications) if assessment.potential_applications else "无"
        
        prompt = f"""请从以下论文评估结果中提取最有价值的观点和洞察：

论文标题：{title}
摘要：{abstract}

评估理由：
{reasoning}

关键发现：
{key_findings}

潜在应用：
{applications}

请提取以下类型的洞察：

1. **核心创新点**：论文的���要技术突破
2. **关键发现**：最重要的实验结果
3. **应用场景**：具体的应用场景和用例
4. **技术优势**：相比现有方案的优势
5. **潜在风险**：需要注意的风险和局限性

请以JSON格式返回：
{{
    "insights": [
        {{
            "insight_id": "insight_1",
            "insight_type": "innovation|finding|application|advantage|risk",
            "insight_text": "洞察内容（简洁明了）",
            "importance_score": 0.85,
            "evidence": ["支持证据1", "支持证据2"],
            "potential_impact": "潜在影响描述"
        }},
        ...
    ]
}}

要求：
- 每个洞察要简洁明了，不超过50字
- importance_score要基于洞察的实际价值
- evidence要引用评估结果中的具体信息
- potential_impact要描述可能的影响范围
"""
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        if not self.llm_config:
            raise ValueError("LLM配置未设置")
        
        system = "你是一个专业的研究论文洞察提取专家。请从论文中提取最有价值的观点。"
        result = ollama_best_effort(cfg=self.llm_config, system=system, user=prompt)
        return result
    
    def _parse_response(self, response: str, assessment: PaperValueAssessment) -> List[KeyInsight]:
        """解析LLM响应"""
        insights = []
        try:
            data = json.loads(response)
            insight_list = data.get("insights", [])
            
            for i, item in enumerate(insight_list, 1):
                insight = KeyInsight(
                    insight_id=f"insight_{i}",
                    paper=assessment.paper,
                    insight_type=item.get("insight_type", "general"),
                    insight_text=item.get("insight_text", ""),
                    importance_score=float(item.get("importance_score", 0.5)),
                    evidence=item.get("evidence", []),
                    potential_impact=item.get("potential_impact", ""),
                    timestamp=self._get_timestamp()
                )
                insights.append(insight)
            
            # 按重要性排序
            insights.sort(key=lambda x: x.importance_score, reverse=True)
            
        except json.JSONDecodeError:
            logger.error(f"LLM响应解析失败: {response}")
            insights = self._fallback_extract(assessment)
        
        return insights
    
    def _fallback_extract(self, assessment: PaperValueAssessment) -> List[KeyInsight]:
        """回退提取方案（基于规则）"""
        insights = []
        
        # 基于评估结果生成洞察
        if assessment.innovation_score > 0.7:
            insights.append(KeyInsight(
                insight_id="insight_1",
                paper=assessment.paper,
                insight_type="innovation",
                insight_text="论文提出了创新的方法或技术",
                importance_score=assessment.innovation_score,
                evidence=["高创新性评分"],
                potential_impact="可能带来技术突破",
                timestamp=self._get_timestamp()
            ))
        
        if assessment.practicality_score > 0.7:
            insights.append(KeyInsight(
                insight_id="insight_2",
                paper=assessment.paper,
                insight_type="application",
                insight_text="论文具有较高的实际应用价值",
                importance_score=assessment.practicality_score,
                evidence=["高实用性评分"],
                potential_impact="可快速落地应用",
                timestamp=self._get_timestamp()
            ))
        
        if assessment.impact_score > 0.7:
            insights.append(KeyInsight(
                insight_id="insight_3",
                paper=assessment.paper,
                insight_type="finding",
                insight_text="论文可能对行业产生重要影响",
                importance_score=assessment.impact_score,
                evidence=["高影响力评分"],
                potential_impact="可能改变行业格局",
                timestamp=self._get_timestamp()
            ))
        
        return insights
    
    def _generate_summary(self, assessment: PaperValueAssessment, insights: List[KeyInsight]) -> str:
        """生成洞察摘要"""
        if not insights:
            return "暂无关键洞察"
        
        top_insights = insights[:3]
        insight_texts = [i.insight_text for i in top_insights]
        
        return "；".join(insight_texts)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def extract_paper_insights(assessments: List[PaperValueAssessment]) -> List[PaperInsightReport]:
    """
    便捷函数：提取论文洞察
    
    Args:
        assessments: 论文评估结果列表
        
    Returns:
        List[PaperInsightReport]: 洞察报告列表
    """
    extractor = InsightExtractor()
    return await extractor.extract_insights_batch(assessments)

"""
论文价值评估器 - 基于LLM的论文价值评估功能
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .llm import LlmConfig, load_ollama_from_env, ollama_best_effort
from .models import EventItem

logger = logging.getLogger(__name__)


@dataclass
class PaperValueAssessment:
    """论文价值评估结果"""
    paper: EventItem
    overall_score: float  # 综合评分（0-1）
    innovation_score: float  # 创新性（0-1）
    practicality_score: float  # 实用性（0-1）
    impact_score: float  # 影响力（0-1）
    timeliness_score: float  # 时效性（0-1）
    landing_score: float  # 可落地性（0-1）
    reasoning: str  # 评估理由
    key_findings: List[str]  # 关键发现
    potential_applications: List[str]  # 潜在应用
    risks: List[str]  # 风险提示


class PaperEvaluator:
    """论文价值评估器"""
    
    def __init__(self, llm_config: Optional[LlmConfig] = None):
        self.llm_config = llm_config or load_ollama_from_env()
    
    async def evaluate(self, paper: EventItem) -> PaperValueAssessment:
        """
        评估单篇论文的价值
        
        Args:
            paper: 论文事件项
            
        Returns:
            PaperValueAssessment: 评估结果
        """
        try:
            if not self.llm_config:
                return self._fallback_evaluate(paper)
            
            prompt = self._build_prompt(paper)
            response = self._call_llm(prompt)
            result = self._parse_response(response, paper)
            
            return result
            
        except Exception as e:
            logger.error(f"论文评估失败: {e}, 使用回退方案")
            return self._fallback_evaluate(paper)
    
    async def evaluate_batch(self, papers: List[EventItem]) -> List[PaperValueAssessment]:
        """
        批量评估论文
        
        Args:
            papers: 论文列表
            
        Returns:
            List[PaperValueAssessment]: 评估结果列表
        """
        assessments = []
        for paper in papers:
            assessment = await self.evaluate(paper)
            assessments.append(assessment)
        return assessments
    
    def _build_prompt(self, paper: EventItem) -> str:
        """构建评估提示词"""
        title = paper.title
        abstract = (paper.meta or {}).get("summary", "") or ""
        authors = (paper.meta or {}).get("authors", []) or []
        categories = (paper.meta or {}).get("categories", []) or []
        
        prompt = f"""请评估以下研究论文的价值，从多个维度进行评分（0-1范围）：

论文标题：{title}
作者：{', '.join(authors) if authors else '未知'}
分类：{', '.join(categories) if categories else '未知'}
摘要：{abstract}

请从以下维度进行评估：

1. **创新性**（0-1）：方法是否新颖？是否有突破性贡献？
2. **实用性**（0-1）：是否有实际应用价值？能否解决现实问题？
3. **影响力**（0-1）：可能对行业/领域产生多大影响？
4. **时效性**（0-1）：与当前热点相关性如何？
5. **可落地性**（0-1）：技术可行性如何？多久能产品化？

请以JSON格式返回：
{{
    "innovation_score": 0.85,
    "practicality_score": 0.75,
    "impact_score": 0.80,
    "timeliness_score": 0.90,
    "landing_score": 0.70,
    "overall_score": 0.80,
    "reasoning": "详细评估理由，包含各维度的判断依据",
    "key_findings": ["关键发现1", "关键发现2", "关键发现3"],
    "potential_applications": ["潜在应用1", "潜在应用2"],
    "risks": ["技术风险1", "应用风险1"]
}}

要求：
- 评分要基于论文内容，不要过度乐观或悲观
- 理由要具体，包含关键判断依据
- 关键发现要提炼核心贡献
- 潜在应用要结合实际场景
- 风险要客观指出可能的问题
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        if not self.llm_config:
            raise ValueError("LLM配置未设置")
        
        system = "你是一个专业的研究论文评估专家。请基于论文内容进行客观、专业的价值评估。"
        result = ollama_best_effort(cfg=self.llm_config, system=system, user=prompt)
        return result
    
    def _parse_response(self, response: str, paper: EventItem) -> PaperValueAssessment:
        """解析LLM响应"""
        try:
            # 尝试解析JSON
            data = json.loads(response)
            
            return PaperValueAssessment(
                paper=paper,
                overall_score=float(data.get("overall_score", 0.5)),
                innovation_score=float(data.get("innovation_score", 0.5)),
                practicality_score=float(data.get("practicality_score", 0.5)),
                impact_score=float(data.get("impact_score", 0.5)),
                timeliness_score=float(data.get("timeliness_score", 0.5)),
                landing_score=float(data.get("landing_score", 0.5)),
                reasoning=data.get("reasoning", "评估完成"),
                key_findings=data.get("key_findings", []),
                potential_applications=data.get("potential_applications", []),
                risks=data.get("risks", [])
            )
            
        except json.JSONDecodeError:
            logger.error(f"LLM响应解析失败: {response}")
            return self._fallback_evaluate(paper)
    
    def _fallback_evaluate(self, paper: EventItem) -> PaperValueAssessment:
        """回退评估方案（基于规则）"""
        title = paper.title.lower()
        abstract = ((paper.meta or {}).get("summary", "") or "").lower()
        
        # 简单的关键词匹配规则
        innovation_keywords = ["novel", "new approach", "first", "breakthrough", "innovative"]
        practical_keywords = ["application", "practical", "real-world", "implementation", "system"]
        impact_keywords = ["large", "significant", "impact", "transformative", "broad"]
        
        innovation_score = 0.5
        practical_score = 0.5
        impact_score = 0.5
        
        for kw in innovation_keywords:
            if kw in title or kw in abstract:
                innovation_score = min(1.0, innovation_score + 0.15)
        
        for kw in practical_keywords:
            if kw in title or kw in abstract:
                practical_score = min(1.0, practical_score + 0.15)
        
        for kw in impact_keywords:
            if kw in title or kw in abstract:
                impact_score = min(1.0, impact_score + 0.15)
        
        overall_score = (innovation_score + practical_score + impact_score) / 3
        
        return PaperValueAssessment(
            paper=paper,
            overall_score=round(overall_score, 2),
            innovation_score=round(innovation_score, 2),
            practicality_score=round(practical_score, 2),
            impact_score=round(impact_score, 2),
            timeliness_score=0.5,
            landing_score=0.5,
            reasoning="基于关键词匹配的回退评估",
            key_findings=[],
            potential_applications=[],
            risks=[]
        )


async def evaluate_papers(papers: List[EventItem]) -> List[PaperValueAssessment]:
    """
    便捷函数：评估论文列表
    
    Args:
        papers: 论文列表
        
    Returns:
        List[PaperValueAssessment]: 评估结果列表
    """
    evaluator = PaperEvaluator()
    return await evaluator.evaluate_batch(papers)

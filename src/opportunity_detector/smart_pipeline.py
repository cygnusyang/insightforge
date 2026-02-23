"""
智能洞察Pipeline - 集成LLM增强的洞察生成
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .config import DetectorConfig
from .models import TopicRawSignals, TopicScored
from .llm import LlmConfig, load_ollama_from_env
from .smart_insights import (
    SmartIndustryClassifier,
    SmartInsightTypePredictor,
    DynamicCommercialAdvisor,
    EnhancedConfidenceEvaluator,
    MultiDimensionalEvidenceFusion,
    IndustryClassification,
    InsightTypePrediction,
    CommercialAdvice,
    ConfidenceScore,
    ComprehensiveEvidence,
)
from .insights import build_topic_insights, render_insights_markdown, TopicInsight

logger = logging.getLogger(__name__)


class SmartInsightBuilder:
    """智能洞察构建器 - 使用LLM增强洞察质量"""
    
    def __init__(self, llm_config: Optional[LlmConfig] = None):
        self.llm_config = llm_config or load_ollama_from_env()
        self.industry_classifier = SmartIndustryClassifier(self.llm_config) if self.llm_config else None
        self.insight_type_predictor = SmartInsightTypePredictor(self.llm_config) if self.llm_config else None
        self.commercial_advisor = DynamicCommercialAdvisor(self.llm_config) if self.llm_config else None
        self.confidence_evaluator = EnhancedConfidenceEvaluator()
        self.evidence_fusion = MultiDimensionalEvidenceFusion()
        
        # 标记是否启用LLM
        self.use_llm = self.llm_config is not None
        
    async def build_smart_insight(
        self,
        topic: str,
        scored: TopicScored,
        raw: TopicRawSignals
    ) -> dict:
        """构建智能洞察"""
        
        # 1. 智能行业分类
        if self.use_llm and self.industry_classifier:
            industry_result = await self.industry_classifier.classify(topic, scored, raw)
            industry = industry_result.industry
            industry_confidence = industry_result.confidence
            industry_reasoning = industry_result.reasoning
        else:
            # 回退到原始规则
            industry = self._fallback_industry_guess(topic)
            industry_confidence = 0.6
            industry_reasoning = "基于规则分类"
            
        # 2. 智能洞察类型预测
        if self.use_llm and self.insight_type_predictor:
            type_result = await self.insight_type_predictor.predict(
                topic, industry, scored, raw
            )
            insight_type = type_result.insight_type
            type_confidence = type_result.confidence
            type_reasoning = type_result.reasoning
            suggested_play = type_result.suggested_play
        else:
            # 回退到原始规则
            type_result = self.insight_type_predictor._fallback_predict(scored) if self.insight_type_predictor else None
            insight_type = type_result.insight_type if type_result else "watchlist"
            type_confidence = type_result.confidence if type_result else 0.5
            type_reasoning = type_result.reasoning if type_result else "基于规则判断"
            suggested_play = type_result.suggested_play if type_result else "持续监测市场动态"
            
        # 3. 动态商业建议生成
        if self.use_llm and self.commercial_advisor:
            industry_template = self._get_industry_template(industry)
            advice = await self.commercial_advisor.generate_advice(
                topic=topic,
                industry=industry,
                insight_type=insight_type,
                market_signals={
                    "demand_norm": scored.demand_norm,
                    "momentum_norm": scored.momentum_norm,
                    "competition_norm": scored.competition_norm
                },
                industry_template=industry_template
            )
            one_line_thesis = advice.one_line_thesis
            target_customer = advice.target_customer
            first_sellable_feature = advice.first_sellable_feature
        else:
            # 回退到原始模板
            one_line_thesis, target_customer, first_sellable_feature = self._fallback_commercial_pack(
                insight_type, topic, industry
            )
            
        # 4. 增强置信度评估
        llm_analysis = {
            "confidence": type_confidence,
            "industry_confidence": industry_confidence
        }
        confidence_score = self.confidence_evaluator.calculate_confidence(
            raw_signals=raw,
            scored_signals=scored,
            llm_analysis=llm_analysis
        )
        
        # 5. 多维度证据融合
        llm_insights = {
            "market_analysis": type_reasoning,
            "industry_insights": industry_reasoning,
            "trend_analysis": f"洞察类型: {insight_type}",
            "opportunity_score": scored.opportunity_score,
            "risk_factors": [],
            "competitive_analysis": f"竞争强度: {scored.competition_norm:.2f}",
            "user_insights": f"目标客户: {target_customer}",
            "tech_trends": "基于当前市场信号分析"
        }
        comprehensive_evidence = self.evidence_fusion.fuse_evidence(
            raw_signals=raw,
            scored_signals=scored,
            llm_insights=llm_insights
        )
        
        return {
            "topic": topic,
            "industry_guess": industry,
            "opportunity_score": scored.opportunity_score,
            "opportunity_band": self._band(scored.opportunity_score),
            "insight_type": insight_type,
            "confidence": round(confidence_score.overall, 3),
            "one_line_thesis": one_line_thesis,
            "target_customer": target_customer,
            "first_sellable_feature": first_sellable_feature,
            "evidence": comprehensive_evidence.summary,
            "suggested_play": suggested_play,
            # 扩展信息
            "llm_analysis": {
                "industry_confidence": industry_confidence,
                "type_confidence": type_confidence,
                "industry_reasoning": industry_reasoning,
                "type_reasoning": type_reasoning
            },
            "confidence_factors": confidence_score.factors,
            "confidence_reasoning": confidence_score.reasoning,
            "evidence_summary": comprehensive_evidence.summary,
            "detailed_analysis": comprehensive_evidence.detailed_analysis,
            "supporting_metrics": comprehensive_evidence.supporting_metrics,
            "qualitative_insights": comprehensive_evidence.qualitative_insights
        }
    
    def _fallback_industry_guess(self, topic: str) -> str:
        """回退的行业分类"""
        keyword_groups = {
            "healthcare": ["clinic", "health", "hospital", "医疗", "诊所", "医药"],
            "manufacturing": ["manufacturing", "factory", "quality", "制造", "工厂", "质检"],
            "ecommerce": ["ecommerce", "shop", "retail", "跨境", "电商", "零售"],
            "finance": ["finance", "accounting", "reconciliation", "财务", "金融", "对账"],
            "hr": ["hr", "onboarding", "hiring", "人力", "招聘", "入职"],
            "logistics": ["logistics", "supply chain", "warehouse", "物流", "仓储", "供应链"],
            "developer_tools": ["coding", "developer", "devops", "aiops", "代码", "研发"],
            "customer_support": ["support", "客服", "call center", "helpdesk"],
        }
        
        normalized = topic.lower()
        for industry, keywords in keyword_groups.items():
            if any(keyword in normalized for keyword in keywords):
                return industry
        return "general_b2b"
    
    def _get_industry_template(self, industry: str) -> Optional[tuple[str, str]]:
        """获取行业模板"""
        templates = {
            "healthcare": (
                "连锁诊所/专科门诊运营负责人",
                "预约-分诊-随访一体化自动化工作流（含合规留痕）",
            ),
            "manufacturing": (
                "工厂质量与生产运营负责人",
                "质检异常自动归因与返工闭环看板",
            ),
            "ecommerce": (
                "跨境/品牌电商运营负责人",
                "订单履约异常预警与自动工单分派",
            ),
            "finance": (
                "财务共享中心或中小企业财务经理",
                "自动对账与差异原因追踪面板",
            ),
            "hr": (
                "HRBP 或招聘运营负责人",
                "入职流程自动化 + 文档校验助手",
            ),
            "logistics": (
                "物流调度与仓配运营负责人",
                "运输延误预测 + 异常任务自动派单",
            ),
            "developer_tools": (
                "研发效能或平台工程负责人",
                "代码规范巡检 + 发布风险审计助手",
            ),
            "customer_support": (
                "客服运营负责人",
                "工单分流 + 回复草拟 + SLA 风险预警",
            ),
            "general_b2b": (
                "中小企业业务流程负责人",
                "单流程自动化插件（可量化节省人时）",
            ),
        }
        return templates.get(industry)
    
    def _fallback_commercial_pack(
        self, 
        insight_type: str, 
        topic: str, 
        industry: str
    ) -> tuple[str, str, str]:
        """回退的商业建议生成"""
        if insight_type == "fast_growing_white_space":
            return (
                f"{topic} 处于高增长且竞争相对可控阶段，适合快速切入。",
                "有明确流程痛点、预算有限但决策快的中小团队负责人",
                "围绕一个高频流程的自动化工作台（含可量化 ROI 看板）",
            )
        if insight_type == "crowded_hot_market":
            return (
                f"{topic} 需求强但同类供给密集，必须垂直化定位。",
                "细分行业中的一线运营/交付团队，而非泛用户",
                "行业模板 + 私有数据接入 + 结果审计的垂直 Copilot",
            )
        if insight_type == "early_signal_niche":
            return (
                f"{topic} 出现早期需求信号，可先做小规模付费验证。",
                "愿意尝鲜、痛点突出、可快速反馈的早期采用者团队",
                "单点痛点工具（如自动报表/自动分单）+ 人工兜底",
            )
        if insight_type == "steady_pain_low_competition":
            return (
                f"{topic} 需求稳定且竞争压力较低，适合做效率替代。",
                "已有手工流程、希望降本提效的业务负责人",
                "现有系统外挂式自动化插件（最小改造即可上线）",
            )
        return (
            f"{topic} 当前信号仍偏弱，建议继续观察并补充关键词。",
            "需求尚不确定的探索型团队",
            "低成本监测面板（关键词趋势 + 异动告警）",
        )
    
    def _band(self, score: float) -> str:
        """机会等级划分"""
        if score >= 0.7:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"


async def build_smart_topic_insights(
    raw_signals: list[TopicRawSignals],
    scored_topics: list[TopicScored],
    llm_config: Optional[LlmConfig] = None
) -> list[TopicInsight]:
    """构建智能主题洞察（异步）"""
    builder = SmartInsightBuilder(llm_config)
    
    insights = []
    for scored in scored_topics:
        raw = next((r for r in raw_signals if r.topic == scored.topic), None)
        if raw:
            insight_dict = await builder.build_smart_insight(scored.topic, scored, raw)
            # 将dict转换为TopicInsight对象
            insight = TopicInsight(
                topic=insight_dict["topic"],
                industry_guess=insight_dict["industry_guess"],
                opportunity_score=insight_dict["opportunity_score"],
                opportunity_band=insight_dict["opportunity_band"],
                insight_type=insight_dict["insight_type"],
                confidence=insight_dict["confidence"],
                one_line_thesis=insight_dict["one_line_thesis"],
                target_customer=insight_dict["target_customer"],
                first_sellable_feature=insight_dict["first_sellable_feature"],
                evidence=insight_dict["evidence"],
                suggested_play=insight_dict["suggested_play"],
            )
            insights.append(insight)
            
    return insights


def build_smart_topic_insights_sync(
    raw_signals: list[TopicRawSignals],
    scored_topics: list[TopicScored],
    llm_config: Optional[LlmConfig] = None
) -> list[TopicInsight]:
    """构建智能主题洞察（同步）"""
    return asyncio.run(build_smart_topic_insights(raw_signals, scored_topics, llm_config))

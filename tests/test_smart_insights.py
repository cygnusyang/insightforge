"""
智能洞察生成器测试
"""
from src.opportunity_detector.smart_insights import (
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
from src.opportunity_detector.models import TopicRawSignals, TopicScored
from src.opportunity_detector.llm import LlmConfig


def test_industry_classifier_fallback():
    """测试行业分类器的回退方案"""
    classifier = SmartIndustryClassifier(llm_config=None)
    
    # 测试医疗相关主题
    result = classifier._fallback_classify("clinic management saas")
    assert result.industry == "healthcare"
    assert result.confidence > 0
    
    # 测试制造相关主题
    result = classifier._fallback_classify("factory quality control")
    assert result.industry == "manufacturing"
    
    # 测试通用主题
    result = classifier._fallback_classify("generic platform")
    assert result.industry == "general_b2b"


def test_insight_type_predictor_fallback():
    """测试洞察类型预测器的回退方案"""
    predictor = SmartInsightTypePredictor(llm_config=None)
    
    # 测试高需求高增长低竞争场景
    scored = TopicScored(
        topic="test topic",
        demand_raw=100.0,
        momentum_raw=0.8,
        competition_raw=15.0,
        demand_norm=0.9,
        momentum_norm=0.9,
        competition_norm=0.2,
        opportunity_score=0.82,
    )
    
    result = predictor._fallback_predict(scored)
    assert result.insight_type == "fast_growing_white_space"
    assert result.confidence > 0


def test_commercial_advisor_template():
    """测试商业建议生成器的模板方案"""
    advisor = DynamicCommercialAdvisor(llm_config=None)
    
    # 测试fast_growing_white_space类型
    advice = advisor._template_advice(
        topic="test topic",
        industry="healthcare",
        insight_type="fast_growing_white_space",
        industry_template=("目标客户", "功能模板")
    )
    
    assert len(advice.one_line_thesis) > 0
    assert len(advice.target_customer) > 0
    assert len(advice.first_sellable_feature) > 0


def test_confidence_evaluator():
    """测试增强置信度评估器"""
    evaluator = EnhancedConfidenceEvaluator()
    
    raw = TopicRawSignals(
        topic="test topic",
        gdelt_total=50,
        gdelt_recent=30,
        hn_total=30,
        hn_recent=20,
        github_total=20,
        github_recent=15,
        reddit_total=40,
        reddit_recent=25,
    )
    
    scored = TopicScored(
        topic="test topic",
        demand_raw=100.0,
        momentum_raw=0.8,
        competition_raw=15.0,
        demand_norm=0.7,
        momentum_norm=0.6,
        competition_norm=0.3,
        opportunity_score=0.65,
    )
    
    llm_analysis = {
        "confidence": 0.8,
        "industry_confidence": 0.7
    }
    
    result = evaluator.calculate_confidence(
        raw_signals=raw,
        scored_signals=scored,
        llm_analysis=llm_analysis
    )
    
    assert isinstance(result, ConfidenceScore)
    assert 0.0 <= result.overall <= 1.0
    assert len(result.factors) > 0
    assert len(result.reasoning) > 0


def test_evidence_fusion():
    """测试多维度证据融合器"""
    fusion = MultiDimensionalEvidenceFusion()
    
    raw = TopicRawSignals(
        topic="test topic",
        gdelt_total=100,
        gdelt_recent=60,
        hn_total=50,
        hn_recent=30,
        github_total=30,
        github_recent=20,
        reddit_total=70,
        reddit_recent=40,
    )
    
    scored = TopicScored(
        topic="test topic",
        demand_raw=150.0,
        momentum_raw=0.9,
        competition_raw=20.0,
        demand_norm=0.8,
        momentum_norm=0.75,
        competition_norm=0.25,
        opportunity_score=0.72,
    )
    
    llm_insights = {
        "market_analysis": "市场分析",
        "industry_insights": "行业洞察",
        "trend_analysis": "趋势分析",
        "opportunity_score": 0.72,
        "risk_factors": [],
        "competitive_analysis": "竞争分析",
        "user_insights": "用户洞察",
        "tech_trends": "技术趋势"
    }
    
    result = fusion.fuse_evidence(
        raw_signals=raw,
        scored_signals=scored,
        llm_insights=llm_insights
    )
    
    assert isinstance(result, ComprehensiveEvidence)
    assert len(result.summary) > 0
    assert len(result.detailed_analysis) > 0
    assert len(result.supporting_metrics) > 0
    assert len(result.qualitative_insights) > 0
    assert len(result.confidence_indicators) > 0


def test_smart_insight_builder_integration():
    """测试智能洞察构建器的集成"""
    from src.opportunity_detector.smart_pipeline import SmartInsightBuilder
    
    builder = SmartInsightBuilder(llm_config=None)
    
    raw = TopicRawSignals(
        topic="clinic management saas",
        gdelt_total=80,
        gdelt_recent=50,
        hn_total=40,
        hn_recent=25,
        github_total=30,
        github_recent=20,
        reddit_total=60,
        reddit_recent=35,
    )
    
    scored = TopicScored(
        topic="clinic management saas",
        demand_raw=120.0,
        momentum_raw=0.85,
        competition_raw=18.0,
        demand_norm=0.85,
        momentum_norm=0.8,
        competition_norm=0.22,
        opportunity_score=0.78,
    )
    
    # 测试同步方法
    import asyncio
    result = asyncio.run(builder.build_smart_insight(
        topic="clinic management saas",
        scored=scored,
        raw=raw
    ))
    
    assert "topic" in result
    assert "industry_guess" in result
    assert "opportunity_score" in result
    assert "confidence" in result
    assert "one_line_thesis" in result
    assert "target_customer" in result
    assert "first_sellable_feature" in result
    assert "suggested_play" in result
    assert "llm_analysis" in result
    assert "confidence_factors" in result
    assert "evidence_summary" in result

"""
智能洞察生成器 - 使用LLM增强洞察质量
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .llm import LlmConfig
from .models import TopicRawSignals, TopicScored

logger = logging.getLogger(__name__)


@dataclass
class IndustryClassification:
    """行业分类结果"""
    industry: str
    confidence: float
    reasoning: str


@dataclass 
class InsightTypePrediction:
    """洞察类型预测结果"""
    insight_type: str
    confidence: float
    reasoning: str
    suggested_play: str


@dataclass
class CommercialAdvice:
    """商业建议"""
    one_line_thesis: str
    target_customer: str
    first_sellable_feature: str
    suggested_play: str


@dataclass
class ConfidenceScore:
    """增强置信度评分"""
    overall: float
    factors: Dict[str, float]
    reasoning: str


@dataclass
class ComprehensiveEvidence:
    """综合证据"""
    summary: str
    detailed_analysis: str
    supporting_metrics: Dict[str, Any]
    qualitative_insights: Dict[str, Any]
    confidence_indicators: Dict[str, float]


class SmartIndustryClassifier:
    """智能行业分类器"""
    
    INDUSTRIES = [
        "healthcare", "manufacturing", "ecommerce", "finance", 
        "hr", "logistics", "developer_tools", "customer_support", "general_b2b"
    ]
    
    def __init__(self, llm_config: Optional[LlmConfig] = None):
        self.llm_config = llm_config
        self.prompt_template = """基于以下主题和相关数据，判断最匹配的行业分类：

主题：{topic}
需求得分：{demand_score}
动量得分：{momentum_score}
竞争得分：{competition_score}
相关关键词：{keywords}
数据源分布：GDELT={gdelt_total}, HackerNews={hn_total}, GitHub={github_total}, Reddit={reddit_total}

可选行业：
- healthcare: 医疗健康、诊所、医院、医药相关
- manufacturing: 制造业、工厂、质量控制、生产相关  
- ecommerce: 电子商务、零售、跨境电商、在线销售
- finance: 金融、财务、会计、对账、支付相关
- hr: 人力资源、招聘、入职、员工管理
- logistics: 物流、供应链、仓储、运输
- developer_tools: 开发工具、代码、研发、DevOps
- customer_support: 客服、支持、呼叫中心、帮助台
- general_b2b: 通用B2B服务、其他商业服务

请考虑：
1. 主题的核心业务场景和应用领域
2. 目标用户群体特征和行业属性
3. 行业发展趋势和数字化程度
4. 技术应用特点和解决方案类型
5. 数据源特征和讨论热度分布

返回JSON格式：{{"industry": "行业名称", "confidence": 0.95, "reasoning": "详细分类理由，包含关键判断依据"}}
"""

    async def classify(self, topic: str, scored: TopicScored, raw: TopicRawSignals) -> IndustryClassification:
        """智能行业分类"""
        try:
            # 构建提示词
            keywords = self._extract_keywords(topic)
            prompt = self.prompt_template.format(
                topic=topic,
                demand_score=scored.demand_norm,
                momentum_score=scored.momentum_norm,
                competition_score=scored.competition_norm,
                keywords=", ".join(keywords),
                gdelt_total=raw.gdelt_total,
                hn_total=raw.hn_total,
                github_total=raw.github_total,
                reddit_total=raw.reddit_total
            )
            
            # 调用LLM进行分类
            response = await self._call_llm(prompt)
            result = self._parse_llm_response(response)
            
            return IndustryClassification(
                industry=result.get("industry", "general_b2b"),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "基于规则分类")
            )
            
        except Exception as e:
            logger.error(f"行业分类失败: {e}, 使用回退方案")
            # 回退到基于规则的分类
            return self._fallback_classify(topic)

    def _extract_keywords(self, topic: str) -> List[str]:
        """提取主题关键词"""
        # 简单的关键词提取，可以后续增强
        words = topic.lower().split()
        # 过滤常见词
        stop_words = {'for', 'the', 'and', 'or', 'in', 'on', 'at', 'to', 'from', 'by', 'with'}
        return [word for word in words if word not in stop_words and len(word) > 2]

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        # 这里需要实现具体的LLM调用逻辑
        # 暂时返回模拟结果
        return json.dumps({
            "industry": "general_b2b",
            "confidence": 0.8,
            "reasoning": "基于主题内容判断为通用B2B服务"
        })

    def _parse_llm_response(self, response: str) -> dict:
        """解析LLM响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"LLM响应解析失败: {response}")
            return {"industry": "general_b2b", "confidence": 0.5, "reasoning": "解析失败，使用默认值"}

    def _fallback_classify(self, topic: str) -> IndustryClassification:
        """回退分类方案"""
        keyword_groups = {
            "healthcare": ["clinic", "health", "hospital", "医疗", "诊所", "医药", "医院", "健康"],
            "manufacturing": ["manufacturing", "factory", "quality", "制造", "工厂", "质检", "生产"],
            "ecommerce": ["ecommerce", "shop", "retail", "跨境", "电商", "零售", "销售"],
            "finance": ["finance", "accounting", "reconciliation", "财务", "金融", "对账", "支付"],
            "hr": ["hr", "onboarding", "hiring", "人力", "招聘", "入职", "员工"],
            "logistics": ["logistics", "supply", "warehouse", "物流", "仓储", "供应链", "运输"],
            "developer_tools": ["coding", "developer", "devops", "aiops", "代码", "研发", "开发"],
            "customer_support": ["support", "客服", "call", "helpdesk", "服务", "支持"],
        }

        normalized = topic.lower()
        best_match = "general_b2b"
        confidence = 0.6

        for industry, keywords in keyword_groups.items():
            matches = sum(1 for keyword in keywords if keyword in normalized)
            if matches > 0:
                best_match = industry
                confidence = min(0.6 + matches * 0.1, 0.9)
                break

        return IndustryClassification(
            industry=best_match,
            confidence=confidence,
            reasoning=f"基于关键词匹配: {topic}"
        )


class SmartInsightTypePredictor:
    """智能洞察类型预测器"""
    
    def __init__(self, llm_config: Optional[LlmConfig] = None):
        self.llm_config = llm_config
        self.prompt_template = """基于以下市场信号，判断最佳的洞察类型和商业策略：

主题：{topic}
需求强度：{demand_norm} (0-1，越高表示需求越强)
市场动量：{momentum_norm} (0-1，越高表示增长越快)
竞争强度：{competition_norm} (0-1，越高表示竞争越激烈)
行业分类：{industry}
数据源活跃度：GDELT={gdelt_total}, HN={hn_total}, GitHub={github_total}, Reddit={reddit_total}

洞察类型定义：
- fast_growing_white_space: 高需求高增长且竞争相对可控，适合快速切入
- crowded_hot_market: 需求强但竞争激烈，需要差异化定位
- early_signal_niche: 早期需求信号，适合小规模验证
- steady_pain_low_competition: 稳定需求低竞争，适合效率提升
- watchlist: 信号偏弱，需要持续观察

请考虑：
1. 市场成熟度和增长潜力
2. 竞争格局和差异化机会
3. 进入时机和风险评估
4. 资源配置和执行难度
5. 行业特性和用户行为

返回JSON格式：{{
    "insight_type": "类型名称",
    "confidence": 0.92,
    "reasoning": "详细判断理由，包含关键考虑因素",
    "suggested_play": "具体商业建议，要具有可执行性"
}}
"""

    async def predict(
        self, 
        topic: str, 
        industry: str, 
        scored: TopicScored, 
        raw: TopicRawSignals
    ) -> InsightTypePrediction:
        """智能洞察类型预测"""
        try:
            prompt = self.prompt_template.format(
                topic=topic,
                demand_norm=scored.demand_norm,
                momentum_norm=scored.momentum_norm,
                competition_norm=scored.competition_norm,
                industry=industry,
                gdelt_total=raw.gdelt_total,
                hn_total=raw.hn_total,
                github_total=raw.github_total,
                reddit_total=raw.reddit_total
            )
            
            response = await self._call_llm(prompt)
            result = self._parse_llm_response(response)
            
            return InsightTypePrediction(
                insight_type=result.get("insight_type", "watchlist"),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "基于规则判断"),
                suggested_play=result.get("suggested_play", "持续监测市场动态")
            )
            
        except Exception as e:
            logger.error(f"洞察类型预测失败: {e}, 使用回退方案")
            return self._fallback_predict(scored)

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        # 暂时返回模拟结果
        return json.dumps({
            "insight_type": "fast_growing_white_space",
            "confidence": 0.85,
            "reasoning": "高需求低竞争，适合快速切入",
            "suggested_play": "优先做垂直场景MVP，抢占市场先机"
        })

    def _parse_llm_response(self, response: str) -> dict:
        """解析LLM响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"LLM响应解析失败: {response}")
            return {
                "insight_type": "watchlist", 
                "confidence": 0.5,
                "reasoning": "解析失败，使用默认值",
                "suggested_play": "持续监测市场动态"
            }

    def _fallback_predict(self, scored: TopicScored) -> InsightTypePrediction:
        """回退预测方案 - 使用原始规则"""
        d = scored.demand_norm
        m = scored.momentum_norm
        c = scored.competition_norm

        if d >= 0.6 and m >= 0.6 and c <= 0.4:
            insight_type = "fast_growing_white_space"
            suggested_play = "优先做垂直场景 MVP，先抢 1-2 个高频流程"
            confidence = 0.8
        elif d >= 0.6 and c >= 0.7:
            insight_type = "crowded_hot_market"
            suggested_play = "避免通用功能内卷，选择细分人群 + 差异化数据/交付"
            confidence = 0.75
        elif d <= 0.4 and m >= 0.6 and c <= 0.4:
            insight_type = "early_signal_niche"
            suggested_play = "用低成本实验验证付费意愿，再决定是否加码"
            confidence = 0.7
        elif d >= 0.4 and m <= 0.3 and c <= 0.4:
            insight_type = "steady_pain_low_competition"
            suggested_play = "从效率提升切入，主打 ROI 和替代人工"
            confidence = 0.75
        else:
            insight_type = "watchlist"
            suggested_play = "先持续监测 2-4 周，观察动量是否继续提升"
            confidence = 0.6

        return InsightTypePrediction(
            insight_type=insight_type,
            confidence=confidence,
            reasoning=f"基于规则引擎: 需求={d:.2f}, 动量={m:.2f}, 竞争={c:.2f}",
            suggested_play=suggested_play
        )


class DynamicCommercialAdvisor:
    """动态商业建议生成器"""
    
    def __init__(self, llm_config: Optional[LlmConfig] = None):
        self.llm_config = llm_config
        
    async def generate_advice(
        self, 
        topic: str,
        industry: str,
        insight_type: str,
        market_signals: dict,
        industry_template: Optional[Tuple[str, str]] = None
    ) -> CommercialAdvice:
        """生成动态商业建议"""
        try:
            prompt = self._build_prompt(
                topic, industry, insight_type, market_signals, industry_template
            )
            
            response = await self._call_llm(prompt)
            result = self._parse_llm_response(response)
            
            return CommercialAdvice(
                one_line_thesis=result.get("one_line_thesis", f"{topic} 存在商业机会"),
                target_customer=result.get("target_customer", "中小企业业务流程负责人"),
                first_sellable_feature=result.get("first_sellable_feature", "基础自动化功能"),
                suggested_play=result.get("suggested_play", "持续监测市场动态")
            )
            
        except Exception as e:
            logger.error(f"商业建议生成失败: {e}, 使用模板方案")
            return self._template_advice(topic, industry, insight_type, industry_template)

    def _build_prompt(
        self,
        topic: str,
        industry: str,
        insight_type: str,
        market_signals: dict,
        industry_template: Optional[Tuple[str, str]]
    ) -> str:
        """构建提示词"""
        base_prompt = f"""为以下商业机会生成个性化的商业建议：

机会主题：{topic}
行业分类：{industry}
洞察类型：{insight_type}
市场信号：{market_signals}

需要生成：
1. 一句话商业论点 (one_line_thesis)：概括核心商业价值和机会
2. 目标客户描述 (target_customer)：具体描述目标客户群体和特征
3. 首个可销售功能 (first_sellable_feature)：最小可行产品的核心功能
4. 具体执行建议 (suggested_play)：可执行的市场进入策略

要求：
- 结合{industry}行业特点和发展趋势
- 考虑当前市场竞争状况和差异化机会
- 突出独特价值和竞争优势
- 具有实际可执行性和商业可行性
- 基于{insight_type}类型的特征制定策略

返回JSON格式：{{
    "one_line_thesis": "...",
    "target_customer": "...",
    "first_sellable_feature": "...",
    "suggested_play": "..."
}}
"""
        
        if industry_template:
            customer_template, feature_template = industry_template
            base_prompt += f"\n行业模板参考：\n目标客户模板：{customer_template}\n功能模板：{feature_template}"
            
        return base_prompt

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        # 暂时返回模拟结果
        return json.dumps({
            "one_line_thesis": f"{prompt.split('机会主题：')[1].split('\\n')[0]} 存在显著的市场机会，适合快速切入",
            "target_customer": f"{prompt.split('行业分类：')[1].split('\\n')[0]}领域的中小企业负责人",
            "first_sellable_feature": "核心业务流程自动化解决方案",
            "suggested_play": "从细分场景切入，快速验证市场需求"
        })

    def _parse_llm_response(self, response: str) -> dict:
        """解析LLM响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"LLM响应解析失败: {response}")
            return {
                "one_line_thesis": "存在商业机会",
                "target_customer": "中小企业业务流程负责人",
                "first_sellable_feature": "基础自动化功能",
                "suggested_play": "持续监测市场动态"
            }

    def _template_advice(
        self, 
        topic: str, 
        industry: str, 
        insight_type: str,
        industry_template: Optional[Tuple[str, str]]
    ) -> CommercialAdvice:
        """模板化建议方案"""
        if industry_template:
            industry_customer, industry_feature = industry_template
            
            if insight_type == "early_signal_niche":
                return CommercialAdvice(
                    one_line_thesis=f"{topic} 出现早期需求信号，可先做小规模付费验证",
                    target_customer=industry_customer,
                    first_sellable_feature=f"{industry_feature}（先做轻量 MVP，验证是否愿意付费）",
                    suggested_play="用低成本实验验证付费意愿，再决定是否加码"
                )
            elif insight_type == "watchlist":
                return CommercialAdvice(
                    one_line_thesis=f"{topic} 当前信号仍偏弱，建议继续观察并补充关键词",
                    target_customer=industry_customer,
                    first_sellable_feature=f"{industry_feature}（监测版，先不做重交付）",
                    suggested_play="先持续监测 2-4 周，观察动量是否继续提升"
                )
            elif insight_type in {"crowded_hot_market", "fast_growing_white_space", "steady_pain_low_competition"}:
                return CommercialAdvice(
                    one_line_thesis=f"{topic} 在{industry}领域存在机会",
                    target_customer=industry_customer,
                    first_sellable_feature=industry_feature,
                    suggested_play=self._get_suggested_play(insight_type)
                )
        
        # 默认模板
        return CommercialAdvice(
            one_line_thesis=f"{topic} 存在商业机会",
            target_customer="中小企业业务流程负责人",
            first_sellable_feature="单流程自动化插件（可量化节省人时）",
            suggested_play=self._get_suggested_play(insight_type)
        )

    def _get_suggested_play(self, insight_type: str) -> str:
        """获取建议策略"""
        suggestions = {
            "fast_growing_white_space": "优先做垂直场景 MVP，先抢 1-2 个高频流程",
            "crowded_hot_market": "避免通用功能内卷，选择细分人群 + 差异化数据/交付",
            "early_signal_niche": "用低成本实验验证付费意愿，再决定是否加码",
            "steady_pain_low_competition": "从效率提升切入，主打 ROI 和替代人工",
            "watchlist": "先持续监测 2-4 周，观察动量是否继续提升"
        }
        return suggestions.get(insight_type, "持续监测市场动态")


class EnhancedConfidenceEvaluator:
    """增强置信度评估器"""
    
    def calculate_confidence(
        self,
        raw_signals: TopicRawSignals,
        scored_signals: TopicScored,
        llm_analysis: dict,
        data_quality_metrics: Optional[dict] = None
    ) -> ConfidenceScore:
        """计算增强置信度"""
        
        # 计算各维度置信度因子
        factors = {
            'data_coverage': self._calc_data_coverage(raw_signals),
            'signal_consistency': self._calc_signal_consistency(scored_signals),
            'llm_confidence': llm_analysis.get('confidence', 0),
            'data_quality': data_quality_metrics.get('overall_score', 0.8) if data_quality_metrics else 0.8,
            'market_stability': self._calc_market_stability(raw_signals),
            'industry_clarity': llm_analysis.get('industry_confidence', 0)
        }
        
        # 权重配置
        weights = {
            'data_coverage': 0.15,
            'signal_consistency': 0.20,
            'llm_confidence': 0.35,
            'data_quality': 0.15,
            'market_stability': 0.05,
            'industry_clarity': 0.10
        }
        
        # 计算整体置信度
        overall_confidence = sum(
            score * weights[factor] 
            for factor, score in factors.items()
        )
        
        # 确保置信度在0-1范围内
        overall_confidence = max(0.0, min(1.0, overall_confidence))
        
        return ConfidenceScore(
            overall=overall_confidence,
            factors=factors,
            reasoning=self._generate_confidence_reasoning(factors)
        )

    def _calc_data_coverage(self, raw: TopicRawSignals) -> float:
        """计算数据覆盖度"""
        coverage = 0
        totals = [raw.gdelt_total, raw.hn_total, raw.github_total, raw.reddit_total]
        
        for total in totals:
            if total > 0:
                coverage += 1
                
        base_coverage = coverage / 4.0
        
        # 考虑数据量质量
        total_mentions = sum(totals)
        if total_mentions >= 100:
            quality_bonus = 0.2
        elif total_mentions >= 50:
            quality_bonus = 0.1
        elif total_mentions >= 20:
            quality_bonus = 0.0
        else:
            quality_bonus = -0.1
            
        return max(0.0, min(1.0, base_coverage + quality_bonus))

    def _calc_signal_consistency(self, scored: TopicScored) -> float:
        """计算信号一致性"""
        # 计算各维度信号的平衡性
        signals = [scored.demand_norm, scored.momentum_norm, scored.competition_norm]
        mean_signal = sum(signals) / len(signals)
        
        # 计算方差（一致性指标）
        variance = sum((s - mean_signal) ** 2 for s in signals) / len(signals)
        consistency = 1.0 - variance  # 方差越小，一致性越高
        
        # 考虑机会得分的合理性
        opportunity_score = scored.opportunity_score
        if opportunity_score > 0.8 or opportunity_score < 0.2:
            # 极高或极低的分数需要更强的证据支持
            consistency *= 0.9
            
        return max(0.0, min(1.0, consistency))

    def _calc_market_stability(self, raw: TopicRawSignals) -> float:
        """计算市场稳定性"""
        # 基于近期vs总体数据的比例判断稳定性
        stability_scores = []
        
        if raw.gdelt_total > 0:
            gdelt_stability = raw.gdelt_recent / raw.gdelt_total if raw.gdelt_total > 0 else 0
            stability_scores.append(gdelt_stability)
            
        if raw.hn_total > 0:
            hn_stability = raw.hn_recent / raw.hn_total if raw.hn_total > 0 else 0
            stability_scores.append(hn_stability)
            
        if raw.github_total > 0:
            github_stability = raw.github_recent / raw.github_total if raw.github_total > 0 else 0
            stability_scores.append(github_stability)
            
        if raw.reddit_total > 0:
            reddit_stability = raw.reddit_recent / raw.reddit_total if raw.reddit_total > 0 else 0
            stability_scores.append(reddit_stability)
        
        if not stability_scores:
            return 0.5
            
        avg_stability = sum(stability_scores) / len(stability_scores)
        
        # 稳定性越高，置信度越高
        return max(0.0, min(1.0, avg_stability))

    def _generate_confidence_reasoning(self, factors: Dict[str, float]) -> str:
        """生成置信度解释"""
        reasoning_parts = []
        
        if factors['data_coverage'] >= 0.8:
            reasoning_parts.append("数据源覆盖全面")
        elif factors['data_coverage'] >= 0.6:
            reasoning_parts.append("数据源覆盖较好")
        else:
            reasoning_parts.append("数据源覆盖有限")
            
        if factors['signal_consistency'] >= 0.7:
            reasoning_parts.append("信号一致性强")
        elif factors['signal_consistency'] >= 0.5:
            reasoning_parts.append("信号一致性一般")
        else:
            reasoning_parts.append("信号存在分歧")
            
        if factors['llm_confidence'] >= 0.8:
            reasoning_parts.append("智能分析置信度高")
        elif factors['llm_confidence'] >= 0.6:
            reasoning_parts.append("智能分析置信度中等")
        else:
            reasoning_parts.append("智能分析置信度较低")
            
        return "; ".join(reasoning_parts) + "."


class MultiDimensionalEvidenceFusion:
    """多维度证据融合器"""
    
    def fuse_evidence(
        self,
        raw_signals: TopicRawSignals,
        scored_signals: TopicScored,
        llm_insights: dict,
        external_data: Optional[dict] = None
    ) -> ComprehensiveEvidence:
        """融合多维度证据"""
        
        # 量化数据证据分析
        quantitative_evidence = self._analyze_quantitative_signals(raw_signals, scored_signals)
        
        # LLM定性分析证据
        qualitative_evidence = self._analyze_qualitative_insights(llm_insights)
        
        # 外部数据证据（如果有）
        external_evidence = self._analyze_external_data(external_data) if external_data else {}
        
        # 综合证据合成
        comprehensive_analysis = self._synthesize_evidence(
            quantitative_evidence,
            qualitative_evidence,
            external_evidence
        )
        
        # 置信度指标计算
        confidence_indicators = self._calculate_confidence_indicators(
            quantitative_evidence,
            qualitative_evidence,
            external_evidence
        )
        
        return ComprehensiveEvidence(
            summary=comprehensive_analysis['summary'],
            detailed_analysis=comprehensive_analysis['detailed_analysis'],
            supporting_metrics=quantitative_evidence,
            qualitative_insights=qualitative_evidence,
            confidence_indicators=confidence_indicators
        )

    def _analyze_quantitative_signals(
        self, 
        raw: TopicRawSignals, 
        scored: TopicScored
    ) -> Dict[str, Any]:
        """分析量化信号"""
        
        demand_analysis = {
            'level': self._categorize_signal_level(scored.demand_norm),
            'trend_direction': self._analyze_demand_trend(raw),
            'platform_distribution': self._analyze_platform_distribution(raw, 'demand'),
            'stability_score': self._calculate_stability_score(raw, 'demand')
        }
        
        momentum_analysis = {
            'level': self._categorize_signal_level(scored.momentum_norm),
            'growth_rate': self._calculate_growth_rate(raw),
            'acceleration': self._calculate_acceleration(raw),
            'sustainability': self._assess_sustainability(raw)
        }
        
        competition_analysis = {
            'level': self._categorize_signal_level(1 - scored.competition_norm),  # 转换为竞争劣势
            'intensity': scored.competition_norm,
            'market_concentration': self._estimate_market_concentration(raw),
            'barrier_analysis': self._analyze_entry_barriers(raw)
        }
        
        return {
            'demand_metrics': demand_analysis,
            'momentum_metrics': momentum_analysis,
            'competition_metrics': competition_analysis,
            'cross_platform_consistency': self._analyze_cross_platform_consistency(raw),
            'temporal_patterns': self._analyze_temporal_patterns(raw)
        }

    def _analyze_qualitative_insights(self, llm_insights: dict) -> Dict[str, Any]:
        """分析LLM定性洞察"""
        
        return {
            'market_understanding': llm_insights.get('market_analysis', ''),
            'industry_context': llm_insights.get('industry_insights', ''),
            'trend_identification': llm_insights.get('trend_analysis', ''),
            'opportunity_assessment': llm_insights.get('opportunity_score', ''),
            'risk_factors': llm_insights.get('risk_factors', []),
            'competitive_landscape': llm_insights.get('competitive_analysis', ''),
            'user_behavior_insights': llm_insights.get('user_insights', ''),
            'technology_trends': llm_insights.get('tech_trends', '')
        }

    def _synthesize_evidence(
        self,
        quantitative_evidence: dict,
        qualitative_evidence: dict,
        external_evidence: dict
    ) -> Dict[str, str]:
        """综合证据合成"""
        
        # 生成摘要
        summary = self._generate_evidence_summary(
            quantitative_evidence,
            qualitative_evidence,
            external_evidence
        )
        
        # 生成详细分析
        detailed_analysis = self._generate_detailed_analysis(
            quantitative_evidence,
            qualitative_evidence,
            external_evidence
        )
        
        return {
            'summary': summary,
            'detailed_analysis': detailed_analysis
        }

    def _generate_evidence_summary(
        self,
        quantitative: dict,
        qualitative: dict,
        external: dict
    ) -> str:
        """生成证据摘要"""
        
        # 基于量化数据生成基础摘要
        demand_level = quantitative['demand_metrics']['level']
        momentum_level = quantitative['momentum_metrics']['level']
        competition_level = quantitative['competition_metrics']['level']
        
        summary_parts = []
        
        # 需求分析
        if demand_level == 'high':
            summary_parts.append("市场需求强劲")
        elif demand_level == 'medium':
            summary_parts.append("市场需求稳定")
        else:
            summary_parts.append("市场需求有限")
            
        # 动量分析
        if momentum_level == 'high':
            summary_parts.append("增长动量充足")
        elif momentum_level == 'medium':
            summary_parts.append("增长动量一般")
        else:
            summary_parts.append("增长动量不足")
            
        # 竞争分析
        if competition_level == 'high':
            summary_parts.append("竞争压力较小")
        elif competition_level == 'medium':
            summary_parts.append("竞争压力适中")
        else:
            summary_parts.append("竞争激烈")
        
        return "; ".join(summary_parts) + "."

    def _generate_detailed_analysis(self, quantitative: dict, qualitative: dict, external: dict) -> str:
        """生成详细分析"""
        
        analysis_parts = []
        
        # 量化分析部分
        demand_score = quantitative['demand_metrics']['stability_score']
        momentum_acceleration = quantitative['momentum_metrics']['acceleration']
        competition_intensity = quantitative['competition_metrics']['intensity']
        
        analysis_parts.append(f"需求稳定性得分: {demand_score:.2f}")
        analysis_parts.append(f"动量加速度: {momentum_acceleration:.2f}")
        analysis_parts.append(f"竞争强度: {competition_intensity:.2f}")
        
        # 一致性分析
        consistency = quantitative['cross_platform_consistency']
        analysis_parts.append(f"跨平台一致性: {consistency:.2f}")
        
        return "; ".join(analysis_parts)

    def _categorize_signal_level(self, score: float) -> str:
        """分类信号等级"""
        if score >= 0.7:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        else:
            return 'low'

    def _analyze_demand_trend(self, raw: TopicRawSignals) -> str:
        """分析需求趋势"""
        # 简化的趋势分析
        recent_ratio = (raw.gdelt_recent + raw.hn_recent + raw.github_recent + raw.reddit_recent) / max(
            raw.gdelt_total + raw.hn_total + raw.github_total + raw.reddit_total, 1
        )
        
        if recent_ratio >= 0.6:
            return 'rising'
        elif recent_ratio >= 0.4:
            return 'stable'
        else:
            return 'declining'

    def _analyze_platform_distribution(self, raw: TopicRawSignals, signal_type: str) -> dict:
        """分析平台分布"""
        platforms = {
            'gdelt': raw.gdelt_total,
            'hackernews': raw.hn_total,
            'github': raw.github_total,
            'reddit': raw.reddit_total
        }
        
        total = sum(platforms.values())
        if total == 0:
            return {platform: 0.25 for platform in platforms.keys()}
            
        return {platform: count / total for platform, count in platforms.items()}

    def _calculate_stability_score(self, raw: TopicRawSignals, signal_type: str) -> float:
        """计算稳定性得分"""
        # 基于近期vs总体比例计算稳定性
        if signal_type == 'demand':
            recent = raw.gdelt_recent + raw.hn_recent
            total = raw.gdelt_total + raw.hn_total
        else:
            recent = raw.github_recent + raw.reddit_recent
            total = raw.github_total + raw.reddit_total
            
        if total == 0:
            return 0.5
            
        stability = recent / total
        return max(0.0, min(1.0, stability))

    def _calculate_growth_rate(self, raw: TopicRawSignals) -> float:
        """计算增长率"""
        # 简化的增长率计算
        recent_activity = raw.gdelt_recent + raw.hn_recent + raw.github_recent + raw.reddit_recent
        old_activity = max(
            raw.gdelt_total - raw.gdelt_recent + 
            raw.hn_total - raw.hn_recent + 
            raw.github_total - raw.github_recent + 
            raw.reddit_total - raw.reddit_recent, 
            1
        )
        
        if old_activity == 0:
            return 1.0
            
        growth_rate = (recent_activity - old_activity) / old_activity
        return max(-1.0, min(1.0, growth_rate))

    def _calculate_acceleration(self, raw: TopicRawSignals) -> float:
        """计算加速度"""
        # 基于增长率的变化计算加速度
        growth_rate = self._calculate_growth_rate(raw)
        
        # 简化的加速度计算（假设之前的增长率为0）
        acceleration = growth_rate  # 相对于无增长的加速度
        
        return max(-1.0, min(1.0, acceleration))

    def _assess_sustainability(self, raw: TopicRawSignals) -> float:
        """评估可持续性"""
        # 基于多平台一致性评估可持续性
        platform_consistency = self._analyze_cross_platform_consistency(raw)
        
        # 基于总体活跃度评估
        total_activity = raw.gdelt_total + raw.hn_total + raw.github_total + raw.reddit_total
        if total_activity >= 100:
            activity_score = 1.0
        elif total_activity >= 50:
            activity_score = 0.8
        elif total_activity >= 20:
            activity_score = 0.6
        else:
            activity_score = 0.4
            
        sustainability = (platform_consistency + activity_score) / 2
        return max(0.0, min(1.0, sustainability))

    def _estimate_market_concentration(self, raw: TopicRawSignals) -> float:
        """估算市场集中度"""
        # 基于平台分布估算市场集中度
        distribution = self._analyze_platform_distribution(raw, 'competition')
        
        # 计算赫芬达尔指数（简化版）
        hhi = sum(share ** 2 for share in distribution.values())
        
        # 转换为集中度得分（越高表示越集中）
        concentration = min(1.0, hhi * 2)
        
        return concentration

    def _analyze_entry_barriers(self, raw: TopicRawSignals) -> dict:
        """分析进入壁垒"""
        # 简化的进入壁垒分析
        total_activity = raw.gdelt_total + raw.hn_total + raw.github_total + raw.reddit_total
        
        if total_activity >= 200:
            barrier_level = 'high'
        elif total_activity >= 100:
            barrier_level = 'medium'
        else:
            barrier_level = 'low'
            
        return {
            'level': barrier_level,
            'factors': ['market_activity', 'competition_intensity'],
            'score': 1.0 if barrier_level == 'high' else (0.5 if barrier_level == 'medium' else 0.2)
        }

    def _analyze_cross_platform_consistency(self, raw: TopicRawSignals) -> float:
        """分析跨平台一致性"""
        platforms = {
            'gdelt': raw.gdelt_total,
            'hackernews': raw.hn_total,
            'github': raw.github_total,
            'reddit': raw.reddit_total
        }
        
        # 移除零值平台
        non_zero_platforms = {k: v for k, v in platforms.items() if v > 0}
        
        if len(non_zero_platforms) <= 1:
            return 0.3  # 只有一个平台有数据，一致性较低
            
        # 计算变异系数
        values = list(non_zero_platforms.values())
        mean_value = sum(values) / len(values)
        
        if mean_value == 0:
            return 0.0
            
        variance = sum((v - mean_value) ** 2 for v in values) / len(values)
        std_deviation = variance ** 0.5
        coefficient_of_variation = std_deviation / mean_value
        
        # 转换为一致性得分（越高表示越一致）
        consistency = max(0.0, min(1.0, 1.0 - coefficient_of_variation))
        
        return consistency

    def _analyze_temporal_patterns(self, raw: TopicRawSignals) -> dict:
        """分析时间模式"""
        # 基于近期vs总体数据分析时间模式
        patterns = {}
        
        # 分析各平台的近期活跃度比例
        platforms = [
            ('gdelt', raw.gdelt_total, raw.gdelt_recent),
            ('hackernews', raw.hn_total, raw.hn_recent),
            ('github', raw.github_total, raw.github_recent),
            ('reddit', raw.reddit_total, raw.reddit_recent)
        ]
        
        for platform, total, recent in platforms:
            if total > 0:
                recency_ratio = recent / total
                if recency_ratio >= 0.7:
                    patterns[platform] = 'very_recent'
                elif recency_ratio >= 0.5:
                    patterns[platform] = 'recent'
                elif recency_ratio >= 0.3:
                    patterns[platform] = 'moderate'
                else:
                    patterns[platform] = 'old'
            else:
                patterns[platform] = 'no_data'
                
        return patterns

    def _calculate_confidence_indicators(
        self,
        quantitative: dict,
        qualitative: dict,
        external: dict
    ) -> Dict[str, float]:
        """计算置信度指标"""
        
        indicators = {}
        
        # 数据质量指标
        indicators['data_quality'] = (
            quantitative['demand_metrics']['stability_score'] * 0.4 +
            quantitative['cross_platform_consistency'] * 0.3 +
            (1.0 - quantitative['competition_metrics']['intensity']) * 0.3
        )
        
        # 信号强度指标
        demand_level = quantitative['demand_metrics']['level']
        momentum_level = quantitative['momentum_metrics']['level']
        
        level_scores = {'high': 1.0, 'medium': 0.6, 'low': 0.3}
        indicators['signal_strength'] = (
            level_scores.get(demand_level, 0.0) * 0.5 +
            level_scores.get(momentum_level, 0.0) * 0.5
        )
        
        # 一致性指标
        indicators['consistency'] = quantitative['cross_platform_consistency']
        # 可持续性指标
        indicators['sustainability'] = quantitative['momentum_metrics']['sustainability']
        
        return indicators

    def _analyze_external_data(self, external_data: dict) -> dict:
        """分析外部数据"""
        # 简化的外部数据分析
        return {
            'market_reports': external_data.get('market_reports', []),
            'regulatory_changes': external_data.get('regulatory_changes', []),
            'technology_advancements': external_data.get('technology_advancements', []),
            'economic_indicators': external_data.get('economic_indicators', {})
        }
        

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import TopicRawSignals, TopicScored


@dataclass
class TopicInsight:
    topic: str
    industry_guess: str
    opportunity_score: float
    opportunity_band: str
    insight_type: str
    confidence: float
    one_line_thesis: str
    target_customer: str
    first_sellable_feature: str
    evidence: str
    suggested_play: str

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "industry_guess": self.industry_guess,
            "opportunity_score": round(self.opportunity_score, 6),
            "opportunity_band": self.opportunity_band,
            "insight_type": self.insight_type,
            "confidence": round(self.confidence, 3),
            "one_line_thesis": self.one_line_thesis,
            "target_customer": self.target_customer,
            "first_sellable_feature": self.first_sellable_feature,
            "evidence": self.evidence,
            "suggested_play": self.suggested_play,
        }


def _band(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _confidence(raw: TopicRawSignals) -> float:
    coverage = 0
    for total in [raw.gdelt_total, raw.hn_total, raw.github_total, raw.reddit_total]:
        if total > 0:
            coverage += 1
    return coverage / 4.0


def _classify(scored: TopicScored) -> tuple[str, str]:
    d = scored.demand_norm
    m = scored.momentum_norm
    c = scored.competition_norm

    if d >= 0.6 and m >= 0.6 and c <= 0.4:
        return "fast_growing_white_space", "优先做垂直场景 MVP，先抢 1-2 个高频流程"
    if d >= 0.6 and c >= 0.7:
        return "crowded_hot_market", "避免通用功能内卷，选择细分人群 + 差异化数据/交付"
    if d <= 0.4 and m >= 0.6 and c <= 0.4:
        return "early_signal_niche", "用低成本实验验证付费意愿，再决定是否加码"
    if d >= 0.4 and m <= 0.3 and c <= 0.4:
        return "steady_pain_low_competition", "从效率提升切入，主打 ROI 和替代人工"
    return "watchlist", "先持续监测 2-4 周，观察动量是否继续提升"


def _commercial_pack(insight_type: str, topic: str) -> tuple[str, str, str]:
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


def _guess_industry(topic: str) -> str:
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


def _industry_template(industry: str) -> tuple[str, str]:
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
    return templates[industry]


def _commercial_pack_by_industry(
    insight_type: str, topic: str, industry: str
) -> tuple[str, str, str]:
    one_line_thesis, target_customer, first_sellable_feature = _commercial_pack(
        insight_type, topic
    )
    industry_customer, industry_feature = _industry_template(industry)

    if insight_type == "early_signal_niche":
        return (
            one_line_thesis,
            industry_customer,
            f"{industry_feature}（先做轻量 MVP，验证是否愿意付费）",
        )
    if insight_type == "watchlist":
        return (
            one_line_thesis,
            industry_customer,
            f"{industry_feature}（监测版，先不做重交付）",
        )
    if insight_type in {"crowded_hot_market", "fast_growing_white_space", "steady_pain_low_competition"}:
        return one_line_thesis, industry_customer, industry_feature
    return one_line_thesis, target_customer, first_sellable_feature


def _evidence(scored: TopicScored, raw: TopicRawSignals) -> str:
    return (
        f"demand={scored.demand_norm:.2f}, momentum={scored.momentum_norm:.2f}, "
        f"competition={scored.competition_norm:.2f}; "
        f"sources(gdelt/hn/github/reddit)={raw.gdelt_total}/{raw.hn_total}/{raw.github_total}/{raw.reddit_total}"
    )


def build_topic_insights(
    raw_signals: list[TopicRawSignals], scored_topics: list[TopicScored]
) -> list[TopicInsight]:
    raw_map = {row.topic: row for row in raw_signals}
    insights: list[TopicInsight] = []

    for scored in scored_topics:
        raw = raw_map[scored.topic]
        insight_type, suggested_play = _classify(scored)
        industry = _guess_industry(scored.topic)
        one_line_thesis, target_customer, first_sellable_feature = _commercial_pack_by_industry(
            insight_type, scored.topic, industry
        )
        insights.append(
            TopicInsight(
                topic=scored.topic,
                industry_guess=industry,
                opportunity_score=scored.opportunity_score,
                opportunity_band=_band(scored.opportunity_score),
                insight_type=insight_type,
                confidence=_confidence(raw),
                one_line_thesis=one_line_thesis,
                target_customer=target_customer,
                first_sellable_feature=first_sellable_feature,
                evidence=_evidence(scored, raw),
                suggested_play=suggested_play,
            )
        )

    return insights


def render_insights_markdown(insights: list[TopicInsight]) -> str:
    if not insights:
        return "# 行业洞察\n\n暂无数据。"

    high_count = sum(1 for item in insights if item.opportunity_band == "high")
    medium_count = sum(1 for item in insights if item.opportunity_band == "medium")
    low_count = sum(1 for item in insights if item.opportunity_band == "low")

    type_counts: dict[str, int] = {}
    for item in insights:
        type_counts[item.insight_type] = type_counts.get(item.insight_type, 0) + 1

    lines: list[str] = []
    lines.append("# 行业洞察与机会建议")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 高机会: {high_count} 个")
    lines.append(f"- 中机会: {medium_count} 个")
    lines.append(f"- 低机会: {low_count} 个")
    lines.append("- 主要机会类型分布:")
    for key, count in sorted(type_counts.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"  - {key}: {count}")

    lines.append("")
    lines.append("## 重点机会（Top 5）")
    lines.append("")
    for index, item in enumerate(insights[:5], start=1):
        lines.append(f"### {index}. {item.topic}")
        lines.append(f"- 行业判定: {item.industry_guess}")
        lines.append(f"- 机会分层: {item.opportunity_band} (score={item.opportunity_score:.3f})")
        lines.append(f"- 机会类型: {item.insight_type}")
        lines.append(f"- 一句话结论: {item.one_line_thesis}")
        lines.append(f"- 建议客群: {item.target_customer}")
        lines.append(f"- 首个可卖功能: {item.first_sellable_feature}")
        lines.append(f"- 证据: {item.evidence}")
        lines.append(f"- 建议动作: {item.suggested_play}")
        lines.append(f"- 置信度: {item.confidence:.2f}")
        lines.append("")

    lines.append("## 解释说明")
    lines.append("")
    lines.append("- 本报告用于机会优先级排序，不等同于收入预测。")
    lines.append("- 若某主题多数数据源为 0，建议扩展关键词并连续观测。")

    return "\n".join(lines)


def pick_daily_insight(
    insights: list[TopicInsight],
    *,
    min_confidence: float = 0.5,
    avoid_types: set[str] | None = None,
) -> TopicInsight | None:
    if not insights:
        return None

    avoid_types = avoid_types or {"crowded_hot_market"}

    for band in ["high", "medium", "low"]:
        band_items = [item for item in insights if item.opportunity_band == band]
        if not band_items:
            continue

        for item in band_items:
            if item.confidence >= min_confidence and item.insight_type not in avoid_types:
                return item

        for item in band_items:
            if item.confidence >= min_confidence:
                return item

        for item in band_items:
            if item.insight_type not in avoid_types:
                return item

        return band_items[0]

    return insights[0] if insights else None


def render_daily_brief_markdown(
    insights: list[TopicInsight],
    *,
    window_days: int,
    recent_days: int,
    as_of: datetime | None = None,
) -> str:
    if not insights:
        return "# 每日机会洞察\n\n暂无数据。"

    as_of = as_of or datetime.now()
    chosen = pick_daily_insight(insights)
    if chosen is None:
        return "# 每日机会洞察\n\n暂无数据。"

    lines: list[str] = []
    lines.append(f"# 每日机会洞察（{as_of.strftime('%Y-%m-%d')}）")
    lines.append("")
    lines.append(f"## 今日机会：{chosen.topic}")
    lines.append("")
    lines.append(f"- 机会分层: {chosen.opportunity_band} (score={chosen.opportunity_score:.3f})")
    lines.append(f"- 机会类型: {chosen.insight_type}")
    lines.append(f"- 行业判定: {chosen.industry_guess}")
    if chosen.confidence < 0.5:
        lines.append("- 注意: 当前信号覆盖偏低，建议先把关键词/子方向拆细再做验证。")
    lines.append(f"- 一句话结论: {chosen.one_line_thesis}")
    lines.append(f"- 建议客群: {chosen.target_customer}")
    lines.append(f"- 首个可卖功能: {chosen.first_sellable_feature}")
    lines.append(f"- 证据: {chosen.evidence}")
    lines.append(f"- 建议动作: {chosen.suggested_play}")
    lines.append(f"- 置信度: {chosen.confidence:.2f}")
    lines.append("")

    lines.append("## 备选观察（Top 3）")
    lines.append("")
    alternatives = [item for item in insights if item.topic != chosen.topic][:3]
    if not alternatives:
        lines.append("- 无")
    else:
        for item in alternatives:
            lines.append(
                f"- {item.topic} | {item.opportunity_band} (score={item.opportunity_score:.3f}) | "
                f"type={item.insight_type} | conf={item.confidence:.2f}"
            )
    lines.append("")
    lines.append("## 数据窗口")
    lines.append("")
    lines.append(f"- window_days: {window_days}")
    lines.append(f"- recent_days: {recent_days}")
    lines.append("")
    lines.append("## 提醒")
    lines.append("")
    lines.append("- 若置信度偏低（<0.50），通常代表只有 1 个数据源提供了有效信号；建议扩展关键词或增加 topic 颗粒度。")

    return "\n".join(lines)

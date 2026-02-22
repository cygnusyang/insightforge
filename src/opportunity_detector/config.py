from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class Weights(BaseModel):
    demand: float = 0.45
    momentum: float = 0.35
    competition: float = 0.20

    @field_validator("competition")
    @classmethod
    def validate_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError(f"权重验证失败: competition 权重不能小于 0，当前值为 {value}")
        return value

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "Weights":
        total = self.demand + self.momentum + self.competition
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"权重验证失败: demand ({self.demand}) + momentum ({self.momentum}) + "
                f"competition ({self.competition}) = {total:.3f}，"
                f"权重之和必须为 1.0"
            )
        return self


@dataclass
class PaperSummaryStats:
    """论文总结统计信息"""
    pdf_downloaded: int = 0
    pdf_download_failed: int = 0
    pdf_cache_hit: int = 0
    llm_summarized: int = 0
    llm_fallback_used: int = 0
    total_time_seconds: float = 0.0
    avg_download_time_seconds: float = 0.0
    avg_summarize_time_seconds: float = 0.0


class PaperConfig(BaseModel):
    """论文相关配置"""
    enable_pdf_download: bool = True
    max_pdfs: int = Field(default=2, ge=0, le=10)
    max_pages: int = Field(default=4, ge=1, le=20)
    download_timeout: int = Field(default=60, ge=10, le=300)
    summary_max_tokens: int = Field(default=2000, ge=100, le=10000)
    enable_cache: bool = True
    cache_ttl_days: int = Field(default=7, ge=1, le=365)
    cache_dir: str = "outputs/papers_cache"


class DetectorConfig(BaseModel):
    window_days: int = Field(default=30, ge=7, le=365)
    recent_days: int = Field(default=7, ge=1)  # le=30 removed to allow custom validation
    daily_days: int = Field(default=1, ge=1, le=7)
    daily_max_items_per_topic: int = Field(default=10, ge=1, le=10)
    daily_max_gdelt_items: int = Field(default=12, ge=1, le=50)
    daily_enable_biz_event_queries: bool = True
    daily_gdelt_biz_query_max_records: int = Field(default=6, ge=0, le=50)
    daily_max_papers_per_topic: int = Field(default=2, ge=0, le=5)
    daily_enable_paper_summaries: bool = True
    daily_enable_pdf_summaries: bool = False
    daily_max_paper_pdfs: int = Field(default=2, ge=0, le=10)
    daily_pdf_max_pages: int = Field(default=4, ge=1, le=20)
    papers_cache_dir: str = "outputs/papers_cache"
    weights: Weights = Weights()
    topics: List[str] = Field(default_factory=list)
    topic_keywords: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Paper config (new in FUNC-005A/B)
    paper_config: PaperConfig = PaperConfig()

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError(
                "配置验证失败: topics 不能为空列表，请至少配置一个主题"
            )
        return cleaned

    @field_validator("topic_keywords")
    @classmethod
    def validate_topic_keywords(cls, value: Dict[str, List[str]]) -> Dict[str, List[str]]:
        cleaned: Dict[str, List[str]] = {}
        for key, items in (value or {}).items():
            topic = (key or "").strip()
            if not topic:
                continue
            keywords = []
            for item in items or []:
                item_clean = str(item or "").strip()
                if not item_clean:
                    continue
                keywords.append(item_clean)
            if keywords:
                cleaned[topic] = keywords
        return cleaned

    @field_validator("recent_days")
    @classmethod
    def validate_recent_window(cls, value: int, info):
        window_days = info.data.get("window_days", 30)
        if value >= window_days:
            raise ValueError(
                f"时间窗口验证失败: recent_days ({value}) 必须小于 window_days ({window_days})，"
                f"请确保 recent_days < window_days"
            )
        return value

    @model_validator(mode="after")
    def validate_config_consistency(self) -> "DetectorConfig":
        # 验证 daily_days <= recent_days
        if self.daily_days > self.recent_days:
            raise ValueError(
                f"时间窗口验证失败: daily_days ({self.daily_days}) 不能大于 recent_days ({self.recent_days})，"
                f"请确保 daily_days <= recent_days"
            )
        
        # 验证 topics 和 topic_keywords 一致性
        missing_keywords: List[str] = []
        for topic in self.topics:
            if topic not in self.topic_keywords:
                missing_keywords.append(topic)
        
        if missing_keywords:
            raise ValueError(
                f"配置验证失败: 以下 topics 缺少对应的 topic_keywords: {missing_keywords}。"
                f"请在配置中为每个 topic 添加对应的关键词列表"
            )
        
        # 兼容性处理：如果配置中使用了旧字段，同步到 paper_config
        # 这样可以确保新旧配置都能正常工作
        if hasattr(self, 'daily_enable_pdf_summaries') and self.daily_enable_pdf_summaries:
            self.paper_config.enable_pdf_download = True
        if hasattr(self, 'daily_max_paper_pdfs') and self.daily_max_paper_pdfs > 0:
            self.paper_config.max_pdfs = self.daily_max_paper_pdfs
        if hasattr(self, 'daily_pdf_max_pages') and self.daily_pdf_max_pages > 0:
            self.paper_config.max_pages = self.daily_pdf_max_pages
        if hasattr(self, 'papers_cache_dir') and self.papers_cache_dir:
            self.paper_config.cache_dir = self.papers_cache_dir
        
        return self


def load_config(path: str | Path) -> DetectorConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return DetectorConfig.model_validate(payload)

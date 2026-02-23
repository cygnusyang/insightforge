"""
论文采集器 - 每日10篇论文采集功能
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import DetectorConfig
from .connectors.arxiv import fetch_arxiv_papers
from .models import EventItem

# 论文采集限制
MAX_PAPERS_PER_DAY = 10
MAX_PAPERS_PER_TOPIC = 3
RELEVANCE_THRESHOLD = 60  # 相关性阈值（百分比）


def _calculate_relevance(title: str, topic: str, keywords: list[str]) -> int:
    """计算论文与主题的相关性分数（0-100）"""
    if not title or not topic:
        return 0
    
    # 简单的相关性计算：关键词匹配
    title_lower = title.lower()
    topic_lower = topic.lower()
    
    relevance = 0
    
    # 主题匹配（权重60%）
    if topic_lower in title_lower:
        relevance += 60
    
    # 关键词匹配（权重40%）
    for keyword in keywords:
        if keyword.lower() in title_lower:
            relevance += 20
    
    return min(relevance, 100)


def _deduplicate_papers(papers: list[EventItem], max_papers: int = MAX_PAPERS_PER_DAY) -> list[EventItem]:
    """去重论文（基于标题相似度）"""
    if len(papers) <= max_papers:
        return papers
    
    # 按相关性排序
    sorted_papers = sorted(papers, key=lambda p: (p.meta or {}).get("relevance", 0), reverse=True)
    
    # 基于标题相似度去重
    unique_papers = []
    seen_titles = []
    
    for paper in sorted_papers:
        title = paper.title.lower().strip()
        
        # 检查是否与已存在标题相似
        is_duplicate = False
        for seen_title in seen_titles:
            # 简单的字符串相似度检查
            if len(title) != len(seen_title):
                similarity = len(set(title) & set(seen_title)) / max(len(title), len(seen_title))
            else:
                similarity = 1.0 if title == seen_title else 0.0
            
            if similarity > 0.85:  # 相似度阈值
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_papers.append(paper)
            seen_titles.append(title)
        
        if len(unique_papers) >= max_papers:
            break
    
    return unique_papers


async def collect_daily_papers(
    client: httpx.AsyncClient,
    config: DetectorConfig,
    since: datetime,
) -> list[EventItem]:
    """
    每日论文采集主函数
    
    Args:
        client: HTTP客户端
        config: 配置对象
        since: 采集起始时间
        
    Returns:
        list[EventItem]: 采集的论文列表（最多10篇）
    """
    all_papers: list[EventItem] = []
    
    # 收集所有主题的论文
    for topic in config.topics:
        # 获取主题关键词
        topic_keywords = []
        if hasattr(config, 'topic_keywords') and topic in config.topic_keywords:
            topic_keywords = config.topic_keywords[topic]
        
        # 从arXiv采集论文
        papers = await fetch_arxiv_papers(
            client=client,
            topic=topic,
            search_query=f"all:{topic}",
            since=since,
            max_items=MAX_PAPERS_PER_TOPIC,  # 每个主题最多采集3篇
        )
        
        # 计算相关性并创建新对象
        for paper in papers:
            relevance = _calculate_relevance(
                paper.title,
                topic,
                topic_keywords
            )
            # 创建新的EventItem副本以添加meta信息
            new_meta = (paper.meta or {}).copy()
            new_meta["relevance"] = relevance
            new_paper = EventItem(
                source=paper.source,
                topic=paper.topic,
                title=paper.title,
                url=paper.url,
                published_at=paper.published_at,
                meta=new_meta,
            )
            all_papers.append(new_paper)
        
        # 过滤低相关性论文
        relevant_papers = [p for p in all_papers if (p.meta or {}).get("relevance", 0) >= RELEVANCE_THRESHOLD]
    
    # 去重并限制总数
    unique_papers = _deduplicate_papers(all_papers, MAX_PAPERS_PER_DAY)
    
    # 按相关性排序
    unique_papers.sort(key=lambda p: (p.meta or {}).get("relevance", 0), reverse=True)
    
    return unique_papers[:MAX_PAPERS_PER_DAY]


async def collect_papers_batch(
    config: DetectorConfig,
    since: datetime | None = None,
) -> list[EventItem]:
    """
    批量采集论文（带HTTP客户端管理）
    
    Args:
        config: 配置对象
        since: 采集起始时间，默认为24小时前
        
    Returns:
        list[EventItem]: 采集的论文列表
    """
    if since is None:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        papers = await collect_daily_papers(client, config, since)
    
    return papers

# 行业/产品机会探测器（多信号融合）

这是一个可运行的 Python MVP 工程，用**尽量免费的数据源**做“机会探测”：
- 新闻热度：GDELT Doc API（免费）
- 开发者讨论：Hacker News Algolia API（免费）
- 开源生态：GitHub Search API（免费额度，建议配 token）
- 用户讨论：Reddit 公共 JSON（免费，可能有区域/频率限制）
- 研究论文：arXiv API（免费）

## 核心思路
对每个 topic 采集多信号：
1. **Demand（需求）**：最近讨论/新闻量
2. **Momentum（动量）**：近 7 天 vs 历史窗口的变化
3. **Competition（竞争）**：GitHub 项目数量近似竞争强度

最终机会分数：

`opportunity = w_demand * demand_norm + w_momentum * momentum_norm + w_competition * (1 - competition_norm)`

## 快速开始

```bash
cd /Users/cygnus/work/github/hunter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/topics.example.yml config/topics.yml
python run.py --config config/topics.yml --out outputs/latest
```

运行后会输出：
- `outputs/latest/signals.csv`：原始与派生信号
- `outputs/latest/opportunities.csv`：机会排序结果
- `outputs/latest/report.md`：可读报告
- `outputs/latest/insights.csv`：结构化行业洞察（机会类型、证据、建议动作、置信度）
- `outputs/latest/insights.md`：可直接阅读的行业洞察与机会建议
- `outputs/latest/events.csv`：抓取到的“事件/素材”（标题、链接、时间、来源）
- `outputs/latest/paper_summaries.csv`：论文摘要/（可选）PDF 总结
- `outputs/latest/paper_summaries.md`：论文总结可读版
- `outputs/latest/daily.md`：每日风格的“今日机会 + 备选观察”
- `outputs/latest/daily/YYYY-MM-DD.md`：按日期归档的每日简报
- `outputs/latest/daily_report.md`：每日“事件 → 洞察 → 机会”的文字性报告
- `outputs/latest/daily/YYYY-MM-DD.report.md`：按日期归档的每日文字性报告

## 可调参数
在 `config/topics.yml` 调整：
- `window_days`：历史窗口
- `recent_days`：最近窗口
- `daily_days`：日报覆盖天数（默认 1）
- `daily_max_items_per_topic`：每个 topic 最多事件条数（默认 10）
- `daily_max_papers_per_topic`：每个 topic 最多论文条数（默认 2）
- `weights`：三类信号权重（和建议为 1）
- `topics`：你要观察的行业/产品方向
- `topic_keywords`：为每个 topic 补充同义词/关键词（提升“事件归因/去噪”效果）

## 免费 API 说明
- **GDELT**：无需 key，免费
- **HN Algolia**：无需 key，免费
- **GitHub Search**：有免费速率限制；建议配置 `GITHUB_TOKEN`
- **Reddit JSON**：无需 key，但可能被限流，代码已做失败降级

## 下一步建议
- 增加关键词扩展（同义词、行业词典）
- 增加时间序列存储（SQLite / DuckDB）
- 增加告警（分数突增时发通知）

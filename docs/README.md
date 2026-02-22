# 文档目录

本文档目录包含了行业/产品机会探测器项目的所有相关文档。

## 文档结构

```
docs/
├── README.md              # 本文档 - 文档目录说明
├── requirements/          # 需求文档
│   ├── functional.md      # 功能需求文档
│   ├── non-functional.md  # 非功能需求文档
│   └── user-stories.md    # 用户故事
├── architecture/          # 架构文档
│   ├── technical.md       # 技术架构文档
│   └── data-flow.md       # 数据流图
├── data-sources/          # 数据源文档
│   ├── overview.md        # 数据源概览
│   ├── gdelt.md          # GDELT 数据源说明
│   ├── github.md         # GitHub API 说明
│   ├── reddit.md         # Reddit 数据源说明
│   ├── hackernews.md     # Hacker News 数据源说明
│   └── arxiv.md          # arXiv 数据源说明
├── configuration/         # 配置文档
│   ├── config-guide.md   # 配置指南
│   └── topics-config.md  # 主题配置说明
├── iteration/            # 迭代计划
│   ├── roadmap.md        # 产品路线图
│   ├── current-sprint.md # 当前迭代计划
│   └── backlog.md        # 待办事项列表
└── api/                  # API 文档（如适用）
    └── api-reference.md  # API 参考文档
```

## 快速开始

1. 从 [`requirements/functional.md`](requirements/functional.md) 开始了解功能需求
2. 查看 [`architecture/technical.md`](architecture/technical.md) 了解技术架构
3. 参考 [`configuration/config-guide.md`](configuration/config-guide.md) 进行配置
4. 查看 [`iteration/roadmap.md`](iteration/roadmap.md) 了解开发计划

## 文档维护

- 所有文档使用 Markdown 格式编写
- 文档应保持最新，与代码同步更新
- 新增功能时应同步更新相关文档
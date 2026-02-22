# 配置指南

## 概述

行业机会探测器采用 YAML 格式的配置文件，支持灵活的系统参数配置。通过配置文件，用户可以自定义数据源、信号权重、时间窗口、输出格式等各种参数，无需修改代码即可适应不同的使用场景。

## 配置文件结构

### 主配置文件 (`config/topics.yml`)

```yaml
# 系统配置
system:
  name: "行业机会探测器"
  version: "1.0.0"
  debug: false
  log_level: "INFO"
  
# 时间配置
time:
  window_days: 30          # 历史窗口天数
  recent_days: 7           # 近期窗口天数
  timezone: "UTC"          # 时区设置
  
# 信号权重配置
signals:
  demand:       0.4        # 需求信号权重
  momentum:     0.3        # 动量信号权重
  competition:  0.3        # 竞争信号权重
  
# 数据源配置
data_sources:
  gdelt:
    enabled: true
    weight: 0.3
    timeout: 30
    max_retries: 3
    cache_hours: 24
    
  github:
    enabled: true
    weight: 0.25
    token: "${GITHUB_TOKEN}"  # 环境变量引用
    timeout: 60
    max_retries: 2
    cache_hours: 12
    
  hackernews:
    enabled: true
    weight: 0.25
    timeout: 30
    max_retries: 2
    cache_hours: 6
    
  reddit:
    enabled: true
    weight: 0.15
    timeout: 45
    max_retries: 2
    cache_hours: 8
    
  arxiv:
    enabled: true
    weight: 0.05
    timeout: 30
    max_retries: 2
    cache_hours: 24

# 输出配置
output:
  directory: "./outputs"
  formats: ["csv", "markdown", "json"]
  generate_daily: true
  generate_insights: true
  compress: false
  
# 报告配置
report:
  max_items_per_topic: 10
  max_papers_per_topic: 2
  include_charts: false
  language: "zh-CN"
  template: "default"

# 监控配置
monitoring:
  enabled: true
  metrics_port: 8080
  health_check_interval: 60
  alert_thresholds:
    error_rate: 0.05
    response_time: 30
    data_quality: 0.8

# 主题列表
topics:
  - name: "人工智能"
    keywords: 
      - "人工智能"
      - "AI"
      - "机器学习"
      - "深度学习"
      - "神经网络"
    enabled: true
    weight: 1.0
    priority: "high"
    
  - name: "区块链"
    keywords:
      - "区块链"
      - "比特币"
      - "加密货币"
      - "DeFi"
      - "NFT"
    enabled: true
    weight: 1.0
    priority: "medium"
    
  - name: "新能源"
    keywords:
      - "新能源"
      - "电动汽车"
      - "太阳能"
      - "风能"
      - "储能"
    enabled: true
    weight: 1.0
    priority: "medium"
```

## 配置参数详解

### 系统配置 (`system`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| name | string | "行业机会探测器" | 系统名称 |
| version | string | "1.0.0" | 系统版本 |
| debug | boolean | false | 调试模式开关 |
| log_level | string | "INFO" | 日志级别 (DEBUG, INFO, WARNING, ERROR) |

### 时间配置 (`time`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| window_days | integer | 30 | 历史数据窗口天数 |
| recent_days | integer | 7 | 近期数据窗口天数 |
| timezone | string | "UTC" | 时区设置 |

**配置建议**:
- `window_days`: 建议 30-90 天，平衡历史深度和计算效率
- `recent_days`: 建议 7-14 天，捕捉短期趋势
- `timezone`: 根据用户所在地区设置，如 "Asia/Shanghai"

### 信号权重配置 (`signals`)

| 参数 | 类型 | 默认值 | 说明 | 范围 |
|------|------|--------|------|------|
| demand | float | 0.4 | 需求信号权重 | 0.0-1.0 |
| momentum | float | 0.3 | 动量信号权重 | 0.0-1.0 |
| competition | float | 0.3 | 竞争信号权重 | 0.0-1.0 |

**配置原则**:
- 三个权重之和必须等于 1.0
- 根据分析重点调整权重分配
- 建议定期评估和调整权重设置

**典型配置场景**:
```yaml
# 市场导向分析
signals:
  demand: 0.5       # 重点关注市场需求
  momentum: 0.3
  competition: 0.2

# 技术趋势分析
signals:
  demand: 0.3
  momentum: 0.4     # 重点关注发展趋势
  competition: 0.3

# 竞争分析
signals:
  demand: 0.2
  momentum: 0.3
  competition: 0.5  # 重点关注竞争强度
```

### 数据源配置 (`data_sources`)

#### 通用配置项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| enabled | boolean | true | 数据源开关 |
| weight | float | varies | 数据源权重 |
| timeout | integer | 30 | 请求超时时间（秒） |
| max_retries | integer | 3 | 最大重试次数 |
| cache_hours | integer | 24 | 缓存时间（小时） |

#### 数据源特定配置

##### GitHub 配置
```yaml
github:
  enabled: true
  weight: 0.25
  token: "${GITHUB_TOKEN}"  # 强烈建议使用 token
  timeout: 60
  max_retries: 2
  cache_hours: 12
  search_type: "repositories"  # repositories, code, issues
  sort: "updated"              # updated, stars, forks
  order: "desc"                # desc, asc
  per_page: 100                # 每页结果数 (max: 100)
```

**GitHub Token 获取**:
1. 登录 GitHub 账户
2. 进入 Settings → Developer settings → Personal access tokens
3. 创建新的 token，选择适当的权限
4. 将 token 设置为环境变量 `GITHUB_TOKEN`

##### Reddit 配置
```yaml
reddit:
  enabled: true
  weight: 0.15
  timeout: 45
  max_retries: 2
  cache_hours: 8
  subreddits:                 # 特定子版块
    - "technology"
    - "programming"
    - "artificial"
  sort: "hot"                 # hot, new, top
  time_filter: "week"         # all, year, month, week, day
  limit: 100                  # 返回结果数量
```

### 输出配置 (`output`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| directory | string | "./outputs" | 输出目录 |
| formats | list | ["csv", "markdown"] | 输出格式 |
| generate_daily | boolean | true | 生成每日报告 |
| generate_insights | boolean | true | 生成洞察报告 |
| compress | boolean | false | 压缩输出文件 |

### 报告配置 (`report`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_items_per_topic | integer | 10 | 每个主题最大事件数 |
| max_papers_per_topic | integer | 2 | 每个主题最大论文数 |
| include_charts | boolean | false | 包含图表 |
| language | string | "zh-CN" | 报告语言 |
| template | string | "default" | 报告模板 |

### 监控配置 (`monitoring`)

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| enabled | boolean | true | 监控开关 |
| metrics_port | integer | 8080 | 指标端口 |
| health_check_interval | integer | 60 | 健康检查间隔（秒） |
| alert_thresholds | dict | - | 告警阈值 |

## 主题配置详解

### 主题结构

```yaml
topics:
  - name: "主题名称"           # 主题显示名称
    keywords:               # 关键词列表
      - "关键词1"
      - "关键词2"
    enabled: true           # 主题开关
    weight: 1.0             # 主题权重
    priority: "high"        # 优先级 (high, medium, low)
    custom_config:          # 自定义配置（可选）
      signals:
        demand: 0.5
        momentum: 0.3
        competition: 0.2
      data_sources:
        github:
          weight: 0.4
        gdelt:
          weight: 0.3
```

### 关键词配置技巧

#### 1. 同义词覆盖
```yaml
keywords:
  - "人工智能"
  - "AI"
  - "机器学习"
  - "深度学习"
  - "神经网络"
  - "Artificial Intelligence"  # 英文关键词
```

#### 2. 领域细分
```yaml
# 人工智能大主题下的细分领域
keywords:
  - "自然语言处理"
  - "计算机视觉"
  - "语音识别"
  - "推荐系统"
  - " autonomous driving"  # 自动驾驶
```

#### 3. 排除词配置
```yaml
# 高级配置，支持排除词
custom_config:
  exclude_keywords:
    - "游戏"      # 排除游戏相关的人工智能
    - "娱乐"      # 排除娱乐相关的内容
```

### 主题权重配置

#### 权重分配原则
- 核心业务主题：1.0-1.5
- 重要关注主题：0.8-1.0
- 一般监控主题：0.5-0.8
- 试验性主题：0.3-0.5

#### 动态权重调整
```yaml
topics:
  - name: "人工智能"
    weight: 1.2  # 当前重点关注
    priority: "high"
    
  - name: "区块链"
    weight: 0.8  # 一般关注
    priority: "medium"
    
  - name: "虚拟现实"
    weight: 0.5  # 试验性关注
    priority: "low"
```

## 环境变量配置

### 支持的环境变量

```bash
# API 密钥
export GITHUB_TOKEN="your_github_token_here"
export REDDIT_CLIENT_ID="your_reddit_client_id"
export REDDIT_CLIENT_SECRET="your_reddit_client_secret"

# 系统配置
export OPPORTUNITY_DETECTOR_CONFIG="/path/to/config.yml"
export OPPORTUNITY_DETECTOR_LOG_LEVEL="DEBUG"
export OPPORTUNITY_DETECTOR_OUTPUT_DIR="/path/to/outputs"

# 数据库配置（如使用）
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
export REDIS_URL="redis://localhost:6379"

# 监控配置
export PROMETHEUS_PORT="8080"
export GRAFANA_URL="http://localhost:3000"
```

### 环境变量引用

在配置文件中使用环境变量：
```yaml
github:
  token: "${GITHUB_TOKEN}"              # 直接引用
  backup_token: "${GITHUB_TOKEN_BACKUP:-default_token}"  # 带默认值
  
output:
  directory: "${OPPORTUNITY_DETECTOR_OUTPUT_DIR:-./outputs}"
```

## 配置验证

### 内置验证规则

#### 1. 基本格式验证
- YAML 语法正确性
- 必填字段完整性
- 数据类型正确性

#### 2. 业务逻辑验证
- 信号权重之和为 1.0
- 时间窗口参数合理性
- 数据源权重范围有效性

#### 3. 依赖关系验证
- 启用的数据源配置完整性
- API 密钥等敏感信息存在性
- 输出目录可写性

### 自定义验证

```python
# 配置验证器示例
class ConfigValidator:
    def validate(self, config: Dict) -> ValidationResult:
        errors = []
        warnings = []
        
        # 验证信号权重
        signal_weights = config.get('signals', {})
        total_weight = sum(signal_weights.values())
        if abs(total_weight - 1.0) > 0.001:
            errors.append(f"信号权重之和必须为 1.0，当前为 {total_weight}")
        
        # 验证时间窗口
        window_days = config.get('time', {}).get('window_days', 0)
        recent_days = config.get('time', {}).get('recent_days', 0)
        if recent_days >= window_days:
            errors.append("近期窗口天数必须小于历史窗口天数")
        
        # 验证数据源配置
        data_sources = config.get('data_sources', {})
        enabled_sources = [name for name, source in data_sources.items() 
                          if source.get('enabled', False)]
        
        if not enabled_sources:
            warnings.append("没有启用任何数据源")
        
        return ValidationResult(errors=errors, warnings=warnings)
```

## 配置模板

### 快速开始模板
```yaml
# config/quickstart.yml
system:
  name: "机会探测器"
  debug: false
  log_level: "INFO"

time:
  window_days: 30
  recent_days: 7

signals:
  demand: 0.4
  momentum: 0.3
  competition: 0.3

data_sources:
  gdelt:
    enabled: true
    weight: 0.4
  github:
    enabled: true
    weight: 0.3
    token: "${GITHUB_TOKEN}"
  hackernews:
    enabled: true
    weight: 0.3

topics:
  - name: "人工智能"
    keywords: ["人工智能", "AI", "机器学习"]
    enabled: true
```

### 生产环境模板
```yaml
# config/production.yml
system:
  name: "行业机会探测器"
  debug: false
  log_level: "WARNING"

time:
  window_days: 90      # 更长的历史窗口
  recent_days: 14      # 更长的近期窗口

signals:
  demand: 0.5          # 更重视需求信号
  momentum: 0.3
  competition: 0.2

data_sources:
  gdelt:
    enabled: true
    weight: 0.35
    timeout: 60
    max_retries: 5
    cache_hours: 48    # 更长的缓存时间
    
  github:
    enabled: true
    weight: 0.30
    token: "${GITHUB_TOKEN}"
    timeout: 120
    max_retries: 3
    cache_hours: 24
    
  hackernews:
    enabled: true
    weight: 0.20
    timeout: 60
    max_retries: 3
    cache_hours: 12
    
  reddit:
    enabled: true
    weight: 0.10
    timeout: 90
    max_retries: 3
    cache_hours: 16
    
  arxiv:
    enabled: true
    weight: 0.05
    timeout: 60
    max_retries: 3
    cache_hours: 48

output:
  directory: "/data/outputs"
  formats: ["csv", "markdown", "json"]
  generate_daily: true
  compress: true        # 启用压缩

monitoring:
  enabled: true
  metrics_port: 8080
  health_check_interval: 300  # 5分钟检查一次
```

### 开发环境模板
```yaml
# config/development.yml
system:
  name: "机会探测器-开发版"
  debug: true           # 启用调试模式
  log_level: "DEBUG"    # 详细日志

time:
  window_days: 7        # 较短的历史窗口，加快测试
  recent_days: 3        # 较短的近期窗口

signals:
  demand: 0.4
  momentum: 0.3
  competition: 0.3

data_sources:
  gdelt:
    enabled: true
    weight: 0.5         # 简化数据源，主要使用GDELT
    cache_hours: 1      # 短缓存时间，便于测试
    
  github:
    enabled: false      # 禁用其他数据源，加快测试
    
  hackernews:
    enabled: false
    
  reddit:
    enabled: false
    
  arxiv:
    enabled: false

output:
  directory: "./test_outputs"
  formats: ["csv", "markdown"]  # 简化输出格式
  generate_daily: false         # 不生成每日报告

topics:
  - name: "测试主题"
    keywords: ["test", "testing"]
    enabled: true
```

## 配置管理最佳实践

### 1. 配置版本控制
- 使用 Git 管理配置文件
- 为不同环境创建分支
- 记录配置变更历史

### 2. 配置安全
- 敏感信息使用环境变量
- 加密存储 API 密钥
- 限制配置文件的访问权限

### 3. 配置测试
- 在测试环境验证配置
- 使用配置验证工具
- 建立配置回滚机制

### 4. 配置文档化
- 为每个配置项编写说明
- 提供配置示例
- 建立配置变更流程

## 故障排除

### 常见配置错误

#### 1. YAML 语法错误
**问题**: 缩进不正确、缺少冒号等
**解决**: 使用 YAML 验证工具检查语法

#### 2. 信号权重和不等于 1.0
**问题**: 权重配置错误
**解决**: 检查权重计算，确保总和为 1.0

#### 3. 数据源配置缺失
**问题**: 启用的数据源缺少必要配置
**解决**: 检查数据源配置完整性

#### 4. 环境变量未设置
**问题**: 引用的环境变量不存在
**解决**: 设置相应的环境变量或提供默认值

### 调试技巧

#### 1. 启用调试模式
```yaml
system:
  debug: true
  log_level: "DEBUG"
```

#### 2. 逐步验证配置
```bash
# 验证基本配置
python -m opportunity_detector.config --validate --config config/basic.yml

# 测试单个数据源
python -m opportunity_detector.config --test-source gdelt --config config/test.yml
```

#### 3. 使用配置生成工具
```python
# 配置生成器示例
from opportunity_detector.config import ConfigGenerator

generator = ConfigGenerator()
config = generator.generate_config(
    topics=["人工智能", "区块链"],
    output_formats=["csv", "markdown"],
    data_sources=["gdelt", "github"],
    environment="production"
)

generator.save_config(config, "config/generated.yml")
```

## 总结

通过合理的配置管理，用户可以灵活地定制行业机会探测器的行为，适应不同的使用场景和需求。配置文件提供了丰富的参数选项，同时保持了易用性和可维护性。建议用户根据实际需求选择合适的配置模板，并遵循最佳实践进行配置管理。
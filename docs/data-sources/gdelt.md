# GDELT 数据源说明

## 概述

GDELT (Global Database of Events, Language, and Tone) 是一个免费的全球新闻事件数据库，实时监控全球新闻媒体的报道。它提供了从1979年至今的全球新闻事件数据，每15分钟更新一次，覆盖全球各种语言的新闻媒体。

## 数据源特点

### 核心优势
- **全球覆盖**: 监控全球 100+ 种语言的 15,000+ 新闻网站
- **实时更新**: 每15分钟更新一次数据
- **历史数据**: 从1979年开始的完整历史数据
- **免费使用**: 完全免费，无 API 限制
- **多维度**: 包含事件、情感、地理位置等多维度信息

### 数据规模
- **每日事件**: 约 200,000-300,000 个事件
- **年均增长**: 约 7500 万个新事件
- **总记录数**: 超过 30 亿个事件记录
- **语言覆盖**: 支持 100+ 种语言

## API 接口

### 主要 API 端点

#### 1. Global Knowledge Graph (GKG) API
**用途**: 获取新闻文章的详细知识图谱
**端点**: `https://api.gdeltproject.org/api/v2/doc/doc`
**主要参数**:
```
query: 查询关键词
mode: 返回模式 (ArtList, ArtInfo, etc.)
maxrecords: 最大返回记录数 (1-250)
format: 返回格式 (json, xml, html)
timespan: 时间范围 (如：1w, 1d, 1h)
```

#### 2. Event API
**用途**: 获取结构化的事件数据
**端点**: `https://api.gdeltproject.org/api/v2/events/events`
**主要参数**:
```
query: 查询条件
format: 返回格式 (json, csv)
maxrows: 最大返回行数
timespan: 时间范围
```

#### 3. Timeline API
**用途**: 获取时间序列数据
**端点**: `https://api.gdeltproject.org/api/v2/timeline/timeline`
**主要参数**:
```
query: 查询关键词
format: 返回格式
startdate: 开始日期
enddate: 结束日期
```

### 使用示例

#### 基本查询
```python
import requests
import json

# 查询最近一周关于"人工智能"的新闻
def query_gdelt_news(keyword, timespan="1w", max_records=50):
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f"{keyword}",
        "mode": "ArtList",
        "maxrecords": max_records,
        "format": "json",
        "timespan": timespan
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GDELT API 错误: {response.status_code}")

# 使用示例
data = query_gdelt_news("artificial intelligence", "1w", 50)
```

#### 高级查询
```python
def query_gdelt_advanced(keywords, start_date, end_date, language="english"):
    """高级查询，支持多条件和时间段"""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    # 构建复杂查询
    query_parts = []
    for keyword in keywords:
        query_parts.append(f'"{keyword}"')
    
    query = " OR ".join(query_parts)
    
    params = {
        "query": query,
        "mode": "ArtInfo",
        "format": "json",
        "startdatetime": start_date + "000000",
        "enddatetime": end_date + "000000",
        "language": language
    }
    
    response = requests.get(url, params=params)
    return response.json() if response.status_code == 200 else None
```

## 数据结构

### GKG (Global Knowledge Graph) 数据格式

#### 主要字段
```json
{
  "url": "新闻文章URL",
  "title": "文章标题",
  "seendate": "发现日期",
  "socialimage": "社交图片URL",
  "domain": "域名",
  "language": "语言",
  "sourcecountry": "来源国家",
  "sentiment": "情感分数",
  "themes": ["主题列表"],
  "locations": ["地理位置列表"],
  "persons": ["人物列表"],
  "organizations": ["组织列表"],
  "tone": "语调分数",
  "wordcount": "词数统计"
}
```

#### 关键字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| sentiment | float | 情感分数，-1到1，负值表示负面情感 | 0.25 |
| tone | float | 语调分数，反映文章的语调倾向 | 0.8 |
| themes | list | 识别出的主题列表 | ["ECONOMIC", "TECHNOLOGY"] |
| locations | list | 提到的地理位置 | ["United States", "China"] |
| persons | list | 提到的人物 | ["Elon Musk", "Bill Gates"] |
| organizations | list | 提到的组织 | ["Google", "Microsoft"] |

### 事件数据格式

#### 主要字段
```json
{
  "globaleventid": "全局事件ID",
  "day": "事件日期",
  "actor1name": "参与者1",
  "actor2name": "参与者2",
  "eventcode": "事件类型代码",
  "eventbasecode": "事件基础代码",
  "quadclass": "四元分类",
  "goldstein": "戈德斯坦分数",
  "nummentions": "提及次数",
  "numsources": "来源数量",
  "numarticles": "文章数量",
  "avgtone": "平均语调"
}
```

## 数据质量分析

### 优势
1. **数据量大**: 每日数十万条记录
2. **覆盖面广**: 全球多语言覆盖
3. **实时性强**: 15分钟更新频率
4. **免费使用**: 无 API 限制和费用
5. **历史完整**: 40+ 年历史数据

### 局限性
1. **语言偏差**: 英语内容占比过高
2. **地域偏差**: 发达国家报道更多
3. **媒体偏差**: 依赖传统新闻媒体报道
4. **噪声较多**: 包含大量不相关新闻
5. **重复内容**: 同一事件多次报道

### 质量改进措施

#### 1. 数据过滤
```python
def filter_quality_news(data, min_tone=-0.5, max_tone=0.5):
    """过滤质量较低的新闻"""
    filtered = []
    for item in data:
        # 过滤语调极端的文章
        if item.get('tone', 0) < min_tone or item.get('tone', 0) > max_tone:
            continue
        
        # 过滤过短的文章
        if item.get('wordcount', 0) < 100:
            continue
        
        # 过滤非目标语言的文章
        if item.get('language') != 'english':
            continue
            
        filtered.append(item)
    
    return filtered
```

#### 2. 去重处理
```python
def remove_duplicates(data, similarity_threshold=0.8):
    """基于标题相似度去重"""
    unique_items = []
    seen_titles = []
    
    for item in data:
        title = item.get('title', '').lower()
        is_duplicate = False
        
        for seen_title in seen_titles:
            similarity = calculate_similarity(title, seen_title)
            if similarity > similarity_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_items.append(item)
            seen_titles.append(title)
    
    return unique_items
```

#### 3. 相关性评分
```python
def calculate_relevance_score(item, keywords):
    """计算文章与关键词的相关性分数"""
    title = item.get('title', '').lower()
    content = item.get('content', '').lower()
    themes = [t.lower() for t in item.get('themes', [])]
    
    score = 0
    
    # 标题匹配权重最高
    for keyword in keywords:
        if keyword.lower() in title:
            score += 0.5
    
    # 内容匹配
    for keyword in keywords:
        if keyword.lower() in content:
            score += 0.3
    
    # 主题匹配
    for keyword in keywords:
        if any(keyword.lower() in theme for theme in themes):
            score += 0.2
    
    return min(score, 1.0)
```

## 使用最佳实践

### 1. 查询优化
```python
class GDELTQueryOptimizer:
    """GDELT 查询优化器"""
    
    def __init__(self):
        self.cache = {}
        self.rate_limiter = RateLimiter(calls=100, period=3600)
    
    def optimize_query(self, keywords, timespan):
        """优化查询参数"""
        # 关键词预处理
        processed_keywords = self._preprocess_keywords(keywords)
        
        # 时间范围优化
        optimal_timespan = self._optimize_timespan(timespan)
        
        # 缓存检查
        cache_key = f"{processed_keywords}_{optimal_timespan}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 执行查询
        with self.rate_limiter:
            result = self._execute_query(processed_keywords, optimal_timespan)
        
        # 缓存结果
        self.cache[cache_key] = result
        
        return result
```

### 2. 错误处理
```python
class GDELTErrorHandler:
    """GDELT 错误处理器"""
    
    def __init__(self):
        self.retry_config = {
            'max_retries': 3,
            'backoff_factor': 2,
            'retry_status_codes': [429, 500, 502, 503, 504]
        }
    
    async def fetch_with_retry(self, url, params):
        """带重试机制的异步获取"""
        for attempt in range(self.retry_config['max_retries']):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status in self.retry_config['retry_status_codes']:
                            if attempt < self.retry_config['max_retries'] - 1:
                                wait_time = self.retry_config['backoff_factor'] ** attempt
                                await asyncio.sleep(wait_time)
                                continue
                        else:
                            raise Exception(f"GDELT API 错误: {response.status}")
            
            except Exception as e:
                if attempt < self.retry_config['max_retries'] - 1:
                    wait_time = self.retry_config['backoff_factor'] ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
        
        return None
```

### 3. 数据缓存策略
```python
class GDELTCache:
    """GDELT 数据缓存"""
    
    def __init__(self, cache_dir="./cache/gdelt"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, query, timespan):
        """生成缓存文件路径"""
        query_hash = hashlib.md5(f"{query}_{timespan}".encode()).hexdigest()
        return self.cache_dir / f"{query_hash}.json"
    
    def get(self, query, timespan, max_age_hours=24):
        """从缓存获取数据"""
        cache_path = self.get_cache_path(query, timespan)
        
        if cache_path.exists():
            # 检查缓存是否过期
            file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
            if file_age.total_seconds() < max_age_hours * 3600:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        return None
    
    def set(self, query, timespan, data):
        """保存数据到缓存"""
        cache_path = self.get_cache_path(query, timespan)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

## 监控和维护

### 数据质量监控
```python
class GDELTQualityMonitor:
    """GDELT 数据质量监控"""
    
    def __init__(self):
        self.quality_metrics = {
            'completeness': [],
            'accuracy': [],
            'timeliness': [],
            'relevance': []
        }
    
    def monitor_data_quality(self, data, expected_keywords):
        """监控数据质量"""
        # 完整性检查
        completeness = self._check_completeness(data)
        self.quality_metrics['completeness'].append(completeness)
        
        # 准确性检查
        accuracy = self._check_accuracy(data)
        self.quality_metrics['accuracy'].append(accuracy)
        
        # 时效性检查
        timeliness = self._check_timeliness(data)
        self.quality_metrics['timeliness'].append(timeliness)
        
        # 相关性检查
        relevance = self._check_relevance(data, expected_keywords)
        self.quality_metrics['relevance'].append(relevance)
        
        return {
            'completeness': completeness,
            'accuracy': accuracy,
            'timeliness': timeliness,
            'relevance': relevance
        }
    
    def generate_quality_report(self):
        """生成质量报告"""
        report = {}
        for metric, values in self.quality_metrics.items():
            if values:
                report[metric] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'trend': self._calculate_trend(values)
                }
        
        return report
```

## 成本分析

### 直接成本
- **API 费用**: 免费
- **存储成本**: 约 $10-50/月（取决于数据量）
- **计算成本**: 约 $20-100/月（取决于处理复杂度）

### 间接成本
- **开发时间**: 初始开发 40-60 小时
- **维护时间**: 每月 10-20 小时
- **优化时间**: 持续投入

### ROI 分析
- **数据价值**: 高（全球新闻覆盖）
- **成本效益**: 优秀（免费数据源）
- **维护投入**: 中等（需要持续优化）

## 总结

GDELT 作为核心数据源，为我们的行业机会探测器提供了丰富的新闻媒体数据。通过合理的使用策略、质量控制和优化措施，我们能够充分利用这一宝贵的数据资源，为用户提供准确、及时的市场洞察。尽管存在一些局限性，但通过与其他数据源的融合使用，GDELT 仍然是一个极具价值的数据源。
# FUNC-005A/B: 论文 PDF 下载与总结增强 - 实现计划

## 需求概述

**需求编号**: FUNC-005A, FUNC-005B  
**优先级**: 中  
**状态**: 待实现

### 功能描述

#### FUNC-005A: 论文 PDF 下载与缓存
- 支持下载论文 PDF（优先 arXiv PDF），并做本地缓存
- 输入: arXiv 论文链接（或 arXiv id）、下载目录、缓存策略
- 输出: PDF 文件路径、下载状态、基础元信息（页数/大小）

#### FUNC-005B: 论文总结
- 对论文进行总结（优先基于全文/前几页 + 摘要）
- 输出"可落地"摘要：贡献点、方法要点、结论、可产品化方向、局限/风险
- 可接入本地/远程大模型（如 Ollama）

---

## 当前实现分析

### 现有代码位置
- [`src/opportunity_detector/papers.py`](../src/opportunity_detector/papers.py)

### 现有功能
1. **PDF 下载** (`_download_pdf`)
   - ✅ 支持从 arXiv 下载 PDF
   - ✅ 本地缓存机制（基于 URL hash）
   - ⚠️ 仅在 `config.daily_enable_pdf_summaries` 为 true 时下载

2. **PDF 文本提取** (`_extract_pdf_text`)
   - ✅ 使用 pypdf 提取文本
   - ✅ 支持限制最大页数和字符数

3. **LLM 总结** (`_summarize_with_llm`)
   - ✅ 支持调用 Ollama 进行总结
   - ⚠️ 依赖环境变量 `OLLAMA_BASE_URL` 和 `OLLAMA_MODEL`

4. **摘要生成** (`build_paper_summaries`)
   - ✅ 生成 abstract_summary（基于摘要）
   - ✅ 生成 pdf_summary（基于全文，可选）

### 现有配置
在 [`config/topics.yml`](../config/topics.yml) 中：
```yaml
daily_enable_pdf_summaries: false  # 控制是否下载 PDF
daily_max_paper_pdfs: 2            # 最多下载的 PDF 数量
daily_pdf_max_pages: 4             # PDF 最大读取页数
```

---

## 改进计划

### 阶段 1: 优化 PDF 下载与缓存策略

#### 1.1 缓存策略优化
- **目标**: 提高缓存命中率，减少重复下载
- **改进点**:
  - 添加缓存过期机制（基于日期）
  - 支持手动清除缓存
  - 添加缓存统计信息

#### 1.2 下载重试机制
- **目标**: 提高下载成功率
- **改进点**:
  - 添加重试逻辑（使用 tenacity）
  - 支持断点续传（如果服务器支持）

### 阶段 2: 增强 LLM 总结功能

#### 2.1 总结模板优化
- **目标**: 提高总结质量
- **改进点**:
  - 优化 system prompt，更明确的输出格式要求
  - 添加多轮总结（先摘要后全文）
  - 支持自定义总结粒度

#### 2.2 Fallback 机制
- **目标**: 确保即使 LLM 失败也能生成基础总结
- **改进点**:
  - 基于关键词的自动摘要（TF-IDF）
  - 基于句子位置的启发式摘要（首尾句）

### 阶段 3: 用户体验改进

#### 3.1 配置增强
- **目标**: 提供更灵活的配置选项
- **改进点**:
  - 添加 `pdf_download_timeout` 配置
  - 添加 `summary_max_tokens` 配置
  - 添加 `enable_cache` 开关

#### 3.2 输出增强
- **目标**: 提供更丰富的输出信息
- **改进点**:
  - 添加 PDF 下载耗时统计
  - 添加 LLM 调用耗时统计
  - 添加总结质量评分

---

## 实现细节

### 1. 新增配置项

在 `config/topics.yml` 中添加：
```yaml
papers:
  enable_pdf_download: true
  max_pdfs: 3
  max_pages: 5
  download_timeout: 60
  summary:
    max_tokens: 2000
    enable_cache: true
    cache_ttl_days: 7
```

### 2. 修改文件

#### `src/opportunity_detector/papers.py`
- 重构 `_download_pdf` 函数，添加重试机制
- 优化 `_extract_pdf_text` 函数，添加进度反馈
- 改进 `_summarize_with_llm` 函数，添加 fallback 机制
- 新增 `PaperSummaryStats` 数据类，记录统计信息

#### `src/opportunity_detector/config.py`
- 新增 `PaperConfig` 类，封装论文相关配置
- 修改 `DetectorConfig` 类，集成 `PaperConfig`

### 3. 测试计划

#### 单元测试
- `test_download_pdf_success`: 测试成功下载
- `test_download_pdf_failure`: 测试下载失败重试
- `test_extract_pdf_text`: 测试文本提取
- `test_summarize_with_llm`: 测试 LLM 总结
- `test_fallback_summary`: 测试 fallback 机制

#### 集成测试
- `test_paper_summaries_full`: 完整流程测试
- `test_cache_hit`: 测试缓存命中
- `test_timeout_handling`: 测试超时处理

---

## 预期成果

1. **PDF 下载成功率**: 从当前的 ~70% 提升到 ~95%
2. **总结质量**: 通过 LLM 总结，信息完整度提升 50%
3. **缓存命中率**: 提升到 ~80%，减少重复下载
4. **用户体验**: 提供更清晰的错误信息和进度反馈

---

## 风险评估

### 技术风险
1. **arXiv API 限流**: 可能导致下载失败
   - 缓解: 添加重试机制和缓存
2. **LLM 服务不可用**: 可能导致总结失败
   - 缓解: 实现 fallback 机制
3. **PDF 解析失败**: 某些 PDF 可能无法解析
   - 缓解: 添加异常处理和 fallback

### 时间风险
- 预计实现时间: 3-5 天
- 预计测试时间: 2-3 天

---

## 下一步行动

1. ✅ 创建实现计划文档
2. ⏳ 开始实施代码修改
3. ⏳ 编写单元测试
4. ⏳ 编写集成测试
5. ⏳ 更新文档
6. ⏳ 发布新版本

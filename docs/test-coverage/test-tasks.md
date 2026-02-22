# 测试任务列表

本文档记录测试相关的任务计划，包括已完成和待完成的任务。

---

## 任务列表概览

| 任务编号 | 任务名称 | 优先级 | 状态 | 关联需求 | 关联版本 |
|---------|---------|--------|------|---------|---------|
| TEST-001 | 信号计算测试 | 高 | ⏳ 待完成 | FUNC-006 | v0.2.0 |
| TEST-002 | 数据标准化测试 | 高 | ⏳ 待完成 | FUNC-008 | v0.2.0 |
| TEST-003 | CLI 测试 | 高 | ⏳ 待完成 | FUNC-017 | v0.2.0 |
| TEST-004 | 参数验证测试 | 高 | ⏳ 待完成 | FUNC-018 | v0.2.0 |
| TEST-005 | 研究论文采集测试 | 中 | ⏳ 待完成 | FUNC-005 | v0.2.0 |
| TEST-006 | 机会类型识别测试 | 中 | ⏳ 待完成 | FUNC-010 | v0.2.0 |
| TEST-007 | 历史对比测试 | 中 | ⏳ 待完成 | FUNC-013 | v0.2.0 |
| TEST-008 | 配置文件加载测试 | 低 | ⏳ 待完成 | FUNC-014 | v0.3.0 |
| TEST-009 | 时间窗口计算测试 | 低 | ⏳ 待完成 | FUNC-015 | v0.3.0 |
| TEST-010 | 集成测试 | 高 | ⏳ 待完成 | 多个需求 | v0.2.0 |
| TEST-011 | 端到端测试 | 中 | ⏳ 待完成 | 多个需求 | v0.2.0 |
| TEST-012 | 性能测试 | 中 | ⏳ 待完成 | 多个需求 | v0.3.0 |

---

## 详细任务列表

### 高优先级任务

#### TEST-001: 信号计算测试

**状态**: ⏳ 待完成  
**优先级**: 高  
**关联需求**: FUNC-006  
**关联版本**: v0.2.0

**任务描述**: 测试需求、动量、竞争三个核心信号的计算逻辑

**测试用例**:
- [ ] `test_demand_signal_calculation`: 测试需求信号计算
- [ ] `test_momentum_signal_calculation`: 测试动量信号计算
- [ ] `test_competition_signal_calculation`: 测试竞争信号计算
- [ ] `test_signal_calculation_with_empty_data`: 测试空数据情况
- [ ] `test_signal_calculation_with_single_data`: 测试单数据情况

**验收标准**:
- [ ] 所有信号计算逻辑正确
- [ ] 边界条件覆盖
- [ ] 测试覆盖率 ≥ 80%

**文件位置**: `tests/test_fusion.py`

---

#### TEST-002: 数据标准化测试

**状态**: ⏳ 待完成  
**优先级**: 高  
**关联需求**: FUNC-008  
**关联版本**: v0.2.0

**任务描述**: 测试 min-max 标准化算法

**测试用例**:
- [ ] `test_min_max_normalize_basic`: 测试基本标准化
- [ ] `test_min_max_normalize_all_same`: 测试所有值相同的情况
- [ ] `test_min_max_normalize_empty`: 测试空数据情况
- [ ] `test_min_max_normalize_negative`: 测试负数情况
- [ ] `test_min_max_normalize_large_values`: 测试大数值情况

**验收标准**:
- [ ] 标准化结果在 0-1 范围内
- [ ] 边界条件覆盖
- [ ] 测试覆盖率 ≥ 80%

**文件位置**: `tests/test_fusion.py`

---

#### TEST-003: CLI 测试

**状态**: ⏳ 待完成  
**优先级**: 高  
**关联需求**: FUNC-017  
**关联版本**: v0.2.0

**任务描述**: 测试命令行参数解析和执行

**测试用例**:
- [ ] `test_cli_help`: 测试帮助信息输出
- [ ] `test_cli_version`: 测试版本信息输出
- [ ] `test_cli_run`: 测试运行命令
- [ ] `test_cli_with_config`: 测试配置文件参数
- [ ] `test_cli_with_topics`: 测试主题参数
- [ ] `test_cli_with_days`: 测试时间窗口参数

**验收标准**:
- [ ] 所有命令行参数正确解析
- [ ] 错误参数处理正确
- [ ] 测试覆盖率 ≥ 80%

**文件位置**: `tests/test_cli.py` (新建)

---

#### TEST-004: 参数验证测试

**状态**: ⏳ 待完成  
**优先级**: 高  
**关联需求**: FUNC-018  
**关联版本**: v0.2.0

**任务描述**: 测试输入参数的有效性验证

**测试用例**:
- [ ] `test_config_weights_sum`: 测试权重之和为1.0
- [ ] `test_config_time_windows`: 测试时间窗口参数
- [ ] `test_config_topics_consistency`: 测试 topics 和 topic_keywords 一致性
- [ ] `test_config_invalid_value`: 测试无效参数值
- [ ] `test_config_missing_required`: 测试缺失必填参数

**验收标准**:
- [ ] 所有验证规则实现
- [ ] 错误提示清晰明确
- [ ] 测试覆盖率 ≥ 80%

**文件位置**: `tests/test_config.py` (新建)

---

#### TEST-010: 集成测试

**状态**: ⏳ 待完成  
**优先级**: 高  
**关联需求**: 多个需求  
**关联版本**: v0.2.0

**任务描述**: 添加集成测试，测试完整流程

**测试场景**:
- [ ] `test_full_data_collection`: 完整数据采集流程
- [ ] `test_signal_calculation_pipeline`: 信号计算流程
- [ ] `test_insight_generation_pipeline`: 洞察生成流程
- [ ] `test_report_generation_pipeline`: 报告生成流程
- [ ] `test_end_to_end_run`: 完整运行流程

**验收标准**:
- [ ] 所有核心流程测试通过
- [ ] 错误处理测试通过
- [ ] 测试覆盖率 ≥ 70%

**文件位置**: `tests/test_integration.py` (新建)

---

### 中优先级任务

#### TEST-005: 研究论文采集测试

**状态**: ⏳ 待完成  
**优先级**: 中  
**关联需求**: FUNC-005  
**关联版本**: v0.2.0

**任务描述**: 测试实际 arXiv API 调用

**测试用例**:
- [ ] `test_arxiv_api_call`: 测试实际 API 调用
- [ ] `test_arxiv_api_error_handling`: 测试网络错误处理
- [ ] `test_arxiv_api_timeout`: 测试超时处理
- [ ] `test_arxiv_id_extraction`: 测试 ID 提取
- [ ] `test_arxiv_pdf_url_generation`: 测试 PDF URL 生成

**验收标准**:
- [ ] API 调用成功
- [ ] 错误处理正确
- [ ] 测试覆盖率 ≥ 70%

**文件位置**: `tests/test_papers.py`

---

#### TEST-006: 机会类型识别测试

**状态**: ⏳ 待完成  
**优先级**: 中  
**关联需求**: FUNC-010  
**关联版本**: v0.2.0

**任务描述**: 测试所有 5 种机会类型识别

**测试用例**:
- [ ] `test_insight_type_fast_growing_white_space`: 测试 fast_growing_white_space 类型
- [ ] `test_insight_type_crowded_hot_market`: 测试 crowded_hot_market 类型
- [ ] `test_insight_type_early_signal_niche`: 测试 early_signal_niche 类型
- [ ] `test_insight_type_steady_pain_low_competition`: 测试 steady_pain_low_competition 类型
- [ ] `test_insight_type_watchlist`: 测试 watchlist 类型

**验收标准**:
- [ ] 所有类型识别正确
- [ ] 边界条件覆盖
- [ ] 测试覆盖率 ≥ 80%

**文件位置**: `tests/test_insights.py`

---

#### TEST-007: 历史对比测试

**状态**: ⏳ 待完成  
**优先级**: 中  
**关联需求**: FUNC-013  
**关联版本**: v0.2.0

**任务描述**: 测试多日报告对比

**测试用例**:
- [ ] `test_daily_report_comparison`: 测试多日报告对比
- [ ] `test_trend_analysis`: 测试趋势分析
- [ ] `test_history_archive`: 测试历史归档
- [ ] `test_daily_report_with_missing_data`: 测试缺失数据处理

**验收标准**:
- [ ] 对比逻辑正确
- [ ] 趋势分析准确
- [ ] 测试覆盖率 ≥ 70%

**文件位置**: `tests/test_events.py`

---

### 低优先级任务

#### TEST-008: 配置文件加载测试

**状态**: ⏳ 待完成  
**优先级**: 低  
**关联需求**: FUNC-014  
**关联版本**: v0.3.0

**任务描述**: 测试 YAML 配置文件解析

**测试用例**:
- [ ] `test_config_file_loading`: 测试配置文件加载
- [ ] `test_config_default_values`: 测试默认值处理
- [ ] `test_config_override`: 测试配置覆盖
- [ ] `test_config_invalid_yaml`: 测试无效 YAML 处理

**验收标准**:
- [ ] 配置文件正确解析
- [ ] 默认值处理正确
- [ ] 测试覆盖率 ≥ 70%

**文件位置**: `tests/test_config.py`

---

#### TEST-009: 时间窗口计算测试

**状态**: ⏳ 待完成  
**优先级**: 低  
**关联需求**: FUNC-015  
**关联版本**: v0.3.0

**任务描述**: 测试时间窗口计算

**测试用例**:
- [ ] `test_time_window_calculation`: 测试时间范围计算
- [ ] `test_time_window_boundary`: 测试边界情况
- [ ] `test_time_window_with_timezone`: 测试时区处理

**验收标准**:
- [ ] 时间窗口计算正确
- [ ] 边界条件覆盖
- [ ] 测试覆盖率 ≥ 70%

**文件位置**: `tests/test_config.py`

---

#### TEST-012: 性能测试

**状态**: ⏳ 待完成  
**优先级**: 中  
**关联需求**: 多个需求  
**关联版本**: v0.3.0

**任务描述**: 测试系统性能指标

**测试场景**:
- [ ] `test_data_collection_performance`: 数据采集性能测试
- [ ] `test_report_generation_performance`: 报告生成性能测试
- [ ] `test_data_processing_performance`: 数据处理性能测试
- [ ] `test_concurrent_processing_performance`: 并发处理性能测试
- [ ] `test_memory_usage`: 内存使用测试

**验收标准**:
- [ ] 数据采集时间 ≤ 30s
- [ ] 报告生成时间 ≤ 5min
- [ ] 数据处理时间 ≤ 10s
- [ ] 内存使用合理

**文件位置**: `tests/test_performance.py` (新建)

---

## 任务完成统计

### 按优先级统计

| 优先级 | 总任务数 | 已完成 | 待完成 | 完成率 |
|--------|---------|--------|--------|--------|
| 高 | 4 | 0 | 4 | 0% |
| 中 | 4 | 0 | 4 | 0% |
| 低 | 1 | 0 | 1 | 0% |
| **总计** | **9** | **0** | **9** | **0%** |

### 按版本统计

| 版本 | 总任务数 | 已完成 | 待完成 | 完成率 |
|------|---------|--------|--------|--------|
| v0.2.0 | 7 | 0 | 7 | 0% |
| v0.3.0 | 2 | 0 | 2 | 0% |
| **总计** | **9** | **0** | **9** | **0%** |

---

## 任务依赖关系

```
TEST-001 (信号计算测试)
  └─ 无依赖

TEST-002 (数据标准化测试)
  └─ 无依赖

TEST-003 (CLI 测试)
  └─ 无依赖

TEST-004 (参数验证测试)
  └─ 无依赖

TEST-005 (研究论文采集测试)
  └─ TEST-001 (需要信号计算测试)

TEST-006 (机会类型识别测试)
  └─ TEST-001 (需要信号计算测试)

TEST-007 (历史对比测试)
  └─ TEST-005 (需要论文采集测试)

TEST-008 (配置文件加载测试)
  └─ TEST-004 (需要参数验证测试)

TEST-009 (时间窗口计算测试)
  └─ TEST-008 (需要配置文件加载测试)

TEST-010 (集成测试)
  ├─ TEST-001 (信号计算测试)
  ├─ TEST-002 (数据标准化测试)
  └─ TEST-005 (研究论文采集测试)

TEST-011 (端到端测试)
  └─ TEST-010 (需要集成测试)

TEST-012 (性能测试)
  └─ TEST-010 (需要集成测试)
```

---

## 下一步行动

1. **优先实现高优先级任务**:
   - TEST-001: 信号计算测试
   - TEST-002: 数据标准化测试
   - TEST-003: CLI 测试
   - TEST-004: 参数验证测试

2. **实现中优先级任务**:
   - TEST-005: 研究论文采集测试
   - TEST-006: 机会类型识别测试
   - TEST-007: 历史对比测试

3. **实现低优先级任务**:
   - TEST-008: 配置文件加载测试
   - TEST-009: 时间窗口计算测试

4. **实现性能测试**:
   - TEST-012: 性能测试

5. **更新测试覆盖率报告**:
   - 每完成 2-3 个任务，更新测试覆盖率报告

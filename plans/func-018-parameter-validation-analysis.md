# FUNC-018 参数验证需求分析

## 需求概述

**需求编号**: FUNC-018  
**需求名称**: 参数验证  
**优先级**: 中  
**当前状态**: ⚠️ 部分实现  

## 需求分析

### 1. 需求定义

FUNC-018 需求旨在确保系统在运行前对所有输入参数进行验证，包括：

1. **CLI 参数验证**：验证命令行参数的有效性
2. **配置文件验证**：验证配置文件的完整性和正确性
3. **组合验证**：验证多个参数之间的逻辑关系

### 2. 当前实现状态

#### 2.1 已实现部分

##### CLI 参数验证 (`src/opportunity_detector/validator.py`)

已实现以下验证功能：

1. **配置文件路径验证** ([`validate_config_path()`](src/opportunity_detector/validator.py:33))
   - 验证文件是否存在
   - 验证路径是否为文件
   - 验证文件扩展名（.yml/.yaml）

2. **输出路径验证** ([`validate_output_path()`](src/opportunity_detector/validator.py:66))
   - 验证父目录是否存在
   - 自动创建不存在的父目录
   - 验证目录是否可写

3. **组合验证** ([`validate_cli_args()`](src/opportunity_detector/validator.py:128))
   - 同时验证配置文件和输出路径
   - 统一错误处理

##### 配置验证 (`src/opportunity_detector/config.py`)

已实现以下验证功能：

1. **权重验证** ([`Weights`](src/opportunity_detector/config.py:11))
   - 验证权重非负
   - 验证权重之和为 1.0

2. **时间窗口验证** ([`DetectorConfig`](src/opportunity_detector/config.py:60))
   - 验证 `recent_days < window_days`
   - 验证 `daily_days <= recent_days`

3. **主题配置验证** ([`validate_topics()`](src/opportunity_detector/config.py:81), [`validate_topic_keywords()`](src/opportunity_detector/config.py:91))
   - 验证 topics 不为空
   - 验证 topic_keywords 格式
   - 验证 topics 和 topic_keywords 一致性

#### 2.2 未实现/不完整部分

##### 1. 配置文件内容验证

**缺失功能**：
- 配置文件语法验证（YAML 格式错误）
- 配置文件结构验证（必需字段检查）
- 配置文件值范围验证（超出字段定义的范围）

**影响**：
- YAML 语法错误时，错误信息不够友好
- 缺少自定义验证规则

##### 2. CLI 参数组合验证

**缺失功能**：
- 参数依赖关系验证（如：某些参数组合无效）
- 参数互斥验证（如：不能同时设置 A 和 B）

**影响**：
- 用户可能输入逻辑上矛盾的参数组合

##### 3. 配置文件路径与内容的一致性验证

**缺失功能**：
- 验证配置文件路径是否在允许的目录范围内
- 验证配置文件内容是否符合预期格式

**影响**：
- 安全性考虑（防止路径遍历攻击）

##### 4. 验证结果反馈优化

**缺失功能**：
- 验证失败时提供修复建议
- 验证结果可视化（表格形式展示）

**影响**：
- 用户体验不佳

## 实现计划

### 阶段一：配置文件内容验证增强

**文件**: `src/opportunity_detector/validator.py`

**实现内容**：
```python
class ConfigFileValidator:
    """配置文件内容验证器"""
    
    @staticmethod
    def validate_yaml_syntax(content: str) -> ValidationResult:
        """验证 YAML 语法"""
        pass
    
    @staticmethod
    def validate_required_fields(payload: dict) -> ValidationResult:
        """验证必需字段"""
        pass
    
    @staticmethod
    def validate_value_ranges(payload: dict) -> ValidationResult:
        """验证值范围"""
        pass
```

### 阶段二：CLI 参数组合验证

**文件**: `src/opportunity_detector/validator.py`

**实现内容**：
```python
class CLIValidator:
    """CLI 参数验证器"""
    
    @staticmethod
    def validate_parameter_dependencies(args: argparse.Namespace) -> ValidationResult:
        """验证参数依赖关系"""
        pass
    
    @staticmethod
    def validate_parameter_exclusions(args: argparse.Namespace) -> ValidationResult:
        """验证参数互斥"""
        pass
```

### 阶段三：配置文件路径安全验证

**文件**: `src/opportunity_detector/validator.py`

**实现内容**：
```python
class CLIValidator:
    """CLI 参数验证器"""
    
    @staticmethod
    def validate_config_path_safety(config_path: str, allowed_dirs: List[str]) -> ValidationResult:
        """验证配置文件路径安全性"""
        pass
```

### 阶段四：验证结果反馈优化

**文件**: `src/opportunity_detector/validator.py`

**实现内容**：
```python
def format_validation_errors(errors: List[str]) -> str:
    """格式化验证错误信息"""
    pass

def generate_fix_suggestions(error_type: str) -> List[str]:
    """生成修复建议"""
    pass
```

## 测试计划

### 单元测试

**文件**: `tests/test_validator.py`

**测试用例**：
1. YAML 语法错误验证
2. 必需字段缺失验证
3. 值范围验证
4. 参数依赖关系验证
5. 参数互斥验证
6. 路径安全验证

### 集成测试

**文件**: `tests/test_integration.py` (新建)

**测试场景**：
1. 完整的参数验证流程
2. 配置文件加载和验证
3. CLI 参数组合验证

## 文档更新

### 用户文档

**文件**: `docs/configuration/config-guide.md`

**更新内容**：
- 添加配置验证说明
- 添加常见验证错误及解决方案
- 添加配置示例

### 开发者文档

**文件**: `docs/developer-guide.md` (新建)

**更新内容**：
- 添加验证模块说明
- 添加验证规则文档
- 添加测试指南

## 优先级排序

1. **高优先级**：配置文件内容验证增强
2. **中优先级**：CLI 参数组合验证
3. **低优先级**：配置文件路径安全验证
4. **中优先级**：验证结果反馈优化

## 总结

FUNC-018 参数验证需求当前已实现基础的 CLI 参数验证和配置验证功能，但缺少：

1. 配置文件内容的深度验证
2. 参数组合的逻辑验证
3. 安全性验证
4. 用户友好的错误反馈

建议按照上述实现计划逐步完善。

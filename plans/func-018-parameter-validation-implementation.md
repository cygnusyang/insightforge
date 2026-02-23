# FUNC-018 参数验证实现计划

## 1. 需求概述

**需求编号**: FUNC-018  
**需求名称**: 参数验证  
**优先级**: 中  
**当前状态**: ⚠️ 部分实现  
**实现状态**: 🚧 进行中  

## 2. 需求分析

### 2.1 需求定义

FUNC-018 需求旨在确保系统在运行前对所有输入参数进行验证，包括：

1. **CLI 参数验证**：验证命令行参数的有效性
2. **配置文件验证**：验证配置文件的完整性和正确性
3. **组合验证**：验证多个参数之间的逻辑关系

### 2.2 当前实现状态

#### 2.2.1 已实现部分

**CLI 参数验证** ([`src/opportunity_detector/validator.py`](src/opportunity_detector/validator.py)):
- 配置文件路径验证
- 输出路径验证
- 组合验证

**配置验证** ([`src/opportunity_detector/config.py`](src/opportunity_detector/config.py)):
- 权重验证（非负、之和为 1.0）
- 时间窗口验证（recent_days < window_days, daily_days <= recent_days）
- 主题配置验证（topics 和 topic_keywords 一致性）

#### 2.2.2 未实现/不完整部分

1. **配置文件内容验证**
   - YAML 语法验证
   - 必需字段检查
   - 值范围验证

2. **CLI 参数组合验证**
   - 参数依赖关系验证
   - 参数互斥验证

3. **配置文件路径安全验证**
   - 路径遍历防护
   - 允许目录范围验证

4. **验证结果反馈优化**
   - 修复建议
   - 可视化展示

## 3. 实现计划

### 3.1 阶段一：配置文件内容验证增强

**优先级**: 高  
**工作量**: 1 天  
**文件**: `src/opportunity_detector/validator.py`

#### 3.1.1 实现内容

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

#### 3.1.2 测试用例

**文件**: `tests/test_validator.py`

```python
class TestConfigFileValidator:
    def test_validate_yaml_syntax_valid(self) -> None:
        """测试有效 YAML 语法"""
        pass
    
    def test_validate_yaml_syntax_invalid(self) -> None:
        """测试无效 YAML 语法"""
        pass
    
    def test_validate_required_fields(self) -> None:
        """测试必需字段验证"""
        pass
    
    def test_validate_value_ranges(self) -> None:
        """测试值范围验证"""
        pass
```

### 3.2 阶段二：CLI 参数组合验证

**优先级**: 中  
**工作量**: 0.5 天  
**文件**: `src/opportunity_detector/validator.py`

#### 3.2.1 实现内容

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

#### 3.2.2 测试用例

```python
class TestCLIParameterValidation:
    def test_validate_parameter_dependencies(self) -> None:
        """测试参数依赖关系"""
        pass
    
    def test_validate_parameter_exclusions(self) -> None:
        """测试参数互斥"""
        pass
```

### 3.3 阶段三：配置文件路径安全验证

**优先级**: 低  
**工作量**: 0.5 天  
**文件**: `src/opportunity_detector/validator.py`

#### 3.3.1 实现内容

```python
class CLIValidator:
    """CLI 参数验证器"""
    
    @staticmethod
    def validate_config_path_safety(config_path: str, allowed_dirs: List[str]) -> ValidationResult:
        """验证配置文件路径安全性"""
        pass
```

#### 3.3.2 测试用例

```python
class TestConfigPathSecurity:
    def test_validate_config_path_safety_valid(self) -> None:
        """测试有效路径"""
        pass
    
    def test_validate_config_path_safety_invalid(self) -> None:
        """测试无效路径"""
        pass
```

### 3.4 阶段四：验证结果反馈优化

**优先级**: 中  
**工作量**: 0.5 天  
**文件**: `src/opportunity_detector/validator.py`

#### 3.4.1 实现内容

```python
def format_validation_errors(errors: List[str]) -> str:
    """格式化验证错误信息"""
    pass

def generate_fix_suggestions(error_type: str) -> List[str]:
    """生成修复建议"""
    pass
```

#### 3.4.2 测试用例

```python
class TestValidationFeedback:
    def test_format_validation_errors(self) -> None:
        """测试错误信息格式化"""
        pass
    
    def test_generate_fix_suggestions(self) -> None:
        """测试修复建议生成"""
        pass
```

## 4. 详细实现任务

### 4.1 任务 1.1: ConfigFileValidator 类实现

**文件**: `src/opportunity_detector/validator.py`  
**优先级**: 高  
**工作量**: 1 天  

#### 4.1.1 验证 YAML 语法

```python
@staticmethod
def validate_yaml_syntax(content: str) -> ValidationResult:
    """验证 YAML 语法"""
    try:
        yaml.safe_load(content)
        return ValidationResult(is_valid=True, message="YAML 语法有效")
    except yaml.YAMLError as e:
        return ValidationResult(
            is_valid=False,
            message=f"YAML 语法错误: {str(e)}"
        )
```

#### 4.1.2 验证必需字段

```python
@staticmethod
def validate_required_fields(payload: dict) -> ValidationResult:
    """验证必需字段"""
    required_fields = [
        "window_days", "recent_days", "weights", "topics", "topic_keywords"
    ]
    missing_fields = []
    
    for field in required_fields:
        if field not in payload:
            missing_fields.append(field)
    
    if missing_fields:
        return ValidationResult(
            is_valid=False,
            message=f"缺少必需字段: {', '.join(missing_fields)}"
        )
    
    return ValidationResult(is_valid=True, message="所有必需字段都存在")
```

#### 4.1.3 验证值范围

```python
@staticmethod
def validate_value_ranges(payload: dict) -> ValidationResult:
    """验证值范围"""
    errors = []
    
    # 验证 window_days
    if "window_days" in payload:
        if not (7 <= payload["window_days"] <= 365):
            errors.append("window_days 必须在 7-365 之间")
    
    # 验证 recent_days
    if "recent_days" in payload:
        if payload["recent_days"] < 1:
            errors.append("recent_days 必须大于等于 1")
    
    # 验证 daily_days
    if "daily_days" in payload:
        if not (1 <= payload["daily_days"] <= 7):
            errors.append("daily_days 必须在 1-7 之间")
    
    if errors:
        return ValidationResult(
            is_valid=False,
            message="值范围验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    
    return ValidationResult(is_valid=True, message="所有值都在有效范围内")
```

### 4.2 任务 1.2: CLI 参数组合验证实现

**文件**: `src/opportunity_detector/validator.py`  
**优先级**: 中  
**工作量**: 0.5 天  

#### 4.2.1 验证参数依赖关系

```python
@staticmethod
def validate_parameter_dependencies(args: argparse.Namespace) -> ValidationResult:
    """验证参数依赖关系"""
    errors = []
    
    # 如果设置了 --config，必须指定有效的配置文件
    if hasattr(args, 'config'):
        if not args.config:
            errors.append("配置文件路径不能为空")
    
    # 如果设置了 --out，必须指定有效的输出路径
    if hasattr(args, 'out'):
        if not args.out:
            errors.append("输出路径不能为空")
    
    if errors:
        return ValidationResult(
            is_valid=False,
            message="参数依赖关系验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    
    return ValidationResult(is_valid=True, message="参数依赖关系有效")
```

#### 4.2.2 验证参数互斥

```python
@staticmethod
def validate_parameter_exclusions(args: argparse.Namespace) -> ValidationResult:
    """验证参数互斥"""
    # 当前版本暂无互斥参数
    return ValidationResult(is_valid=True, message="无互斥参数冲突")
```

### 4.3 任务 1.3: 配置文件路径安全验证实现

**文件**: `src/opportunity_detector/validator.py`  
**优先级**: 低  
**工作量**: 0.5 天  

#### 4.3.1 验证路径安全性

```python
@staticmethod
def validate_config_path_safety(config_path: str, allowed_dirs: List[str]) -> ValidationResult:
    """验证配置文件路径安全性"""
    path = Path(config_path).resolve()
    
    # 检查路径是否在允许的目录范围内
    for allowed_dir in allowed_dirs:
        allowed_path = Path(allowed_dir).resolve()
        if path.is_relative_to(allowed_path):
            return ValidationResult(is_valid=True, message="配置文件路径安全")
    
    return ValidationResult(
        is_valid=False,
        message=f"配置文件路径不在允许的目录范围内: {config_path}"
    )
```

### 4.4 任务 1.4: 验证结果反馈优化实现

**文件**: `src/opportunity_detector/validator.py`  
**优先级**: 中  
**工作量**: 0.5 天  

#### 4.4.1 格式化验证错误信息

```python
def format_validation_errors(errors: List[str]) -> str:
    """格式化验证错误信息"""
    if not errors:
        return ""
    
    return "验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
```

#### 4.4.2 生成修复建议

```python
def generate_fix_suggestions(error_type: str) -> List[str]:
    """生成修复建议"""
    suggestions = {
        "yaml_syntax": [
            "检查 YAML 缩进是否正确",
            "检查是否有非法字符",
            "确保使用空格而不是制表符"
        ],
        "required_fields": [
            "检查配置文件格式是否正确",
            "确保包含所有必需字段"
        ],
        "value_ranges": [
            "检查数值是否在允许范围内",
            "参考文档中的配置说明"
        ],
        "path_security": [
            "确保配置文件在允许的目录范围内",
            "检查路径是否正确"
        ]
    }
    
    return suggestions.get(error_type, ["请检查配置文件格式"])
```

## 5. 测试计划

### 5.1 单元测试

**文件**: `tests/test_validator.py`

#### 5.1.1 ConfigFileValidator 测试

```python
class TestConfigFileValidator:
    def test_validate_yaml_syntax_valid(self) -> None:
        """测试有效 YAML 语法"""
        content = "key: value"
        result = ConfigFileValidator.validate_yaml_syntax(content)
        assert result.is_valid is True
    
    def test_validate_yaml_syntax_invalid(self) -> None:
        """测试无效 YAML 语法"""
        content = "key: value: invalid"
        result = ConfigFileValidator.validate_yaml_syntax(content)
        assert result.is_valid is False
    
    def test_validate_required_fields(self) -> None:
        """测试必需字段验证"""
        payload = {"key": "value"}
        result = ConfigFileValidator.validate_required_fields(payload)
        assert result.is_valid is False
    
    def test_validate_value_ranges(self) -> None:
        """测试值范围验证"""
        payload = {"window_days": 5}
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is False
```

#### 5.1.2 CLIValidator 测试

```python
class TestCLIParameterValidation:
    def test_validate_parameter_dependencies(self) -> None:
        """测试参数依赖关系"""
        args = argparse.Namespace(config=None)
        result = CLIValidator.validate_parameter_dependencies(args)
        assert result.is_valid is False
    
    def test_validate_parameter_exclusions(self) -> None:
        """测试参数互斥"""
        args = argparse.Namespace()
        result = CLIValidator.validate_parameter_exclusions(args)
        assert result.is_valid is True
```

#### 5.1.3 ConfigPathSecurity 测试

```python
class TestConfigPathSecurity:
    def test_validate_config_path_safety_valid(self) -> None:
        """测试有效路径"""
        result = CLIValidator.validate_config_path_safety(
            "/allowed/path/config.yml",
            ["/allowed/path"]
        )
        assert result.is_valid is True
    
    def test_validate_config_path_safety_invalid(self) -> None:
        """测试无效路径"""
        result = CLIValidator.validate_config_path_safety(
            "/not/allowed/config.yml",
            ["/allowed/path"]
        )
        assert result.is_valid is False
```

#### 5.1.4 ValidationFeedback 测试

```python
class TestValidationFeedback:
    def test_format_validation_errors(self) -> None:
        """测试错误信息格式化"""
        errors = ["error1", "error2"]
        formatted = format_validation_errors(errors)
        assert "error1" in formatted
        assert "error2" in formatted
    
    def test_generate_fix_suggestions(self) -> None:
        """测试修复建议生成"""
        suggestions = generate_fix_suggestions("yaml_syntax")
        assert len(suggestions) > 0
```

### 5.2 集成测试

**文件**: `tests/test_integration.py` (新建)

#### 5.2.1 完整的参数验证流程

```python
def test_complete_validation_flow() -> None:
    """测试完整的参数验证流程"""
    # 1. 验证配置文件路径
    # 2. 验证配置文件内容
    # 3. 验证 CLI 参数
    # 4. 验证参数组合
    # 5. 加载配置
    # 6. 验证配置
    pass
```

#### 5.2.2 配置文件加载和验证

```python
def test_config_loading_and_validation() -> None:
    """测试配置文件加载和验证"""
    # 1. 加载配置文件
    # 2. 验证 YAML 语法
    # 3. 验证必需字段
    # 4. 验证值范围
    # 5. 验证配置对象
    pass
```

#### 5.2.3 CLI 参数组合验证

```python
def test_cli_parameter_combination() -> None:
    """测试 CLI 参数组合"""
    # 1. 解析 CLI 参数
    # 2. 验证参数依赖关系
    # 3. 验证参数互斥
    # 4. 验证配置文件路径
    # 5. 验证输出路径
    pass
```

## 6. 文档更新

### 6.1 用户文档

**文件**: `docs/configuration/config-guide.md`

#### 6.1.1 配置验证说明

添加配置验证说明，包括：

- 验证规则
- 常见错误
- 解决方案

#### 6.1.2 配置示例

添加配置示例，包括：

- 基本配置
- 高级配置
- 错误配置示例

### 6.2 开发者文档

**文件**: `docs/developer-guide.md` (新建)

#### 6.2.1 验证模块说明

- 模块架构
- 验证流程
- 扩展指南

#### 6.2.2 验证规则文档

- 验证规则列表
- 验证优先级
- 验证错误代码

#### 6.2.3 测试指南

- 单元测试
- 集成测试
- 性能测试

## 7. 实现时间表

| 阶段 | 任务 | 优先级 | 工作量 | 预计完成时间 |
|------|------|--------|--------|--------------|
| 阶段一 | ConfigFileValidator 类实现 | 高 | 1 天 | 2024-02-24 |
| 阶段二 | CLI 参数组合验证实现 | 中 | 0.5 天 | 2024-02-25 |
| 阶段三 | 配置文件路径安全验证实现 | 低 | 0.5 天 | 2024-02-26 |
| 阶段四 | 验证结果反馈优化实现 | 中 | 0.5 天 | 2024-02-27 |
| 阶段五 | 测试编写 | 中 | 1 天 | 2024-02-28 |
| 阶段六 | 文档更新 | 低 | 0.5 天 | 2024-03-01 |

## 8. 验收标准

### 8.1 功能验收

- [ ] ConfigFileValidator 类实现
- [ ] CLI 参数组合验证实现
- [ ] 配置文件路径安全验证实现
- [ ] 验证结果反馈优化实现

### 8.2 测试验收

- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试通过
- [ ] 性能测试通过

### 8.3 文档验收

- [ ] 用户文档更新
- [ ] 开发者文档更新
- [ ] 测试文档更新

## 9. 风险评估

### 9.1 技术风险

- **风险**: YAML 语法验证可能不够全面
- **缓解**: 使用成熟的 YAML 库进行验证

### 9.2 时间风险

- **风险**: 实现时间可能超出预期
- **缓解**: 分阶段实现，优先实现高优先级功能

### 9.3 质量风险

- **风险**: 验证规则可能不够完善
- **缓解**: 充分测试，收集用户反馈

## 10. 总结

FUNC-018 参数验证需求的实现计划已经制定完成，包括：

1. **需求分析**: 明确了当前实现状态和未实现部分
2. **实现计划**: 制定了详细的实现步骤
3. **测试计划**: 制定了完整的测试方案
4. **文档计划**: 制定了文档更新计划
5. **时间表**: 制定了实现时间表
6. **验收标准**: 制定了验收标准
7. **风险评估**: 评估了潜在风险

下一步将按照实现计划逐步完成各阶段任务。

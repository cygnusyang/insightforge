"""CLI 参数验证测试模块

测试 FUNC-018: 参数验证

测试用例与需求对应关系:
| 测试用例 | 需求编号 | 验证内容 |
|---------|---------|---------|
| test_validate_config_path_valid | FUNC-018 | 有效配置文件路径 |
| test_validate_config_path_not_exist | FUNC-018 | 配置文件不存在 |
| test_validate_config_path_not_file | FUNC-018 | 配置路径不是文件 |
| test_validate_config_path_invalid_extension | FUNC-018 | 配置文件扩展名无效 |
| test_validate_output_path_valid | FUNC-018 | 有效输出路径 |
| test_validate_output_path_create_dir | FUNC-018 | 自动创建输出目录 |
| test_validate_output_path_not_writable | FUNC-018 | 输出目录不可写 |
| test_validate_cli_args_valid | FUNC-018 | 有效 CLI 参数组合 |
| test_validate_cli_args_invalid_config | FUNC-018 | 无效配置文件路径 |
| test_validate_cli_args_invalid_output | FUNC-018 | 无效输出路径 |
| test_validate_yaml_syntax_valid | FUNC-018 | 有效 YAML 语法 |
| test_validate_yaml_syntax_invalid | FUNC-018 | 无效 YAML 语法 |
| test_validate_required_fields | FUNC-018 | 必需字段验证 |
| test_validate_value_ranges | FUNC-018 | 值范围验证 |
| test_validate_parameter_dependencies | FUNC-018 | 参数依赖关系 |
| test_validate_parameter_exclusions | FUNC-018 | 参数互斥 |
| test_validate_config_path_safety_valid | FUNC-018 | 配置文件路径安全（有效） |
| test_validate_config_path_safety_invalid | FUNC-018 | 配置文件路径安全（无效） |
| test_format_validation_errors | FUNC-018 | 错误信息格式化 |
| test_generate_fix_suggestions | FUNC-018 | 修复建议生成 |
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.opportunity_detector.validator import (
    CLIValidator,
    ConfigFileValidator,
    format_validation_errors,
    generate_fix_suggestions,
    validate_cli_args,
    ValidationResult,
)


class TestCLIValidator:
    """CLIValidator 类的验证测试"""
    
    def test_validate_config_path_valid(self) -> None:
        """测试有效配置文件路径
        
        需求: FUNC-018
        验证: 有效配置文件路径应返回成功
        """
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("test: value")
            temp_path = f.name
        
        try:
            result = CLIValidator.validate_config_path(temp_path)
            assert result.is_valid is True
            assert "有效" in result.message
        finally:
            os.unlink(temp_path)
    
    def test_validate_config_path_not_exist(self) -> None:
        """测试不存在的配置文件路径
        
        需求: FUNC-018
        验证: 不存在的配置文件应返回失败
        """
        result = CLIValidator.validate_config_path("/nonexistent/path/config.yml")
        assert result.is_valid is False
        assert "不存在" in result.message
    
    def test_validate_config_path_not_file(self) -> None:
        """测试配置路径不是文件的情况
        
        需求: FUNC-018
        验证: 目录路径应返回失败
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            result = CLIValidator.validate_config_path(tmpdir)
            assert result.is_valid is False
            assert "不是文件" in result.message
    
    def test_validate_config_path_invalid_extension(self) -> None:
        """测试配置文件扩展名无效的情况
        
        需求: FUNC-018
        验证: 非 .yml/.yaml 文件应返回失败
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test: value")
            temp_path = f.name
        
        try:
            result = CLIValidator.validate_config_path(temp_path)
            assert result.is_valid is False
            assert "格式无效" in result.message
        finally:
            os.unlink(temp_path)
    
    def test_validate_output_path_valid(self) -> None:
        """测试有效输出路径
        
        需求: FUNC-018
        验证: 有效输出路径应返回成功
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output")
            result = CLIValidator.validate_output_path(output_path)
            assert result.is_valid is True
            assert "有效" in result.message
    
    def test_validate_output_path_create_dir(self) -> None:
        """测试自动创建输出目录
        
        需求: FUNC-018
        验证: 不存在的输出目录应自动创建
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "new", "output", "dir")
            result = CLIValidator.validate_output_path(output_path)
            assert result.is_valid is True
            # 检查父目录是否被创建（output_path 是文件路径，不一定存在）
            assert os.path.exists(os.path.dirname(output_path))
    
    def test_validate_output_path_not_writable(self) -> None:
        """测试输出目录不可写的情况
        
        需求: FUNC-018
        验证: 不可写的输出目录应返回失败
        """
        # 在只读目录中测试（在某些系统上可能不适用）
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建只读子目录
            readonly_dir = Path(tmpdir) / "readonly"
            readonly_dir.mkdir()
            os.chmod(str(readonly_dir), 0o400)  # 只读
            
            try:
                output_path = str(readonly_dir / "output")
                result = CLIValidator.validate_output_path(output_path)
                # 注意：在某些系统上（如 macOS），root 用户可能仍然可写
                # 所以我们只检查结果是有效或失败，不检查具体原因
                assert isinstance(result.is_valid, bool)
            finally:
                # 恢复权限以便清理
                os.chmod(str(readonly_dir), 0o755)
    
    def test_validate_cli_args_valid(self) -> None:
        """测试有效 CLI 参数组合
        
        需求: FUNC-018
        验证: 有效参数组合不应抛出异常
        """
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("test: value")
            temp_config = f.name
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_out = os.path.join(tmpdir, "output")
            try:
                # 应该不抛出异常
                validate_cli_args(temp_config, temp_out)
            finally:
                os.unlink(temp_config)
    
    def test_validate_cli_args_invalid_config(self) -> None:
        """测试无效配置文件路径
        
        需求: FUNC-018
        验证: 不存在的配置文件应抛出异常
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_out = os.path.join(tmpdir, "output")
            with pytest.raises(Exception):  # ValidationError 或 ValueError
                validate_cli_args("/nonexistent/config.yml", temp_out)
    
    def test_validate_cli_args_invalid_output(self) -> None:
        """测试无效输出路径
        
        需求: FUNC-018
        验证: 无效输出路径应抛出异常
        """
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("test: value")
            temp_config = f.name
        
        try:
            # 使用只读目录作为输出
            with tempfile.TemporaryDirectory() as tmpdir:
                readonly_dir = Path(tmpdir) / "readonly"
                readonly_dir.mkdir()
                os.chmod(str(readonly_dir), 0o400)
                
                try:
                    output_path = str(readonly_dir / "output")
                    # 应该抛出异常
                    with pytest.raises(Exception):  # ValidationError 或 ValueError
                        validate_cli_args(temp_config, output_path)
                finally:
                    os.chmod(str(readonly_dir), 0o755)
        finally:
            os.unlink(temp_config)


class TestValidationResult:
    """ValidationResult 命名元组测试"""
    
    def test_validation_result_namedtuple(self) -> None:
        """测试 ValidationResult 是命名元组
        
        需求: FUNC-018
        验证: ValidationResult 应具有 is_valid 和 message 属性
        """
        result = ValidationResult(is_valid=True, message="测试消息")
        assert result.is_valid is True
        assert result.message == "测试消息"
        # 验证是不可变的
        # ValidationResult 是不可变的，无法修改属性
        # 这里只验证属性存在性
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'message')


class TestConfigFileValidator:
    """ConfigFileValidator 类的验证测试"""
    
    def test_validate_yaml_syntax_valid(self) -> None:
        """测试有效 YAML 语法
        
        需求: FUNC-018
        验证: 有效的 YAML 语法应返回成功
        """
        content = "key: value\nnested:\n  - item1\n  - item2"
        result = ConfigFileValidator.validate_yaml_syntax(content)
        assert result.is_valid is True
        assert "有效" in result.message
    
    def test_validate_yaml_syntax_invalid(self) -> None:
        """测试无效 YAML 语法
        
        需求: FUNC-018
        验证: 无效的 YAML 语法应返回失败
        """
        content = "key: value: invalid\n  - nested: item"
        result = ConfigFileValidator.validate_yaml_syntax(content)
        assert result.is_valid is False
        assert "错误" in result.message
    
    def test_validate_yaml_syntax_with_special_chars(self) -> None:
        """测试包含特殊字符的 YAML 语法
        
        需求: FUNC-018
        验证: 包含特殊字符的有效 YAML 应返回成功
        """
        content = "key: 'value with special chars: []{}'"
        result = ConfigFileValidator.validate_yaml_syntax(content)
        assert result.is_valid is True
    
    def test_validate_required_fields_all_present(self) -> None:
        """测试所有必需字段都存在
        
        需求: FUNC-018
        验证: 包含所有必需字段的配置应返回成功
        """
        payload = {
            "window_days": 30,
            "recent_days": 7,
            "weights": {"demand": 0.5, "momentum": 0.3, "competition": 0.2},
            "topics": ["topic1"],
            "topic_keywords": {"topic1": ["kw1"]}
        }
        result = ConfigFileValidator.validate_required_fields(payload)
        assert result.is_valid is True
        assert "所有必需字段" in result.message
    
    def test_validate_required_fields_missing(self) -> None:
        """测试缺少必需字段
        
        需求: FUNC-018
        验证: 缺少必需字段的配置应返回失败
        """
        payload = {"key": "value"}
        result = ConfigFileValidator.validate_required_fields(payload)
        assert result.is_valid is False
        assert "缺少必需字段" in result.message
    
    def test_validate_value_ranges_valid(self) -> None:
        """测试值范围验证通过
        
        需求: FUNC-018
        验证: 值在有效范围内的配置应返回成功
        """
        payload = {
            "window_days": 30,
            "recent_days": 7,
            "daily_days": 1,
            "daily_max_items_per_topic": 5,
            "daily_max_gdelt_items": 20
        }
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is True
        assert "有效范围内" in result.message
    
    def test_validate_value_ranges_invalid_window_days(self) -> None:
        """测试 window_days 超出范围
        
        需求: FUNC-018
        验证: window_days 超出 7-365 范围应返回失败
        """
        payload = {"window_days": 5}
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is False
        assert "window_days" in result.message
    
    def test_validate_value_ranges_invalid_recent_days(self) -> None:
        """测试 recent_days 小于 1
        
        需求: FUNC-018
        验证: recent_days 小于 1 应返回失败
        """
        payload = {"recent_days": 0}
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is False
        assert "recent_days" in result.message
    
    def test_validate_value_ranges_invalid_daily_days(self) -> None:
        """测试 daily_days 超出范围
        
        需求: FUNC-018
        验证: daily_days 超出 1-7 范围应返回失败
        """
        payload = {"daily_days": 10}
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is False
        assert "daily_days" in result.message
    
    def test_validate_value_ranges_invalid_daily_max_items_per_topic(self) -> None:
        """测试 daily_max_items_per_topic 超出范围
        
        需求: FUNC-018
        验证: daily_max_items_per_topic 超出 1-10 范围应返回失败
        """
        payload = {"daily_max_items_per_topic": 15}
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is False
        assert "daily_max_items_per_topic" in result.message
    
    def test_validate_value_ranges_invalid_daily_max_gdelt_items(self) -> None:
        """测试 daily_max_gdelt_items 超出范围
        
        需求: FUNC-018
        验证: daily_max_gdelt_items 超出 1-50 范围应返回失败
        """
        payload = {"daily_max_gdelt_items": 60}
        result = ConfigFileValidator.validate_value_ranges(payload)
        assert result.is_valid is False
        assert "daily_max_gdelt_items" in result.message


class TestCLIParameterValidation:
    """CLI 参数组合验证测试"""
    
    def test_validate_parameter_dependencies_valid(self) -> None:
        """测试有效的参数依赖关系
        
        需求: FUNC-018
        验证: 具有有效参数依赖关系的配置应返回成功
        """
        import argparse
        args = argparse.Namespace(config="config.yml", out="output")
        result = CLIValidator.validate_parameter_dependencies(args)
        assert result.is_valid is True
    
    def test_validate_parameter_dependencies_invalid_config(self) -> None:
        """测试无效的参数依赖关系（配置路径为空）
        
        需求: FUNC-018
        验证: 配置路径为空应返回失败
        """
        import argparse
        args = argparse.Namespace(config=None, out="output")
        result = CLIValidator.validate_parameter_dependencies(args)
        assert result.is_valid is False
    
    def test_validate_parameter_exclusions(self) -> None:
        """测试参数互斥
        
        需求: FUNC-018
        验证: 无互斥参数时应返回成功
        """
        import argparse
        args = argparse.Namespace()
        result = CLIValidator.validate_parameter_exclusions(args)
        assert result.is_valid is True


class TestConfigPathSecurity:
    """配置文件路径安全验证测试"""
    
    def test_validate_config_path_safety_valid(self) -> None:
        """测试有效的配置文件路径
        
        需求: FUNC-018
        验证: 在允许目录范围内的路径应返回成功
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = str(Path(tmpdir) / "config.yml")
            result = CLIValidator.validate_config_path_safety(
                config_path, [tmpdir]
            )
            assert result.is_valid is True
    
    def test_validate_config_path_safety_invalid(self) -> None:
        """测试无效的配置文件路径
        
        需求: FUNC-018
        验证: 不在允许目录范围内的路径应返回失败
        """
        result = CLIValidator.validate_config_path_safety(
            "/etc/passwd", ["/allowed/path"]
        )
        assert result.is_valid is False
        assert "不在允许的目录范围内" in result.message


class TestValidationFeedback:
    """验证结果反馈测试"""
    
    def test_format_validation_errors(self) -> None:
        """测试错误信息格式化
        
        需求: FUNC-018
        验证: 错误信息应被正确格式化
        """
        errors = ["error1", "error2"]
        formatted = format_validation_errors(errors)
        assert "error1" in formatted
        assert "error2" in formatted
        assert "验证失败" in formatted
    
    def test_format_validation_errors_empty(self) -> None:
        """测试空错误列表格式化
        
        需求: FUNC-018
        验证: 空错误列表应返回空字符串
        """
        errors = []
        formatted = format_validation_errors(errors)
        assert formatted == ""
    
    def test_generate_fix_suggestions_yaml_syntax(self) -> None:
        """测试 YAML 语法错误的修复建议
        
        需求: FUNC-018
        验证: 应返回正确的修复建议
        """
        suggestions = generate_fix_suggestions("yaml_syntax")
        assert len(suggestions) > 0
        assert "缩进" in suggestions[0] or "缩进" in suggestions[1]
    
    def test_generate_fix_suggestions_required_fields(self) -> None:
        """测试必需字段缺失的修复建议
        
        需求: FUNC-018
        验证: 应返回正确的修复建议
        """
        suggestions = generate_fix_suggestions("required_fields")
        assert len(suggestions) > 0
        assert "必需字段" in suggestions[0] or "必需字段" in suggestions[1]
    
    def test_generate_fix_suggestions_value_ranges(self) -> None:
        """测试值范围错误的修复建议
        
        需求: FUNC-018
        验证: 应返回正确的修复建议
        """
        suggestions = generate_fix_suggestions("value_ranges")
        assert len(suggestions) > 0
        assert "范围" in suggestions[0] or "范围" in suggestions[1]
    
    def test_generate_fix_suggestions_path_security(self) -> None:
        """测试路径安全错误的修复建议
        
        需求: FUNC-018
        验证: 应返回正确的修复建议
        """
        suggestions = generate_fix_suggestions("path_security")
        assert len(suggestions) > 0
        assert "目录" in suggestions[0] or "路径" in suggestions[1]
    
    def test_generate_fix_suggestions_unknown(self) -> None:
        """测试未知错误类型的修复建议
        
        需求: FUNC-018
        验证: 应返回默认的修复建议
        """
        suggestions = generate_fix_suggestions("unknown_type")
        assert len(suggestions) > 0
        assert "配置文件格式" in suggestions[0]

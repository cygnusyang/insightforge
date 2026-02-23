"""参数验证模块

提供 CLI 参数和配置文件的验证功能。

验证需求:
- FUNC-018 (参数验证): 验证输入参数的有效性
- FUNC-014 (主题配置): 验证配置文件中的主题配置
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, NamedTuple

import yaml
from rich.console import Console

from .error import ValidationError

console = Console()


class ValidationResult(NamedTuple):
    """验证结果"""
    is_valid: bool
    message: str


class ConfigFileValidator:
    """配置文件内容验证器"""
    
    @staticmethod
    def validate_yaml_syntax(content: str) -> ValidationResult:
        """验证 YAML 语法
        
        Args:
            content: YAML 内容
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            yaml.safe_load(content)
            return ValidationResult(is_valid=True, message="YAML 语法有效")
        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                message=f"YAML 语法错误: {str(e)}"
            )
    
    @staticmethod
    def validate_required_fields(payload: dict) -> ValidationResult:
        """验证必需字段
        
        Args:
            payload: 配置字典
            
        Returns:
            ValidationResult: 验证结果
        """
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
    
    @staticmethod
    def validate_value_ranges(payload: dict) -> ValidationResult:
        """验证值范围
        
        Args:
            payload: 配置字典
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        
        # 验证 window_days
        if "window_days" in payload:
            value = payload["window_days"]
            if not isinstance(value, int) or not (7 <= value <= 365):
                errors.append("window_days 必须是整数且在 7-365 之间")
        
        # 验证 recent_days
        if "recent_days" in payload:
            value = payload["recent_days"]
            if not isinstance(value, int) or value < 1:
                errors.append("recent_days 必须是整数且大于等于 1")
        
        # 验证 daily_days
        if "daily_days" in payload:
            value = payload["daily_days"]
            if not isinstance(value, int) or not (1 <= value <= 7):
                errors.append("daily_days 必须是整数且在 1-7 之间")
        
        # 验证 daily_max_items_per_topic
        if "daily_max_items_per_topic" in payload:
            value = payload["daily_max_items_per_topic"]
            if not isinstance(value, int) or not (1 <= value <= 10):
                errors.append("daily_max_items_per_topic 必须是整数且在 1-10 之间")
        
        # 验证 daily_max_gdelt_items
        if "daily_max_gdelt_items" in payload:
            value = payload["daily_max_gdelt_items"]
            if not isinstance(value, int) or not (1 <= value <= 50):
                errors.append("daily_max_gdelt_items 必须是整数且在 1-50 之间")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                message="值范围验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            )
        
        return ValidationResult(is_valid=True, message="所有值都在有效范围内")


class CLIValidator:
    """CLI 参数验证器"""
    
    @staticmethod
    def validate_config_path(config_path: str) -> ValidationResult:
        """验证配置文件路径
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        path = Path(config_path)
        
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                message=f"配置文件不存在: {config_path}"
            )
        
        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                message=f"配置路径不是文件: {config_path}"
            )
        
        # 检查文件扩展名
        if path.suffix.lower() not in {'.yml', '.yaml'}:
            return ValidationResult(
                is_valid=False,
                message=f"配置文件格式无效: {config_path} (仅支持 .yml 或 .yaml)"
            )
        
        return ValidationResult(is_valid=True, message="配置文件路径有效")
    
    @staticmethod
    def validate_output_path(output_path: str) -> ValidationResult:
        """验证输出路径
        
        Args:
            output_path: 输出路径
            
        Returns:
            ValidationResult: 验证结果
        """
        path = Path(output_path)
        
        # 检查父目录是否存在
        parent = path.parent
        if not parent.exists():
            # 尝试创建父目录
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                return ValidationResult(
                    is_valid=False,
                    message=f"无法创建输出目录: {output_path} ({e})"
                )
        
        # 检查是否可写
        if not os.access(str(parent), os.W_OK):
            return ValidationResult(
                is_valid=False,
                message=f"输出目录不可写: {output_path}"
            )
        
        return ValidationResult(is_valid=True, message="输出路径有效")
    
    @staticmethod
    def validate_config_and_output(
        config_path: str,
        output_path: str
    ) -> ValidationResult:
        """验证配置文件和输出路径的组合
        
        Args:
            config_path: 配置文件路径
            output_path: 输出路径
            
        Returns:
            ValidationResult: 验证结果
        """
        # 先验证配置文件路径
        config_result = CLIValidator.validate_config_path(config_path)
        if not config_result.is_valid:
            return config_result
        
        # 再验证输出路径
        output_result = CLIValidator.validate_output_path(output_path)
        if not output_result.is_valid:
            return output_result
        
        return ValidationResult(
            is_valid=True,
            message=f"配置文件和输出路径组合有效: config={config_path}, output={output_path}"
        )
    
    @staticmethod
    def validate_parameter_dependencies(args) -> ValidationResult:
        """验证参数依赖关系
        
        Args:
            args: argparse.Namespace 对象
            
        Returns:
            ValidationResult: 验证结果
        """
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
    
    @staticmethod
    def validate_parameter_exclusions(args) -> ValidationResult:
        """验证参数互斥
        
        Args:
            args: argparse.Namespace 对象
            
        Returns:
            ValidationResult: 验证结果
        """
        # 当前版本暂无互斥参数
        return ValidationResult(is_valid=True, message="无互斥参数冲突")
    
    @staticmethod
    def validate_config_path_safety(config_path: str, allowed_dirs: List[str]) -> ValidationResult:
        """验证配置文件路径安全性
        
        Args:
            config_path: 配置文件路径
            allowed_dirs: 允许的目录列表
            
        Returns:
            ValidationResult: 验证结果
        """
        path = Path(config_path).resolve()
        
        # 检查路径是否在允许的目录范围内
        for allowed_dir in allowed_dirs:
            allowed_path = Path(allowed_dir).resolve()
            try:
                if path.is_relative_to(allowed_path):
                    return ValidationResult(is_valid=True, message="配置文件路径安全")
            except ValueError:
                # 路径不在同一文件系统上
                continue
        
        return ValidationResult(
            is_valid=False,
            message=f"配置文件路径不在允许的目录范围内: {config_path}"
        )


def validate_cli_args(config: str, out: str) -> None:
    """验证 CLI 参数并处理错误
    
    Args:
        config: 配置文件路径
        out: 输出路径
        
    Raises:
        ValidationError: 当验证失败时抛出
    """
    errors = []
    
    # 验证配置文件路径
    config_result = CLIValidator.validate_config_path(config)
    if not config_result.is_valid:
        errors.append(config_result.message)
    
    # 验证输出路径
    out_result = CLIValidator.validate_output_path(out)
    if not out_result.is_valid:
        errors.append(out_result.message)
    
    if errors:
        error_msg = "参数验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValidationError(message=error_msg)


def print_validation_result(result: ValidationResult) -> None:
    """打印验证结果
    
    Args:
        result: 验证结果
    """
    if result.is_valid:
        console.print(f"[green]✓[/green] {result.message}")
    else:
        console.print(f"[red]✗[/red] {result.message}")


def format_validation_errors(errors: List[str]) -> str:
    """格式化验证错误信息
    
    Args:
        errors: 错误信息列表
        
    Returns:
        格式化后的错误信息
    """
    if not errors:
        return ""
    
    return "验证失败:\n" + "\n".join(f"  - {e}" for e in errors)


def generate_fix_suggestions(error_type: str) -> List[str]:
    """生成修复建议
    
    Args:
        error_type: 错误类型
        
    Returns:
        修复建议列表
    """
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

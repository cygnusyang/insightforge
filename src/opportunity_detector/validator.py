"""参数验证模块

提供 CLI 参数和配置文件的验证功能。

验证需求:
- FUNC-018 (参数验证): 验证输入参数的有效性
- FUNC-014 (主题配置): 验证配置文件中的主题配置
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple

from rich.console import Console

from .error import ValidationError

console = Console()


class ValidationResult(NamedTuple):
    """验证结果"""
    is_valid: bool
    message: str


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

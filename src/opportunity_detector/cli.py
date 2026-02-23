from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import load_config
from .pipeline import run_pipeline
from .validator import CLIValidator, validate_cli_args

# 默认配置路径
DEFAULT_CONFIG_PATH = "config/topics.yml"
DEFAULT_OUTPUT_PATH = "outputs/latest"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="行业/产品机会探测器（多信号融合）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
默认配置: {DEFAULT_CONFIG_PATH}
默认输出: {DEFAULT_OUTPUT_PATH}

示例:
  python -m src.opportunity_detector.cli              # 使用默认配置
  python -m src.opportunity_detector.cli --config custom.yml
  python -m src.opportunity_detector.cli --out custom_output
  python -m src.opportunity_detector.cli --config custom.yml --out custom_output
""",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"配置文件路径，默认 {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUTPUT_PATH,
        help=f"输出目录，默认 {DEFAULT_OUTPUT_PATH}",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="启用监控模式",
    )
    parser.add_argument(
        "--alert-test",
        action="store_true",
        help="测试告警通知",
    )
    parser.add_argument(
        "--alert-receivers",
        nargs="+",
        choices=["email", "webhook"],
        help="告警接收者类型 (email, webhook)",
    )
    return parser


def _test_alert(config) -> None:
    """测试告警通知"""
    from .alert import AlertConfig, AlertManager, AlertLevel
    
    console = Console()
    
    # 创建告警管理器
    alert_config = config.alert_config if hasattr(config, "alert_config") else AlertConfig()
    manager = AlertManager(alert_config)
    
    # 创建测试告警
    alert = manager.create_alert(
        level=AlertLevel.WARNING,
        message="这是一条测试告警消息",
        rule="test_rule",
    )
    
    if alert:
        console.print(f"[green]✓ 测试告警创建成功: {alert.id}[/green]")
        console.print(f"[green]✓ 告警消息: {alert.message}[/green]")
    else:
        console.print("[yellow]告警功能已禁用[/yellow]")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # 验证 CLI 参数
    try:
        validate_cli_args(args.config, args.out)
    except ValueError as e:
        console = Console()
        console.print(f"[red]参数验证失败:[/red] {e}")
        return

    config = load_config(args.config)
    
    # 测试告警
    if args.alert_test:
        _test_alert(config)
        return
    
    # 运行管道
    _, scored = run_pipeline(config, Path(args.out), enable_monitor=args.monitor)

    console = Console()
    table = Table(title="机会排名（按分数降序）")
    table.add_column("Rank", justify="right")
    table.add_column("Topic")
    table.add_column("Score", justify="right")

    for index, item in enumerate(scored, start=1):
        table.add_row(str(index), item.topic, f"{item.opportunity_score:.4f}")

    console.print(table)
    console.print(f"\n输出已生成到: {args.out}")


if __name__ == "__main__":
    main()

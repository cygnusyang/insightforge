from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import load_config
from .pipeline import run_pipeline
from .validator import CLIValidator, validate_cli_args


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="行业/产品机会探测器（多信号融合）")
    parser.add_argument(
        "--config",
        required=True,
        help="配置文件路径，如 config/topics.yml",
    )
    parser.add_argument(
        "--out",
        default="outputs/latest",
        help="输出目录，默认 outputs/latest",
    )
    return parser


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
    _, scored = run_pipeline(config, Path(args.out))

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

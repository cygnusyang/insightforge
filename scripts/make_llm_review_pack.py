from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CmdResult:
    cmd: list[str]
    exit_code: int
    stdout: str
    stderr: str


def _run(cmd: list[str], cwd: Path) -> CmdResult:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    return CmdResult(
        cmd=cmd,
        exit_code=proc.returncode,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def _read_text(path: Path, max_chars: int) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    if max_chars <= 0:
        return content
    return content[:max_chars]


def _section(title: str) -> str:
    return f"\n## {title}\n"


def _format_cmd_result(result: CmdResult, max_chars: int) -> str:
    body = result.stdout or result.stderr or ""
    if max_chars > 0:
        body = body[:max_chars]
    return (
        "```text\n"
        f"$ {' '.join(result.cmd)}\n"
        f"exit_code={result.exit_code}\n"
        f"{body}\n"
        "```\n"
    )


def build_review_pack(
    repo_root: Path,
    opportunity_out: Path | None,
    since_days: int,
    max_cmd_chars: int,
    max_file_chars: int,
) -> str:
    now = datetime.now()
    lines: list[str] = []
    lines.append("# InsightForge 定时检查包（给大模型的上下文）")
    lines.append("")
    lines.append(f"- generated_at: {now.isoformat(timespec='seconds')}")
    lines.append(f"- repo_root: {repo_root}")
    lines.append(f"- since_days: {since_days}")
    if opportunity_out is not None:
        lines.append(f"- opportunity_out: {opportunity_out}")

    lines.append(_section("目标（你可以直接让大模型按此输出）").rstrip())
    lines.append(
        "\n".join(
            [
                "请基于以下上下文输出：",
                "1) 工程层面的可优化点（按 ROI 排序，给出具体改动建议）",
                "2) 产品/机会层面的新想法（结合本次探测报告，给出可验证的下一步）",
                "3) 风险与盲区（数据源、偏差、限流、误报等）",
                "4) 未来 1~2 周的迭代清单（可拆分成任务）",
            ]
        )
    )

    lines.append(_section("最近产出（机会探测）").rstrip())
    if opportunity_out is None:
        lines.append("未提供 `--opportunity-out`，跳过。")
    else:
        daily_report = opportunity_out / "daily_report.md"
        daily_md = opportunity_out / "daily.md"
        report_md = opportunity_out / "report.md"
        insights_md = opportunity_out / "insights.md"
        lines.append(f"- daily_report.md: {daily_report}")
        lines.append(_read_text(daily_report, max_file_chars) or "(missing)")
        lines.append("")
        lines.append(f"- daily.md: {daily_md}")
        lines.append(_read_text(daily_md, max_file_chars) or "(missing)")
        lines.append("")
        lines.append(f"- report.md: {report_md}")
        lines.append(_read_text(report_md, max_file_chars) or "(missing)")
        lines.append("")
        lines.append(f"- insights.md: {insights_md}")
        lines.append(_read_text(insights_md, max_file_chars) or "(missing)")

    lines.append(_section("代码与变更（最近提交）").rstrip())
    if shutil.which("git"):
        result = _run(
            ["git", "log", f"--since={since_days}.days", "--oneline", "--decorate"],
            cwd=repo_root,
        )
        lines.append(_format_cmd_result(result, max_cmd_chars))
    else:
        lines.append("未找到 `git`。")

    lines.append(_section("待办线索（TODO/FIXME）").rstrip())
    if shutil.which("rg"):
        result = _run(["rg", "-n", r"(TODO|FIXME)"], cwd=repo_root)
        lines.append(_format_cmd_result(result, max_cmd_chars))
    else:
        lines.append("未找到 `rg`（ripgrep）。")

    lines.append(_section("测试（可选）").rstrip())
    lines.append(
        "如需让定时任务也跑测试：设置 `RUN_TESTS=1`，或在 CI/Actions 里跑 `pytest -q`。"
    )
    if os.getenv("RUN_TESTS", "").strip() == "1":
        if shutil.which("pytest"):
            result = _run(["pytest", "-q"], cwd=repo_root)
            lines.append(_format_cmd_result(result, max_cmd_chars))
        else:
            lines.append("未找到 `pytest`。")

    lines.append(_section("环境（用于排查）").rstrip())
    lines.append(f"- python: {shutil.which('python') or ''}")
    lines.append(f"- python3: {shutil.which('python3') or ''}")
    lines.append(f"- rg: {shutil.which('rg') or ''}")
    lines.append(f"- git: {shutil.which('git') or ''}")

    lines.append("")
    return "\n".join(lines).strip() + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="为大模型生成 InsightForge 工程的定时检查上下文包")
    parser.add_argument(
        "--out",
        default="outputs/review/latest.md",
        help="输出路径（默认 outputs/review/latest.md）",
    )
    parser.add_argument(
        "--opportunity-out",
        default="outputs/latest",
        help="机会探测输出目录（默认 outputs/latest）",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=7,
        help="最近提交窗口（天），默认 7",
    )
    parser.add_argument(
        "--max-cmd-chars",
        type=int,
        default=8000,
        help="每段命令输出的最大字符数（默认 8000）",
    )
    parser.add_argument(
        "--max-file-chars",
        type=int,
        default=12000,
        help="每个 Markdown 文件片段的最大字符数（默认 12000）",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    out_path = Path(args.out)
    opportunity_out = Path(args.opportunity_out) if args.opportunity_out else None
    pack = build_review_pack(
        repo_root=repo_root,
        opportunity_out=opportunity_out,
        since_days=args.since_days,
        max_cmd_chars=args.max_cmd_chars,
        max_file_chars=args.max_file_chars,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(pack, encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()


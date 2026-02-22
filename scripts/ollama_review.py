from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import httpx


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="调用 Ollama，为 InsightForge 生成工程/机会优化建议")
    parser.add_argument("--base-url", required=True, help="Ollama 服务地址，如 http://127.0.0.1:11434")
    parser.add_argument("--model", required=True, help="模型名，如 llama3.2:latest / qwen2.5:14b")
    parser.add_argument("--in", dest="in_path", required=True, help="输入 review pack 路径（Markdown）")
    parser.add_argument("--out", dest="out_path", required=True, help="输出建议路径（Markdown）")
    parser.add_argument("--timeout", type=float, default=900.0, help="HTTP 超时（秒），默认 900")
    parser.add_argument("--temperature", type=float, default=0.2, help="温度，默认 0.2")
    return parser


def _normalize_base_url(base_url: str) -> str:
    base_url = base_url.strip().rstrip("/")
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "http://" + base_url
    return base_url


def _iter_ollama_json_lines(resp: httpx.Response) -> list[dict]:
    out: list[dict] = []
    for line in resp.iter_lines():
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def call_ollama_generate(
    *,
    base_url: str,
    model: str,
    prompt_md: str,
    timeout: float,
    temperature: float,
) -> str:
    base_url = _normalize_base_url(base_url)
    url = f"{base_url}/api/generate"

    system = (
        "你是一个资深软件工程师 + 产品策略顾问。"
        "你会基于给定的 InsightForge 上下文，输出可执行的工程优化与产品机会建议。"
        "请用中文输出，结构清晰，尽量给出具体改动点/命令/文件路径。"
    )
    prompt = f"{system}\n\n{prompt_md}".strip()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": temperature},
    }

    chunks: list[str] = []
    last_error: Exception | None = None
    with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
        try:
            with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                for data in _iter_ollama_json_lines(resp):
                    chunk = data.get("response")
                    if isinstance(chunk, str) and chunk:
                        chunks.append(chunk)
                    if data.get("done") is True:
                        break
        except Exception as exc:  # noqa: BLE001 - want a clear error message in output
            last_error = exc

    out = "".join(chunks).strip()
    if out:
        return out
    if last_error is not None:
        raise last_error
    raise RuntimeError("empty ollama response (generate)")


def call_ollama_chat(
    *,
    base_url: str,
    model: str,
    prompt_md: str,
    timeout: float,
    temperature: float,
) -> str:
    base_url = _normalize_base_url(base_url)
    url = f"{base_url}/api/chat"

    system = (
        "你是一个资深软件工程师 + 产品策略顾问。"
        "你会基于给定的 InsightForge 上下文，输出可执行的工程优化与产品机会建议。"
        "请用中文输出，结构清晰，尽量给出具体改动点/命令/文件路径。"
    )

    payload = {
        "model": model,
        "stream": True,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt_md},
        ],
    }

    chunks: list[str] = []
    with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for data in _iter_ollama_json_lines(resp):
                message = data.get("message") or {}
                content = message.get("content")
                if isinstance(content, str) and content:
                    chunks.append(content)
                if data.get("done") is True:
                    break

    out = "".join(chunks).strip()
    if out:
        return out
    raise RuntimeError("empty ollama response (chat)")


def call_ollama_best_effort(
    *,
    base_url: str,
    model: str,
    prompt_md: str,
    timeout: float,
    temperature: float,
) -> str:
    try:
        return call_ollama_chat(
            base_url=base_url,
            model=model,
            prompt_md=prompt_md,
            timeout=timeout,
            temperature=temperature,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in {502, 503, 504}:
            return call_ollama_generate(
                base_url=base_url,
                model=model,
                prompt_md=prompt_md,
                timeout=timeout,
                temperature=temperature,
            )
        raise
    except httpx.RequestError:
        return call_ollama_generate(
            base_url=base_url,
            model=model,
            prompt_md=prompt_md,
            timeout=timeout,
            temperature=temperature,
        )


def main() -> None:
    args = _build_parser().parse_args()
    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    prompt_md = in_path.read_text(encoding="utf-8")
    advice = call_ollama_best_effort(
        base_url=args.base_url,
        model=args.model,
        prompt_md=prompt_md,
        timeout=args.timeout,
        temperature=args.temperature,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# InsightForge LLM 建议（Ollama）",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- base_url: {args.base_url}",
        f"- model: {args.model}",
        f"- source: {in_path}",
        "",
        "---",
        "",
    ]
    out_path.write_text("\n".join(header) + advice + "\n", encoding="utf-8")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()

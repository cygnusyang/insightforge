from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    model: str
    timeout_s: float = 900.0
    temperature: float = 0.2


def load_ollama_from_env() -> LlmConfig | None:
    base_url = (os.getenv("OLLAMA_BASE_URL", "") or "").strip()
    model = (os.getenv("OLLAMA_MODEL", "") or "").strip()
    if not base_url or not model:
        return None
    timeout_raw = (os.getenv("OLLAMA_TIMEOUT", "") or "").strip()
    timeout_s = 900.0
    if timeout_raw:
        try:
            timeout_s = float(timeout_raw)
        except ValueError:
            timeout_s = 900.0
    return LlmConfig(base_url=base_url, model=model, timeout_s=timeout_s)


def _normalize_base_url(base_url: str) -> str:
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "http://" + base_url
    return base_url


def _iter_json_lines(resp: httpx.Response) -> list[dict]:
    out: list[dict] = []
    for line in resp.iter_lines():
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def ollama_generate(*, cfg: LlmConfig, prompt: str) -> str:
    base_url = _normalize_base_url(cfg.base_url)
    url = f"{base_url}/api/generate"
    payload = {
        "model": cfg.model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": cfg.temperature},
    }

    chunks: list[str] = []
    with httpx.Client(timeout=httpx.Timeout(cfg.timeout_s)) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for data in _iter_json_lines(resp):
                part = data.get("response")
                if isinstance(part, str) and part:
                    chunks.append(part)
                if data.get("done") is True:
                    break
    return "".join(chunks).strip()


def ollama_chat(*, cfg: LlmConfig, system: str, user: str) -> str:
    base_url = _normalize_base_url(cfg.base_url)
    url = f"{base_url}/api/chat"
    payload = {
        "model": cfg.model,
        "stream": True,
        "options": {"temperature": cfg.temperature},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    chunks: list[str] = []
    with httpx.Client(timeout=httpx.Timeout(cfg.timeout_s)) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for data in _iter_json_lines(resp):
                message = data.get("message") or {}
                part = message.get("content")
                if isinstance(part, str) and part:
                    chunks.append(part)
                if data.get("done") is True:
                    break
    return "".join(chunks).strip()


def ollama_best_effort(*, cfg: LlmConfig, system: str, user: str) -> str:
    try:
        return ollama_chat(cfg=cfg, system=system, user=user)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in {502, 503, 504}:
            prompt = f"{system}\n\n{user}".strip()
            return ollama_generate(cfg=cfg, prompt=prompt)
        raise
    except httpx.RequestError:
        prompt = f"{system}\n\n{user}".strip()
        return ollama_generate(cfg=cfg, prompt=prompt)


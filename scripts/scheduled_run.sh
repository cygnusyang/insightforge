#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

LOCK_DIR="${LOCK_DIR:-$ROOT/outputs/.scheduled_run.lock}"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[hunter] $(date -Iseconds) another run in progress; skip"
  exit 0
fi
cleanup() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
trap cleanup EXIT

CONFIG_PATH="${CONFIG_PATH:-$ROOT/config/topics.yml}"
OUT_DIR="${OUT_DIR:-$ROOT/outputs/latest}"
REVIEW_OUT="${REVIEW_OUT:-$ROOT/outputs/review/latest.md}"
LLM_OUT="${LLM_OUT:-$ROOT/outputs/review/llm_advice.md}"
SINCE_DAYS="${SINCE_DAYS:-7}"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

cd "$ROOT"

echo "[hunter] $(date -Iseconds) run pipeline"
"$PYTHON_BIN" run.py --config "$CONFIG_PATH" --out "$OUT_DIR"

echo "[hunter] $(date -Iseconds) build LLM review pack"
"$PYTHON_BIN" scripts/make_llm_review_pack.py \
  --out "$REVIEW_OUT" \
  --since-days "$SINCE_DAYS" \
  --opportunity-out "$OUT_DIR"

if [[ -n "${OLLAMA_BASE_URL:-}" && -n "${OLLAMA_MODEL:-}" ]]; then
  echo "[hunter] $(date -Iseconds) call ollama for review"
  if ! "$PYTHON_BIN" scripts/ollama_review.py \
    --base-url "$OLLAMA_BASE_URL" \
    --model "$OLLAMA_MODEL" \
    --in "$REVIEW_OUT" \
    --out "$LLM_OUT" \
    --timeout "${OLLAMA_TIMEOUT:-900}"; then
    echo "[hunter] $(date -Iseconds) ollama failed; keep other outputs"
  fi
fi

echo "[hunter] $(date -Iseconds) done"

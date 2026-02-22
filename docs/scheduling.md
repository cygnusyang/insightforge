# 定时任务：周期性运行 Hunter，并生成“大模型检查包”

下面给出 3 种常见方式（你选一种即可）：本机 `cron` / macOS `launchd` / CI（GitHub Actions）。

> 目标：隔一段时间自动运行 `python run.py`，生成 `outputs/latest/*` 报告；并额外生成一个 `outputs/review/latest.md`，作为“喂给大模型”的上下文包（包含最近产出、最近提交、TODO 线索等）。

## 方式 A：最简单（手动先验证一次）

```bash
bash scripts/scheduled_run.sh
```

常用环境变量（可选）：
- `CONFIG_PATH`：默认 `config/topics.yml`
- `OUT_DIR`：默认 `outputs/latest`
- `REVIEW_OUT`：默认 `outputs/review/latest.md`
- `OLLAMA_BASE_URL`：如 `http://127.0.0.1:11434`（设置后会自动调用 Ollama）
- `OLLAMA_MODEL`：如 `qwen2.5:14b` / `llama3.2:latest`
- `LLM_OUT`：默认 `outputs/review/llm_advice.md`
- `OLLAMA_TIMEOUT`：默认 `900`（秒）。大模型首 token 很慢时建议调大
- `SINCE_DAYS`：默认 `7`
- `RUN_TESTS=1`：让 `make_llm_review_pack.py` 额外跑 `pytest -q`

## 方式 B：Linux/macOS cron（每 2 小时跑一次）

1) 编辑 crontab：

```bash
crontab -e
```

2) 添加一行（注意把路径改成你本机实际路径）：

```cron
0 */2 * * * cd /ABS/PATH/TO/hunter && bash scripts/scheduled_run.sh >> outputs/logs/cron.log 2>&1
```

如果你要 **每 1 分钟跑一次**（注意：一次运行可能超过 1 分钟，脚本内置了锁，会在上一次未结束时自动跳过本次）：

```cron
* * * * * cd /ABS/PATH/TO/hunter && bash scripts/scheduled_run.sh >> outputs/logs/cron.log 2>&1
```

建议你先创建日志目录：

```bash
mkdir -p outputs/logs
```

## 方式 C：macOS launchd（更稳定）

1) 复制模板并改路径：

- 模板：`config/schedule/com.hunter.scheduled.plist.example`
- 目标：`~/Library/LaunchAgents/com.hunter.scheduled.plist`

2) 加载并启动：

```bash
launchctl load -w ~/Library/LaunchAgents/com.hunter.scheduled.plist
launchctl start com.hunter.scheduled
```

3) 停止/卸载：

```bash
launchctl unload -w ~/Library/LaunchAgents/com.hunter.scheduled.plist
```

## 方式 D：CI（GitHub Actions）建议

适合你希望“每天自动跑一次并产出 artifact”，且不依赖本机常开。

要点：
- 使用 `schedule:` 触发
- 把 `.env` 里的敏感信息改成 GitHub Secrets（如 `GITHUB_TOKEN`）
- 用 `actions/upload-artifact` 上传 `outputs/latest` 供下载

如果你要我直接给你生成 `.github/workflows/scheduled.yml`，告诉我：触发频率、是否需要把日报发到 Slack/飞书/邮箱、以及你要用哪家大模型（OpenAI/Claude/本地）。

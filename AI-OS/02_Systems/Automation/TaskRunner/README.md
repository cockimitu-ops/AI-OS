# Task Runner

Purpose: The live automation loop that lets Felix hand AI-OS a task from anywhere (shell or Telegram) and get it executed headlessly on the server. Moved here from the repo root on 2026-08-26 so the vault's own README reflects what's actually running, instead of the automation living as loose scripts beside it.
Last Updated: 2026-08-26
Status: Active — three systemd services running continuously on the server
Related Documents: [[02_Systems/Automation/README|Automation]], [[Future_Integration]]

---

## What runs here

| File | Role |
|---|---|
| `aios_runner.py` | The worker. Polls `tasks/inbox/` in a loop, runs each task through Open Interpreter (headless, `auto_run=True`), writes the result to `tasks/logs/`, moves the task to `tasks/completed/`. Primary model `groq/openai/gpt-oss-120b`, falls back to `gemini/gemini-3.6-flash` on rate limit/failure. |
| `dispatch_task.py` | CLI entry point. Drops a task file into `tasks/inbox/`, then polls for the matching log (up to 180s) and prints the result. `--no-wait` to fire and return immediately. |
| `telegram_bridge.py` | Same idea, over Telegram — only replies to the one allowed user ID, edits its own status message once the worker's log appears. |
| `scripts/cloud_backup.py` | Tars the whole repo (`/home/nost/AI-OS`), uploads to Google Drive via `rclone`, prunes local archives older than 7 days. |
| `scripts/send_telegram_notification.py` | One-off outbound Telegram message, reusing the same bot token — for things other than task results (e.g. backup failures). |

`tasks/` (inbox/completed/logs) and `backups/` are runtime output, not source — gitignored except for structure.

## How it's wired to the server

Three systemd services, all under `/etc/systemd/system/`, `WorkingDirectory` and `ExecStart` pointing into this folder:

- `aios-worker.service` — runs `aios_runner.py`, `Restart=always`
- `aios-telegram.service` — runs `telegram_bridge.py`, `Restart=always`, starts `After=aios-worker.service`
- `aios-backup.service` (`Type=oneshot`) + `aios-backup.timer` — runs `scripts/cloud_backup.py` daily at 03:00

All three load secrets via `EnvironmentFile=/home/nost/AI-OS/.env` — the `.env` file itself stays at the repo root (gitignored), not inside the vault, since it's a secret rather than vault content.

`AIOS_WORKSPACE` in `.env` points at this folder (`/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner`) — that's what `aios_runner.py`, `dispatch_task.py`, and `telegram_bridge.py` resolve `tasks/inbox|completed|logs` against. `cloud_backup.py` doesn't use that variable — it hardcodes the repo root as its backup source independently, since it needs to tar the whole tree, not just this folder.

## Why backups/ excludes itself

`cloud_backup.py` tars the entire repo including this folder. Without an explicit exclude, every new archive would embed all previous archives inside itself, growing without bound. `EXCLUDE_RELATIVE_PATHS` in the script excludes its own `backups/` and `tasks/logs/` for exactly that reason — don't remove those excludes without addressing that.

## Verified working (2026-08-26)

Moved from repo root into this vault path; systemd units, `.env`, and both scripts' hardcoded fallback paths updated to match. Confirmed via `sudo systemctl restart` on both continuous services plus a live `dispatch_task.py` round trip (task landed in the new inbox, worker picked it up, log + completed file appeared in the new location). The round trip's *LLM* result errored — Groq per-minute limit plus Gemini's daily free-tier quota both exhausted at the time — unrelated to the move itself, worth re-testing once quota resets.

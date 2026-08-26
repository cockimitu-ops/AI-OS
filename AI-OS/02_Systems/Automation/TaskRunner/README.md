# Task Runner

Purpose: The live automation loop that lets Felix hand AI-OS a task from anywhere (shell or Telegram) and get it executed headlessly on the server. Moved here from the repo root on 2026-08-26 so the vault's own README reflects what's actually running, instead of the automation living as loose scripts beside it.
Last Updated: 2026-08-26
Status: Active — three systemd services running continuously on the server
Related Documents: [[02_Systems/Automation/README|Automation]], [[Future_Integration]]

---

## What runs here

| File | Role |
|---|---|
| `aios_runner.py` | The worker. Polls `tasks/inbox/` in a loop, runs each task through Open Interpreter (headless, `auto_run=True`), writes the result to `tasks/logs/`, moves the task to `tasks/completed/`. Tries a chain of free models in order (`MODEL_CHAIN`) before giving up — see below. A Claude tier (`claude -p --model sonnet`) exists but is **disabled** — see further below. |
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

## Free model rotation (expanded 2026-08-26)

Felix has no budget for a paid API, so the whole chain stays free by construction. `MODEL_CHAIN` in `aios_runner.py` tries, in order: `groq/openai/gpt-oss-120b` → same model again after a 20s cooldown (Groq's per-minute bucket clears fast) → `groq/openai/gpt-oss-20b` → `gemini/gemini-3.6-flash` → `gemini/gemini-3.5-flash-lite`. The two "second sibling" models (`gpt-oss-20b`, `flash-lite`) cost nothing new — same `GROQ_API_KEY`/`GEMINI_API_KEY` already in `.env`, no new signup — and each is metered as a separate quota bucket from its sibling, so they're genuinely additional headroom, not the same limit under a different name.

**One real dead end during this, worth remembering:** the obvious pick, `gemini/gemini-flash-lite-latest`, works fine as a raw API call but 400s specifically inside Open Interpreter's tool-calling flow (`Function call is missing a thought_signature` — a real constraint newer "thinking" Gemini models impose on function-call parts, not a config mistake). Always verify a new model through the *actual* code path (`_attempt()`), not just a raw curl — that's what caught this before it shipped silently broken. `gemini-3.5-flash-lite` was checked the same way and works cleanly.

## Why backups/ excludes itself

`cloud_backup.py` tars the entire repo including this folder. Without an explicit exclude, every new archive would embed all previous archives inside itself, growing without bound. `EXCLUDE_RELATIVE_PATHS` in the script excludes its own `backups/` and `tasks/logs/` for exactly that reason — don't remove those excludes without addressing that.

## Verified working (2026-08-26)

Moved from repo root into this vault path; systemd units, `.env`, and both scripts' hardcoded fallback paths updated to match. Confirmed via `sudo systemctl restart` on both continuous services plus a live `dispatch_task.py` round trip (task landed in the new inbox, worker picked it up, log + completed file appeared in the new location). The round trip's *LLM* result errored — Groq per-minute limit plus Gemini's daily free-tier quota both exhausted at the time — unrelated to the move itself, worth re-testing once quota resets.

**Also fixed the same day:** the move had left `aios-worker.service`'s `WorkingDirectory` pointing into this nested folder instead of the repo root — harmless for `aios_runner.py` itself (it resolves its own paths via `AIOS_WORKSPACE`), but it silently changed the cwd that Open Interpreter's shell commands execute *tasks'* file operations from. Reverted to `/home/nost/AI-OS`.

## Claude escalation tier — built 2026-08-26, disabled the same day

Groq's per-minute bucket and Gemini's free-tier daily cap (20 requests/day on `gemini-3.6-flash`) both failed live during the move's own verification test — not hypothetical, it just happened. Built `_attempt_claude()` as a **third tier**, only firing after both Groq and its retry and Gemini have already failed — same mechanism as AI-Bridge's `askClaude()` (`claude -p --model sonnet`, prompt via stdin) but called directly via `subprocess` instead of through `bridge.mjs`/Node, so it inherits the worker's own cwd. Installed Node.js + the `claude` CLI, generated a long-lived OAuth token via `claude setup-token` (postmortem on a `400` error during that: not clock skew, not SSH/port-forwarding — the flow redirects to a hosted callback page, `platform.claude.com/oauth/code/callback`, not `localhost`; a fresh retry on a clean URL/code fixed it). Verified working end-to-end, including through the actual `_attempt_claude()` function with the token loaded.

**Then disabled, same day, before ever running in anger.** A prior session's handoff (`~/HANDOFF-1.md`, 2026-08-24) had already flagged this exact pattern — routing Claude Code through Pro-subscription auth instead of a metered API key — in AI-Bridge's `askClaude()`, calling it "likely a real ToS problem... parked until rebuilt with an actual API key." This session's build reintroduced the identical pattern without that context, then found the handoff note while verifying AI-Bridge separately. `CLAUDE_ESCALATION_ENABLED = False` in `aios_runner.py` now gates the whole tier off — see the comment there for the full reasoning. `-p` mode is genuinely Anthropic's own documented CI/scripting feature, so this isn't a clear-cut violation either way; it's unresolved, not dismissed. The `CLAUDE_CODE_OAUTH_TOKEN` stays in `.env` (harmless while the flag is off) so flipping this back on — or switching to a real `ANTHROPIC_API_KEY` instead — is a small change, not a rebuild, once Felix actually decides.

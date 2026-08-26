# Task Runner

Purpose: The live automation loop that lets Felix hand AI-OS a task from anywhere (shell or Telegram) and get it executed headlessly on the server. Moved here from the repo root on 2026-08-26 so the vault's own README reflects what's actually running, instead of the automation living as loose scripts beside it.
Last Updated: 2026-08-26
Status: Active — three systemd services running continuously on the server; hardened and re-verified 2026-08-26
Related Documents: [[02_Systems/Automation/README|Automation]], [[Future_Integration]]

---

## What runs here

| File | Role |
|---|---|
| `aios_runner.py` | The worker. Polls `tasks/inbox/` in a loop, runs each task through Open Interpreter (headless, `auto_run=True`), writes the result to `tasks/logs/`, moves the task to `tasks/completed/`. Tries a chain of free models in order (`MODEL_CHAIN`) before giving up — see below. A Claude tier (`claude -p --model sonnet`) exists but is **disabled** — see further below. |
| `System_Prompt.md` | The worker's actual system prompt — see below. |
| `dispatch_task.py` | CLI entry point. Drops a task file into `tasks/inbox/`, then polls for the matching log (up to 180s) and prints the result. `--no-wait` to fire and return immediately. |
| `telegram_bridge.py` | Same idea, over Telegram — only replies to the one allowed user ID, edits its own status message once the worker's log appears. |
| `scripts/cloud_backup.py` | Tars the whole repo (`/home/nost/AI-OS`), uploads to Google Drive via `rclone`, prunes local archives older than 7 days. |
| `scripts/send_telegram_notification.py` | One-off outbound Telegram message, reusing the same bot token — for things other than task results. Now actually wired into `cloud_backup.py`'s failure path. Stdlib-only on purpose: systemd runs `cloud_backup.py` under `/usr/bin/python3`, which has no `python-dotenv`, so a notifier importing it would have failed exactly when it was needed. |
| `requirements.txt` | Pinned dependencies for the venv at `/home/nost/interpreter-env`. Added 2026-08-26 — there was no dependency manifest at all before. |

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

## Vault-aware system prompt (added 2026-08-26)

The system prompt used to be a generic six-line string hardcoded in `aios_runner.py` — no awareness this worker runs inside a specific, structured vault. Every task that needed to find something (e.g. "check TemplateSales status") burned a `find`/`grep` round-trip rediscovering the folder layout from scratch, which costs more on the small free models in `MODEL_CHAIN` than on a large one.

Moved to [[02_Systems/Automation/TaskRunner/System_Prompt|System_Prompt.md]] instead — same "Markdown is the source of truth" convention the rest of the vault already follows, so it's editable/versioned like everything else, not buried in Python. `_load_system_prompt()` reads it at startup and extracts everything between two HTML-comment markers (plain text only in there — no wikilinks, the worker can't resolve Obsidian syntax).

Content-wise it gives the worker: what AI-OS actually is, the real top-level folder map (so `10_Projects/<name>/` vs `02_Systems/` isn't rediscovered every time), and one new guardrail that didn't exist before — no destructive/hard-to-reverse actions (`rm -rf`, force-push, deleting outside scratch, overwriting uncommitted git changes) unless the task text explicitly asks for that exact thing. Everything else stays exactly as unattended as before.

**Deliberately not filed under `04_Agents/`.** That folder's own README states plainly it introduces no automation — every entry there is "invoked manually, in chat" with "no separate infrastructure." TaskRunner is precisely that infrastructure, for a different purpose (fire-and-forget execution while Felix isn't at a keyboard) — filing it there would misrepresent both what `04_Agents/` means and what this actually is. `System_Prompt.md`'s own "What you are, and aren't" section says this explicitly, so a future session reading either file lands on the same answer.

Verified live: worker restarted, then a real `dispatch_task.py` call asked it to name TemplateSales's and the capabilities' folders "without searching first" — answered both correctly on the first response, no filesystem discovery.

## Backup: what was actually broken

**Pruning ran even when the upload failed.** `cleanup_old_archives()` deleted local archives older than 7 days regardless of whether anything reached Google Drive. Combined with the next item, that is a real path to having no backup in either place: uploads fail silently, pruning keeps running on schedule, and after a week the local copies are gone too. Pruning is now conditional on a successful upload.

**Failures were invisible.** This runs unattended from a timer at 03:00, and a failure only reached the journal. `aios-backup.service` was in fact sitting in a `failed` state — the 19:40 run on 2026-08-26 predated the `rclone config`, so the upload had never actually succeeded from systemd. Nothing said so anywhere. `cloud_backup.py` now calls `send_telegram_notification.py` on upload failure. The stale failed state was cleared and the `gdrive:` remote confirmed reachable.

**One open item:** the timer's first *scheduled* run since rclone was configured has not happened yet. The remote is confirmed working and the script path is confirmed working; the systemd-triggered combination of the two is the piece still unproven.

## Why backups/ excludes itself

`cloud_backup.py` tars the entire repo including this folder. Without an explicit exclude, every new archive would embed all previous archives inside itself, growing without bound. `EXCLUDE_RELATIVE_PATHS` in the script excludes its own `backups/` and `tasks/logs/` for exactly that reason — don't remove those excludes without addressing that.

## Reliability fixes (2026-08-26)

Four failure modes found by reading the code against how the pieces actually call each other, all fixed:

1. **Crash-loop on one bad task.** Nothing guarded the per-task body in `run_worker()`. An unreadable task file, a full disk, a failed rename — anything outside `_attempt()`'s own handling — escaped the loop, systemd's `Restart=always` brought the worker straight back, it re-globbed the *same* still-queued file, and repeated forever. Per-task work now runs under a guard that writes an error log and quarantines the task into `completed/`.

2. **Half-written logs read as answers.** `dispatch_task.py` and `telegram_bridge.py` poll for the *existence* of `tasks/logs/<task>.log`. The worker created it with a plain `open("w")`, so both could read a zero-byte or partial file and print it as the result. Logs are now written to `<name>.log.partial` and `os.replace`d into place — the pollers never see an incomplete file.

3. **Half-written tasks executed.** The same race in the other direction: both entry points wrote task files directly into `tasks/inbox/`, which the worker globs every two seconds. A truncated instruction could be picked up and run. Both now write `.part` and rename.

4. **Empty task = 180s of nothing.** An empty task file was deleted with no log written, so a waiting caller blocked for its full timeout on an instantly-known failure. It now gets an error log immediately.

Backup fixes are in the backup section below.

## Verified working (2026-08-26)

Moved from repo root into this vault path; systemd units, `.env`, and both scripts' hardcoded fallback paths updated to match. Confirmed via `sudo systemctl restart` on both continuous services plus a live `dispatch_task.py` round trip (task landed in the new inbox, worker picked it up, log + completed file appeared in the new location). The round trip's *LLM* result errored at the time — Groq per-minute limit plus Gemini's daily free-tier quota both exhausted — unrelated to the move itself. **Re-tested 2026-08-26 after the reliability fixes above: worker restarted on the patched code, `dispatch_task.py` round trip returned the expected answer through the free chain.** The model rotation works; that earlier failure was quota, as suspected.

**Also fixed the same day:** the move had left `aios-worker.service`'s `WorkingDirectory` pointing into this nested folder instead of the repo root — harmless for `aios_runner.py` itself (it resolves its own paths via `AIOS_WORKSPACE`), but it silently changed the cwd that Open Interpreter's shell commands execute *tasks'* file operations from. Reverted to `/home/nost/AI-OS`.

## Claude escalation tier — built 2026-08-26, disabled the same day

Groq's per-minute bucket and Gemini's free-tier daily cap (20 requests/day on `gemini-3.6-flash`) both failed live during the move's own verification test — not hypothetical, it just happened. Built `_attempt_claude()` as a **third tier**, only firing after both Groq and its retry and Gemini have already failed — same mechanism as AI-Bridge's `askClaude()` (`claude -p --model sonnet`, prompt via stdin) but called directly via `subprocess` instead of through `bridge.mjs`/Node, so it inherits the worker's own cwd. Installed Node.js + the `claude` CLI, generated a long-lived OAuth token via `claude setup-token` (postmortem on a `400` error during that: not clock skew, not SSH/port-forwarding — the flow redirects to a hosted callback page, `platform.claude.com/oauth/code/callback`, not `localhost`; a fresh retry on a clean URL/code fixed it). Verified working end-to-end, including through the actual `_attempt_claude()` function with the token loaded.

**Then disabled, same day, before ever running in anger.** A prior session's handoff (`~/HANDOFF-1.md`, 2026-08-24) had already flagged this exact pattern — routing Claude Code through Pro-subscription auth instead of a metered API key — in AI-Bridge's `askClaude()`, calling it "likely a real ToS problem... parked until rebuilt with an actual API key." This session's build reintroduced the identical pattern without that context, then found the handoff note while verifying AI-Bridge separately. `CLAUDE_ESCALATION_ENABLED = False` in `aios_runner.py` now gates the whole tier off — see the comment there for the full reasoning. `-p` mode is genuinely Anthropic's own documented CI/scripting feature, so this isn't a clear-cut violation either way; it's unresolved, not dismissed. The `CLAUDE_CODE_OAUTH_TOKEN` stays in `.env` (harmless while the flag is off) so flipping this back on — or switching to a real `ANTHROPIC_API_KEY` instead — is a small change, not a rebuild, once Felix actually decides.

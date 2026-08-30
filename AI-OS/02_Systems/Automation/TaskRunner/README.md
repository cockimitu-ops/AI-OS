# Task Runner

Purpose: The live automation loop that lets Felix hand AI-OS a task from anywhere (shell or Telegram) and get it executed headlessly on the server. Moved here from the repo root on 2026-08-26 so the vault's own README reflects what's actually running, instead of the automation living as loose scripts beside it.
Last Updated: 2026-08-30
Status: Active — two continuous services plus five timers; agents plan unattended daily and act only on Felix's 20:00 approval as of 2026-08-30
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
| `scripts/health_check.py` | The supervision layer (added 2026-08-30) — see below. |
| `scripts/run_schedules.py` | Enqueues due recurring agent tasks from `schedules/` (added 2026-08-30) — see below. |
| `proposals.py` | The propose/approve gate: what agents want to change, waiting on Felix (added 2026-08-30) — see below. |
| `scripts/evening_review.py` | 20:00 sharp — sends the day's proposals to Telegram and asks which to take. |
| `scripts/morning_brief.py` | Daily good-morning digest over Telegram (added 2026-08-30) — see below. |
| `scripts/send_telegram_notification.py` | One-off outbound Telegram message, reusing the same bot token — for things other than task results. Wired into `cloud_backup.py`'s failure path and `health_check.py`'s alerts. Stdlib-only on purpose: systemd runs both under `/usr/bin/python3`, which has no `python-dotenv`, so a notifier importing it would have failed exactly when it was needed. |
| `agents.py` | Agent selection. Resolves aliases (`@research` → `Research_Analyst`), loads each agent's Executable Prompt block from [[04_Agents/README|04_Agents]]. Shared by all three entry points so they can't disagree about what an alias means. |
| `memory.py` | Bounded per-conversation memory. Stores the *conversation* (your message + the worker's prose answer), never Open Interpreter's raw transcript — replaying old command output into a small free model degrades it silently. |
| `vault_write.py` | Structured write-back. Creates notes and appends Analytics rows, with an allowlist of destinations, correct vault headers, and no code path that overwrites. |
| `requirements.txt` | Pinned dependencies for the venv at `/home/nost/interpreter-env`. Added 2026-08-26 — there was no dependency manifest at all before. |
| `External_Access_Plan.md` | Planning only, nothing built — what it would take to extend TaskRunner to Gmail, YouTube, and a phone, and why that's a different risk class from the vault-write allowlist. |
| `test_taskrunner.py` | Regression tests for every reliability fix below. stdlib `unittest`, no dependencies, no venv: `python3 -m unittest test_taskrunner -v`. Runs in well under a second. |

`tasks/` (inbox/completed/logs) and `backups/` are runtime output, not source — gitignored except for structure.

## How it's wired to the server

Seven systemd units, all under `/etc/systemd/system/`, `WorkingDirectory` and `ExecStart` pointing into this folder — two continuous services and five timers:

- `aios-worker.service` — runs `aios_runner.py`, `Restart=always`
- `aios-telegram.service` — runs `telegram_bridge.py`, `Restart=always`, starts `After=aios-worker.service`
- `aios-backup.service` (`Type=oneshot`) + `aios-backup.timer` — runs `scripts/cloud_backup.py` daily at 03:00
- `aios-healthcheck.service` (`Type=oneshot`) + `aios-healthcheck.timer` — runs `scripts/health_check.py` every 15 minutes
- `aios-scheduler.service` (`Type=oneshot`) + `aios-scheduler.timer` — runs `scripts/run_schedules.py` every 10 minutes
- `aios-review.service` (`Type=oneshot`) + `aios-review.timer` — runs `scripts/evening_review.py` at 20:00 Europe/Berlin, `AccuracySec=1s` (systemd defaults to a 1-minute window and would otherwise batch the wakeup; Felix asked for 20:00 sharp)
- `aios-morning.service` (`Type=oneshot`) + `aios-morning.timer` — runs `scripts/morning_brief.py` daily at 07:00 Europe/Berlin (the timer unit's `OnCalendar` carries the timezone directly, so it tracks DST — the server itself stays on UTC)

All of them load secrets via `EnvironmentFile=/home/nost/AI-OS/.env` — the `.env` file itself stays at the repo root (gitignored), not inside the vault, since it's a secret rather than vault content.

`AIOS_WORKSPACE` in `.env` points at this folder (`/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner`) — that's what `aios_runner.py`, `dispatch_task.py`, and `telegram_bridge.py` resolve `tasks/inbox|completed|logs` against. `cloud_backup.py` doesn't use that variable — it hardcodes the repo root as its backup source independently, since it needs to tar the whole tree, not just this folder.

## Free model rotation (expanded 2026-08-26)

Felix has no budget for a paid API, so the whole chain stays free by construction. `MODEL_CHAIN` in `aios_runner.py` tries, in order: `groq/openai/gpt-oss-120b` → same model again after a 20s cooldown (Groq's per-minute bucket clears fast) → `groq/openai/gpt-oss-20b` → `gemini/gemini-3.6-flash` → `gemini/gemini-3.5-flash-lite`. The two "second sibling" models (`gpt-oss-20b`, `flash-lite`) cost nothing new — same `GROQ_API_KEY`/`GEMINI_API_KEY` already in `.env`, no new signup — and each is metered as a separate quota bucket from its sibling, so they're genuinely additional headroom, not the same limit under a different name.

**One real dead end during this, worth remembering:** the obvious pick, `gemini/gemini-flash-lite-latest`, works fine as a raw API call but 400s specifically inside Open Interpreter's tool-calling flow (`Function call is missing a thought_signature` — a real constraint newer "thinking" Gemini models impose on function-call parts, not a config mistake). Always verify a new model through the *actual* code path (`_attempt()`), not just a raw curl — that's what caught this before it shipped silently broken. `gemini-3.5-flash-lite` was checked the same way and works cleanly.

## Two more backup providers, direct this time (2026-08-30)

Tried [FreeLLMAPI](https://freellmapi.co) as a self-hosted router the same day — worked, but Felix wanted more free capacity without a second service to run and patch, so it was removed a few hours later. Added **Cerebras** and **OpenRouter** directly instead — litellm-native providers, no custom endpoint, same pattern as Groq/Gemini above.

Each is gated on its own env var (`CEREBRAS_API_KEY`, `OPENROUTER_API_KEY`) being present in `.env` — absent either one, `MODEL_CHAIN` is unchanged from before this section existed.

**Both keys were added 2026-08-30. Real activation status, checked live, not assumed:**
- **Cerebras: blocked.** Correctly wired — the worker reaches Cerebras with the right model and the right auth — but the account itself returns `CerebrasException - Payment required to access this resource. Visit your billing tab.` Cerebras' own docs say the free tier needs no credit card; this account is hitting a payment wall anyway. **Someone needs to visit Cerebras' billing tab and check what it's actually asking for** before this tier does anything besides fail over immediately. Not a code problem.
- **OpenRouter: confirmed working**, 2026-08-30 — called directly through `_attempt()` (bypassing the rest of the chain, since it sits last and the real chain kept succeeding on earlier entries first), returned a correct response. Same test surfaced a real gap: Open Interpreter couldn't auto-detect this model's context window and silently defaulted to 8000 against an actual 1,000,000 (confirmed on OpenRouter's own model page) — a real capability loss, not a cosmetic warning. `MODEL_CHAIN` now sets `context_window`/`max_tokens` explicitly for this entry; re-tested afterward with no warning.

- **Cerebras** (`cerebras/gpt-oss-120b`) — same model family already used via Groq, a separate vendor's quota. Genuinely generous free tier, verified against Cerebras' own docs rather than an aggregator site: 1M tokens/day, 14,400 requests/day per model, no expiration, 65k context on the free tier. Inserted early in the chain to match that headroom.
- **OpenRouter** (`openrouter/nvidia/nemotron-3-super-120b-a12b:free`) — appended last, deliberately: the free tier caps at 50 requests/day on an unfunded account, the tightest quota of anything in this chain. **OpenRouter's free models rotate without warning** — confirmed live against `https://openrouter.ai/api/v1/models` on 2026-08-30; the first pick (`meta-llama/llama-3.3-70b-instruct:free`) was already gone from that list by the time it was checked, which is exactly why it was checked rather than assumed. If this one 404s later, re-query that endpoint for a current replacement rather than guessing a new name.

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

## Supervision layer (added 2026-08-30)

`health_check.py`, on a 15-minute timer, checks the three things the 2026-08-30 LAN outage showed nobody was watching:

- **Services up** — `systemctl is-active` on `aios-worker.service` and `aios-telegram.service`.
- **Network has a real default route** — parses `ip route show default` for the interface(s) actually carrying it, checks `eno1` (the server's real uplink) specifically has an IPv4 address, and confirms an actual socket connect to `1.1.1.1:443` succeeds. This exists because of what really happened that day: `eno1` silently lost its IPv4, traffic kept working because `wlo1` (a phone-based bridge Felix built for a different purpose) picked up the default route, and nothing said so anywhere — the failure was invisible until someone went looking. The check specifically flags a default route that exists but isn't via `eno1`, not just "no route at all", so this exact failure mode gets caught even though connectivity technically still works.
- **Last backup succeeded** — `systemctl is-failed aios-backup.service` (did the last run fail) *and* the newest archive's age in `backups/` (is a run even still happening — `is-failed` alone would miss a disabled or removed timer, since it only reflects whatever the last run that actually happened returned).

Alerts go out over the same `send_telegram_notification.py` used by backup failures. State (which checks are currently failing, when each was last alerted) persists to `health/state.json` — gitignored runtime data, same pattern as `tasks/` and `backups/*.tar.gz`. This is what keeps it from being spam: a new failure alerts immediately, an unresolved one reminds again only every 6 hours, and a recovery alerts once. A check that has never failed stays completely silent.

The gather/evaluate split (`gather_*` does subprocess/socket/filesystem calls, `evaluate_*` and `decide_alerts` are pure functions on their output) exists so the actual pass/fail and alert-timing logic is unit tested (`TestHealthCheck` in `test_taskrunner.py`) without mocking subprocess or touching the network.

**Deliberately not implemented:** an alert on the health-check service itself dying — the same blind spot `aios-backup.service` had before this existed. `Restart=` doesn't apply to a `Type=oneshot` unit, but the timer's `Persistent=true` means a missed run (server was off) catches up on the next boot. If this needs a stronger guarantee later, a `OnFailure=` unit on `aios-healthcheck.service` is the standard way, not built here since two silent-failure classes were already fixed today and a third can wait for Felix to actually want it.

## Morning brief (added 2026-08-30)

`morning_brief.py`, daily at 07:00 Europe/Berlin, sends a plain Telegram message through the same bot — no new channel, no page to open. Right now it has one section: server status, built by importing `health_check.py` directly and formatting whatever `run_checks()` returns ("everything's fine" or a list of what's down).

**Email is deliberately not in it yet.** Felix asked for new emails in the digest too, and this session checked the Gmail tools actually connected here (`forward`, `reply`, `send_message`, `trash_message`, spam/label management) before assuming it could be built — every one of them is an *action* on a message you already have the ID for. `reply`/`forward` both reference a `get_thread` tool to obtain that ID, but no such tool (or any list/search tool) is actually available. There is currently no way to read or list Gmail from this session at all, read-only or otherwise.

Separately: even once that's fixed, the *inbox-reading* half of this specific script can't go through that connector anyway — connector tools only exist inside a Claude/claude.ai session, and this script runs unattended under `systemd`/`/usr/bin/python3`, with nothing resembling a session around it.

The two scheduled agent mechanisms available in a Claude session (`scheduled-tasks`, tied to opening the desktop app on Felix's Windows machine; `CronCreate`, session-only and gone in 7 days) were both considered and rejected for this specifically because neither is the always-on Linux server — a systemd timer, matching every other piece of TaskRunner, was the only option that's actually unattended and actually reliable.

**Two real attempts at Gmail read access, both dropped 2026-08-30 — don't retry either blindly.**
1. **OAuth device flow** (`gmail.readonly`, no local redirect listener needed) — abandoned before finishing: registering the OAuth client in Google Cloud Console required a billing-enabled project, a real wall for a personal single-account setup.
2. **IMAP with a Gmail App Password** (`imaplib`, stdlib, no Cloud project at all) — built, wired into `morning_brief.py`, then dropped the same day: Felix's account doesn't have App Passwords available at all (Google gates this off entirely for some accounts — not something either of us can configure around).

Both builds were fully removed rather than left disabled in the tree. `morning_brief.py` is back to server status only. If this comes up again, it needs an actual third option, not another pass at OAuth or App Passwords specifically — see [[02_Systems/Automation/TaskRunner/External_Access_Plan|External_Access_Plan.md]] for the risk framing that still applies regardless of mechanism.

## Why backups/ excludes itself

`cloud_backup.py` tars the entire repo including this folder. Without an explicit exclude, every new archive would embed all previous archives inside itself, growing without bound. `EXCLUDE_RELATIVE_PATHS` in the script excludes its own `backups/` and `tasks/logs/` for exactly that reason — don't remove those excludes without addressing that.

## Agents and memory (2026-08-27)

```bash
dispatch_task.py --agent research --thread demo "profile Acme Corp"
dispatch_task.py --thread demo "now do the same for their closest competitor"
dispatch_task.py --thread demo --reset
```

On Telegram it's automatic — each chat is its own thread, so a bare follow-up just works. `agents` lists the roster, `memory` shows what's remembered, `reset` clears it.

**Memory is bounded on two axes**, because either alone is insufficient: `MAX_TURNS = 6` and `MAX_CHARS = 6000`, plus `MAX_TURN_CHARS = 2000` so one huge turn can't consume the whole budget. Oldest drops first. The models in `MODEL_CHAIN` have modest context windows and degrade *silently* rather than erroring, so these are deliberately conservative.

Three behaviours worth knowing:
- **A bare follow-up inherits the thread's agent.** `@research do X` then `now do Y` stays Research_Analyst.
- **Failed tasks never enter memory.** Replaying "all models failed" as context spends budget a real turn needs.
- **The CLI is opt-in (`--thread`), Telegram is automatic.** A shell invocation is usually one-shot; silently accumulating history across unrelated commands would surprise.

## Agent handoffs (added 2026-08-30)

Agents could be selected but never talked to each other — every task ran in isolation, so a Research_Analyst finding with real pricing implications had nowhere to go but a log. `agents.py` now parses a trailing `<!-- handoff: Agent: reason -->` line out of a successful agent's own output (`parse_handoff`) and, if the named agent resolves, `_run_task` in `aios_runner.py` enqueues that output as a brand new task file for it — atomically, `.part` + `os.replace`, the same pattern `dispatch_task.py`/`telegram_bridge.py` already use, since this write happens from inside the worker's own loop, which globs `tasks/inbox/` again on its very next pass.

The directive line itself is stripped from what actually reaches the log/Telegram/memory — Felix sees a plain "(Handed off to Business Development: reason)" footer instead of raw HTML-comment syntax. A self-handoff (an agent naming itself) is a silent no-op rather than a queued task, and every handoff-created file carries `<!-- handoff_depth: N -->`; past `agents.MAX_HANDOFF_DEPTH` (3), a handoff is suppressed and says so in the output rather than chaining further. That cap is structural, not a prompt instruction telling agents to stop — free models under load already don't reliably follow the ones they have (see `System_Prompt.md`'s guardrail section), so a two-agent ping-pong needs a real ceiling, not a polite request.

Only wired into the two flows that are real today — Research_Analyst → Business_Development and Content_Producer → Business_Development, both now spelled out in the relevant agent's Executable Prompt block, not just the human-facing prose above it (Content_Producer's "hand to Business_Development" line existed since Sprint 024ish and had never once done anything). See [[04_Agents/README|04_Agents]] for the framing; this section is the implementation.

## Orchestration: routing (added 2026-08-30)

TaskRunner used to *dispatch* — you named an agent or got the base prompt. It now *orchestrates*: a task that names no agent gets one picked for it. `_route()` in `aios_runner.py` sends the request plus a catalog of agents and their scopes to one model, and runs the task under whichever specialist comes back.

**Routing is a direct `litellm.completion()` call, deliberately not `_attempt()`.** Picking an agent is a classification; putting it through Open Interpreter would spin up the entire tool-calling loop — shell access included — to answer a question that needs one word. Direct is cheaper, faster, and structurally cannot execute a command.

Three properties that make it safe to leave on by default:
- **An explicit agent always wins.** Routing runs last, after the `<!-- agent: -->` directive and after a thread's inherited role, so it can never override a stated intent.
- **Every failure path returns `None`**, which is precisely the pre-routing behaviour. A dead router degrades to "runs on the base prompt", never to a failed task.
- **Only the first 3 `MODEL_CHAIN` entries are tried.** Routing must not cost more than the task it routes; if the chain is that degraded, running general-purpose is the right answer.

The agent catalog is built from each agent file's own `Purpose:` header (`agents.summaries()`) rather than a second list — so routing reads the same description a person does, and the two can't drift apart.

**One real trap, found live rather than by inspection:** the first version used `max_tokens=16` — plenty for one agent name — and routing returned an empty string *every single time*. `gpt-oss`, the whole top of `MODEL_CHAIN`, is a reasoning model: it spends its token budget thinking before emitting any content, so 16 tokens produced pure reasoning and no answer. The failure is completely silent, because an empty reply is indistinguishable from "no specialist fits" — routing would have sat there looking enabled and doing nothing. `ROUTING_MAX_TOKENS = 512`; verified the same prompt returns `Business_Development` at 512 and `''` at 16.

## Self-directed agents: propose, then approve (added 2026-08-30)

The agents plan on their own every day and change nothing. At 20:00 Europe/Berlin Felix gets one Telegram message listing what they came up with, replies `approve 1 3`, and only the approved items become real tasks.

**The gate is structural, not a prompt.** A proposing run writes to `proposals/pending.json` and has no code path into `tasks/inbox/` at all. The only place a proposal becomes an executable task is the `approve` handler in `telegram_bridge.py`. `External_Access_Plan.md` already made this argument for Gmail and it holds identically here: a confirmation that lives outside the model's own judgement beats a system prompt asking it to check first, because free models under load demonstrably skip instructions they were given.

```
schedules/*.md  --(propose)-->  proposals/pending.json     [agents: unattended, changes nothing]
                                        |
                                    20:00 sharp
                                        v
                                 proposals/review.json  --> Telegram
                                        |
                                 Felix: approve 1 3          [the only crossing]
                                        v
                                  tasks/inbox/  ------------> worker executes
```

Two daily planners ship with it, both pointed at revenue because that is the actual goal: `daily_revenue_plan.md` (Business_Development, 18:30 — TemplateSales has three built products earning nothing and the bottleneck is publishing) and `daily_system_plan.md` (Vault_Architect, 18:45 — judged by whether a change helps Felix earn sooner, not by tidiness).

**This is also how agents schedule themselves.** `daily_system_plan` is explicitly allowed to propose new or changed files in `schedules/`, so the system can evolve its own cadence — but every such change still lands in the 20:00 review first. Self-scheduling and the approval gate are the same mechanism, which is why there is no separate one. It works: the very first live run proposed changing its own `daily_revenue_plan.md`.

Behaviours worth knowing:
- **Proposals are numbered against a snapshot.** `open_review()` copies pending into `review.json` and clears pending, so `approve 2` means entry 2 of what Felix is looking at, even if a planner runs while he is deciding.
- **Declined is a decision, not a deferral.** A declined proposal is archived, not returned to pending — otherwise it would be re-asked every night until approved out of attrition rather than agreement.
- **Out-of-range is an error, not a partial approval.** `approve 1 5` of four proposals does nothing and says so, rather than doing three-quarters of what was asked.
- **Failed runs store nothing.** "All models failed" is not a proposal, and padding the review with them trains Felix to skim it.
- **A missing `PROPOSAL:` marker costs one long line, not the day's thinking** — unmarked output becomes a single proposal rather than being dropped.

Telegram: `proposals` (or `review`) re-shows the current review, `approve ...` decides it.

## Scheduled agents (added 2026-08-30)

Agents ran only when Felix asked. They now also run on their own schedule: drop a Markdown file in `schedules/`, and `scripts/run_schedules.py` (systemd timer, every 10 min) enqueues it whenever it's due.

```markdown
<!-- agent: Business_Development -->
<!-- schedule: weekly mon 08:00 -->
Report which TemplateSales products are still unpublished and the next action.
```

**A file, not a systemd unit per schedule** — deliberately. One unit per recurring task would put every new schedule behind `sudo`, and adding one should cost exactly what adding any other vault content costs: writing a Markdown file.

Cadence grammar is intentionally tiny — `daily HH:MM`, `weekly <day> HH:MM`, `hourly`. A real cron parser is more expressive and offers more ways to be subtly wrong about what runs unattended at 3am. Times are **Europe/Berlin**, not the server's UTC, so `07:30` means 07:30 where Felix is and keeps meaning it across DST.

Two behaviours worth knowing:
- **A missed run fires once, not never and not N times.** `next_due_after()` returns the most recent *scheduled* moment and compares it against the last run, so the server being off overnight produces exactly one catch-up run rather than a backfill burst.
- **A bad schedule file never blocks the others.** An unparseable cadence, a missing instruction or an unreadable file is reported and skipped; every other schedule still fires.

**`<!-- notify -->` is what makes any of this useful.** Interactive tasks are shown to whoever is waiting — `dispatch_task.py` and `telegram_bridge.py` both poll for the log themselves. A scheduled task has nobody waiting, so without this directive its answer would land in `tasks/logs/` and be read by no one. The scheduler adds it to everything it queues, and the worker pushes the result through the same `send_telegram_notification.py` the backup and health-check paths use. A failed push is a printed warning, never a failed task — the work is already done and logged by then.

**`PYTHONUNBUFFERED=1` is set on `aios-worker.service`/`aios-telegram.service`** and matters more than it looks: Python block-buffers stdout when it's a pipe, so `[✓] Done` lines sat in the buffer and never reached journald. Verified live 2026-08-30 — a task's log file was written at 16:25 while the journal's last line was 16:23:52. For a system meant to run unattended, "did that task ever finish?" has to be answerable from the journal.

## Write-back (2026-08-27)
`09_Analytics` held four databases with zero rows since Sprint 012 and `Promotion_Candidates` was empty just as long — the Learning Loop in `02_Systems/Analytics/` was fully specified and never executed, because the worker could only read the vault.

```bash
python3 vault_write.py destinations
python3 vault_write.py note --folder 08_Research --title "X" --body-file /tmp/b.md
python3 vault_write.py row --file 09_Analytics/Hook_Database.md --cells "a|b|c|d|e"
```

**This grants no new capability** — the worker runs `auto_run=True` with a shell and could already write anywhere. What it lacked was a path that gets the vault's conventions right and a boundary keeping generated output away from files the vault depends on:

- **Allowlist.** Only `08_Research`, `09_Analytics`, `06_Assets` and existing `10_Projects/*` accept notes. `00_System/`, `01_Architecture/` and traversal attempts are refused — all tested.
- **Never overwrites.** Every path either creates or appends; a repeat run suffixes `_2` rather than destroying the first note. A test asserts no `open(path, "w")` exists in the module.
- **Headers are generated, not prompted for.** `Naming_Convention.md` requires four fields a small model won't produce reliably.
- **Execution markers are stripped.** Open Interpreter instruments shell with `echo "##active_line5##"`; via a heredoc those land *inside* the file. The first real write produced a note whose `Purpose:` was literally that echo. The model never sees the injected lines, so no prompt prevents it — it's sanitised in code.

## Reliability fixes (2026-08-26)

Four failure modes found by reading the code against how the pieces actually call each other, all fixed:

1. **Crash-loop on one bad task.** Nothing guarded the per-task body in `run_worker()`. An unreadable task file, a full disk, a failed rename — anything outside `_attempt()`'s own handling — escaped the loop, systemd's `Restart=always` brought the worker straight back, it re-globbed the *same* still-queued file, and repeated forever. Per-task work now runs under a guard that writes an error log and quarantines the task into `completed/`.

2. **Half-written logs read as answers.** `dispatch_task.py` and `telegram_bridge.py` poll for the *existence* of `tasks/logs/<task>.log`. The worker created it with a plain `open("w")`, so both could read a zero-byte or partial file and print it as the result. Logs are now written to `<name>.log.partial` and `os.replace`d into place — the pollers never see an incomplete file.

3. **Half-written tasks executed.** The same race in the other direction: both entry points wrote task files directly into `tasks/inbox/`, which the worker globs every two seconds. A truncated instruction could be picked up and run. Both now write `.part` and rename.

4. **Empty task = 180s of nothing.** An empty task file was deleted with no log written, so a waiting caller blocked for its full timeout on an instantly-known failure. It now gets an error log immediately.

Backup fixes are in the backup section below.

**These are covered by tests now** — `test_taskrunner.py`, 20 cases, stdlib only. Each one maps to a bug that was actually live here, because all four of the above fail silently rather than loudly: a truncated instruction, a blank answer, a service that restarts forever. Nothing raises.

The suite was mutation-checked rather than assumed to work: each fix was reverted in a throwaway copy and the tests re-run. All four reverts were caught, each by the intended test. A test that passes against the broken code is worse than no test, so this check is worth repeating if the suite is ever extended.

`AIOS_WORKSPACE` is redirected to a temp directory before `aios_runner` is imported, and the open-interpreter import is stubbed — the tests never touch the live queue, and never call a model.

## Verified working (2026-08-26)

Moved from repo root into this vault path; systemd units, `.env`, and both scripts' hardcoded fallback paths updated to match. Confirmed via `sudo systemctl restart` on both continuous services plus a live `dispatch_task.py` round trip (task landed in the new inbox, worker picked it up, log + completed file appeared in the new location). The round trip's *LLM* result errored at the time — Groq per-minute limit plus Gemini's daily free-tier quota both exhausted — unrelated to the move itself. **Re-tested 2026-08-26 after the reliability fixes above: worker restarted on the patched code, `dispatch_task.py` round trip returned the expected answer through the free chain.** The model rotation works; that earlier failure was quota, as suspected.

**Also fixed the same day:** the move had left `aios-worker.service`'s `WorkingDirectory` pointing into this nested folder instead of the repo root — harmless for `aios_runner.py` itself (it resolves its own paths via `AIOS_WORKSPACE`), but it silently changed the cwd that Open Interpreter's shell commands execute *tasks'* file operations from. Reverted to `/home/nost/AI-OS`.

## Claude escalation tier — built 2026-08-26, disabled the same day

Groq's per-minute bucket and Gemini's free-tier daily cap (20 requests/day on `gemini-3.6-flash`) both failed live during the move's own verification test — not hypothetical, it just happened. Built `_attempt_claude()` as a **third tier**, only firing after both Groq and its retry and Gemini have already failed — same mechanism as AI-Bridge's `askClaude()` (`claude -p --model sonnet`, prompt via stdin) but called directly via `subprocess` instead of through `bridge.mjs`/Node, so it inherits the worker's own cwd. Installed Node.js + the `claude` CLI, generated a long-lived OAuth token via `claude setup-token` (postmortem on a `400` error during that: not clock skew, not SSH/port-forwarding — the flow redirects to a hosted callback page, `platform.claude.com/oauth/code/callback`, not `localhost`; a fresh retry on a clean URL/code fixed it). Verified working end-to-end, including through the actual `_attempt_claude()` function with the token loaded.

**Then disabled, same day, before ever running in anger.** A prior session's handoff (`~/HANDOFF-1.md`, 2026-08-24) had already flagged this exact pattern — routing Claude Code through Pro-subscription auth instead of a metered API key — in AI-Bridge's `askClaude()`, calling it "likely a real ToS problem... parked until rebuilt with an actual API key." This session's build reintroduced the identical pattern without that context, then found the handoff note while verifying AI-Bridge separately. `CLAUDE_ESCALATION_ENABLED = False` in `aios_runner.py` now gates the whole tier off — see the comment there for the full reasoning. `-p` mode is genuinely Anthropic's own documented CI/scripting feature, so this isn't a clear-cut violation either way; it's unresolved, not dismissed. The `CLAUDE_CODE_OAUTH_TOKEN` stays in `.env` (harmless while the flag is off) so flipping this back on — or switching to a real `ANTHROPIC_API_KEY` instead — is a small change, not a rebuild, once Felix actually decides.

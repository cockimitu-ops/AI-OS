# External Access Plan — Gmail, YouTube, Phone

Purpose: A planning document, not a build spec. TaskRunner currently reads and writes only inside this vault, with a hand-built allowlist ([[02_Systems/Automation/TaskRunner/README|vault_write.py]]) as its only writable surface. This lays out what it would take to extend it to Gmail, YouTube, and a phone, and specifically why that is a different risk class from what exists today — not just more integrations of the same kind.
Last Updated: 2026-08-27
Status: Planning — nothing here is built, nothing here is authorized
Related Documents: [[02_Systems/Automation/TaskRunner/README|TaskRunner]], [[02_Systems/Automation/README|Automation]], [[04_Agents/README|04_Agents]], [[Future_Integration]]

---

## The actual question this answers
Not "can TaskRunner call these APIs" — it can, mechanically, the same way it can already write anywhere on disk. The real question is what changes about the worker's trust model once its actions can leave the vault: send an email, publish a video, or reach a physical device. Right now every mistake it makes is recoverable — a bad note gets deleted, a corrupted table row gets reverted from git. A sent email is not recoverable. That asymmetry is the design constraint everything below is built around.

## Start from what already exists, so this isn't confused with it
This session's own Claude connector already has Gmail-shaped tools (`forward`, `reply`, `send_message`, `trash_message`, `mark_message_spam`, label management) — separate from TaskRunner entirely. That's Claude, with a human steering every single turn, using Anthropic's frontier models, reviewed before each action executes. What this document plans is different in kind: an **unattended** worker, **Telegram-triggerable by design**, running on **free models** (`gpt-oss-20b`, `gemini-3.5-flash-lite` are in its own fallback chain) with **no per-message human review** — that is the entire point of TaskRunner, stated plainly in its own README as "fire-and-forget execution while Felix isn't at a keyboard." Giving *that* executor its own mailbox access is not the same decision as Claude already having one, and should not be reasoned about as if it were.

Worth naming directly: this worker produced `echo "##active_line2##"` as literal file content on its first real attempt at vault write-back today, in a sandboxed folder with no send/delete capability. That is exactly the caliber of mistake a wrong email recipient or a bad YouTube upload would not survive.

---

## Gmail

### What "access" could mean — needs a decision, not an assumption
"All my gmails" implies multiple accounts, and those are not interchangeable in risk:
- **A dedicated automation mailbox** (new or existing, not Felix's daily-driver address) — lowest stakes, the natural place to start.
- **Felix's actual primary personal/business inbox** — contains password resets, financial notices, real correspondence with real people. A wrong autonomous action here has consequences outside the vault entirely.

Recommendation: **stage by account, not just by capability.** Build and prove the whole read→act pipeline against a low-stakes mailbox first. Only extend to the primary inbox once the pattern has run for real, not on day one because "all" was the literal word used.

### Scopes, staged
1. **Read-only** (`gmail.readonly`) — search, summarize, surface things that need Felix's attention. This is the genuinely low-risk tier: worst case is a bad summary, not a bad action.
2. **Draft, never send** — the worker composes a reply and leaves it as a Gmail draft. Felix sends it himself. This gets most of the time-saving with none of the irreversibility; it mirrors the escalation pattern already written into `Business_Development`'s agent prompt ("this role drafts, it doesn't act on the real world").
3. **Autonomous send** — not recommended for this worker under its current design at all. If it's ever wanted, it needs a structurally different gate than "the model decided to," e.g. a Telegram confirmation round-trip ("about to send this to X, reply YES") that blocks on a human response before the send call fires — not a system-prompt instruction asking the model to ask first, which is exactly the kind of rule a free model under load will skip.
4. **Delete/archive/label at scale** — same category as send. Out of scope for an unattended worker unless explicitly revisited.

### Concrete build shape (later, not now)
A new sibling to `vault_write.py` — `mail_read.py` / `mail_draft.py` — same discipline: an allowlist (which labels/senders it can act on), no destructive path, everything logged. OAuth token per account, stored in `.env` alongside the existing secrets, refreshed via the standard Google OAuth flow (a one-time interactive step, not something the worker does itself).

---

## YouTube

### What it's actually for, per this vault's own stated goals
Two distinct use cases, and they should be planned separately because their risk profiles differ:
- **Read: analytics and research.** Pull stats on published videos, check comments, research competitor content — feeds `AI_Video_Production` and the "produce faster every month" goal the Design Review named as currently unsupported. Low risk, close to what `vault_write.py`'s note-taking already does conceptually.
- **Write: publishing.** Uploading video, posting comments, editing metadata on a live channel. This is public-facing the moment it executes — closer to Gmail's send tier than to a vault write, because a bad upload is visible to an audience immediately, not just to Felix.

### Recommendation
Read (YouTube Data API, `youtube.readonly` scope) is a reasonable second integration after Gmail read-only proves the pattern. Write/publish should follow the same draft-not-send logic as Gmail: the worker prepares an upload (file staged, metadata written) and a human triggers the actual publish, at least until the pattern has a real track record.

---

## Phone

### This is the one that needs a scoping conversation before any technical design, not after
"Access to my phone" is not one thing. It could mean any of these, and they are wildly different in both what they grant and how they'd be built:

| Option | What it actually grants | Rough mechanism |
|---|---|---|
| A phone-side trigger surface | A way to send TaskRunner a task from the phone — this already exists, it's the Telegram bridge | Nothing new needed |
| Notification relay (read-only) | The worker sees what notifications arrived | Tasker/Termux companion script pushing events to the worker |
| SMS read/send | Full text message access | Android app with SMS permissions, or Tasker+HTTP |
| Contacts / calendar | Read or write personal data | Google account APIs (Contacts, Calendar) — same OAuth pattern as Gmail |
| Location | Where the phone is | Requires an always-running companion app with location permission — meaningfully invasive |
| Full device control | Camera, calls, app launching | Not something an unattended free-model worker should have under any staging this document can responsibly recommend |

**Before anything else here is planned in more depth, the actual want needs to be named specifically** — the difference between "I want to text the worker from my phone" (already solved) and "I want the worker to read my SMS" is not a matter of degree, it's a different feature entirely. This section stays a menu, not a proposal, until that's picked.

---

## The cross-cutting design question, regardless of which service
Every stage above that isn't pure-read needs the same thing: **a confirmation gate that lives outside the model's own judgment.** Not a system-prompt instruction telling it to ask first — instructions get skipped under load, and this worker already has instructions it doesn't reliably follow (the `python3`-vs-`python` mistake from earlier today is exactly this failure mode: told the rule, broke it anyway on a live task). The gate needs to be structural: the send/publish/write call is a separate code path that requires an external confirmation signal (a Telegram reply, a second dispatch with `--confirm`) before it executes, so a model that "decides" to send an email cannot actually cause one without a human in that specific loop.

`vault_write.py`'s allowlist-and-no-overwrite design is the right template for this, not a coincidence — extend that same shape (bounded destinations, no irreversible path, everything logged and reviewable) to whatever gets built here, rather than inventing a new trust model per service.

## Suggested order, if this proceeds
1. Gmail read-only, one low-stakes account.
2. YouTube read-only.
3. Confirmation-gate mechanism, built once, generically — not per-service.
4. Gmail draft-only, using the gate.
5. Everything else, including any phone integration, waits on (3) actually existing and (4) having run for real — and on the phone scoping conversation above happening first.

## What this document is not
Not an ADR — nothing here is decided. Not a build spec — no code, no credentials, no scopes have been requested from any provider. It exists so the next conversation about this starts from a shared understanding of the risk shape, instead of from "can the worker call the Gmail API" — it obviously can; that was never the hard part.

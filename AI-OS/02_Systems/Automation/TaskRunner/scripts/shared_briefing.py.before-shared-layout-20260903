#!/usr/bin/env python3
"""One current, bounded briefing for every AI-OS engine.

Two kinds of standing context live here:

    Knowledge_Core.md   what Felix or an AI session wrote down as durable -
                        unchanged behaviour, see load()/system_instruction().
    the event journal    what was actually said, moments ago, to whichever
                        engine answered it - see record_event()/
                        recent_activity(). Added so that "I told the Google
                        engine X five minutes ago" is not invisible to Codex
                        the next time Felix opens it - four engines behind
                        one interface should not behave like four strangers.

The journal is deliberately NOT the conversation history (conversation_store
owns that, per-conversation). It is the cross-cutting one: short, bounded,
attributed by source and engine, and every user turn on every channel is
supposed to land in it before dispatch - see api.py and telegram_bridge.py.
"""
import json
import os
import re
import threading
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
VAULT_DIR = os.path.abspath(os.path.join(TASK_RUNNER_DIR, "..", "..", ".."))
KNOWLEDGE_CORE_PATH = os.path.join(VAULT_DIR, "07_Context", "Knowledge_Core.md")
MAX_CHARS = 10_000

JOURNAL_PATH = os.path.join(TASK_RUNNER_DIR, "journal", "events.jsonl")
# Kept short on purpose - this rides on top of every single turn to every
# engine, so it is priced like a cost, not a convenience. Enough to remind an
# engine what was just discussed elsewhere, not enough to replay it.
MAX_JOURNAL_EVENTS = 400
MAX_JOURNAL_CONTEXT_CHARS = 2000
MAX_EVENT_CHARS = 400

_journal_lock = threading.Lock()

# Patterns for things that must never leave this machine's own context,
# let alone ride along into a prompt sent to a third party's API. Matched
# before anything is written, not before it is read back - a secret that
# made it to disk unredacted is still a secret that leaked once shown to a
# model.
_REDACT_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),                       # OpenAI-style
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),                      # Google API key
    re.compile(r"AKIA[A-Z0-9]{16}"),                             # AWS access key
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),                  # GitHub tokens
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),                # Slack tokens
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwort)\b\s*[:=]\s*\S+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}"),
]


def redact(text):
    """-> text with anything that looks like a live credential blanked out.

    Deliberately over-eager rather than precise: a false positive here costs
    a placeholder in a log line; a false negative costs a real secret riding
    into a prompt sent to Codex or Google."""
    text = str(text or "")
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def load():
    """Return fresh standing context, bounded so it is safe on every turn."""
    try:
        with open(KNOWLEDGE_CORE_PATH, encoding="utf-8") as handle:
            return handle.read(MAX_CHARS).strip()
    except OSError:
        return ""


# --- the shared event journal ----------------------------------------------
#
# Every user turn, on every channel, before it is dispatched anywhere. The
# point is narrow: let one engine know what was just said to another, not
# reconstruct a full transcript - that is what conversation_store.py is for,
# per-conversation.

def record_event(source, text, engine=None):
    """Append one attributed, redacted, bounded line to the shared journal.

    Never raises - a journal write failing must not be the reason a message
    was not sent. source names the channel ("web-chat", "telegram",
    "engine:codex", "background-task", ...), engine names which of the four
    answered or will answer, when known."""
    text = redact(text)[:MAX_EVENT_CHARS].strip()
    if not text:
        return
    entry = {"ts": datetime.now().isoformat(timespec="seconds"),
             "source": str(source or "unknown")[:40],
             "engine": str(engine)[:20] if engine else None,
             "text": text}
    try:
        os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
        with _journal_lock:
            lines = []
            if os.path.exists(JOURNAL_PATH):
                with open(JOURNAL_PATH, encoding="utf-8") as f:
                    lines = f.readlines()[-(MAX_JOURNAL_EVENTS - 1):]
            lines.append(json.dumps(entry, ensure_ascii=False) + "\n")
            tmp = JOURNAL_PATH + ".part"
            with open(tmp, "w", encoding="utf-8") as f:
                f.writelines(lines)
            os.replace(tmp, JOURNAL_PATH)
    except OSError:
        pass


def recent_events(limit=20):
    """Newest last (chronological), like the file itself. Never raises."""
    try:
        with open(JOURNAL_PATH, encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def recent_activity(max_chars=MAX_JOURNAL_CONTEXT_CHARS):
    """The journal, rendered as a small attributed block ready to inject into
    a prompt. Empty string if there is nothing yet, so callers never prepend
    a header over nothing."""
    events = recent_events()
    if not events:
        return ""
    lines = []
    total = 0
    for e in reversed(events):
        when = (e.get("ts") or "")[11:16]  # HH:MM, the date rarely matters here
        who = e.get("engine") or e.get("source") or "?"
        line = f"- [{when} · {who}] {e.get('text', '')}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    lines.reverse()
    return "## Recent activity across engines (attributed, may be partial)\n" + "\n".join(lines)


def system_instruction():
    """Shared instruction block for engines with a system-prompt channel."""
    core = load()
    activity = recent_activity()
    lead = (
        "You are one of several AI engines serving Felix in AI-OS. "
        "Treat the standing context below as current project context. "
        "Follow Felix's explicit request; do not take actions in his name "
        "without a clear request or approval. Keep durable project knowledge "
        "in the vault rather than inventing a private memory."
    )
    parts = [lead]
    if core:
        parts.append(f"## Shared AI-OS briefing\n{core}")
    if activity:
        parts.append(activity)
    return "\n\n".join(parts)


def prepend(message):
    """Give command-line engines the same context before the current request."""
    return f"{system_instruction()}\n\n## Felix's current request\n{message}"

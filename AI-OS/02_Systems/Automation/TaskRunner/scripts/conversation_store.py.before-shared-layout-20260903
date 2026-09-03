#!/usr/bin/env python3
"""Persistent conversations, one file per conversation, shared by every engine.

WHY

Before this, only Claude had something worth calling a conversation - its own
JSONL session files. Every other engine was either stateless per call
(codex, google-pro) or kept a single un-listable thread per Telegram chat
(gemini_chat.py). Felix asked for a real picker across all four engines: list
existing conversations, open one, keep talking, start a new one. That needs
one place that knows what a "conversation" is regardless of which engine is
answering it.

WHAT NATIVE ENGINES KEEP FOR THEMSELVES

Claude Code already owns its own session files and its own context (the CLI
resumes by session id and the transcript lives under ~/.claude/projects/).
This store does not duplicate that: a claude conversation's *messages* are
still read from claude_chat.transcript(), and this store only remembers which
native session_id belongs to which conversation id, plus the metadata
(title, timestamps) needed to list it next to the other three.

For codex, google-pro and aios there is no native multi-turn session to
attach to (codex/google-pro are one-shot CLI calls; aios is a task queue) -
so this store is their entire memory, and engines.py reads history_context()
back out to give the next call bounded context.

BOUNDS

Both axes are capped for the same reason memory.py caps them: an unbounded
conversation turns every later message in it into a more expensive one, and
the failure mode is silent (a slow, degraded reply) rather than an error.

Stdlib only.
"""
import json
import os
import re
import threading
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
CONVERSATIONS_DIR = os.path.join(TASK_RUNNER_DIR, "conversations")

# A conversation stores at most this many messages before the oldest are
# dropped - generous enough that a real back-and-forth never notices, tight
# enough that a conversation left open for months does not become a file
# scan. Each message's text is separately capped so one giant paste cannot
# burn the whole budget alone.
MAX_STORED_MESSAGES = 400
MAX_MESSAGE_CHARS = 8000

# What actually goes back into a prompt as "history". Far tighter than
# storage: this is resent in full on every non-Claude turn, so it is a cost,
# not just a display convenience.
MAX_CONTEXT_MESSAGES = 24
MAX_CONTEXT_CHARS = 6000

ID_RE = re.compile(r"conv_[a-z][a-z0-9_-]{0,20}_\d{8}_\d{6}_\d{1,6}")
ENGINE_RE = re.compile(r"[a-z][a-z0-9_-]{0,20}")

_locks_guard = threading.Lock()
_locks = {}


def _lock_for(conversation_id):
    with _locks_guard:
        lock = _locks.get(conversation_id)
        if lock is None:
            lock = threading.Lock()
            _locks[conversation_id] = lock
        return lock


def _path(conversation_id):
    return os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _load(conversation_id):
    try:
        with open(_path(conversation_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _save(conversation_id, record):
    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
    path = _path(conversation_id)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def exists(conversation_id):
    return bool(conversation_id) and bool(ID_RE.fullmatch(conversation_id)) \
        and os.path.isfile(_path(conversation_id))


def create(engine, title=None, session_id=None):
    """A new, empty conversation for one engine. -> its id.

    Raises ValueError for an engine name that could not have come from the
    catalogue - this becomes a filename fragment, so it is checked before it
    ever reaches disk."""
    engine = (engine or "").strip()
    if not ENGINE_RE.fullmatch(engine):
        raise ValueError(f"ungültige engine: {engine!r}")
    conversation_id = (f"conv_{engine}_"
                       f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    record = {
        "id": conversation_id,
        "engine": engine,
        "title": (title or "").strip()[:80],
        "session_id": session_id,
        "created": _now(),
        "updated": _now(),
        "messages": [],
    }
    _save(conversation_id, record)
    return conversation_id


def read(conversation_id):
    """Full record, or None. -> {id, engine, title, session_id, messages:
    [{role, text, ts, job_id, model}], created, updated}."""
    if not exists(conversation_id):
        return None
    record = _load(conversation_id)
    if record is None:
        return None
    record.setdefault("messages", [])
    return record


def list_conversations(engine=None, limit=50):
    """Every conversation, newest first. -> [{id, title, engine, updated_at,
    message_count}]. Optionally filtered to one engine, which is what the
    picker actually shows - a phone screen is not a place for four engines'
    conversations in one undifferentiated list."""
    try:
        names = [n for n in os.listdir(CONVERSATIONS_DIR) if n.endswith(".json")]
    except OSError:
        return []
    rows = []
    for name in names:
        record = _load(name[:-len(".json")])
        if not record:
            continue
        if engine and record.get("engine") != engine:
            continue
        rows.append({
            "id": record["id"],
            "title": record.get("title") or "(ohne Titel)",
            "engine": record.get("engine"),
            "updated_at": record.get("updated"),
            "message_count": len(record.get("messages") or []),
        })
    rows.sort(key=lambda r: r["updated_at"] or "", reverse=True)
    return rows[:limit]


def _title_from(text):
    first_line = (text or "").strip().splitlines()
    return first_line[0][:80] if first_line else ""


def append(conversation_id, role, text, job_id=None, model=None):
    """Record one message. -> the updated record, or None if the
    conversation does not exist.

    Idempotent on job_id: a client polling /api/engine-result for the same
    finished job must never see its answer recorded twice. Without this, a
    slow network retry or two browser tabs polling the same ticket each
    write their own copy of the reply."""
    if not exists(conversation_id):
        return None
    text = (text or "")[:MAX_MESSAGE_CHARS]
    with _lock_for(conversation_id):
        record = _load(conversation_id)
        if record is None:
            return None
        messages = record.setdefault("messages", [])
        if job_id and any(m.get("job_id") == job_id for m in messages):
            return record
        entry = {"role": role, "text": text, "ts": _now()}
        if job_id:
            entry["job_id"] = job_id
        if model:
            entry["model"] = model
        messages.append(entry)
        if len(messages) > MAX_STORED_MESSAGES:
            del messages[:len(messages) - MAX_STORED_MESSAGES]
        if not record.get("title") and role == "user":
            record["title"] = _title_from(text)
        record["updated"] = _now()
        _save(conversation_id, record)
        return record


def set_session_id(conversation_id, session_id):
    """Attach a native engine session (currently: Claude) to a conversation
    so the next send resumes it instead of starting over."""
    if not exists(conversation_id) or not session_id:
        return
    with _lock_for(conversation_id):
        record = _load(conversation_id)
        if record is None:
            return
        record["session_id"] = session_id
        record["updated"] = _now()
        _save(conversation_id, record)


def history_context(conversation_id, max_messages=MAX_CONTEXT_MESSAGES,
                    max_chars=MAX_CONTEXT_CHARS):
    """Recent turns, bounded, oldest first. -> [{"role", "text"}].

    For engines with no server-side memory of their own (everything but
    Claude), this IS the conversation as far as the model is concerned -
    what is not returned here was never said, on the next turn."""
    record = read(conversation_id)
    if not record:
        return []
    kept, total = [], 0
    for msg in reversed(record["messages"][-max_messages:]):
        size = len(msg.get("text", ""))
        if kept and total + size > max_chars:
            break
        kept.append({"role": msg["role"], "text": msg.get("text", "")})
        total += size
    return list(reversed(kept))


def format_context(conversation_id):
    """history_context(), rendered as the plain-text block a one-shot CLI
    prompt can be prefixed with. Empty string if there is nothing yet -
    the caller should not prepend a header for a conversation that has not
    started."""
    turns = history_context(conversation_id)
    if not turns:
        return ""
    lines = ["## Bisheriger Gesprächsverlauf"]
    for turn in turns:
        speaker = "Felix" if turn["role"] == "user" else "Assistent"
        lines.append(f"{speaker}: {turn['text']}")
    return "\n".join(lines)

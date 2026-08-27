#!/usr/bin/env python3
"""Conversation memory for TaskRunner.

Every task ran cold: `interpreter.messages = []` per attempt, so "now do the
same for the other project" was impossible over Telegram. This adds a bounded
per-conversation thread.

What is stored is the *conversation*, not Open Interpreter's raw message list -
your instruction and the worker's prose answer, which is exactly what
format_interpreter_output() now returns. Replaying the raw transcript would feed
old `find` output and command echoes back into a small free model's context,
which is both expensive and actively harmful: the models in MODEL_CHAIN have
modest context windows, and the failure mode is silent degradation rather than
an error.

Bounded on two axes because either alone is insufficient - a few enormous turns
blow the budget as easily as many small ones. Oldest turns drop first.

Threads are runtime state, gitignored like tasks/.
"""
import json
import os
import re
import time

AIOS_DIR = os.environ.get(
    "AIOS_WORKSPACE", "/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner")
THREADS = os.path.join(AIOS_DIR, "tasks", "threads")

# Deliberately conservative. gpt-oss-20b and flash-lite are in the chain, and a
# bloated history degrades their answers long before it errors.
MAX_TURNS = 6
MAX_CHARS = 6000
# One turn should never be able to consume the whole budget on its own.
MAX_TURN_CHARS = 2000

DIRECTIVE_RE = re.compile(r"^\s*<!--\s*thread:\s*([A-Za-z0-9_\-]+)\s*-->\s*\n?", re.I)
SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_\-]")


def directive(thread_id):
    return f"<!-- thread: {thread_id} -->\n"


def parse_directive(raw):
    """Strip a leading thread directive. Returns (thread_id_or_None, rest)."""
    m = DIRECTIVE_RE.match(raw or "")
    if not m:
        return None, (raw or "")
    return _safe(m.group(1)), raw[m.end():]


def _safe(thread_id):
    """Thread ids reach us from Telegram and the CLI and become filenames."""
    if not thread_id:
        return None
    cleaned = SAFE_ID_RE.sub("_", str(thread_id).strip())[:64]
    return cleaned or None


def _path(thread_id):
    return os.path.join(THREADS, f"{_safe(thread_id)}.json")


def load(thread_id):
    if not thread_id:
        return {"thread_id": thread_id, "turns": [], "agent": None}
    try:
        with open(_path(thread_id), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        # A corrupt thread file must never cost the task. Start fresh.
        return {"thread_id": thread_id, "turns": [], "agent": None}
    data.setdefault("turns", [])
    data.setdefault("agent", None)
    return data


def _trim(turns):
    """Newest-first budget, then restore chronological order."""
    kept, total = [], 0
    for turn in reversed(turns[-MAX_TURNS * 2:]):
        size = len(turn.get("user", "")) + len(turn.get("assistant", ""))
        if kept and total + size > MAX_CHARS:
            break
        kept.append(turn)
        total += size
        if len(kept) >= MAX_TURNS:
            break
    return list(reversed(kept))


def save_turn(thread_id, user, assistant, agent=None):
    """Record one completed exchange. Failures are deliberately not stored -
    replaying "ERROR: all models failed" as context teaches the model nothing
    and consumes budget that a real turn needs."""
    if not thread_id:
        return
    os.makedirs(THREADS, exist_ok=True)
    data = load(thread_id)
    data["turns"].append({
        "user": (user or "")[:MAX_TURN_CHARS],
        "assistant": (assistant or "")[:MAX_TURN_CHARS],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    data["turns"] = _trim(data["turns"])
    data["thread_id"] = thread_id
    if agent:
        data["agent"] = agent
    data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    tmp = _path(thread_id) + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _path(thread_id))


def as_messages(thread_id):
    """Prior turns in Open Interpreter's message shape, ready to seed
    interpreter.messages before a chat call."""
    out = []
    for turn in load(thread_id).get("turns", []):
        if turn.get("user"):
            out.append({"role": "user", "type": "message",
                        "content": turn["user"]})
        if turn.get("assistant"):
            out.append({"role": "assistant", "type": "message",
                        "content": turn["assistant"]})
    return out


def last_agent(thread_id):
    """So `@research do X` followed by a bare `now do Y` stays in role."""
    return load(thread_id).get("agent")


def reset(thread_id):
    """Returns True if a thread actually existed."""
    if not thread_id:
        return False
    try:
        os.remove(_path(thread_id))
        return True
    except OSError:
        return False


def summary(thread_id):
    data = load(thread_id)
    turns = data.get("turns", [])
    if not turns:
        return "No memory in this conversation yet."
    chars = sum(len(t.get("user", "")) + len(t.get("assistant", "")) for t in turns)
    agent = data.get("agent")
    lines = [f"{len(turns)} turn(s) remembered, ~{chars} chars of {MAX_CHARS}."]
    if agent:
        lines.append(f"Current agent: {agent.replace('_', ' ')}")
    lines.append("")
    for t in turns[-3:]:
        first = (t.get("user", "").splitlines() or [""])[0]
        lines.append(f"- {first[:70]}")
    return "\n".join(lines)

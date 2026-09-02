#!/usr/bin/env python3
"""Automatic, conservative capture of decisions and preferences from chat.

WHY DETERMINISTIC AND NOT A MODEL CALL

"Save what mattered" is a summarisation task, and the obvious way to do it is
to ask a model to read the exchange and decide. That is exactly what this
does NOT do: a model asked to find "important" things in Felix's own words
will find some, and it is not possible from outside to tell its guesses from
his actual decisions. This instead only ever stores a sentence Felix (or an
engine, relaying him) actually wrote, gated on him having used a phrase that
marks it as one - "remember that", "merk dir", "wichtig:", "we'll go with".
Conservative on purpose: it is fine to miss a decision that was phrased
plainly, it is not fine to invent one.

It also means nothing here ever stores a model's reasoning. There is no
"why" field synthesised from anything - only the sentence as typed, redacted
the same way the event journal is, with where it came from kept alongside it
so a stored line can always be traced back to its conversation.
"""
import json
import os
import re
import threading
from datetime import datetime

import shared_briefing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
STORE_PATH = os.path.join(TASK_RUNNER_DIR, "knowledge", "decisions.jsonl")
MAX_STORED = 500
MAX_ITEM_CHARS = 400
# One exchange should not be able to flood the store - a pasted document full
# of colons would otherwise produce dozens of "matches".
MAX_ITEMS_PER_CALL = 5

_lock = threading.Lock()

# Trigger phrases, EN/DE, that mark a sentence as a decision or a standing
# preference rather than an ordinary remark. Anchored loosely (not to
# sentence-start) because the trigger is as likely to be the middle of a
# sentence ("let's go with option B") as the start of one.
_TRIGGERS = [
    r"remember that", r"don't forget(?: that)?", r"note that", r"noted:",
    r"important:", r"we'?ll go with", r"let'?s go with", r"decided to",
    r"from now on", r"going forward", r"always ", r"never ",
    r"merk dir", r"vergiss nicht", r"wichtig:", r"lass uns .* nehmen",
    r"ich habe entschieden", r"wir nehmen", r"ab jetzt", r"künftig",
]
_TRIGGER_RE = re.compile("|".join(_TRIGGERS), re.I)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\n])\s+")


def extract_conservative(text):
    """-> a short list of sentences from `text` that look like a decision or
    a preference, in the order they appeared. Empty if none do - most
    messages are not decisions, and that is the expected, common result."""
    text = (text or "").strip()
    if not text:
        return []
    found = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        sentence = sentence.strip()
        if not sentence or not _TRIGGER_RE.search(sentence):
            continue
        found.append(sentence[:MAX_ITEM_CHARS])
        if len(found) >= MAX_ITEMS_PER_CALL:
            break
    return found


def _append_rows(rows):
    if not rows:
        return
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with _lock:
        existing = []
        if os.path.exists(STORE_PATH):
            with open(STORE_PATH, encoding="utf-8") as f:
                existing = f.readlines()
        existing.extend(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        existing = existing[-MAX_STORED:]
        tmp = STORE_PATH + ".part"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(existing)
        os.replace(tmp, STORE_PATH)


def save(conversation_id, engine, text=None, source="auto"):
    """Save either an explicit `text` (source="manual", stored verbatim, one
    item) or - when text is None - whatever extract_conservative() finds in
    the conversation's most recent exchange (source="auto", zero or more
    items). -> the list of stored item dicts (possibly empty).

    Source references travel with every item: a saved line that cannot be
    traced back to who said it in which conversation is a line nobody can
    verify later."""
    if text is not None:
        text = shared_briefing.redact(text.strip())[:MAX_ITEM_CHARS]
        if not text:
            return []
        items = [text]
        source = "manual"
    else:
        import conversation_store
        record = conversation_store.read(conversation_id) if conversation_id else None
        if not record:
            return []
        recent = "\n".join(m.get("text", "") for m in record["messages"][-2:])
        items = [shared_briefing.redact(i) for i in extract_conservative(recent)]
        if not items:
            return []

    now = datetime.now().isoformat(timespec="seconds")
    rows = [{"ts": now, "conversation_id": conversation_id, "engine": engine,
             "source": source, "text": item} for item in items]
    _append_rows(rows)
    return rows


def recent(limit=20):
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
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

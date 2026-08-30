#!/usr/bin/env python3
"""Proposals: what the agents want to change, waiting on Felix to say yes.

The trust boundary this whole module exists to enforce: an agent running
unattended can write a *proposal* and nothing else. It has no path from here
into tasks/inbox/. Only an explicit approval - Felix replying to the 20:00
review over Telegram - turns a proposal into a task the worker will execute.

That gate is structural, not a prompt instruction. External_Access_Plan.md
already argued the point for Gmail and it holds identically here: "the send
call is a separate code path that requires an external confirmation signal"
beats "the system prompt tells the model to ask first", because free models
under load demonstrably skip instructions they were given.

Three files, all gitignored runtime state:
  pending.json  - accumulating, appended by proposer runs during the day
  review.json   - the numbered snapshot sent at 20:00; `approve 2` means
                  entry 2 *of that snapshot*, so proposals arriving after
                  the review cannot silently renumber what Felix is looking at
  archive.jsonl - every decided proposal, append-only, so "what did I say no
                  to last week" is answerable

Stdlib only: scripts/ runs under /usr/bin/python3 with no venv packages.
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROPOSALS_DIR = os.path.join(HERE, "proposals")
PENDING_PATH = os.path.join(PROPOSALS_DIR, "pending.json")
REVIEW_PATH = os.path.join(PROPOSALS_DIR, "review.json")
ARCHIVE_PATH = os.path.join(PROPOSALS_DIR, "archive.jsonl")

# An agent marks each proposal with this prefix on its own line. A marker
# beats parsing prose into items: small models number things inconsistently,
# drop bullets, and wrap lines, but they reliably repeat a literal token they
# were shown.
PROPOSAL_RE = re.compile(r"^\s*PROPOSAL:\s*(.+?)\s*$", re.M)

MAX_PROPOSAL_CHARS = 400


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def parse(output):
    """Agent output -> list of proposal strings.

    Falls back to the whole output as a single proposal when no marker is
    present. Losing an agent's day of thinking because it forgot a prefix
    would be a worse failure than showing Felix one unusually long item."""
    found = [m.strip() for m in PROPOSAL_RE.findall(output or "") if m.strip()]
    if found:
        return [p[:MAX_PROPOSAL_CHARS] for p in found]
    text = (output or "").strip()
    if not text:
        return []
    return [text[:MAX_PROPOSAL_CHARS]]


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def add(agent, items, now=None):
    """Append this run's proposals to the pending list."""
    if not items:
        return 0
    pending = load(PENDING_PATH)
    stamp = now or time.strftime("%Y-%m-%d %H:%M")
    for text in items:
        pending.append({"agent": agent or "worker", "text": text, "created": stamp})
    _atomic_write(PENDING_PATH, json.dumps(pending, indent=2, ensure_ascii=False))
    return len(items)


def open_review():
    """Snapshot pending into a numbered review and clear pending.

    Clearing matters: without it, anything Felix declined would reappear in
    tomorrow's review unchanged, every day, until he approved it out of sheer
    attrition. A declined proposal is a decision, and it is recorded in the
    archive rather than re-asked."""
    pending = load(PENDING_PATH)
    _atomic_write(REVIEW_PATH, json.dumps(pending, indent=2, ensure_ascii=False))
    _atomic_write(PENDING_PATH, "[]")
    return pending


def load_review():
    return load(REVIEW_PATH)


def resolve(selection, review=None):
    """'1 3' / 'all' / 'none' -> (chosen, rejected, error_or_None).

    Out-of-range numbers are an error rather than a silent skip: approving
    "1 5" when only 4 exist should say so, not quietly do three-quarters of
    what was asked."""
    review = load_review() if review is None else review
    if not review:
        return [], [], "There is nothing waiting for review."

    text = (selection or "").strip().lower()
    if text in ("none", "no", "skip", "nothing"):
        return [], list(review), None
    if text in ("all", "yes", "everything"):
        return list(review), [], None

    numbers = re.findall(r"\d+", text)
    if not numbers:
        return [], [], "Reply with numbers (e.g. `approve 1 3`), `approve all`, or `approve none`."

    picked = []
    for raw in numbers:
        index = int(raw)
        if not 1 <= index <= len(review):
            return [], [], f"There is no proposal {index} - the review has {len(review)}."
        if index not in picked:
            picked.append(index)

    chosen = [review[i - 1] for i in picked]
    rejected = [p for i, p in enumerate(review, 1) if i not in picked]
    return chosen, rejected, None


def close_review(chosen, rejected, now=None):
    """Archive the decision and clear the review so it can't be approved twice."""
    stamp = now or time.strftime("%Y-%m-%d %H:%M")
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    with open(ARCHIVE_PATH, "a", encoding="utf-8") as f:
        for item in chosen:
            f.write(json.dumps({**item, "decision": "approved", "decided": stamp},
                               ensure_ascii=False) + "\n")
        for item in rejected:
            f.write(json.dumps({**item, "decision": "declined", "decided": stamp},
                               ensure_ascii=False) + "\n")
    _atomic_write(REVIEW_PATH, "[]")


def format_review(review):
    """The 20:00 Telegram message."""
    if not review:
        return ("Nothing proposed today.\n\n"
                "No agent had a change worth making - which is a real answer, "
                "not a failure.")
    lines = [f"Tonight's proposals ({len(review)}) - which should I take?", ""]
    for i, item in enumerate(review, 1):
        who = item.get("agent", "worker").replace("_", " ")
        lines.append(f"{i}. [{who}] {item.get('text','')}")
    lines += ["",
              "Reply `approve 1 3` for the ones you want, "
              "`approve all`, or `approve none`."]
    return "\n".join(lines)

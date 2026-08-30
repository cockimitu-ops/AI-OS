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
  todo.json     - approved human-intervention items, i.e. Felix's own list

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
TODO_PATH = os.path.join(PROPOSALS_DIR, "todo.json")

# An agent marks each proposal with one of these prefixes on its own line. A
# literal marker beats parsing prose into items: small models number things
# inconsistently, drop bullets and wrap lines, but they reliably repeat a
# token they were shown. Two whole words rather than a bracketed variant
# (PROPOSAL[AI]:) for the same reason - brackets are punctuation, and
# punctuation is what small models mangle first.
#
# Bare "PROPOSAL:" still parses, so older schedule files keep working.
PROPOSAL_RE = re.compile(r"^\s*(?:(AI|HUMAN)_)?PROPOSAL:\s*(.+?)\s*$", re.M | re.I)

# Two kinds, and the distinction is operational rather than cosmetic:
#   ai    - the worker can do the whole thing itself. Approving it queues a
#           real task.
#   human - needs Felix: an account, a payment, a publish button, a decision,
#           anything in the physical world. Approving it adds to his list; it
#           is never queued, because a worker handed "publish the Gumroad
#           listing" will either flail or report success it did not achieve.
KINDS = ("ai", "human")
DEFAULT_KIND = "human"

MAX_PROPOSAL_CHARS = 400


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def parse(output):
    """Agent output -> [{"kind": "ai"|"human", "text": str}].

    An unlabelled proposal is treated as human, deliberately. The two failure
    directions are not symmetric: mislabelling human work as AI queues a task
    the worker cannot possibly do and may report as done, while mislabelling
    AI work as human just means Felix reads a line he could have delegated.
    Guess toward the harmless mistake.

    Falls back to the whole output as one proposal when no marker is present
    at all - losing an agent's day of thinking to a forgotten prefix would be
    worse than showing Felix one unusually long item."""
    found = []
    for kind, text in PROPOSAL_RE.findall(output or ""):
        text = text.strip()
        if not text:
            continue
        found.append({"kind": (kind or DEFAULT_KIND).lower(),
                      "text": text[:MAX_PROPOSAL_CHARS]})
    if found:
        return found
    text = (output or "").strip()
    if not text:
        return []
    return [{"kind": DEFAULT_KIND, "text": text[:MAX_PROPOSAL_CHARS]}]


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
    for item in items:
        pending.append({"agent": agent or "worker",
                        "kind": item.get("kind", DEFAULT_KIND),
                        "text": item.get("text", ""),
                        "created": stamp})
    _atomic_write(PENDING_PATH, json.dumps(pending, indent=2, ensure_ascii=False))
    return len(items)


def open_review():
    """Snapshot pending into a numbered review and clear pending.

    Clearing matters: without it, anything Felix declined would reappear in
    tomorrow's review unchanged, every day, until he approved it out of sheer
    attrition. A declined proposal is a decision, and it is recorded in the
    archive rather than re-asked."""
    pending = load(PENDING_PATH)
    # Group AI work before human work in the stored snapshot, so the numbers
    # Felix reads run 1,2,3 within each heading instead of 1,2,5,6 then 3,4,7.
    # Sorting here rather than in format_review keeps the numbering and the
    # snapshot identical - the number he replies with indexes this file.
    # Stable, so each agent's own ordering survives inside its group.
    pending = sorted(pending, key=lambda x: 0 if x.get("kind") == "ai" else 1)
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
    """The 20:00 Telegram message, grouped by who has to do the work.

    Numbering runs continuously across both groups rather than restarting
    per group - `approve 3` has to mean exactly one thing."""
    if not review:
        return ("Nothing proposed today.\n\n"
                "No agent had a change worth making - which is a real answer, "
                "not a failure.")

    numbered = list(enumerate(review, 1))
    ai = [(i, x) for i, x in numbered if x.get("kind") == "ai"]
    human = [(i, x) for i, x in numbered if x.get("kind") != "ai"]

    lines = [f"Tonight's proposals ({len(review)}) - which should I take?"]
    for title, group in (("**AI work** - I build these myself:", ai),
                         ("**Needs you** - I can't do these:", human)):
        if not group:
            continue
        lines += ["", title]
        for i, item in group:
            who = item.get("agent", "worker").replace("_", " ")
            lines.append(f"{i}. [{who}] {item.get('text','')}")

    lines += ["",
              "Reply `approve 1 3` for the ones you want, "
              "`approve all`, or `approve none`."]
    return "\n".join(lines)


# --- Felix's own list: approved work only he can do --------------------------

def add_todos(items, now=None):
    """Approved human-intervention proposals land here rather than in the
    task queue. Without a list they would be approved into nothing - the
    same "shouting into a log" failure the notify directive fixed for
    scheduled tasks."""
    if not items:
        return 0
    todos = load(TODO_PATH)
    stamp = now or time.strftime("%Y-%m-%d")
    for item in items:
        todos.append({"agent": item.get("agent", "worker"),
                      "text": item.get("text", ""), "added": stamp})
    _atomic_write(TODO_PATH, json.dumps(todos, indent=2, ensure_ascii=False))
    return len(items)


def load_todos():
    return load(TODO_PATH)


def complete_todo(selection):
    """-> (done_items, error_or_None). Same numbering discipline as approve:
    an out-of-range number is an error, not a silent partial."""
    todos = load_todos()
    if not todos:
        return [], "Your list is empty."
    numbers = re.findall(r"\d+", selection or "")
    if not numbers:
        return [], "Reply `done 2` with the number you finished."
    picked = sorted({int(n) for n in numbers})
    for index in picked:
        if not 1 <= index <= len(todos):
            return [], f"There is no item {index} - your list has {len(todos)}."
    done = [todos[i - 1] for i in picked]
    remaining = [t for i, t in enumerate(todos, 1) if i not in picked]
    _atomic_write(TODO_PATH, json.dumps(remaining, indent=2, ensure_ascii=False))
    return done, None


def format_todos(todos=None):
    todos = load_todos() if todos is None else todos
    if not todos:
        return "Nothing on your list."
    lines = [f"Your list ({len(todos)}) - only you can do these:"]
    for i, item in enumerate(todos, 1):
        lines.append(f"{i}. {item.get('text','')}  _(added {item.get('added','')})_")
    lines += ["", "Reply `done 2` when one is finished."]
    return "\n".join(lines)

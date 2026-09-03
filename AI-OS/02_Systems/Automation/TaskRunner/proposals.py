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
import urllib.request
import urllib.error
import re
import threading
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

# An optional longer rationale following a proposal line. Kept separate from
# PROPOSAL_RE (one line, strict) because the explanation is prose that can
# wrap - it is captured from the block of text after a proposal up to the
# next proposal marker or a blank line, not by a single-line regex.
EXPLANATION_RE = re.compile(r"^\s*(?:ERKL[ÄA]RUNG|EXPLANATION)\s*:\s*(.+)$", re.M | re.I)
MAX_EXPLANATION_CHARS = 1200

# Markdown-Auszeichnung raus, Text rein.
#
# Ein Vorschlag landet auf einem Telefonbildschirm und in einer
# Telegram-Nachricht, und beide zeigen `**` als das, was es ist: zwei
# Sternchen. Beobachtet 2026-09-03 in Felix' Liste - dort stand wörtlich
# "**Ephemeral Containerized Execution Sandboxes**". Die Modelle darum zu
# bitten hilft nur meistens; hier wird es abgeräumt, statt darauf zu hoffen.
_MD_BOLD = re.compile(r"\*{1,3}(?=\S)(.+?)(?<=\S)\*{1,3}", re.S)
_MD_CODE = re.compile(r"`{1,3}([^`]+)`{1,3}", re.S)
_MD_HEAD = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)
_MD_BULLET = re.compile(r"^\s{0,3}[-*+]\s+", re.M)


def _plain(text):
    """Markdown-Auszeichnung entfernen, Inhalt behalten."""
    if not text:
        return ""
    text = _MD_CODE.sub(r"\1", text)
    text = _MD_BOLD.sub(r"\1", text)
    text = _MD_HEAD.sub("", text)
    text = _MD_BULLET.sub("", text)
    # Übrig gebliebene einzelne Sternchen (unpaarige Auszeichnung) fallen
    # ebenfalls weg - sie tragen nie Bedeutung, nur Rauschen.
    text = text.replace("**", "").replace("`", "")
    return " ".join(text.split())

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


# --- fact checks before a proposal reaches Felix --------------------------
#
# Written after 2026-09-01, when Tech_Scout proposed dropping
# `openrouter-labs/free-tier-tracker` into aios_runner.py's MODEL_CHAIN. The
# repository does not exist. The digest it was told to reason over contained
# exactly one project, an offline point-of-sale starter, and the invention had
# a name, a description, a target file and an integration point - the kind of
# hallucination that reads as competence.
#
# The approval gate could not catch it and could not have: a plausible
# technical claim is not something a human can verify from a Telegram message.
# Felix approved it. Nothing broke, but only because the worker was too weak
# to act on it - which is a coincidence, not a safety property.
#
# So: claims that are cheaply checkable get checked before they are shown.
# Deterministic, no model involved.

GITHUB_REPO_RE = re.compile(r"\b([A-Za-z0-9][\w.-]{0,38})/([A-Za-z0-9][\w.-]{0,99})\b")
# Words that look like owner/repo but are paths, not repositories.
_NOT_A_REPO = {"and", "or", "the", "a", "an", "km", "eur", "usd",
               "input", "output", "yes", "no", "n", "s", "w", "e"}
GITHUB_TIMEOUT = 8


def _looks_like_repo(owner, name):
    if owner.lower() in _NOT_A_REPO or name.lower() in _NOT_A_REPO:
        return False
    # File paths are the main false positive: "scripts/money_board.py",
    # "10_Projects/LocalArbitrage". A real repo name has no dots pointing at
    # a file extension and no vault-style numeric prefix.
    if "." in name and name.rsplit(".", 1)[-1].isalpha() and len(name.rsplit(".", 1)[-1]) <= 4:
        return False
    if owner[:2].isdigit():
        return False
    return True


def github_repo_exists(owner, name, timeout=GITHUB_TIMEOUT):
    """-> True / False / None (could not check).

    None matters: a network failure must not be reported as "does not exist",
    or a flaky connection starts silently dropping real proposals."""
    url = f"https://api.github.com/repos/{owner}/{name}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "AI-OS-proposal-check",
        "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return False if e.code == 404 else None
    except Exception:  # noqa: BLE001 - offline, DNS, rate limit: unknown, not absent
        return None


def check_claims(text, verify=github_repo_exists):
    """-> list of problems found in a proposal's text. Empty means nothing
    checkable was wrong."""
    problems = []
    seen = set()
    text = text or ""
    for match in GITHUB_REPO_RE.finditer(text):
        owner, name = match.groups()
        # A candidate embedded in a longer path is a path, not a repository.
        # "02_Systems/Automation/TaskRunner/webapp/api.py" produced a false
        # "TaskRunner/webapp does not exist" until this check existed - and a
        # false positive here silently deletes a real proposal, which is worse
        # than the hallucination it is meant to catch.
        before = text[:match.start()]
        after = text[match.end():]
        if before.endswith("/") or after.startswith("/"):
            continue
        if not _looks_like_repo(owner, name) or (owner, name) in seen:
            continue
        seen.add((owner, name))
        if verify(owner, name) is False:
            problems.append(f"GitHub-Repo existiert nicht: {owner}/{name}")
    return problems


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
    text_all = output or ""
    matches = list(PROPOSAL_RE.finditer(text_all))
    found = []
    matched_any = bool(matches)
    for i, m in enumerate(matches):
        kind, text = m.group(1), m.group(2)
        text = text.strip()
        if not text:
            continue
        # A "none" answer is a real and preferred outcome for a scheduled
        # agent - Tech_Scout's own prompt says silence beats a weak
        # suggestion. It should never become a reviewable item, which is
        # exactly what happened on 2026-09-01: its correct refusal arrived as
        # proposal number four in Felix's list.
        if _is_refusal(text):
            continue
        item = {"kind": (kind or DEFAULT_KIND).lower(),
                "text": _plain(text)[:MAX_PROPOSAL_CHARS]}
        # Look for an ERKLÄRUNG: block between this proposal and the next one
        # (or the end of the output). Stops at the first blank line so a
        # following proposal's own prose is never swallowed into this one.
        span_end = matches[i + 1].start() if i + 1 < len(matches) else len(text_all)
        between = text_all[m.end():span_end]
        exp_m = EXPLANATION_RE.search(between)
        if exp_m:
            para = between[exp_m.start(1):].split("\n\n", 1)[0]
            explanation = " ".join(line.strip() for line in para.splitlines() if line.strip())
        else:
            # Kein ERKLÄRUNG:-Marker - dann ist die Prosa direkt hinter der
            # Vorschlagszeile die Beschreibung.
            #
            # Beobachtet 2026-09-03: Google antwortete mit einer fetten
            # Überschrift als Vorschlag und dem eigentlichen Inhalt in den
            # Zeilen darunter. Weil nur der Marker gelesen wurde, stand bei
            # Felix eine Überschrift ohne jede Beschreibung. Auf ein Format zu
            # bestehen, das Modelle nur meistens einhalten, heisst die Hälfte
            # der Antwort wegzuwerfen - der Marker bleibt der bevorzugte Weg,
            # aber er ist nicht mehr der einzige.
            para = between.strip().split("\n\n", 1)[0]
            explanation = " ".join(
                line.strip() for line in para.splitlines()
                if line.strip() and not PROPOSAL_RE.match(line))
        explanation = _plain(explanation)
        if explanation:
            item["explanation"] = explanation[:MAX_EXPLANATION_CHARS]
        found.append(item)
    if found:
        return found
    # The fallback exists for output that carries no marker at all - losing an
    # agent's whole run to a forgotten prefix would be worse than one long
    # item. It must NOT fire when markers were present and everything they
    # held was filtered: that turned a correctly-refused "none" back into a
    # reviewable proposal, which is exactly the bug this filtering was added
    # to remove.
    if matched_any:
        return []
    text = (output or "").strip()
    if not text or _is_refusal(text):
        return []
    return [{"kind": DEFAULT_KIND, "text": text[:MAX_PROPOSAL_CHARS]}]


REFUSAL_RE = re.compile(
    r"^\W*(none|keine|nichts|no proposal|kein vorschlag)\b[\s.,;:—-]*",
    re.I)


def _is_refusal(text):
    """Is this an agent declining rather than proposing?

    Matched at the start only, and required to be essentially the whole
    message: "none. the repository X is a POS starter but does not fit" is a
    refusal with reasoning, while a proposal that merely mentions the word
    none somewhere is not."""
    stripped = (text or "").strip()
    m = REFUSAL_RE.match(stripped)
    if not m:
        return False
    remainder = stripped[m.end():].strip()
    # A refusal may explain itself; it may not smuggle in a proposal. If the
    # explanation is long enough to be one, keep it and let Felix decide.
    return len(remainder) < 400


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
        text = item.get("text", "")
        # Checked here rather than at review time: this runs once, when the
        # proposal is written, instead of on every listing - and a proposal
        # that fails a check should never enter the pending list at all, so
        # it cannot be approved by someone scrolling quickly.
        problems = check_claims(text)
        if problems:
            print(f"[!] Vorschlag verworfen ({agent}): {'; '.join(problems)}")
            continue
        pending.append({"agent": agent or "worker",
                        "kind": item.get("kind", DEFAULT_KIND),
                        "text": text,
                        "explanation": item.get("explanation", ""),
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


# The instruction to EXECUTE is explicit, and it has to be. Observed
# 2026-09-01: two approved tasks came back as prose and as another
# AI_PROPOSAL rather than as work. The agents were behaving correctly for
# their own personas - Tech_Scout's prompt says to output only proposal lines
# - so an approved task looked to them like another proposal round. Nothing
# was done, and both were logged as completed.
APPROVED_PREAMBLE = (
    "<!-- notify -->\n"
    "(Approved by Felix from tonight's review.)\n\n"
    "DO THIS NOW. This is not a proposal round - Felix has already approved "
    "it and is expecting the work to be done. Do NOT reply with AI_PROPOSAL "
    "or HUMAN_PROPOSAL; that output is ignored here. Make the actual change, "
    "then report in plain words what you changed and where. If it turns out "
    "to be impossible or the premise is wrong - a file or repository that "
    "does not exist, for instance - say that plainly instead of doing "
    "something adjacent.\n\n")


def dispatch(chosen, inbox=None, agents_module=None, engines_module=None):
    """Turn approved proposals into work. -> how many tasks were queued.

    Lives here rather than in whichever front door happened to approve them.
    It was written inside telegram_bridge.py, which was fine while Telegram
    was the only way to say yes; the web app is a second one, and two copies
    of the rule that decides what the worker is allowed to be handed is
    exactly the kind of duplication that drifts apart quietly.

    Approval branches on who can actually do the work. Queueing a
    human-intervention item would hand the worker something it cannot
    possibly do - "publish the Gumroad listing" - and a free model given an
    impossible task tends to report success rather than refuse. Those go on
    Felix's own list instead.

    engines_module exists for the same reason agents_module does: without it,
    a test that approves an "ai" item has no way to avoid firing a real,
    full-permission engine call. That actually happened (2026-09-02) - a test
    fixture named "Run automated health check diagnostics" reached the real
    Google AI Pro CLI with --dangerously-skip-permissions, because dispatch()
    always imported the live engines module regardless of what the test
    mocked. Costs real quota and, with that flag on, could do real work."""
    import agents as _agents  # local: proposals.py is imported by tools that
    if agents_module is not None:  # have no need for the agent registry
        _agents = agents_module
    import safety_controls
    if engines_module is not None:
        _eng = engines_module
    else:
        try:
            import engines as _eng
        except ImportError:
            import scripts.engines as _eng

    inbox = inbox or os.path.join(HERE, "tasks", "inbox")
    ai_items = [i for i in chosen if i.get("kind") == "ai"]
    human_items = [i for i in chosen if i.get("kind") != "ai"]
    for item in ai_items:
        body = (_agents.directive(item["agent"])
                if _agents.resolve(item.get("agent", "")) else "")
        body += APPROVED_PREAMBLE + f"{item['text']}\n"
        
        allowed = ["claude", "codex", "google-pro"]
        choice = safety_controls.choose_engine(allowed)
        engine_id = choice.engine or "claude"
        
        if _eng.limited(engine_id):
            nxt = _eng.next_engine(engine_id, exclude=["aios"])
            if nxt and nxt in allowed:
                engine_id = nxt

        ticket = _eng.send(engine_id, body, fallback=False)
        # Mutates the same dict `chosen` holds - so whoever called dispatch()
        # with that list (the web app, Telegram) can tell Felix which of the
        # group actually got it, never GLM.
        item["executed_by"] = engine_id
        job_id = ticket.get("job")
        if job_id:
            _escalate_on_failure(engine_id, job_id, body, allowed, item["text"])

    if human_items:
        add_todos(human_items)
    return len(ai_items)


ESCALATIONS_PATH = os.path.join(PROPOSALS_DIR, "escalations.jsonl")
_ESCALATION_POLL_S = 5.0


def _escalate_on_failure(engine_id, job_id, body, allowed, proposal_text, attempted=None):
    """Background watch on one dispatched build. If it fails - not just a
    rate limit, any failure - the next engine in `allowed` picks it up
    automatically. Felix asked for the group (Claude/Codex/Google-Pro) to
    jump in on problems rather than leaving a failed build silent; only when
    every one of the three has failed does it become a todo item, so he
    still hears about it if the whole group struck out.

    Runs in a background thread because `_eng.send` is already fire-and-
    forget - the caller (a web/Telegram request) has returned long before an
    agentic build finishes."""
    attempted = attempted or [engine_id]

    def _watch():
        try:
            import engines as _eng
        except ImportError:
            import scripts.engines as _eng
        deadline = time.time() + 2700  # generous: an agentic build can run long
        res = None
        while time.time() < deadline:
            res = _eng.result(engine_id, job_id, fallback=False, notify=False)
            if res.get("ready"):
                break
            time.sleep(_ESCALATION_POLL_S)
        if res is None or not res.get("ready") or res.get("ok"):
            return  # succeeded, or never finished in time - not a failure to escalate

        remaining = [e for e in allowed if e not in attempted]
        record = {"proposal": proposal_text, "failed_engine": engine_id,
                  "error": (res.get("error") or "")[:400],
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        if not remaining:
            record["outcome"] = "group_exhausted"
            _append_jsonl(ESCALATIONS_PATH, record)
            add_todos([{"agent": "eskalation",
                        "text": f"Alle drei Agenten sind an \"{proposal_text[:200]}\" gescheitert "
                                f"(zuletzt {engine_id}: {record['error']}). Bitte selbst ansehen."}])
            return

        next_engine_id = remaining[0]
        record["outcome"] = f"handed_to_{next_engine_id}"
        _append_jsonl(ESCALATIONS_PATH, record)
        ticket = _eng.send(next_engine_id, body, fallback=False)
        nxt_job = ticket.get("job")
        if nxt_job:
            _escalate_on_failure(next_engine_id, nxt_job, body, allowed, proposal_text,
                                 attempted=attempted + [next_engine_id])

    threading.Thread(target=_watch, daemon=True).start()


def _append_jsonl(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def decide_one(index, approve, now=None):
    """Accept or decline a single proposal by its number. -> (item, error).

    Telegram takes a batch - "approve 1 3" - because typing it out is the
    interaction. A screen with a row per proposal wants the opposite: one
    decision, one tap, and the list is shorter. Both write the same archive
    and both go through dispatch()."""
    review = load_review()
    if not review:
        return None, "Es liegt gerade nichts zur Entscheidung."
    try:
        index = int(index)
    except (TypeError, ValueError):
        return None, "Ungültige Nummer."
    if not 1 <= index <= len(review):
        return None, f"Vorschlag {index} gibt es nicht - es sind {len(review)}."
    item = review[index - 1]
    remaining = [p for i, p in enumerate(review, 1) if i != index]
    stamp = now or time.strftime("%Y-%m-%d %H:%M")
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    with open(ARCHIVE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({**item, "decision": "approved" if approve else "declined",
                            "decided": stamp}, ensure_ascii=False) + "\n")
    # Written before the work is queued: a crash between the two costs a
    # dispatched task that is no longer in the review, which is recoverable.
    # The other order costs a proposal that can be approved twice.
    _atomic_write(REVIEW_PATH, json.dumps(remaining, indent=2, ensure_ascii=False))
    return item, None


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


# --- Safe batch approvals & narrow allowlist --------------------------------
#
# Felix approved batch approvals, but with strict trust boundaries:
# 1. BATCH_DECIDE delegates to the existing verified proposal gate:
#    It archives to archive.jsonl, removes from review.json, and dispatches.
#    It never bypasses verification (proposals still had check_claims() on entry)
#    or explicit approval (the user/caller must decide).
# 2. SAFE ALLOWLIST is strictly opt-in and defaults to empty.
#    It matches only narrow known harmless actions. Arbitrary model text
#    is NEVER auto-approved.
# 3. RECOMMENDED_SAFE_IDS exposes safe candidate indices to caller/UI.

SAFE_ALLOWLIST = []


def configure_safe_allowlist(patterns):
    """Configures the narrow harmless actions allowlist (opt-in only).
    Patterns may be strings (substring match) or re.Pattern regexes.
    Defaults to empty list."""
    global SAFE_ALLOWLIST
    if patterns is None:
        SAFE_ALLOWLIST = []
    elif isinstance(patterns, (list, tuple, set)):
        SAFE_ALLOWLIST = list(patterns)
    else:
        raise ValueError("patterns must be a list, tuple, or set of strings/regexes")
    return list(SAFE_ALLOWLIST)


def get_safe_allowlist():
    """Returns a copy of the current safe allowlist."""
    return list(SAFE_ALLOWLIST)


def is_safe_proposal(item):
    """Determines whether a proposal item matches the configured safe allowlist.
    Returns False when the allowlist is empty (the default).
    Never auto-approves arbitrary text."""
    if not SAFE_ALLOWLIST:
        return False
    text = (item.get("text") if isinstance(item, dict) else str(item)) or ""
    text = text.strip()
    for pattern in SAFE_ALLOWLIST:
        if isinstance(pattern, re.Pattern):
            if pattern.search(text):
                return True
        elif isinstance(pattern, str):
            if pattern.lower() in text.lower():
                return True
    return False


def recommended_safe_ids(review=None):
    """Returns a list of 1-based indices in the review that match the safe allowlist.
    Returns [] when allowlist is empty (default). Does not auto-approve."""
    review = load_review() if review is None else review
    if not review or not SAFE_ALLOWLIST:
        return []
    safe_indices = []
    for i, item in enumerate(review, 1):
        if is_safe_proposal(item):
            safe_indices.append(i)
    return safe_indices


def batch_decide(ids, decision, now=None, inbox=None, agents_module=None, verify_fn=None,
                 engines_module=None):
    """Accept or decline a batch of proposals by their 1-based numbers.

    Delegates to the existing verified proposal gate:
    - Never bypasses verification or approval signal
    - Validates all requested indices; errors out atomically if any index is invalid
    - Verifies references/claims at approval time via check_claims(); aborts if verification fails
    - Avoids partial approval if one item fails verification or validation
    - Writes every decision to archive.jsonl
    - Updates review.json atomically
    - Dispatches approved items to tasks/inbox or Felix's todo list in stable original index order

    -> (decided_items, error_or_None)
    """
    review = load_review()
    if not review:
        return [], "Es liegt gerade nichts zur Entscheidung."

    if isinstance(decision, str):
        dec_norm = decision.strip().lower()
        if dec_norm in ("approve", "approved", "yes", "true", "1"):
            approve = True
        elif dec_norm in ("decline", "declined", "reject", "rejected", "no", "false", "0"):
            approve = False
        else:
            return [], f"Ungültige Entscheidung: {decision!r}. Erwarte 'approve' oder 'decline'."
    else:
        approve = bool(decision)

    if not ids:
        return [], "Keine Vorschlags-IDs angegeben."

    if isinstance(ids, (str, int)):
        ids = [ids]

    parsed_indices = []
    for raw in ids:
        try:
            val = int(raw)
        except (TypeError, ValueError):
            return [], f"Ungültige Vorschlagsnummer: {raw!r}"
        if not 1 <= val <= len(review):
            return [], f"Vorschlag {val} gibt es nicht - es sind {len(review)}."
        if val not in parsed_indices:
            parsed_indices.append(val)

    if not parsed_indices:
        return [], "Keine gültigen Vorschlagsnummern angegeben."

    # Verify claims at actual approval time using existing proposal checks
    if approve:
        v_fn = verify_fn if verify_fn is not None else github_repo_exists
        for idx in parsed_indices:
            item = review[idx - 1]
            text = item.get("text", "")
            problems = check_claims(text, verify=v_fn)
            if problems:
                return [], f"Verifikation für Vorschlag {idx} fehlgeschlagen: {'; '.join(problems)}"

    chosen = [review[i - 1] for i in parsed_indices]
    remaining = [p for i, p in enumerate(review, 1) if i not in parsed_indices]

    stamp = now or time.strftime("%Y-%m-%d %H:%M")
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    with open(ARCHIVE_PATH, "a", encoding="utf-8") as f:
        for item in chosen:
            f.write(json.dumps({**item, "decision": "approved" if approve else "declined",
                                "decided": stamp}, ensure_ascii=False) + "\n")

    _atomic_write(REVIEW_PATH, json.dumps(remaining, indent=2, ensure_ascii=False))

    if approve:
        dispatch(chosen, inbox=inbox, agents_module=agents_module, engines_module=engines_module)

    return chosen, None


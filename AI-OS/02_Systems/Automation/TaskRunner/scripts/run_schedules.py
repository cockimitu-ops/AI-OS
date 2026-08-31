#!/usr/bin/env python3
"""Recurring agent tasks: reads schedules/*.md, enqueues whichever are due.

Runs from a single systemd timer every 10 minutes. Deliberately NOT one
systemd unit per schedule - that would put every new recurring task behind
sudo, and adding one should be as cheap as dropping a Markdown file in a
folder, same as every other thing this vault treats as source of truth.

A schedule file looks exactly like a task file with one extra directive:

    <!-- agent: Business_Development -->
    <!-- schedule: daily 07:30 -->
    Check which TemplateSales products are still unpublished and say so.

Cadence grammar is deliberately tiny - `daily HH:MM`, `weekly <DAY> HH:MM`,
`hourly`. A real cron parser would be more expressive and more ways to be
subtly wrong about what actually runs unattended at 3am.

Times are Europe/Berlin, not the server's UTC - a schedule saying 07:30
should mean 07:30 where Felix is, and should keep meaning it across DST.

Stdlib only (agents.py is stdlib too, so importing it here is safe):
systemd runs this under /usr/bin/python3, which has no venv packages.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, TASK_RUNNER_DIR)
import agents  # noqa: E402  (needs sys.path set first)

SCHEDULES_DIR = os.path.join(TASK_RUNNER_DIR, "schedules")
STATE_PATH = os.path.join(SCHEDULES_DIR, "state.json")
INBOX = os.path.join(
    os.environ.get("AIOS_WORKSPACE", TASK_RUNNER_DIR), "tasks", "inbox")

TZ = ZoneInfo("Europe/Berlin")

SCHEDULE_RE = re.compile(r"^\s*<!--\s*schedule:\s*(.+?)\s*-->\s*\n?", re.I | re.M)
PROPOSE_RE = re.compile(r"^\s*<!--\s*propose\s*-->\s*\n?", re.I | re.M)
MODEL_RE = re.compile(r"^\s*<!--\s*model:\s*(paid|free|quality)\s*-->\s*\n?", re.I | re.M)

DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


# --- parsing: pure -----------------------------------------------------------

def parse_schedule_file(text):
    """-> (cadence_or_None, agent_or_None, propose_bool, instruction).

    Every directive is stripped here and re-emitted by enqueue() rather than
    passed through in the body. That ordering is load-bearing: the worker
    parses its directives anchored to the start of the task, so one left
    sitting after the "(Scheduled task from ...)" line is invisible to it.
    Found live 2026-08-30 - <!-- propose --> was being passed through in the
    body, so both daily planners ran as ordinary tasks and stored nothing."""
    cadence = None
    m = SCHEDULE_RE.search(text or "")
    if m:
        cadence = m.group(1).strip()
        text = text[:m.start()] + text[m.end():]

    propose = False
    m = PROPOSE_RE.search(text or "")
    if m:
        propose = True
        text = text[:m.start()] + text[m.end():]

    # Stripped and re-emitted like every other directive, for the same
    # load-bearing reason: the worker anchors its parsers to the start of the
    # task, so a <!-- model: --> left sitting in the body is invisible to it
    # and the schedule silently runs on the free chain it asked not to use.
    model = None
    m = MODEL_RE.search(text or "")
    if m:
        model = m.group(1).strip().lower()
        text = text[:m.start()] + text[m.end():]

    agent, instruction = agents.parse_directive(text)
    return cadence, agent, propose, model, instruction


def next_due_after(cadence, reference):
    """The first moment at or before `reference` that this cadence should
    have fired, or None if the cadence is unparseable.

    Returning the *scheduled* moment rather than a bare "is it due" boolean
    is what makes catch-up correct: comparing that moment against the last
    run tells you whether this occurrence has already happened, so a run
    missed because the server was off fires once on the next tick instead of
    being skipped or fired repeatedly."""
    parts = (cadence or "").lower().split()
    if not parts:
        return None

    if parts[0] == "hourly" and len(parts) == 1:
        return reference.replace(minute=0, second=0, microsecond=0)

    if parts[0] == "daily" and len(parts) == 2:
        hhmm = _parse_hhmm(parts[1])
        if hhmm is None:
            return None
        hour, minute = hhmm
        today = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return today if today <= reference else today - timedelta(days=1)

    if parts[0] == "weekly" and len(parts) == 3:
        weekday = DAYS.get(parts[1][:3])
        hhmm = _parse_hhmm(parts[2])
        if weekday is None or hhmm is None:
            return None
        hour, minute = hhmm
        candidate = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # Walk back to the most recent occurrence of that weekday-and-time.
        delta = (candidate.weekday() - weekday) % 7
        candidate -= timedelta(days=delta)
        return candidate if candidate <= reference else candidate - timedelta(days=7)

    return None


def _parse_hhmm(token):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", token)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def is_due(cadence, last_run_iso, now):
    """True when this cadence's most recent scheduled moment hasn't run yet."""
    scheduled = next_due_after(cadence, now)
    if scheduled is None:
        return False
    if not last_run_iso:
        return True
    try:
        last_run = datetime.fromisoformat(last_run_iso)
    except ValueError:
        return True  # unreadable state should re-run, not silently never run
    return last_run < scheduled


# --- state + enqueue ---------------------------------------------------------

def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    os.makedirs(SCHEDULES_DIR, exist_ok=True)
    tmp = STATE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, STATE_PATH)


def enqueue(agent, instruction, source_name, propose=False, model=None):
    """Same atomic .part-then-rename the other producers use - the worker
    globs tasks/inbox/*.md every two seconds and would happily pick up a
    half-written file."""
    os.makedirs(INBOX, exist_ok=True)
    # The schedule's own name is part of the filename, not just a timestamp.
    # Second-resolution stamps collide the moment two schedules come due in
    # the same tick - which is the normal case here, not an edge case: this
    # runner walks every schedule in one pass. Observed live 2026-08-30,
    # daily_revenue_plan and daily_system_plan both produced
    # "task_sched_20260830_164116.md" and the second silently overwrote the
    # first, while state.json recorded both as having run - so the lost one
    # would not retry until the next day, having never executed at all.
    stamp = time.strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", os.path.splitext(source_name)[0])[:40]
    filename = f"task_sched_{stamp}_{safe}.md"
    path = os.path.join(INBOX, filename)
    tmp = f"{path}.part"
    # <!-- notify --> so the result reaches Telegram: nothing is polling for
    # a scheduled task's log the way dispatch_task.py/telegram_bridge.py do
    # for an interactive one, so without it the answer would go unread.
    # Directive order matters: the worker reads agent, then notify, then
    # propose, each anchored to the start of what remains.
    header = agents.directive(agent) if agent else ""
    # Immediately after the agent directive: that is the order aios_runner
    # parses them in, each anchored to the start of what is left.
    header += agents.model_directive(model)
    header += "<!-- notify -->\n"
    if propose:
        header += "<!-- propose -->\n"
    body = f"{header}(Scheduled task from {source_name}.)\n\n{instruction}\n"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)
    return filename


def run(now=None):
    """-> list of (schedule_name, status) for logging. Never raises on one
    bad schedule file: a typo in one must not stop the others from firing."""
    now = now or datetime.now(TZ)
    state = load_state()
    results = []

    try:
        files = sorted(f for f in os.listdir(SCHEDULES_DIR) if f.endswith(".md"))
    except OSError:
        return results

    for name in files:
        try:
            with open(os.path.join(SCHEDULES_DIR, name), encoding="utf-8") as f:
                (cadence, agent, propose, model,
                 instruction) = parse_schedule_file(f.read())
        except OSError as e:
            results.append((name, f"unreadable: {e}"))
            continue

        if not cadence:
            results.append((name, "skipped: no schedule directive"))
            continue
        if not instruction:
            results.append((name, "skipped: no instruction"))
            continue
        if next_due_after(cadence, now) is None:
            results.append((name, f"skipped: unparseable cadence {cadence!r}"))
            continue
        if not is_due(cadence, state.get(name), now):
            results.append((name, "not due"))
            continue

        queued = enqueue(agent, instruction, name, propose=propose,
                         model=model)
        state[name] = now.isoformat()
        results.append((name, f"queued as {queued}"))

    save_state(state)
    return results


def main():
    for name, status in run():
        print(f"{name}: {status}")


if __name__ == "__main__":
    main()

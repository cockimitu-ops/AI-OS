#!/usr/bin/env python3
"""Tracks real USD spend against a paid model tier and enforces a monthly cap.

Exists because of what MODEL_CHAIN's history already documents: on 2026-08-30
a single stuck call blocked the worker for 101 minutes (see aios_runner.py's
ATTEMPT_TIMEOUT_S comment), and systemd reported the worker healthy the whole
time. Every model tried up to now is free, so incidents like that cost time,
not money. A paid tier changes the failure class - this is what keeps a bug
in an unattended, Restart=always service from becoming a bill instead of
just a delay.

The cap fails closed: once the month's spend reaches the budget, the paid
tier is skipped before the call, never billed past the limit and refunded
after. A skipped call degrades the task to whatever the chain does without
it (its next entry, or the "all models failed" message) - a failed task is
always the safer outcome than an uncapped one.

Pure ledger arithmetic only - no network, no litellm. aios_runner.py (which
already imports litellm for cost calculation) is the only real caller, but
this stays importable and unit-testable without the venv, the same as every
other module in scripts/.
"""
import json
import os
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "spend", "openrouter_ledger.json")

# Roughly EUR 5.50 at the exchange rate checked 2026-08-31. Overridable via
# OPENROUTER_MONTHLY_BUDGET_USD in .env - this is only the default when that
# is unset, not a ceiling on what Felix can configure.
DEFAULT_MONTHLY_BUDGET_USD = 6.0


def month_key(now=None):
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


def load_ledger(path=None):
    """path=None resolves LEDGER_PATH at CALL time, not at function-definition
    time. `path=LEDGER_PATH` in the signature would bind the module-global's
    value once, when this function object is created - reassigning
    spend_guard.LEDGER_PATH afterward (a test isolating its own ledger file,
    or any future runtime reconfiguration) would then silently do nothing,
    and every call would keep hitting the original path regardless. Exactly
    that happened live while writing this module's own tests: a test that
    reassigned LEDGER_PATH still wrote through to the real path in the repo,
    dropping a stray $0.0005 into it."""
    path = path or LEDGER_PATH
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save(ledger, path=None):
    path = path or LEDGER_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def month_spent(ledger, month=None):
    """Pure: how much of the given month has already been spent. Takes an
    already-loaded ledger rather than a path, so budget decisions are
    testable without touching a filesystem."""
    return ledger.get(month or month_key(), 0.0)


def can_spend(ledger, budget_usd, month=None):
    """Whether the paid tier may be tried AT ALL this month.

    Checked before the call, never after - this cap exists to prevent a call
    from happening, not to true up the bill once it already has."""
    return month_spent(ledger, month) < budget_usd


def calls_path(path=None):
    """Where the per-call log lives, derived from the ledger's own location.

    Derived rather than a separate constant so a test that redirects the
    ledger to a temporary directory redirects this with it - the alternative
    is a test that quietly appends to the real log while checking a fake
    ledger, which is the same class of bug the load_ledger() docstring
    already describes."""
    return os.path.join(os.path.dirname(path or LEDGER_PATH),
                        "openrouter_calls.jsonl")


def record_spend(usd, path=None, month=None, model=None, task=None):
    """Adds a completed call's cost to the current month's total.

    Always additive. The month resets itself: once month_key() rolls over,
    a fresh key starts at 0 with no cleanup step required, and old months
    stay in the file as a small permanent record rather than being pruned -
    at one float per month this never becomes a size problem.

    Also appends one line to the per-call log. The monthly total alone can
    say "you spent $4.50" but never "on what" - and a cost display that
    cannot answer that is a number to worry about rather than one to act on.
    Appending is best-effort: a failure to write the log must never lose the
    ledger entry, which is what the budget cap actually depends on."""
    path = path or LEDGER_PATH
    ledger = load_ledger(path)
    key = month or month_key()
    ledger[key] = round(ledger.get(key, 0.0) + max(usd, 0.0), 6)
    _save(ledger, path)
    try:
        line = json.dumps({"ts": (datetime.now(timezone.utc)
                                  .isoformat(timespec="seconds")),
                           "usd": round(max(usd, 0.0), 6),
                           "model": model, "task": (task or "")[:120]},
                          ensure_ascii=False)
        with open(calls_path(path), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    return ledger[key]


def recent_calls(limit=50, path=None):
    """The last `limit` logged calls, newest first."""
    try:
        with open(calls_path(path), encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def status_line(budget_usd, path=None, month=None):
    """One line for the periodic status update. Absent-ledger and
    zero-spend both read the same way - "$0.00 of $6.00" - since a paid
    tier that has simply never fired yet is not an error worth flagging."""
    spent = month_spent(load_ledger(path), month)
    return f"OpenRouter bezahlt: ${spent:.2f} von ${budget_usd:.2f} diesen Monat"

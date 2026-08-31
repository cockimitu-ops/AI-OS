#!/usr/bin/env python3
"""The single source of truth for 'what earns money next, and who must act'.

Why this exists: an audit of the vault found ~17 finished-but-not-earning
deliverables scattered across project files, and two daily LLM planners
(daily_revenue_plan, daily_system_plan) burning a full Open Interpreter loop
every night to re-derive a list that barely changes. The blocked-on-human
inventory is *known* - it does not need a model to rediscover it at token
cost each evening; it needs to be written down once and kept honest.

So this is a deterministic board: a hand-maintained list of concrete revenue
actions, each tagged with who can do it (AI vs Felix), euros-at-stake, and
minutes-of-human-time. It renders for zero tokens and never hallucinates a
status. The LLM planners still run for genuinely NEW ideas - but the standing
"here is what's already built and waiting" list comes from here.

Live signals are folded in where they exist and are cheap: whether the two
remaining TemplateSales products are still unpublished (contacted/ledger
files), how many DMARC letters are queued vs sent, sniper activity. Anything
that can be checked from a state file is; the rest is declared.

Stdlib only.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)

# Each item: (who, action, euros_soon, human_minutes, note)
# who: "felix" = only Felix can do it; "ai" = the worker can; "done" = shipped.
# euros_soon is a rough "money reachable if this is done and it works", used
# only to sort - it is not a forecast. Ordered by the audit's own findings.
#
# This list is the durable record. When something ships, flip its `who` to
# "done" with a date rather than deleting it - same record-the-change
# convention the rest of the vault follows.
BOARD = [
    ("felix", "DMARC outreach: fill OUTREACH_SENDER_* in .env, print a 25-letter batch (scripts/outreach.py), post them", 249, 40,
     "534 mailable leads ready. First postal batch ~24 EUR. One sale = 249 EUR. The single biggest new revenue lever."),
    ("felix", "Publish the 2 remaining TemplateSales products (Pricing Teardown 29, Retention Engineering 39) on Gumroad", 68, 45,
     "All assets written incl. cover.png. ~20 min each. Moat Blueprint already live."),
    ("felix", "Gewerbeanmeldung + ELSTER (required before buy-to-resell earns legally)", 0, 60,
     "Gates LocalArbitrage revenue. 22-112 EUR fee. Blocks nothing else."),
    ("felix", "Attach the finished Omni Shield sample PDF to the live Fiverr gig", 30, 10,
     "Gig live since 2026-08-27, no order yet. Sample exists in QuickTurnaroundGigs/_infra/."),
    ("felix", "Act on Kleinanzeigen sniper Telegram alerts: inspect, buy, flip", 50, 0,
     "Sniper live. 250 EUR allocated, 0 deployed. Each flip ~50 EUR, ~15-25 EUR/hr."),
    ("felix", "Create the 45 EUR Validation Stack bundle listing (needs the 2 singles live first)", 45, 10,
     "Copy already written. Gated on the two products above being published."),
    ("felix", "List the Moat free lead-magnet as a 0 EUR Gumroad product for email capture", 0, 10,
     "Complete. Turns traffic into an email list that feeds every later product."),
    ("felix", "Verify Gumroad SEPA payout is set up", 0, 10,
     "Without it a sale earns nothing. One-time."),
    ("ai", "Draft/refine DMARC letter copy and per-provider variants as response data comes in", 0, 0,
     "outreach.py renders these; the worker can improve the template between batches."),
    ("ai", "German-language security content (leg 3) as lead-gen for DMARC outreach", 0, 0,
     "Planned, not started. The security-content pivot after Horror."),
]


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def live_signals():
    """Cheap, real state folded onto the board. Never raises - a missing file
    just means that signal is unknown, not that the board is broken."""
    signals = {}
    contacted = _load(os.path.join(TASK_RUNNER_DIR, "outreach", "contacted.json"))
    signals["letters_sent"] = len(contacted)
    results = _load(os.path.join(TASK_RUNNER_DIR, "prospects", "results.json"))
    signals["leads_qualified"] = sum(1 for r in results.values() if r.get("score", 0) >= 6)
    return signals


def felix_actions(board=BOARD):
    return [i for i in board if i[0] == "felix"]


def render(board=BOARD, top=None):
    signals = live_signals()
    actions = sorted(felix_actions(board), key=lambda i: -i[2])
    if top:
        actions = actions[:top]
    lines = ["GELD-BOARD — was Felix tun muss (nach Ertrag sortiert):"]
    for _, action, euros, minutes, _note in actions:
        tag = f"~{euros} EUR" if euros else "Basis"
        lines.append(f"  • [{tag}, {minutes}min] {action}")
    if signals.get("letters_sent"):
        lines.append(f"  (DMARC: {signals['letters_sent']} Briefe raus, "
                     f"{signals['leads_qualified']} Leads im Bestand)")
    elif signals.get("leads_qualified"):
        lines.append(f"  (DMARC: 0 Briefe raus, {signals['leads_qualified']} Leads bereit)")
    return "\n".join(lines)


def brief_section(board=BOARD, top=3):
    """Compact form for the morning brief / status update - the top human
    actions only, since the full board is a lot to read four times a day."""
    actions = sorted(felix_actions(board), key=lambda i: -i[2])[:top]
    if not actions:
        return None
    lines = ["Top Geld-Moves:"]
    for _, action, euros, minutes, _ in actions:
        tag = f"~{euros}EUR" if euros else "Basis"
        short = action if len(action) <= 70 else action[:67] + "..."
        lines.append(f"  • [{tag}/{minutes}min] {short}")
    return "\n".join(lines)


if __name__ == "__main__":
    if "--brief" in sys.argv:
        print(brief_section() or "(no actions)")
    else:
        print(render())

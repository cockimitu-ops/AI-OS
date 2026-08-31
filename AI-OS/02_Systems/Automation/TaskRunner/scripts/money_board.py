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
#      "felix-first" = Felix, AND it gates the rows under it. Sorts to the top
#      regardless of euros: a legally-required step that earns 0 EUR by itself
#      still has to be read before the step whose money it unblocks.
# euros_soon is a rough "money reachable if this is done and it works", used
# only to sort - it is not a forecast. Ordered by the audit's own findings.
#
# This list is the durable record. When something ships, flip its `who` to
# "done" with a date rather than deleting it - same record-the-change
# convention the rest of the vault follows.
BOARD = [
    ("felix", "DMARC outreach: print a 25-letter batch (scripts/outreach.py), post them", 249, 40,
     "OUTREACH_SENDER_* was still unset when this row was written; it is filled in "
     ".env since 2026-08-31, so the only step left is printing and posting. The "
     "mailable-lead count is a live signal, not restated here - a hand-typed copy "
     "of it is exactly what goes stale."),
    ("felix", "Publish the 2 remaining TemplateSales products (Pricing Teardown 29, Retention Engineering 39) on Gumroad", 68, 45,
     "All assets written incl. cover.png. ~20 min each. Moat Blueprint already live."),
    ("felix-first", "Gewerbeanmeldung + ELSTER - required BEFORE taking the first EUR from ANY paying customer", 0, 60,
     "Gates both LocalArbitrage AND DMARC outreach revenue - not LocalArbitrage-only, "
     "as an earlier version of this board wrongly scoped it. Registration is legally "
     "due at the START of a commercial activity, not after a first sale. If a DMARC "
     "letter gets a yes before this is done, wait to invoice until it is. 22-112 EUR fee."),
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


def _flip_stats():
    """Reads Transaction_Log.md's own table via flip_log.py - no separate
    copy of that data kept here. Returns None if flip_log can't be imported
    or the file can't be read, so a LocalArbitrage-unrelated board render
    never breaks because of it."""
    try:
        sys.path.insert(0, SCRIPT_DIR)
        import flip_log
        rows = flip_log.read_log()
    except Exception:  # noqa: BLE001 - this signal is optional, never fatal
        return None
    open_rows = [r for r in rows if not r.get("Sold €")]
    capital_tied_up = sum(
        (flip_log.parse_num(r["Buy €"]) or 0) + (flip_log.parse_num(r["Repair €"]) or 0)
        for r in open_rows)
    return {"open": len(open_rows), "capital_tied_up": round(capital_tied_up, 2)}


def live_signals():
    """Cheap, real state folded onto the board. Never raises - a missing file
    just means that signal is unknown, not that the board is broken."""
    signals = {}
    contacted = _load(os.path.join(TASK_RUNNER_DIR, "outreach", "contacted.json"))
    signals["letters_sent"] = len(contacted)
    results = _load(os.path.join(TASK_RUNNER_DIR, "prospects", "results.json"))
    qualified = [d for d, r in results.items() if r.get("score", 0) >= 6]
    signals["leads_qualified"] = len(qualified)
    # Qualified is not mailable: the audit scores a domain, the postal address
    # comes from the OSM record in domains.json, and only the overlap can
    # actually receive a letter. Reporting the larger number as if it were
    # the mailable one would overstate the batch by ~125 leads.
    domains = _load(os.path.join(TASK_RUNNER_DIR, "prospects", "domains.json"))
    signals["leads_mailable"] = sum(
        1 for d in qualified if domains.get(d, {}).get("address"))
    signals["flips"] = _flip_stats()
    return signals


def felix_actions(board=BOARD):
    return [i for i in board if i[0].startswith("felix")]


def _sort_key(item):
    return (0 if item[0] == "felix-first" else 1, -item[2])


def sorted_actions(board=BOARD, top=None):
    """The board's one canonical order: gating rows first, then by euros.

    Every caller goes through this. It used to be a `sorted(..., key=-euros)`
    duplicated in three places, and the copy that was missing it was a real
    bug - so the ordering rule lives in exactly one function now. Sorting on
    euros alone had its own honesty problem: the Gewerbeanmeldung is worth
    0 EUR on its own and sank to the bottom, directly under the DMARC letters
    whose income it legally gates. Read top-down, the board told Felix to
    mail first and register afterwards."""
    actions = sorted(felix_actions(board), key=_sort_key)
    return actions[:top] if top else actions


def render(board=BOARD, top=None):
    signals = live_signals()
    actions = sorted_actions(board, top=top)
    lines = ["GELD-BOARD — was Felix tun muss (Pflicht-Schritt zuerst, dann nach Ertrag):"]
    for who, action, euros, minutes, _note in actions:
        tag = "ZUERST" if who == "felix-first" else (
            f"~{euros} EUR" if euros else "Basis")
        lines.append(f"  • [{tag}, {minutes}min] {action}")
    if signals.get("leads_qualified"):
        lines.append(f"  (DMARC: {signals.get('letters_sent', 0)} Briefe raus, "
                     f"{signals['leads_qualified']} Leads qualifiziert, "
                     f"{signals.get('leads_mailable', 0)} davon mit Postadresse)")
    flips = signals.get("flips")
    if flips and flips["open"]:
        lines.append(f"  (Flips: {flips['open']} offen, "
                     f"{flips['capital_tied_up']:.0f} EUR Kapital gebunden)")
    return "\n".join(lines)


def brief_section(board=BOARD, top=3):
    """Compact form for the morning brief / status update - the top human
    actions only, since the full board is a lot to read four times a day."""
    actions = sorted_actions(board, top=top)
    if not actions:
        return None
    lines = ["Top Geld-Moves:"]
    for who, action, euros, minutes, _ in actions:
        tag = "ZUERST" if who == "felix-first" else (
            f"~{euros}EUR" if euros else "Basis")
        short = action if len(action) <= 70 else action[:67] + "..."
        lines.append(f"  • [{tag}/{minutes}min] {short}")
    return "\n".join(lines)


if __name__ == "__main__":
    if "--brief" in sys.argv:
        print(brief_section() or "(no actions)")
    else:
        print(render())

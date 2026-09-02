#!/usr/bin/env python3
"""Is each saved search still actually working?

WHY THIS EXISTS

On 2026-09-01 all five Kleinanzeigen watches had gone completely blind. The
site had restyled and every CSS-class regex missed, so each run parsed zero
listings - and the run reported success, because fetching worked. The Today
screen said "0 Funde insgesamt", which is exactly what a slow market looks
like. Nothing was broken loudly enough to notice.

The sniper does now print a failure when a watch parses nothing, but that
line lives in a journal nobody reads and vanishes on the next run. What was
missing is memory: a watch that has returned nothing for three days is a
different fact from a watch that returned nothing this morning, and only one
of them is a market.

WHAT IT RECORDS

One row per watch, updated on every run: when it last parsed anything, how
many consecutive runs have come back empty, and a bounded daily history. From
that comes a status:

    ok        parsed listings on its most recent run
    quiet     empty, but not for long enough to mean anything
    blind     empty for BLIND_AFTER runs in a row - the scraper, not the market
    stale     has not run at all in STALE_AFTER_HOURS

"blind" is the one that matters. It is the state the whole tool was in for an
unknown number of days.

Pure state handling and arithmetic, no network - the sniper feeds it, the
daily check reads it. Stdlib only.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
WATCHES_DIR = os.path.join(TASK_RUNNER_DIR, "watches")
HEALTH_PATH = os.path.join(WATCHES_DIR, "health.json")

# Three empty runs in a row. One is a market, two is a quiet morning, three
# against a site that carries thousands of listings is a parser that has
# stopped parsing. Deliberately not one: a false "your scraper is broken"
# every quiet Sunday teaches the same lesson the false alerts did.
BLIND_AFTER = 3
# A watch that has not run at all. The sniper is on a timer; if a watch has
# not been touched in this long, something upstream stopped rather than
# something in the parser.
STALE_AFTER_HOURS = 26
# Days of per-day history kept per watch. Enough to see a pattern, small
# enough that the file stays a file.
HISTORY_DAYS = 30


def _now():
    return datetime.now(timezone.utc)


def load(path=None):
    try:
        with open(path or HEALTH_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(data, path=None):
    path = path or HEALTH_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)


def record(watch, listings, matches=0, path=None, now=None):
    """One watch's outcome from one run. -> its updated row.

    Called by the sniper for every watch it touches, including the ones that
    came back empty - especially those."""
    now = now or _now()
    data = load(path)
    row = data.get(watch) or {}
    day = now.date().isoformat()

    row["last_run"] = now.isoformat()
    row["runs"] = row.get("runs", 0) + 1
    row["listings_total"] = row.get("listings_total", 0) + int(listings)
    row["matches_total"] = row.get("matches_total", 0) + int(matches)
    if listings:
        row["last_ok"] = now.isoformat()
        row["last_listings"] = int(listings)
        row["consecutive_zero"] = 0
    else:
        row["consecutive_zero"] = row.get("consecutive_zero", 0) + 1

    history = {k: v for k, v in (row.get("history") or {}).items()}
    entry = history.get(day) or {"runs": 0, "listings": 0, "matches": 0, "zero": 0}
    entry["runs"] += 1
    entry["listings"] += int(listings)
    entry["matches"] += int(matches)
    if not listings:
        entry["zero"] += 1
    history[day] = entry
    # Pruned relative to the newest day the history actually contains, not to
    # the clock of whichever call happens to be running. Those are the same
    # thing in production and not in a test that walks backwards through time
    # - and an ordering assumption that only holds when the clock is
    # monotonic is one that will eventually be wrong after a reboot or a
    # timezone change.
    newest = max(history)
    cutoff = (datetime.fromisoformat(newest).date()
              - timedelta(days=HISTORY_DAYS)).isoformat()
    row["history"] = {k: v for k, v in history.items() if k >= cutoff}

    data[watch] = row
    save(data, path)
    return row


def status_of(row, now=None):
    """-> "ok" | "quiet" | "blind" | "stale" | "unknown"."""
    if not row or not row.get("last_run"):
        return "unknown"
    now = now or _now()
    try:
        last = datetime.fromisoformat(row["last_run"])
    except ValueError:
        return "unknown"
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if (now - last) > timedelta(hours=STALE_AFTER_HOURS):
        return "stale"
    zero = row.get("consecutive_zero", 0)
    if zero >= BLIND_AFTER:
        return "blind"
    if zero:
        return "quiet"
    return "ok"


def report(path=None, now=None):
    """Every watch, worst first. -> a list of rows ready to render."""
    now = now or _now()
    data = load(path)
    order = {"blind": 0, "stale": 1, "quiet": 2, "ok": 3, "unknown": 4}
    out = []
    for watch, row in data.items():
        state = status_of(row, now)
        last_ok = row.get("last_ok")
        hours = None
        if last_ok:
            try:
                seen = datetime.fromisoformat(last_ok)
                if seen.tzinfo is None:
                    seen = seen.replace(tzinfo=timezone.utc)
                hours = round((now - seen).total_seconds() / 3600, 1)
            except ValueError:
                pass
        out.append({
            "watch": watch,
            "status": state,
            "consecutive_zero": row.get("consecutive_zero", 0),
            "last_run": row.get("last_run"),
            "last_ok": last_ok,
            "hours_since_ok": hours,
            "last_listings": row.get("last_listings"),
            "runs": row.get("runs", 0),
            "listings_total": row.get("listings_total", 0),
            "matches_total": row.get("matches_total", 0),
            "days": sorted(row.get("history", {}).items(), reverse=True)[:14],
        })
    out.sort(key=lambda r: (order.get(r["status"], 9), r["watch"]))
    return out


def problems(rows=None, path=None, now=None):
    """Only the ones worth waking someone for."""
    rows = report(path, now) if rows is None else rows
    return [r for r in rows if r["status"] in ("blind", "stale")]


def format_report(rows=None, path=None, now=None):
    """The daily message. Says nothing at length when nothing is wrong."""
    rows = report(path, now) if rows is None else rows
    if not rows:
        return ("Sniper-Check: noch keine Daten - der Sniper hat seit dem "
                "Einbau der Prüfung nicht gelaufen.")
    bad = [r for r in rows if r["status"] in ("blind", "stale")]
    if not bad:
        total = sum(r["last_listings"] or 0 for r in rows)
        return (f"Sniper-Check: alle {len(rows)} Suchen liefern Ergebnisse "
                f"({total} Anzeigen im letzten Durchlauf).")
    lines = [f"Sniper-Check: {len(bad)} von {len(rows)} Suchen liefern nichts."]
    for row in bad:
        if row["status"] == "stale":
            lines.append(f"• {row['watch']}: läuft gar nicht mehr "
                         f"(zuletzt {(row['last_run'] or '?')[:16]})")
        else:
            since = (f"seit {row['hours_since_ok']:.0f}h"
                     if row["hours_since_ok"] is not None else "seit Beginn")
            lines.append(f"• {row['watch']}: {row['consecutive_zero']} Läufe "
                         f"ohne eine einzige Anzeige, {since}")
    lines.append("")
    lines.append("Das ist fast immer der Parser, nicht der Markt - "
                 "Kleinanzeigen hat am 1.9. schon einmal das Layout geändert.")
    return "\n".join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--notify", action="store_true",
                    help="send a Telegram message when something is blind")
    args = ap.parse_args(argv)
    rows = report()
    print(format_report(rows))
    if args.notify and problems(rows):
        try:
            import kleinanzeigen_sniper as sniper
            sniper.send_telegram(format_report(rows))
        except Exception as e:  # noqa: BLE001 - a failed notification must not
            print(f"[!] Telegram: {e}")  # turn a health check into an outage
    return 1 if problems(rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())

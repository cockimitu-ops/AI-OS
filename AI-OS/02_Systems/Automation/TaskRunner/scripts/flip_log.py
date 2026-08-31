#!/usr/bin/env python3
"""Logs LocalArbitrage flips and computes ROI/EUR-per-hour per entry.

Reads and writes 10_Projects/LocalArbitrage/Transaction_Log.md's own Markdown
table DIRECTLY - it does not keep a separate JSON ledger that then "syncs" to
that file. Two copies of the same record drifting apart is the exact bug
class an earlier audit of this vault found repeatedly (a project's own README
saying one thing, an _infra file saying another, neither corrected). The
vault's stated architecture is "Markdown is the source of truth" - this tool
takes that literally rather than working around it.

The schema, the ROI philosophy, and the fuel-cost framing all come from this
project's own docs, not invented here:

  - Valuation_Method.md: "AI does not estimate resale prices. Sold listings
    do." This tool never guesses a resale price - it only records what
    Felix already decided and computes arithmetic on it.
  - Valuation_Method.md: "If EUR/hour comes out below what your time is
    otherwise worth, it's a NO regardless of the margin looking nice in
    percentage terms. A 100% markup on a EUR12 item is still EUR12." So
    EUR/hour is the primary indicator here; ROI% is reported too (the ask
    was explicitly for an ROI indicator) but never used alone to rank flips.
  - Transaction_Log.md: "Record failed buys too... A log of only wins
    teaches nothing." `report` shows losers as prominently as winners.

Stdlib only, matching every other script in this folder.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
VAULT_ROOT = os.path.normpath(os.path.join(TASK_RUNNER_DIR, "..", "..", ".."))
LOG_PATH = os.path.join(VAULT_ROOT, "10_Projects", "LocalArbitrage", "Transaction_Log.md")

COLUMNS = ["#", "Date", "Item", "Category", "Buy €", "Distance km", "Repair €",
           "List €", "Sold €", "Days to sell", "Hours", "Net €", "€/hour", "Notes"]

# Distance in the log (and in kleinanzeigen_sniper's own alerts) is one-way,
# the way Kleinanzeigen itself displays it ("9 km", "ca. 30 km"). A flip is a
# round trip, so fuel is 2x that. EUR/km is a rough all-in estimate (fuel +
# wear), not just pump price - adjust with --fuel-per-km if it's off for your
# car; nothing here hardcodes it beyond this default.
DEFAULT_FUEL_PER_KM = 0.25

# The README's own honest-economics section: "roughly EUR15-25/hour... that
# is genuinely better than the Fiverr gig's effective rate". Thresholds for
# the at-a-glance label below are anchored to that stated range, not invented.
LABEL_THRESHOLDS = (
    (20.0, "GUT"),   # at/above the top of the README's own stated range
    (10.0, "OK"),    # inside or near the stated range
    (None, "SCHWACH"),  # below it - Valuation_Method's "it's a NO" territory
)

# Captures the header+separator as group 1, then ONLY consecutive lines that
# are themselves full table rows ("| ... |") as group 2. Deliberately NOT
# "everything up to the next ## heading" - an earlier version used that and
# it silently swallowed the "Record failed buys too" paragraph (prose sitting
# between the table and the next heading, with no ## of its own in between)
# into the table body, which parse_table then discards because it does not
# start with "|". Caught by testing against a scratch copy and diffing every
# non-table line before ever running this on the real vault file - exactly
# the check that earns its keep.
TABLE_HEADER_RE = re.compile(
    r'(\| # \| Date \|.*?\|\n\|[-|\s]+\|\n)((?:\|.*\|\n?)*)')


def fmt_num(x):
    """None/blank stays blank in the table; a real number renders without a
    trailing .0 for whole euros, since the existing table's placeholder row
    is entirely blank cells and mixing in visual noise for zero decimals
    would look like a formatting regression, not real data."""
    if x is None or x == "":
        return ""
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return f"{x:.2f}" if isinstance(x, float) else str(x)


def parse_num(cell):
    cell = (cell or "").strip().replace("€", "").replace(",", ".")
    if not cell or cell.startswith("*"):
        return None
    try:
        return float(cell)
    except ValueError:
        return None


def parse_table(text):
    """Transaction_Log.md -> (prefix, rows, suffix).

    prefix/suffix are everything before/after the table block, preserved
    byte-for-byte on write - this tool must never touch the explanatory
    prose sections a human wrote, only the table between them.
    """
    m = TABLE_HEADER_RE.search(text)
    if not m:
        raise ValueError("Schema table not found in Transaction_Log.md - "
                         "has its header row been edited?")
    header_block, body = m.group(1), m.group(2)
    prefix = text[:m.start(1)] + header_block
    suffix = text[m.end(2):]

    rows = []
    for line in body.strip("\n").split("\n"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS):
            continue
        if cells[0].startswith("*"):  # the "(none yet)" placeholder row
            continue
        rows.append(dict(zip(COLUMNS, cells)))
    return prefix, rows, suffix


def render_table(rows):
    """Every returned line is properly \n-terminated, including the last -
    a table row is a complete line, not a fragment waiting for whatever
    happens to follow it."""
    if not rows:
        return "| *(none yet)* | | | | | | | | | | | | | |\n"
    lines = []
    for i, row in enumerate(rows, 1):
        cells = [str(i)] + [row.get(c, "") for c in COLUMNS[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def read_log(path=None):
    """-> rows only. path=None resolves LOG_PATH at CALL time, not at
    function-definition time - the same fix spend_guard.py needed the same
    day. `path=LOG_PATH` in the signature binds the module-global's value
    once, when this function object is created; reassigning flip_log.LOG_PATH
    afterward (exactly what testing against a scratch copy does) would then
    silently keep hitting the original path.

    Returns only `rows`, not the (prefix, rows, suffix) parse_table gives -
    every caller only ever wants the rows, and write_log() re-reads the file
    for prefix/suffix itself right before writing, so there is exactly one
    read-modify-write cycle per command, not a stale prefix/suffix pair
    captured earlier and reused."""
    path = path or LOG_PATH
    with open(path, encoding="utf-8") as f:
        return parse_table(f.read())[1]


def write_log(rows, path=None):
    path = path or LOG_PATH
    with open(path, encoding="utf-8") as f:
        prefix, _, suffix = parse_table(f.read())
    # The blank line between the table and whatever prose follows it
    # (Transaction_Log.md's "Record failed buys too..." paragraph) is
    # inserted explicitly here, every write - never inferred from how many
    # newlines happened to survive in `suffix`. An earlier version trusted
    # suffix's leading whitespace, and because render_table's output had no
    # trailing newline of its own, each successive buy/sell cycle consumed
    # one more newline than the last: first call left "row\nRecord" (blank
    # line gone), second call left "row" and "Record" jammed onto the same
    # line with zero separation. Stripping suffix's leading blank lines and
    # re-inserting exactly one makes every write converge to the same
    # spacing regardless of the file's prior state, instead of decaying a
    # little further on every call.
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(prefix + render_table(rows) + "\n" + suffix.lstrip("\n"))
    os.replace(tmp, path)


# --- domain logic: pure -------------------------------------------------

def fuel_cost(distance_km, fuel_per_km=DEFAULT_FUEL_PER_KM):
    if distance_km is None:
        return 0.0
    return round(distance_km * 2 * fuel_per_km, 2)


def compute_close(buy, repair, sold, distance_km, hours, fuel_per_km=DEFAULT_FUEL_PER_KM):
    """-> (net_eur, eur_per_hour, roi_pct). Any missing input propagates as
    None rather than silently computing against a 0 that looks like real
    data - an open flip must show as open, not as a EUR0 loss."""
    if sold is None:
        return None, None, None
    capital = (buy or 0) + (repair or 0)
    net = round(sold - capital - fuel_cost(distance_km, fuel_per_km), 2)
    per_hour = round(net / hours, 2) if hours else None
    roi_pct = round((net / capital) * 100, 1) if capital else None
    return net, per_hour, roi_pct


def label_for(eur_per_hour):
    """At-a-glance indicator. None (still open, or hours never logged) shows
    as a distinct label rather than silently sorting as the worst category -
    "unknown" and "bad" are different facts."""
    if eur_per_hour is None:
        return "OFFEN"
    for threshold, label in LABEL_THRESHOLDS:
        if threshold is None or eur_per_hour >= threshold:
            return label
    return "SCHWACH"


def days_between(d1, d2):
    try:
        return (datetime.strptime(d2, "%Y-%m-%d") - datetime.strptime(d1, "%Y-%m-%d")).days
    except ValueError:
        return None


# --- commands -------------------------------------------------------------

def cmd_buy(args):
    rows = read_log()
    today = args.date or datetime.now().strftime("%Y-%m-%d")
    row = {
        "Date": today, "Item": args.item, "Category": args.category,
        "Buy €": fmt_num(args.buy), "Distance km": fmt_num(args.distance),
        "Repair €": fmt_num(args.repair), "List €": fmt_num(args.list_price),
        "Sold €": "", "Days to sell": "", "Hours": fmt_num(args.hours) if args.hours else "",
        "Net €": "", "€/hour": "",
        "Notes": args.notes or "",
    }
    if args.url:
        row["Notes"] = (row["Notes"] + " " + args.url).strip()
    rows.append(row)
    write_log(rows)
    print(f"Logged buy #{len(rows)}: {args.item} - {args.buy} EUR "
         f"({args.distance} km, category {args.category})")
    print("Still open. Close it out with: flip_log.py sell --row "
         f"{len(rows)} --sold <price> --hours <total hours>")
    return 0


def _find_open_row(rows, item=None, row_num=None):
    if row_num:
        if row_num < 1 or row_num > len(rows):
            return None
        return row_num - 1
    open_idx = [i for i, r in enumerate(rows) if not r.get("Sold €")]
    if item:
        matches = [i for i in open_idx if item.lower() in r_item(rows[i]).lower()]
        open_idx = matches or open_idx
    if len(open_idx) == 1:
        return open_idx[0]
    return None


def r_item(row):
    return row.get("Item", "")


def cmd_sell(args):
    rows = read_log()
    idx = _find_open_row(rows, item=args.item, row_num=args.row)
    if idx is None:
        open_rows = [(i + 1, r["Item"]) for i, r in enumerate(rows) if not r.get("Sold €")]
        print("Could not find exactly one matching open flip. Open flips:", file=sys.stderr)
        for n, name in open_rows:
            print(f"  #{n}  {name}", file=sys.stderr)
        print("Use --row <#> to pick one.", file=sys.stderr)
        return 1

    row = rows[idx]
    sold_date = args.sold_date or datetime.now().strftime("%Y-%m-%d")
    hours = args.hours if args.hours is not None else parse_num(row.get("Hours"))
    net, per_hour, roi_pct = compute_close(
        parse_num(row["Buy €"]), parse_num(row["Repair €"]), args.sold,
        parse_num(row["Distance km"]), hours, args.fuel_per_km)

    row["Sold €"] = fmt_num(args.sold)
    row["Hours"] = fmt_num(hours)
    row["Days to sell"] = fmt_num(days_between(row["Date"], sold_date))
    row["Net €"] = fmt_num(net)
    row["€/hour"] = fmt_num(per_hour)
    if args.notes:
        row["Notes"] = (row.get("Notes", "") + " " + args.notes).strip()

    write_log(rows)

    label = label_for(per_hour)
    print(f"Closed #{idx+1}: {row['Item']}")
    print(f"  Net: {fmt_num(net)} EUR   EUR/hour: {fmt_num(per_hour)}   "
         f"ROI: {fmt_num(roi_pct)}%   [{label}]")
    if net is not None and net < 0:
        print("  This was a loss - logged anyway, per Transaction_Log.md's "
             "own rule: only recording wins teaches nothing.")
    return 0


def cmd_report(args):
    rows = read_log()
    if not rows:
        print("No flips logged yet. First one: flip_log.py buy --item ... --buy ... --distance ...")
        return 0

    open_rows = [r for r in rows if not r.get("Sold €")]
    closed = [r for r in rows if r.get("Sold €")]

    print(f"{len(rows)} flips total: {len(closed)} closed, {len(open_rows)} open\n")

    if closed:
        total_net = sum(parse_num(r["Net €"]) or 0 for r in closed)
        total_capital = sum((parse_num(r["Buy €"]) or 0) + (parse_num(r["Repair €"]) or 0) for r in closed)
        total_hours = sum(parse_num(r["Hours"]) or 0 for r in closed)
        overall_per_hour = round(total_net / total_hours, 2) if total_hours else None
        overall_roi = round((total_net / total_capital) * 100, 1) if total_capital else None
        print(f"Closed: {fmt_num(total_net)} EUR net on {fmt_num(total_capital)} EUR capital "
             f"= {fmt_num(overall_roi)}% ROI, {fmt_num(overall_per_hour)} EUR/hour overall")

        by_cat = {}
        for r in closed:
            by_cat.setdefault(r["Category"] or "?", []).append(parse_num(r["€/hour"]) or 0)
        if len(by_cat) > 1:
            ranked = sorted(by_cat.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
            print("\nBy category (avg EUR/hour, best first):")
            for cat, vals in ranked:
                print(f"  {cat:20} {sum(vals)/len(vals):6.2f}  (n={len(vals)})")

        losers = [r for r in closed if (parse_num(r["Net €"]) or 0) < 0]
        if losers:
            print(f"\n{len(losers)} loss(es) - not hidden, per the log's own rule:")
            for r in losers:
                print(f"  {r['Item'][:40]:42} {r['Net €']} EUR")

    if open_rows:
        print(f"\n{len(open_rows)} open flip(s):")
        for i, r in enumerate(rows, 1):
            if r.get("Sold €"):
                continue
            age = days_between(r["Date"], datetime.now().strftime("%Y-%m-%d"))
            flag = "  <- sitting a while, days-to-sell is a cost" if age and age > 21 else ""
            print(f"  #{i}  {r['Item'][:40]:42} bought {r['Date']} ({age}d ago){flag}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Log LocalArbitrage flips directly into Transaction_Log.md.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("buy", help="log a new purchase (opens a flip)")
    b.add_argument("--item", required=True)
    b.add_argument("--category", required=True)
    b.add_argument("--buy", type=float, required=True)
    b.add_argument("--distance", type=float, required=True, help="one-way km")
    b.add_argument("--repair", type=float, default=None)
    b.add_argument("--list-price", type=float, default=None, dest="list_price")
    b.add_argument("--hours", type=float, default=None, help="hours so far, if known")
    b.add_argument("--date", default=None, help="YYYY-MM-DD, default today")
    b.add_argument("--url", default=None, help="the Kleinanzeigen ad, for provenance")
    b.add_argument("--notes", default=None)
    b.set_defaults(func=cmd_buy)

    s = sub.add_parser("sell", help="close out an open flip")
    s.add_argument("--row", type=int, default=None, help="row # from `report`, if ambiguous")
    s.add_argument("--item", default=None, help="match by (partial) item name instead of --row")
    s.add_argument("--sold", type=float, required=True)
    s.add_argument("--hours", type=float, default=None, help="total hours end-to-end")
    s.add_argument("--sold-date", default=None, dest="sold_date")
    s.add_argument("--fuel-per-km", type=float, default=DEFAULT_FUEL_PER_KM, dest="fuel_per_km")
    s.add_argument("--notes", default=None)
    s.set_defaults(func=cmd_sell)

    r = sub.add_parser("report", help="portfolio stats: ROI, EUR/hour, open flips")
    r.set_defaults(func=cmd_report)

    args = ap.parse_args()
    sys.exit(args.func(args))

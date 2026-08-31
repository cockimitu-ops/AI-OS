#!/usr/bin/env python3
"""Kleinanzeigen sniper: polls saved searches, Telegram-pings genuinely new ads.

Exists to serve LocalArbitrage and the broken-phone flip loop, where the entire
edge is being the first buyer to message an urgency seller. A listing found 20
minutes late is usually a listing someone else already collected.

A watch is one Markdown file in watches/, same "drop a file in a folder"
convention scripts/run_schedules.py uses for schedules - adding a search should
never require sudo or a code change:

    <!-- search: monitor -->
    <!-- location: 4178 -->
    <!-- radius: 30 -->
    <!-- price: 20-150 -->
    <!-- exclude: halterung, kabel -->
    Free text below the directives is notes for humans and is ignored.

Directive grammar is deliberately tiny, for the same reason run_schedules.py
keeps its cadence grammar tiny: every additional filter is another way to be
silently wrong about what ran unattended while nobody was watching.

Stdlib only. systemd runs this under /usr/bin/python3, outside the venv at
/home/nost/interpreter-env - the same constraint documented on
send_telegram_notification.py, and the same reason there is no requests/bs4 here.
"""
import argparse
import html as htmlmod
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
from send_telegram_notification import send as send_telegram  # noqa: E402

WATCHES_DIR = os.path.join(TASK_RUNNER_DIR, "watches")
STATE_PATH = os.path.join(WATCHES_DIR, "state.json")

BASE = "https://www.kleinanzeigen.de"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

# Crimmitschau. Look another up with:
#   curl 's://www.kleinanzeigen.de/s-ort-empfehlungen.json?query=Zwickau'
DEFAULT_LOCATION = "4178"
DEFAULT_RADIUS = "30"

# Keep the total request rate low and obviously human-scale. Politeness is also
# self-interest: this only keeps working as long as it stays unremarkable.
DELAY_BETWEEN_WATCHES = (2.0, 5.0)
HTTP_TIMEOUT = 20
SEEN_RETENTION_DAYS = 14
MAX_ALERTS_PER_RUN = 10

# A broken watch must not ping every 3 minutes. Same interval health_check
# uses for an unresolved failure: say it once, then stay quiet for 6 hours.
FAILURE_REALERT_SECONDS = 6 * 3600

DIRECTIVE_RE = re.compile(r"^\s*<!--\s*([a-z_]+)\s*:\s*(.+?)\s*-->\s*$", re.I | re.M)

ARTICLE_RE = re.compile(
    r'<article[^>]*class="[^"]*\baditem\b[^"]*"[^>]*data-adid="(\d+)"'
    r'[^>]*data-href="([^"]+)"(.*?)</article>', re.S)
TITLE_RE = re.compile(r"<h2[^>]*>\s*<a[^>]*>(.*?)</a>", re.S)
PRICE_RE = re.compile(r'price-shipping--price"[^>]*>(.*?)</p>', re.S)
LOC_RE = re.compile(r'aditem-main--top--left"[^>]*>(.*?)</div>', re.S)
DATE_RE = re.compile(r'aditem-main--top--right"[^>]*>(.*?)</div>', re.S)
DESC_RE = re.compile(r'aditem-main--middle--description"[^>]*>(.*?)</p>', re.S)
DISTANCE_RE = re.compile(r"(\d+)\s*km")

# Kleinanzeigen pads thin result pages with ads well outside the requested
# radius ("Teutschenthal + 200 km" showed up in a 35km search on 2026-08-31).
# Allow a little slack over the stated radius, because the site rounds ("ca.
# 30 km") - but not 200km, which is a full day's driving against a 50 EUR margin.
DISTANCE_SLACK_KM = 5


# --- parsing: pure -----------------------------------------------------------

def strip_tags(raw):
    """HTML fragment -> collapsed plain text."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", htmlmod.unescape(text)).strip()


def parse_distance(location):
    """Location line -> distance in km, or None when the ad states none.

    None means "no distance shown", which happens for ads in the search town
    itself. Those are the closest ads there are, so they must never be dropped
    by the distance filter.
    """
    m = DISTANCE_RE.search(location or "")
    return int(m.group(1)) if m else None


def parse_price(raw):
    """-> int euros, or None when the ad names no number.

    Takes the FIRST number on purpose. A reduced listing renders as
    "280 € VB 290 €" (new price, then the struck-through old one), and reading
    that as 290 would push real finds past a max_price filter. "Zu verschenken"
    is a genuine 0, not a missing price - it is also the single strongest
    signal this whole tool exists to catch, so it must never be dropped.
    """
    text = strip_tags(raw)
    if not text:
        return None
    if "verschenk" in text.lower():
        return 0
    m = re.search(r"(\d[\d.]*)\s*€", text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def parse_watch(text):
    """Markdown watch file -> (config dict, error string or None)."""
    cfg = {"search": None, "url": None, "location": DEFAULT_LOCATION,
           "radius": DEFAULT_RADIUS, "min_price": None, "max_price": None,
           "require": [], "exclude": []}

    for key, value in DIRECTIVE_RE.findall(text):
        key = key.lower()
        if key == "search":
            cfg["search"] = value
        elif key == "url":
            cfg["url"] = value
        elif key == "location":
            cfg["location"] = value.strip()
        elif key == "radius":
            cfg["radius"] = value.strip()
        elif key == "price":
            lo, _, hi = value.partition("-")
            if lo.strip():
                cfg["min_price"] = int(re.sub(r"\D", "", lo) or 0)
            if hi.strip():
                cfg["max_price"] = int(re.sub(r"\D", "", hi) or 0)
        elif key in ("require", "exclude"):
            cfg[key] = [w.strip().lower() for w in value.split(",") if w.strip()]

    if not cfg["search"] and not cfg["url"]:
        return None, "needs a <!-- search: ... --> or <!-- url: ... --> directive"
    return cfg, None


def is_watch_file(name, text):
    """README.md lives in this folder and is documentation, not a broken watch.

    Treating it as one made the sniper alert "Sniper-Problem: README.md" every
    3 minutes for hours - the folder's own docs became a permanent failure.
    A file with no directives at all is prose; a file with directives but no
    search/url is a real mistake and still reports.
    """
    if name.lower() == "readme.md":
        return False
    return bool(DIRECTIVE_RE.search(text))


def build_url(cfg):
    if cfg["url"]:
        return cfg["url"]
    # Umlauts have no place in the slug, but must survive in the query string -
    # "haushaltsaufloesung" and "haushaltsauflösung" are different searches to
    # Kleinanzeigen, and the second one is the one with the results.
    slug = re.sub(r"[^a-z0-9]+", "-",
                  cfg["search"].lower()
                  .replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("-") or "suche"
    keywords = urllib.parse.quote(cfg["search"])
    return (f"{BASE}/s-crimmitschau/{slug}/k0l{cfg['location']}"
            f"r{cfg['radius']}?keywords={keywords}")


def parse_listings(html):
    """Search results HTML -> list of listing dicts."""
    out = []
    for match in ARTICLE_RE.finditer(html):
        adid, href, body = match.groups()
        title_m = TITLE_RE.search(body)
        desc_m = DESC_RE.search(body)
        loc_m = LOC_RE.search(body)
        date_m = DATE_RE.search(body)
        price_m = PRICE_RE.search(body)
        out.append({
            "id": adid,
            "url": BASE + href if href.startswith("/") else href,
            "title": strip_tags(title_m.group(1)) if title_m else "(kein Titel)",
            "desc": strip_tags(desc_m.group(1)) if desc_m else "",
            "location": strip_tags(loc_m.group(1)) if loc_m else "",
            "posted": strip_tags(date_m.group(1)) if date_m else "",
            "price": parse_price(price_m.group(1)) if price_m else None,
        })
        out[-1]["distance"] = parse_distance(out[-1]["location"])
    return out


def matches(listing, cfg):
    """Does this listing survive the watch's filters?

    A price-less ad ("VB", "auf Anfrage") always passes the price filter rather
    than being dropped: no stated price is exactly the seller-doesn't-know
    signal LocalArbitrage's README targets, and silently filtering those out
    would remove the best finds while looking like it worked.
    """
    max_km = int(cfg["radius"]) + DISTANCE_SLACK_KM
    if listing.get("distance") is not None and listing["distance"] > max_km:
        return False
    haystack = (listing["title"] + " " + listing["desc"]).lower()
    if cfg["exclude"] and any(w in haystack for w in cfg["exclude"]):
        return False
    if cfg["require"] and not any(w in haystack for w in cfg["require"]):
        return False
    price = listing["price"]
    if price is not None:
        if cfg["min_price"] is not None and price < cfg["min_price"]:
            return False
        if cfg["max_price"] is not None and price > cfg["max_price"]:
            return False
    return True


def format_alert(listing, watch_name):
    price = "VB / kein Preis" if listing["price"] is None else f"{listing['price']} €"
    # The location line already carries "(30 km)" whenever a distance exists,
    # so appending it again just made every alert read "Stollberg (30 km) (~30
    # km)". In-town ads show no km at all, which is correct - they are local.
    location = listing["location"]
    lines = [
        f"[{watch_name}] {listing['title']}",
        f"{price} — {location}",
        f"{listing['posted']}",
        listing["url"],
    ]
    return "\n".join(line for line in lines if line.strip())


# --- state -------------------------------------------------------------------

def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        state = {}
    state.setdefault("seen", {})
    state.setdefault("seeded", [])
    # Activity counters since the last status update read them. They exist so
    # that "no alerts" can be reported as a number rather than as silence -
    # from the outside a working sniper on a quiet morning and a broken one
    # look identical, which is what made the first live day unreadable.
    state.setdefault("stats", {"runs": 0, "listings": 0, "new_ads": 0, "alerts": 0})
    state.setdefault("alerted", {})
    return state


def take_stats():
    """Read and reset the activity counters. Called by the status update, which
    reports the window since it last ran."""
    state = load_state()
    stats = dict(state["stats"])
    state["stats"] = {"runs": 0, "listings": 0, "new_ads": 0, "alerts": 0}
    save_state(state)
    return stats


def save_state(state):
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)
    cutoff_iso = cutoff.isoformat()
    state["seen"] = {k: v for k, v in state["seen"].items() if v >= cutoff_iso}
    os.makedirs(WATCHES_DIR, exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, STATE_PATH)


# --- io ----------------------------------------------------------------------

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "de-DE,de;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read().decode("utf-8", "replace")


def run(dry_run=False, only=None, reseed=False):
    if not os.path.isdir(WATCHES_DIR):
        print(f"No watches dir at {WATCHES_DIR}", file=sys.stderr)
        return 1

    files = []
    for name in sorted(os.listdir(WATCHES_DIR)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(WATCHES_DIR, name), encoding="utf-8") as f:
            if is_watch_file(name, f.read()):
                files.append(name)
    if only:
        files = [f for f in files if f == only or f == only + ".md"]
    if not files:
        print("No watch files found.", file=sys.stderr)
        return 1

    state = load_state()
    stats = state["stats"]
    now_iso = datetime.now(timezone.utc).isoformat()
    alerts, failures, first = [], [], False
    scanned = new_ads = 0

    for i, fname in enumerate(files):
        path = os.path.join(WATCHES_DIR, fname)
        with open(path, encoding="utf-8") as f:
            cfg, err = parse_watch(f.read())
        if err:
            failures.append(f"{fname}: {err}")
            continue

        if i:
            time.sleep(random.uniform(*DELAY_BETWEEN_WATCHES))

        url = build_url(cfg)
        try:
            listings = parse_listings(fetch(url))
        except urllib.error.HTTPError as e:
            failures.append(f"{fname}: HTTP {e.code}")
            continue
        except Exception as e:  # noqa: BLE001 - one bad watch must not kill the rest
            failures.append(f"{fname}: {type(e).__name__}: {e}")
            continue

        if not listings:
            failures.append(f"{fname}: 0 listings parsed (layout may have changed)")
            continue

        # A watch's first run only records what is already there. Without this,
        # adding a search means an instant burst of 25 "new" ads that are not
        # new at all, which trains you to ignore the alerts - the one failure
        # mode that makes the whole tool worthless.
        seeding = reseed or fname not in state["seeded"]
        watch_name = os.path.splitext(fname)[0]
        hits = 0

        scanned += len(listings)
        for listing in listings:
            if listing["id"] in state["seen"]:
                continue
            state["seen"][listing["id"]] = now_iso
            new_ads += 1
            if seeding or not matches(listing, cfg):
                continue
            alerts.append(format_alert(listing, watch_name))
            hits += 1

        if seeding:
            first = True
            if fname not in state["seeded"]:
                state["seeded"].append(fname)
            print(f"{fname}: seeded {len(listings)} existing listings (no alerts)")
        else:
            print(f"{fname}: {len(listings)} listings, {hits} new match(es)")

    if not first:
        stats["runs"] += 1
        stats["listings"] += scanned
        stats["new_ads"] += new_ads
        stats["alerts"] += len(alerts)

    if dry_run:
        print("\n--- DRY RUN, nothing sent, state not written ---")
        for a in alerts:
            print(a + "\n")
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 0

    # Print failures in every mode, not just --dry-run. They were previously
    # sent to Telegram and never logged, so the journal showed five healthy
    # watches while the phone buzzed every 3 minutes - the one view that would
    # have explained it was the one that stayed silent.
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)

    for alert in alerts[:MAX_ALERTS_PER_RUN]:
        send_telegram(alert)
    if len(alerts) > MAX_ALERTS_PER_RUN:
        send_telegram(f"…und {len(alerts) - MAX_ALERTS_PER_RUN} weitere Treffer "
                      f"(gedrosselt). Filter enger stellen?")

    # Parse failures are the silent killer here: if Kleinanzeigen changes its
    # markup, every watch returns 0 listings and this reports "nothing new"
    # forever. Surface that as an alert instead of as silence.
    if failures and not first:
        signature = "|".join(sorted(failures))
        last = state.get("alerted", {}).get(signature)
        due = True
        if last:
            try:
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(last)).total_seconds()
                due = age > FAILURE_REALERT_SECONDS
            except ValueError:
                due = True
        if due:
            send_telegram("Sniper-Problem:\n" + "\n".join(failures[:5]))
            state.setdefault("alerted", {})[signature] = \
                datetime.now(timezone.utc).isoformat()
    elif not failures:
        state["alerted"] = {}

    save_state(state)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Poll Kleinanzeigen watches, alert on new ads.")
    ap.add_argument("--dry-run", action="store_true", help="print instead of sending; do not write state")
    ap.add_argument("--only", help="run a single watch file, e.g. --only monitore")
    ap.add_argument("--reseed", action="store_true", help="mark everything currently listed as seen, alert on nothing")
    args = ap.parse_args()
    sys.exit(run(dry_run=args.dry_run, only=args.only, reseed=args.reseed))

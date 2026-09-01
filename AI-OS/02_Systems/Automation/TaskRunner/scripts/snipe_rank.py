#!/usr/bin/env python3
"""Ranks the sniper's finds into tiers - a triage order, not a valuation.

THE LINE THIS DELIBERATELY DOES NOT CROSS

`10_Projects/LocalArbitrage/Valuation_Method.md` opens with its own rule, in
bold: **"AI does not estimate resale prices. Sold listings do."** The reasoning
there is exact - a confident, plausible, specific hallucinated number on a real
purchase is how you lose real money while feeling well informed.

So this does not score deals. It cannot: nothing here knows what a Bosch GSR
sells for, and inventing that number would break the project's first rule while
looking helpful.

What it ranks is **attention**: which listings are worth opening first, out of
signals that are actually observable in the ad itself. An S tier means "look at
this before the others", never "this is worth more than you pay". The resale
number still comes from sold comps, by hand, exactly as that document requires.

Everything below is arithmetic on data already in the listing. Zero tokens,
no model, no network - same design as money_board.py.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import kleinanzeigen_sniper as sniper  # noqa: E402  (needs sys.path first)

# Urgency language. LocalArbitrage's own README names these as the edge: a
# seller who wants the thing gone today prices to make it gone today. Weighted
# highest of any single signal because it is the closest thing to a real
# discount indicator that is visible without knowing market value.
URGENCY = {
    "muss weg": 30, "schnell weg": 30, "sofort": 18, "heute noch": 22,
    "umzug": 22, "haushaltsauflösung": 25, "haushaltsaufloesung": 25,
    "wohnungsauflösung": 25, "entrümpelung": 22, "keller": 10,
    "räumung": 20, "nachlass": 18, "aufgabe": 14, "letzte": 8,
}
# Negotiability. "VB" is a stated invitation to offer less; a fixed price is
# not. Small weight - it moves the final price, not whether it is worth a look.
NEGOTIABLE = {"vb": 10, "verhandlungsbasis": 10, "verhandelbar": 10,
              "preis vb": 10}
# Words that mean "this will cost you more than the ad says". Negative, and
# deliberately not disqualifying: a broken phone is the whole point of one of
# the watches, so this lowers priority rather than removing the listing.
RISK = {"bastler": -12, "defekt": -8, "ersatzteil": -10, "kaputt": -12,
        "reparatur": -8, "funktioniert nicht": -18, "ungetestet": -14,
        "unvollständig": -12, "ohne akku": -14, "ohne ladegerät": -12}

TIERS = [(78, "S"), (58, "A"), (40, "B"), (22, "C")]
DEFAULT_TIER = "D"


def _hay(find):
    return f"{find.get('title', '')} {find.get('desc', '')}".lower()


def _fold(text):
    """Umlaut-folded lowercase, so "Haushaltsauflösung" and the watch file
    "aufloesung.md" can be compared at all."""
    return (text or "").lower().replace("ä", "ae").replace("ö", "oe") \
                              .replace("ü", "ue").replace("ß", "ss")


def _implied_by_watch(word, watch):
    """Is this urgency word just restating what the watch searched for?

    Caught on the first run against real listings: the `aufloesung` watch
    searches for "Haushaltsauflösung", which is also one of the highest-weighted
    urgency keywords - so every single one of its listings collected +25 for
    containing the term it was selected by, and that watch swept the top of the
    board regardless of whether any individual ad was actually good. The search
    already applied that filter; scoring it again is counting it twice."""
    if not watch:
        return False
    folded_watch, folded_word = _fold(watch), _fold(word)
    return folded_word in folded_watch or folded_watch in folded_word


def _keyword_score(hay, table):
    """Sum every distinct phrase that appears. Distinct, not per-occurrence:
    an ad that says "muss weg" four times is not four times as urgent, it is
    one urgent seller who repeats himself."""
    hits = [(word, weight) for word, weight in table.items() if word in hay]
    return sum(w for _, w in hits), [word for word, _ in hits]


def _age_hours(find, now=None):
    """Hours since the sniper first saw it. Uses found_at, not the ad's own
    'Heute, 18:19' text: that is a display string in the site's timezone with
    no date on it, and parsing it would be guessing."""
    stamp = find.get("found_at")
    if not stamp:
        return None
    try:
        seen = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    # Clamped at zero: a clock skew between the sniper host and here would
    # otherwise produce a negative age and score a listing as impossibly fresh.
    elapsed = (now or datetime.now(timezone.utc)) - seen
    return max(elapsed, timedelta(0)).total_seconds() / 3600


def score(find, now=None):
    """-> (points, tier, reasons). Reasons are shown in the UI, because a
    rank Felix cannot audit is a rank he is right not to trust."""
    points, reasons = 0, []
    hay = _hay(find)
    price = find.get("price")
    distance = find.get("distance")

    # Free is categorically different from cheap. LocalArbitrage's README
    # calls "zu verschenken" the single strongest signal the tool exists to
    # catch, so it is scored as such rather than as "price 0".
    if price == 0:
        points += 45
        reasons.append("zu verschenken")
    elif price is None:
        # No stated price is the seller-doesn't-know signal, not missing data.
        points += 14
        reasons.append("kein Preis genannt")
    elif price <= 25:
        points += 20
        reasons.append(f"niedriger Preis ({price} €)")
    elif price <= 60:
        points += 12
    elif price <= 120:
        points += 5

    # Distance is a real, computable cost - fuel and an hour of his life -
    # not a preference. It is the one number here that is unambiguous.
    if distance is not None:
        if distance <= 10:
            points += 18
            reasons.append(f"{distance} km")
        elif distance <= 20:
            points += 11
        elif distance <= 30:
            points += 4
        else:
            points -= 8
            reasons.append(f"weit ({distance} km)")
    else:
        # No distance shown means the ad is in the search town itself.
        points += 16
        reasons.append("im Ort")

    urgency, urgency_words = _keyword_score(hay, URGENCY)
    watch = find.get("watch")
    redundant = [w for w in urgency_words if _implied_by_watch(w, watch)]
    if redundant:
        urgency -= sum(URGENCY[w] for w in redundant)
        urgency_words = [w for w in urgency_words if w not in redundant]
    if urgency > 0:
        points += min(urgency, 40)
        reasons.append("Dringlichkeit: " + ", ".join(sorted(urgency_words)[:3]))

    negotiable, _ = _keyword_score(hay, NEGOTIABLE)
    if negotiable:
        points += negotiable
        reasons.append("VB")

    risk, risk_words = _keyword_score(hay, RISK)
    if risk:
        points += max(risk, -35)
        reasons.append("Risiko: " + ", ".join(sorted(risk_words)[:3]))

    # Freshness. The whole edge in this project is messaging first, so a
    # listing found ten minutes ago is worth more attention than the same
    # listing found yesterday - and this is the only score component that
    # changes on its own over time.
    age = _age_hours(find, now=now)
    if age is not None:
        if age <= 1:
            points += 22
            reasons.append("frisch")
        elif age <= 6:
            points += 12
        elif age <= 24:
            points += 4
        elif age > 96:
            points -= 10
            reasons.append("älter")

    points = max(0, min(points, 100))
    tier = DEFAULT_TIER
    for threshold, name in TIERS:
        if points >= threshold:
            tier = name
            break
    return points, tier, reasons


def rank(finds=None, watch=None, tier=None, max_price=None, max_distance=None,
         limit=None, now=None):
    """-> scored finds, best first. Filters are applied AFTER scoring so a
    tier filter means what it says rather than 'best of what survived'."""
    rows = []
    for find in (finds if finds is not None else sniper.load_finds()):
        points, tier_name, reasons = score(find, now=now)
        rows.append(dict(find, score=points, tier=tier_name, reasons=reasons))

    if watch:
        rows = [r for r in rows if r.get("watch") == watch]
    if tier:
        wanted = {t.strip().upper() for t in
                  (tier if isinstance(tier, (list, tuple)) else [tier])}
        rows = [r for r in rows if r["tier"] in wanted]
    if max_price is not None:
        # A price-less ad survives a max-price filter on purpose: it is a
        # signal, not a missing value, and dropping it would filter out the
        # exact thing the sniper is for.
        rows = [r for r in rows
                if r.get("price") is None or r["price"] <= max_price]
    if max_distance is not None:
        rows = [r for r in rows
                if r.get("distance") is None or r["distance"] <= max_distance]

    # Score first, then newest among equals - two listings that rank the same
    # are separated by which one Felix could still be first to answer.
    rows.sort(key=lambda r: (r["score"], r.get("found_at") or ""), reverse=True)
    return rows[:limit] if limit else rows


def watches():
    """Watch names that actually appear in the finds, for the UI's filter."""
    return sorted({f.get("watch") for f in sniper.load_finds() if f.get("watch")})


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--watch")
    ap.add_argument("--tier")
    ap.add_argument("--max-price", type=int)
    ap.add_argument("--max-distance", type=int)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args(argv)

    rows = rank(watch=args.watch, tier=args.tier, max_price=args.max_price,
                max_distance=args.max_distance, limit=args.limit)
    if not rows:
        print("Keine Funde. (Sniper hatte noch keine Treffer, oder Filter zu eng.)")
        return 0
    for r in rows:
        price = "verschenkt" if r.get("price") == 0 else (
            f"{r['price']} €" if r.get("price") is not None else "kein Preis")
        dist = f"{r['distance']} km" if r.get("distance") is not None else "im Ort"
        print(f"[{r['tier']}] {r['score']:>3}  {r['title'][:52]}")
        print(f"        {price} · {dist} · {r.get('watch', '?')}")
        if r["reasons"]:
            print(f"        {' · '.join(r['reasons'][:4])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Finds local businesses whose email domain can be spoofed, and ranks them.

The sales premise, from 10_Projects/MoneyMaking's option 8: most German SMBs
have no DMARC record, which means anyone can send mail as them. It is a real
risk an owner understands in one sentence, and a ~2h fix worth 150-300 EUR.
The bottleneck was never the fix - it was knowing who to call. This is that.

STRICTLY PASSIVE, AND MUST STAY THAT WAY. Two data sources, both public and
both designed to be queried:

  - OpenStreetMap via Overpass API, for which local businesses have a website
    at all. Open data (ODbL), a public API, no scraping of anyone's site.
  - Public DNS (TXT, MX) via dig. Looking up a domain's published DNS records
    is not a scan, not a probe, and not access to anything of theirs - it is
    reading a phone book they published.

Nothing here connects to a prospect's servers, tests a login, sends mail, or
touches a port. If a future change would need any of that, it does not belong
in this file - it belongs behind a signed engagement.

Stdlib only, same reason as the rest of scripts/: systemd runs this under
/usr/bin/python3, outside the venv at /home/nost/interpreter-env. DNS goes
through dig rather than dnspython for exactly that reason.
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
PROSPECTS_DIR = os.path.join(TASK_RUNNER_DIR, "prospects")
AREAS_PATH = os.path.join(PROSPECTS_DIR, "areas.md")
DOMAINS_PATH = os.path.join(PROSPECTS_DIR, "domains.json")
RESULTS_PATH = os.path.join(PROSPECTS_DIR, "results.json")
REPORTED_PATH = os.path.join(PROSPECTS_DIR, "reported.json")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
UA = "AI-OS-prospector/1.0 (personal prospecting; contact felix.haubold143@gmail.com)"

# Overpass is a free community service. Discovery runs weekly at most - a
# bakery does not change its domain overnight - and the nightly job is DNS
# only, which hits the resolver rather than anyone's volunteer infrastructure.
OVERPASS_TIMEOUT = 180
DNS_TIMEOUT = 8
DNS_DELAY = 0.15

# How many domains to (re)check per nightly run, and how stale a result may get
# before it is rechecked. A prospect who fixes their DMARC stops being a
# prospect, so results have to expire - but rechecking 1400 domains every night
# is 4200 pointless queries.
NIGHTLY_BUDGET = 1200
# A full run is ~13 minutes of DNS. Writing results only at the end means a
# reboot or a kill at minute 12 discards all of it, and the next night starts
# from nothing. Checkpointing makes progress durable and costs one small write
# per 100 domains.
CHECKPOINT_EVERY = 100
RECHECK_AFTER_DAYS = 7

# A domain sitting at many separate locations is a chain (MediaMarkt, Globus,
# Sparkasse). Chains have an IT department and are not the customer. Local
# businesses appear once or twice.
MAX_LOCATIONS_BEFORE_CHAIN = 3

# Overpass answers 429 if you fire areas back to back - seen live on the first
# run, which cost the Gera area entirely. Space them out and retry once.
OVERPASS_AREA_DELAY = 25
OVERPASS_RETRIES = 2

# Many small businesses "have a website" that is really a page on someone
# else's platform: 12706.apotheken-website-vorschau.de, 1a-hausdorf.go1a.de.
# Publishing DMARC for those is the platform operator's job, not the local
# pharmacy's - so they are not merely low-quality leads, they are the wrong
# person to call. Detected by parent domain reuse, not by a hardcoded list.
MAX_SUBDOMAINS_BEFORE_PLATFORM = 3

DIRECTIVE_RE = re.compile(r"^\s*<!--\s*([a-z_]+)\s*:\s*(.+?)\s*-->\s*$", re.I | re.M)

# Categories worth a call. Deliberately an allowlist: OSM's "website" tag also
# lands on bus stops, churches, and recycling containers.
BUSINESS_KEYS = ("shop", "craft", "office", "healthcare")


# --- discovery: OpenStreetMap ------------------------------------------------

def parse_areas(text):
    """areas.md -> list of (name, lat, lon, radius_m)."""
    areas, current = [], {}
    for key, value in DIRECTIVE_RE.findall(text):
        key = key.lower()
        if key == "area":
            if current.get("name"):
                areas.append(current)
            current = {"name": value, "radius": 20}
        elif key == "center":
            lat, _, lon = value.partition(",")
            current["lat"], current["lon"] = lat.strip(), lon.strip()
        elif key == "radius":
            current["radius"] = int(re.sub(r"\D", "", value) or 20)
    if current.get("name"):
        areas.append(current)
    return [a for a in areas if a.get("lat") and a.get("lon")]


def build_overpass_query(lat, lon, radius_km):
    radius_m = int(radius_km) * 1000
    clauses = []
    for tag in ("website", "contact:website"):
        for key in BUSINESS_KEYS:
            clauses.append(f'  nwr(around:{radius_m},{lat},{lon})["{tag}"]["{key}"];')
    return "[out:json][timeout:120];\n(\n" + "\n".join(clauses) + "\n);\nout tags;"


def domain_from_url(url):
    """URL -> bare registrable-ish hostname, or None.

    Deliberately conservative: anything that does not look like a hostname is
    dropped rather than guessed at, because a malformed domain becomes a
    wasted DNS lookup and a nonsense line in the morning brief.
    """
    if not url:
        return None
    url = url.strip().lower()
    url = re.sub(r"^[a-z]+://", "", url)
    url = url.split("/")[0].split("?")[0].split("#")[0]
    url = url.split("@")[-1].split(":")[0]
    if url.startswith("www."):
        url = url[4:]
    if not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9-]+)*\.[a-z]{2,}", url):
        return None
    if url.count(".") > 3:
        return None
    return url


def registrable_parent(domain):
    """Best-effort "the domain someone actually owns" - last two labels, with
    the common German/UK second-level suffixes taken as part of the suffix.
    Not a public-suffix-list implementation; it only has to be right often
    enough to spot a platform hosting hundreds of subdomains."""
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "gov", "ac"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def drop_platform_subdomains(found):
    """Keep only domains the business plausibly controls the DNS zone for.

    Every subdomain goes, not just those under a busy parent. The pitch is
    "publish this DNS record", so someone who cannot edit the zone cannot buy
    - agentur.barmenia.de is an insurance agent on the insurer's corporate
    domain, and DMARC there is Barmenia's decision, not his. Precision beats
    recall on a cold-outreach list: a wasted call costs more than a missed
    lead, and there are 4,000 of these.
    """
    return {d: e for d, e in found.items() if d == registrable_parent(d)}


def parse_overpass(payload):
    """Overpass JSON -> {domain: {name, category, locations}}, chains dropped."""
    found = {}
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        domain = domain_from_url(tags.get("website") or tags.get("contact:website"))
        if not domain:
            continue
        category = next((tags[k] for k in BUSINESS_KEYS if tags.get(k)), "?")
        entry = found.setdefault(domain, {
            "domain": domain,
            "name": tags.get("name", "?"),
            "category": category,
            "locations": 0,
        })
        entry["locations"] += 1
    found = {d: e for d, e in found.items()
             if e["locations"] <= MAX_LOCATIONS_BEFORE_CHAIN}
    return drop_platform_subdomains(found)


def fetch_overpass(query, retries=OVERPASS_RETRIES):
    req = urllib.request.Request(
        OVERPASS_URL, data=query.encode("utf-8"),
        headers={"User-Agent": UA, "Content-Type": "text/plain"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=OVERPASS_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            # 429/504 mean the free service is busy, not that the query is
            # wrong. Backing off is the difference between losing an area and
            # waiting a minute for it.
            if e.code not in (429, 504) or attempt == retries:
                raise
            time.sleep(OVERPASS_AREA_DELAY * (attempt + 2))
    raise RuntimeError("unreachable")


# --- audit: public DNS -------------------------------------------------------

def dig(record_type, name):
    """-> list of answer strings. Never raises; DNS failure is a normal result."""
    try:
        proc = subprocess.run(
            ["dig", "+short", "+time=3", "+tries=2", record_type, name],
            capture_output=True, text=True, timeout=DNS_TIMEOUT)
    except Exception:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def join_txt(answers):
    """dig splits long TXT records into adjacent quoted chunks: '"a" "b"'.
    Joining them matters - an SPF record over 255 chars arrives split, and
    reading only the first chunk would misreport its policy."""
    out = []
    for answer in answers:
        parts = re.findall(r'"([^"]*)"', answer)
        out.append("".join(parts) if parts else answer)
    return out


def parse_spf(txts):
    """-> (policy, record). policy is one of -all/~all/?all/+all/none/None."""
    for txt in txts:
        if txt.lower().startswith("v=spf1"):
            m = re.search(r"([-~?+])all\b", txt.lower())
            return (m.group(1) + "all") if m else "none", txt
    return None, None


def parse_dmarc(txts):
    """-> (policy, record). policy is reject/quarantine/none, or None."""
    for txt in txts:
        if txt.lower().replace(" ", "").startswith("v=dmarc1"):
            m = re.search(r"\bp\s*=\s*(reject|quarantine|none)\b", txt, re.I)
            return (m.group(1).lower() if m else "none"), txt
    return None, None


def classify_provider(mx_answers):
    """Which mail host, for the sales conversation - "you're on IONOS, this is
    a 20 minute change" lands better than a lecture about DNS."""
    joined = " ".join(mx_answers).lower()
    for needle, label in (
        ("google", "Google Workspace"), ("outlook", "Microsoft 365"),
        ("protection.outlook", "Microsoft 365"), ("ionos", "IONOS"),
        ("1und1", "IONOS"), ("kasserver", "all-inkl"), ("strato", "STRATO"),
        ("telekom", "Telekom"), ("mailbox.org", "mailbox.org"),
        ("hosteurope", "Host Europe"), ("netcup", "netcup"),
        ("df.eu", "domainFACTORY"), ("udag", "united-domains"),
    ):
        if needle in joined:
            return label
    return "unknown" if mx_answers else "no MX"


def score(spf_policy, dmarc_policy, has_mx):
    """Higher = better prospect. The weights encode the actual sales argument,
    not a security grade: a domain that sends real mail and publishes no DMARC
    is both the easiest sale and the realest risk.

    A domain with DMARC p=reject and SPF -all scores 0 and should never be
    called - they already did it, and pitching them wastes the one thing this
    whole list is meant to save."""
    points = 0
    if dmarc_policy is None:
        points += 4          # anyone can spoof them, and nobody is even watching
    elif dmarc_policy == "none":
        points += 2          # monitoring only; published a policy that enforces nothing
    elif dmarc_policy == "quarantine":
        points += 1

    if spf_policy is None:
        points += 3
    elif spf_policy in ("+all", "?all", "none"):
        points += 3          # an SPF record that authorises everyone is not SPF
    elif spf_policy == "~all":
        points += 1

    # Mail flow amplifies an existing weakness rather than being one itself.
    # Adding this unconditionally scored a fully-protected domain at 2 instead
    # of 0 - caught by its own test. It never leaked into the ranked list
    # (min_score is 6), but "already secure" has to mean zero, or the number
    # stops meaning what its name says.
    if points and has_mx:
        points += 2
    return points


def lookup_dmarc(domain):
    """-> (policy, record, source). RFC 7489 requires falling back to the
    organizational domain: a subdomain with no record of its own inherits the
    parent's policy. Skipping that fallback reports "no DMARC" for a domain
    that is actually protected - a false positive that turns into a cold call
    telling someone they have a problem they already fixed."""
    policy, record = parse_dmarc(join_txt(dig("TXT", "_dmarc." + domain)))
    if policy is not None:
        return policy, record, "own"
    parent = registrable_parent(domain)
    if parent != domain:
        policy, record = parse_dmarc(join_txt(dig("TXT", "_dmarc." + parent)))
        if policy is not None:
            return policy, record, "inherited"
    return None, None, "none"


def audit_domain(domain):
    spf_policy, spf_record = parse_spf(join_txt(dig("TXT", domain)))
    dmarc_policy, dmarc_record, dmarc_source = lookup_dmarc(domain)
    mx = dig("MX", domain)
    return {
        "domain": domain,
        "spf": spf_policy,
        "dmarc": dmarc_policy,
        "dmarc_source": dmarc_source,
        "mx": bool(mx),
        "provider": classify_provider(mx),
        "score": score(spf_policy, dmarc_policy, bool(mx)),
        "checked": datetime.now(timezone.utc).isoformat(),
    }


# --- reporting ---------------------------------------------------------------

def describe(result):
    """The one-sentence version of the finding, in the words used on the call."""
    if result["dmarc"] is None:
        return "kein DMARC - Domain ist frei fälschbar"
    if result["dmarc"] == "none":
        return "DMARC p=none - überwacht nur, schützt nicht"
    if result["dmarc"] == "quarantine":
        return "DMARC p=quarantine - halber Schutz"
    return "DMARC aktiv"


def format_prospect(result, entry):
    name = (entry or {}).get("name", result["domain"])
    bits = [f"{name} ({result['domain']})", f"  {describe(result)}"]
    detail = []
    if result["spf"] is None:
        detail.append("kein SPF")
    elif result["spf"] in ("+all", "?all", "none"):
        detail.append(f"SPF {result['spf']} (wirkungslos)")
    if result["provider"] not in ("unknown", "no MX"):
        detail.append(result["provider"])
    elif result["provider"] == "no MX":
        detail.append("kein MX")
    if detail:
        bits.append("  " + " · ".join(detail))
    return "\n".join(bits)


def rank(results, domains, limit=5, min_score=6):
    """Best prospects first. min_score=6 means, in practice, no DMARC plus real
    mail flow - the ones actually worth a phone call."""
    # Ties break randomly, not alphabetically. There are ~660 leads and the
    # brief shows 3 a day; sorting ties by domain name would serve
    # "Agrar..., Apotheke..., Apotheke..." for a month before reaching B.
    # Seeded per day so the same day's list is stable across reruns.
    seed = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    jitter = random.Random(seed)
    keyed = [(r, jitter.random()) for r in results.values()
             if r.get("score", 0) >= min_score]
    ranked = [r for r, _ in sorted(keyed, key=lambda pair: (-pair[0]["score"], pair[1]))]
    return [(r, domains.get(r["domain"])) for r in ranked[:limit]]


def build_brief_section(results, domains, reported, limit=3):
    """The morning-brief section. Only ever shows prospects not yet reported,
    so the digest is a worklist rather than the same five names every day."""
    fresh = {d: r for d, r in results.items() if d not in reported}
    top = rank(fresh, domains, limit=limit)
    if not top:
        total = sum(1 for r in results.values() if r.get("score", 0) >= 6)
        if not total:
            return None
        return f"DMARC-Leads: keine neuen. {total} offene im Bestand."
    remaining = sum(1 for r in fresh.values() if r.get("score", 0) >= 6) - len(top)
    lines = [f"DMARC-Leads ({len(top)} neu):"]
    for result, entry in top:
        lines.append(format_prospect(result, entry))
    if remaining > 0:
        lines.append(f"  (+{remaining} weitere neue)")
    return "\n".join(lines)


# --- state -------------------------------------------------------------------

def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def load_reported():
    """Domains already shown in a morning brief. Kept separate from results so
    that re-auditing a domain never accidentally re-surfaces it as new."""
    return set(_load(REPORTED_PATH, []))


def mark_reported(domains):
    _save(REPORTED_PATH, sorted(load_reported() | set(domains)))


def morning_section(limit=3):
    """The whole morning-brief contribution, in one call that cannot raise.

    morning_brief.py is the thing Felix actually relies on every day; a broken
    prospect file must degrade to a missing section, never to a missing digest.
    """
    try:
        results, domains = _load(RESULTS_PATH, {}), _load(DOMAINS_PATH, {})
        reported = load_reported()
        section = build_brief_section(results, domains, reported, limit=limit)
        shown = [r["domain"] for r, _ in rank(
            {d: r for d, r in results.items() if d not in reported},
            domains, limit=limit)]
        return section, shown
    except Exception as e:  # noqa: BLE001
        print(f"prospector section unavailable: {e}", file=sys.stderr)
        return None, []


def due_for_check(domains, results, budget=NIGHTLY_BUDGET):
    """Never-checked domains first, then the stalest. Returns at most `budget`."""
    cutoff = time.time() - RECHECK_AFTER_DAYS * 86400
    never, stale = [], []
    for domain in domains:
        result = results.get(domain)
        if not result:
            never.append(domain)
            continue
        try:
            checked = datetime.fromisoformat(result["checked"]).timestamp()
        except (KeyError, ValueError):
            never.append(domain)
            continue
        if checked < cutoff:
            stale.append((checked, domain))
    # Shuffled, not alphabetical. Auditing in sorted order means the first
    # nights return only A-names, so the morning brief shows "Adler-Apotheke,
    # AED-Service, Ärztehaus..." for a week instead of a spread across the
    # whole region. Seeded per-day so a rerun on the same day is stable.
    random.Random(datetime.now(timezone.utc).strftime("%Y-%m-%d")).shuffle(never)
    stale.sort()
    return (never + [d for _, d in stale])[:budget]


# --- commands ----------------------------------------------------------------

def cmd_discover(verbose=True):
    areas = parse_areas(open(AREAS_PATH, encoding="utf-8").read()) \
        if os.path.exists(AREAS_PATH) else []
    if not areas:
        print(f"No areas configured in {AREAS_PATH}", file=sys.stderr)
        return 1
    domains = _load(DOMAINS_PATH, {})
    added = 0
    for i, area in enumerate(areas):
        if i:
            time.sleep(OVERPASS_AREA_DELAY)
        query = build_overpass_query(area["lat"], area["lon"], area["radius"])
        try:
            payload = fetch_overpass(query)
        except Exception as e:  # noqa: BLE001
            print(f"{area['name']}: Overpass failed: {e}", file=sys.stderr)
            continue
        found = parse_overpass(payload)
        for domain, entry in found.items():
            if domain not in domains:
                domains[domain] = entry
                added += 1
        if verbose:
            print(f"{area['name']}: {len(found)} businesses, {added} new so far")
    _save(DOMAINS_PATH, domains)
    print(f"{len(domains)} domains known ({added} added).")
    return 0


def cmd_audit(limit=None, verbose=True):
    domains = _load(DOMAINS_PATH, {})
    if not domains:
        print("No domains yet - run --discover first.", file=sys.stderr)
        return 1
    results = _load(RESULTS_PATH, {})
    todo = due_for_check(domains, results, budget=limit or NIGHTLY_BUDGET)
    if verbose:
        print(f"{len(domains)} domains known, checking {len(todo)}")
    for i, domain in enumerate(todo, 1):
        results[domain] = audit_domain(domain)
        if i % CHECKPOINT_EVERY == 0:
            _save(RESULTS_PATH, results)
            if verbose:
                print(f"  ...{i}/{len(todo)} (checkpointed)")
        time.sleep(DNS_DELAY)
    _save(RESULTS_PATH, results)
    hot = sum(1 for r in results.values() if r.get("score", 0) >= 6)
    print(f"checked {len(todo)}; {hot} qualified leads in {len(results)} audited")
    return 0


def cmd_report(limit=10):
    domains, results = _load(DOMAINS_PATH, {}), _load(RESULTS_PATH, {})
    top = rank(results, domains, limit=limit)
    if not top:
        print("No qualified leads yet.")
        return 0
    for result, entry in top:
        print(format_prospect(result, entry))
        print()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Find local businesses with spoofable email domains.")
    ap.add_argument("--discover", action="store_true", help="refresh the domain list from OpenStreetMap")
    ap.add_argument("--audit", action="store_true", help="run DNS checks on domains due for one")
    ap.add_argument("--report", action="store_true", help="print the current top leads")
    ap.add_argument("--limit", type=int, help="cap domains audited / leads reported")
    args = ap.parse_args()

    if args.report:
        sys.exit(cmd_report(limit=args.limit or 10))
    if args.discover:
        rc = cmd_discover()
        if rc or not args.audit:
            sys.exit(rc)
    sys.exit(cmd_audit(limit=args.limit))

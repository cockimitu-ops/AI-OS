#!/usr/bin/env python3
"""Finds current, genuinely relevant GitHub repos and tech discussion for
AI-OS to consider adopting - deterministic fetch, never the LLM's own
free-form web search.

Why fetch-then-reason instead of letting the model search: this session's
own history is the reason. The free-tier models this worker runs on
struggled even to synthesize a clean answer to a simple lookup question
(see aios_runner.py's synthesis-nudge fix) and got a file path wrong on a
genuine build task. Letting a model that unreliable freely improvise web
scraping for "AI news" would produce inconsistent, possibly fabricated
results with no way to tell real findings from hallucinated ones. Every
other data-gathering feature in this project (dmarc_prospector.py,
kleinanzeigen_sniper.py) follows the same split: a tested, deterministic
script does the fetching against a real documented API, the LLM only
reasons over what was actually found.

Two free, official, documented, unauthenticated APIs:
  - GitHub Search API (api.github.com/search/repositories) - rate limited
    to 10 req/min unauthenticated; this script sends a handful of queries
    once a day, nowhere near that.
  - HN via Algolia (hn.algolia.com/api/v1/search_by_date) - the real,
    stable search API; the raw Firebase HN API has no search, only
    story-ID lists, which is why this project uses Algolia's instead.

Deliberately scoped to a handful of topics that actually match what this
vault has built - not generic "AI news", which would just be noise. Each
topic doubles as a GitHub query and an HN query, so relevance comes from
the query itself, not a post-hoc filter guessing at what matters.

Stdlib only, matching every other script in this folder.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(TASK_RUNNER_DIR, "techscout")
SEEN_PATH = os.path.join(STATE_DIR, "seen.json")
DIGEST_PATH = os.path.join(STATE_DIR, "digest.md")

UA = "AI-OS-tech-scout/1.0 (personal research; contact felix.haubold143@gmail.com)"
HTTP_TIMEOUT = 20

# Each topic is a real search query for BOTH APIs, not a keyword filter
# applied after a generic fetch - this is what keeps a small daily run
# relevant instead of noisy. Chosen to match what this vault has actually
# built, not "AI" in general:
#   - the exact stack aios_runner.py runs on (Open Interpreter, litellm) -
#     a real upgrade or alternative there is directly actionable
#   - the DMARC business (leg 2)
#   - the web client just built (PWA)
#   - MODEL_CHAIN's whole economics (free/cheap LLM APIs)
TOPICS = [
    ("agent-runtime", "open interpreter OR litellm agent runtime"),
    ("email-security", "DMARC OR SPF OR email-spoofing"),
    ("pwa-offline", 'PWA OR "progressive web app" offline-first'),
    ("free-llm-api", "free llm api OR openrouter OR groq inference"),
]
# All four topics use explicit OR between alternative terms - verified live
# 2026-08-31 that bare multi-word queries are AND-all-terms on GitHub's
# search, not OR: "DMARC SPF email spoofing" (no OR) matched zero repos
# because it demanded all four words together, while "DMARC OR SPF OR
# email-spoofing" correctly found real, current results. A query that
# looks reasonable and silently returns nothing is worse than one that
# errors - it just makes a topic look quiet when it's actually broken.

# Deliberately conservative thresholds. The point is a short, high-signal
# list Felix's agent can reason about carefully, not a firehose - a daily
# review works only if it stays small enough to actually read.
GITHUB_MIN_STARS = 15
GITHUB_LOOKBACK_DAYS = 30
GITHUB_PER_TOPIC = 3

HN_MIN_POINTS = 15
HN_LOOKBACK_DAYS = 5
HN_PER_TOPIC = 3


# --- fetch: network, no logic ------------------------------------------

def _get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def fetch_github(query, since_days=GITHUB_LOOKBACK_DAYS, min_stars=GITHUB_MIN_STARS):
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y-%m-%d")
    q = f"{query} created:>{since} stars:>={min_stars}"
    url = ("https://api.github.com/search/repositories?"
          + urllib.parse.urlencode({"q": q, "sort": "stars", "order": "desc", "per_page": 10}))
    try:
        data = _get_json(url, headers={"Accept": "application/vnd.github+json"})
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"[!] GitHub search failed for {query!r}: {e}", file=sys.stderr)
        return []
    return data.get("items", [])


def fetch_hn(query, since_days=HN_LOOKBACK_DAYS):
    since_ts = int((datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp())
    url = ("https://hn.algolia.com/api/v1/search_by_date?"
          + urllib.parse.urlencode({
              "query": query, "tags": "story",
              "numericFilters": f"created_at_i>{since_ts}",
          }))
    try:
        data = _get_json(url)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"[!] HN search failed for {query!r}: {e}", file=sys.stderr)
        return []
    return data.get("hits", [])


# --- normalize + filter: pure --------------------------------------------

def normalize_github(item, topic):
    return {
        "source": "github",
        "topic": topic,
        "id": f"gh:{item['full_name']}",
        "title": item["full_name"],
        "description": (item.get("description") or "").strip(),
        "url": item["html_url"],
        "score": item.get("stargazers_count", 0),
        "score_label": "stars",
    }


def normalize_hn(hit, topic):
    return {
        "source": "hn",
        "topic": topic,
        "id": f"hn:{hit['objectID']}",
        "title": hit.get("title") or "(untitled)",
        "description": "",
        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
        "score": hit.get("points") or 0,
        "score_label": "points",
    }


def filter_hn_by_points(hits, min_points=HN_MIN_POINTS):
    return [h for h in hits if (h.get("points") or 0) >= min_points]


# --- state -----------------------------------------------------------------

def load_seen():
    try:
        with open(SEEN_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, json.JSONDecodeError):
        return set()


def save_seen(seen):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = SEEN_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=1)
    os.replace(tmp, SEEN_PATH)


# --- digest ----------------------------------------------------------------

def render_digest(candidates, now=None):
    """New candidates -> the Markdown file the agent actually reads. Absent
    entirely (not an empty-but-present file) when there is nothing new -
    the schedule task checks for the file's existence before running the
    LLM at all, so a quiet day costs zero tokens, not a wasted call that
    reads an empty digest and has to invent something to say about it."""
    if not candidates:
        return None
    now = now or datetime.now(timezone.utc)
    lines = [f"# Tech Scout — {now.strftime('%Y-%m-%d')}", "",
             "New candidates since the last run, not previously surfaced:", ""]
    by_topic = {}
    for c in candidates:
        by_topic.setdefault(c["topic"], []).append(c)
    for topic, items in by_topic.items():
        lines.append(f"## {topic}")
        for c in sorted(items, key=lambda x: -x["score"]):
            desc = f" — {c['description']}" if c["description"] else ""
            lines.append(f"- **{c['title']}** ({c['score']} {c['score_label']}){desc}")
            lines.append(f"  {c['url']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


# --- command -----------------------------------------------------------

def run(verbose=True):
    seen = load_seen()
    all_candidates = []

    for i, (topic, query) in enumerate(TOPICS):
        if i:
            time.sleep(2)  # stay well clear of GitHub's 10/min search limit
        gh_items = [normalize_github(it, topic) for it in fetch_github(query)]
        time.sleep(1)
        hn_hits = filter_hn_by_points(fetch_hn(query))
        hn_items = [normalize_hn(h, topic) for h in hn_hits]

        gh_new = [c for c in gh_items if c["id"] not in seen][:GITHUB_PER_TOPIC]
        hn_new = [c for c in hn_items if c["id"] not in seen][:HN_PER_TOPIC]
        all_candidates += gh_new + hn_new
        seen.update(c["id"] for c in gh_new + hn_new)
        if verbose:
            print(f"{topic}: {len(gh_items)} GitHub / {len(hn_items)} HN fetched, "
                 f"{len(gh_new)}+{len(hn_new)} new")

    save_seen(seen)
    digest = render_digest(all_candidates)
    os.makedirs(STATE_DIR, exist_ok=True)
    if digest:
        with open(DIGEST_PATH, "w", encoding="utf-8") as f:
            f.write(digest)
    elif os.path.exists(DIGEST_PATH):
        # No new candidates today - remove yesterday's file rather than leave
        # it sitting there for the schedule task to misread as still current.
        os.remove(DIGEST_PATH)

    print(f"{len(all_candidates)} new candidate(s) total"
         + (f" -> {DIGEST_PATH}" if digest else " - no digest written"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fetch current relevant GitHub repos + HN discussion.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    sys.exit(run(verbose=not args.quiet))

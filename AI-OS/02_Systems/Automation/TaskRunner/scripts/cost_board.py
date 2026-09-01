#!/usr/bin/env python3
"""What the AI-OS actually costs, in one place.

Felix asked for "einen api costen tab wo steht was der spass kostet und wo
direkt ein link ist zum mehr aufladen". Two very different kinds of money end
up in that answer, and mixing them would be misleading:

  OpenRouter  Real, prepaid, and spendable. Balance and usage come live from
              OpenRouter's own API, so the number is theirs, not a local
              guess - and the local ledger (spend_guard.py) says how much of
              the monthly cap is gone. This is the one with a top-up link,
              because it is the one that can run out.

  Claude      The chat from the phone resumes a Claude Code session, which
              runs on Felix's subscription. Nothing is billed per turn. The
              figures here are what those turns WOULD cost at API list price
              - useful for seeing which conversation is expensive to keep
              going, and deeply misleading if read as an invoice. Everything
              that returns it labels it as an estimate.

The Claude side is cached per transcript file, keyed on (mtime, size): the
session archive is ~45 MB and re-reading all of it to draw a screen would
make the tab the slowest thing in the app.

Stdlib only.
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import claude_chat
import spend_guard

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
CACHE_PATH = os.path.join(TASK_RUNNER_DIR, "spend", "claude_cost_cache.json")

OPENROUTER_CREDITS_URL = "https://openrouter.ai/api/v1/credits"
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"
# Where Felix tops up. Deliberately the settings page rather than a checkout
# deep link: a page that shows the balance before asking for money is the
# right place to land when the reason you clicked was "how much is left".
OPENROUTER_TOPUP_URL = "https://openrouter.ai/settings/credits"
# Short. This runs inside a request the app is waiting on, and a cost screen
# that hangs because OpenRouter is slow is worse than one that says the
# balance could not be fetched.
HTTP_TIMEOUT_S = 8


def _get_json(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as r:
        return json.loads(r.read().decode("utf-8"))


def openrouter():
    """Live balance and usage. Never raises - a missing key or a network
    failure is reported as part of the answer, not instead of it."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    budget = float(os.environ.get("OPENROUTER_MONTHLY_BUDGET_USD",
                                  spend_guard.DEFAULT_MONTHLY_BUDGET_USD))
    ledger = spend_guard.load_ledger()
    month = spend_guard.month_key()
    out = {
        "topup_url": OPENROUTER_TOPUP_URL,
        "budget_usd": budget,
        "month": month,
        "month_spent_usd": round(spend_guard.month_spent(ledger, month), 4),
        "months": {k: round(v, 4) for k, v in sorted(ledger.items(), reverse=True)},
        "paid_enabled": os.environ.get("OPENROUTER_PAID_ENABLED", "").lower() == "true",
        "paid_model": os.environ.get("OPENROUTER_PAID_MODEL",
                                     "openrouter/z-ai/glm-5.2"),
        "calls": spend_guard.recent_calls(limit=40),
    }
    out["budget_left_usd"] = round(max(budget - out["month_spent_usd"], 0.0), 4)
    if not key:
        out["live"] = False
        out["error"] = "OPENROUTER_API_KEY ist nicht gesetzt"
        return out
    try:
        credits = _get_json(OPENROUTER_CREDITS_URL, key).get("data") or {}
        total = float(credits.get("total_credits") or 0.0)
        used = float(credits.get("total_usage") or 0.0)
        out.update({"live": True, "credits_usd": round(total, 4),
                    "used_usd": round(used, 4),
                    "balance_usd": round(total - used, 4)})
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as e:
        out["live"] = False
        out["error"] = f"Guthaben nicht abrufbar: {str(e)[:120]}"
        return out
    try:
        info = _get_json(OPENROUTER_KEY_URL, key).get("data") or {}
        out["usage"] = {
            "today": round(float(info.get("usage_daily") or 0.0), 4),
            "week": round(float(info.get("usage_weekly") or 0.0), 4),
            "month": round(float(info.get("usage_monthly") or 0.0), 4),
        }
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        # The balance is the part that matters; a missing usage breakdown is
        # not worth downgrading the whole panel for.
        pass
    return out


# --- Claude Code side ----------------------------------------------------

def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, CACHE_PATH)
    except OSError:
        pass


def _month_of(ts):
    """YYYY-MM from a transcript timestamp, or None if it cannot be read."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).strftime("%Y-%m")
    except ValueError:
        return None


def _scan_session(path):
    """-> {"months": {...}, "usd": total, "turns": n} for one transcript."""
    months, total, turns = {}, 0.0, 0
    for row in claude_chat._iter_rows(path):
        if row.get("type") != "assistant":
            continue
        msg = row.get("message") or {}
        usd, _ = claude_chat.usage_cost(msg.get("usage"), msg.get("model"))
        total += usd
        turns += 1
        key = _month_of(row.get("timestamp"))
        if key:
            months[key] = round(months.get(key, 0.0) + usd, 6)
    return {"months": months, "usd": round(total, 4), "turns": turns}


def claude_sessions(project=None):
    """Estimated list-price cost of every Claude Code session, newest first.

    Cached per file on (mtime, size). Only a transcript that actually changed
    is re-read, which is what keeps this off the critical path of a screen -
    the archive is tens of megabytes and one session alone is 23 of them."""
    directory = claude_chat.sessions_dir(project)
    try:
        names = sorted(n for n in os.listdir(directory) if n.endswith(".jsonl"))
    except OSError:
        return []
    cache = _load_cache()
    changed = False
    out = []
    for name in names:
        full = os.path.join(directory, name)
        try:
            stat = os.stat(full)
        except OSError:
            continue
        hit = cache.get(name)
        if not hit or hit.get("mtime") != stat.st_mtime or hit.get("size") != stat.st_size:
            hit = _scan_session(full)
            hit.update({"mtime": stat.st_mtime, "size": stat.st_size})
            cache[name] = hit
            changed = True
        out.append({
            "id": name[:-len(".jsonl")],
            "usd": hit["usd"],
            "turns": hit["turns"],
            "months": hit.get("months", {}),
            "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "updated_ago": int(time.time() - stat.st_mtime),
        })
    # Entries for transcripts that no longer exist would grow the cache
    # forever; the listing is the authority on what still does.
    for stale in set(cache) - set(names):
        cache.pop(stale, None)
        changed = True
    if changed:
        _save_cache(cache)
    out.sort(key=lambda s: s["updated_ago"])
    return out


def claude_summary(project=None):
    """Totals across all sessions, plus this month's - list price, estimated."""
    sessions = claude_sessions(project)
    month = datetime.now().strftime("%Y-%m")
    by_month = {}
    for s in sessions:
        for k, v in (s.get("months") or {}).items():
            by_month[k] = round(by_month.get(k, 0.0) + v, 4)
    return {
        "estimate": True,
        "note": ("Listenpreis-Schätzung. Läuft über dein Claude-Abo - "
                 "es wird nichts pro Nachricht abgerechnet."),
        "total_usd": round(sum(s["usd"] for s in sessions), 2),
        "month_usd": round(by_month.get(month, 0.0), 2),
        "months": dict(sorted(by_month.items(), reverse=True)),
        "sessions": sessions[:12],
        "pricing": claude_chat.PRICING,
    }


def board(project=None):
    return {"openrouter": openrouter(), "claude": claude_summary(project),
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds")}


if __name__ == "__main__":
    print(json.dumps(board(), indent=1, ensure_ascii=False)[:3000])

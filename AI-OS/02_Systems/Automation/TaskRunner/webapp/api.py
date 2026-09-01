#!/usr/bin/env python3
"""Request handlers for the AI-OS web client. Every handler returns
(http_status, json_serializable_payload) - server.py owns all HTTP mechanics,
this file only ever touches the data.

Every dashboard handler is a live read through the SAME functions the CLI
tools already use (money_board.py, dmarc_prospector.py, flip_log.py) -
nothing here re-implements scoring, ranking, or table parsing. If a number
looks wrong here, the fix belongs in that module, not in this one - see the
approved plan (~/.claude/plans/virtual-tumbling-locket.md) for why that
separation matters.

The chat handler builds a task file the exact same way dispatch_task.py does
(read that file if this one is ever unclear) and blocks on the result the
same way - single user, one message in flight, no reason for anything
fancier.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import agents
import memory
import money_board
import dmarc_prospector
import flip_log
import phone_root
import proposals
import snipe_rank
import study_agent
import vault_write

TASK_RUNNER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
LOGS = os.path.join(TASK_RUNNER_DIR, "tasks", "logs")
CHAT_TIMEOUT_S = 170  # stays under the 180s dispatch_task.py/telegram_bridge.py already use
UPLOAD_DIR = os.path.join(TASK_RUNNER_DIR, "uploads")
# Passed to voice_import.py explicitly rather than letting it fall back to
# its own default. Its default is the same directory, so this changes nothing
# in production - but it makes the destination something a caller can point
# elsewhere, and a test that could not do that wrote a profile built from
# fixture data straight into the live one.
VOICE_DIR = os.path.join(TASK_RUNNER_DIR, "voice")
# A WhatsApp export without media is a few hundred KB of text; 25 MB is
# already generous. The cap exists because this endpoint reads the body into
# memory before writing it - server.py refuses on Content-Length before any
# of it is read, so an oversized POST costs nothing.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# Deliberately narrow: the only thing this is for is getting chat exports and
# similar plain data onto the server. Anything executable or web-servable
# would be a genuinely different feature with genuinely different questions
# to answer first.
ALLOWED_UPLOAD_EXT = (".txt", ".zip", ".csv", ".json", ".md",
                      # Photos: needed both for sending a design reference and
                      # for the photo-to-notes path (Felix does not type notes
                      # on his phone, he photographs slides and boards).
                      ".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf")
UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ ()\u00c0-\u024f-]")


# --- phone ---------------------------------------------------------------

# Notification packages that are never worth surfacing: system plumbing and
# persistent media controls. An assistant that reports "Android System" and a
# paused Spotify track as things needing attention teaches you to ignore it.
PHONE_NOISE = {
    "android", "com.android.systemui", "com.android.settings",
    "com.miui.securitycenter", "com.miui.powerkeeper", "com.xiaomi.misettings",
    "com.google.android.gms", "com.android.providers.downloads",
    "com.spotify.music", "com.miui.player", "com.google.android.apps.youtube.music",
}


def get_phone(_body):
    """Live state of the rooted phone: battery, foreground app, notifications
    worth seeing.

    Degrades rather than fails. The phone is frequently unreachable - out of
    the house on mobile data with the tailnet asleep, rebooted since the last
    `adb tcpip`, or simply off - and none of that should make the home screen
    show an error. Unreachable is a normal state for a phone, not a fault."""
    try:
        state = phone_root.status()
    except Exception as e:  # noqa: BLE001 - see docstring
        return 200, {"reachable": False, "reason": str(e)[:160]}

    try:
        notes = phone_root.notifications()
    except Exception:  # noqa: BLE001
        notes = []
    signal = [n for n in notes if n.get("package") not in PHONE_NOISE]
    return 200, {
        "reachable": True,
        "battery": state.get("battery"),
        "screen_on": state.get("screen_on"),
        "current_app": state.get("current_app"),
        "notifications": signal[:12],
        "notification_total": len(notes),
        "filtered": len(notes) - len(signal),
    }


# --- snipes --------------------------------------------------------------

SNIPE_LIMIT = 60


def get_snipes(body):
    """Sniper finds, ranked into tiers, with filters.

    The tier is a TRIAGE order - which listing to open first - and explicitly
    not a valuation. LocalArbitrage's Valuation_Method.md opens with its own
    rule in bold: "AI does not estimate resale prices. Sold listings do." A
    tier here says "look at this before the others", never "this is worth more
    than it costs"; the resale number still comes from sold comps, by hand.
    Every score ships with the reasons that produced it, because a ranking
    Felix cannot audit is one he is right not to trust."""
    body = body or {}
    tier = body.get("tier") or None
    if isinstance(tier, str):
        tier = [t for t in tier.split(",") if t.strip()]

    def _int(name):
        value = body.get(name)
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    rows = snipe_rank.rank(
        watch=body.get("watch") or None,
        tier=tier,
        max_price=_int("max_price"),
        max_distance=_int("max_distance"),
        limit=min(_int("limit") or SNIPE_LIMIT, SNIPE_LIMIT),
    )
    counts = {}
    for row in snipe_rank.rank():
        counts[row["tier"]] = counts.get(row["tier"], 0) + 1
    return 200, {
        "snipes": rows,
        "watches": snipe_rank.watches(),
        # Unfiltered tier totals, so the filter chips can show what exists
        # rather than what survived the current filter.
        "tier_counts": counts,
        "total": sum(counts.values()),
    }


# --- vault ---------------------------------------------------------------

VAULT = vault_write.VAULT
# Bounded on purpose. These are read by MCP clients whose whole cost model is
# tokens: an unbounded grep over 280+ vault files would hand a model tens of
# thousands of tokens of context to answer "what is the DMARC project", which
# is both expensive and worse than a focused answer.
VAULT_MAX_HITS = 20
VAULT_SNIPPET_CHARS = 240
VAULT_MAX_PAGE_CHARS = 20_000
# Folders that are machine state or vendored code, not knowledge. Searching
# them returns noise (node_modules) or churn (task logs) and buries the notes.
VAULT_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "backups", "tasks",
                   "uploads", "voice", "spend", "prospects", "study", "techscout"}


def _vault_files():
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in VAULT_SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name.endswith(".md"):
                yield os.path.join(root, name)


def get_vault_search(body):
    """Keyword search across the vault's Markdown. -> ranked hits with
    snippets.

    Reads the real files rather than Notion. The existing AI-OSmcp server
    queried Notion, which is a copy: everything that actually matters now -
    the money board, the leads, the flip log, proposals - lives in files here
    and was never in Notion at all. A search that answers from the copy would
    confidently describe a system that no longer exists."""
    query = (body.get("query") or "").strip()
    if len(query) < 2:
        return 400, {"error": "query must be at least 2 characters"}
    limit = min(int(body.get("limit") or VAULT_MAX_HITS), VAULT_MAX_HITS)
    needle = query.lower()
    hits = []
    for path in _vault_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        low = text.lower()
        count = low.count(needle)
        if not count:
            continue
        where = low.find(needle)
        start = max(0, where - VAULT_SNIPPET_CHARS // 3)
        snippet = text[start:start + VAULT_SNIPPET_CHARS].replace("\n", " ").strip()
        hits.append({
            "page": os.path.relpath(path, VAULT),
            "matches": count,
            "snippet": ("..." if start else "") + snippet + "...",
        })
    # Most matches first: a page that mentions the term twenty times is
    # almost always the page about it, and a title match is worth more than
    # a passing mention, so exact-name hits get pushed to the top.
    hits.sort(key=lambda h: (needle in os.path.basename(h["page"]).lower(),
                             h["matches"]), reverse=True)
    return 200, {"query": query, "total": len(hits), "hits": hits[:limit]}


def get_vault_page(body):
    """One page's full Markdown, by vault-relative path or bare name."""
    name = (body.get("page") or "").strip()
    if not name:
        return 400, {"error": "page is required"}
    # Same containment check vault_write.py uses for writes: resolve first,
    # then verify the result is still inside the vault, so "../../.ssh/id_rsa"
    # cannot be read back through an endpoint meant for notes.
    candidates = []
    direct = os.path.realpath(os.path.join(VAULT, name))
    if direct.startswith(os.path.realpath(VAULT) + os.sep) and os.path.isfile(direct):
        candidates.append(direct)
    if not candidates:
        stem = name.lower().removesuffix(".md")
        for path in _vault_files():
            if os.path.basename(path).lower().removesuffix(".md") == stem:
                candidates.append(path)
                break
    if not candidates:
        return 404, {"error": f"no vault page matching {name!r}"}
    try:
        with open(candidates[0], encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        return 500, {"error": str(e)}
    truncated = len(text) > VAULT_MAX_PAGE_CHARS
    return 200, {
        "page": os.path.relpath(candidates[0], VAULT),
        "truncated": truncated,
        "content": text[:VAULT_MAX_PAGE_CHARS],
    }


# --- today ---------------------------------------------------------------

def _load_json(path):
    """Never raises: a missing or half-written state file means that one
    signal is unknown, not that the home screen fails to render."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _sniper_state():
    """Last sniper run and how many ads it has ever flagged. Never raises -
    a missing state file means the sniper has not run, not that the home
    screen is broken."""
    state = _load_json(os.path.join(TASK_RUNNER_DIR, "watches", "state.json"))
    alerted = state.get("alerted") or {}
    return {
        "last_run": state.get("last_run"),
        "alerted": len(alerted) if isinstance(alerted, (dict, list)) else 0,
    }


def get_today(_body):
    """Everything the home screen shows, in one request.

    One endpoint rather than five: this is the first screen on a phone, and
    five round trips over a tailnet is the difference between "instant" and
    "loading". Every field is a live read through the same modules the CLI
    uses - nothing here keeps its own copy of anything.

    Every section degrades on its own. A broken flip log must not blank the
    money board next to it, because the home screen is the one view that has
    to be trustworthy at a glance."""
    signals = money_board.live_signals()
    actions = money_board.sorted_actions()
    top = actions[0] if actions else None

    try:
        review = proposals.load_review() or {}
        pending_proposals = len(review.get("items") or [])
    except Exception:  # noqa: BLE001 - optional signal, never fatal
        pending_proposals = 0

    try:
        study_pending = study_agent.pending_count()
    except Exception:  # noqa: BLE001
        study_pending = 0

    return 200, {
        "next_action": None if not top else {
            "action": top[1], "euros": top[2], "minutes": top[3],
            "note": top[4], "gates": top[0] == "felix-first",
        },
        "open_actions": len(actions),
        "signals": signals,
        "proposals_pending": pending_proposals,
        "study_pending": study_pending,
        "sniper": _sniper_state(),
    }


# --- dashboards --------------------------------------------------------

def get_money_board(_body):
    # money_board.sorted_actions() owns the ordering - gating rows first,
    # then euros descending. This handler used to re-implement the sort
    # (`sorted(felix_actions(), key=-euros)`), which was itself the fix for a
    # real bug where it did not sort at all; keeping a second copy of the rule
    # here meant the dashboard silently disagreed with the CLI the moment the
    # rule changed. One function, three callers.
    actions = [
        {"action": action, "euros": euros, "minutes": minutes, "note": note,
         "gates": who == "felix-first"}
        for who, action, euros, minutes, note in money_board.sorted_actions()
    ]
    return 200, {"actions": actions, "signals": money_board.live_signals()}


def get_dmarc_leads(_body):
    domains = dmarc_prospector._load(dmarc_prospector.DOMAINS_PATH, {})
    results = dmarc_prospector._load(dmarc_prospector.RESULTS_PATH, {})
    # 100, not the CLI's default 5 - a dashboard has room to scroll a real
    # list; the top-5 default belongs to the terse morning-brief message, not
    # a screen built to be looked at directly.
    top = dmarc_prospector.rank(results, domains, limit=100)
    leads = [{
        "domain": result["domain"],
        "name": (entry or {}).get("name", result["domain"]),
        "category": (entry or {}).get("category"),
        "score": result.get("score"),
        "dmarc": result.get("dmarc"),
        "spf": result.get("spf"),
        "provider": result.get("provider"),
        "address": (entry or {}).get("address"),
        "phone": (entry or {}).get("phone"),
    } for result, entry in top]
    total_qualified = sum(1 for r in results.values() if r.get("score", 0) >= 6)
    return 200, {"leads": leads, "total_qualified": total_qualified}


def get_flip_log(_body):
    rows = flip_log.read_log()
    for row in rows:
        row["open"] = not bool(row.get("Sold €"))
    return 200, {"rows": rows}


DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "static", "downloads")


def get_downloads(_body):
    """Files the worker generated for Felix to pull down - PDFs from a chat
    request most commonly, per how this was actually asked for ("let the
    workers pull data and create pdfs i can download"). Served by
    server.py's existing static-file path (already path-traversal-tested)
    at /downloads/<name> - this endpoint only lists what's there, it does
    not serve the bytes itself."""
    try:
        names = [n for n in os.listdir(DOWNLOADS_DIR) if not n.startswith(".")]
    except OSError:
        names = []
    files = []
    for name in names:
        full = os.path.join(DOWNLOADS_DIR, name)
        try:
            stat = os.stat(full)
        except OSError:
            continue
        files.append({
            "name": name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "url": f"/downloads/{name}",
        })
    files.sort(key=lambda f: f["modified"], reverse=True)
    return 200, {"files": files}


# --- uploads -------------------------------------------------------------

def safe_upload_name(raw):
    """-> a filename that can only ever land directly in UPLOAD_DIR.

    basename() first so "../../.ssh/authorized_keys" becomes
    "authorized_keys", then the extension allowlist, then a character scrub.
    Order matters: checking the extension before stripping directories would
    happily accept "../../x.txt"."""
    name = os.path.basename((raw or "").strip().replace("\\", "/"))
    # Strips leading dots and surrounding spaces (no hidden files, no
    # trailing-space names) but NOT underscores: iOS names every WhatsApp
    # export literally "_chat.txt", and silently renaming his files is a
    # confusing thing for an upload button to do.
    name = UNSAFE_NAME_RE.sub("_", name).strip(" ").lstrip(".")
    if not name or len(name) > 120:
        return None
    if not name.lower().endswith(ALLOWED_UPLOAD_EXT):
        return None
    return name


def _unique_path(name):
    """Never silently overwrite. Four WhatsApp exports can arrive as four
    files called "_chat.txt" - iOS names every single one of them that -
    and losing three of them to the fourth would be invisible until the
    voice profile came out built on a quarter of the data."""
    base, ext = os.path.splitext(name)
    candidate, n = name, 2
    while os.path.exists(os.path.join(UPLOAD_DIR, candidate)):
        candidate = f"{base}_{n}{ext}"
        n += 1
    return os.path.join(UPLOAD_DIR, candidate), candidate


def post_upload(query, raw):
    """Raw request body -> one file in uploads/.

    Deliberately not multipart/form-data: this client is the only thing that
    will ever call this endpoint, so there is no interop reason to hand-roll
    a multipart parser (the stdlib's cgi module, which used to do it, was
    removed in Python 3.13 - this service runs 3.14). One file per request,
    filename in the query string, bytes in the body. The frontend loops."""
    name = safe_upload_name((query.get("name") or [""])[0])
    if not name:
        return 400, {"error": "invalid or unsupported filename "
                              f"(allowed: {', '.join(ALLOWED_UPLOAD_EXT)})"}
    if not raw:
        return 400, {"error": "empty file"}
    if len(raw) > MAX_UPLOAD_BYTES:
        return 413, {"error": "file too large"}
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path, final_name = _unique_path(name)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, path)  # atomic, same reason dispatch_task.py does it
    return 200, {"name": final_name, "size": len(raw)}


def get_uploads(_body):
    try:
        names = [n for n in os.listdir(UPLOAD_DIR)
                 if not n.startswith(".") and not n.endswith(".part")]
    except OSError:
        names = []
    files = []
    for name in names:
        try:
            stat = os.stat(os.path.join(UPLOAD_DIR, name))
        except OSError:
            continue
        files.append({
            "name": name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        })
    files.sort(key=lambda f: f["modified"], reverse=True)
    # No download URL, unlike get_downloads: these are Felix's own private
    # chat exports. He uploaded them, he has them - re-serving them over
    # HTTP would add exposure for no use.
    return 200, {"files": files}


def post_voice_import(_body):
    """Rebuild the voice profile from every .txt currently in uploads/.

    Runs voice_import.py as a subprocess rather than importing it: it is a
    CLI tool with its own argument handling, and a crash in a chat-export
    parser must not be able to take the web server down with it. Fixed argv,
    never a shell string. No model is involved - this is pure parsing and
    arithmetic, so it costs nothing and cannot hallucinate a profile."""
    try:
        txts = sorted(os.path.join(UPLOAD_DIR, n) for n in os.listdir(UPLOAD_DIR)
                      if n.lower().endswith(".txt"))
    except OSError:
        txts = []
    if len(txts) < 2:
        return 400, {"error": "Mindestens 2 Chat-Exporte nötig - aus einem "
                              "einzigen Chat wird das Profil eine Karikatur "
                              "einer Beziehung, nicht deine Stimme."}
    script = os.path.join(TASK_RUNNER_DIR, "scripts", "voice_import.py")
    try:
        proc = subprocess.run([sys.executable, script] + txts
                              + ["--out", VOICE_DIR],
                              capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return 500, {"error": "Import hat zu lange gebraucht"}
    if proc.returncode != 0:
        return 400, {"error": (proc.stderr or "Import fehlgeschlagen").strip()[:500]}
    return 200, {"files": len(txts), "output": proc.stdout.strip()}


# --- chat ----------------------------------------------------------------

def post_chat(body):
    message = (body.get("message") or "").strip()
    thread_id = (body.get("thread_id") or "").strip()
    if not message:
        return 400, {"error": "message is required"}
    if not thread_id:
        return 400, {"error": "thread_id is required"}

    # Same @agent-prefix convention telegram_bridge.py already uses: an
    # unresolved leading word is left alone rather than treated as a failed
    # agent selection, so "@felix should I..." stays a normal sentence.
    agent = None
    if message.startswith("@"):
        head, _, rest = message.partition(" ")
        resolved = agents.resolve(head)
        if resolved:
            agent, message = resolved, rest.strip()
    if not message:
        return 400, {"error": "no message text after the @agent prefix"}

    # `web_` prefix on the client-generated id keeps this namespace distinct
    # from Telegram's `tg_<chat_id>` threads on disk - two front doors, never
    # the same conversation by accident.
    memory_thread = f"web_{thread_id}"
    body_text = (memory.directive(memory_thread)
                + (agents.directive(agent) if agent else "")
                + message)

    for d in (INBOX, LOGS):
        os.makedirs(d, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"task_web_{timestamp}.md"
    task_path = os.path.join(INBOX, filename)
    log_path = os.path.join(LOGS, f"{filename}.log")

    tmp_path = f"{task_path}.part"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(body_text)
    os.replace(tmp_path, task_path)  # atomic enqueue, same reason dispatch_task.py does this

    # Returns immediately with a ticket instead of holding the connection open
    # until the worker finishes.
    #
    # Why this changed: a real message on 2026-09-01 took 93 seconds to answer.
    # The worker produced a perfectly good reply and wrote it to its log - and
    # Felix saw "failed to fetch", because a phone browser does not keep a
    # request open that long. Screen off, app backgrounded, or a network switch
    # and the fetch dies. The answer existed and was unreachable, which is the
    # worst of both outcomes.
    #
    # Polling also makes the reply survive a reload: the ticket is the task
    # filename, so a client that comes back later can still collect it.
    return 200, {"task_id": filename, "pending": True, "agent": agent}


def get_chat_result(body):
    """Collect a queued chat reply. -> pending, ready, or failed.

    Deliberately reports elapsed seconds: the client shows it, so a slow model
    reads as "still thinking, 40s" rather than as a frozen app. That ambiguity
    is what made the old behaviour feel broken."""
    task_id = (body or {}).get("task_id") or ""
    # The ticket becomes a filesystem path, so it is validated as a plain
    # task filename and nothing else.
    if not re.fullmatch(r"task_web_[\w.-]{1,60}\.md", task_id):
        return 400, {"error": "invalid task_id"}

    log_path = os.path.join(LOGS, f"{task_id}.log")
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            return 200, {"ready": True, "reply": f.read().strip()}

    queued = os.path.join(INBOX, task_id)
    running = os.path.join(TASK_RUNNER_DIR, "tasks", "completed", task_id)
    if not os.path.exists(queued) and not os.path.exists(running):
        # Neither waiting, nor finished, nor recorded as done: the task is
        # gone. Saying so beats polling forever against a task that will
        # never produce a log.
        return 200, {"ready": False, "lost": True,
                     "error": "Task nicht mehr auffindbar"}

    try:
        age = int(time.time() - os.path.getmtime(queued if os.path.exists(queued)
                                                 else running))
    except OSError:
        age = 0
    return 200, {"ready": False, "elapsed": age,
                 "timed_out": age > CHAT_TIMEOUT_S}

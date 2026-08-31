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
import os
import time
from datetime import datetime

import agents
import memory
import money_board
import dmarc_prospector
import flip_log

TASK_RUNNER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
LOGS = os.path.join(TASK_RUNNER_DIR, "tasks", "logs")
CHAT_TIMEOUT_S = 170  # stays under the 180s dispatch_task.py/telegram_bridge.py already use


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

    start = time.time()
    while time.time() - start < CHAT_TIMEOUT_S:
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                return 200, {"reply": f.read().strip(), "agent": agent}
        time.sleep(1)

    return 504, {"error": "worker did not respond in time"}

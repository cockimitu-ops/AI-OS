#!/usr/bin/env python3
"""In-app notifications for work that finishes without anyone watching.

WHY NOT TELEGRAM

Every other completion in this codebase that needed to reach Felix reliably
used Telegram, because it is push and a browser tab is not. Felix asked for
background jobs specifically NOT to do that - a background task is something
he chose to fire and forget, and a phone buzz for each one defeats the point.
So this writes to a small store the app polls instead, and the watcher below
exists so that store gets written even if nobody is polling /api/engine-result
at the moment the job actually finishes.

THE WATCHER

A bounded background thread per job, started when /api/background-task is
called, living inside the webapp process (webapp/server.py already runs
ThreadingHTTPServer, so a few long-lived daemon threads cost it nothing it
does not already pay for one per request). It polls engines.result() the same
way a browser would, and stops for exactly one of three reasons: the job
finished, the job was lost, or JOB_TIMEOUT_S ran out - never forever.

Because engines.result() itself performs the limit-handoff (see engines.py),
the watcher has to follow the SAME re-routing a polling browser would: a
handed-off ticket returns a new engine/job, and it is that pair, not the
original one, whose completion actually gets notified. Notifying under the
original engine's name would misattribute the answer to an engine that never
produced it.
"""
import json
import os
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
STORE_PATH = os.path.join(TASK_RUNNER_DIR, "notifications", "notifications.json")
MAX_STORED = 200
# A watcher outlives any single poll, but not forever - matches the same
# ceiling engines.py itself gives up at.
WATCH_TIMEOUT_S = 950

_lock = threading.Lock()


def _load():
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save(rows):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    tmp = STORE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows[-MAX_STORED:], f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE_PATH)


def add(text, conversation_id=None, engine=None, job_id=None):
    """One notification. -> the stored row, or the existing one if job_id
    was already recorded - a job cannot finish twice, and a watcher racing a
    manual poll must not be able to write it twice either."""
    with _lock:
        rows = _load()
        if job_id:
            existing = next((r for r in rows if r.get("job_id") == job_id), None)
            if existing:
                return existing
        row = {
            "id": f"ntf_{time.strftime('%Y%m%d_%H%M%S')}_{len(rows)}",
            "text": str(text or "")[:500],
            "conversation_id": conversation_id,
            "engine": engine,
            "job_id": job_id,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "read": False,
        }
        rows.append(row)
        _save(rows)
        return row


def list_notifications(unread_only=False, limit=50):
    rows = _load()
    if unread_only:
        rows = [r for r in rows if not r.get("read")]
    return list(reversed(rows[-limit:]))


def mark_read(notification_id):
    """-> True if a matching, unread-or-not notification was found."""
    if not notification_id:
        return False
    with _lock:
        rows = _load()
        found = False
        for row in rows:
            if row.get("id") == notification_id:
                row["read"] = True
                found = True
        if found:
            _save(rows)
        return found


def watch_job(engine, job, conversation_id=None, preview=None, record_reply=None):
    """Start a bounded background watcher for one ticket. Fire-and-forget:
    nothing here is awaited by the caller, which is the entire point - the
    HTTP request that started the job returns immediately either way.

    record_reply, if given, is called as record_reply(final_engine,
    final_job, result_dict) once the job is ready - this is how the
    notification path and the conversation-recording path share one
    completion event instead of each polling separately."""
    import engines  # local import: avoids a hard dependency for callers that
                    # only want add()/list_notifications()/mark_read()

    def _run():
        cur_engine, cur_job = engine, job
        deadline = time.time() + WATCH_TIMEOUT_S
        wait = 2.0
        res = None
        while time.time() < deadline:
            try:
                res = engines.result(cur_engine, cur_job)
            except ValueError:
                return
            if res.get("handed_off") and res.get("engine") and res.get("job"):
                # Followed, not reported: the answer has not arrived yet, it
                # has only been re-routed. Notifying now would announce a
                # reply that does not exist.
                cur_engine, cur_job = res["engine"], res["job"]
                continue
            if res.get("ready") or res.get("lost"):
                break
            time.sleep(wait)
            wait = min(wait * 1.2, 15.0)
        else:
            res = {"ready": False, "ok": False,
                  "error": f"Keine Antwort nach {WATCH_TIMEOUT_S}s"}

        if res.get("lost"):
            text = f"{cur_engine}: {res.get('error', 'Auftrag nicht mehr auffindbar')}"
        elif res.get("ok"):
            reply = (res.get("reply") or "").strip()
            text = f"{cur_engine}: {reply[:300]}" if reply else f"{cur_engine} ist fertig."
        else:
            text = f"{cur_engine}: {res.get('error', 'Fehlgeschlagen')[:300]}"
            try:
                import safety_controls
                safety_controls.escalate_error(f"Background Job ({cur_engine})", text)
            except Exception:
                pass
        add(text, conversation_id=conversation_id, engine=cur_engine, job_id=cur_job)
        if record_reply and res.get("ready"):
            try:
                record_reply(cur_engine, cur_job, res)
            except Exception:  # noqa: BLE001 - a recording failure must not
                pass            # crash a background thread nobody is watching

    threading.Thread(target=_run, daemon=True,
                     name=f"watch-{job}").start()

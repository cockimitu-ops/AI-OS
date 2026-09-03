#!/usr/bin/env python3
"""Supervision layer: services up, network has a real default route, last
backup succeeded. Runs on a timer and alerts over the existing Telegram
bridge, rather than waiting for Felix to notice a symptom.

Stdlib only, on purpose - same reasoning as send_telegram_notification.py:
this is exactly the thing that needs to keep working when something else
on the box has already broken, and systemd runs it under /usr/bin/python3,
which has no third-party packages.

Gathering (subprocess/socket/filesystem calls) is kept separate from
evaluation (pure functions on strings/numbers) so the actual pass/fail
logic - the part worth getting right - can be unit tested without mocking
subprocess or touching a real network.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
BACKUP_DIR = os.path.join(TASK_RUNNER_DIR, "backups")
STATE_PATH = os.path.join(TASK_RUNNER_DIR, "health", "state.json")
NOTIFIER = os.path.join(SCRIPT_DIR, "send_telegram_notification.py")

SERVICES = ["aios-worker.service", "aios-telegram.service"]
BACKUP_SERVICE = "aios-backup.service"
LAN_INTERFACE = "eno1"  # the interface that silently lost its IPv4 on 2026-08-30
MAX_BACKUP_AGE_HOURS = 30  # timer runs daily at 03:00 - 30h leaves a few hours' grace
REALERT_SECONDS = 6 * 3600  # don't re-notify an unresolved problem more than every 6h

INBOX = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
# Worst legitimate case per task is roughly MODEL_CHAIN length x
# ATTEMPT_TIMEOUT_S (7 x 300s = 35min), so this has to sit above that or it
# would page on a task that is merely slow. Anything past it means the queue
# is genuinely not draining.
MAX_QUEUE_AGE_MINUTES = 45

SNIPER_STATE = os.path.join(TASK_RUNNER_DIR, "watches", "state.json")
# Sniper timer fires every 3 minutes between 07:00 and 22:59 Europe/Berlin, so
# the gap across a night is ~8h. 10h clears that without hiding a real outage.
# This check exists because the sniper's failure mode is silence, and silence
# is exactly what a working sniper looks like on a quiet afternoon.
MAX_SNIPER_AGE_HOURS = 10

PROSPECTOR_RESULTS = os.path.join(TASK_RUNNER_DIR, "prospects", "results.json")
# Nightly at 01:30, so 26h leaves a few hours' grace. Same reasoning as the
# sniper: a dead prospector looks exactly like a quiet one from the morning
# brief, which would just say "keine neuen" forever.
MAX_PROSPECTOR_AGE_HOURS = 26


# --- gathering: subprocess/socket/filesystem, no logic ---------------------

def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"<error: {e}>"


def gather_service_status(name):
    return _run(["systemctl", "is-active", name])


def gather_sniper_age_hours():
    """-> hours since the sniper last completed a run, or None if it never has."""
    try:
        with open(SNIPER_STATE, encoding="utf-8") as f:
            last = json.load(f).get("last_run")
    except (OSError, json.JSONDecodeError):
        return None
    if not last:
        return None
    try:
        from datetime import datetime
        stamp = datetime.fromisoformat(last)
    except ValueError:
        return None
    return (time.time() - stamp.timestamp()) / 3600.0


def gather_prospector_age_hours():
    """Age of the results file. Its mtime is the run stamp - the audit rewrites
    it on every completed run, so no separate bookkeeping is needed."""
    try:
        return (time.time() - os.path.getmtime(PROSPECTOR_RESULTS)) / 3600.0
    except OSError:
        return None


def gather_backup_is_failed():
    return _run(["systemctl", "is-failed", BACKUP_SERVICE])


def gather_default_route():
    return _run(["ip", "route", "show", "default"])


def gather_iface_addr(iface):
    return _run(["ip", "-4", "addr", "show", iface])


def gather_internet_ok(host="1.1.1.1", port=443, timeout=5):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def gather_oldest_queued_task_age_minutes():
    """Age of the oldest thing sitting in tasks/inbox/, or None if empty.

    This is the only check here that can see a *wedged* worker. `systemctl
    is-active` reports a hung process as healthy - on 2026-08-30 the worker
    sat on one task for 101 minutes and every check above still said OK."""
    try:
        queued = [f for f in os.listdir(INBOX) if f.endswith(".md")]
    except OSError:
        return None
    if not queued:
        return None
    oldest = min(os.path.getmtime(os.path.join(INBOX, f)) for f in queued)
    return (time.time() - oldest) / 60


def gather_newest_backup_age_hours():
    try:
        archives = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")]
    except OSError:
        return None
    if not archives:
        return None
    newest = max(os.path.getmtime(os.path.join(BACKUP_DIR, f)) for f in archives)
    return (time.time() - newest) / 3600


# --- evaluation: pure functions, unit tested --------------------------------

def parse_default_route_interfaces(route_output):
    """['default via 1.2.3.4 dev eno1 ...', ...] -> ['eno1', ...]"""
    return re.findall(r"\bdev\s+(\S+)", route_output)


def evaluate_service(is_active_output):
    ok = is_active_output == "active"
    return ok, is_active_output


def evaluate_network(route_output, iface_addr_output, iface, internet_ok):
    problems = []
    interfaces = parse_default_route_interfaces(route_output)
    if not interfaces:
        problems.append("no default route at all")
    elif iface not in interfaces:
        problems.append(
            f"default route is via {', '.join(interfaces)}, not {iface} - "
            f"LAN uplink may be down and silently failed over"
        )
    if "inet " not in iface_addr_output:
        problems.append(f"{iface} has no IPv4 address")
    if not internet_ok:
        problems.append("cannot reach the internet (1.1.1.1:443)")
    if problems:
        return False, "; ".join(problems)
    return True, f"default route via {iface}, internet reachable"


def evaluate_queue(age_minutes, max_age_minutes=MAX_QUEUE_AGE_MINUTES):
    """An empty queue and a fast-draining queue are both fine; only a task
    that has been sitting far past the worst legitimate case is a problem."""
    if age_minutes is None:
        return True, "queue empty"
    if age_minutes > max_age_minutes:
        return False, (
            f"oldest queued task is {age_minutes:.0f}min old "
            f"(>{max_age_minutes}min) - worker may be wedged"
        )
    return True, f"oldest queued task {age_minutes:.0f}min old"


def evaluate_backup(is_failed_output, age_hours, max_age_hours=MAX_BACKUP_AGE_HOURS):
    problems = []
    if is_failed_output == "failed":
        problems.append("last run failed")
    if age_hours is None:
        problems.append("no backup archive found")
    elif age_hours > max_age_hours:
        problems.append(f"newest archive is {age_hours:.1f}h old (>{max_age_hours}h)")
    if problems:
        return False, "; ".join(problems)
    return True, f"last run ok, newest archive {age_hours:.1f}h old"


def decide_alerts(prev_failing, current, now, realert_seconds=REALERT_SECONDS):
    """prev_failing: {check_id: {"since": ts, "last_alert": ts}} from the last
    run's state file. current: {check_id: (ok, detail)} from this run.

    Alerts on a new failure immediately, on an unresolved one only after
    realert_seconds have passed since the last alert, and once on recovery.
    Returns (messages, new_failing) - new_failing is what gets persisted.
    """
    messages = []
    new_failing = {}
    for check_id, (ok, detail) in current.items():
        if ok:
            if check_id in prev_failing:
                messages.append(f"RECOVERED: {check_id} - {detail}")
            continue
        if check_id in prev_failing:
            entry = prev_failing[check_id]
            if now - entry["last_alert"] >= realert_seconds:
                messages.append(f"STILL DOWN: {check_id} - {detail}")
                new_failing[check_id] = {"since": entry["since"], "last_alert": now}
            else:
                new_failing[check_id] = entry
        else:
            messages.append(f"DOWN: {check_id} - {detail}")
            new_failing[check_id] = {"since": now, "last_alert": now}
    return messages, new_failing


# --- state + notification ---------------------------------------------------

def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def notify(message):
    try:
        subprocess.run([sys.executable, NOTIFIER, message], timeout=30, check=False)
    except Exception as e:  # never let the notifier itself mask the real failure
        print(f"Could not send notification: {e}", file=sys.stderr)


def evaluate_sniper(age_hours):
    """Never-run is deliberately OK, not a failure: the sniper is opt-in, and a
    box that has never had a watch configured should not page about it."""
    if age_hours is None:
        return True, "no runs recorded yet"
    if age_hours > MAX_SNIPER_AGE_HOURS:
        return False, f"last run {age_hours:.1f}h ago (timer stopped?)"
    return True, f"last run {age_hours:.1f}h ago"


def evaluate_prospector(age_hours):
    """Never-run is OK: prospecting is opt-in, and a box with no prospect list
    configured should not page about one."""
    if age_hours is None:
        return True, "no runs recorded yet"
    if age_hours > MAX_PROSPECTOR_AGE_HOURS:
        return False, f"last audit {age_hours:.1f}h ago (timer stopped?)"
    return True, f"last audit {age_hours:.1f}h ago"


def run_checks():
    current = {}
    for svc in SERVICES:
        current[svc] = evaluate_service(gather_service_status(svc))
    current["network"] = evaluate_network(
        gather_default_route(), gather_iface_addr(LAN_INTERFACE),
        LAN_INTERFACE, gather_internet_ok(),
    )
    current["backup"] = evaluate_backup(
        gather_backup_is_failed(), gather_newest_backup_age_hours(),
    )
    current["queue"] = evaluate_queue(gather_oldest_queued_task_age_minutes())
    current["sniper"] = evaluate_sniper(gather_sniper_age_hours())
    current["prospector"] = evaluate_prospector(gather_prospector_age_hours())
    return current


def main():
    current = run_checks()
    for check_id, (ok, detail) in current.items():
        print(f"{'OK  ' if ok else 'FAIL'}  {check_id}: {detail}")

    prev_failing = load_state()
    messages, new_failing = decide_alerts(prev_failing, current, time.time())

    if messages:
        notify("AI-OS health check:\n" + "\n".join(messages))
        try:
            import safety_controls
            safety_controls.escalate_error("health_check.py", "\n".join(messages))
        except Exception:
            pass

    save_state(new_failing)
    sys.exit(0 if all(ok for ok, _ in current.values()) else 1)


if __name__ == "__main__":
    main()

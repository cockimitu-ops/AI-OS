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


# --- gathering: subprocess/socket/filesystem, no logic ---------------------

def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"<error: {e}>"


def gather_service_status(name):
    return _run(["systemctl", "is-active", name])


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
    return current


def main():
    current = run_checks()
    for check_id, (ok, detail) in current.items():
        print(f"{'OK  ' if ok else 'FAIL'}  {check_id}: {detail}")

    prev_failing = load_state()
    messages, new_failing = decide_alerts(prev_failing, current, time.time())

    if messages:
        notify("AI-OS health check:\n" + "\n".join(messages))

    save_state(new_failing)
    sys.exit(0 if all(ok for ok, _ in current.values()) else 1)


if __name__ == "__main__":
    main()

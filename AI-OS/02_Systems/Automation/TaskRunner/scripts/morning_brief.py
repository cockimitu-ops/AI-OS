#!/usr/bin/env python3
"""Daily good-morning digest, sent over the same Telegram bridge as
everything else. Currently just server health (from health_check.py) -
more sections slot in here once their data sources actually exist, without
needing a rewrite of what's already working. Email was tried twice (OAuth,
then IMAP + App Password) and dropped both times - see the TaskRunner
README for why - so there's nothing email-shaped here for now.

Stdlib only, same reasoning as the rest of scripts/: systemd runs this
under /usr/bin/python3, which has no third-party packages installed.
"""
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
import health_check  # noqa: E402  (needs sys.path set first)
import proposals  # noqa: E402

NOTIFIER = os.path.join(SCRIPT_DIR, "send_telegram_notification.py")


def format_status_section(current_checks):
    bad = [(check_id, detail) for check_id, (ok, detail) in current_checks.items() if not ok]
    if not bad:
        return "Status: everything's fine - worker, bot, network, and last backup all OK."
    lines = [f"Status: {len(bad)} thing(s) need attention:"]
    for check_id, detail in bad:
        lines.append(f"  - {check_id}: {detail}")
    return "\n".join(lines)


def format_todo_section(todos):
    """Approved human-intervention work, surfaced every morning.

    Without this the list would be write-only: Felix approves something at
    20:00 that only he can do, and then nothing ever reminds him. Same
    failure the notify directive fixed for scheduled tasks - work that
    lands somewhere nobody looks."""
    if not todos:
        return None
    lines = [f"Your list ({len(todos)}):"]
    for i, item in enumerate(todos, 1):
        lines.append(f"  {i}. {item.get('text','')}")
    return "\n".join(lines)


def build_digest(current_checks, todos=None, now=None):
    now = now or time.localtime()
    date_str = time.strftime("%A, %d %B %Y", now)
    parts = [f"Good morning - {date_str}", "", format_status_section(current_checks)]
    todo_section = format_todo_section(todos)
    if todo_section:
        parts += ["", todo_section]
    return "\n".join(parts)


def main():
    digest = build_digest(health_check.run_checks(), proposals.load_todos())
    print(digest)
    result = subprocess.run([sys.executable, NOTIFIER, digest], timeout=30, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Daily good-morning digest, sent over the same Telegram bridge as
everything else. Currently just server health (from health_check.py) -
more sections (email, project status) slot in here once their data sources
actually exist, without needing a rewrite of what's already working.

Stdlib only, same reasoning as the rest of scripts/: systemd runs this
under /usr/bin/python3, which has no third-party packages installed.
"""
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import health_check  # noqa: E402  (needs sys.path set first)

NOTIFIER = os.path.join(SCRIPT_DIR, "send_telegram_notification.py")


def format_status_section(current_checks):
    bad = [(check_id, detail) for check_id, (ok, detail) in current_checks.items() if not ok]
    if not bad:
        return "Status: everything's fine - worker, bot, network, and last backup all OK."
    lines = [f"Status: {len(bad)} thing(s) need attention:"]
    for check_id, detail in bad:
        lines.append(f"  - {check_id}: {detail}")
    return "\n".join(lines)


def format_email_section():
    """Not wired up yet. The Gmail tools connected to this session are
    action-only (reply/forward/send/label) - there is no tool to list or
    read messages, so there is nothing to summarize here. Needs real Gmail
    read access sorted first - see External_Access_Plan.md."""
    return None


def build_digest(current_checks, now=None):
    now = now or time.localtime()
    date_str = time.strftime("%A, %d %B %Y", now)
    status = format_status_section(current_checks)
    email = format_email_section()

    parts = [f"Good morning - {date_str}", "", status]
    if email:
        parts += ["", email]
    else:
        parts += ["", "(Email isn't wired in yet - still waiting on real Gmail read access.)"]
    return "\n".join(parts).strip()


def main():
    digest = build_digest(health_check.run_checks())
    print(digest)
    result = subprocess.run([sys.executable, NOTIFIER, digest], timeout=30, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""20:00 sharp: show Felix what the agents proposed today and ask which to take.

This is the human end of the propose/approve gate. Everything the agents
planned during the day sits in proposals/pending.json having changed
nothing; this snapshots it into a numbered review and sends it to Telegram.
Felix replies `approve 1 3` (handled in telegram_bridge.py), and only then
does anything become a real task.

Stdlib only - systemd runs this under /usr/bin/python3.
"""
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, TASK_RUNNER_DIR)
import proposals  # noqa: E402  (needs sys.path set first)

NOTIFIER = os.path.join(SCRIPT_DIR, "send_telegram_notification.py")


def main():
    review = proposals.open_review()
    message = proposals.format_review(review)
    print(message)
    result = subprocess.run(["/usr/bin/python3", NOTIFIER, message],
                            timeout=30, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

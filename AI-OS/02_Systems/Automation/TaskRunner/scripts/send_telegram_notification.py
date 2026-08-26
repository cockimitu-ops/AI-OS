#!/usr/bin/env python3
"""Generic outbound Telegram notifier. Reuses the same bot token and allowed
chat id as telegram_bridge.py, but sends unprompted instead of replying.

Deliberately dependency-free (stdlib only, and its own .env parser instead of
python-dotenv). This is the script that runs when something else has already
broken - e.g. cloud_backup.py's failure path, which systemd runs under
/usr/bin/python3, where python-dotenv is not installed. A notifier that only
works inside one virtualenv is a notifier that stays silent exactly when it
matters.

Usage: python3 send_telegram_notification.py "message text"
"""
import json
import os
import sys
import urllib.error
import urllib.request

ENV_PATH = "/home/nost/AI-OS/.env"


def load_env(path=ENV_PATH):
    """Minimal KEY=VALUE reader - real env vars always win, matching how the
    systemd units already inject the same file via EnvironmentFile=."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("\"'")


load_env()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_ALLOWED_USER_ID")


def send(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_USER_ID missing in .env", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        print(f"ERROR: Telegram API returned {e.code}: {e.read()[:300]!r}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: could not reach Telegram API: {e}", file=sys.stderr)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: send_telegram_notification.py \"message text\"", file=sys.stderr)
        sys.exit(2)

    message = " ".join(sys.argv[1:])
    ok = send(message)
    sys.exit(0 if ok else 1)

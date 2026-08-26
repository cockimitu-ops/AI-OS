#!/usr/bin/env python3
"""Generic outbound Telegram notifier. Reuses the same bot token and allowed
chat id as telegram_bridge.py, but sends unprompted instead of replying.

Usage: python3 send_telegram_notification.py "message text"
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv("/home/nost/AI-OS/.env")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_ALLOWED_USER_ID")


def send(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_USER_ID missing in .env", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=15)
    if resp.status_code != 200:
        print(f"ERROR: Telegram API returned {resp.status_code}: {resp.text}", file=sys.stderr)
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: send_telegram_notification.py \"message text\"", file=sys.stderr)
        sys.exit(2)

    message = " ".join(sys.argv[1:])
    ok = send(message)
    sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""Read-only Gmail access via IMAP with an App Password.

The Google Cloud OAuth route (originally planned - see git history and
External_Access_Plan.md) hit a real wall: registering the API/OAuth client
required a billing-enabled (paid) Google Cloud project. An App Password
needs none of that - just 2-Step Verification turned on for the account and
a password generated at https://myaccount.google.com/apppasswords. Stdlib
only (imaplib + email), same reasoning as everything else in scripts/:
systemd runs this under /usr/bin/python3, no third-party packages.

Setup (done by Felix, never through Claude - the app password is a
credential like any other):
    GMAIL_ADDRESS=you@gmail.com
    GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
added directly to .env. This module does nothing (returns None) until both
are present.

BODY.PEEK is used throughout, never plain BODY - PEEK reads a message
without setting its \\Seen flag. A summary tool that marks your mail as
read as a side effect of describing it would be a bad trade.
"""
import email
import email.header
import imaplib
import os

ENV_PATH = "/home/nost/AI-OS/.env"
IMAP_HOST = "imap.gmail.com"


def load_env(path=ENV_PATH):
    env = {}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return env
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("\"'")
    return env


def decode_header_value(value):
    """Header values can arrive MIME-encoded (=?UTF-8?B?...?=) - decode to
    plain text, falling back to the raw value for anything malformed."""
    if not value:
        return ""
    try:
        parts = email.header.decode_header(value)
    except email.errors.HeaderParseError:
        return value
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _connect(address, app_password):
    conn = imaplib.IMAP4_SSL(IMAP_HOST)
    conn.login(address, app_password)
    return conn


def fetch_unread_summaries(max_results=10, env=None):
    """Returns a list of {"from": ..., "subject": ...} for unread inbox
    messages, most recent first. Returns None - distinct from an empty list -
    if GMAIL_ADDRESS/GMAIL_APP_PASSWORD aren't in .env yet, so callers can
    tell "not configured" apart from "configured, nothing unread"."""
    env = env if env is not None else load_env()
    address = env.get("GMAIL_ADDRESS")
    app_password = env.get("GMAIL_APP_PASSWORD")
    if not address or not app_password:
        return None

    conn = _connect(address, app_password)
    try:
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []
        ids = data[0].split()[-max_results:]

        out = []
        for msg_id in reversed(ids):
            status, msg_data = conn.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            headers = email.message_from_bytes(msg_data[0][1])
            out.append({
                "from": decode_header_value(headers.get("From", "(unknown)")),
                "subject": decode_header_value(headers.get("Subject", "(no subject)")),
            })
        return out
    finally:
        try:
            conn.logout()
        except OSError:
            pass

#!/usr/bin/env python3
"""One-time interactive setup for real Gmail read access.

Run this yourself, directly in your own terminal - never paste its output,
or GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET, to Claude. Two credentials already
leaked into a chat transcript once this project; this script exists so a
third doesn't. Claude writes the code, you run it, the token never leaves
this machine's .env.

Uses Google's OAuth 2.0 Device Authorization flow - no browser and no
redirect listener needed on this headless box. You'll get a short code to
type in on your phone (or any browser), nothing more.

Requires GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET already in .env, from a
Google Cloud Console OAuth client of type "TVs and Limited Input devices"
(see External_Access_Plan.md). On success, writes GMAIL_REFRESH_TOKEN into
.env - the one thing mail_read.py actually needs afterward.

Usage: python3 gmail_oauth_setup.py
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_PATH = "/home/nost/AI-OS/.env"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


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


def set_env_var(key, value, path=ENV_PATH):
    """Replaces an existing KEY= line in place, or appends one if it's not
    there yet. .env is a gitignored secrets file, not vault content - the
    vault's own no-overwrite convention (see vault_write.py) is about
    Markdown notes, and deliberately doesn't apply here."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        lines = []
    out = []
    replaced = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}\n")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def _post(url, data):
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main():
    env = load_env()
    client_id = env.get("GMAIL_CLIENT_ID")
    client_secret = env.get("GMAIL_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET in .env - add those first.", file=sys.stderr)
        sys.exit(1)

    device = _post("https://oauth2.googleapis.com/device/code", {
        "client_id": client_id,
        "scope": SCOPE,
    })

    print()
    print(f"1. On your phone or any browser, go to: {device['verification_url']}")
    print(f"2. Enter this code:  {device['user_code']}")
    print("3. Sign in and approve read-only Gmail access.")
    print()
    print("Waiting for approval...")

    interval = device.get("interval", 5)
    expires_at = time.time() + device.get("expires_in", 1800)

    while time.time() < expires_at:
        time.sleep(interval)
        try:
            token = _post("https://oauth2.googleapis.com/token", {
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            })
        except urllib.error.HTTPError as e:
            err = json.loads(e.read())
            if err.get("error") == "authorization_pending":
                continue
            if err.get("error") == "slow_down":
                interval += 5
                continue
            print(f"Failed: {err}", file=sys.stderr)
            sys.exit(1)
        else:
            refresh_token = token.get("refresh_token")
            if not refresh_token:
                print(
                    "Approved, but Google didn't send a refresh token - this happens if "
                    "you've authorized this exact app before. Revoke it at "
                    "https://myaccount.google.com/permissions and run this again.",
                    file=sys.stderr,
                )
                sys.exit(1)
            set_env_var("GMAIL_REFRESH_TOKEN", refresh_token)
            print("Done. GMAIL_REFRESH_TOKEN written to .env.")
            return

    print("Timed out waiting for approval - run this again.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

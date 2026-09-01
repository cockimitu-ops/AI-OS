#!/usr/bin/env python3
"""Prints the web client's login link as a scannable QR code.

Why: the access token is 43 random characters. Opening the app on a device
that has not saved it meant asking for the token and retyping it on a phone
keyboard - which is exactly how the masked-input bug went unnoticed for a day.
Scanning a square is one action instead of forty-three.

On the encoder: the first version of this file hand-rolled QR generation to
stay stdlib-only. It rendered something that looked like a QR code and did not
scan - verified by decoding it with zbarimg, which read segno's output
instantly and mine not at all. The purity argument was not worth an unusable
code, so this uses python3-segno (packaged, pure Python, no dependencies of
its own). "Looks right" is not a standard for something whose entire job is to
be machine-readable.
"""
import os
import sys

import segno

TASK_RUNNER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.normpath(os.path.join(TASK_RUNNER_DIR, *([os.pardir] * 4), ".env"))


def load_env(path=ENV_PATH):
    values = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def login_url(env=None):
    env = env if env is not None else load_env()
    token = env.get("AIOS_WEB_TOKEN")
    if not token:
        return None
    host = env.get("AIOS_WEB_BIND", "100.64.2.100")
    port = env.get("AIOS_WEB_PORT", "8787")
    return f"http://{host}:{port}/?token={token}"


def main(argv=None):
    url = login_url()
    if not url:
        print("AIOS_WEB_TOKEN steht nicht in der .env", file=sys.stderr)
        return 1
    # Terminal output uses half-block characters so the code stays square:
    # a character cell is about twice as tall as it is wide, and a QR
    # stretched 2:1 does not scan.
    print()
    segno.make(url, error="l").terminal(compact=True)
    print(f"\n{url}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

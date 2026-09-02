#!/usr/bin/env python3
"""Read the signed-in Codex account allowance through its local app server."""
import json
import os
import select
import subprocess
import time

BIN = os.environ.get("AIOS_CODEX_BIN", "codex")
TIMEOUT_S = 8


def _read(proc, expected_id, timeout=TIMEOUT_S):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        ready, _, _ = select.select([proc.stdout], [], [], max(0, end - time.monotonic()))
        if not ready:
            break
        line = proc.stdout.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == expected_id:
            if "error" in msg:
                raise RuntimeError(str(msg["error"]))
            return msg.get("result") or {}
    raise RuntimeError("Codex usage response timed out")


def read_rate_limits():
    """Return the account's real rate-limit snapshot, or a safe error record."""
    try:
        proc = subprocess.Popen([BIN, "app-server", "--stdio"], text=True,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, bufsize=1)
        proc.stdin.write(json.dumps({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "AI-OS", "version": "1"}, "capabilities": None}}) + "\n")
        proc.stdin.flush()
        _read(proc, 1)
        proc.stdin.write(json.dumps({"id": 2, "method": "account/rateLimits/read",
                                     "params": None}) + "\n")
        proc.stdin.flush()
        result = _read(proc, 2)
        limits = result.get("rateLimits") or {}
        primary = limits.get("primary") or {}
        return {"live": True, "plan": limits.get("planType"),
                "used_percent": primary.get("usedPercent"),
                "window_minutes": primary.get("windowDurationMins"),
                "resets_at": primary.get("resetsAt"),
                "credits": limits.get("credits") or {}}
    except (OSError, RuntimeError, ValueError) as exc:
        return {"live": False, "error": str(exc)[:180]}
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except (UnboundLocalError, OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except (UnboundLocalError, OSError):
                pass

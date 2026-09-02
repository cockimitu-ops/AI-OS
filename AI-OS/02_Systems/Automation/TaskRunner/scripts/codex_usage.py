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


# Spawning the app server costs a subprocess, and next_engine() asks about
# every candidate. Cached like the login check, and short enough that hitting
# a wall becomes visible within the minute.
_CACHE_TTL_S = 45
_cache = {"at": 0.0, "value": None}


def read_rate_limits(force=False):
    now = time.time()
    if not force and _cache["value"] and now - _cache["at"] < _CACHE_TTL_S:
        return _cache["value"]
    value = _read_rate_limits()
    _cache.update(at=now, value=value)
    return value


def reached():
    """-> (out, why, resets_at) using the account's own verdict and clock.

    The reset timestamp is the part worth carrying: it turns "skip Codex for
    an hour and hope" into "Codex is back at 21:35", which is both the honest
    answer and the one Felix can plan around."""
    data = read_rate_limits()
    if not data.get("live"):
        return False, "", None
    windows = [w for w in (data.get("primary"), data.get("secondary")) if w]
    full = [w for w in windows if (w.get("used_percent") or 0) >= 100]
    resets = min((w["resets_at"] for w in full if w.get("resets_at")), default=None)
    if data.get("reached"):
        return True, f"Codex-Kontingent erschöpft ({data['reached']})", resets
    if data.get("spend_control_reached"):
        return True, "Codex-Ausgabengrenze erreicht", resets
    return False, "", None


def _read_rate_limits():
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
        # Both windows, and the account's own verdict. Reading only `primary`
        # showed 13% of a 30-day window while Felix was standing in front of a
        # wall - the short window and rateLimitReachedType are where a real
        # refusal shows up, and they were being thrown away.
        def window(row):
            row = row or {}
            if not row:
                return None
            return {"used_percent": row.get("usedPercent"),
                    "window_minutes": row.get("windowDurationMins"),
                    "resets_at": row.get("resetsAt")}

        primary = window(limits.get("primary"))
        return {"live": True, "plan": limits.get("planType"),
                # Kept flat as well so the existing cost view keeps working.
                "used_percent": (primary or {}).get("used_percent"),
                "window_minutes": (primary or {}).get("window_minutes"),
                "resets_at": (primary or {}).get("resets_at"),
                "primary": primary, "secondary": window(limits.get("secondary")),
                "reached": limits.get("rateLimitReachedType"),
                "spend_control_reached": bool(limits.get("spendControlReached")),
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

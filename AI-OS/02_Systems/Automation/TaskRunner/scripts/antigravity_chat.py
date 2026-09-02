#!/usr/bin/env python3
"""Google AI Pro through the supported Antigravity CLI."""
import json
import os
import subprocess
import sys

import shared_briefing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = os.environ.get("AIOS_GOOGLE_PRO_PROJECT", "/home/nost/AI-OS")
BIN = os.environ.get("AIOS_ANTIGRAVITY_BIN", "/home/nost/.local/bin/agy")
TIMEOUT_S = int(os.environ.get("AIOS_GOOGLE_PRO_TIMEOUT", "900"))
MODELS = [
    "gemini-3.8-flash-high", "gemini-3.8-flash-medium", "gemini-3.8-flash-low",
    "gemini-3.7-flash-high", "gemini-3.7-flash-medium", "gemini-3.7-flash-low",
    "gemini-3.6-flash-high", "gemini-3.6-flash-medium", "gemini-3.6-flash-low",
    "gemini-3.1-pro-high", "gemini-3.1-pro-low",
]
DEFAULT_MODEL = "gemini-3.8-flash-high"


class GoogleProError(RuntimeError):
    pass


def available():
    """Only inspect local setup here; the actual turn verifies the account."""
    if not os.path.isfile(BIN) or not os.access(BIN, os.X_OK):
        return False, "Google AI Pro CLI ist nicht installiert"
    return True, ""


def usage():
    """Live Google AI Pro Gemini allowance from Antigravity's signed-in account."""
    argv = [BIN, "-p", "/usage", "--output-format", "json", "--print-timeout", "30s"]
    try:
        proc = subprocess.run(argv, cwd=PROJECT_DIR, capture_output=True, timeout=45)
        data = json.loads((proc.stdout or b"").decode("utf-8", "replace"))
        groups = ((data.get("command") or {}).get("data") or {}).get("groups") or []
        gemini = next((g for g in groups if g.get("name") == "Gemini Models"), None)
        if proc.returncode or not gemini:
            raise GoogleProError("Google AI Pro usage is unavailable")
        return {"live": True, "buckets": [{
            "name": b.get("name"), "remaining_percent": round(float(b.get("remaining_fraction", 0)) * 100),
            "resets_at": b.get("reset_time")
        } for b in gemini.get("buckets") or []]}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired, GoogleProError) as exc:
        return {"live": False, "error": str(exc)[:180]}


def ask(message, model=None, cwd=None):
    """One non-interactive account-backed Google AI Pro turn."""
    model = model or DEFAULT_MODEL
    prompt = shared_briefing.prepend(message)
    argv = [BIN, "-p", prompt, "--output-format", "json", "--model", model,
            "--print-timeout", f"{TIMEOUT_S}s"]
    try:
        proc = subprocess.run(argv, cwd=cwd or PROJECT_DIR, capture_output=True,
                              timeout=TIMEOUT_S + 30)
    except subprocess.TimeoutExpired:
        raise GoogleProError(f"Google AI Pro hat in {TIMEOUT_S}s nicht geantwortet")
    except OSError as exc:
        raise GoogleProError(f"Google AI Pro konnte nicht starten: {exc}")
    raw = (proc.stdout or b"").decode("utf-8", "replace").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise GoogleProError((err or raw or "Google AI Pro lieferte keine lesbare Antwort")[:600])
    reply = str(data.get("response") or "").strip()
    if proc.returncode or data.get("status") != "SUCCESS" or not reply:
        raise GoogleProError(str(data.get("error") or data.get("status") or "Google AI Pro antwortete nicht")[:600])
    return {"reply": reply, "model": model, "usage": data.get("usage") or {}}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("message", nargs="*")
    args = parser.parse_args(argv)
    message = (open(args.prompt_file, encoding="utf-8").read()
               if args.prompt_file else " ".join(args.message))
    try:
        result = ask(message, model=args.model)
        print(json.dumps({"is_error": False, "result": result["reply"], "model": result["model"], "usage": result["usage"]}, ensure_ascii=False) if args.json else result["reply"])
    except GoogleProError as exc:
        data = {"is_error": True, "result": str(exc)}
        print(json.dumps(data, ensure_ascii=False) if args.json else str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

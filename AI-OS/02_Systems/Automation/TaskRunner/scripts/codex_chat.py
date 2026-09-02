#!/usr/bin/env python3
"""OpenAI's Codex CLI as a chat engine.

A thin wrapper, and the thin part is deliberate: `codex exec` already is the
headless interface, so this only translates between its shape and the one
every other engine here uses.

WHAT THE REAL CLI ACTUALLY OFFERS (codex-cli 0.152.1, checked 2026-09-02
against the installed binary rather than the docs)

    codex exec [PROMPT]        prompt as an argument, or "-" to read stdin
    -m, --model                the model
    -s, --sandbox              read-only | workspace-write | danger-full-access
    -C, --cd                   working root
    --skip-git-repo-check      allow running outside a repository
    -o, --output-last-message  write ONLY the final message to a file
    --json                     event stream as JSONL

-o is why this file is short. Without it the answer has to be dug out of an
event stream or scraped off a terminal-shaped stdout; with it, the final
message lands in a file and everything else is noise that can go to the log.

The prompt goes in on stdin rather than as an argument. A question from Felix
can be a paragraph with quotes and newlines in it, and argv is the wrong
place for that.

SANDBOX

workspace-write by default: Codex may edit inside the project and run
commands, and may not touch the rest of the machine. That is a narrower grant
than the Claude engine has (Felix chose --dangerously-skip-permissions there,
knowingly), and it is the right default for an engine he has not watched work
yet. AIOS_CODEX_SANDBOX overrides it.

Stdlib only.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import shared_briefing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)

BIN = os.environ.get("AIOS_CODEX_BIN", "codex")
PROJECT_DIR = os.environ.get("AIOS_CLAUDE_PROJECT", "/home/nost/AI-OS")
SANDBOX = os.environ.get("AIOS_CODEX_SANDBOX", "workspace-write")
TIMEOUT_S = int(os.environ.get("AIOS_CODEX_TIMEOUT", "900"))

# "auto" means: do not pass -m at all, and let Codex use whatever the account
# and config say. Listed first because inventing model names for a CLI that
# has not been logged into yet is how you ship a picker full of 404s.
MODELS = ["auto", "gpt-5.1-codex", "gpt-5.1-codex-mini"]
DEFAULT_MODEL = "auto"


class CodexError(RuntimeError):
    pass


# The login check spawns a process, and catalogue() is called by the chat
# screen and the cost screen on every open. Cached for a few seconds so that
# a page load costs one subprocess rather than one per engine listing - and
# short enough that logging in shows up almost immediately.
_LOGIN_TTL_S = 30
_login_cache = {"at": 0.0, "value": None}


def logged_in(force=False):
    """-> (bool, message). `codex login status` is the only honest source."""
    now = time.time()
    if not force and _login_cache["value"] and now - _login_cache["at"] < _LOGIN_TTL_S:
        return _login_cache["value"]
    value = _login_status()
    _login_cache.update(at=now, value=value)
    return value


def _login_status():
    try:
        out = subprocess.run([BIN, "login", "status"], capture_output=True,
                             timeout=20)
    except FileNotFoundError:
        return False, ("Codex ist nicht installiert - "
                       "`sudo npm i -g @openai/codex`")
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"Codex antwortet nicht: {e}"
    text = (out.stdout + out.stderr).decode("utf-8", "replace").strip()
    if out.returncode == 0 and "not logged in" not in text.lower():
        return True, text[:120]
    return False, ("Codex ist installiert, aber nicht angemeldet - "
                   "im Terminal `codex login` und mit dem ChatGPT-Konto anmelden")


def ask(message, model=None, cwd=None, resume=None):
    """One turn. -> {"reply", "model"}. Raises CodexError with what it said."""
    message = shared_briefing.prepend(message)
    model = model or DEFAULT_MODEL
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as last:
        last_path = last.name
    argv = [BIN, "exec"]
    if resume:
        argv += ["resume", resume]
    if model and model != "auto":
        argv += ["-m", model]
    argv += ["-s", SANDBOX, "--skip-git-repo-check",
             "-C", cwd or PROJECT_DIR,
             "-o", last_path, "-"]          # "-" : prompt comes from stdin
    try:
        proc = subprocess.run(argv, input=message.encode("utf-8"),
                              capture_output=True, timeout=TIMEOUT_S)
    except FileNotFoundError:
        raise CodexError("Codex ist nicht installiert")
    except subprocess.TimeoutExpired:
        raise CodexError(f"Codex hat in {TIMEOUT_S}s nicht geantwortet")
    finally:
        pass
    try:
        with open(last_path, encoding="utf-8") as f:
            reply = f.read().strip()
    except OSError:
        reply = ""
    try:
        os.unlink(last_path)
    except OSError:
        pass
    if not reply:
        # Nothing in the answer file: say what the process said instead of
        # reporting an empty success.
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        out = (proc.stdout or b"").decode("utf-8", "replace").strip()
        raise CodexError((err or out or f"Codex endete mit Code {proc.returncode}")[:600])
    return {"reply": reply, "model": model}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--resume")
    ap.add_argument("--cwd")
    ap.add_argument("--prompt-file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("message", nargs="*")
    args = ap.parse_args(argv)
    text = (open(args.prompt_file, encoding="utf-8").read()
            if args.prompt_file else " ".join(args.message))
    try:
        out = ask(text, model=args.model, cwd=args.cwd, resume=args.resume)
    except CodexError as e:
        if args.json:
            print(json.dumps({"is_error": True, "result": str(e)}, ensure_ascii=False))
            return 1
        print(f"[!] {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"is_error": False, "result": out["reply"],
                          "model": out["model"]}, ensure_ascii=False))
    else:
        print(out["reply"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

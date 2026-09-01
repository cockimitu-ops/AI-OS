#!/usr/bin/env python3
"""Read and continue Claude Code sessions from the web app.

WHY

Felix asked for exactly one thing here: "ich will genau in dem chat hier
weiterschreiben von meinem handy aus". Not a summary of the session, not a
second assistant that has read it - the same conversation, continued from a
phone. Claude Code already stores every session as JSONL under
~/.claude/projects/<slug>/, and `claude -p --resume <id>` continues one
non-interactively and keeps the same session id, so the file simply grows.
This module is the two halves of that: reading those files for display, and
running that command for a reply.

PERMISSIONS

Sends run with --dangerously-skip-permissions. That is Felix's explicit
decision, taken with the alternative in front of him: a headless run cannot
ask, so anything less either fails on the first real task or silently does
half of it. The boundary that remains is the one that was already there -
the tailnet, plus the bearer token on every request. Worth being honest
about what that means: a message typed on a phone can change anything on
this machine, with nobody watching.

CONCURRENCY

Nothing stops a session being resumed here while the same session is open in
a terminal, and both would append to one file. Rather than pretend to lock
it, list_sessions() reports `active` for anything written to in the last
ACTIVE_WINDOW_S so the app can say so.

Stdlib only, plus the `claude` CLI.
"""
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
JOBS_DIR = os.path.join(TASK_RUNNER_DIR, "claude_jobs")

# The directory Claude Code runs in, and therefore which project's sessions
# these are. Overridable so a test never has to touch the real transcripts.
PROJECT_DIR = os.environ.get("AIOS_CLAUDE_PROJECT", "/home/nost/AI-OS")
CLAUDE_BIN = os.environ.get("AIOS_CLAUDE_BIN", "claude")
# A turn on a large session genuinely takes minutes; this only stops a job
# that has hung from occupying the queue forever.
SEND_TIMEOUT_S = 900
# Written to in the last minute and a half: something is probably typing into
# it right now, somewhere else.
ACTIVE_WINDOW_S = 90
SESSION_ID_RE = re.compile(r"[0-9a-fA-F-]{36}")

# Per million tokens, from platform.claude.com/docs (prompt-caching pricing),
# checked 2026-09-01. Cache writes and reads are NOT the input rate: a 1-hour
# cache write costs 2x input and a cache read costs 0.1x, and this session
# type writes 1-hour cache entries - counting those at the input rate would
# overstate a long conversation badly, and counting them as free would
# understate it.
PRICING = {
    "claude-opus-5":   {"in": 5.0, "out": 25.0, "cache_5m": 6.25, "cache_1h": 10.0, "cache_read": 0.50},
    "claude-opus-4-8": {"in": 5.0, "out": 25.0, "cache_5m": 6.25, "cache_1h": 10.0, "cache_read": 0.50},
    "claude-sonnet-5": {"in": 2.0, "out": 10.0, "cache_5m": 2.50, "cache_1h": 4.0, "cache_read": 0.20},
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0, "cache_5m": 1.25, "cache_1h": 2.0, "cache_read": 0.10},
}
DEFAULT_PRICING = PRICING["claude-opus-5"]


def project_slug(path=None):
    """Claude Code's directory name for a project: the absolute path with
    every separator replaced by a dash."""
    return (path or PROJECT_DIR).replace("/", "-")


def sessions_dir(path=None):
    return os.path.join(os.path.expanduser("~"), ".claude", "projects",
                        project_slug(path))


def _iter_rows(path, limit=None):
    """Rows of one transcript, oldest first. Skips lines that will not parse
    rather than failing the whole read - a transcript being appended to while
    it is read can end in half a line."""
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows[-limit:] if limit else rows


def _text_of(content):
    """The human-readable part of a message's content.

    Content is either a plain string or a list of blocks. Thinking blocks are
    dropped (they are empty in the transcript anyway - the raw chain of
    thought is never stored), and tool traffic is reduced to one line naming
    the tool, because a phone-sized reading of a coding session wants to see
    that a command ran, not its full argv."""
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            parts.append((block.get("text") or "").strip())
        elif kind == "tool_use":
            name = block.get("name") or "tool"
            arg = ""
            inp = block.get("input") or {}
            if isinstance(inp, dict):
                for key in ("command", "file_path", "path", "pattern", "query",
                            "description", "url"):
                    if inp.get(key):
                        arg = str(inp[key])
                        break
            # One line, always. A Bash block in this project is routinely a
            # 200-line heredoc; pasted whole into a phone-width transcript it
            # buries the actual conversation under its own source code.
            arg = " ".join(arg.split())[:90]
            parts.append(f"⚙ {name}" + (f": {arg}" if arg else ""))
    return "\n\n".join(p for p in parts if p).strip()


def _title(rows, fallback):
    for row in reversed(rows):
        if row.get("type") == "ai-title" and row.get("aiTitle"):
            return str(row["aiTitle"])[:80]
    for row in rows:
        if row.get("type") == "user":
            text = _text_of((row.get("message") or {}).get("content"))
            if text and not text.startswith("⚙"):
                return text.splitlines()[0][:80]
    return fallback


def usage_cost(usage, model):
    """USD for one assistant turn. -> (usd, tokens_dict)."""
    usage = usage or {}
    rates = PRICING.get(model or "", DEFAULT_PRICING)
    creation = usage.get("cache_creation") or {}
    tok = {
        "input": usage.get("input_tokens", 0) or 0,
        "output": usage.get("output_tokens", 0) or 0,
        "cache_read": usage.get("cache_read_input_tokens", 0) or 0,
        "cache_5m": creation.get("ephemeral_5m_input_tokens", 0) or 0,
        "cache_1h": creation.get("ephemeral_1h_input_tokens", 0) or 0,
    }
    # cache_creation_input_tokens is the total; if the per-TTL breakdown is
    # missing (older transcripts), bill it all at the 5-minute rate, which is
    # the cheaper of the two - an estimate should not flatter itself.
    if not tok["cache_5m"] and not tok["cache_1h"]:
        tok["cache_5m"] = usage.get("cache_creation_input_tokens", 0) or 0
    usd = (tok["input"] * rates["in"] + tok["output"] * rates["out"]
           + tok["cache_read"] * rates["cache_read"]
           + tok["cache_5m"] * rates["cache_5m"]
           + tok["cache_1h"] * rates["cache_1h"]) / 1e6
    return usd, tok


def session_stats(rows):
    """Turns, tokens and estimated USD for one already-read transcript."""
    total = {"input": 0, "output": 0, "cache_read": 0, "cache_5m": 0, "cache_1h": 0}
    usd = 0.0
    turns = 0
    models = set()
    for row in rows:
        if row.get("type") != "assistant":
            continue
        msg = row.get("message") or {}
        model = msg.get("model")
        if model:
            models.add(model)
        turn_usd, tok = usage_cost(msg.get("usage"), model)
        usd += turn_usd
        turns += 1
        for k in total:
            total[k] += tok[k]
    return {"turns": turns, "tokens": total, "usd": round(usd, 4),
            "models": sorted(models)}


def list_sessions(limit=20, project=None):
    """Recent Claude Code sessions for this project, newest first."""
    directory = sessions_dir(project)
    try:
        names = [n for n in os.listdir(directory) if n.endswith(".jsonl")]
    except OSError:
        return []
    entries = []
    for name in names:
        full = os.path.join(directory, name)
        try:
            stat = os.stat(full)
        except OSError:
            continue
        entries.append((stat.st_mtime, stat.st_size, name, full))
    entries.sort(reverse=True)
    now = time.time()
    out = []
    for mtime, size, name, full in entries[:limit]:
        sid = name[:-len(".jsonl")]
        rows = _iter_rows(full)
        messages = sum(1 for r in rows
                       if r.get("type") in ("user", "assistant")
                       and _text_of((r.get("message") or {}).get("content")))
        out.append({
            "id": sid,
            "title": _title(rows, sid[:8]),
            "updated": datetime.fromtimestamp(mtime).isoformat(timespec="seconds"),
            "updated_ago": int(now - mtime),
            "messages": messages,
            "size": size,
            # Something wrote to this file moments ago. Almost always a
            # terminal with the same session open; sending into it from here
            # would interleave two conversations in one file.
            "active": (now - mtime) < ACTIVE_WINDOW_S,
            "stats": session_stats(rows),
        })
    return out


def transcript(session_id, limit=60, project=None):
    """The last `limit` readable messages of one session, oldest first."""
    if not SESSION_ID_RE.fullmatch(session_id or ""):
        raise ValueError("ungültige session id")
    path = os.path.join(sessions_dir(project), f"{session_id}.jsonl")
    if not os.path.isfile(path):
        raise FileNotFoundError("Sitzung nicht gefunden")
    rows = _iter_rows(path)
    # Most "user" rows were never typed by anyone. Tool results, skill
    # injections and system reminders all arrive with role=user, and in a
    # real session they outnumber the actual prompts by forty to one - 135
    # user rows against 3 typed messages, measured on this session. Rendered
    # as speech they bury the conversation under the harness.
    #
    # A genuinely typed prompt carries promptSource/origin. Rather than trust
    # that unconditionally (an older transcript might predate the field and
    # would then show nothing Felix said at all), it is used only when the
    # file proves it has it.
    typed_marked = any(r.get("type") == "user"
                       and (r.get("promptSource") or r.get("origin"))
                       for r in rows)
    msgs = []
    for row in rows:
        kind = row.get("type")
        if kind not in ("user", "assistant"):
            continue
        text = _text_of((row.get("message") or {}).get("content"))
        if not text:
            continue
        machine = (kind == "user" and typed_marked
                   and not (row.get("promptSource") or row.get("origin")))
        msgs.append({
            "role": kind,
            # Machine turns are for glancing at, not reading: a skill payload
            # is thousands of words of instructions to the model.
            "text": (text[:300] + " …") if machine and len(text) > 300 else text,
            "ts": row.get("timestamp"),
            # Anything the harness said to itself, shown as machine output so
            # the conversation still reads as a conversation.
            "tool": text.startswith("⚙") or machine,
        })
    # `limit` counts CONVERSATION turns, not rows. Counting rows put three
    # real messages and fifty-seven machine lines on the screen, which is a
    # window onto the harness rather than onto the conversation - the machine
    # lines come along because they fall between the turns, not because they
    # were asked for.
    kept, turns = 0, 0
    for i in range(len(msgs) - 1, -1, -1):
        kept += 1
        if not msgs[i]["tool"]:
            turns += 1
            if turns >= limit:
                break
    window = msgs[-kept:] if kept else []
    return {"session_id": session_id, "messages": window,
            "total_messages": len(msgs),
            # What the client would be asking for if it wanted more.
            "shown_turns": turns,
            "title": _title(rows, session_id[:8]), "stats": session_stats(rows)}


# --- sending -------------------------------------------------------------

def _job_paths(job_id):
    return {
        "prompt": os.path.join(JOBS_DIR, f"{job_id}.prompt"),
        "out": os.path.join(JOBS_DIR, f"{job_id}.json"),
        "part": os.path.join(JOBS_DIR, f"{job_id}.json.part"),
        "err": os.path.join(JOBS_DIR, f"{job_id}.err"),
        "meta": os.path.join(JOBS_DIR, f"{job_id}.meta"),
    }


def send(session_id, message, project=None):
    """Continue a session with one message. -> job id, immediately.

    Detached on purpose. A turn regularly takes minutes, and a phone browser
    will not hold a request open that long - the web chat already learned
    this once (see api.py's post_chat). The job writes its result to a file,
    so the answer also survives the app being closed, the webapp restarting,
    or the phone changing network."""
    if not SESSION_ID_RE.fullmatch(session_id or ""):
        raise ValueError("ungültige session id")
    message = (message or "").strip()
    if not message:
        raise ValueError("leere Nachricht")
    os.makedirs(JOBS_DIR, exist_ok=True)
    job_id = f"cc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    p = _job_paths(job_id)
    with open(p["prompt"], "w", encoding="utf-8") as f:
        f.write(message)
    with open(p["meta"], "w", encoding="utf-8") as f:
        json.dump({"session_id": session_id, "started": time.time(),
                   "message": message[:2000]}, f, ensure_ascii=False)

    # Written as a shell line so the rename can happen in the same detached
    # process: the presence of the .json file is then the only "is it done"
    # signal the poller needs, and it can never observe a half-written one.
    cmd = (
        f"{shlex.quote(CLAUDE_BIN)} -p --resume {shlex.quote(session_id)}"
        f" --output-format json --dangerously-skip-permissions"
        f" < {shlex.quote(p['prompt'])}"
        f" > {shlex.quote(p['part'])} 2> {shlex.quote(p['err'])};"
        f" mv {shlex.quote(p['part'])} {shlex.quote(p['out'])}"
    )
    subprocess.Popen(["sh", "-c", cmd], cwd=project or PROJECT_DIR,
                     stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return job_id


def result(job_id):
    """-> the finished turn, or how long it has been running."""
    if not re.fullmatch(r"cc_[\w.]{1,40}", job_id or ""):
        raise ValueError("ungültige job id")
    p = _job_paths(job_id)
    if os.path.exists(p["out"]):
        try:
            with open(p["out"], encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            return {"ready": True, "ok": False, "error": f"Antwort unlesbar: {e}"}
        return {
            "ready": True,
            "ok": not data.get("is_error"),
            "reply": data.get("result") or "",
            "usd": data.get("total_cost_usd"),
            "turns": data.get("num_turns"),
            "duration_ms": data.get("duration_ms"),
            "session_id": data.get("session_id"),
        }
    try:
        started = json.load(open(p["meta"], encoding="utf-8")).get("started", 0)
    except (OSError, json.JSONDecodeError):
        return {"ready": False, "lost": True, "error": "Job nicht mehr auffindbar"}
    elapsed = int(time.time() - started)
    if elapsed > SEND_TIMEOUT_S:
        err = ""
        try:
            with open(p["err"], encoding="utf-8") as f:
                err = f.read().strip()[:300]
        except OSError:
            pass
        return {"ready": True, "ok": False,
                "error": err or f"Keine Antwort nach {elapsed}s"}
    return {"ready": False, "elapsed": elapsed}

#!/usr/bin/env python3
"""The four things that can answer a message, behind one interface.

WHY

On 2026-09-02 Felix wrote twice from his phone and got nothing: "You've hit
your session limit · resets 11:30am (UTC)". One of those turns had already
cost $6.79 before it hit the wall. Three hours of nothing, from an assistant
that had three other engines sitting idle on the same machine.

So the chat is no longer wired to one of them. Four engines, one interface:

    claude   the real Claude Code session, resumed - the expensive, capable
             one with a session limit that is the reason this file exists.
    aios     the local worker: the task queue, the agent routing, the
             OpenRouter/Groq/Cerebras chain. Free tier first, GLM behind it.
    gemini   Google's API directly, with its own history.
    codex    OpenAI's Codex CLI, once it is installed and signed in.

WHAT "ONE INTERFACE" MEANS HERE

Every engine takes a message and returns a ticket, and every ticket is
collected the same way. That matters more than it looks: a turn can take
minutes, a phone browser will not hold a request open that long, and the
lesson has already been learned twice in this codebase - once when a
93-second reply arrived as "failed to fetch", once when a webapp restart
killed a detached job nobody was watching for.

Engines differ in what they are, not in how they are called. claude resumes
a session by id; gemini keeps its own thread; aios goes through the task
queue and its agent routing. The caller picks a name and a model.

Stdlib only.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
JOBS_DIR = os.path.join(TASK_RUNNER_DIR, "engine_jobs")
INBOX = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
LOGS = os.path.join(TASK_RUNNER_DIR, "tasks", "logs")

import claude_chat
import codex_chat
import gemini_chat
import antigravity_chat

JOB_RE = re.compile(r"[a-z]{2,8}_[\w.-]{1,60}")
# A turn that has produced nothing for this long is not slow, it is gone.
JOB_TIMEOUT_S = 900

# --- running out, and what to do about it ---------------------------------
#
# Felix: "i want each of you to give the remaining work to another model and
# tell me instead of just hitting the limit walls". That is the exact failure
# of 2026-09-02: he wrote twice from his phone, both turns died on "You've
# hit your session limit · resets 11:30am (UTC)", one of them after spending
# $6.79, and three other engines sat idle on the same machine for three
# hours.
#
# So a limit is no longer an outcome. It is a routing decision, and it is
# announced - a silent handoff would be its own kind of lie, because the
# engines are not interchangeable and he needs to know which one answered.

LIMIT_RE = re.compile(
    r"(session limit|rate.?limit|quota|exceeded your current|usage limit|"
    r"too many requests|429|insufficient_quota|erschöpft|kontingent)", re.I)
RESET_RE = re.compile(
    r"reset[s]?\s+(?:at\s+)?([0-9]{1,2}[:.][0-9]{2}\s*(?:am|pm)?[^\n.,;]{0,20})", re.I)

# Who takes over from whom. Roughly capability-descending, and every engine
# appears so that a chain never runs out of somewhere to go.
FALLBACK_ORDER = ["claude", "codex", "google-pro", "gemini", "aios"]
LIMIT_STATE = os.path.join(TASK_RUNNER_DIR, "spend", "engine_limits.json")
# How long a remembered limit is trusted when the engine did not say when it
# resets. Long enough not to retry into the same wall every thirty seconds,
# short enough that a wrong guess costs one hour, not a day.
LIMIT_ASSUME_S = 3600


def is_limit(text):
    return bool(text) and bool(LIMIT_RE.search(str(text)))


def _limits():
    try:
        with open(LIMIT_STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def mark_limited(engine, message):
    """Remember that this engine said no, and roughly for how long."""
    state = _limits()
    reset = RESET_RE.search(str(message) or "")
    state[engine] = {"at": time.time(), "message": str(message)[:300],
                     "resets": reset.group(1).strip() if reset else None,
                     "until": time.time() + LIMIT_ASSUME_S}
    try:
        os.makedirs(os.path.dirname(LIMIT_STATE), exist_ok=True)
        tmp = LIMIT_STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1, sort_keys=True)
        os.replace(tmp, LIMIT_STATE)
    except OSError:
        pass
    return state[engine]


def clear_limit(engine):
    state = _limits()
    if state.pop(engine, None) is not None:
        try:
            with open(LIMIT_STATE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=1, sort_keys=True)
        except OSError:
            pass


def limited(engine):
    """-> the remembered limit if it is still believed, else None."""
    row = _limits().get(engine)
    if not row:
        return None
    if time.time() > row.get("until", 0):
        clear_limit(engine)
        return None
    return row


def next_engine(after, exclude=()):
    """The next engine that can actually take the work. -> id or None."""
    skip = {after} | set(exclude)
    for name in FALLBACK_ORDER:
        if name in skip or name not in ENGINES:
            continue
        ok, _ = ENGINES[name]["available"]()
        if ok and not limited(name):
            return name
    return None


# --- a generic detached job ------------------------------------------------
#
# The same shape claude_chat uses, for the engines that are a command line.
# Written as a shell line so the rename happens in the same detached process:
# the presence of the .json file is then the only "is it done" signal a
# poller needs, and it can never observe a half-written one.

def _paths(job_id):
    return {"out": os.path.join(JOBS_DIR, f"{job_id}.json"),
            "part": os.path.join(JOBS_DIR, f"{job_id}.json.part"),
            "err": os.path.join(JOBS_DIR, f"{job_id}.err"),
            "meta": os.path.join(JOBS_DIR, f"{job_id}.meta"),
            "prompt": os.path.join(JOBS_DIR, f"{job_id}.prompt")}


def _spawn(prefix, build_argv, message, meta=None, cwd=None):
    """Run one command detached and remember where its answer will land.

    build_argv is a callable, not a list, because two of the three callers
    need the prompt's path - and the prompt file does not exist until the job
    has an id. Passing a placeholder into a list and substituting it later is
    the version of this that silently sends the literal word "PROMPT" to the
    model, which is exactly what the first draft did."""
    os.makedirs(JOBS_DIR, exist_ok=True)
    job_id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    p = _paths(job_id)
    with open(p["prompt"], "w", encoding="utf-8") as f:
        f.write(message)
    argv = build_argv(p["prompt"], message)
    cmd = (" ".join(shlex.quote(a) for a in argv)
           + f" > {shlex.quote(p['part'])} 2> {shlex.quote(p['err'])};"
           + f" mv {shlex.quote(p['part'])} {shlex.quote(p['out'])}")
    proc = subprocess.Popen(["sh", "-c", cmd], cwd=cwd or TASK_RUNNER_DIR,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    with open(p["meta"], "w", encoding="utf-8") as f:
        json.dump(dict(meta or {}, started=time.time(), pid=proc.pid,
                       message=message[:2000]), f, ensure_ascii=False)
    return job_id


def _alive(pid, job_id):
    """Is that pid still this job? Both halves matter - pids are reused, and
    the command line still carries the job id."""
    if not pid:
        return True
    try:
        with open(f"/proc/{int(pid)}/cmdline", "rb") as f:
            return job_id.encode() in f.read()
    except (OSError, ValueError):
        return False


def _collect(job_id):
    p = _paths(job_id)
    if os.path.exists(p["out"]):
        raw = ""
        try:
            with open(p["out"], encoding="utf-8") as f:
                raw = f.read().strip()
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            # A command that printed prose instead of JSON still said
            # something, and showing it beats "unreadable".
            return {"ready": True, "ok": bool(raw), "reply": raw[:8000],
                    "error": None if raw else "leere Antwort"}
        return {"ready": True, "ok": not data.get("is_error"),
                "reply": data.get("result") or "",
                "error": data.get("result") if data.get("is_error") else None,
                "model": data.get("model"), "usage": data.get("usage"),
                "usd": data.get("total_cost_usd")}
    try:
        meta = json.load(open(p["meta"], encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ready": False, "lost": True, "error": "Job nicht mehr auffindbar"}
    elapsed = int(time.time() - meta.get("started", 0))
    if not _alive(meta.get("pid"), job_id) and elapsed > 5:
        err = ""
        try:
            with open(p["err"], encoding="utf-8") as f:
                err = f.read().strip()[:400]
        except OSError:
            pass
        return {"ready": True, "ok": False, "died": True,
                "error": err or "Der Prozess wurde beendet, bevor er antworten konnte."}
    if elapsed > JOB_TIMEOUT_S:
        return {"ready": True, "ok": False, "error": f"Keine Antwort nach {elapsed}s"}
    return {"ready": False, "elapsed": elapsed}


# --- the engines -----------------------------------------------------------

CLAUDE_MODELS = ["opus", "sonnet", "haiku"]
CODEX_BIN = os.environ.get("AIOS_CODEX_BIN", "codex")


def _codex_available():
    # Asked of the CLI itself. Guessing from the presence of an auth file was
    # the first version of this and it is the kind of guess that reports
    # "ready" to someone who is about to get a login error.
    return codex_chat.logged_in()


def _gemini_available():
    if not os.environ.get("GEMINI_API_KEY"):
        return False, "GEMINI_API_KEY ist nicht in .env gesetzt"
    return True, ""


def _google_pro_available():
    return antigravity_chat.available()


def _claude_available():
    if not shutil.which(os.environ.get("AIOS_CLAUDE_BIN", "claude")):
        return False, "claude CLI ist nicht installiert"
    return True, ""


ENGINES = {
    "claude": {
        "label": "Claude",
        "note": "Die Sitzung vom Rechner, fortgesetzt. Kann am Sitzungslimit hängen.",
        "models": CLAUDE_MODELS,
        "default_model": "opus",
        "available": _claude_available,
        "threads": "session",
    },
    "aios": {
        "label": "AI-OS",
        "note": "Der lokale Worker: Agenten, Aufgabenschlange, freie Modelle zuerst.",
        "models": ["auto", "free", "paid"],
        "default_model": "auto",
        "available": lambda: (True, ""),
        "threads": "thread",
    },
    "gemini": {
        "label": "Google",
        "note": "Direkt an Googles API. Eigenes Kontingent pro Modell.",
        "models": gemini_chat.MODELS,
        "default_model": gemini_chat.DEFAULT_MODEL,
        "available": _gemini_available,
        "threads": "thread",
    },
    "google-pro": {
        "label": "Google AI Pro",
        "note": "Google AI Pro über Antigravity CLI, mit dem angemeldeten Konto.",
        "models": antigravity_chat.MODELS,
        "default_model": antigravity_chat.DEFAULT_MODEL,
        "available": _google_pro_available,
        "threads": "thread",
    },

    "codex": {
        "label": "Codex",
        "note": "OpenAIs Codex-CLI, sobald installiert und angemeldet.",
        "models": codex_chat.MODELS,
        "default_model": codex_chat.DEFAULT_MODEL,
        "available": _codex_available,
        "threads": "thread",
    },
}


def catalogue():
    """Every engine, whether it can answer, and what it can answer as."""
    out = []
    for name, spec in ENGINES.items():
        ok, reason = spec["available"]()
        out.append({"id": name, "label": spec["label"], "note": spec["note"],
                    "available": ok, "reason": reason,
                    "models": spec["models"], "default_model": spec["default_model"],
                    "threads": spec["threads"]})
    return out


def send(engine, message, model=None, thread=None, session=None, fallback=True):
    """Ask one engine. -> a ticket that result() can collect.

    If that engine is already known to be out - it refused within the last
    hour and has not reset - the work goes to the next one instead and the
    ticket says so. Sending into a wall that answered "session limit" five
    minutes ago is not respecting a choice, it is wasting a turn."""
    spec = ENGINES.get(engine)
    if not spec:
        raise ValueError(f"unbekannte Engine: {engine!r}")
    ok, reason = spec["available"]()
    if not ok:
        raise ValueError(reason)

    row = limited(engine) if fallback else None
    if row:
        nxt = next_engine(engine)
        if nxt:
            note = (f"{spec['label']} ist am Limit"
                    + (f" (zurück {row['resets']})" if row.get("resets") else "")
                    + f" — {ENGINES[nxt]['label']} übernimmt.")
            _tell_felix(note + f"\n\nFrage: {message.strip()[:300]}")
            ticket = send(nxt, message, thread=thread, fallback=False)
            ticket["handed_off"] = {"from": engine, "to": nxt,
                                    "note": note, "limit": row}
            return ticket
    message = (message or "").strip()
    if not message:
        raise ValueError("leere Nachricht")
    model = model or spec["default_model"]
    if model not in spec["models"]:
        raise ValueError(f"{spec['label']} kennt das Modell {model!r} nicht")

    if engine == "claude":
        return {"engine": "claude",
                "job": claude_chat.send(session or "", message, model=model)}

    if engine == "gemini":
        return {"engine": "gemini", "job": _spawn(
            "gem",
            lambda prompt_path, _text: [
                "python3", os.path.join(SCRIPT_DIR, "gemini_chat.py"),
                "--json", "--model", model, "--thread", thread or "web",
                "--prompt-file", prompt_path],
            message, meta={"model": model, "thread": thread})}

    if engine == "google-pro":
        return {"engine": "google-pro", "job": _spawn(
            "gpro",
            lambda prompt_path, _text: [
                "python3", os.path.join(SCRIPT_DIR, "antigravity_chat.py"),
                "--json", "--model", model, "--prompt-file", prompt_path],
            message, meta={"model": model, "thread": thread}, cwd=claude_chat.PROJECT_DIR)}


    if engine == "codex":
        return {"engine": "codex", "job": _spawn(
            "cdx",
            lambda prompt_path, _text: [
                "python3", os.path.join(SCRIPT_DIR, "codex_chat.py"),
                "--json", "--model", model, "--prompt-file", prompt_path],
            message, meta={"model": model}, cwd=claude_chat.PROJECT_DIR)}

    # aios: the same task file dispatch_task.py and telegram_bridge.py write.
    return {"engine": "aios", "job": _aios_send(message, thread, model)}


def _aios_send(message, thread, model):
    import agents
    import memory
    agent = None
    if message.startswith("@"):
        head, _, rest = message.partition(" ")
        resolved = agents.resolve(head)
        if resolved:
            agent, message = resolved, rest.strip()
    if not message:
        raise ValueError("nach dem @agent-Präfix steht nichts")
    memory_thread = f"web_{thread or 'engine'}"
    body = (memory.directive(memory_thread)
            + (agents.directive(agent) if agent else ""))
    # The worker reads its model preference from the task itself, so "free"
    # and "paid" are a line in the file rather than a second code path.
    if model in ("free", "paid"):
        body += f"<!-- models: {model} -->\n"
    body += message
    for d in (INBOX, LOGS):
        os.makedirs(d, exist_ok=True)
    name = f"task_web_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.md"
    path = os.path.join(INBOX, name)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)   # atomic enqueue
    return name


def _raw_result(engine, job):
    if engine == "claude":
        return claude_chat.result(job)
    if engine == "aios":
        return _aios_result(job)
    if not JOB_RE.fullmatch(job or ""):
        raise ValueError("ungültige job id")
    return _collect(job)


def job_message(engine, job):
    """What was originally asked. -> the text, or ""."""
    meta = (os.path.join(TASK_RUNNER_DIR, "claude_jobs", f"{job}.meta")
            if engine == "claude" else _paths(job)["meta"])
    try:
        with open(meta, encoding="utf-8") as f:
            return json.load(f).get("message", "")
    except (OSError, json.JSONDecodeError):
        return ""


def result(engine, job, fallback=True, notify=True):
    """Collect that ticket - and if it died on a limit, hand the work on.

    The handoff returns a NEW ticket rather than an answer: the next engine
    has only just been asked. The caller follows the engine/job it gets back,
    which is the same thing it was already doing."""
    res = _raw_result(engine, job)
    if not (res.get("ready") and not res.get("ok") and is_limit(res.get("error"))):
        return res

    row = mark_limited(engine, res.get("error"))
    if not fallback:
        return res
    message = job_message(engine, job)
    nxt = next_engine(engine)
    if not nxt or not message:
        # Nowhere to go, or nothing left to re-ask. Say which, rather than
        # reporting the original refusal as if nothing had been tried.
        res["limit"] = row
        res["error"] = (f"{ENGINES[engine]['label']} ist am Limit"
                        + (f" (zurück {row['resets']})" if row.get("resets") else "")
                        + (". Keine andere Engine ist gerade frei."
                           if not nxt else ". Die Frage ist nicht mehr auffindbar."))
        return res

    try:
        ticket = send(nxt, message, thread=_job_thread(engine, job))
    except ValueError as e:
        res["limit"] = row
        res["error"] = f"{ENGINES[engine]['label']} am Limit, {nxt} auch nicht möglich: {e}"
        return res

    note = (f"{ENGINES[engine]['label']} ist am Limit"
            + (f" (zurück {row['resets']})" if row.get("resets") else "")
            + f" — {ENGINES[nxt]['label']} übernimmt.")
    if notify:
        _tell_felix(note + f"\n\nFrage: {message[:300]}")
    return {"ready": False, "handed_off": {"from": engine, "to": nxt,
                                           "note": note, "limit": row},
            "engine": nxt, "job": ticket["job"], "elapsed": 0}


def _job_thread(engine, job):
    meta = (os.path.join(TASK_RUNNER_DIR, "claude_jobs", f"{job}.meta")
            if engine == "claude" else _paths(job)["meta"])
    try:
        with open(meta, encoding="utf-8") as f:
            return json.load(f).get("thread")
    except (OSError, json.JSONDecodeError):
        return None


def _tell_felix(text):
    """A handoff that happens silently is its own kind of lie - the engines
    are not interchangeable and he needs to know which one answered."""
    try:
        from send_telegram_notification import send as tg
        tg(text)
    except Exception:  # noqa: BLE001 - a failed notice must not fail the handoff
        pass


def _aios_result(task_id):
    if not re.fullmatch(r"task_web_[\w.-]{1,60}\.md", task_id or ""):
        raise ValueError("ungültige task id")
    log_path = os.path.join(LOGS, f"{task_id}.log")
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            return {"ready": True, "ok": True, "reply": f.read().strip()}
    queued = os.path.join(INBOX, task_id)
    running = os.path.join(TASK_RUNNER_DIR, "tasks", "completed", task_id)
    if not os.path.exists(queued) and not os.path.exists(running):
        return {"ready": False, "lost": True, "error": "Aufgabe nicht mehr auffindbar"}
    try:
        age = int(time.time() - os.path.getmtime(
            queued if os.path.exists(queued) else running))
    except OSError:
        age = 0
    return {"ready": False, "elapsed": age}

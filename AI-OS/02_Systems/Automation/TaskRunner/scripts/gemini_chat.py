#!/usr/bin/env python3
"""Google Gemini as a chat engine, with its own conversation history.

WHY THIS EXISTS

On 2026-09-02 Felix wrote twice from his phone and got nothing both times:
"You've hit your session limit · resets 11:30am (UTC)". One of those turns
had already cost $6.79 before it hit the wall. His question was the obvious
one - "how can I use Google ai pro again when your limit runs out?" - and the
answer should not be "wait three hours".

This is the Google half of that. Same shape as claude_chat.py: a message in,
an answer out, history kept per thread so it is a conversation rather than a
sequence of strangers.

WHAT IT IS NOT

It is not Google AI Pro. That subscription belongs to the Gemini app and the
Gemini CLI's ChatGPT-style sign-in; this talks to the Generative Language API
with GEMINI_API_KEY, which has its own free tier and its own quota. Measured
2026-09-02: gemini-3.1-pro-preview already answered 429 "you exceeded your
current quota", while gemini-flash-lite-latest and gemini-3-flash-preview
answered fine. So the limits are real, they differ per model, and the honest
thing is to report the API's own words rather than a number invented here.

Stdlib only - no google SDK, because this service runs under plain
/usr/bin/python3 like the rest of the webapp.
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
import shared_briefing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
THREADS_DIR = os.path.join(TASK_RUNNER_DIR, "tasks", "threads")
STATE_PATH = os.path.join(TASK_RUNNER_DIR, "spend", "gemini_state.json")

API = "https://generativelanguage.googleapis.com/v1beta/models"
HTTP_TIMEOUT = 180

# Checked live on 2026-09-02 against Felix's key: these answered, and the
# 2.5 family returned "no longer available to new users". Ordered cheapest-
# and-fastest first, because the reason this engine exists is that the
# expensive one ran out.
MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.1-pro-preview",
]
DEFAULT_MODEL = "gemini-3-flash-preview"
# How much of a conversation is resent. Gemini is stateless per call, so the
# history IS the context - and an unbounded one turns a cheap engine into an
# expensive one without saying so.
HISTORY_TURNS = 20


class GeminiError(RuntimeError):
    pass


def _key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise GeminiError("GEMINI_API_KEY ist nicht gesetzt")
    return key


def thread_path(thread_id):
    return os.path.join(THREADS_DIR, f"gem_{thread_id}.json")


def load_thread(thread_id):
    try:
        with open(thread_path(thread_id), encoding="utf-8") as f:
            data = json.load(f)
        return data.get("turns", [])
    except (OSError, json.JSONDecodeError):
        return []


def save_thread(thread_id, turns):
    os.makedirs(THREADS_DIR, exist_ok=True)
    path = thread_path(thread_id)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"thread_id": thread_id, "turns": turns[-HISTORY_TURNS * 2:],
                   "updated": datetime.now().isoformat(timespec="seconds")},
                  f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _record(model, usage, error=None):
    """Remember what the API last said about this model.

    Quota is not a number this side can compute - it is a thing Google
    decides and only mentions when it says no. So the last answer is kept,
    including the refusal, and the cost view reports that rather than a
    guess."""
    try:
        state = {}
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
        row = state.get(model) or {"calls": 0, "prompt_tokens": 0, "output_tokens": 0}
        row["calls"] += 1
        row["last"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if error:
            row["last_error"] = str(error)[:200]
        else:
            row.pop("last_error", None)
            row["prompt_tokens"] += usage.get("promptTokenCount", 0) or 0
            row["output_tokens"] += usage.get("candidatesTokenCount", 0) or 0
        state[model] = row
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1, sort_keys=True)
        os.replace(tmp, STATE_PATH)
    except OSError:
        pass


def state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def ask(message, thread_id="web", model=None, system=None):
    """One turn. -> {"reply", "model", "usage"}."""
    model = model or DEFAULT_MODEL
    system = f"{shared_briefing.system_instruction()}\n\n{system}" if system else shared_briefing.system_instruction()
    turns = load_thread(thread_id)
    contents = []
    for turn in turns[-HISTORY_TURNS * 2:]:
        contents.append({"role": turn["role"],
                         "parts": [{"text": turn["text"]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    body = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    req = urllib.request.Request(
        f"{API}/{model}:generateContent?key={_key()}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            pass
        _record(model, {}, error=detail or str(e))
        # 429 is the whole reason this engine exists, so it says so plainly
        # instead of arriving as "HTTP Error 429".
        if e.code == 429:
            raise GeminiError(f"{model}: Google-Kontingent erschöpft. "
                              f"Anderes Modell wählen. ({detail[:120]})")
        raise GeminiError(f"{model}: {detail or e}")
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        _record(model, {}, error=str(e))
        raise GeminiError(f"{model}: {e}")

    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "")
        _record(model, {}, error=f"keine Antwort ({reason})")
        raise GeminiError(f"{model} hat nichts geliefert{f' ({reason})' if reason else ''}")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    reply = "".join(p.get("text", "") for p in parts).strip()
    usage = data.get("usageMetadata") or {}
    _record(model, usage)

    turns.append({"role": "user", "text": message,
                  "ts": datetime.now().isoformat(timespec="seconds")})
    turns.append({"role": "model", "text": reply, "model": model,
                  "ts": datetime.now().isoformat(timespec="seconds")})
    save_thread(thread_id, turns)
    return {"reply": reply, "model": model,
            "usage": {"prompt": usage.get("promptTokenCount", 0),
                      "output": usage.get("candidatesTokenCount", 0),
                      "total": usage.get("totalTokenCount", 0)}}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--thread", default="cli")
    ap.add_argument("--prompt-file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("message", nargs="*")
    args = ap.parse_args(argv)
    text = (open(args.prompt_file, encoding="utf-8").read()
            if args.prompt_file else " ".join(args.message))
    try:
        out = ask(text, thread_id=args.thread, model=args.model)
    except GeminiError as e:
        if args.json:
            print(json.dumps({"is_error": True, "result": str(e)}, ensure_ascii=False))
            return 1
        print(f"[!] {e}")
        return 1
    if args.json:
        print(json.dumps({"is_error": False, "result": out["reply"],
                          "model": out["model"], "usage": out["usage"]},
                         ensure_ascii=False))
    else:
        print(out["reply"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

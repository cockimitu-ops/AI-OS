#!/usr/bin/env python3
"""Ask another engine a question, from inside whichever one is running.

Felix asked that the AIs be able to prompt each other. This is the whole
mechanism, deliberately: a command line. Every engine on this machine can run
a shell command - the worker through Open Interpreter, Claude and Codex
through their own Bash tools - so a command is the one interface all four
already have. Anything richer would be a protocol only some of them speak.

    python3 scripts/ask.py google "Was ist an diesem Regex falsch? ..."
    python3 scripts/ask.py aios "Lauf den Sniper und sag mir was rauskam"
    python3 scripts/ask.py claude --session <id> "Warum hast du das so gebaut?"

WHY THIS IS USEFUL AND NOT JUST CUTE

The engines are good at different things and cost differently. The worker is
free and knows the vault; Google is fast and has its own quota; Claude is
expensive, capable, and runs out. A worker that can ask Google to read a wall
of text before deciding what to do with it is cheaper than one that cannot.
And on 2026-09-02, when Claude hit its session limit for three hours, every
other engine on the box was idle.

WHAT IT DELIBERATELY DOES NOT DO

It does not let an engine start work in Felix's name. The answer comes back
as text to whoever asked; nothing is queued, approved or sent anywhere. The
propose/approve gate stays the only path from an idea to an action.

It also refuses to call itself in a loop: AIOS_ASK_DEPTH bounds how far a
chain of "ask the other one" can go, because two agents that can each ask the
other is a machine that can spin forever on someone else's money.
"""
import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import engines  # noqa: E402

# How long to wait for the other engine before giving up. Long enough for a
# real Claude turn, short enough that a wedged call does not hold the caller
# forever.
DEFAULT_TIMEOUT_S = 600
# One engine may ask another, and that one may ask a third. Three is already
# more indirection than any real question needs.
MAX_DEPTH = 3
ALIASES = {"google": "gemini", "gemini": "gemini", "worker": "aios",
           "aios": "aios", "claude": "claude", "codex": "codex"}


def ask(engine, message, model=None, session=None, thread="ask",
        timeout=DEFAULT_TIMEOUT_S):
    """-> (ok, text). Blocks until the other engine answers."""
    engine = ALIASES.get((engine or "").lower())
    if not engine:
        return False, (f"Unbekannte Engine. Bekannt: "
                       f"{', '.join(sorted(set(ALIASES)))}")
    depth = int(os.environ.get("AIOS_ASK_DEPTH", "0"))
    if depth >= MAX_DEPTH:
        return False, (f"Zu tief verschachtelt ({depth}). Eine Kette von "
                       f"'frag die andere' endet hier absichtlich.")
    # Raised only once the call is actually going ahead, and only for the
    # child: incrementing before the check made the refusal report a depth
    # one higher than the real one.
    os.environ["AIOS_ASK_DEPTH"] = str(depth + 1)
    try:
        ticket = engines.send(engine, message, model=model, thread=thread,
                              session=session)
    except ValueError as e:
        return False, str(e)

    deadline = time.time() + timeout
    wait = 1.0
    while time.time() < deadline:
        time.sleep(wait)
        wait = min(wait * 1.3, 6.0)
        res = engines.result(ticket["engine"], ticket["job"])
        if res.get("ready"):
            return bool(res.get("ok")), (res.get("reply") or res.get("error") or "")
        if res.get("lost"):
            return False, res.get("error", "verloren")
    return False, f"Keine Antwort nach {timeout}s"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("engine", help="google | aios | claude | codex")
    ap.add_argument("message", nargs="*", help="die Frage")
    ap.add_argument("--model")
    ap.add_argument("--session", help="nur für claude: die Sitzungs-ID")
    ap.add_argument("--thread", default="ask")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    ap.add_argument("--file", help="Frage aus einer Datei statt aus argv")
    args = ap.parse_args(argv)

    text = (open(args.file, encoding="utf-8").read() if args.file
            else " ".join(args.message))
    if not text.strip():
        ap.error("keine Frage angegeben")

    ok, answer = ask(args.engine, text, model=args.model, session=args.session,
                     thread=args.thread, timeout=args.timeout)
    print(answer)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Checks a chat reply against how Felix actually writes, and says what is off.

Why this exists as code rather than as a stronger prompt: the voice profile
was already in the system prompt and the worker still answered him in
assistant format. Reading tonight's real Telegram replies showed a precise
failure - the register held on throwaway lines ("jo, was gibt's?") and
collapsed the moment the answer had substance, into bold headers, numbered
lists and four paragraphs. Asking a model more nicely does not fix a habit
that strong; measuring the output and handing back a specific correction
does. Same shape as aios_runner.py's synthesis nudge.

Every threshold below is a counted fact about his 55,809 real WhatsApp
messages, not a taste judgement:

    markdown bold          0.01% of messages
    bullet-list lines      0.01%
    numbered-list lines    0.01%
    markdown headings      0.00%
    more than one line     0.07%
    words: p50 3, p90 10, p95 15, p99 28

So a bulleted, bolded, four-paragraph answer is not "a bit formal for him" -
it is a format he has effectively never used in his life.

Code is exempt. When he asks for a script he wants a script, and a fenced
block is not the model slipping into assistant voice - the prose around it is
what gets checked.

Stdlib only.
"""
import json
import os
import re

TASK_RUNNER_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(TASK_RUNNER_DIR, "voice", "stats.json")

FENCE_RE = re.compile(r"```.*?```", re.S)
BOLD_RE = re.compile(r"\*\*[^*\n]+\*\*")
HEADING_RE = re.compile(r"^\s{0,3}#{1,4}\s+\S", re.M)
BULLET_RE = re.compile(r"^\s*[-*•]\s+\S", re.M)
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+\S", re.M)

# Deliberately loose against the real distribution: p99 is 28 words, so 45 is
# already far outside what he writes, and the point is to catch an essay, not
# to police a sentence that ran three words long.
MAX_WORDS = 45
MAX_LINES = 4


def load_stats(path=STATS_PATH):
    """Never raises: no profile imported yet just means no checking."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _prose_only(text):
    """The reply minus fenced code blocks."""
    return FENCE_RE.sub(" ", text or "")


def violations(text, stats=None):
    """-> list of short, specific strings. Empty means it reads like him."""
    if not text or not text.strip():
        return []
    prose = _prose_only(text)
    had_code = prose != text
    out = []

    if BOLD_RE.search(prose):
        out.append("no **bold** - he has used it in 0.01% of 55,809 messages")
    if HEADING_RE.search(prose):
        out.append("no markdown headings - he has never used one")
    bullets = len(BULLET_RE.findall(prose)) + len(NUMBERED_RE.findall(prose))
    if bullets >= 2:
        out.append(f"no bullet or numbered lists ({bullets} here) - "
                   "0.01% of his messages have one")

    # Length and line count are only meaningful for prose. A reply that is
    # mostly a script he asked for is long because the script is long, and
    # trimming that would be obeying the letter of his style while destroying
    # the answer.
    if not had_code:
        lines = [ln for ln in prose.strip().splitlines() if ln.strip()]
        if len(lines) > MAX_LINES:
            out.append(f"{len(lines)} lines - 99.9% of his messages are one line")
        words = len(prose.split())
        if words > MAX_WORDS:
            out.append(f"{words} words - his 99th percentile is 28")
    return out


def nudge(found):
    """The correction handed back to the model. Names what was wrong rather
    than restating the whole profile: a specific, short instruction is far
    more likely to be followed than a repeat of what was already ignored."""
    if not found:
        return ""
    return (
        "Say that again the way Felix would actually text it. Specifically:\n"
        + "\n".join(f"- {v}" for v in found)
        + "\nSame information, same language, nothing dropped and nothing "
          "invented. Short, plain lines, the way one person texts another. "
          "Keep any code block exactly as it is."
    )


def is_better(candidate, original, stats=None):
    """Only accept a rewrite that is genuinely closer to his voice and has
    not thrown the answer away. A shorter reply that lost half the content is
    worse than a well-formatted one, so this refuses anything that collapsed
    to a fraction of the original."""
    if not candidate or not candidate.strip():
        return False
    if len(candidate.strip()) < len(original.strip()) * 0.25:
        return False
    return len(violations(candidate, stats)) < len(violations(original, stats))

#!/usr/bin/env python3
"""Agent selection for TaskRunner.

`04_Agents/` has held four scoped role definitions since Sprint 024, and until
now nothing could invoke them - they were documentation for a human typing "as
Research Analyst, do X" into a chat window. This module makes them selectable
by the worker, which is the whole difference between a definition and a
configuration.

One module rather than three copies, because dispatch_task.py, telegram_bridge.py
and aios_runner.py all need the same name resolution. If they disagreed about
what "@research" means, the CLI and Telegram would silently run different
agents.

The executable half of each agent file lives between AGENT_PROMPT markers, the
same convention System_Prompt.md uses for the worker's base prompt - so the
prose above it stays human-facing and editable without touching what the model
receives.
"""
import os
import re

VAULT = "/home/nost/AI-OS/AI-OS"
AGENTS_DIR = os.path.join(VAULT, "04_Agents")

START = "<!-- AGENT_PROMPT_START -->"
END = "<!-- AGENT_PROMPT_END -->"

# Canonical file stem -> aliases anyone might plausibly type at 7am on a phone.
# Kept deliberately generous: a rejected alias costs a whole round trip on
# Telegram, and there is no ambiguity to protect against with only four agents.
ALIASES = {
    "Vault_Architect": ["vault", "architect", "arch", "va"],
    "Content_Producer": ["content", "producer", "story", "cp"],
    "Research_Analyst": ["research", "analyst", "ra", "gig", "gigs"],
    "Business_Development": ["business", "bizdev", "biz", "bd", "sales"],
    "Study_Teacher": ["study", "teacher", "lernen", "uni", "lecture", "st"],
}

# Written into a task file's first line so the worker knows which agent to load.
# An HTML comment because task files are Markdown: invisible when rendered,
# trivially parsed, and harmless if a human opens one.
DIRECTIVE_RE = re.compile(r"^\s*<!--\s*agent:\s*([A-Za-z0-9_\-]+)\s*-->\s*\n?", re.I)

# An agent hands off by ending its output with this exact line - target and
# reason in one place so there's no ambiguity about how much trailing text
# counts as "the reason." Searched anywhere in the output (re.M), not just
# the start: unlike task-file directives, this is model-generated text, not
# something a caller controls the position of.
HANDOFF_RE = re.compile(
    r"^\s*<!--\s*handoff:\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*-->\s*$", re.I | re.M)

# A handoff-created task file carries this so a two-agent ping-pong can't run
# forever even if both sides ignore their own escalation instructions - free
# models under load already don't reliably follow prompt instructions (see
# System_Prompt.md's own guardrail section), so the cap is structural, not
# "the prompt tells it to stop."
# Which model tier a task wants. Same HTML-comment convention as the agent
# directive: invisible in rendered Markdown, trivially parsed, harmless if a
# human opens the task file. "paid" asks for the budget-capped paid model
# FIRST rather than only after every free tier has failed - for the handful
# of tasks where the answer's quality decides the outcome. It is a
# preference, never a guarantee: if the month's budget is spent, the runner
# falls straight through to the free chain.
MODEL_DIRECTIVE_RE = re.compile(
    r"^\s*<!--\s*model:\s*(paid|free|quality)\s*-->\s*\n?", re.I)

MAX_HANDOFF_DEPTH = 3
HANDOFF_DEPTH_RE = re.compile(r"^\s*<!--\s*handoff_depth:\s*(\d+)\s*-->\s*\n?", re.I)


def available():
    """Canonical agent names that actually exist on disk, not just in ALIASES."""
    if not os.path.isdir(AGENTS_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(AGENTS_DIR)
        if f.endswith(".md") and f != "README.md"
    )


def resolve(name):
    """Alias or partial name -> canonical agent name, or None.

    Case-insensitive, and tolerant of the hyphen/underscore/space confusion
    that is otherwise guaranteed when the same name is typed on a phone, in a
    shell, and in a Markdown file."""
    if not name:
        return None
    key = name.strip().lstrip("@").lower().replace("-", "_").replace(" ", "_")
    if not key:
        return None

    existing = available()
    lookup = {a.lower(): a for a in existing}
    if key in lookup:
        return lookup[key]

    for canonical, aliases in ALIASES.items():
        if canonical in existing and key in aliases:
            return canonical

    # Last resort: unambiguous prefix. "vault_arch" should work; "a" should not.
    matches = [a for a in existing if a.lower().startswith(key)]
    return matches[0] if len(matches) == 1 else None


def load_prompt(canonical):
    """The agent's executable prompt block. Returns None if the file has no
    markers - which is not an error: an agent can be documentation-only, and
    silently degrading to the base prompt beats refusing to run the task."""
    path = os.path.join(AGENTS_DIR, f"{canonical}.md")
    try:
        content = open(path, encoding="utf-8").read()
    except OSError:
        return None
    try:
        start = content.index(START) + len(START)
        end = content.index(END)
    except ValueError:
        return None
    block = content[start:end].strip()
    return block or None


def parse_directive(raw_task):
    """Split a task file into (canonical_agent_or_None, instruction).

    Unknown agent names are deliberately NOT an error - the directive is
    stripped and the task runs on the base prompt. A typo'd alias should cost
    a slightly worse answer, not a lost task."""
    m = DIRECTIVE_RE.match(raw_task or "")
    if not m:
        return None, (raw_task or "").strip()
    return resolve(m.group(1)), raw_task[m.end():].strip()


def directive(canonical):
    return f"<!-- agent: {canonical} -->\n"


def parse_handoff(output):
    """Look for a `<!-- handoff: Agent: reason -->` line anywhere in an
    agent's own output. Returns (canonical_agent_or_None, reason_or_None,
    cleaned_output) - cleaned_output has the directive line removed either
    way, since it's meant to trigger a follow-up task, not sit in what Felix
    reads on Telegram.

    An unresolvable agent name is treated the same as no handoff at all -
    same reasoning as parse_directive: a typo'd target should cost a skipped
    handoff, not a broken task."""
    m = HANDOFF_RE.search(output or "")
    if not m:
        return None, None, output
    cleaned = (output[:m.start()] + output[m.end():]).strip()
    canonical = resolve(m.group(1))
    if not canonical:
        return None, None, cleaned
    return canonical, m.group(2).strip(), cleaned


def parse_handoff_depth(raw_task):
    """Companion to parse_directive - strips a leading
    `<!-- handoff_depth: N -->` marker, present only on task files a handoff
    created itself. Returns (depth, remaining_text); depth is 0 for any
    ordinary task, which was never part of a handoff chain."""
    m = HANDOFF_DEPTH_RE.match(raw_task or "")
    if not m:
        return 0, raw_task or ""
    return int(m.group(1)), raw_task[m.end():]


def parse_model_directive(raw_task):
    """-> ("paid"|"free"|None, remaining_task_text)."""
    m = MODEL_DIRECTIVE_RE.match(raw_task or "")
    if not m:
        return None, raw_task
    pref = m.group(1).lower()
    return ("paid" if pref in ("paid", "quality") else "free"), raw_task[m.end():]


def model_directive(pref):
    return f"<!-- model: {pref} -->\n" if pref else ""


def model_preference(canonical):
    """An agent's own default tier, read from its file's `Preferred Model:`
    header.

    In the vault rather than hardcoded here, for the same reason the prompt
    blocks are: which roles are worth paying for is a judgement Felix should
    be able to change by editing a note, without touching the runner."""
    if not canonical:
        return None
    path = os.path.join(AGENTS_DIR, f"{canonical}.md")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("preferred model:"):
                    value = line.split(":", 1)[1].strip().lower()
                    return "paid" if value in ("paid", "quality") else "free"
                if line.startswith("---"):
                    break  # past the header block
    except OSError:
        pass
    return None


def handoff_depth_marker(depth):
    return f"<!-- handoff_depth: {depth} -->\n"


def summaries():
    """[(canonical_name, one_line_scope)] for every agent on disk.

    The scope line is each file's own `Purpose:` header - already written,
    already human-maintained, and already required by the vault's naming
    convention, so routing reads the same description a person would rather
    than a second copy that can drift from it."""
    out = []
    for name in available():
        path = os.path.join(AGENTS_DIR, f"{name}.md")
        purpose = ""
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Purpose:"):
                        purpose = line[len("Purpose:"):].strip()
                        break
        except OSError:
            pass
        # Wikilinks are noise to a model that cannot resolve them, and the
        # first sentence carries the scope; the rest is provenance.
        purpose = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", purpose)
        purpose = re.sub(r"\[\[([^\]]*)\]\]", r"\1", purpose)
        # First clause only: these headers trail into provenance ("Rescoped
        # 2026-08-13 — was horror-specific, but...") that describes the
        # file's history, not the role's scope.
        purpose = purpose.split(" — ")[0].split(". ")[0].strip()
        out.append((name, purpose))
    return out


def describe():
    """Human-readable roster, for --help and Telegram's /agents."""
    out = []
    for name in available():
        aliases = ALIASES.get(name, [])
        has = "" if load_prompt(name) else "  (no prompt block - runs on base prompt)"
        alias_str = ", ".join(f"@{a}" for a in aliases[:3])
        out.append(f"{name}{has}\n    {alias_str}")
    return "\n".join(out)


if __name__ == "__main__":
    print("Agents available to TaskRunner:\n")
    print(describe())

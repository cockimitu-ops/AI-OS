#!/usr/bin/env python3
"""One current, bounded briefing for every AI-OS engine."""
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
VAULT_DIR = os.path.abspath(os.path.join(TASK_RUNNER_DIR, "..", "..", ".."))
KNOWLEDGE_CORE_PATH = os.path.join(VAULT_DIR, "07_Context", "Knowledge_Core.md")
MAX_CHARS = 10_000


def load():
    """Return fresh standing context, bounded so it is safe on every turn."""
    try:
        with open(KNOWLEDGE_CORE_PATH, encoding="utf-8") as handle:
            return handle.read(MAX_CHARS).strip()
    except OSError:
        return ""


def system_instruction():
    """Shared instruction block for engines with a system-prompt channel."""
    core = load()
    lead = (
        "You are one of several AI engines serving Felix in AI-OS. "
        "Treat the standing context below as current project context. "
        "Follow Felix's explicit request; do not take actions in his name "
        "without a clear request or approval. Keep durable project knowledge "
        "in the vault rather than inventing a private memory."
    )
    return f"{lead}\n\n## Shared AI-OS briefing\n{core}" if core else lead


def prepend(message):
    """Give command-line engines the same context before the current request."""
    return f"{system_instruction()}\n\n## Felix's current request\n{message}"

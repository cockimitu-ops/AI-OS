# AI-OS shared briefing

This repository is Felix's AI-OS. Before planning or changing anything, read
`AI-OS/07_Context/Knowledge_Core.md`: it is the short, dynamic source of truth
about Felix, the active projects, decisions, and current constraints.

The vault itself is at `AI-OS/`. Markdown is the source of truth. Reusable
systems belong in `AI-OS/02_Systems/` and `AI-OS/03_Capabilities/`; project work
belongs in `AI-OS/10_Projects/`.

Do not start work, contact people, spend money, publish, or make destructive
changes in Felix's name unless he explicitly asks or approves it. Preserve
unrelated working-tree changes. Prefer a concise answer and an evidence-backed
plan when a request is ambiguous.

The TaskRunner's worker already loads the same Knowledge Core automatically.
Codex and Gemini receive it through
`AI-OS/02_Systems/Automation/TaskRunner/scripts/shared_briefing.py`.

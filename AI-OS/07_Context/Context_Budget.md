# Context Budget

Purpose: Practical limits on how much context gets loaded per task.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[07_Context/README|07_Context]], [[Loading_Strategy]], [[Dependency_Rules]]

---

## Default Budget
- **5–10 notes** per task, not whole folders.
- If a task's Required Notes alone exceed this, that's a signal the capability is scoped too broadly — split it, don't raise the budget.

## Enforcement
- Prefer loading a specific note over relying on a folder's README as a substitute for reading its contents. Exception: a folder `README.md` counts as one note when the task is genuinely about the folder's scope, not the notes inside it.
- If Optional Notes would push a task over budget, load only the one that resolves the specific gap — not the full optional list.

## Core vs. Dynamic
Every note is one of two stability tiers, stated in its header as `Stability: Core` or `Stability: Dynamic`:
- **Core** — rarely changes (Glossary, Home, Naming_Convention, Vision, Command_Index). Safe to treat as stable within a session; re-reading it mid-task is usually wasted budget.
- **Dynamic** — changes per sprint or session (Dashboard, Roadmap, any active project file). Always re-read if the task depends on current state.
Untagged notes default to Dynamic — safer to over-read than to act on stale state.
A hard ceiling without guidance gets hit and ignored. The budget pairs with [[Context_Resolution]]'s categories specifically so staying under it is the natural result of following the resolution order, not a separate constraint fought against afterward.

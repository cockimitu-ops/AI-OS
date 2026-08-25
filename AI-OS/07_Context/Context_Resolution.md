# Context Resolution

Purpose: How an AI determines which notes to load for a given task.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[07_Context/README|07_Context]], [[Dependency_Rules]], [[Loading_Strategy]]

---

## Four Categories

| Category | Definition | Load When |
|---|---|---|
| Required | Task cannot be done correctly without it | Always |
| Optional | Improves quality or handles edge cases | Only if that edge case is actually hit |
| Related | Useful background, not needed to execute | Only if asked, or referenced directly by Required/Optional context |
| Escalation | Needed only when something goes wrong | Only after a Failure Condition is hit |

## Resolution Order
1. Identify the capability the task maps to (`03_Capabilities/`).
2. Read that capability's declared **Required** context — nothing else, first.
3. Execute. If a gap appears, read the specific **Optional** note that covers it, not the whole optional list.
4. If execution fails, read the relevant **Escalation** context, not the entire system.
5. **Related** context is never auto-loaded — it's for a human or agent to follow deliberately.

## Anti-Pattern
Searching the vault for "anything relevant" is the failure mode this exists to prevent. If a capability doesn't declare its Required context, that's a gap in the capability note — not something to compensate for by reading broadly. See [[Dependency_Rules]].

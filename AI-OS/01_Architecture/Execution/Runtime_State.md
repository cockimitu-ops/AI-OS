# Runtime State

Purpose: What information exists only during execution, and why none of it becomes permanent automatically.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Execution/README|01_Architecture/Execution]], [[Execution_Lifecycle]], [[Learning_Loop]]

---

## What Counts as Runtime State

| Item | Scope |
|---|---|
| Current Task | The active [[Task_Specification]] instance |
| Loaded Context | Whatever [[Context_Resolution]] pulled in for this task |
| Temporary Decisions | Choices made mid-execution that aren't themselves outputs |
| Pending Learnings | Candidates identified in [[Learning_Loop]], not yet routed anywhere |
| Execution Log | A record of which stages ran and what they did |

## Why It Doesn't Persist Automatically
Runtime state is scoped to one task and one execution. Treating it as permanent by default would mean unvalidated, task-specific material could leak into the vault's source of truth without passing through [[Learning_Loop]] or [[Knowledge_Promotion]] — exactly the shortcut those two exist to prevent.

## Rule
At Finish, all runtime state is discarded except whatever Pending Learnings were explicitly routed through Learning Extraction. Nothing survives by default; everything that survives does so because it was deliberately promoted.

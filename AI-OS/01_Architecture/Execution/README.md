# Execution

Purpose: The Execution Engine — the model-independent runtime lifecycle every task in AI OS follows, regardless of which AI or automation executes it.
Last Updated: 2026-08-03
Status: Active — Sprint 005
Related Documents: [[01_Architecture/README|01_Architecture]], [[07_Context/README|07_Context]]

---

## Responsibility
Defines HOW a task executes — not what knowledge exists (that's `02_Systems/`, `03_Capabilities/`, `08_Research/`) and not what to read for a given task (that's `07_Context/`, the Context Engine). See [[Execution_Philosophy]] for why these are kept separate.

## Contents
- [[Execution_Philosophy]] — why Knowledge/Context/Execution/Agents/Automation are separated
- [[Execution_Lifecycle]] — the canonical Task→Finish pipeline
- [[Task_Specification]] — minimum info required before a task executes
- [[Quality_Assurance]] — execution-level QA (not content QA)
- [[Learning_Loop]] — what happens to what's learned after execution
- [[Runtime_State]] — what exists only during execution, and why it doesn't persist automatically
- [[Future_Integration]] — how Capabilities, Agents, MCP, Automation, and Workflows will plug in later (consolidated across all frameworks)

## Why This Lives in 01_Architecture/
The Execution Engine is a foundational, cross-cutting specification — like `Naming_Convention.md` or the ADR framework, it governs how work happens across the whole vault rather than belonging to one system or capability. It's a sibling subfolder to `ADR/`, not a new top-level folder, since adding a top-level folder is a structural change reserved for an ADR. Formalized in [[ADR-0003_Execution_Engine_Placement]].

## Status
Sprint 005 complete.

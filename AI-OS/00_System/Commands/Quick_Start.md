# Quick Start

Purpose: Walks through exactly what happens, mechanically, when a new chat opens and someone types a request — grounded entirely in existing framework notes, nothing new invented for this document.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[00_System/Commands/Command_Index|Command Index]], [[Context_Resolution]], [[Execution_Lifecycle]]

---

## Worked Example: "Generate a horror story."

1. **Intent Detection** (per [[Execution_Lifecycle]]): match against the [[00_System/Commands/Command_Index|Command Index]] — "generate a ___ story" matches the "Generate a story" row.
2. **Capability/Workflow Resolution**: maps to [[Reddit_Story_Production]].
3. **Context Resolution** (per [[Context_Resolution]]): read only [[Reddit_Story_Production]]'s own Required Notes ([[Workflow_Structure]], [[Workflow_Composition]]) — nothing extra, nothing pre-loaded "just in case."
4. **Execution**: the workflow runs its steps in order, per [[Workflow_Composition]] — each step resolves its own Required Notes independently. [[Hook_Writing]] loads [[Hook_Principles]] and [[Suspense_And_Curiosity]] only when that step actually runs, not upfront.
5. **"Horror" is a content parameter, not a routing signal** — it doesn't change which workflow runs, only what [[Story_Ideation]] and [[Story_Validation]] treat as the premise.
6. **Output**: a completed [[Publishing_Checklist]] instance, exactly matching [[Reddit_Story_Production]]'s own declared Output.

## Why This Stays Token-Efficient
No step in this sequence reads more than its own declared Required Notes (see [[Dependency_Rules]]). The [[00_System/Commands/Command_Index|Command Index]] is the one thing worth reading in full up front — it's small by design. Everything else loads only once it's actually needed, within the limits [[Context_Budget]] already sets.

## Other Examples
- "Review my analytics" → [[Review_Process]] → invokes [[Failure_Analysis]] / [[Viral_Analysis]] / [[Experiment_Tracking]] / [[Learning_Extraction]] only as needed, per [[Review_Process]]'s own rules — not all four every time.
- "Create captions" → [[Multi_Platform_Caption_Generation]] → loads [[Reddit_Story_Workflow]], its one Required Note.
- "Generate 10 ideas" → [[Story_Ideation]] → loads [[Storytelling_Fundamentals]] and [[Reddit_Story_Workflow]] only.

## When a Request Doesn't Match Anything
If a request doesn't match a row in the [[00_System/Commands/Command_Index|Command Index]], that's a signal to check the Index's own "Gaps" section before assuming something's broken — a few real gaps are already documented there rather than silently failing.

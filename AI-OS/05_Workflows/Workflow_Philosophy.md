# Workflow Philosophy

Purpose: Why workflows exist as their own layer, distinct from capabilities, knowledge, and agents.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Execution_Philosophy]], [[Analytics_Philosophy]], [[Task_Specification]]

---

## Core Principles
- A workflow is orchestration, not new capability. If a workflow needs logic that isn't just "call capability X, then capability Y," that logic belongs in a capability, not the workflow definition.
- A workflow holds no permanent knowledge of its own. Every fact it needs comes from a capability's Required Notes, resolved via the Context Engine — never restated inline.
- A workflow doesn't redefine execution or context mechanics. [[Execution_Lifecycle]] and [[Context_Resolution]] already state how a workflow should invoke them: once per capability in the chain, not once for the whole workflow.
- Determinism means the same inputs produce the same capability sequence every time. A workflow that branches on judgment calls rather than declared conditions isn't deterministic — that's agent territory, not workflow territory.

## Inputs
A defined goal that requires more than one capability to satisfy.

## Outputs
A named, reusable sequence of capability calls.

## Dependencies
None — this is the root note for the Workflow Framework, the same role [[Execution_Philosophy]] and [[Analytics_Philosophy]] play for their systems.

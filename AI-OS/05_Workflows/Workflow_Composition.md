# Workflow Composition

Purpose: How individual capabilities chain into a single workflow without duplicating Context or Execution mechanics.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Lifecycle]], [[Runtime_State]]
Required Notes: [[Workflow_Structure]], [[Execution_Lifecycle]], [[Context_Resolution]], [[Future_Integration]]

---

## Core Principles
- Composition means: for each step, run the full [[Execution_Lifecycle]] for that step's capability, once. This is exactly what [[Future_Integration]] already stated — "a workflow runs the full Execution Lifecycle once per capability in its chain, not once for the whole workflow." This note operationalizes that statement; it doesn't re-derive the reasoning.
- [[Context_Resolution]] runs per step too, not once for the whole workflow — matching [[Future_Integration]]'s own prediction, for the same reason: bounded context per step, not accumulated across the whole chain.
- A later step may reference an earlier step's Output as its own Input — this is the only form of state a workflow passes between steps. Nothing else persists across steps; [[Runtime_State]]'s discard rule applies per step, not per workflow.

## Inputs
An ordered list of capability steps, from [[Workflow_Structure]].

## Outputs
A composed execution — one Execution Lifecycle run per step, in order.

## Dependencies
[[Workflow_Structure]], [[Execution_Lifecycle]], [[Context_Resolution]].

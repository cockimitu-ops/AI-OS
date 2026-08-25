# Workflow Lifecycle

Purpose: How a workflow itself moves from defined to running to finished — the workflow-level counterpart to Execution Lifecycle.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Validation]], [[Workflow_Error_Handling]]
Required Notes: [[Workflow_Structure]], [[Execution_Lifecycle]]

---

## Core Principles
- A workflow's lifecycle: Defined → Triggered → Step Executing (repeated per step) → Validated → Finished. This does not replace [[Execution_Lifecycle]] — each Step Executing stage IS one full run of Execution Lifecycle for that step's capability.
- Finish only occurs once every step has either completed or been explicitly handled by [[Workflow_Error_Handling]]. A workflow that stops mid-sequence without either is Incomplete, not silently Finished.
- No step begins before the prior step's output is validated (see [[Workflow_Validation]]) — steps aren't launched speculatively in parallel; this framework version is sequential only.

## Inputs
A triggered workflow instance.

## Outputs
A sequence of completed (or explicitly handled) steps, ending in Finished or Incomplete.

## Dependencies
[[Workflow_Structure]] (what's being run), [[Execution_Lifecycle]] (what each step actually is).

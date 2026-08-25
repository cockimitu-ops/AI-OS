# Workflow Error Handling

Purpose: What happens when a step fails validation or fails to execute at all.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Review]]
Required Notes: [[Workflow_Lifecycle]], [[Workflow_Validation]], [[Failure_Analysis]]

---

## Core Principles
- A failed step doesn't automatically retry, skip, or abort the whole workflow — which applies is declared per-workflow, not assumed by the framework. A workflow definition that doesn't declare its failure behavior is incomplete, not defaulting to "abort."
- An aborted workflow is marked Incomplete (per [[Workflow_Lifecycle]]), not deleted. A partial result is often still useful, and the failure itself is data for [[Failure_Analysis]].
- A step failure is not itself a "learning" until it's actually been through [[Failure_Analysis]]. This note reports the failure; it doesn't diagnose it.

## Inputs
A failed step — execution failure or validation failure.

## Outputs
One of: retry, skip, abort, per the workflow's declared behavior — plus a report routed toward [[Failure_Analysis]] if applicable.

## Dependencies
[[Workflow_Lifecycle]], [[Workflow_Validation]], [[Failure_Analysis]].

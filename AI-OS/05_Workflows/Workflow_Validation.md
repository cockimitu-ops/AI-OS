# Workflow Validation

Purpose: How a workflow's actual output is checked against what it was supposed to produce.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Error_Handling]]
Required Notes: [[Quality_Assurance]], [[Workflow_Structure]]

---

## Core Principles
- Validation happens at two points: after each step (does this step's output satisfy what the next step needs as input) and at Finish (does the overall output satisfy the workflow's Success Criteria). This doesn't replace [[Quality_Assurance]] — a workflow's per-step QA is Quality Assurance run once per step, exactly as [[Execution_Lifecycle]] already dictates.
- A step that produces valid-but-unexpected output (right shape, wrong content) still needs a human-visible flag. Validation checks structure and completeness; it doesn't judge content quality, which belongs to the capability's own domain.
- Failed validation routes to [[Workflow_Error_Handling]], never silently continues to the next step with bad input.

## Inputs
A completed step's output, or the workflow's final output.

## Outputs
Pass, or a routed failure.

## Dependencies
[[Quality_Assurance]], [[Workflow_Structure]].

# Workflow Inputs and Outputs

Purpose: How a workflow's overall Inputs/Outputs relate to its individual steps' Inputs/Outputs.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Structure]], [[Workflow_Validation]]
Required Notes: [[Task_Specification]], [[Workflow_Structure]]

---

## Core Principles
- A workflow's declared Inputs (per [[Task_Specification]]) become the first step's Inputs. A workflow's declared Outputs are the last step's Outputs — not something computed separately afterward.
- An intermediate step's output that isn't consumed by a later step and isn't the workflow's final output is a signal the workflow has an unnecessary step, not a signal to keep it "just in case."
- A workflow's Success Criteria apply to the whole sequence, not to each step individually — a step can complete without necessarily satisfying the workflow's overall Success Criteria on its own. See [[Workflow_Validation]] for when that gets checked.

## Inputs
The workflow's own Objective and Inputs, per [[Task_Specification]].

## Outputs
The final step's Output, treated as the workflow's Output.

## Dependencies
[[Task_Specification]], [[Workflow_Structure]].

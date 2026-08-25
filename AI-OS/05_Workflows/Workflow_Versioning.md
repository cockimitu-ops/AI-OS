# Workflow Versioning

Purpose: How a workflow definition changes over time without breaking runs that already depend on it.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Review]]
Required Notes: [[Workflow_Structure]]

---

## Core Principles
- A workflow definition change — adding, removing, or reordering steps — is a new version, not an edit to the existing one. This mirrors how ADR decisions are never rewritten, only superseded.
- A running or recently-run workflow instance keeps referencing the version it actually ran under, even after a newer version exists. Otherwise [[Workflow_Review]] would be judging a run against rules it never actually followed.
- A capability update (e.g., `Hook_Writing`'s own rules changing) doesn't require a new workflow version by itself. The workflow still just says "run Hook Writing" — only a change to the step sequence itself is a workflow version change.

## Inputs
A proposed change to a workflow's step sequence.

## Outputs
A new workflow version, with the prior version retained rather than overwritten.

## Dependencies
[[Workflow_Structure]].

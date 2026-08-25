# Workflow Review

Purpose: How a completed (or incomplete) workflow run gets assessed after the fact — the workflow-level entry point into the Analytics system.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Versioning]], [[Continuous_Improvement_Cycle]]
Required Notes: [[Workflow_Lifecycle]], [[Review_Process]]

---

## Core Principles
- This is not a new review mechanism. A workflow run is completed work like any other and gets reviewed through the existing [[Review_Process]], not a separate workflow-specific process.
- What's specific to workflows here is what gets handed to Review Process: the full step sequence, which steps passed or failed validation, and any [[Workflow_Error_Handling]] outcomes — richer input than a single capability's result, but the same downstream process.
- A workflow that completes successfully every run is still worth reviewing occasionally — success without review can hide a workflow succeeding at the wrong thing. See [[Success_Criteria]].

## Inputs
A finished or incomplete workflow run, including its step-by-step record.

## Outputs
An entry into [[Review_Process]].

## Dependencies
[[Workflow_Lifecycle]], [[Review_Process]].

# Workflow Structure

Purpose: What a workflow definition actually contains.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[05_Workflows/README|05_Workflows]], [[Workflow_Philosophy]], [[Workflow_Composition]]
Required Notes: [[Workflow_Philosophy]], [[Task_Specification]]

---

## Core Principles
- A workflow definition is a named, ordered list of capability references — nothing else earns a place in the definition itself.
- Each step names exactly one entry from `03_Capabilities/`. A step that isn't backed by an existing capability isn't ready to be a workflow step — build the capability first.
- Steps carry no duplicated logic from the capability they reference. A step says "run Hook Writing"; it doesn't restate what Hook Writing does.

## Inputs
An ordered list of capability names, plus the workflow's own [[Task_Specification]]-style framing (Objective, Inputs, Constraints, Expected Outputs, Success Criteria).

## Outputs
A structured workflow definition, ready for [[Workflow_Composition]] to chain.

## Dependencies
[[Workflow_Philosophy]], [[Task_Specification]].

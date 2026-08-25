# Template Validation

Purpose: How a filled-in template instance gets checked before it's considered complete.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Lifecycle]]
Required Notes: [[Template_Variables]], [[Quality_Assurance]]

---

## Core Principles
- Validation checks that every required variable (see [[Template_Variables]]) was filled and every field matches its declared type. It does not judge whether the filled-in content is good — that belongs to whatever capability produced the content, the same boundary [[Quality_Assurance]] already draws for execution-level QA generally.
- A template instance missing a required variable is Incomplete, not silently accepted with a blank — the same discipline [[Workflow_Lifecycle]] applies to unhandled step failures.
- Validation runs once per filled instance, not once per template definition. The definition itself is checked separately, by [[Template_Quality_Standards]].

## Inputs
A filled-in template instance.

## Outputs
Pass, or a list of missing or mistyped fields.

## Dependencies
[[Template_Variables]], [[Quality_Assurance]].

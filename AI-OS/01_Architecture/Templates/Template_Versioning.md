# Template Versioning

Purpose: How a template definition changes over time without breaking instances already filled from an earlier version.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Lifecycle]]
Required Notes: [[Template_Structure]]

---

## Core Principles
- A structural change to a template — adding, removing, or retyping a field — is a new version, not an edit to the existing one. Same discipline as [[Workflow_Versioning]] and, before that, how ADRs are never rewritten.
- A filled instance keeps a record of which template version it was filled from, even after the template itself is updated — otherwise [[Template_Validation]] would be checking an instance against rules it was never filled under.
- A wording-only change to a field's description, with no structural change, doesn't require a new version. Only changes that would affect what a filled instance looks like structurally do.

## Inputs
A proposed change to a template's fields.

## Outputs
A new template version, with the prior version retained.

## Dependencies
[[Template_Structure]].

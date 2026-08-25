# Template Variables

Purpose: How placeholder values within a template get declared and filled.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Validation]]
Required Notes: [[Template_Structure]]

---

## Core Principles
- A variable is a named placeholder with a declared type and, where relevant, a declared source (e.g., "pulled from the workflow's Task Specification Objective field"). An undeclared blank isn't a variable — it's an error.
- Variables are filled at use time, by whatever capability or workflow invokes the template. The template itself never hardcodes a value, or it stops being reusable.
- A variable with no value at fill time is either explicitly optional (declared as such) or blocks completion. Silently leaving it blank is not a valid template state.

## Inputs
A template's declared fields, from [[Template_Structure]].

## Outputs
A set of named, typed variables, ready to be filled per use.

## Dependencies
[[Template_Structure]].

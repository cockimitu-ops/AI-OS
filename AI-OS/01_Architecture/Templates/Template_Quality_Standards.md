# Template Quality Standards

Purpose: What makes a template definition itself well-formed — checked once at definition time, not per filled instance (that's [[Template_Validation]]).
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Validation]], [[Template_Lifecycle]]
Required Notes: [[Template_Structure]], [[Context_Resolution]]

---

## Core Principles
- Every field has a stated purpose. A field that exists "in case it's useful," without a stated purpose, is a sign the template was drafted before the need was concrete — cut it or wait.
- No field duplicates information already available from context. A template shouldn't ask for something a capability could resolve through [[Context_Resolution]] instead of asking a human or model to retype it.
- A template definition follows the same atomic-note discipline as everything else in this vault: one template, one responsibility. A template trying to serve two structurally different purposes should be two templates.

## Inputs
A proposed or existing template definition.

## Outputs
A pass/fail against these standards — distinct from [[Template_Validation]]'s per-instance check.

## Dependencies
[[Template_Structure]], [[Context_Resolution]].

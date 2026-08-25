# Template Reuse

Purpose: How the same template gets used correctly across multiple capabilities or workflows without drifting into capability-specific variants.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Future_Integration]]
Required Notes: [[Template_Structure]]

---

## Core Principles
- A template is written once and referenced, never copied and locally modified. A capability needing a slightly different structure either uses the template as-is with more fields left optional, or the case for a genuinely new template is real — and it gets defined as one, not forked.
- Two capabilities using the same template should produce structurally comparable output. That's what makes the template worth having; if their outputs end up structurally incomparable despite sharing a template, something upstream — most likely [[Template_Variables]]' optionality — is too loose.
- A template's reuse count is itself a signal worth tracking through Analytics, not redefined here — a template referenced by exactly one thing may not need to be a template yet. See `Metrics_Framework` for how that kind of signal actually gets evaluated.

## Inputs
A template already defined, and a second (or later) capability or workflow wanting the same structure.

## Outputs
A shared reference, not a copy.

## Dependencies
[[Template_Structure]].

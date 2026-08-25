# Template Lifecycle

Purpose: How a template definition itself moves from proposed to active to retired.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Versioning]], [[Template_Quality_Standards]]
Required Notes: [[Template_Structure]], [[Review_Process]]

---

## Core Principles
- Lifecycle: Proposed → Active → (optionally) Deprecated → Retired. A template is Active as soon as it's referenced by at least one real capability or workflow — a template with no consumer stays Proposed, a valid, non-urgent state (see [[Template_Reuse]] on single-use templates possibly not needing to exist yet).
- Deprecating a template doesn't delete it or existing filled instances. It marks that new uses should prefer a replacement, while old instances remain valid under the version they were filled under (see [[Template_Versioning]]).
- A template's lifecycle stage is reviewed at the same cadence Analytics reviews everything else, through `Review_Process` — not a separate template-specific review cycle.

## Inputs
A template at any point from proposal to retirement.

## Outputs
A lifecycle stage, and for Retired specifically, a note of what — if anything — replaced it.

## Dependencies
[[Template_Structure]], `Review_Process`.

# Knowledge Promotion

Purpose: How information moves from an observation to permanent, loadable knowledge.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[07_Context/README|07_Context]], [[Principles]]

---

## Pipeline

```
Observation
 ↓
Experiment
 ↓
Validated Learning
 ↓
Permanent Knowledge
```

## Stage Definitions

| Stage | What It Is | Where It Lives |
|---|---|---|
| Observation | An unverified note — "this seems to work" | Not yet a vault file |
| Experiment | A deliberate test of the observation | `08_Research/`, once populated |
| Validated Learning | An experiment with a clear result | `08_Research/`, marked validated |
| Permanent Knowledge | A validated learning folded into a system, capability, or standard | `02_Systems/`, `03_Capabilities/`, or `01_Architecture/` — wherever it governs |

## Promotion Rule
Nothing skips a stage. An observation doesn't become permanent knowledge without passing through an experiment and a validated result — this is what keeps `02_Systems/` and `03_Capabilities/` from filling up with untested assumptions.

## Discard Rule
An observation or experiment that fails to validate isn't promoted, and isn't silently dropped either — it's recorded as a negative result in `08_Research/` (once populated) so the same idea isn't re-tested from scratch later.

## Relationship to Existing Governance
This pipeline governs *content* knowledge — how a system or capability should work. It does not replace `01_Architecture/ADR/`, which governs *structural* decisions about the vault itself. A validated learning that implies a structural change still requires an ADR — promotion through this pipeline is not a substitute for that process.

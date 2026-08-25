# Generation Mode Selection

Purpose: Decides Lite vs. Fast vs. Quality generation mode per clip (corrected 2026-08-13 — was documented as a Fast/Quality binary; Veo 3.1 actually has three tiers).
Last Updated: 2026-08-13
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[AI_Video_Production]]
Required Notes: [[AI_Video_Production]]
Used By: [[AI_Video_Production]]

---

## What It Does
Chooses which Veo 3.1 generation tier to use per clip, per [[AI_Video_Production]]'s tiering rules.

## Inputs / Outputs
In: clip concept, whether the prompt/concept is already validated, posting-volume context, performance expectation. Out: Lite, Fast, or Quality decision, recorded with a reason.

## Success Criteria
Fast for testing a new or unvalidated prompt/concept and for regular posting volume once validated. Quality only for a clip that's already confirmed to work and is expected to be a top performer — never as the first test of something new. Lite only for rough drafts where fidelity genuinely doesn't matter, not for judging whether a concept works.

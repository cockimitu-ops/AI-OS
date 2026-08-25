# Hook Writing

Purpose: Capability for writing the opening hook of a Reddit/TikTok story adaptation.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Hook_Principles]], [[Suspense_And_Curiosity]], [[Reddit_Story_Workflow]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Produces the opening line(s) of a story script. Applies [[Hook_Principles]] and [[Suspense_And_Curiosity]] — see those notes for the underlying craft; this capability adds only the platform-specific constraint of landing the first reveal within 20 seconds, per [[Reddit_Story_Workflow]].

## Inputs
- Source story (Reddit post or equivalent)
- Target platform

## Outputs
- Opening hook line(s), timed to land the first reveal within 20 seconds of playback

## Success Criteria
- The first reveal lands within 20 seconds (hard threshold, from [[Reddit_Story_Workflow]]).
- No sentence in the hook resolves the open loop it creates — see [[Hook_Principles]] for what counts as premature resolution.

## Validation
Content-specific check, not execution-level QA (see [[Quality_Assurance]] for that boundary): does the hook create an open loop without resolving it? A hook that states the outcome, even partially, fails regardless of how well-written it is.

## Analytics Reference
Reviewed via [[Metrics_Framework]] and [[Failure_Analysis]] once real output exists; outcomes are recorded in [[Hook_Database]]. A hook that fails to hold attention is a [[Failure_Analysis]] case, not automatically a Hook Writing defect — see that note's caution against single-cause explanations.

## Knowledge Dependencies
[[Hook_Principles]], [[Suspense_And_Curiosity]] — the craft this capability operationalizes. See Required Notes above for the complete prerequisite list, which also includes system context.

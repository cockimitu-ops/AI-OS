# Retention Beat Scripting

Purpose: Capability for structuring a script's escalation beats and cliffhangers.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Narrative_Structure]], [[Pacing]], [[Suspense_And_Curiosity]], [[Reader_Retention]], [[Reddit_Story_Workflow]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Places retention beats through a script's body, applying [[Narrative_Structure]], [[Pacing]], [[Suspense_And_Curiosity]], and [[Reader_Retention]]. Adds the specific timing and part-boundary rules [[Reddit_Story_Workflow]] requires on top of that general craft.

## Inputs
- Story outline
- Part number and total part count

## Outputs
- Beat-by-beat script skeleton with escalation points and a closing beat (cliffhanger or payoff)

## Success Criteria
- Escalation beat every 10–15 seconds (hard threshold, [[Reddit_Story_Workflow]]).
- First reveal within 20 seconds of the part's start.
- Every non-final part ends on an unresolved loop, per [[Reader_Retention]]; the final part resolves.
- Every sentence maps to exactly one purpose — see the sentence-purpose rule in [[Reddit_Story_Workflow]], not redefined here.

## Validation
Does every beat either escalate or resolve, per [[Pacing]]'s dead-zone rule? A beat that does neither fails regardless of prose quality.

## Analytics Reference
Beat pacing reviewed via [[Metrics_Framework]]; outcomes are recorded in [[Retention_Database]]. A part that loses retention mid-script (not at the hook) is a [[Failure_Analysis]] candidate for this capability specifically, since Hook Writing would already be ruled out by the point of failure.

## Knowledge Dependencies
[[Narrative_Structure]], [[Pacing]], [[Suspense_And_Curiosity]], [[Reader_Retention]].

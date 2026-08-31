# Story Drafting

Purpose: Capability for turning a validated idea into a structured multi-part outline.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Narrative_Structure]], [[Pacing]], [[Reddit_Story_Workflow]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Applies [[Narrative_Structure]]'s stages (setup, disruption, escalation, turning point, resolution) to a validated idea, and splits the result into parts per [[Reddit_Story_Workflow]]'s 3-part maximum. Produces a structural skeleton only — the actual hook, beats, cliffhangers, and ending are written by [[Hook_Writing]], [[Retention_Beat_Scripting]], [[Cliffhanger_Creation]], and [[Ending_Design]] respectively. This capability sequences the skeleton; it doesn't write final lines.

## Inputs
A validated story idea, from [[Story_Validation]].

## Outputs
A structured outline: which narrative stage falls in which part, and where each part boundary sits.

## Success Criteria
Every narrative stage from [[Narrative_Structure]] is placed in exactly one part; no stage is dropped, and no part is projected to exceed [[Reddit_Story_Workflow]]'s length target.

## Validation
Does the outline account for all five narrative stages, and does each part boundary land on an escalation or resolution point rather than mid-beat, per [[Pacing]]'s dead-zone rule?

## Analytics Reference
Outline-stage accuracy — did the eventual draft follow the outline, or deviate — is worth an occasional [[Review_Process]] spot-check, not a per-story requirement.

## Knowledge Dependencies
[[Narrative_Structure]], [[Pacing]].

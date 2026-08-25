# Metadata Generation

Purpose: Capability for producing a story's title, discovery tags, and series/part labeling — distinct from platform captions.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Reddit_Story_Workflow]]
Related Notes: [[Multi_Platform_Caption_Generation]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Generates the video title, discovery tags, and part-numbering label (e.g., "Part 1 of 3"). Distinct from [[Multi_Platform_Caption_Generation]], which produces the per-platform caption/description body — this capability covers the title and tags specifically.

## Inputs
The finished, TTS-optimized script and its story premise.

## Outputs
A title, a tag set, and a part label if the story has more than one part.

## Success Criteria
The title doesn't resolve the hook's open loop — the same discipline as [[Hook_Principles]], applied to the title specifically, since a title is often read before the hook plays. Part labeling is present on every multi-part story and absent on single-part stories.

## Validation
Does the title avoid spoiling the reveal, and is part-numbering consistent across all parts of the same story?

## Analytics Reference
Title-driven click-through is a [[Metrics_Framework]] measurement distinct from the hook's own retention measurement — a title can succeed independently of whether the hook then holds attention.

## Knowledge Dependencies
[[Hook_Principles]] — for the no-spoiler discipline, applied to titles.

# Reddit Story Production

Purpose: The first production workflow — sequences the full Reddit Story pipeline from validated idea to publish-ready output.
Last Updated: 2026-08-03
Status: Active — Workflow Version 1
Related Documents: [[10_Projects/SocialMediaContent/README|SocialMediaContent]], [[Reddit_Story_Workflow]]
Required Notes: [[Workflow_Structure]], [[Workflow_Composition]]

---

## Objective
Turn a validated Reddit story idea into a fully produced, publish-ready output: script, production settings, captions, metadata, and a completed Publishing Checklist.

## Steps
Per [[Workflow_Composition]], each step runs one full [[Execution_Lifecycle]], in order:

1. [[Story_Drafting]] — validated idea → structured outline
2. [[Hook_Writing]] — outline's opening → hook
3. [[Retention_Beat_Scripting]] — outline's body, per part → paced beats
4. [[Cliffhanger_Creation]] — every non-final part → closing lines
5. [[Ending_Design]] — final part → resolution
6. [[Story_Editing]] — complete draft → edited draft
7. [[TTS_Optimization]] — edited draft → TTS-ready script
8. [[CapCut_Production_Formatting]] — TTS-ready script → production settings
9. [[Multi_Platform_Caption_Generation]] — finished script → platform captions
10. [[Metadata_Generation]] — finished script → title, tags, part label
11. Fill [[Publishing_Checklist]] — every prior output → a completed checklist instance

## Inputs
A story that has already passed [[Story_Ideation]] and [[Story_Validation]] — this workflow starts at drafting, not ideation, since ideation and validation run against a pool of candidates, not one committed story.

## Outputs
A completed [[Publishing_Checklist]] instance, referencing every output produced along the way.

## Error Handling
Per [[Workflow_Error_Handling]]: this workflow declares **abort** as its only failure behavior — a Reddit story pipeline has no meaningful partial output (a story with a hook but no ending isn't publishable). Any abort routes to [[Failure_Analysis]].

## Not Included
[[Story_Ideation]], [[Story_Validation]], and [[Series_Planning]] operate outside this workflow. The first two happen before a story is committed to production; the third operates across many runs of this workflow, not within one. See [[Reddit_Story_Workflow]] for how all of these relate at the system level.

# Horror Story Production

Purpose: The production workflow for the horror content pillar — sequences the full pipeline from validated idea to publish-ready output.
Last Updated: 2026-08-03
Status: Archived 2026-08-13 — see 99_Archive/HorrorProject/README.md
Related Documents: [[99_Archive/HorrorProject/README|HorrorProject (Archived)]], [[Horror_Story_System]]
Required Notes: [[Workflow_Structure]], [[Workflow_Composition]]

---

## Objective
Turn a validated original horror premise into a fully produced, publish-ready output: script, production settings, captions, metadata, and a completed Publishing Checklist.

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
A story that has already passed [[Story_Ideation]], [[Story_Validation]], and [[Originality_Check]] — this workflow starts at drafting, not ideation, for the same reason [[Reddit_Story_Production]] does: ideation and validation run against a pool of candidates, not one committed story.

## Outputs
A completed [[Publishing_Checklist]] instance.

## Error Handling
Per [[Workflow_Error_Handling]]: abort is the only declared failure behavior, same reasoning as [[Reddit_Story_Production]] — a horror story with a hook but no ending isn't publishable.

## Relationship to Reddit_Story_Production
Same steps, same shared capabilities — the two workflows differ only in which system doc and ideation capability feed them. [[Reddit_Story_Workflow]]'s workflow remains defined but is no longer the primary pillar; this one is.

## Not Included
[[Story_Ideation]], [[Story_Validation]], [[Originality_Check]], and [[Series_Planning]] operate outside this workflow, for the same reasons documented in [[Reddit_Story_Production]].

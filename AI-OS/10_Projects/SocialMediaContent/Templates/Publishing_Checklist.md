# Publishing Checklist

Purpose: A fill-in-the-blank verification pass before a Reddit Story production goes live — confirms every capability's Success Criteria were actually met, not re-executed.
Last Updated: 2026-08-03
Status: Active
Template Version: 2
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Reddit_Story_Workflow]], [[Reddit_Story_Production]]
Required Notes: [[Template_Structure]], [[Template_Validation]]

---

## Fields

| Field | Type | Purpose |
|---|---|---|
| Story Title | text | Confirms [[Metadata_Generation]] produced a non-spoiling title |
| Hook Timing Confirmed | checkbox | Confirms [[Hook_Writing]]'s 20-second Success Criterion was met |
| All Parts Have Escalation Beats | checkbox | Confirms [[Retention_Beat_Scripting]]'s cadence criterion |
| Non-Final Parts End on Cliffhanger | checkbox | Confirms [[Cliffhanger_Creation]]'s Success Criteria |
| Final Part Resolves the Hook's Question | checkbox | Confirms [[Ending_Design]]'s Success Criteria |
| Sentence-Purpose Pass Complete | checkbox | Confirms [[Story_Editing]] ran |
| TTS Read-Through Complete | checkbox per part | Confirms [[TTS_Optimization]]'s Validation step actually happened — tracked per part for multi-part stories, not as one story-wide checkbox, since parts are produced and posted sequentially, not all at once |
| Length Within 105–125s Per Part | checkbox | Confirms [[CapCut_Production_Formatting]]'s Success Criteria |
| All Four Platform Captions Present | checkbox | Confirms [[Multi_Platform_Caption_Generation]]'s Success Criteria |
| Part Numbering Consistent | checkbox | Confirms [[Metadata_Generation]]'s part-labeling criterion |
| Series Sequencing Reviewed | checkbox | Confirms [[Series_Planning]] was consulted for this story's placement |

## How It's Used
This checklist doesn't perform any of the checks itself. Per [[Template_Philosophy]], a template has no execution logic — each row exists because a specific capability's Success Criteria needs a final confirmation before publish, not because the checklist re-derives what "correct" means.

## Validation
Per [[Template_Validation]]: an instance is Incomplete if any checkbox is unchecked or the Story Title field is blank. Publishing on an Incomplete instance is a process failure, not a judgment call.

# Command Index

Purpose: A compact routing table from natural-language requests to existing capabilities and workflows. This is the map, not new content — every row orchestrates something that already exists; nothing here duplicates a capability's or workflow's own documentation.
Last Updated: 2026-08-03
Status: Active
Stability: Core
Related Documents: [[00_System/Commands/Quick_Start|Quick Start]], [[03_Capabilities/README|03_Capabilities]], [[05_Workflows/README|05_Workflows]]

---

## How to Read This
Each row: a trigger phrase → what it maps to → what kind of thing that is. What context gets loaded for each is whatever that artifact already declares as its own Required Notes — nothing new is specified here. See [[00_System/Commands/Quick_Start|Quick Start]] for a worked example of the full mechanism.

## Content

| Say... | Maps To | Type |
|---|---|---|
| "Generate a story" / "Generate me a story" | [[Reddit_Story_Production]] | Workflow — full pipeline. Horror archived 2026-08-13, no active story pillar's primary right now |
| "Generate 10 ideas" / "Generate ideas" | [[Story_Ideation]] | Capability — generates original premises |
| "Check this idea's originality" | [[Originality_Check]] | Capability |
| "Should I make this story?" / "Validate this idea" | [[Story_Validation]] | Capability |
| "Generate an outline" | [[Story_Drafting]] | Capability |
| "Generate a hook" | [[Hook_Writing]] | Capability |
| "Write a cliffhanger" | [[Cliffhanger_Creation]] | Capability |
| "Generate an ending" | [[Ending_Design]] | Capability |
| "Edit this story" / "Edit this draft" | [[Story_Editing]] | Capability |
| "Optimize for TTS" | [[TTS_Optimization]] | Capability |
| "Format for CapCut" | [[CapCut_Production_Formatting]] | Capability |
| "Create captions" / "Generate captions" | [[Multi_Platform_Caption_Generation]] | Capability |
| "Generate a title" / "Generate metadata" | [[Metadata_Generation]] | Capability |
| "Plan my next stories" / "Series planning" | [[Series_Planning]] | Capability |
| "Publish checklist" | [[Publishing_Checklist]] | Template |
| "Generate a Veo prompt" | [[Veo_Prompt_Design]] | Capability |
| "Which generation mode should I use?" | [[Generation_Mode_Selection]] | Capability |
| "Am I near my generation limit?" | [[Watermark_Tier_Management]] | Capability |
| "Split this into parts" | [[Story_Drafting]]'s output | Composite — no separate capability |
| "Generate one part" (mid-pipeline) | Steps 2–5 of [[Reddit_Story_Production]] | Composite — no separate capability |
| "Generate thumbnail ideas" | *(gap)* | No capability exists yet |
| "Generate a Reddit-adaptation story" | [[Reddit_Story_Production]] | Workflow — secondary pillar, still functional |

## Analytics

| Say... | Maps To | Type |
|---|---|---|
| "Review my analytics" / "Analyze performance" | [[Review_Process]] | Capability |
| "Daily/Weekly/Monthly review" | [[Review_Cadences]] | Cadence |
| "Why did this fail?" | [[Failure_Analysis]] | Capability |
| "Why did this do so well?" / "Why did this go viral?" | [[Viral_Analysis]] | Capability |
| "Track an experiment" | [[Experiment_Tracking]] | Capability |
| "What's ready to promote?" | [[Promotion_Candidates]] | Output — query, not action |

## System

| Say... | Maps To | Type |
|---|---|---|
| "Promote this knowledge" | [[Knowledge_Promotion_Rules]] → [[Knowledge_Promotion]] | Capability → pipeline |
| "Build a new workflow" | [[Workflow_Structure]] + [[Workflow_Composition]] | Framework (meta) |
| "Build a new capability" | `03_Capabilities/README.md`'s field standard | Framework (meta) |
| "Build a new template" | [[Template_Structure]] | Framework (meta) |

## Gaps
Two items from the original request have no underlying capability. Listed honestly rather than invented on the spot — this index is about usability, not new architecture:
- **Generate Thumbnail Ideas** — no capability exists.
- **Generate a Story Part / Split Story** — works today as a composite of existing pieces, not a single dedicated entry point.

## What's Deliberately Not Here
"Generate a workflow," "generate a template," and "generate a capability" route to the *frameworks* that govern building one, not to a finished thing — building any of those is real architecture work and stays a deliberate, reviewed action, not a one-line command.

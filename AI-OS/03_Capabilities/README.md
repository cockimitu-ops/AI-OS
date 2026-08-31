# 03_Capabilities

Purpose: Reusable, named units of work exposed by the systems in `02_Systems/`.
Last Updated: 2026-08-26
Status: Active — 17 content capability specs plus one parked infrastructure capability (AI-Bridge)
Related Documents: [[Glossary]], [[02_Systems/README|02_Systems]], [[99_Archive/HorrorProject/README|HorrorProject (Archived)]]

---

## Responsibility
A capability is one specific, composable thing AI OS can do, defined once here and referenced by workflows (`05_Workflows/`) and agents (`04_Agents/`) rather than redefined wherever it's used.

## Capability Field Standard
Every capability follows the template established in Sprint 010: Purpose/Last Updated/Status/Related Documents (standard header), Required/Optional/Related Notes + Used By (per [[Dependency_Rules]]), then Success Criteria, Inputs, Outputs, Validation, Analytics Reference, Knowledge Dependencies.

## Capabilities

### Shared production pipeline — [[Reddit_Story_Workflow]] (currently the only active consumer)
Horror_Story_System was the primary consumer of this pipeline until archived 2026-08-13 — see [[99_Archive/HorrorProject/README|HorrorProject]]. Every capability below is genre-agnostic and available to whatever new content topic replaces it.
Pipeline order (see [[Reddit_Story_Production]]):
- [[Story_Ideation]] — generates original premises. Reusable for any original-content system; not currently in active use.
- [[Story_Validation]] — premise → go/no-go, includes [[Originality_Check]]. Not currently in active use.
- [[Originality_Check]] — IP/reuse safeguard for original content. Not currently in active use.
- [[Story_Drafting]] — validated idea → structured outline
- [[Hook_Writing]] — outline's opening → hook
- [[Retention_Beat_Scripting]] — outline's body → paced beats
- [[Cliffhanger_Creation]] — non-final part → closing lines
- [[Ending_Design]] — final part → resolution
- [[Story_Editing]] — complete draft → edited draft
- [[TTS_Optimization]] — edited draft → TTS-ready script
- [[CapCut_Production_Formatting]] — TTS-ready script → production settings
- [[Multi_Platform_Caption_Generation]] — finished script → platform captions
- [[Metadata_Generation]] — finished script → title, tags, part label
- [[Series_Planning]] — validated pool → production order (outside the per-story workflow)

### From [[AI_Video_Production]] (active)
- [[Veo_Prompt_Design]]
- [[Generation_Mode_Selection]]
- [[Watermark_Tier_Management]]

### `Kind: Service` — [[03_Capabilities/AI-Bridge/README|AI-Bridge]] (parked)
Everything else in this folder is `Kind: Spec` — a Markdown description of a unit of work. This one is runnable code. The distinction and why it stays in this folder: [[ADR-0007_Code_Capabilities]].
Not a content capability and not a Markdown spec: a real code capability (Node) letting Claude and Gemini call each other, plus an HTTP surface for n8n. **Parked since 2026-08-26** pending the same unresolved Claude-Pro-auth ToS question that gates TaskRunner's escalation tier — see its own README. Listed here because it lives in this folder and was missing from this index entirely until 2026-08-26.

## Status
17 content capability specs, all preserved through the Horror archival — none were deleted, since none were horror-specific in mechanism. 3 (Story_Ideation, Story_Validation, Originality_Check) currently have no active consumer, kept because they're genuinely reusable for whatever original-content system gets built next. Their Success Criteria still carry Reddit-specific numeric thresholds, unreconciled — see `Suggestions.md`. No capabilities exist yet for Research, Analytics, Automation, or Architecture systems.

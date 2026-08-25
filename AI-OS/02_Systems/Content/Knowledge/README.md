# Knowledge

Purpose: Permanent, reusable domain knowledge about storytelling and writing craft — the foundational material capabilities and system processes draw on, independent of platform or AI model.
Last Updated: 2026-08-03
Status: Active — Sprint 006
Related Documents: [[02_Systems/Content/README|Content]], [[Reddit_Story_Workflow]]

---

## Responsibility
Ten atomic knowledge notes, cross-referenced rather than duplicated. Timeless craft knowledge only — no platform specifics, no implementation details, no prompts, no templates. Those live in the system/capability layers that consume this knowledge.

## Contents
- [[Storytelling_Fundamentals]] — the root note: what a story is, why audiences engage
- [[Narrative_Structure]] — how change is organized across a telling
- [[Hook_Principles]] — what earns attention before trust is established
- [[Suspense_And_Curiosity]] — the two distinct mechanisms of sustained tension
- [[Pacing]] — the rate of information release
- [[Emotional_Engagement]] — how genuine investment is created, not just attention
- [[Reader_Retention]] — why engagement continues past every point it could stop
- [[Writing_Style]] — voice, word choice, sentence construction
- [[Clarity]] — being understood as intended, on first pass
- [[Editing_Principles]] — how a draft becomes a final version

## Field Mapping
This sprint's brief requested per-note fields (`Purpose`, `Core Principles`, `Key Concepts`, `Related Knowledge`, `Dependencies`, `Used By`). To avoid a second, competing metadata schema, these map onto the vault's existing standard:
- `Purpose`, `Core Principles`, `Key Concepts` — used as-is
- `Related Knowledge` → `Related Documents` (existing header field)
- `Dependencies` → `Required Notes` (from [[Dependency_Rules]])
- `Used By` → new field, added to [[Dependency_Rules]] as a formal (small) extension this sprint

## Why This Lives Here
Placed inside `02_Systems/Content/` rather than a new top-level location, since [[Reddit_Story_Workflow]] is currently the only concrete consumer — building a cross-system location now would mean organizing for reuse that doesn't exist yet. Nothing about the physical location restricts a future system from linking to these notes directly; promoting them to a shared location later, if a second system needs them, is a cheap, mechanical move. See `Suggestions.md` for the full reasoning.

## Relationship to Capabilities
As of Sprint 011, the full 13-capability Reddit Story pipeline exists. Most draw directly on this Knowledge Core: [[Hook_Writing]], [[Retention_Beat_Scripting]], [[Cliffhanger_Creation]], [[Ending_Design]], and [[Story_Editing]] each declare specific Knowledge Dependencies; [[Story_Ideation]], [[Story_Validation]], and [[Story_Drafting]] depend on [[Storytelling_Fundamentals]] and [[Narrative_Structure]] specifically. [[Multi_Platform_Caption_Generation]], [[CapCut_Production_Formatting]], [[TTS_Optimization]], and [[Metadata_Generation]] correctly declare none or only a single note ([[Clarity]] or [[Hook_Principles]]) — they're platform/production mechanics, not general storytelling craft. The 3 AI Video Production capabilities declare none at all — that pillar doesn't draw on this Knowledge Core.

## Status
Sprint 006 complete.

# Changelog

Purpose: Version history of AI OS.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[Roadmap]], [[Development_Workflow]]

---

## [0.1.0-alpha] — 2026-08-03
### Added
- Repository folder structure (`00_System` through `99_Archive`)
- Core `00_System` documents: `Home`, `Dashboard`, `Roadmap`, `Changelog`, `Glossary`
- Core `01_Architecture` documents: `Vision`, `Principles`, `Architecture`, `Repository_Structure`, `Naming_Convention`, `Development_Workflow`
- ADR framework (`01_Architecture/ADR/`) — no ADRs recorded yet
- `02_Systems` subfolder scaffolding: `Content`, `Research`, `Analytics`, `Automation`, `AI`, `Architecture`
- README for every folder in the repository
- Root `README.md` and `Suggestions.md`

### Notes
This is the foundation sprint. No systems, capabilities, agents, or workflows contain content yet.

## [0.2.0-alpha] — 2026-08-03
### Added
- `ADR-0001_Naming_Disambiguation` (Accepted) — resolves the `02_Systems`/top-level naming overlap and the `AI` acronym exception
- `ADR-0002_Git_Workflow_Conventions` (Accepted) — branch naming and commit message format
- `02_Systems/Content/Reddit_Story_Workflow.md`
- `02_Systems/Content/AI_Video_Production.md`

### Changed
- `02_Systems/Content/README.md` expanded from stub to active system definition
- `Suggestions.md` updated: naming, acronym, and ADR-numbering items resolved via ADR-0001; Git workflow item resolved via ADR-0002; templates and tagging convention marked deferred
- `Naming_Convention.md`, `Development_Workflow.md` updated to reference the new ADRs
- `Dashboard.md`, `Roadmap.md` updated to reflect Sprint 001 completion and Sprint 002 progress

### Notes
Sprint 002 is in progress. The Content system is populated based on already-established production workflows; Research, Analytics, Automation, AI, and Architecture systems remain queued pending concrete scope.

## [0.3.0-alpha] — 2026-08-03
### Added
- Seven capability definitions in `03_Capabilities/`, extracted from the Content system:
  - From Reddit Story Workflow: `Hook_Writing`, `Retention_Beat_Scripting`, `Multi_Platform_Caption_Generation`, `CapCut_Production_Formatting`
  - From AI Video Production: `Veo_Prompt_Design`, `Generation_Mode_Selection`, `Watermark_Tier_Management`

### Changed
- `03_Capabilities/README.md` expanded from stub to a real capability index
- `Reddit_Story_Workflow.md` and `AI_Video_Production.md` candidate-capability sections replaced with links to the extracted notes

### Notes
Sprint 003 is complete for the Content system only. No capabilities exist yet for Research, Analytics, Automation, AI, or Architecture, since those systems still aren't populated. Sprint 004 (Agents) needs a concrete decision on what agent is actually being formalized before it can be more than a placeholder.

## [0.4.0-alpha] — 2026-08-03
### Added
- Context Engine in `07_Context/`: `Context_Philosophy.md`, `Context_Resolution.md`, `Dependency_Rules.md`, `Loading_Strategy.md`, `Context_Budget.md`, `Knowledge_Promotion.md`, `Future_Integration.md`

### Changed
- `07_Context/README.md` expanded to index the Context Engine alongside its original standing-context scope
- `01_Architecture/Architecture.md` and `01_Architecture/Repository_Structure.md`: `07_Context/` row updated to note the Context Engine
- `00_System/Roadmap.md`: Context Engine inserted as Sprint 004; Agents and Workflows renumbered to Sprint 005 and 006
- `Suggestions.md`: logged the `07_Templates/08_Reference/09_Knowledge` naming discrepancy and the Conventional-Commits/ADR-0002 conflict

### Notes
No folders renamed or moved. No ADR required — this sprint added content within the already-defined `07_Context/` structure, per `Development_Workflow.md`.

## [0.5.0-alpha] — 2026-08-03
### Added
- Execution Engine in `01_Architecture/Execution/`: `Execution_Philosophy.md`, `Execution_Lifecycle.md`, `Task_Specification.md`, `Quality_Assurance.md`, `Learning_Loop.md`, `Runtime_State.md`, `Future_Runtime_Integration.md`
- `ADR-0003_Execution_Engine_Placement` (Accepted) — governs where future cross-cutting engine subsystems live

### Changed
- `01_Architecture/README.md`, `01_Architecture/Repository_Structure.md`, `01_Architecture/Architecture.md`, `01_Architecture/ADR/README.md` updated to reflect the new subfolder and ADR
- `07_Context/Future_Integration.md` cross-linked to the new `Future_Runtime_Integration.md`
- `00_System/Roadmap.md`: Execution Engine inserted as Sprint 005; Agents and Workflows renumbered to Sprint 006 and 007

### Notes
No folders renamed or moved, no accepted ADR modified — ADR-0003 is a new record, not a change to ADR-0001/0002. Placement of the Execution Engine (`01_Architecture/Execution/`, a sibling to `ADR/`) was a genuine judgment call, since no existing folder matched the way `07_Context/` matched the Context Engine — formalized via ADR-0003 rather than left implicit.

## [0.6.0-alpha] — 2026-08-03
### Added
- Knowledge Core in `02_Systems/Content/Knowledge/`: `Storytelling_Fundamentals.md`, `Narrative_Structure.md`, `Hook_Principles.md`, `Suspense_And_Curiosity.md`, `Pacing.md`, `Emotional_Engagement.md`, `Reader_Retention.md`, `Writing_Style.md`, `Clarity.md`, `Editing_Principles.md`
- `Used By` field added to `07_Context/Dependency_Rules.md`

### Changed
- `02_Systems/Content/README.md` and `Reddit_Story_Workflow.md` cross-linked to the new Knowledge Core
- `01_Architecture/Repository_Structure.md` tree and table updated

### Notes
No ADR required — new subfolder within an already-existing top-level folder. Placement reasoning (why `02_Systems/Content/Knowledge/` and not a shared cross-system location) logged in `Suggestions.md`. Capability retrofit remains open, now with something concrete to point to.

## [0.7.0-alpha] — 2026-08-03
### Added
- Analytics methodology in `02_Systems/Analytics/`: `Analytics_Philosophy.md`, `Metrics_Framework.md`, `Success_Criteria.md`, `Failure_Analysis.md`, `Experiment_Tracking.md`, `Learning_Extraction.md`, `Knowledge_Promotion_Rules.md`, `Review_Process.md`, `Monthly_Review_Standard.md`, `Continuous_Improvement_Cycle.md`

### Changed
- `02_Systems/Analytics/README.md` expanded from stub to full index
- `09_Analytics/README.md` cross-linked to the new methodology (stays empty — output, not process)
- `02_Systems/README.md` fixed — was stale since Sprint 002, still said "no system content yet"
- `01_Architecture/Repository_Structure.md` tree and table updated

### Notes
Placement resolved against [[ADR-0001_Naming_Disambiguation]] rather than the brief's literal pre-read pointer — see `Suggestions.md`. No new ADR needed. Analytics has zero declared consumers so far (`Used By` intentionally blank across all 10 notes) — accurate, since nothing has been reviewed through this framework yet.

## [0.8.0-alpha] — 2026-08-03
### Added
- Workflow Framework in `05_Workflows/`: `Workflow_Philosophy.md`, `Workflow_Structure.md`, `Workflow_Lifecycle.md`, `Workflow_Composition.md`, `Workflow_Inputs_And_Outputs.md`, `Workflow_Validation.md`, `Workflow_Error_Handling.md`, `Workflow_Review.md`, `Workflow_Versioning.md`, `Workflow_Integration.md`

### Changed
- `05_Workflows/README.md` expanded from stub to full index
- `07_Context/Future_Integration.md` and `01_Architecture/Execution/Future_Runtime_Integration.md`: Workflows sections updated from "not yet built" to point at the new framework
- `01_Architecture/Repository_Structure.md` tree and table updated

### Notes
No ADR needed — `05_Workflows/` is a standalone top-level category with no process/output split to reconcile. No production workflow created, per this sprint's explicit scope. `Used By` blank across all 10 notes — accurate, nothing instantiates a workflow yet.

## [0.9.0-alpha] — 2026-08-03
### Added
- Template Framework in `01_Architecture/Templates/`: `Template_Philosophy.md`, `Template_Structure.md`, `Template_Metadata.md`, `Template_Variables.md`, `Template_Validation.md`, `Template_Versioning.md`, `Template_Reuse.md`, `Template_Integration.md`, `Template_Lifecycle.md`, `Template_Quality_Standards.md`
- `ADR-0004_Template_Framework_Placement` (Accepted) — generalizes ADR-0003 to a third cross-cutting category

### Changed
- `06_Assets/README.md` — disambiguated "templates" (actual files) from the new Template Framework (the standard governing them)
- `01_Architecture/README.md`, `Architecture.md`, `Repository_Structure.md`, `ADR/README.md` updated to reflect the new subfolder and ADR

### Notes
No production template created, per this sprint's explicit scope. `Used By` blank across all 10 notes — nothing formally consumes this framework yet.

## [0.10.0-alpha] — 2026-08-03
### Changed
- All 7 capabilities in `03_Capabilities/` retrofitted to the full field standard (Required/Optional/Related Notes, Used By, Success Criteria, Inputs, Outputs, Validation, Analytics Reference, Knowledge Dependencies)
- Restated craft theory removed from `Hook_Writing.md`, `Retention_Beat_Scripting.md`, `CapCut_Production_Formatting.md` — replaced with links to the Knowledge Core and system docs
- `03_Capabilities/README.md` rewritten with the field standard and its source mapping
- `07_Context/Dependency_Rules.md` — documented the new `Knowledge Dependencies` field
- `02_Systems/Content/Knowledge/README.md` — corrected now-resolved claim about the retrofit being open

### Notes
No new capabilities. No ADR required — retrofit is content within already-existing files, not a structural change. Commit message specified directly by this sprint's brief rather than derived: `03_Capabilities: retrofit capability library`.

## [0.11.0-alpha] — 2026-08-03
### Added
- 9 new capabilities in `03_Capabilities/`: `Story_Ideation.md`, `Story_Validation.md`, `Story_Drafting.md`, `Cliffhanger_Creation.md`, `Ending_Design.md`, `Story_Editing.md`, `TTS_Optimization.md`, `Metadata_Generation.md`, `Series_Planning.md`
- First production template: `02_Systems/Content/Templates/Publishing_Checklist.md`
- First production workflow: `05_Workflows/Reddit_Story_Production.md`

### Changed
- `Hook_Writing.md`, `Retention_Beat_Scripting.md`, `CapCut_Production_Formatting.md`, `Multi_Platform_Caption_Generation.md` — `Used By` updated to include [[Reddit_Story_Production]]
- `Reddit_Story_Workflow.md` — Capabilities section expanded to all 13, new Production System section added
- `03_Capabilities/README.md`, `02_Systems/Content/README.md`, `05_Workflows/README.md`, `01_Architecture/Templates/README.md`, `02_Systems/Content/Knowledge/README.md` — all updated to reflect the complete pipeline
- `01_Architecture/Repository_Structure.md` — full tree and table rewrite

### Notes
No new capabilities were created for items already covered (Hook Writing, Caption Generation) — referenced instead, per this sprint's explicit instruction. No ADR required. Commit message specified directly by the brief.

## [0.12.0-alpha] — 2026-08-03
### Added
- `02_Systems/Analytics/`: `Daily_Review.md`, `Weekly_Review.md`, `Viral_Analysis.md`
- `09_Analytics/`: `Hook_Database.md`, `Ending_Database.md`, `Retention_Database.md`, `Promotion_Candidates.md`

### Changed
- `Monthly_Review_Standard.md`, `Failure_Analysis.md`, `Review_Process.md` cross-linked to new siblings
- `Hook_Writing.md`, `Retention_Beat_Scripting.md`, `Cliffhanger_Creation.md`, `Ending_Design.md` — Analytics Reference sections now point to their actual output database
- `02_Systems/Analytics/README.md`, `09_Analytics/README.md` rewritten
- `01_Architecture/Repository_Structure.md` tree and table updated

### Notes
No new capabilities, no ADR required — this sprint populated both sides of a split ADR-0001 already defined. `09_Analytics/` structures are schemas only; zero real entries, since no story has been produced and published yet. Commit message specified directly by the brief.

## [0.13.0-alpha] — 2026-08-03
### Added
- `00_System/Commands/Command_Index.md` and `Quick_Start.md` — the command layer
- `02_Systems/Content/Story_Tracker.md`
- `00_System/Repository_Audit.md`
- `02_Systems/Content/Templates/README.md` — was missing since Sprint 011, caught by this sprint's own audit

### Changed
- `Home.md` — fully rewritten; was stuck at "Sprint 001, 0.1.0-alpha" since the first sprint
- `Dashboard.md` — redesigned as an operating-system home screen (Quick Actions, Current Work, Recent Stories, Analytics Waiting, Experiments, Knowledge Promotions, Commands, Version, Repository Health)
- `02_Systems/README.md` — subfolder list converted from plain text to wikilinks
- `01_Architecture/Repository_Structure.md` — tree and table updated

### Deferred
- Universe Support (Entities/Locations/Organizations/Artifacts/Events/Rules) and their templates — no grounding in anything built so far; flagged in `Suggestions.md` rather than built or dropped silently.
- "Generate Thumbnail Ideas" — real gap, no capability exists; logged in the Command Index rather than invented under a usability-sprint framing.

### Notes
No ADR required. Real repository audit run against the actual file tree (see `Repository_Audit.md`): 0 dead links, 0 orphans, 1 missing index (fixed), 7 navigation gaps (fixed).

## [0.14.0-alpha] — 2026-08-03
### Added
- `00_System/Design_Review.md` — full critical review against the confirmed actual business (original horror content brand, not Reddit adaptation)

### Findings, not yet implemented
5 critical, 5 high-value, 3 useful, 2 optional, 2 future recommendations — see `Design_Review.md` for the ranked list. Headline: `Reddit_Story_Workflow.md` and `Story_Ideation.md` are built for sourcing real material, not generating original fiction; Universe Support's Sprint 013 deferral is reversed given this confirmation; the Databases won't survive 500 stories as currently structured.

### Notes
No architecture changed — this was explicitly a review sprint, not a build sprint, per the brief's own instruction.

## [0.15.0-alpha] — 2026-08-03
### Added
- Horror Knowledge layer in `02_Systems/Content/Knowledge/Horror/`: 10 notes (`Horror_Hook_Techniques`, `Horror_Pacing_Model`, `Escalation_Techniques`, `Curiosity_Psychology`, `Open_Loops`, `Fear_Of_The_Unknown`, `Dread_And_Anticipation`, `Body_Horror`, `Existential_Horror`, `First_Person_Horror_Technique`), synthesized from uploaded research
- `02_Systems/Content/Horror_Story_System.md` — new primary Content pillar
- `03_Capabilities/Originality_Check.md` — new capability
- `05_Workflows/Horror_Story_Production.md` — parallel production workflow

### Changed
- `03_Capabilities/Story_Ideation.md` — fully rewritten for generation, not sourcing
- `03_Capabilities/Story_Validation.md` — now includes Originality Check
- `02_Systems/Content/Reddit_Story_Workflow.md` — status changed to secondary, not deleted
- 11 shared capabilities — `Used By` updated to include the Horror pillar
- `02_Systems/Content/README.md`, `03_Capabilities/README.md`, `00_System/Commands/Command_Index.md`, `00_System/Dashboard.md` — all updated for the new primary pillar

### Explicitly not resolved (see Suggestions.md)
Numeric threshold reconciliation between Reddit-specific and horror-evidence-based timing for a multi-part structure; horror subgenre-specific knowledge; Universe Support; AI Video Production pillar status.

## [0.16.0-alpha] — 2026-08-03
### Added
- `02_Systems/Content/Stories/` — new subfolder, the vault's first home for actual produced content
- `02_Systems/Content/Stories/The_Doorbell_Camera.md` — first complete production run: ideation, validation, originality check, outline, full 3-part script, editing/TTS/production notes, captions, metadata, filled Publishing Checklist

### Changed
- `Story_Tracker.md` — first real entry
- `00_System/Dashboard.md` — Current Work / Recent Stories now show real content

### Findings from actually running the system
- No content library existed until now — fixed
- The multi-part vs. single-episode timing reconciliation worked in practice (run once per story, once per part) — documented as one worked example, not yet generalized back into the system spec
- The CapCut background-visual convention doesn't fit horror tonally — flagged, not resolved
- The Publishing Checklist correctly reports Incomplete (2 of 11 items need something outside this system) — validated the checklist design works as intended

## [0.16.1-alpha] — 2026-08-03
### Fixed
- `CapCut_Production_Formatting.md` — background visual rotation was hardcoded to Reddit_Story_Workflow's specific games inside a shared capability; genericized to defer to each system's own convention
### Added
- `Horror_Story_System.md` — horror-specific background rotation: Phasmophobia / Poppy Playtime / Fears to Fathom, not AI-generated (cost, and arguably worse for the retention mechanic anyway)
### Changed
- `The_Doorbell_Camera.md` — production notes updated from open question to resolved decision

## [0.16.2-alpha] — 2026-08-03
### Added
- `Review_Process.md` — "First Checkpoint for New Content": 24–48h then ~1 week, distinct from the standing Daily/Weekly/Monthly cadences
- `Horror_Story_System.md` — "What to Measure": retention, watch time, completion rate, shares, comments, saves, followers, returning viewers, in priority order

### Notes
Both were real gaps surfaced by a practical question, not planned work — nothing previously said when to first check a brand-new story or which specific numbers matter for this pillar.

## [0.16.3-alpha] — 2026-08-03
### Added
- `Horror_Pacing_Model.md` — spoken-pace principle (brisker-than-conversational helps retention, up to the clarity ceiling), from the original research but not previously captured
- `CapCut_Production_Formatting.md` — TTS voice speed guidance: 1.1–1.2x starting point, per-segment variation as the better option, tied to rhythm-as-signal

## [0.17.0-alpha] — 2026-08-04
### Added
- `10_Projects/MoneyMaking/` — first real project: exploring a low-time, €50-start income approach, separate from the content pipeline
- `10_Projects/MoneyMaking/Perplexity_Research_Prompt.md` — research prompt v1

### Changed
- `10_Projects/README.md` — no longer empty
- `00_System/Dashboard.md` — new Projects section; version display corrected (had drifted behind 3 undisplayed patch bumps)

### Notes
No ADR needed — subfolder within an already-existing top-level folder, same precedent as `Content/Knowledge/`, `Content/Templates/`, `Content/Stories/`.

## [0.17.1-alpha] — 2026-08-04
### Fixed
- `Publishing_Checklist.md` — TTS Read-Through field bumped to Template Version 2, now tracked per-part
- `The_Doorbell_Camera.md` — Part 1's TTS read-through confirmed; Parts 2–3 still open

### Changed
- `Roadmap.md` — rewritten for accuracy; Universe Support marked approved-and-queued (distinct from the general backlog); Agents and AI Video Production status reframed as decisions with concrete options, not open-ended blockers

## [0.17.2-alpha] — 2026-08-04
### Decided
- Agents: manual, chat-triggered — confirmed as the approach, not just the default

### Added
- `10_Projects/MoneyMaking/README.md` — first Decision Log entry: Perplexity Pro purchased (~$20/mo recurring), Education Pro student discount ($10/mo) flagged as unclaimed savings

## [0.17.3-alpha] — 2026-08-04
### Changed
- `MoneyMaking/README.md` — Goal and Constraints revised: time constraint dropped, scope opened to a legitimate startup, not just side income
- `Perplexity_Research_Prompt.md` — v2 written (in German), v1 kept as version history

### Added
- `MoneyMaking/German_Legal_Basics.md` — durable German tax/legal findings preserved from v1, independent of which specific idea eventually gets chosen

### Notes
v1's candidate ideas (video editing services, UGC ads) rejected as too small given the revised goal, not as bad research — the time constraint that shaped v1's search is exactly what changed.

## [0.17.4-alpha] — 2026-08-04
### Added
- `MoneyMaking/Candidate_Options.md` — 5 ranked business options with Claude's own synthesis
- `MoneyMaking/Funding_Opportunities.md` — German/Saxony grant programs, especially InnoStartBonus

### Changed
- `MoneyMaking/README.md` — Candidate Ideas populated (was empty since project creation); new Immediate Next Actions section

### Notes
InnoStartBonus (up to €12,600 over 12 months, non-repayable, no degree required) flagged as the highest-priority action — more important than picking a specific business idea yet, per the research's own framing.

## [0.17.5-alpha] — 2026-08-04
### Added
- `The_Doorbell_Camera.md` — Video Review section with a Gemini-facing prompt (Claude has no native video capability), results not yet back

### Notes
Flagged as a candidate for a future formal capability if it proves useful beyond this one story — not built as a capability yet.

## [0.17.6-alpha] — 2026-08-04
### Changed
- `The_Doorbell_Camera.md` — full Gemini video review results and 4 concrete pre-publish fixes
- `Story_Tracker.md` — Lessons column populated with real findings
- `CapCut_Production_Formatting.md` — scene-matching refinement (beyond genre-matching), new caption-collision and TTS-variation-actually-applied Validation checks
- `Cliffhanger_Creation.md` — new Production Note on CTA timing
- `Ending_Design.md` — cross-referenced the same CTA-timing concern, untested on a final part specifically

### Notes
Confirmed the Sprint 016 background-visual fix was correct; found it wasn't actually applied in production. Two genuinely new findings incorporated directly as craft/production judgment, not staged through the formal Knowledge_Promotion pipeline — consistent with how the original background-genre fix was handled.

## [0.18.0-alpha] — 2026-08-05
### Added
- `01_Architecture/ADR/ADR-0005_Project_Knowledge_Separation.md` — the structural decision behind this sprint
- `10_Projects/SocialMediaContent/` — Horror/Reddit/AI Video execution, moved from `02_Systems/Content/` and `05_Workflows/`
- `10_Projects/ContentAgency/README.md`, `10_Projects/TemplateSales/README.md`, `10_Projects/FundingApplications/README.md` — three new active projects (Candidate Options 1, 3, 4)

### Changed
- `02_Systems/Content/README.md` — narrowed to knowledge/methodology only
- `05_Workflows/README.md` — narrowed to framework only, instances moved out
- `10_Projects/MoneyMaking/README.md` — rewritten as the research/umbrella record now that sub-projects exist
- `10_Projects/README.md`, `02_Systems/README.md`, `Architecture.md`, `Repository_Structure.md` — updated for the new structure
- `Home.md` — was stale at `0.13.0-alpha` since Sprint 013, fully updated
- `00_System/README.md` — added missing references to `Commands/`, `Repository_Audit.md`, `Design_Review.md`

### Fixed (found via post-move audit)
- Two broken bare wikilinks (`ContentAgency`, `TemplateSales`) needed folder-qualified paths
- `SocialMediaContent/README.md`'s `Stories/`/`Templates/` references were plain text, not links

### Notes
Bare wikilinks (the established convention) resolve by filename, not path — most cross-references into the moved files survived automatically. Full dead-link/orphan/missing-index audit run before and after, not assumed clean.

## [0.20.0-alpha] — 2026-08-06
### Added
- `10_Projects/QuickTurnaroundGigs/` — new project: `Research_And_Briefing_Gigs.md`, `Real_Time_Problem_Arbitrage.md`

### Changed
- `10_Projects/TemplateSales/README.md` — enriched with digital-tools/Claude-Artifacts angle and a Platforms section
- `10_Projects/README.md`, `Repository_Structure.md`, `Dashboard.md` — updated for 6 active projects

### Notes
Structure only, per explicit scope for this sprint — no pitches written, no gigs claimed, no platform listings created. Naming-convention inconsistency in project folder names (no underscores, deviating from the stated rule) logged in Suggestions.md, not resolved.

## [0.20.1-alpha] — 2026-08-06
### Changed
- `QuickTurnaroundGigs/Research_And_Briefing_Gigs.md` — real Fiverr gig drafted: title, category, tags, 3-tier pricing grounded in current live Fiverr data ($43–100 category norm), description, FAQ, buyer requirements
- Pricing set under the established range to win first reviews as a new seller; faster turnaround (24–48h vs. the 2–3 day norm) framed as the real differentiator, not price alone

## [0.20.2-alpha] — 2026-08-06
### Added
- `QuickTurnaroundGigs/Fulfillment_Workflow.md` — the operational backend for all 3 Research & Briefing packages: per-tier Perplexity and Claude prompts, take-home time budgets, and a QA step specifically checking that cited claims are real (protects the gig's own "no fabricated stats" promise)

### Notes
Time budgets are estimates, not measured yet — flagged in the doc itself for correction once real orders run through it. Premium's effective hourly rate is the tightest of the three, worth watching first.

## [0.21.0-alpha] — 2026-08-07
### Added
- `10_Projects/Personal/` — Reading List, Supplement Stack, Substance History (starting inventory for the future Get Clean project, not built yet)

## [0.21.1-alpha] — 2026-08-07
### Changed
- Full audit run — vault clean, no dead links, no missing indexes
- Roadmap: added missing Sprint 021 entry (Personal project)
- Roadmap and Changelog synced to Notion (previously skipped as token-heavy) — Changelog condensed to one line per version for Notion, full granular detail stays in the local Changelog.md

## [0.22.0-alpha] — 2026-08-07
### Removed
- `Future_Runtime_Integration.md`, `Template_Integration.md`, `Workflow_Integration.md` — merged into new `01_Architecture/Future_Integration.md`
- `Daily_Review.md`, `Weekly_Review.md`, `Monthly_Review_Standard.md` — merged into new `02_Systems/Analytics/Review_Cadences.md`

### Changed
- `Watermark_Tier_Management.md`, `Generation_Mode_Selection.md`, `Veo_Prompt_Design.md` — trimmed boilerplate
- `Reddit_Story_Workflow.md` — condensed to a stub, only pillar-specific content remains
- 7 remaining Analytics files — compressed in place, same filenames, denser content
- All referencing files (11 total across the two merges) updated, verified via full audit

### Notes
Token efficiency pass, per direct request. 161 → 156 files. Full audit clean before and after.

## [0.23.0-alpha] — 2026-08-07
### Changed
- `QuickTurnaroundGigs/Research_And_Briefing_Gigs.md` — refocused on startup competitor analysis, new $30/$80/$180 tiers replacing the old generic $25/$45/$75
- `QuickTurnaroundGigs/Fulfillment_Workflow.md` — rebuilt as a 6-step research process (competitor ID, profiling, comparison/SWOT, gaps, investor insights, report structure), with the collaboration loop made explicit: buyer answers in, per-order prompts out, raw research in, finished report out

## [0.23.1-alpha] — 2026-08-08
### Changed
- `Fulfillment_Workflow.md` — Step 2 updated with a real, tested finding from the Omni Shield test run: batching 3 competitor profiles in one Perplexity message truncates the last one's Weaknesses/Recent Moves; 2 at a time is the safe ceiling

## [0.23.2-alpha] — 2026-08-08
### Changed
- `Fulfillment_Workflow.md` — noted Perplexity sometimes appends unprompted strategic-implications synthesis after a Step 2 batch; useful but not to be relied on, Step 4 still runs explicitly

## [0.23.3-alpha] — 2026-08-08
### Changed
- `Fulfillment_Workflow.md` — noted Step 3's SWOT can absorb part of Step 4's job when client context is already present, per Omni Shield test

## [0.23.4-alpha] — 2026-08-08
### Changed
- `Fulfillment_Workflow.md` — Omni Shield test run closed out at 3/8 competitors, deliberately, once the loop was proven end-to-end. Honest flag added: round-trip overhead between Perplexity and Claude makes the time budget table optimistic until tested against a real paid order.

## [0.24.0-alpha] — 2026-08-08
### Added
- `10_Projects/CyberSecurityLearning/` — self-directed head start ahead of September studies (TryHackMe Pre Security, NetworkChuck, Professor Messer, milestone plan)

### Fixed
- `Repository_Structure.md` — Personal project was missing from the tree entirely since its creation; added alongside the new project
## [0.24.1-alpha] - 2026-08-08
Added Core/Dynamic stability tagging to Context_Budget.md; tagged 6 starter files.

## [0.25.0-alpha] - 2026-08-08
### Added
- 07_Context/Knowledge_Core.md - hard-capped (~10,000 char) self-curating record about Felix, Hermes-style bounded core. Eviction rule: stable/reproducible beats recent/one-off.

## [0.26.0-alpha] - 2026-08-08
### Added
- 10_Projects/GetClean/ - active project, cannabis cessation specifically, nicotine/psilocybin explicitly out of scope for now
### Changed
- Knowledge_Core.md updated with the now-concrete scope (was a vague deferred note)

## [0.26.1-alpha] - 2026-08-08
Added Kali Linux setup guidance to CyberSecurityLearning: browser-based AttackBox for now, VirtualBox+official VM image once past fundamentals, tool-by-tool learning approach.

## [0.27.0-alpha] - 2026-08-11
### Added
- 04_Agents/ populated for the first time since Sprint 001: 4 scoped role definitions (Vault_Architect, Content_Producer, Research_Analyst, Business_Development), each with Scope/Allowed/Escalation fields
### Notes
Execution model unchanged - manual, chat-triggered only, per the existing Decided note. This formalizes context/capability scope per role, not automation.

## [0.28.0-alpha] - 2026-08-13
### Added
- 02_Systems/Automation/README.md - first real content since Sprint 001: documents the AI OS MCP server (separate deliverable, ai-os-mcp.zip). Read-only, stays inside the standing no-automation decision.
### Notes
MCP server itself: written without network access to compile/test. Honestly flagged as unverified in both the server's own README and this vault note.

## [0.29.0-alpha] - 2026-08-13
### Fixed
- Status drift: 02_Systems/README.md, Repository_Structure.md, and Dashboard.md all still described Agents and/or Automation as empty/not-started after both were built
- Roadmap.md was four sprints stale (stopped at 021, Changelog was at 0.28.0) - added Sprints 022-026
- Development_Workflow.md: sprint-completion step omitted Roadmap.md from the update checklist, which is the root cause of the drift above. All three status docs now required, every sprint.
### Changed
- Knowledge_Core.md: MCP server noted, flagged unverified
### Notes
Deliberately NOT compressed: Suggestions.md and Changelog.md (~16% of vault by size) appear in no Required Notes, so cost nothing at load time. Shrinking them would look productive without changing anything real.

## [0.29.1-alpha] - 2026-08-13
FundingApplications closed by choice, not oversight. Roadmap updated: Actual Next Steps now leads with the Fiverr gig and ContentAgency prospecting.

## [0.30.0-alpha] - 2026-08-13
### Added
- 10_Projects/MoneyMaking/Income_Portfolio.md - the multi-stream strategy. Core finding from 2026 market research: median template seller with no distribution earns close to nothing; distribution beats product quality. Key synergy identified - short-form video is the #1 discovery channel for Notion templates, and that production capability already exists in SocialMediaContent.
### Changed
- TemplateSales: priority set to ONE product first (the AI OS pattern), not three product lines
- Roadmap: Actual Next Steps sequenced; futureSAX/Time-Sensitive section correctly removed (an earlier edit reported success but silently failed to match - caught and fixed)

## [0.31.0-alpha] - 2026-08-13
### Added
- 10_Projects/LocalArbitrage/ - physical goods arbitrage. README, Valuation_Method, Transaction_Log, Legal_Reality.
### Key design decisions vs. the original plan
- AI explicitly does NOT estimate resale prices - sold comps do. A hallucinated price estimate on a real purchase decision is the highest-risk failure mode in this whole model.
- Legal_Reality added (absent from the source plan): buy-to-resell is gewerblich, Gewerbeanmeldung required at start, DAC7 triggers at 30 sales/EUR2000, and the EUR565/month Familienversicherung threshold is the binding constraint.
- Differenzbesteuerung (25a UStG) verified as NOT available to Kleinunternehmer - noted so it isn't planned around.
- Honest economics stated: ~EUR15-25/hour, not passive.

## [0.32.0-alpha] - 2026-08-13
Documented Gemini access: no MCP support in regular chat app (use shared Notion links, same as Perplexity); Antigravity (replaced Gemini CLI June 2026) supports the existing ai-os-mcp server directly via ~/.gemini/config/mcp_config.json, zero new code needed.

## [0.32.1-alpha] - 2026-08-13
AI_Video_Production activated - first real concept (Glass Crush Loop), first Veo prompt written and sent for generation. Series strategy documented: format consistency over novelty, per current ASMR research.

## [0.32.2-alpha] - 2026-08-13
### Fixed
Generation_Mode_Selection.md and AI_Video_Production.md documented a Fast/Quality binary; Veo 3.1 actually has three tiers (Lite/Fast/Quality). Corrected, with explicit sequencing: test new prompts on Fast, only regenerate confirmed keepers on Quality.

## [0.32.3-alpha] - 2026-08-13
### Fixed
Corrected a false assumption in AI_Video_Production: 60 seconds is not required per video. That's TikTok's Creator Rewards payout threshold, not a performance requirement - short loops actually outperform for this genre. One 8-second Veo generation, looped, is a complete video.
### Notes
Flagged that a Gemini text response presented as a video critique was actually a generic AI-video-failure diagnostic - Gemini stated upfront it could not view the actual file. The loop-mechanism flaw it caught is real and independently valid (a prompt-design issue, not dependent on watching footage), but the rest should not be treated as evidence about the specific render.

## [0.33.0-alpha] - 2026-08-13
### Archived
- Horror_Story_System.md, Horror_Story_Production.md, Stories/ (The_Doorbell_Camera.md) moved to 99_Archive/HorrorProject/
### Changed (references fixed across the vault, verified by audit)
- 14 capability files (Used By / Required Notes updated, 3 horror-specific ones marked reusable-but-unused)
- 03_Capabilities/README.md, 04_Agents/Content_Producer.md (rescoped, genre-agnostic)
- SocialMediaContent/README.md, Reddit_Story_Workflow.md, Story_Tracker.md (all rewritten, not patched)
- Command_Index.md, Dashboard.md, Knowledge_Core.md, 02_Systems/Content/README.md, Repository_Structure.md, 10_Projects/README.md, 99_Archive/README.md
### Deliberately NOT changed
- ADR-0005 - historical record of a past decision, never rewritten per the vault's own rule, even though it names Horror_Story_System as an example
- Changelog/Suggestions/Roadmap history - append-only, accurate as of when written
### Notes
Full audit run before and after - dead links, orphans, missing indexes all clean. One real stale reference (10_Projects/README.md) caught by the audit and fixed, not missed.

## [0.34.0-alpha] - 2026-08-26
Retroactive entry. Everything below was built and committed between 2026-08-25 and 2026-08-26 and was never logged here — the Changelog stopped at 0.33.0 (2026-08-13) while the repository kept moving. Reconstructed from git history and the live server, not from memory.

### Added
- `02_Systems/Automation/TaskRunner/` — the first real automation in the vault. Headless Open Interpreter worker (`aios_runner.py`), CLI dispatcher, Telegram bridge, daily rclone backup. Three systemd services (`aios-worker`, `aios-telegram`, `aios-backup.timer`) running continuously on the server. Moved in from loose scripts at the repo root.
- `System_Prompt.md` — the worker's prompt, versioned as Markdown rather than hardcoded in Python. Gives it the vault's folder map so it stops rediscovering the layout per task.
- `03_Capabilities/AI-Bridge/` — Claude×Gemini bridge (Node), plus an HTTP surface and an n8n service for it.
- `10_Projects/TemplateSales/` — three complete products (Micro-SaaS Moat Blueprint $29, Pricing Teardown $29, Retention Engineering $39), a $45 bundle listing, a shared prompt-pack PDF generator, and a staged launch order.
- `AI-OSmcp/` and `server-stack/` brought into the repository as siblings of the vault.

### Changed
- Free-model rotation expanded to five attempts across two providers after both the primary and fallback models failed live in the same test run.

### Parked
- Claude escalation tier in TaskRunner: built, verified working, then disabled the same day (`CLAUDE_ESCALATION_ENABLED = False`). Routing an unattended, Telegram-triggerable service through Pro-subscription auth is an unresolved ToS question. AI-Bridge is parked for the identical reason.

## [0.35.0-alpha] - 2026-08-26
### Fixed — live code
- `aios_runner.py`: an unhandled exception anywhere in the per-task body escaped the polling loop. With systemd's `Restart=always` and the task still sitting in `tasks/inbox/`, that was an unbounded crash-loop on a single bad file. Per-task work now runs under a guard that quarantines the task and writes an error log.
- `aios_runner.py`: result logs were written with a plain `open("w")`, but `dispatch_task.py` and `telegram_bridge.py` poll for that file's *existence* — both could read an empty or half-written log and report it as the answer. Logs are now written to a temp name and renamed atomically.
- `dispatch_task.py`, `telegram_bridge.py`: task files were written non-atomically into a directory the worker globs every 2 seconds, so a half-written file could be picked up and a truncated instruction executed. Both now write `.part` and rename.
- `aios_runner.py`: an empty task file was deleted with no log written, leaving any waiting caller to block for its full 180-second timeout on an instant, known failure.
- `cloud_backup.py`: local archives were pruned on a 7-day schedule regardless of whether the upload succeeded. A silently broken remote plus scheduled pruning means no backup in either place after a week. Pruning now requires a successful upload.
- `cloud_backup.py`: failures were silent — journal-only, on a job that runs unattended at 03:00. `send_telegram_notification.py` existed for exactly this and had never been wired to anything. It is now.
- `send_telegram_notification.py`: depended on `python-dotenv`, which is not installed for the interpreter systemd runs `cloud_backup.py` with. The notifier would have failed precisely when called. Rewritten stdlib-only.
- `cloud_backup.py`: added `server-stack/jellyfin/cache` to the excludes — regenerable, and unbounded once real media is attached.
- `AI-OSmcp/docker-compose.yml`: `tty: true` on a stdio MCP server. A pseudo-TTY corrupts newline-delimited JSON-RPC. Removed, and the documented Claude Desktop command corrected to pass `-T`.
- `AI-Bridge/server.mjs`: listened on `0.0.0.0` while its own auth is optional (no `BRIDGE_TOKEN` = open). Started outside Docker, that exposed unauthenticated Claude access to the whole LAN. Defaults to `127.0.0.1` now; the container sets `HOST=0.0.0.0` explicitly, where compose already binds it to loopback.
- `AI-Bridge`: `.env.example` was referenced by the README and `.env.docker.example` by the compose file. Neither existed. One real `.env.example` added, both references fixed.

### Verified
- MCP server: `npm install` clean, `npm run build` compiles with zero errors (Node 22). Closes the "written blind, never compiled" caveat carried since Sprint 025.
- TaskRunner: worker restarted on the patched code and a real `dispatch_task.py` round trip returned correctly.
- `rclone gdrive:` remote confirmed reachable; `aios-backup.service`'s stale `failed` state (from a run that predated the rclone config) cleared.

### Fixed — status drift
- Root `README.md` said "Version 0.1.0-alpha, Sprint 001" — twenty-eight sprints stale. Root cause: it was never in `Development_Workflow.md`'s sprint-completion checklist. It is now, which is the second time that checklist has been the actual fix.
- `Home.md` at 0.20.0-alpha, `Dashboard.md` at 0.33.0-alpha.
- `Dashboard.md` contradicted itself: "Current Work: The_Doorbell_Camera — Ready to Publish" directly above "archived, never published."
- `FundingApplications/README.md` header said "Closed — not pursued, by choice"; its own Status section said the futureSAX call was the highest-priority action across the whole effort.
- `TemplateSales/README.md` said "nothing packaged yet" while three finished products sat in its subfolders, and still named a first product ("the AI OS pattern") that was never what got built.
- `_infra/LAUNCH-ORDER.md` referenced `pricing/` and `retention/` folders that do not exist. All 14 file references now resolve.
- `Knowledge_Core.md` — the always-loaded standing context — carried four stale facts: no automation, unverified MCP server, nothing packaged in TemplateSales, and funding as the top unclaimed action.
- `02_Systems/Automation/README.md` claimed the whole folder stayed inside the no-automation boundary, in a file whose first section is a live unattended executor.
- `03_Capabilities/README.md` never listed AI-Bridge, which lives in that folder.
- `Repository_Structure.md` — the authoritative map — was missing TaskRunner, AI-Bridge, all three TemplateSales products, `AI-OSmcp/`, and `server-stack/`.

### Notes
Wikilink integrity was checked across all 216 Markdown files: zero dead links. The nine apparent hits are the same illustrative placeholders `Repository_Audit.md` identified in Sprint 013. Link hygiene is genuinely solid; *status* hygiene is where this vault repeatedly fails, and every drift item above was a file contradicting either itself or a sibling, not a broken reference.

## [0.36.0-alpha] - 2026-08-26
Second half of Sprint 029: the decisions the audit surfaced, plus the two build items that came out of them.

### Added
- `01_Architecture/ADR/ADR-0006_Project_Folder_Naming.md` — closes the Sprint 018 backlog item (open eleven sprints). Amends the rule rather than renaming ten project folders: `PascalCase` for projects under `10_Projects/`, `kebab-case` for product folders inside a project, leading underscore for tooling. Renaming was rejected on evidence — the vault's link integrity is currently perfect and renaming would put every wikilink into `10_Projects/` at risk to satisfy a rule nobody had been confused by.
- `02_Systems/Automation/TaskRunner/test_taskrunner.py` — 20 regression tests, stdlib `unittest`, no dependencies, 0.06s. Covers every reliability fix from 0.35.0. Mutation-checked: each fix was reverted in a throwaway copy and all four reverts were caught by the intended test. The suite redirects `AIOS_WORKSPACE` to a temp directory and stubs the open-interpreter import, so it never touches the live queue and never calls a model.
- `10_Projects/TemplateSales/_infra/packs/moat.py` — product 1 shipped a prompt-pack PDF with no config behind it, so unlike the other two it could not be regenerated. Reconstructed by decoding the shipped PDF's ASCII85+Flate content streams; the rebuilt PDF's rendered text is byte-identical to the shipped file across all 108 lines.
- `_infra/requirements.txt` — `reportlab` is installed nowhere on this machine, so `pack_builder.py` could not run at all.

### Decided
- **Claude via the Pro subscription: both paths stay parked.** TaskRunner's escalation tier and the whole AI-Bridge capability. The free Groq/Gemini chain is verified working and costs nothing; the ToS question isn't worth resolving for capacity that isn't currently needed. Both are a flag away from returning. Moved from "genuinely blocked" to Off the Table — it was a question being carried, not a blocker.
- **Universe Support: dropped**, after eleven sprints queued-and-approved. Its justification was written for the horror brand archived in Sprint 027.
- **AI Video Production status and the new story topic: deferred by decision**, until the three built TemplateSales products are published. Both stay untouched rather than half-pursued.
- **`.env` stays inside the backup archive.** A restore needs it. Recorded as a conscious tradeoff rather than left as an unexamined default.
- **Jellyfin's media path stays a placeholder** — no media attached yet.

### Notes
Two things worth carrying forward. First, the mutation check on the test suite mattered: a test that passes against the broken code is worse than no test, and that is only knowable by breaking the code on purpose. Second, `moat.py`'s reconstruction was verified by diffing rendered output rather than by reading it over — the config *looking* right and the config *reproducing the product* are different claims, and only the second one is worth stating.

## [0.37.0-alpha] - 2026-08-27
Vault usability pass, plus two Telegram worker fixes.

### Added
- `02_Systems/Automation/vault_status.py` — scans every `Status:` header and regenerates a summary block in [[Dashboard]] between markers. Every file already declared a status; nothing collected it, so "what is actually live here?" could only be answered by reading the whole vault. 165 files scanned. Surfaces two previously invisible groups: 5 **Dormant** (scaffolded Sprint 001, never used) and 12 **Active but empty**. `--check` mode exits 1 if the block is stale.
- `ADR-0007_Code_Capabilities` — AI-Bridge is a running Node service sitting among seventeen Markdown specs, and nothing distinguished them; that omission is why `03_Capabilities/README.md` failed to list it for four sprints. Adds `Kind: Spec` / `Kind: Service`.

### Changed
- The five never-used folders (`02_Systems/Research`, `02_Systems/AI`, `02_Systems/Architecture`, `08_Research`, `06_Assets`) now read `Status: Dormant` instead of `Scaffolded`. "Scaffolded" implied work in progress; twenty-eight sprints of no content means dormant, and saying so makes the Dashboard able to count it.
- `format_interpreter_output()` returns the worker's prose instead of its full shell transcript — Telegram was showing scratch work (a `find`, then a truncated wall of paths) instead of an answer. Falls back to the transcript only when there is no prose, so silent failures stay debuggable.
- `System_Prompt.md` — worker now told it is talking to a person in a chat; that the folder map it already has is authoritative (it was running `find` to rediscover data it had been handed); that judgement questions want a recommendation, not an inventory; and that only `python`/`shell` exist as code languages, never `python3`, which fails and wastes the turn.
- `telegram_bridge.py` — HTML parse mode, so `**bold**` and code fences render instead of appearing literally.

### Deliberately NOT changed
- **AI-Bridge was not moved** out of `03_Capabilities/`. Four path-based wikilinks and five `Changelog.md` references point at its current path, and the Changelog is append-only — moving would make those permanently wrong rather than merely stale. It is parked, so the move buys nothing operationally. Same reasoning ADR-0006 used against renaming project folders.
- **The seventeen `Kind: Spec` capabilities were not retrofitted.** Spec is the default and those files are unambiguous.
- **The folder numbering was not changed.** The worker's own suggestion (merge `03`–`07` into `00_System`, rename `10_Projects` → `02_Projects`) was rejected: it fights ADR-0001's system/output distinction, and renaming a top-level folder referenced vault-wide is exactly the link risk ADR-0006 declined twelve hours earlier.

### Verified
- Wikilink integrity: 230 Markdown files, zero dead links.
- Stale prose paths from the Sprint 018 reorg and Sprint 027 archival (`02_Systems/Content/Horror_Story_System.md`, `05_Workflows/Reddit_Story_Production.md`, and eight others) were checked individually: **every remaining occurrence is inside `Changelog.md`, `Suggestions.md`, or an ADR** — append-only records that are correct as history and must not be rewritten. Nothing to fix.
- TaskRunner regression suite 20 → 23 tests, all passing. The suite caught the formatter change, which is what it is for; the test was rewritten to assert the new contract rather than deleted.

## [0.38.0-alpha] - 2026-08-27
### Fixed
- `02_Systems/Automation/TaskRunner/README.md`: a stray backslash inside a wikilink (`[[04_Agents/README\|04_Agents]]`) — a real dead link introduced in the Sprint 029 agent-selection commit and caught only now by re-running the link audit. First dead link found in this vault's history that wasn't an intentional placeholder.

### Added
- `02_Systems/Automation/TaskRunner/External_Access_Plan.md` — planning only, nothing built. Lays out what it would take to extend TaskRunner to Gmail, YouTube, and a phone, and why that's a genuinely different risk class from the existing vault-write allowlist: every mistake `vault_write.py` can make is git-recoverable, and a sent email is not. Stages Gmail/YouTube read-only first, draft-not-send before any autonomous send, and a structural (not prompted) confirmation gate for anything irreversible. Explicitly does not scope "phone access" further — six different things could be meant by it, and the document lists them as a menu rather than guessing.

### Synced to Notion
First sync since 2026-08-24/25. 11 pages updated: Dashboard, Roadmap, `04_Agents` + its 4 role pages (now reflecting they're executable), the AI OS root and `00_System` version strings, plus ADR-0006 and ADR-0007 created as new pages under `01_Architecture`. Scoped deliberately — not a full 237-file mirror. TemplateSales' product marketing assets (PDFs, SVGs, long-form listing copy) were left out: each product has its own separate, manually-run Notion-template-per-product workflow already, and mirroring those into the architecture-tree side of Notion would conflate two different things this vault keeps separate on purpose.

## [0.39.0-alpha] - 2026-08-27
Money-focused work, per direct request: publish groundwork and the unfinished reference sample.

### Added
- `10_Projects/QuickTurnaroundGigs/Reference_Sample_Report_Omni_Shield.md` — the Sprint 023 Omni Shield test validated Steps 1-3 and 6 but stopped at 3 of 8 competitors deliberately, rather than complete a fake deliverable. Finished as a full Standard-tier sample: 5 real, currently-sourced competitors (Firewalla, Bitdefender BOX, Gryphon Guardian, IronWiFi, Cisco Meraki Go), a comparison table, SWOT, and five recommendations. One genuinely useful finding: CUJO AI still surfaces in searches and comparison articles as a live competitor; it discontinued its hardware in 2021. Caught and flagged rather than silently included - exactly the stale-data trap the workflow's own "found via" citation requirement exists to catch.
- Standalone Notion page for the Micro-SaaS Moat Blueprint template, created outside the private AI OS mirror on purpose - a public duplicate-able template shouldn't carry breadcrumbs back to operational notes. Two manual steps remain: "Allow duplicate as template" (a Notion UI toggle, not reachable via the API) and the Gumroad listing.

### Changed
- Fiverr gig confirmed live as of today. Status updated in QuickTurnaroundGigs/README.md and Roadmap's Actual Next Steps.

### Process note
First task where the TaskRunner worker did real, useful autonomous work in the same session as manual work, rather than everything routing through direct edits: dispatched `--agent research` to record the Fiverr-live milestone via `vault_write.py`. Standing practice going forward - durable facts and decisions get logged by the worker, not written by hand, wherever the worker's actual capabilities (allowlisted note creation, no overwrite) cover the case.

## [0.40.0-alpha] - 2026-08-27
### Milestone
- **Micro-SaaS Moat Blueprint is live** - the first TemplateSales product actually published, first real point where revenue could start. Notion template duplicate-enabled, Gumroad listing published with all four purchasable files (including `notion-template-link.md`, gated correctly after the earlier fix). Status updated across `_infra/AI-CONTEXT.md` (the authoritative table), `TemplateSales/README.md`, `Dashboard.md`, `Roadmap.md`.
- QuickTurnaroundGigs' Fiverr gig status corrected in `Research_And_Briefing_Gigs.md` - its own Status header still said "not yet posted to Fiverr" after the gig had already gone live, caught by the same drift pattern this vault keeps failing at and re-running the audit keeps catching.

### Process
Second milestone logged by the TaskRunner worker rather than by hand -
`10_Projects/TemplateSales/Micro_SaaS_Moat_Blueprint_Live_2026_08_27.md`,
dispatched `--agent business`, verified before trusting it. The existing-file
status-table edits (AI-CONTEXT.md, README.md, Dashboard.md, Roadmap.md)
stayed manual, same boundary as before: vault_write.py's allowlist covers new
notes, not overwriting hand-maintained files, and that boundary is doing its
job rather than being a gap.

## [0.41.0-alpha] - 2026-08-27
### Added
- `10_Projects/TemplateSales/_infra/pull_pricing_teardown_launch_kit.sh` / `.ps1` - same launch-kit pattern as Moat Blueprint, staged for Week 3-4 per `_infra/LAUNCH-ORDER.md`. Deliberately not published yet - both scripts carry that warning inline, and no Notion page was created for it (unlike Moat Blueprint), matching the vault's own one-product-at-a-time sequencing.
- `10_Projects/TemplateSales/Micro-SaaS-Moat-Blueprint/reddit_post1_ready_today.md` - just today's action (r/SaaS Post 1 + reply templates), not all three scheduled posts. Bundling day-3 and day-7 content into "today's" file would invite posting all three at once, exactly what `_infra/LAUNCH-ORDER.md` warns against.

## [0.42.0-alpha] - 2026-08-27
### Fixed
- `vault_write.py`: `Purpose:` extraction took the body's literal first line, no matter what it was. A worker-written note started its body with `## Context`, and that heading landed in `Purpose:` verbatim — `08_Research/Reddit_SaaS_Launch_Constraints_And_Warmup_Requirements.md` shipped with `Purpose: ## Context`. `_first_sentence_for_purpose()` now skips heading and list-marker lines to find the first real prose line. Fixed the one already-written note directly; two regression tests added.

### Blocked, correctly
- Micro-SaaS Moat Blueprint's Reddit launch: Felix has no comment history in r/SaaS. Confirmed via research this is a real constraint, not overcaution — r/SaaS actively auto-removes zero-participation posters, and caps self-promotion (comments included) to once per 60 days as of April 2026. `reddit_post1_ready_today.md` renamed to `reddit_post1_warmup_then_post.md` and rewritten with a warm-up plan; status updated in TemplateSales/README.md and Dashboard.md. Logged as a standing research note (`08_Research/`) since it applies to all three products' Reddit launches, not just this one.

## [0.43.0-alpha] - 2026-08-30
### Fixed
- **Root cause of intermittent Telegram bot failures: `eno1` (the server's LAN ethernet) had never been configured for DHCPv4** in `/etc/netplan/00-installer-config.yaml` — only `wlo1` (WiFi) had `dhcp4: true`. The physical link was fine (IPv6 via SLAAC worked the whole time, which is why this wasn't a clean outage), but any IPv4-only connection attempt — including some of python-telegram-bot's requests to api.telegram.org — had nowhere to route and failed instantly. Added `dhcp4: true` to eno1; it now holds a real address (192.168.178.69) and default route via the FRITZ!Box (192.168.178.1). Old config backed up to `00-installer-config.yaml.bak-20260830` on the server (not vault-tracked - lives outside the repo).
- Misdiagnosed twice before this: first suspected `eno1` had "lost" an IPv4 lease (wrong - it never had one), then suspected the WiFi network "Lazu" was the primary uplink and its absence was the fault (wrong - Felix clarified it's a phone-based WiFi bridge, expected to be intermittent, not the server's real connection). LAN was always meant to be primary; it just had a one-line config gap since whenever this box was provisioned.

## [0.44.0-alpha] - 2026-08-30
### Added
- **FreeLLMAPI** (freellmapi.co) installed as a new systemd service (`freellmapi.service`, `/opt/freellmapi`, port 3001) — a self-hosted, OpenAI-compatible router in front of ~34 free-tier LLM providers with its own internal failover. Per Felix: the hand-rolled Groq/Gemini chain wasn't enough under real use; this is the interim measure until there's budget for a metered GLM tier (GLM-4.5/4.7 are already in freellmapi's free catalog in the meantime).
- `aios_runner.py`'s `MODEL_CHAIN` restructured from 2-tuples to dicts (model/delay/api_base/api_key) to carry the new endpoint fields without fragile positional unpacking. freellmapi (`openai/auto`) is now the primary tier; the original 5-entry direct Groq/Gemini chain is kept as fallback, not deleted — verified live that it still fires correctly when freellmapi has no providers configured. 60 → 64 tests.

### Fixed
- **Root cause of intermittent Telegram bot failures, corrected diagnosis:** `eno1` (LAN ethernet) never had `dhcp4: true` in netplan — only WiFi did. Not a cable fault, not a lost lease, not the router resetting (all suspected and ruled out in sequence). One line added; `eno1` now holds a real IPv4 address and default route.

### Process failures worth recording plainly
- **Two secrets got printed into this chat transcript** while wiring up freellmapi's `.env` entry: first two API key values from an overly-broad grep, then the entire `.env` file (Gemini, Groq, Telegram bot token, and the Claude Code OAuth token) via a Read call that should have been narrower. Felix was told to rotate all four. Recorded here because it's the kind of mistake worth designing around going forward, not just apologizing for once - future secret handling in this workflow should default to name-only confirmation (`grep -o '^[A-Za-z0-9_]*='`), the pattern that was already established and used correctly earlier in this same session, before it was skipped here.
- Misdiagnosed the network problem twice before finding the real cause (see Fixed above) - first assumed a lost IPv4 lease on eno1, then assumed a WiFi network was the server's primary uplink when it was actually a phone-based bridge Felix built for a different purpose. Both corrected on new information rather than pursued further on a wrong premise.

## [0.45.0-alpha] - 2026-08-30
### Removed
- **FreeLLMAPI, completely** — the self-hosted router installed hours earlier. Per Felix: didn't want a second service to run and keep patched for this. Systemd unit stopped/disabled/removed, `/opt/freellmapi` deleted, `.env` entries removed, the dedicated test class deleted, README section removed. `MODEL_CHAIN`'s dict-based entry structure (added for freellmapi's api_base/api_key fields) was kept — it's a genuine readability improvement independent of freellmapi, and the two providers added below needed the same shape anyway.

### Added
- **Cerebras and OpenRouter** as direct backup tiers in `MODEL_CHAIN` — litellm-native providers, no custom endpoint, gated on their own env vars so shipping this changes nothing until `CEREBRAS_API_KEY`/`OPENROUTER_API_KEY` are actually added to `.env`. Both model IDs verified against live sources before being written into code, not assumed: Cerebras' `gpt-oss-120b` against Cerebras' own docs (an aggregator site's "8k context" claim was checked and found wrong — it's 65k on the free tier), and OpenRouter's free-model pick against its live `/api/v1/models` endpoint after the first candidate turned out to already be rotated out. 60 → 65 tests.

### Process note
Two more secrets got printed into this session's transcript while removing the freellmapi `.env` entries — a `Read` call that wasn't necessary, since the file's content was already in context from earlier the same session. Same mistake as the previous entry, repeated once more before being caught. Felix does not need to take any *additional* rotation action beyond what was already recommended — the same four credentials are affected, not new ones.

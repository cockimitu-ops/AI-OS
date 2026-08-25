# Suggestions

Purpose: A place for the Lead Repository Engineer to record observations and proposed improvements without altering the architecture. Nothing here is implemented until the Chief Systems Architect approves it, ideally via an ADR.

Last Updated: 2026-08-03
Status: Partially resolved (see below)

---

## Resolved via ADR-0001
~~1. Naming overlap between 02_Systems subfolders and top-level folders~~ — Resolved. Confirmed as system/output distinction, documented across affected READMEs. See [[ADR-0001_Naming_Disambiguation]].

~~5. ADR numbering~~ — Resolved. Zero-padded four-digit sequential IDs confirmed. See [[ADR-0001_Naming_Disambiguation]] and `Naming_Convention.md`.

~~6. "AI" as a folder name~~ — Resolved. Accepted as an acronym exception to Pascal_Case. See [[ADR-0001_Naming_Disambiguation]].

## Resolved via ADR-0002
~~4. Git workflow specifics~~ — Resolved. Branch and commit conventions defined. See [[ADR-0002_Git_Workflow_Conventions]].

## Deferred (not urgent, no decision needed yet)
**2. Template notes** — Still worth doing once a templating plugin (e.g., Templater) is actually in use. Deferred until then; no vault content depends on it yet.

**3. Tagging / taxonomy convention** — Still worth doing once enough tagged content exists that an uncontrolled vocabulary becomes a real risk. Deferred; revisit once `03_Capabilities/` or `08_Research/` starts filling in.

---

## New: Sprint 002 scope decision
Given creative control on Sprint 002, I populated `02_Systems/Content/` first rather than all six systems at once, since it's the only system with enough established, concrete detail (Reddit/TikTok story workflow, AI video/Veo 3.1 production) to document accurately rather than invent. `Research/`, `Analytics/`, `Automation/`, `AI/`, and `Architecture/` remain scaffolded — populating them with real definitions would mean guessing at scope that hasn't been established. Flagging this as a deliberate, not accidental, gap.

---

## New: Sprint 004 folder-naming discrepancy
The Sprint 004 brief listed `07_Templates/`, `08_Reference/`, `09_Knowledge/` as existing folders. They don't — the real folders are `07_Context/`, `08_Research/`, `09_Analytics/`. Most likely cause: my prior sync brief compressed the folder list with "…" instead of spelling out positions 07–09, leaving room for the architect to fill the gap with a plausible-but-wrong guess. Resolved by building the Context Engine inside the existing `07_Context/` folder rather than introducing new ones — no rename, no duplication.

**Process suggestion:** future sync briefs should paste `01_Architecture/Repository_Structure.md` verbatim rather than a compressed listing, to prevent this class of gap recurring.

## New: Commit-format conflict with ADR-0002
The Sprint 004 brief asked for a Conventional Commit message (`feat:`, `docs:`, etc.). [[ADR-0002_Git_Workflow_Conventions]] explicitly considered and rejected that format in favor of `<scope>: <what changed>`. Per the brief's own instruction to respect existing ADRs, the commit message below uses the ratified format instead. Flagging in case future briefs should be told this ADR exists, rather than re-suggesting a format it already rejected.

---

## New: Sprint 005 — sprint renumbering (again)
Same pattern as Sprint 004: the brief called itself "Sprint 005 — Execution Engine," which collided with the Roadmap's existing Sprint 005 (Agents). Resolved the same way — renumbered Agents to 006, Workflows to 007. Not flagging this as a problem, just noting the sprint numbers in the Roadmap are now two steps ahead of the brief author's numbering twice in a row. If a third cross-cutting engine gets proposed before Agents, worth the architect pre-reserving a range (e.g., 004–006 for engines) rather than inserting one at a time.

## New: Execution Engine placement — resolved via ADR-0003
No existing folder matched "model-independent execution lifecycle" the way `07_Context/` matched the Context Engine. Placed it at `01_Architecture/Execution/`, as a sibling to `ADR/`, and formalized the reasoning as [[ADR-0003_Execution_Engine_Placement]] rather than leaving it as an implicit one-off choice — this should make the next cross-cutting engine's placement a non-question.

---

## New: Sprint 006 — Knowledge Core placement
Placed at `02_Systems/Content/Knowledge/`, not a new top-level folder or a cross-system location. Reddit Story Workflow is the only concrete consumer right now, and the notes themselves stay platform-agnostic regardless of folder location — a future system needing this knowledge can link to it directly; promoting it to a shared location later (if that happens) is a cheap, mechanical move, not a redesign. No ADR needed: this is a new subfolder within an already-existing top-level folder (`02_Systems/Content/`), which `Development_Workflow.md` treats as content-within-structure, not a structural change.

## New: `Used By` field added to Dependency_Rules
The brief's requested per-note fields mostly already existed under different names (`Related Knowledge` → `Related Documents`, `Dependencies` → `Required Notes`). One was genuinely new — `Used By`, the reverse-reference field — added to [[Dependency_Rules]] rather than left as a one-off convention local to the Knowledge Core. First real usage: all 10 new knowledge notes declare `Reddit_Story_Workflow` as their consumer.

## Still open: capability retrofit
The 7 existing `03_Capabilities/` notes still don't formally declare dependencies (flagged since Sprint 004, restated in Sprint 005). With the Knowledge Core now in place, this retrofit has something concrete to point to — e.g., `Hook_Writing.md` should add `Required Notes: [[Hook_Principles]], [[Suspense_And_Curiosity]]`. Not done this sprint, since the brief scoped this sprint to knowledge only.

---

## New: Sprint 007 — Analytics placement (09_Analytics vs 02_Systems/Analytics)
The brief's pre-read list pointed at `09_Analytics/`, but per [[ADR-0001_Naming_Disambiguation]] that folder is output (real metrics/reports about real completed projects), not methodology. Everything requested this sprint — Philosophy, Metrics Framework, Success Criteria, etc. — is methodology, and the Mission text confirms it ("NOT to analyze existing content... define HOW"). Built in `02_Systems/Analytics/` instead. `09_Analytics/` was updated with a one-line pointer to the new methodology but stays empty, correctly, since no real project has been reviewed yet.

## New: also fixed — stale 02_Systems/README.md
While touching this area, found `02_Systems/README.md` still said "no system content yet" and treated the naming distinction as unresolved, both stale since Sprint 002 and Sprint 002 (ADR-0001) respectively. Updated to reflect current state. Worth a standing note: system-index files (`02_Systems/README.md`, `01_Architecture/README.md`, etc.) don't get automatically revisited when their subfolders change — each sprint should check the relevant parent index, not just the folder being worked in.

---

## New: Sprint 008 — clean sprint, no placement ambiguity
`05_Workflows/` is a standalone top-level category (never split between a `02_Systems/` process side and an output side the way Analytics was), so no ADR-0001-style reconciliation was needed. Framework built directly where the brief pointed.

## New: nice continuity moment, not a problem
Both existing Future Integration notes (`07_Context/Future_Integration.md`, `01_Architecture/Execution/Future_Runtime_Integration.md`) had already predicted this sprint's central rule — one Execution Lifecycle run per capability per step, not once for the whole workflow. `Workflow_Composition.md` implements that prediction rather than re-deriving it, and both source notes were updated with a one-line pointer back. Flagging only because it's a good signal the earlier engine sprints were designed with enough foresight that this one didn't need to guess.

## Still open: capability retrofit
Now blocking two things, not one — Sprint 004's original ask (declare `Required Notes` on the 7 capabilities) and, as of this sprint, real workflow definitions can't be built without it either, since `Workflow_Structure` requires each step to reference an existing, well-defined capability. Still not done — still out of scope for a framework-only sprint, but worth surfacing before Sprint 009 if that's Agents or a first real workflow.

---

## New: Sprint 009 — Template Framework placement (ADR-0004)
No existing folder fit, same situation as Execution in Sprint 005 — but this time the concern (document format/structure) didn't match ADR-0003's literal scope (runtime/retrieval), so I wrote a new ADR rather than silently stretching the old one. ADR-0004 generalizes the pattern instead of replacing ADR-0003: three categories now share the same placement rule (`ADR/`, `Execution/`, `Templates/`), and a fourth clearly-analogous case in the future can point to ADR-0004 without needing its own.

## New: also fixed — 06_Assets/README.md's stale "templates" mention
Sprint 001's `06_Assets/README.md` listed "templates" as an example non-Markdown asset type, written long before this framework existed. Now genuinely ambiguous (does "templates" mean this Sprint 009 framework, or an actual `.docx` file?), so disambiguated: `06_Assets/` still covers actual template *files*; `01_Architecture/Templates/` covers the *framework* governing them. Same category of fix as `02_Systems/README.md` in Sprint 007 — a standing pattern now: check for pre-existing stray mentions of new terminology before introducing it formally.

---

## Resolved: capability retrofit (open since Sprint 004)
All 7 capabilities now carry the full field set: Required/Optional/Related Notes, Used By, Success Criteria, Inputs, Outputs, Validation, Analytics Reference, Knowledge Dependencies. Restated craft theory removed throughout — e.g., `Hook_Writing.md` no longer restates what makes a hook work (that duplicated `Hook_Principles.md` almost sentence-for-sentence); it now links and keeps only the platform-specific threshold (20 seconds) that's actually specific to this capability. Same pattern applied across all 7.

## New: Sprint renumbering (third time)
This retrofit sprint had no number of its own in the brief, but following the established `Sprint N → 0.N.0-alpha` mapping, it's Sprint 010 (version 0.10.0-alpha). Agents — previously slated as Sprint 010 — is renumbered to Sprint 011. This is the third time a prerequisite sprint has been inserted ahead of Agents (after Context Engine and Execution Engine). Worth noting as a pattern: Agents appears to be the natural "everything else needs to exist first" sprint, which may be exactly why it keeps getting deferred rather than a sign of drift.

## New: Required Notes vs. Knowledge Dependencies overlap — by design, documented
`Knowledge Dependencies` necessarily repeats entries already in `Required Notes` for the 2 capabilities that have any (Hook Writing, Retention Beat Scripting) — Required Notes has to stay complete since [[Context_Resolution]]'s retrieval algorithm reads only that field. Knowledge Dependencies is a labeled subset for human scanning, not a competing source of truth. Documented once in `Dependency_Rules.md` rather than re-explained per capability.

---

## New: Sprint 011 — Reddit Story System completed end-to-end
Two of the twelve requested items (Hook Writing, Caption Generation) already existed as capabilities — referenced into the pipeline rather than duplicated, per this sprint's own instruction. Publishing Checklist became a Template Framework instance rather than a capability, since a checklist has no execution logic to describe (would have just restated the fields as prose — exactly the duplication being avoided). Net: 9 new capabilities (13 total for this pillar), 1 production template (the framework's first real use), 1 production workflow (also a first).

## New: capability boundary decisions worth surfacing
Three splits were judgment calls, not obvious from the brief's flat list, and worth flagging in case they don't match intent:
- **Cliffhanger Creation vs. Retention Beat Scripting** — split so Retention Beat Scripting owns a part's body/pacing and Cliffhanger Creation owns only its final lines. Mirrors the existing Hook Writing / Retention Beat Scripting split (opening vs. body).
- **TTS Optimization vs. CapCut Production Formatting** — split so TTS Optimization touches only script text (punctuation, pronunciation) and CapCut Production Formatting keeps the production package (timing, overlay, SFX) it already owned.
- **Metadata Generation vs. Multi-Platform Caption Generation** — split so Metadata owns title/tags/part-labeling and Captions keeps the per-platform description body it already owned.

## New: Story Ideation, Story Validation, and Series Planning operate outside the workflow
[[Reddit_Story_Production]] starts at Story Drafting, not Ideation — the first two run against a candidate pool, not a committed story, and Series Planning runs across many workflow runs, not within one. Documented in three places (the workflow's own "Not Included" section, the system doc, and the capability README) rather than left implicit, since it's the kind of boundary an incomplete workflow definition could otherwise miss.

---

## New: Sprint 012 — Review Workflow, split across the ADR-0001 boundary for the first time
Three of the nine requested items already existed (Monthly Review, Failure Analysis) or were process, not data (Daily/Weekly Review, Viral Analysis) — those extended `02_Systems/Analytics/`. The other four (the three Databases, Promotion Candidates) are genuinely output — literal, evolving records — and went into `09_Analytics/`, which has correctly sat empty since Sprint 001. This is the first sprint that legitimately touches both sides of the process/output split in one delivery, rather than one or the other.

## New: 09_Analytics/ now has structure but zero data — flagged as deliberate
Built table schemas and cross-references, not fabricated entries. No Reddit Story has actually been produced and published yet (the pipeline from Sprint 011 hasn't had a real run), so there's genuinely nothing to record. Same pattern as the Workflow and Template frameworks: structure before instance, instance before data.

## New: Viral Analysis closes a real gap in Knowledge Promotion Rules' own caution
[[Knowledge_Promotion_Rules]] already required "reproducible in principle, not a one-off fluke" but had nothing that actually interrogated a single strong result before it reached that filter. Viral Analysis is that missing step — explicitly notes that success invites more confidence than failure does, making a wrong attribution more likely to slip through.

---

## New: Sprint 013 — Universe Support deferred, not built
Entities, Locations, Organizations, Artifacts, Events, Rules, recurring Characters, and templates for each of those, were requested. Nothing in this vault — across 13 sprints of Reddit Story pipeline work — treats stories as part of a connected continuity; every capability built assumes a one-off, real-or-real-sounding adaptation. Building 15–20 files of universe-tracking infrastructure on a guess risked either significant wasted effort or genuine clutter if it's not actually wanted. Deferred rather than built or silently dropped. If this is a real, new direction — original serialized fiction with a shared universe, distinct from the Reddit adaptation pillar — say so and it's a well-scoped follow-up sprint, not a redesign of what exists.

## New: Commands/ placement — resolved without an ADR
The brief asked for a new top-level "Commands/" section while also saying not to invent new architecture — a direct contradiction. Resolved by recognizing a command doesn't need new content (every capability/workflow already declares Purpose/Inputs/Outputs/Required Notes); it needs a thin trigger-to-artifact mapping, which is exactly what `00_System/` is for. Built as `00_System/Commands/`, a subfolder of an already-existing top-level folder — no ADR needed, consistent with the `Content/Knowledge/` and `Content/Templates/` precedent from Sprints 006 and 011.

## New: Story Database → Story Tracker, one field dropped
Built as `Story_Tracker.md`, keeping every requested field except "Universe Connections" — which only makes sense if Universe Support exists, and it doesn't yet. Add the column back if Universe Support gets built later; it's a one-line addition, not a redesign.

## New: 19 elaborate per-command files → one compact index
The brief's per-command spec (Purpose/Inputs/Outputs/Workflow/Capabilities/Knowledge/Success Criteria/Validation/Expected Result — 8 fields × 19 commands) would have meant restating what every underlying capability already declares, directly contradicting the brief's own "should NOT duplicate documentation, it should orchestrate it." Built one table instead: trigger phrase → target → type. Everything else stays exactly once, where it already lives.

---

## New: Sprint 014 — business premise confirmed changed
Confirmed: the actual business is an original horror content brand, not Reddit Story adaptation. This reverses last sprint's Universe Support deferral (now justified — see [[00_System/Design_Review|Design Review]]) and identifies [[Reddit_Story_Workflow]] and [[Story_Ideation]] as built for the wrong content model. Nothing rebuilt this sprint — this was a review, per its own explicit instruction not to add architecture. Full findings in `Design_Review.md`; the ★★★★★ items are the natural next sprint.

---

## New: Sprint 015 — horror knowledge implemented, real gaps flagged not hidden
Built a 10-note Horror Knowledge layer synthesizing the uploaded research (paraphrased throughout, not reproduced — consistent with every other Knowledge Core note), a new [[Horror_Story_System]] as the primary pillar, a genuinely rewritten [[Story_Ideation]] (generative, not sourcing), a new [[Originality_Check]] capability, and a parallel [[Horror_Story_Production]] workflow. Three things are explicitly NOT resolved this sprint, and shouldn't be assumed fixed:

1. **Numeric threshold reconciliation.** The 11 shared capabilities (Hook_Writing, Retention_Beat_Scripting, etc.) still hard-code Reddit-specific numbers in their Success Criteria (105–125s/part, 20s first reveal, 10–15s escalation beats) inherited from [[Reddit_Story_Workflow]]. The new research provides different, evidence-based numbers for a *single-episode* horror structure (Hook 0–3s, Setup 4–15s, Escalation 16–90s, Reveal 75–92%), but [[Horror_Story_System]] is a *multi-part* format the research doesn't directly address. Reconciling per-part timing for a multi-part horror series against a single-episode research model is real design work, not a find-and-replace — flagged in `Horror_Pacing_Model.md`, `Horror_Story_System.md`, and `Story_Validation.md` rather than guessed at.
2. **Subgenre-specific knowledge still doesn't exist.** This research covers universal horror mechanics (fear of the unknown, dread, curiosity) — it doesn't distinguish Rule Horror's numbered-list mechanic from Psychological Horror's unreliable narration, which was Design Review Critical Item #2. Still open.
3. **Universe Support still not built** (Critical Item #3) — this sprint's research doesn't address recurring monsters/locations/organizations at all.

## New: AI_Video_Production status now genuinely unclear
The confirmed pivot was specifically about the story-content business. Whether the AI-video (oddly-satisfying) pillar is still real, alongside horror, wasn't addressed by the confirmation and wasn't touched this sprint — noted in `02_Systems/Content/README.md` as "status unconfirmed" rather than assumed either way.

---

## New: Sprint 016 — first real production run, real findings
Running an actual story through the full pipeline surfaced things documentation alone hadn't: 
1. **There was no home for actual produced content.** Every prior sprint built specification or tracking, never a content library. Fixed: `02_Systems/Content/Stories/`.
2. **The multi-part vs. single-episode timing question resolved itself in practice** — running the five-phase model once across the whole story and again in miniature per part worked cleanly. Documented in [[The_Doorbell_Camera]]'s Story_Drafting notes as one worked example, not yet generalized back into `Horror_Story_System.md`'s own spec — that generalization is the natural next step, not assumed done from one instance.
3. **The CapCut background-visual question is real, not hypothetical.** Reddit_Story_Workflow's gameplay-overlay convention (Minecraft Parkour/Subway Surfers/GTA Driving) genuinely doesn't fit horror tonally — flagged in the story's own production notes rather than defaulted into or silently replaced with an unreviewed alternative.
4. **The Publishing Checklist correctly reports Incomplete**, not complete — two boxes need something outside this system entirely (an actual audio read-through; a second story to sequence against). This is the checklist behaving exactly as designed: [[Template_Validation]] said an instance with unchecked boxes is Incomplete, and it is.

---

## Resolved: CapCut background-visual convention (flagged Sprint 016, resolved same day)
Horror-genre gameplay footage (Phasmophobia, Poppy Playtime, Fears to Fathom), not AI-generated visuals — AI generation is too costly per-video, and real gameplay footage arguably serves the constant-visual-movement retention mechanic better anyway, not just cheaper. Found and fixed a real bug while resolving this: the original game rotation was hardcoded into the *shared* `CapCut_Production_Formatting` capability, meaning Horror productions were silently inheriting Reddit's specific games rather than getting their own. Capability is now system-agnostic; each system doc owns its own rotation.

---

## Resolved: Publishing_Checklist needed per-part TTS tracking
Checking off Part 1's read-through surfaced that the checklist template couldn't actually represent "one part done, others not" — it had a single story-wide checkbox for a field that's inherently per-part in a sequentially-posted multi-part story. Bumped to Template Version 2 rather than editing in place, per [[Template_Versioning]]'s own rule that a structural field change is a new version, not an edit. Small, but exactly the kind of gap that only shows up from actually using a template, not from designing one.

## New: Agents and AI Video Production status — options laid out, not decided
Both moved from "blocked, needs more info" to "blocked, here are the actual choices" in `Roadmap.md`. Neither resolved — waiting on a decision, not on more building.

---

## New: Video Review via Gemini — candidate for a future capability, not built yet
Claude has no native video-watching tool, so a Gemini-facing review prompt was built as a one-off for [[The_Doorbell_Camera]] rather than a new vault capability. Covers hook timing, pacing, TTS naturalness, visual fit, captions, and cliffhanger pull — genuinely broader than the existing "TTS Read-Through Complete" checklist field, which only covers audio. If this proves useful across more than one story, it's a real candidate for a formal `Video_Review` capability or a new Publishing_Checklist field (Template Version 3) — not done now, since one use isn't a pattern yet.

---

## New: first real video review — one spec confirmed, one execution gap found, two new findings
Gemini's review of the actual rendered Part 1:
1. **Confirmed the background-visual fix from two turns ago was right** — Fears to Fathom-style grounded horror gameplay was independently recommended by the review itself. What was actually used in the render (Backrooms, retro horror house, snowy outdoors, pixelated kitchen) doesn't match that rotation at all — an execution gap between spec and production, not a spec problem. Refined the spec anyway: scene-matching, not just genre-matching (a front-door story wants front-door/hallway footage specifically).
2. **Confirmed a spec that was written but not executed** — per-segment TTS speed variation (added to `CapCut_Production_Formatting.md` two turns ago) wasn't applied in the render; the reveal line delivers at the same flat pace as the setup. Added an explicit Validation check for this, since apparently writing the rule isn't sufficient — it has to be checked for.
3. **Two genuinely new findings**, folded directly into the relevant capabilities rather than staged through Promotion_Candidates: caption/overlay visual collisions (new Validation check in `CapCut_Production_Formatting.md`) and CTA timing cutting off a cliffhanger's final line (new Production Note in `Cliffhanger_Creation.md`, cross-referenced from `Ending_Design.md` since it likely applies there too, untested).

These weren't run through the formal Knowledge_Promotion pipeline — they're production/craft judgment calls (legibility, timing, coherence), not empirical claims about audience behavior that need real retention data to validate. Same category as the original CapCut background-genre fix, which was also incorporated directly rather than staged as a promotion candidate.

---

## New: Sprint 018 — project/knowledge separation, the biggest structural change since Sprint 001
Split reusable knowledge/methodology (stays in `02_Systems/`, `03_Capabilities/`) from project-specific execution (moves to `10_Projects/`) — see [[ADR-0005_Project_Knowledge_Separation]]. Reasoning for what moved and what stayed: a system doc defining how one specific initiative runs, its actual produced output, and its tracking are execution; the Knowledge Core and Capabilities they draw on are reusable across every current and future project, so they stay central regardless of which project needs them.

**What moved:** `Horror_Story_System.md`, `Reddit_Story_Workflow.md`, `AI_Video_Production.md`, `Story_Tracker.md`, `Stories/`, `Templates/` (from `02_Systems/Content/`) and both production workflow instances (from `05_Workflows/`) → new `10_Projects/SocialMediaContent/`. `Funding_Opportunities.md` → new `10_Projects/FundingApplications/`, since it graduated from research into an active pursuit.

**What didn't move, deliberately:** the Knowledge Core (general + Horror), all Capabilities, and every cross-cutting framework (Context/Execution/Template/Workflow) — all genuinely reusable across projects, not owned by the content pillar specifically.

**Three new active projects**, corresponding to Candidate Options 1, 3, and 4 from `MoneyMaking/Candidate_Options.md`: [[10_Projects/ContentAgency/README|ContentAgency]], [[10_Projects/TemplateSales/README|TemplateSales]], [[10_Projects/FundingApplications/README|FundingApplications]]. Options 2 and 5 stay documented but weren't approved for active work.

**Link integrity note:** the vault's established convention of bare wikilinks resolving by unique filename (not path) meant the vast majority of cross-references — every capability pointing at `[[Horror_Story_System]]` or `[[Reddit_Story_Workflow]]`, for instance — survived the move automatically. Only plain-text path mentions and folder-qualified links needed manual fixes; a full audit (dead links, orphans, missing indexes) was run before and after to confirm this, not assumed.

**Caught two things stale since Sprint 013 while doing this pass:** `Home.md` still displayed version `0.13.0-alpha`, and `00_System/README.md`'s own Contents list never mentioned `Commands/`, `Repository_Audit.md`, or `Design_Review.md` despite all three existing since Sprint 013/014. Both fixed.

---

## New: Sprint 020 — QuickTurnaroundGigs, and a naming-convention gap worth flagging
"1,3,4" this time referred to a newly-pasted strategy document's own numbering (Research & Briefing Gigs, Real-Time Problem Arbitrage, Digital Assets & Micro-Tools), not the earlier Candidate_Options numbering — disambiguated up front since the two overlap in number but not in content. #4 folded into the already-existing `TemplateSales` rather than duplicating it. #1 and #3 share one underlying workflow (Perplexity sources the opportunity, Claude executes fast) against different channels, so they became two documents inside one new project, `QuickTurnaroundGigs`, rather than two separate projects.

**Naming-convention gap, noted not fixed:** `Naming_Convention.md` specifies `Pascal_Case` (underscore-separated) for folders, but every `10_Projects/` project folder created since Sprint 017 (`SocialMediaContent`, `ContentAgency`, `TemplateSales`, `FundingApplications`, `QuickTurnaroundGigs`) uses PascalCase without underscores instead, for readability at that naming length. This is an inconsistency with the stated rule, not a one-off exception like the `AI` acronym case — worth either amending `Naming_Convention.md` to formalize project-folder names as a second accepted pattern, or renaming the folders for consistency. Neither done now, per this sprint's "structure only" scope.

---

## New: Sprint 022 — token efficiency pass
Five things fixed, per direct request:
1. Trimmed the 3 thinnest capability files (Watermark Tier Management, Generation Mode Selection, Veo Prompt Design) — cut boilerplate Analytics Reference/Knowledge Dependencies sections that just said "not applicable yet" in different words each time.
2. Consolidated 4 near-duplicate integration docs (Future_Integration, Future_Runtime_Integration, Template_Integration, Workflow_Integration) into one — `01_Architecture/Future_Integration.md`. All four said versions of the same thing about Agents/MCP/Automation not existing yet.
3. Condensed Reddit_Story_Workflow to a stub — only what's genuinely pillar-specific (its own numbers, its own gameplay rotation) stays; everything shared with Horror_Story_System is no longer restated.
4. Analytics: merged Daily/Weekly/Monthly Review (90% identical content, only the interval differed) into one Review_Cadences.md; compressed the remaining 7 files without merging them, since they're each genuinely distinct concepts — reduced density, not file count, for those.
5. Going forward: full vault-wide audits are reserved for actual structural changes, not every single-line edit — scaled to match the size of the change.

Net: 161 → 156 files, and the files that stayed are meaningfully denser. Full audit run before and after, not assumed clean.

---

## New: Sprint 026 — accuracy pass, and the process bug behind it
Asked to "optimize," the honest finding was that the vault's problem wasn't size — it was **accuracy drift**. Four files still described `04_Agents/` and `02_Systems/Automation/` as empty after both had been built, and `Roadmap.md` was four sprints stale (stopped at 021 while the Changelog ran to 0.28.0). A second brain that misreports its own state is a worse failure than a slightly bloated one, because every downstream decision inherits the wrong picture.

**Root cause, found rather than assumed:** `Development_Workflow.md`'s sprint-completion step listed `Changelog.md` and `Dashboard.md` but omitted `Roadmap.md`. That's exactly why one stayed current and the other didn't — not carelessness, a missing checklist item. Fixed at the process level, not just by patching the symptom.

**Deliberately not done:** `Suggestions.md` (30KB) and `Changelog.md` (30KB) are together ~16% of the vault by size, but neither appears in any note's Required Notes, so neither costs anything at load time. Compressing them would have looked productive while changing nothing real. Left alone on purpose.

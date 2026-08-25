# Horror Story System

Purpose: System definition for the original horror content pillar — the active Content pillar as of Sprint 015, confirmed as the actual business.
Last Updated: 2026-08-03
Status: Archived 2026-08-13 — see 99_Archive/HorrorProject/README.md
Related Documents: [[99_Archive/HorrorProject/README|HorrorProject (Archived)]], [[Reddit_Story_Workflow]], [[02_Systems/Content/Knowledge/Horror/README|Horror Knowledge]]

---

## What It Produces
Original multi-part horror stories — psychological, rule, mystery, supernatural, and internet horror — for TikTok, YouTube Shorts, and Instagram Reels. First-person, TTS-narrated. Original material, not sourced or adapted from existing posts — see [[Story_Ideation]].

## Format Constraints
Adapted from evidence-based short-form horror research (see [[Horror_Pacing_Model]]):
- A single episode/part follows five phases: Hook (0–3s) → Setup (4–15s) → Escalation (16–90s) → Climax/Reveal (~75–92% of runtime) → Final Sting (final stretch).
- Multi-part stories carry this same arc across the whole series while each individual part still needs its own local hook — a viewer can land on part 2 without having watched part 1. Exact per-part timing for a multi-part structure is not yet reconciled with the single-episode research model — see `Suggestions.md`.
- Visual/audio re-engagement cues roughly every 3–5 seconds; narrative escalation beats roughly every 8–15 seconds. Different rhythms — not the same rule stated twice.
- **Background visual: horror-genre gameplay footage**, rotating every 3–5 seconds (per the cue cadence above). Not [[Reddit_Story_Workflow]]'s Minecraft Parkour / Subway Surfers / GTA Driving rotation — that convention is cheerful and chaotic, which actively fights dread-paced narration. Rotation: Phasmophobia, Poppy Playtime, Fears to Fathom — same production cost as the original convention (screen-recorded, no AI generation), same constant-visual-movement retention mechanic, tonally consistent instead of dissonant. Resolved from a real conflict surfaced in [[The_Doorbell_Camera]]'s production notes, not decided in the abstract.

## Retention Structure
- Concrete, specific detail with exactly one withheld element — not vague mystery. See [[Horror_Hook_Techniques]].
- The threat is evidenced, never explained, until the reveal. See [[Fear_Of_The_Unknown]].
- Reveal lands before the very end of the runtime, not at the literal end — audience loss is heaviest in the first quartile and spikes again at the very end, so a payoff placed only at the true end reaches a small fraction of the audience that started.
- The final line reframes what came before and leaves one smaller thread open. See [[Open_Loops]].

## Craft Knowledge
Two layers apply, and neither duplicates the other:
- General storytelling craft — [[Storytelling_Fundamentals]], [[Narrative_Structure]], [[Hook_Principles]], [[Suspense_And_Curiosity]], [[Pacing]], [[Emotional_Engagement]], [[Reader_Retention]], [[Writing_Style]], [[Clarity]], [[Editing_Principles]] — stays fully reusable, unchanged.
- Horror-specific, evidence-based craft — [[02_Systems/Content/Knowledge/Horror/README|Horror Knowledge]] — extends the above with fear psychology, escalation mechanics, and first-person-specific technique.

## Capabilities
Shares the same capability set built for [[Reddit_Story_Workflow]] — [[Hook_Writing]], [[Retention_Beat_Scripting]], [[Cliffhanger_Creation]], [[Ending_Design]], [[Story_Editing]], [[TTS_Optimization]], [[CapCut_Production_Formatting]], [[Multi_Platform_Caption_Generation]], [[Metadata_Generation]], [[Series_Planning]] — since their core logic is genre-agnostic. [[Story_Ideation]] has been rewritten specifically for this pillar (generation, not sourcing). [[Story_Validation]] now includes an originality check — see [[Originality_Check]]. These capabilities' Success Criteria still reference Reddit-specific numeric thresholds inherited from [[Reddit_Story_Workflow]] and haven't yet been reconciled against this system's own numbers — flagged in `Suggestions.md`, not silently left inconsistent.

## What to Measure
Per the confirmed growth objective: retention (the drop-off curve within a video, especially at the hook), watch time, completion rate, shares, comments, saves, followers gained, and returning-viewer rate — in roughly that priority order. Views alone are the least informative of these; a story can get views without holding anyone, which the retention curve shows and a view count doesn't. See [[Metrics_Framework]] for how a raw number like "62% average watch time" becomes a metric — compared against a stated expectation, not read in isolation. First checkpoint timing (24–48 hours, then ~1 week) is [[Review_Process]]'s, not repeated here.

## Relationship to Reddit_Story_Workflow
[[Reddit_Story_Workflow]] is no longer the primary Content pillar — see its own updated status. Its capabilities remain valid and are shared here rather than duplicated.

## Not Yet Built
Universe Support (recurring monsters, locations, organizations) and horror subgenre-specific knowledge (what structurally distinguishes Rule Horror from Psychological Horror, etc.) — both flagged as open in prior sprints, neither resolved by this one. This sprint's research covers universal horror mechanics, not subgenre differentiation.

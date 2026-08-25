# CapCut Production Formatting

Purpose: Capability for turning a finished script into CapCut-ready production instructions.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]], [[Horror_Story_System]]
Required Notes: [[Reddit_Story_Workflow]], [[Horror_Story_System]]
Related Notes: [[Editing_Principles]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Attaches overlay text, visual direction, SFX cues, gameplay background selection, and timing to a finished script so it's ready to edit in CapCut. Compression follows [[Editing_Principles]]'s subtractive-by-default rule. The timing numbers below (length, part count) are shared defaults inherited from [[Reddit_Story_Workflow]]; the background visual rotation is system-specific and NOT shared — see each system doc's own convention, and `Suggestions.md` for why these were split apart.

## Inputs
- Finished script (with retention beats already scripted)
- Target length

## Outputs
- CapCut settings, overlay text, visual direction, SFX cues, background gameplay schedule

## Success Criteria
- 105–125 seconds of CapCut TTS (~240–290 words) per part.
- Maximum 3 parts per story.
- Background visual rotation follows the active system's own convention (see [[Reddit_Story_Workflow]]) — this capability applies whatever rotation is designated, it doesn't own the choice of what's in it. Horror_Story_System's rotation (Phasmophobia/Poppy Playtime/Fears to Fathom) is archived alongside it, reusable if a future system needs it.
- Within that rotation, footage should match the *specific scene* being narrated, not just the genre — a story about a front door benefits from footage of an actual dark hallway or doorway, not just any dark horror game. Genre-matching alone (Sprint 016) was a real fix; scene-matching is the finer-grained version of the same principle, found by actually reviewing a rendered video rather than reasoned out in advance.
- TTS voice speed starts around 1.1–1.2x — see [[Horror_Pacing_Model]]'s spoken-pace principle. If the tool supports per-segment speed, vary it slightly faster through escalation beats and slightly slower through calm sensory lines, implementing [[First_Person_Horror_Technique]]'s rhythm-as-signal principle in production, not just in the script text. A single flat speed is the practical fallback, not the ideal — and specifying this rule doesn't guarantee it gets applied; see Validation below.

## Validation
Does the formatted output fall within the length window, and does every required element (overlay, SFX, gameplay schedule) exist for every part? A missing SFX cue or an out-of-range length fails. Two checks added after the first real production run: does any on-screen overlay (background footage text, notes, UI elements) visually collide with the caption text at any point — a multi-second collision is a fail, not a minor note; and was the per-segment TTS speed variation actually applied, or does the rendered audio sound flat despite the spec calling for variation? A correct spec that wasn't executed still fails validation.

## Analytics Reference
Length-vs-retention correlation is a [[Metrics_Framework]] question for [[Review_Process]] once real output exists.

## Knowledge Dependencies
None directly — [[Editing_Principles]] informs the compression approach, but this capability is primarily production mechanics.

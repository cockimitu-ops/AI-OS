# TTS Optimization

Purpose: Capability for optimizing a script's text specifically for spoken/TTS delivery, distinct from CapCut production settings.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Clarity]], [[Reddit_Story_Workflow]]
Related Notes: [[CapCut_Production_Formatting]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Adjusts punctuation, sentence length, and pronunciation-sensitive words so the edited draft reads naturally through TTS. Distinct from [[CapCut_Production_Formatting]], which sets timing, overlay, and SFX — this capability only touches the script text itself, applying [[Clarity]]'s spoken/TTS principle directly.

## Inputs
An edited draft, from [[Story_Editing]].

## Outputs
A TTS-ready script: adjusted punctuation and flagged pronunciation risks.

## Success Criteria
No sentence exceeds a length that would force an unnatural TTS pause mid-thought, per [[Clarity]]'s one-idea-per-sentence rule applied to spoken delivery specifically. Any name or word with a non-obvious pronunciation is flagged with a phonetic hint.

## Validation
Read the script through the actual CapCut TTS engine before finalizing — a script that reads fine silently but stumbles aloud fails, since the whole point of this capability is the spoken result, not the written one.

## Analytics Reference
TTS-specific failure points — mispronunciations, awkward pacing — are [[Failure_Analysis]] material distinct from content-quality failures.

## Knowledge Dependencies
[[Clarity]].

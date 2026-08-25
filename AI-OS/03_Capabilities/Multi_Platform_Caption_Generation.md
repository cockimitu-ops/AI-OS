# Multi-Platform Caption Generation

Purpose: Capability for producing platform-specific captions and a TTS-ready plain-text export for a finished script.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Reddit_Story_Workflow]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Generates a caption tailored to each target platform's conventions, plus a plain-text/unformatted version of the full script for direct TTS copying. Purely mechanical — draws on platform requirements from [[Reddit_Story_Workflow]], not on the Knowledge Core.

## Inputs
- Finished script
- Story title/theme

## Outputs
- One caption each for TikTok, YouTube Shorts, Instagram Reels, Facebook Reels
- One plain-text TTS copy of the script

## Success Criteria
- Exactly four captions produced, one per platform — not a single caption reused.
- Plain-text export contains no formatting or stage directions.

## Validation
Structural check: are all four platform captions present and distinct, and does the plain-text export parse as pure narration with nothing else in it?

## Analytics Reference
Caption performance (which platform captions actually drove engagement) is a [[Metrics_Framework]] question once real output exists — not evaluated by this capability itself.

## Knowledge Dependencies
None — this capability is platform mechanics, not storytelling craft.

# Originality Check

Purpose: Capability for verifying a generated horror premise, monster, or setting isn't an unattributed reuse of existing IP, before drafting time is spent on it.
Last Updated: 2026-08-03
Status: Active — new Sprint 015
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[99_Archive/HorrorProject/README|HorrorProject (Archived)]]
Required Notes: [[Story_Ideation]]
Used By: [[Story_Validation]] — its Sprint 015 originality pass calls this. (Horror_Story_System archived 2026-08-13; this capability is otherwise reusable for any original, non-adapted content system.)

---

## What It Does
Checks a candidate premise against known horror IP and established genre conventions — a specific monster design, a named mythos, a widely-circulated creepypasta — before the premise clears validation. Reddit adaptation had a built-in originality floor: the source material actually existed and was attributable. Original horror generation has no equivalent safeguard by default, which is exactly why this capability exists now and didn't for the prior pillar.

## Inputs
A candidate premise, including any proposed recurring monster, location, or organization, from [[Story_Ideation]].

## Outputs
A pass, or a flagged concern naming the specific existing work or convention the candidate resembles too closely.

## Success Criteria
A passed premise's core "hook" element — the monster's specific mechanic, the location's specific rule, the organization's specific structure — is not a close match to a single identifiable existing work. Genre conventions (a haunted house, a rule-following entity) are fine; a specific, recognizable execution of one is not.

## Validation
Was a specific check actually performed and recorded, or was originality assumed by default? An unrecorded pass is treated the same as a fail — this capability exists to create a record, not just a feeling of having checked.

## Analytics Reference
A flagged premise that gets revised and re-passes is worth a [[Learning_Extraction]] entry if the same kind of near-miss recurs — a pattern of the same convention getting flagged repeatedly suggests [[Story_Ideation]] itself should avoid it earlier, not just catch it here every time.

## Knowledge Dependencies
None — this is a check against external reference points, not internal craft knowledge.

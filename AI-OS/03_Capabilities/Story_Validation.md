# Story Validation

Purpose: Capability for deciding whether a candidate idea is worth drafting.
Last Updated: 2026-08-03
Status: Active — updated Sprint 015
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[99_Archive/HorrorProject/README|HorrorProject (Archived)]]
Required Notes: [[Storytelling_Fundamentals]], [[Reader_Retention]]
Used By: none currently — Horror_Story_System archived 2026-08-13. Genuinely reusable, available for a future system.

---

## What It Does
Screens a candidate premise, from [[Story_Ideation]], against retention potential and originality before drafting time is spent on it. As of Sprint 015, includes an originality pass — see [[Originality_Check]] — which the prior Reddit-adaptation version of this capability didn't need, since real source material had its own originality floor.

## Inputs
A candidate premise, from [[Story_Ideation]].

## Outputs
A go / no-go decision, with the specific reason if no-go, and an [[Originality_Check]] result attached.

## Success Criteria
- A "go" candidate can name where its opening disturbance and its major reveal would land in the structure — see [[Horror_Pacing_Model]]. Exact numeric thresholds for this system haven't been finalized against the inherited Reddit-specific ones yet; see `Suggestions.md`.
- A "go" candidate has passed [[Originality_Check]].
- If neither the structural placement nor originality can be confirmed, it's a no-go.

## Validation
Was a specific reason given for the decision? "Doesn't feel right" is not a valid no-go reason — it must name what's missing: change, conflict, placeable reveal, or an originality concern.

## Analytics Reference
False negatives (rejected ideas that would have worked) and false positives (approved ideas that failed) are both [[Failure_Analysis]] material, evaluated once enough validated-and-published stories exist to compare against.

## Knowledge Dependencies
[[Storytelling_Fundamentals]], [[Reader_Retention]].

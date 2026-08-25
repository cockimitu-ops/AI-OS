# Quality Assurance

Purpose: Execution-level QA — checking that a task followed AI OS's process correctly, not judging the content itself.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Execution/README|01_Architecture/Execution]], [[Execution_Lifecycle]], [[Principles]]

---

## Scope
This QA layer checks the *process*: did execution respect the repository's own standards. It does not judge whether a piece of content is good — that's content-specific QA, owned by the capability that produced it (e.g., a horror story script's retention quality is judged by the relevant `10_Projects/` content system doc, not here).

## Checklist

| Check | Question |
|---|---|
| Architecture consistency | Does the output fit the repository's existing structure without requiring a redesign? |
| Knowledge reuse | Did execution reference existing notes instead of restating their content? |
| No duplicated information | Does any fact now exist in two places that should exist in one? |
| Output completeness | Does the output satisfy every Success Criterion from [[Task_Specification]]? |
| Token efficiency | Was only Required (and, if needed, Optional) context loaded — see [[Context_Budget]]? |
| Repository standards | Does every new or changed file follow `Naming_Convention.md` and the standard header? |

## Failure Handling
A failed check doesn't discard the output — it routes back to the relevant earlier stage. A duplication failure goes back to Capability Resolution to check whether the right capability was even used; a completeness failure goes back to Execution. See [[Execution_Lifecycle]].

# ADR-0002: Git Workflow Conventions

Status: Accepted
Date: 2026-08-03
Related Documents: [[Development_Workflow]], [[Suggestions]]

---

## Context
`Development_Workflow.md` established roles and the sprint cycle but left branch naming and commit message format undefined, even though Git is one of the vault's three stated pillars (Obsidian as interface, Markdown as source of truth, Git as version history).

## Decision
**Branches**
- `sprint/<number>-<short-slug>` for sprint work, e.g. `sprint/002-content-system`
- `adr/<id>-<short-slug>` for ADR drafting, e.g. `adr/0002-git-workflow`
- `fix/<short-slug>` for corrections outside a sprint's original scope

**Commits**
Format: `<scope>: <what changed>`, where `<scope>` is the top-level folder or ADR affected.
Examples: `01_Architecture: add ADR-0001`, `02_Systems/Content: add Reddit story workflow definition`.
An optional body explains *why*, not just *what* — especially when the reason isn't obvious from the diff alone.

**Main branch**
Always reflects the last Architect-approved state. A sprint branch merges in only once that sprint is marked complete in `Changelog.md`, not before.

## Alternatives Considered
- Conventional Commits (`feat:`, `fix:`, `docs:`) — rejected as unnecessary ceremony for a documentation-first repository where nearly every commit is effectively `docs:`.
- No fixed convention — rejected: history becomes unsearchable exactly as the vault approaches the scale it's designed for.

## Consequences
- Commit scope should always be inferable from the message alone, without opening the diff.
- Sprint branches give a natural revert point if a sprint needs to be rolled back wholesale.

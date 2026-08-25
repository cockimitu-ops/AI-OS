# ADR-0003: Placement of Cross-Cutting Engine Subsystems

Status: Accepted
Date: 2026-08-03
Related Documents: [[Repository_Structure]], [[01_Architecture/Execution/README|01_Architecture/Execution]], [[07_Context/README|07_Context]]

---

## Context
Sprint 004 placed the Context Engine in `07_Context/` because that folder already existed with a near-exact matching purpose ("standing context fed to agents and workflows"). Sprint 005 needed to place the Execution Engine — a similarly foundational, model-independent, cross-cutting specification — but no existing top-level folder matches its purpose, and creating a new top-level folder is a structural change `Development_Workflow.md` reserves for an ADR.

## Decision
Cross-cutting, model-independent runtime/retrieval specifications — the Context Engine, the Execution Engine, and any similar future subsystem without an obviously matching existing folder — live as dedicated subfolders under `01_Architecture/`, following the precedent already set by `ADR/`. `01_Architecture/Execution/` is accepted as the home for the Execution Engine on this basis.

This does not relocate the Context Engine — `07_Context/` remains its home, since a matching folder already existed before this question arose. This ADR governs future engines without an existing folder, not the one already placed.

## Alternatives Considered
- A new top-level folder per engine — rejected: would require its own ADR each time and has no clear numbering slot in the existing 00–10/99 sequence without renumbering everything after it.
- Folding every future engine into `07_Context/` regardless of topic — rejected: directly contradicts the Knowledge/Context/Execution/Agents/Automation separation the Execution Engine itself documents.

## Consequences
- `01_Architecture/` will accumulate more subfolders as new engines are defined, alongside `ADR/`.
- `Repository_Structure.md` treats "`01_Architecture/` subfolders" as an evolving category rather than a fixed pair.
- Future sprints proposing a new engine-type subsystem don't need a fresh ADR to decide placement — this one already answers it, unless a case arises that genuinely doesn't fit the pattern.

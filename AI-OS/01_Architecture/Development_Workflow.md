# Development Workflow

Purpose: How work actually gets done in AI OS — roles, sequencing, and how changes are proposed.
Last Updated: 2026-08-26
Status: Active
Related Documents: [[Roadmap]], [[01_Architecture/ADR/README|ADR README]]

---

## Roles
**Chief Systems Architect** — owns the architecture: folder structure, conventions, what gets built and in what order.
**Lead Repository Engineer** — implements the architecture faithfully: creates the files, folders, and documentation the architecture calls for.

The Engineer does not change the architecture unilaterally. Anything the Engineer believes should change goes into `Suggestions.md` at the repository root instead of being applied directly.

## Sprint Cycle
1. Architect defines the scope of a sprint.
2. Engineer implements the scope: files, folders, documentation.
3. Engineer records suggestions and open questions, but does not act on them.
4. Architect reviews, approves, and either authorizes the next sprint or requests changes to the current one.
5. `Changelog.md`, `Dashboard.md`, `Roadmap.md`, **and the root `README.md`** are updated to reflect the completed sprint. All four, every time — Roadmap was originally omitted here and drifted four sprints behind before it was caught (Sprint 026); the root `README.md` was omitted too and sat frozen on "Sprint 001, 0.1.0-alpha" for twenty-eight sprints until Sprint 029 caught it. A status document that isn't in this checklist will go stale, regardless of intent. That is now twice-demonstrated, not a theory.

## Proposing Structural Change
Structural changes (new top-level folders, renamed responsibilities, changed conventions) go through an ADR, not a direct edit:
1. Draft the ADR in `01_Architecture/ADR/` using the next sequential ID.
2. State the decision, the context, and the alternatives considered.
3. Once accepted, update the affected documents (`Repository_Structure.md`, `Naming_Convention.md`, etc.) to match and reference the ADR.

## Version Control
Git tracks every change. Branch naming and commit message conventions are defined in [[ADR-0002_Git_Workflow_Conventions]].

## What Doesn't Need an ADR
Adding content within an already-defined structure (a new capability inside `03_Capabilities/`, a new agent inside `04_Agents/`) doesn't require an ADR — it requires following the conventions already documented in `Naming_Convention.md` and the relevant folder's `README.md`.

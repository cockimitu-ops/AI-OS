# ADR-0005: Project/Knowledge Separation for Multi-Project, Token-Conscious Organization

Status: Accepted
Date: 2026-08-05
Related Documents: [[Repository_Structure]], [[10_Projects/README|10_Projects]], [[02_Systems/README|02_Systems]]

---

## Context
The vault was built around one initiative (Reddit/Horror content production), so project-specific execution — system docs defining how that initiative runs, its actual produced output, its status tracking — grew up alongside genuinely reusable knowledge (the Knowledge Core, the shared Capabilities) under `02_Systems/Content/`. With multiple concurrent business initiatives now active (content production, a B2B content agency, template sales, funding applications), that conflation has a real cost: every new project either re-derives knowledge that already exists, or has to load an unrelated project's execution history to get at the knowledge sitting next to it. Both work against the stated goal of a token-conscious, multi-project "second brain."

## Decision
Separate reusable knowledge/methodology from project-specific execution:
- **Reusable knowledge/methodology stays central** — the Knowledge Core and Horror Knowledge subfolder remain in `02_Systems/Content/Knowledge/`; Capabilities remain in `03_Capabilities/`; all cross-cutting frameworks (Context Engine, Execution Engine, Template Framework, Workflow Framework, Analytics methodology) are untouched.
- **Project-specific execution moves to `10_Projects/`** — a system doc that defines how one specific initiative operates (e.g., `Horror_Story_System.md`), that initiative's actual produced output, and its own tracking, move into a dedicated project folder. `10_Projects/` already exists for exactly this per its original definition; this decision extends "time-bound initiative with a defined deliverable" to include an ongoing business initiative with a specific goal, not only a literally time-boxed task.
- Capabilities and Knowledge Core notes are explicitly shared across every `10_Projects/` initiative that needs them — a project consumes them, never forks or duplicates them.

## Alternatives Considered
- Leave content execution under `02_Systems/Content/` and treat `10_Projects/` as research/decision documentation only — rejected: doesn't scale once more than one execution-heavy initiative exists at once, and directly works against the token-budget goal, since loading "the Content system" would pull in every pillar's execution history regardless of which one a task actually needs.
- A new top-level folder specifically for active initiatives, distinct from `10_Projects/` — rejected: `10_Projects/` already serves this purpose; adding a second category for the same concept duplicates responsibility rather than clarifying it.

## Consequences
- `02_Systems/Content/` becomes purely knowledge/methodology — the Knowledge Core, not execution.
- `05_Workflows/` keeps the Workflow *Framework* (the specification of how any workflow is structured); production workflow *instances* (`Reddit_Story_Production.md`, `Horror_Story_Production.md`) move alongside the project they serve, since an instance is execution, not framework.
- Every future initiative gets its own `10_Projects/` subfolder, keeping per-project context small enough to load or share independently — with any AI tool, not just the one that built it.
- Bare wikilinks (the vault's established convention) resolve by unique filename regardless of folder, so this move does not break cross-references from Capabilities or other notes into the moved files — only plain-text path mentions and folder-qualified links needed manual fixes, both audited before and after this change.

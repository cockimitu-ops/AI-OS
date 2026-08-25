# ADR-0001: Naming Disambiguation for 02_Systems Subfolders and Acronym Folder Names

Status: Accepted
Date: 2026-08-03
Related Documents: [[Naming_Convention]], [[02_Systems/README|02_Systems]], [[Suggestions]]

---

## Context
Sprint 001 raised two naming ambiguities:
1. `02_Systems/Research/`, `02_Systems/Analytics/`, and `02_Systems/Architecture/` share names with the top-level `08_Research/`, `09_Analytics/`, and `01_Architecture/` folders, risking confusion about where new content belongs.
2. `02_Systems/AI/` doesn't fit the `Pascal_Case` folder naming rule, since "AI" is an acronym rather than a capitalized word.

## Decision
The originally specified folder names are retained as-is — no renaming.

- The distinction between `02_Systems/{Research,Analytics,Architecture}` and their top-level counterparts is now ratified as: `02_Systems/X/` documents the *system/process* that performs the work; the corresponding top-level folder holds the *output* that process produces. This is the authoritative rule, not a working assumption.
- Acronym folder/file names (e.g., `AI`) are an accepted exception to `Pascal_Case` and are written exactly as the acronym — not force-cased, not expanded.

## Alternatives Considered
- Renaming `02_Systems/Research/` etc. to something more distinct (e.g., `Research_Ops/`) — rejected, to preserve the folder names as originally specified and avoid structural churn this early in the vault's life.
- Merging each system/output pair into a single location — rejected: it collapses "how the work is done" from "what the work produced," a distinction worth keeping as the vault scales toward thousands of files.

## Consequences
- No files move as a result of this decision.
- `Naming_Convention.md` and the affected `README.md` files reference this ADR as the source of the rule.
- Going forward: process/methodology documentation belongs under `02_Systems/`; produced content belongs under the corresponding top-level folder.

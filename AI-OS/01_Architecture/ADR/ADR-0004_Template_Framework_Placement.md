# ADR-0004: Generalizing Cross-Cutting Subsystem Placement to Include Format/Documentation Standards

Status: Accepted
Date: 2026-08-03
Related Documents: [[ADR-0003_Execution_Engine_Placement]], [[01_Architecture/Templates/README|01_Architecture/Templates]]

---

## Context
ADR-0003 established that cross-cutting, model-independent runtime/retrieval specifications (Context Engine, Execution Engine) live as dedicated subfolders under `01_Architecture/`. Sprint 009 introduced a Template Framework — also cross-cutting and model-independent, but governing document format/structure rather than runtime or retrieval. It doesn't cleanly fit ADR-0003's literal scope, and no existing folder matches its purpose. `06_Assets/` was considered and rejected: it's explicitly for non-Markdown files, while the Template Framework's own documentation is Markdown philosophy/structure content, not the non-Markdown asset files a template might eventually produce.

## Decision
ADR-0003's placement rule is generalized: any cross-cutting, model-independent specification — whether it governs runtime, retrieval, or document format/structure — without an existing matching folder, lives as a dedicated subfolder under `01_Architecture/`, alongside `ADR/`, `Execution/`, and now `Templates/`. This doesn't relocate the Context Engine or Execution Engine; it extends the same reasoning to a third, related category rather than treating Templates as a one-off exception.

## Alternatives Considered
- Treating this as already covered by ADR-0003's literal wording — rejected: ADR-0003 named "runtime/retrieval" specifically, and stretching a rule past its stated scope without saying so undermines the point of writing rules down at all.
- `06_Assets/` — rejected: reserved for non-Markdown files; the Template Framework itself is Markdown documentation, not the (out of scope this sprint) actual template files it will eventually govern.
- A new top-level folder for Templates specifically — rejected for the same reason ADR-0003 rejected it for Execution: no clear numbering slot, and a fresh ADR needed every time a new cross-cutting concern appears.

## Consequences
- `01_Architecture/` continues to accumulate subfolders as new cross-cutting concerns are identified — now three: `ADR/`, `Execution/`, `Templates/`.
- Future proposals for a new cross-cutting subsystem, of any of these three kinds or a clearly analogous fourth, can point to this ADR rather than needing another one, unless the case genuinely doesn't fit.
- `06_Assets/README.md`'s original description (Sprint 001) listed "templates" as an example asset type, written before the Template Framework existed and referring to non-Markdown template files (e.g., a `.docx` template) — a different concept from this sprint's Markdown framework. Updated to avoid the now-ambiguous overlap.

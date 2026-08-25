# 07_Context

Purpose: Standing context fed to agents and workflows — and, as of Sprint 004, home of the Context Engine: the retrieval layer that decides what an AI reads before doing a task.
Last Updated: 2026-08-03
Status: Active — Sprint 004
Related Documents: [[04_Agents/README|04_Agents]], [[05_Workflows/README|05_Workflows]], [[03_Capabilities/README|03_Capabilities]]

---

## Responsibility
Two things live here:
1. **Standing context** — background, constraints, and preferences agents and workflows need but that aren't themselves capabilities. Original Sprint 001 scope; still empty, populated alongside the first agent/workflow.
2. **The Context Engine** — the rules governing how any AI working in this vault decides what to read before acting. Added in Sprint 004.

## Context Engine — Contents
- [[Context_Philosophy]] — why context and token efficiency matter here
- [[Context_Resolution]] — Required / Optional / Related / Escalation categories
- [[Dependency_Rules]] — how a note declares what it depends on
- [[Loading_Strategy]] — the fixed order an AI reads things in
- [[Context_Budget]] — practical limits on how much gets loaded
- [[Knowledge_Promotion]] — how observations become permanent knowledge, without duplicating existing governance
- [[Future_Integration]] — how Capabilities, Agents, Workflows, and Automation will plug in later (now consolidated in `01_Architecture/`)
- [[Knowledge_Core]] — a hard-capped, self-curating standing record about Felix specifically, distinct from the Knowledge Promotion pipeline that governs craft knowledge

## Note on Folder Naming
An earlier brief referenced `07_Templates/`, `08_Reference/`, `09_Knowledge/` — those don't exist. The actual folders at those positions are `07_Context/` (this one), `08_Research/`, `09_Analytics/`. Since this sprint's mission is literally the Context Engine, it's built here rather than in a new folder. See `Suggestions.md`.

## Status
Sprint 004 complete. Standing context itself (item 1 above) remains empty, still pending the first agent/workflow.

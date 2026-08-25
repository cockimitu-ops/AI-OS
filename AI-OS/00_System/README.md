# 00_System

Purpose: Operational entry points for the vault — navigation, status, history, and terminology.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[README|AI OS README]], [[01_Architecture/README|01_Architecture]]

---

## Responsibility
This folder answers "where do I start" and "what's the current state." It contains no architecture decisions and no system/capability content — those live in `01_Architecture/` and `02_Systems/` onward.

## Contents
- `Home.md` — landing page and top-level map of content
- `Dashboard.md` — current sprint and system status snapshot
- `Roadmap.md` — sprint-level plan
- `Changelog.md` — version history
- `Glossary.md` — shared vocabulary
- `Repository_Audit.md` — structural health checks (dead links, orphans, missing indexes)
- `Design_Review.md` — strategic review against the actual business
- [[00_System/Commands/README|Commands/]] — the command layer: [[00_System/Commands/Command_Index|Command Index]] and [[00_System/Commands/Quick_Start|Quick Start]]

## Maintenance
`Dashboard.md` and `Changelog.md` should be updated at the end of every sprint. `Roadmap.md` updates when sprint scope changes. `Glossary.md` updates whenever a new term is introduced anywhere in the vault — terms should be defined once, here, and linked to elsewhere, not redefined per-document.

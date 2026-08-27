# 02_Systems

Purpose: The operating domains of AI OS — where systems, as opposed to one-off content, live.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[Glossary]], [[Architecture]], [[ADR-0005_Project_Knowledge_Separation]]

---

## Responsibility
A "system" here is a broad operating domain — Content, Research, Analytics, Automation, AI, Architecture — that groups reusable knowledge and methodology. As of Sprint 018, systems hold knowledge/methodology only, not project-specific execution — see [[ADR-0005_Project_Knowledge_Separation]]. See [[Glossary]] for the precise definition.

## Subfolders
- [[02_Systems/Content/README|Content/]] — **populated**: general and horror-specific storytelling knowledge. Project execution (system docs, produced stories, tracking) lives in [[10_Projects/SocialMediaContent/README|10_Projects/SocialMediaContent]] instead.
- [[02_Systems/Analytics/README|Analytics/]] — **populated**: review methodology, cadences, outlier analysis
- [[02_Systems/Research/README|Research/]] — scaffolded, not yet populated
- [[02_Systems/Automation/README|Automation/]] — **populated**: the live Task Runner (worker + Telegram bridge + backups, added 2026-08-26) and the AI OS MCP server (Sprint 025)
- [[02_Systems/AI/README|AI/]] — scaffolded, not yet populated
- [[02_Systems/Architecture/README|Architecture/]] — scaffolded, not yet populated — systems for designing external systems, not this vault's own architecture (see [[01_Architecture/README|01_Architecture]] for that)

## Note on Naming
`Research`, `Analytics`, and `Architecture` also exist as top-level folders (`08_Research/`, `09_Analytics/`, `01_Architecture/`) with a different meaning: the top-level folders hold output, these subfolders hold the systems/methodology that produce that output. Resolved in [[ADR-0001_Naming_Disambiguation]] — no longer an open question.

## Status
Content, Analytics, and Automation populated. Research, AI, and Architecture remain scaffolded, pending concrete scope.

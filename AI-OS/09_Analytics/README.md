# 09_Analytics

Purpose: Metrics, reports, and performance tracking produced by the vault's Analytics system.
Last Updated: 2026-08-03
Status: Active — structures built Sprint 012, no data yet
Related Documents: [[02_Systems/Analytics/README|02_Systems/Analytics]]

---

## Responsibility
The actual measurement output — retention data, performance reports, dashboards — as opposed to `02_Systems/Analytics/`, which holds the system/process that produces this output. See [[ADR-0001_Naming_Disambiguation]].

## Contents
- [[Hook_Database]] — hook outcomes per published story
- [[Ending_Database]] — ending/completion-rate outcomes per published story
- [[Retention_Database]] — part-to-part drop-off and mid-story retention
- [[Promotion_Candidates]] — the running queue between [[Knowledge_Promotion_Rules]]'s recommendations and [[Knowledge_Promotion]]'s actual pipeline

## Status
Sprint 012 built the structure — table schemas, cross-references to the capabilities and Analytics notes each database serves — with zero real entries in any of them. This is deliberate, not incomplete: no Reddit Story has actually been produced and published yet, so there's no real output to record. Populated as real reviews happen, per [[Review_Process]].

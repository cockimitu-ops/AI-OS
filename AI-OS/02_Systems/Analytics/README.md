# Analytics

Purpose: The system responsible for measurement, tracking, and reporting — HOW AI OS learns from completed work, not the completed-work data itself.
Last Updated: 2026-08-03
Status: Active — Sprint 012
Related Documents: [[02_Systems/README|02_Systems]], [[09_Analytics/README|09_Analytics]], [[Knowledge_Promotion]], [[Learning_Loop]]

---

## Responsibility
Defines how a completed project gets reviewed, how success/failure gets determined, how a learning gets extracted, and how a promotion gets recommended. Never performs the promotion itself — that's [[Knowledge_Promotion]]'s job. See [[Analytics_Philosophy]] for the full boundary.

## Contents
11 notes, condensed for density Sprint 022 (was 13, merged 3 review-cadence notes into 1):
- [[Analytics_Philosophy]], [[Metrics_Framework]], [[Success_Criteria]] — foundations
- [[Failure_Analysis]], [[Viral_Analysis]] — outcome analysis, negative and positive
- [[Experiment_Tracking]], [[Learning_Extraction]], [[Knowledge_Promotion_Rules]] — the learning pipeline
- [[Review_Process]], [[Review_Cadences]], [[Continuous_Improvement_Cycle]] — when review happens and how it closes the loop

## Relationship to 09_Analytics/
This folder defines the methodology. `09_Analytics/` holds the actual output — as of Sprint 012, that includes structured (but still empty) databases for hooks, endings, and retention, plus a promotion-candidates queue. See [[ADR-0001_Naming_Disambiguation]].

## Status
Sprint 012 complete, condensed Sprint 022. No real project has been reviewed against this framework yet — the output structures in `09_Analytics/` exist, with zero entries.

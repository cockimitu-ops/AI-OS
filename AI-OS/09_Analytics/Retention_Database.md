# Retention Database

Purpose: Accumulated record of mid-story retention performance across published Reddit Story productions — output, feeding Failure Analysis, Viral Analysis, and Knowledge Promotion.
Last Updated: 2026-08-03
Status: Active — no entries yet
Related Documents: [[09_Analytics/README|09_Analytics]], [[Retention_Beat_Scripting]], [[Cliffhanger_Creation]], [[Metrics_Framework]]
Required Notes: [[Metrics_Framework]], [[Retention_Beat_Scripting]], [[Cliffhanger_Creation]]

---

## What This Is
The output half of [[Retention_Beat_Scripting]]'s and [[Cliffhanger_Creation]]'s Analytics References — part-to-part drop-off and mid-script retention, not a methodology. Both capabilities feed the same database since they jointly own a story's body: Retention Beat Scripting paces it, Cliffhanger Creation closes each non-final part. Lives here, not `02_Systems/Analytics/`, per [[ADR-0001_Naming_Disambiguation]].

## Entries
| Story | Part | Drop-off Point | Outcome | Analysis |
|---|---|---|---|---|
| *(none yet)* | | | | |

## How Entries Get Added
A row is added per part as part of [[Review_Process]], once part-to-part viewer data is available. "Outcome" is a [[Metrics_Framework]] judgment; "Analysis" links to [[Failure_Analysis]] or [[Viral_Analysis]] where relevant.

## Feeds
Patterns here are [[Learning_Extraction]] material, filtered through [[Knowledge_Promotion_Rules]] before anything reaches [[Pacing]], [[Reader_Retention]], [[Retention_Beat_Scripting]], or [[Cliffhanger_Creation]] itself.

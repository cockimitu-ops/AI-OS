# Hook Database

Purpose: Accumulated record of hook performance across published Reddit Story productions — output, feeding Failure Analysis, Viral Analysis, and Knowledge Promotion.
Last Updated: 2026-08-03
Status: Active — no entries yet
Related Documents: [[09_Analytics/README|09_Analytics]], [[Hook_Writing]], [[Metrics_Framework]]
Required Notes: [[Metrics_Framework]], [[Hook_Writing]]

---

## What This Is
The output half of [[Hook_Writing]]'s Analytics Reference — a running table of actual hook outcomes, not a methodology (see `02_Systems/Analytics/` for that). Lives here, not there, per [[ADR-0001_Naming_Disambiguation]]: this folder holds output, that one holds process.

## Entries
| Story | Hook (summary) | First-Reveal Timing | Outcome | Analysis |
|---|---|---|---|---|
| *(none yet)* | | | | |

## How Entries Get Added
A row is added as part of [[Review_Process]], once a published story's actual retention data is available. "Outcome" is a [[Metrics_Framework]] judgment (met/missed the Success Criteria threshold); "Analysis" links to a [[Failure_Analysis]] or [[Viral_Analysis]] entry for a notable miss or standout, and stays blank for an unremarkable pass.

## Feeds
Patterns across multiple entries here are [[Learning_Extraction]] material, filtered through [[Knowledge_Promotion_Rules]] before anything gets promoted back into [[Hook_Principles]] or [[Hook_Writing]] itself.

# Review Process

Purpose: The recurring act of running completed work through Failure Analysis, Viral Analysis, Experiment Tracking, and Learning Extraction.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[02_Systems/Analytics/README|Analytics]], [[Analytics_Philosophy]], [[Review_Cadences]], [[Continuous_Improvement_Cycle]]
Required Notes: [[Failure_Analysis]], [[Viral_Analysis]], [[Experiment_Tracking]], [[Learning_Extraction]]

---

## Core Principles
- A review is the trigger, not the analysis itself. This note defines when and how a review happens; the actual analytical work is done by the notes it invokes.
- A review covers a defined set of completed work — a single project, or a time window (see [[Review_Cadences]]) — never "everything ever," to stay within `Context_Budget`.
- A review that finds nothing worth extracting is a complete, successful review. The process isn't judged by how much it produces per run.
- A metric that missed its threshold routes to [[Failure_Analysis]]; one that significantly exceeded it routes to [[Viral_Analysis]] — both, where relevant, get recorded as a row in the appropriate `09_Analytics/` database ([[Hook_Database]], [[Ending_Database]], or [[Retention_Database]]), not just referenced in passing.

## First Checkpoint for New Content
A story's first review checkpoint isn't governed by [[Review_Cadences]] — those are standing cadences for a body of existing work, not a rule for brand-new content. A single newly-published story gets one dedicated first look at 24–48 hours post-publish: early enough to catch a systemic problem before more gets built on the same broken pattern, late enough that the platform's initial algorithmic distribution pass has actually run. A second look at roughly one week catches whether it sustained or got a delayed second wave, which short-form platforms are known to give older content. Everything folds into the standing cadences once there's a real body of published work to review as a set.

## Inputs
A defined set of completed projects or experiments.

## Outputs
Zero or more entries into [[Failure_Analysis]], [[Viral_Analysis]], [[Experiment_Tracking]], or [[Learning_Extraction]] — and correspondingly, zero or more rows added to the relevant `09_Analytics/` database.

## Dependencies
[[Failure_Analysis]], [[Viral_Analysis]], [[Experiment_Tracking]], [[Learning_Extraction]] — a review invokes these as needed; it performs none of them itself.

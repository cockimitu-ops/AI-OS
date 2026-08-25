# Watermark / Tier Management

Purpose: Capability for tracking generation-tier status and the upgrade decision point.
Last Updated: 2026-08-07
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[AI_Video_Production]]
Required Notes: [[AI_Video_Production]]
Used By: [[AI_Video_Production]]

---

## What It Does
Tracks free-tier generation usage against the monthly cap and flags upgrade need, per [[AI_Video_Production]]'s tiering rules.

## Inputs / Outputs
In: generations used this month, current tier. Out: tier status, watermark status, upgrade recommendation.

## Success Criteria
Correctly tracks usage against the 10-generation cap; flags upgrade before the cap is exceeded, not after.

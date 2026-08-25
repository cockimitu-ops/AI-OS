# Cliffhanger Creation

Purpose: Capability for crafting the final lines of a non-final part specifically.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[Reddit_Story_Workflow]]
Required Notes: [[Reader_Retention]], [[Suspense_And_Curiosity]], [[Reddit_Story_Workflow]]
Used By: [[Reddit_Story_Workflow]], [[Reddit_Story_Production]] — Horror_Story_System/Production archived 2026-08-13, see 99_Archive/HorrorProject/

---

## What It Does
Writes the closing lines of any part except the last, applying [[Reader_Retention]]'s open-loop principle and [[Suspense_And_Curiosity]]'s escalation rule. Distinct from [[Retention_Beat_Scripting]], which paces the body of a part — this capability owns only its final moment.

## Inputs
A part's drafted body, from [[Retention_Beat_Scripting]], and confirmation it isn't the final part.

## Outputs
Closing lines that end the part on an unresolved loop.

## Production Note
The line itself isn't the whole delivery — a "follow for part 2" or similar CTA overlay that appears before the narrator finishes speaking cuts off the line's weight, even when the line itself is strong. Give the final words roughly half a second to land — a brief pause or quiet audio sting before the CTA overlay — rather than triggering it on the last word. Found by reviewing an actual rendered video, not something the script-level Success Criteria below can catch on their own.

## Success Criteria
The closing line raises a new question or escalates an existing one — it does not restate a question already asked earlier in the same part, per [[Suspense_And_Curiosity]]'s escalation-vs-repetition rule.

## Validation
Does the part actually end mid-tension, with no resolution language in the final lines? Any resolving phrase in a non-final part's ending fails.

## Analytics Reference
Part-to-part drop-off — viewers who don't continue to the next part — is a direct [[Metrics_Framework]] measurement of this capability's effectiveness specifically, once real series data exists; recorded in [[Retention_Database]].

## Knowledge Dependencies
[[Reader_Retention]], [[Suspense_And_Curiosity]].

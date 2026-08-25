# Horror Project (Archived)

Purpose: The horror content pillar — archived 2026-08-13, superseded by a new content engine built on a higher-CPM topic. Preserved, not deleted: the production methodology and the one real story produced are genuinely reusable if a future project needs horror-genre technique again.
Last Updated: 2026-08-13
Status: Archived
Related Documents: [[99_Archive/README|99_Archive]], [[10_Projects/SocialMediaContent/README|SocialMediaContent]]

---

## Why Archived
Research done for [[10_Projects/MoneyMaking/Candidate_Options|MoneyMaking]] was explicit early on: horror/entertainment as an audience doesn't monetize well, and the sector has the lowest 5-year survival rate of any German industry. The *production capability* built for it — hooks, retention scripting, CapCut formatting, the full shared pipeline — was never the problem and stays active in `03_Capabilities/`. Only the horror-specific system doc and its produced content are archived here.

## Contents
- `Horror_Story_System.md` — the system definition
- `Horror_Story_Production.md` — the production workflow instance
- `Stories/` — The Doorbell Camera, the one story actually produced under this system (fixes from its video review were never applied; it was never published)

## What Did NOT Move
- The 14 shared story-production capabilities — still active, still used by [[Reddit_Story_Workflow]], and available to whatever the new content engine needs.
- The Horror Knowledge notes (`02_Systems/Content/Knowledge/Horror/`) — reusable craft knowledge stays central per ADR-0005, regardless of whether an active project currently uses it. Not deleted, just currently unused.
- `Templates/Publishing_Checklist.md` — the template itself is genre-agnostic and stays with SocialMediaContent for reuse.

## What This Means Going Forward
`Content_Producer` (the agent) was scoped specifically to horror — rescoped 2026-08-13 to be genre-agnostic, since its actual job (running the shared story-production capability chain) never depended on the topic being horror.

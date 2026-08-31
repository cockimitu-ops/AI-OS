# Areas

Purpose: Which geographic areas `scripts/dmarc_prospector.py` pulls business domains from, via OpenStreetMap's Overpass API.
Last Updated: 2026-08-31
Status: Active
Stability: Dynamic
Related Documents: [[02_Systems/Automation/TaskRunner/prospects/README|Prospects]]

---

<!-- area: Crimmitschau + Zwickau -->
<!-- center: 50.8156,12.3906 -->
<!-- radius: 25 -->

<!-- area: Chemnitz -->
<!-- center: 50.8278,12.9214 -->
<!-- radius: 15 -->

<!-- area: Gera -->
<!-- center: 50.8809,12.0828 -->
<!-- radius: 15 -->

## Why these three
Crimmitschau alone is too small to sustain a prospect list — 20km around it already
pulled ~2,000 businesses, but the *qualified* fraction is what matters, and cold
outreach burns a list fast. Zwickau falls inside the first radius anyway.

Chemnitz and Gera are the two nearest real cities (~35km and ~30km), both reachable
by car for an on-site meeting, which is the closing advantage over a remote seller.
They are separate areas rather than one huge radius so each can be tuned or removed
independently.

Add an area by copying the three directives. `radius` is in km. Find coordinates by
right-clicking a spot on openstreetmap.org and reading them off the URL.

# Local Arbitrage

Purpose: Buy mispriced physical goods locally, resell at market price. Exploits information asymmetry (sellers who don't know what they have) and urgency discounts (Haushaltsauflösung, Umzug, "muss weg"). Car-enabled — the geographic radius is the moat.
Last Updated: 2026-08-31
Status: Active — scouting automated 2026-08-31; no capital deployed yet
Stability: Dynamic
Related Documents: [[10_Projects/README|10_Projects]], [[German_Legal_Basics]], [[Transaction_Log]], [[Valuation_Method]], [[Income_Portfolio]], [[02_Systems/Automation/TaskRunner/watches/README|Sniper Watches]]

---

## Why This Fits
Most people doing this are laptop-only and can't collect. A car turns "too far to bother" listings into reachable inventory, and urgency sellers specifically want *gone today* — which is a service, not just a discount. That combination is the actual edge, not the AI.

## The Loop
1. **Scout** — monitor Kleinanzeigen/eBay for urgency + ignorance signals. **Automated as of 2026-08-31:** the sniper at `02_Systems/Automation/TaskRunner/scripts/kleinanzeigen_sniper.py` polls the searches in its `watches/` folder every 3 minutes during waking hours and pushes matches to Telegram. Manual scouting is now the exception, not the loop.
2. **Value** — estimate resale from *sold* comps, not guesses (see [[Valuation_Method]])
3. **Negotiate** — reasonable offer, fast; don't burn 30 messages saving €5
4. **Inspect & buy** — verify in person before money moves
5. **Improve** — clean, test, identify exact model, photograph properly, write a real listing
6. **Sell & log** — every transaction into [[Transaction_Log]]

## Search Signals
`muss weg` · `dringend` · `keine Ahnung` · `Haushaltsauflösung` · `Umzug` · `zu verschenken` · `Wohnungsauflösung` · `Nachlass` · `VB` · badly-photographed lots · misspelled brand names (these don't show up in other buyers' searches)

## Target Categories
High value-density, testable quickly, fits in a car: power tools, monitors, gaming peripherals, cameras, audio equipment, bicycles, networking gear, small appliances, branded outdoor equipment, older/collectible electronics.

## Capital Plan (€250, revised 2026-08-31)
Revised up from €100 when the €250 budget was allocated here. The extra capital is not more flips — it is *bigger* flips: at €100 the reachable inventory is gaming peripherals and small electronics, where a good outcome is €30. At €250 monitors, power tools, and broken phones come into range, where a single flip clears €50–150 for the same per-flip overhead of driving, cleaning, photographing, and meeting a buyer.

- €150 inventory (incl. the broken-phone loop — see below)
- €60 fuel/transport
- €40 cleaning/testing/misc
- **€0 on AI subscriptions until the operation has paid for them**

Target progression: €250 → €340 → €450 → €600 — compounding, not one lucky flip.

## The broken-phone sub-loop (added 2026-08-31)
Buy soft-bricked/bootlooping Androids and iPhones at €10–60, unbrick via fastboot/Odin/EDL, wipe, resell at €80–150. The edge is specifically that a rooted-phone background makes a "defekt" listing readable as a 20-minute fix rather than as scrap — an information asymmetry ordinary flippers don't have, which is the same premise as the rest of this project applied to a category most buyers skip.

**Hard rule, not a preference:** never buy a device with an active Google/FRP or iCloud activation lock from a stranger. It is unsellable, and it is the single clearest stolen-device signal in this market. The `iphone_defekt` watch excludes lock phrases so these never even arrive as alerts.

## Honest Economics
A €50-profit flip is realistically 2–4 hours end-to-end (drive, inspect, buy, clean, test, photograph, list, message buyers, meet again to sell). That's roughly €15–25/hour — genuinely better than the Fiverr gig's effective rate, but it is **not passive**, and it's capped by your time and by how deep the local market is. The compounding is in the capital and the data, not the hours.

## What Actually Compounds
[[Transaction_Log]]. After 30–50 completed flips you own something no AI can hand you: a *local* pricing dataset for your specific radius. That's the part matching the build-once-benefit-repeatedly goal — the flips are labor, the dataset is the asset.

## Practical Safety
Meet in public or bring someone for high-value pickups. Cash only, count before handing over. Test electronics before paying, not after. Trust the instinct that says leave — a lost €40 opportunity costs less than any alternative.

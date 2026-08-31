# Income Portfolio

Purpose: The actual multi-stream income strategy — what to build, in what order, and why. Prioritizes build-once-sell-repeatedly products, with service income as the funding layer underneath.
Last Updated: 2026-08-31
Status: Active — sequence revised 2026-08-31; sniper shipped, nothing sold yet
Stability: Dynamic
Related Documents: [[10_Projects/MoneyMaking/README|MoneyMaking]], [[Candidate_Options]], [[10_Projects/TemplateSales/README|TemplateSales]], [[10_Projects/QuickTurnaroundGigs/README|QuickTurnaroundGigs]]

---

## The One Insight This Whole Strategy Rests On
Across every 2026 source on template selling, the same finding repeats: **the median seller with one template and no distribution earns close to nothing.** Product quality is not the bottleneck — distribution is. Most people who fail at "passive income" build a good product and have no way for anyone to find it.

That matters here specifically because **TikTok is the #1 discovery channel for Notion templates in 2026**, and a documented short-form content production pipeline already exists in [[10_Projects/SocialMediaContent/README|SocialMediaContent]] — capabilities for hooks, retention scripting, CapCut formatting, multi-platform captions. The horror *audience* doesn't monetize well (established in earlier research), but the *production capability* is exactly the missing piece for template sales.

This is the asset nobody else in the template market reliably has. Everything below is built around it.

## Honest Expectations, Not Hype
- Realistic range: **$0–3,000/month for sellers who build consistently over 6–12 months.** Not month one.
- A realistic first-year target: **5–10 templates earning $200–300/month each.** Not one viral product.
- "Passive" is misleading — it's front-loaded build plus ongoing marketing. The income is leveraged, not effortless.
- Price at **$19–29 minimum.** $5 templates reportedly don't build real income; they attract the wrong buyers and cap ceiling.
- Pick **two** distribution channels and do them consistently. Five channels done inconsistently loses to two done well.

---

## Tier 1 — Build Once, Sell Repeatedly (priority)

### 1a. The AI OS as a product
The most differentiated thing available. Not another pretty dashboard — a documented system with real architecture: Context Engine, Execution Engine, capability/workflow separation, ADRs recording actual design decisions. Most "second brain" templates are aesthetic; this one has reasoning behind every structural choice.
- **Sell the pattern, not the instance** — strip all personal/project content, ship the framework.
- Natural companion product: a written breakdown of *why* it's structured this way. That's the part competitors can't copy from a screenshot.
- Price tier: premium end ($29–49), because it's a system, not a page.

### 1b. German-language Notion templates
Earlier research found English generic templates (planners, "Second Brain") are oversaturated while **German-language niches are barely covered**. Niche focus — not quality — is repeatedly named as the deciding factor between sellers who earn and sellers who don't.
- Candidates: Bewerbungsvorlagen (job application tracker), Ausbildungs-/Studienplaner, Kleinunternehmer bookkeeping tracker, Werkstudent/Nebenjob finance tracker.
- Native German is a real moat here against the mostly-English creator market.

### 1c. n8n workflow packs
Adjacent, established product category, and the skill already exists. Lower priority than 1a/1b until one of those is actually shipping — three simultaneous product lines with zero shipped products is the failure mode to avoid.

## Tier 1.5 — Capital-Compounding (added 2026-08-13)
**[[10_Projects/LocalArbitrage/README|LocalArbitrage]]** — buying mispriced physical goods and reselling. Doesn't fit the build-once-sell-repeatedly frame (each flip is real labor), but it's the only stream here that compounds *capital* rather than requiring traffic, and it produces cash fastest. Its build-once component is [[Transaction_Log]]: after 30–50 flips, a local pricing dataset that makes every later flip faster. Realistic ~€15–25/hour, capped by time and local market depth.

Notably, it has **no distribution problem** — unlike templates, buyers are already searching. That makes it the natural funding layer for Tier 1, which needs time before it earns.

## Tier 2 — Service Income (funds Tier 1)

### 2a. Fiverr research gig
Nearly live. Real economics, stated honestly: ~$24 take-home on Basic, and the Omni Shield test showed round-trip overhead makes the effective hourly rate modest. **Its value is proof and reviews, not income** — treat the first five orders as marketing spend. Reviews here are what make Tier 3 credible.

### 2b. ContentAgency retainers
Highest ceiling of anything here (one client at €500–800/month recurring beats dozens of one-off gigs), but gated on sales skill that hasn't been practiced yet. Comes after 2a produces a track record.

---

## Sequence (the part that matters)
1. **Ship the Fiverr gig.** It's 95% done. Finishing it costs almost nothing and starts the review clock.
2. **Build ONE template — the AI OS pattern.** Not three. One, shipped, on Gumroad or Payhip.
3. **Make 3 TikToks/Reels demoing it.** Screen recordings of the template solving a problem. This is the step almost everyone skips, and it's the one that decides whether anything sells.
4. **Only then** add template #2, and repeat.

The failure mode to actively avoid: building five products and marketing none. Given how much of this vault is infrastructure that hasn't shipped yet, that's the realistic risk, not lack of ideas.

## Platforms and Fees
Gumroad (10%), Payhip (5% on free plan), Notion Marketplace (10% + $0.40, best discovery), Etsy (6.5% + $0.20 listing). Common approach: list on Notion Marketplace for discovery, run checkout through Gumroad or Payhip for margin.

## Status
Strategy set. Nothing shipped. The next real milestone is a single product live on a single storefront — not another plan.

---

## Sequence revised 2026-08-31
An options review (server + laptop + phones + €250) produced 26 candidates. Felix picked four and ordered them himself. Recording the order and the *reasoning*, because the order is the decision — the individual ideas were the easy part.

**1. Sniper-fed side hustle (now).** [[10_Projects/LocalArbitrage/README|LocalArbitrage]] plus a broken-phone sub-loop, both fed by the Kleinanzeigen sniper built the same day. Chosen first because it is the only stream here with **no distribution problem** — buyers are already searching — which is precisely the bottleneck this document's opening insight says kills everything else. It produces cash while the other two legs are still unearning.

**2. DMARC/SPF remediation for Mittelstand (next).** Passive DNS checks only, no scanning, no legal exposure; €150–300 per fix. Deferred behind the sniper deliberately: it is the higher ceiling but needs sales conversations, and the sniper needs none.

**3. German-language security content (once money is coming in).** Fills the pillar left empty since the horror archival — with the one subject Felix is about to spend three years becoming credible in. Monetised as **lead-gen for leg 2**, not as ad revenue. That is the correction to the horror mistake: the earlier finding was never "content doesn't work," it was that the *audience* didn't monetise.

**Explicitly deferred, not rejected:** bug bounty and CTFs. Correctly identified by Felix as learning, not income — realistic first-year bounty earnings for a beginner are ~€0. They resume as skill-building once leg 1 pays, and they are what makes leg 2 credible at 20 rather than 19.

### The constraint that shaped the whole order
Familienversicherung dies above **€565/month** (see [[German_Legal_Basics]]), costing ~€150/month — so income between €565 and ~€715 is strictly *worse* than €560. Every leg above is therefore chosen for high €/hour at low hours, not for volume. Blowing through that ceiling should be a deliberate decision with the numbers checked in writing with the Krankenkasse first, not something a good month does by accident.

Second, quieter constraint: the cybersecurity degree starts September 2026. Time, not money, becomes the scarce input within weeks — which is the real argument for leg 1 being a *machine* that pings a phone rather than a habit requiring daily browser refreshing.

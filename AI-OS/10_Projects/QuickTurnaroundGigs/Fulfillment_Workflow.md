# Fulfillment Workflow

Purpose: The actual repeatable process for delivering [[Research_And_Briefing_Gigs]]'s three startup-competitor-analysis packages. Rebuilt Sprint 023 for the startup-focused pivot — deeper, multi-step research replaces the old single-prompt-per-tier process.
Last Updated: 2026-08-08
Status: Active — process defined, not yet run on a real order
Related Documents: [[10_Projects/QuickTurnaroundGigs/README|QuickTurnaroundGigs]], [[Research_And_Briefing_Gigs]]

---

## The Collaboration Loop
This is the actual per-order workflow, every time:
1. **You paste the buyer's answers** to the 5 requirement questions (startup description, target customer, known competitors, goal, region).
2. **I generate the specific Perplexity prompts** for that order — which steps below actually apply depends on the tier and whether competitors were already named.
3. **You run them in Perplexity and paste the raw output back.**
4. **I structure it into the finished report**, per the structure below, ready to deliver.

Nothing here is a static template to fill in alone — each order gets prompts built from that buyer's actual answers, not generic placeholders.

## Take-Home Math (Fiverr keeps 20%)
| Package | Listed Price | Take-Home | Target Time | Effective Rate |
|---|---|---|---|---|
| Basic (3 competitors) | $30 | $24 | ~60–90 min | ~$16–24/hr |
| Standard (5 competitors) | $80 | $64 | ~2–3 hr | ~$21–32/hr |
| Premium (7–10 competitors) | $180 | $144 | ~3–5 hr | ~$29–48/hr |

Premium scales best — worth steering repeat buyers there once there's a track record. Basic is the loss-leader for first reviews, not the target margin.

**Honest flag from the Omni Shield test (Sprint 023):** these targets assume smooth execution. The actual test — roughly Basic-tier scope (3 competitors + comparison + SWOT) — took multiple real round-trips between Perplexity and Claude, each with copy/paste and wait time on top of the thinking time. The time budget above is optimistic until it's been checked against a real order; don't assume it's accurate yet.

---

## Step 1 — Identify Competitors (only if the buyer didn't name any)
```
Who are the main competitors of a startup that [DESCRIPTION] targeting [TARGET CUSTOMER] in [REGION] as of 2026? List at least 10 companies, and for each include: name and website, one-sentence description, whether they're a direct, indirect, or aspirational competitor. Cite sources.
```
Then narrow to the package's competitor count:
```
From this list, which [N] are the most relevant competitors for an early-stage startup with limited budget? Prioritize similar ICP and pricing level. Explain why.
```

## Step 2 — Profile Each Competitor
Run once per competitor, or batch up to 2 at a time in one message — tested Sprint 023: batching 3 kept genuine depth but truncated the last competitor's Weaknesses/Recent Moves sections. 2 is the safe ceiling at this level of detail; if a batch of 3+ truncates, re-run just the cut-off sections for the affected competitor rather than the whole profile.
```
Research [COMPETITOR NAME, URL] as of 2026 and create a detailed profile for a startup founder audience. Include: company overview (founding year, location, stage, funding if public), core product/features, target customer and positioning, pricing model and tiers, main marketing channels, strengths and weaknesses based on reviews (G2, Capterra, Reddit, Trustpilot), and recent strategic moves in the last 6–12 months. Cite all sources.
```
Optional depth add-on:
```
Summarize what customers complain about most regarding [COMPETITOR]. Focus on 2–3 star reviews from G2, Capterra, Reddit, and similar sites. List recurring themes with examples and sources.
```
Observed Sprint 023: Perplexity sometimes appends an unprompted strategic-implications section after a batch of profiles — genuinely useful, but don't rely on it appearing; Step 4 still needs to be run explicitly.

## Step 3 — Comparison Tables and SWOT
```
Create a comparison table for these competitors: [LIST]. Compare: target customer, core product and key features (10–15 max, only what matters to customers), pricing model, key differentiators claimed, main weaknesses from customer feedback. Cite sources where possible.
```
```
Based on all previous research, create a SWOT analysis for each competitor: [LIST]. Use 3–5 bullets per quadrant.
```
Observed Sprint 023: when run with the client's context already in the conversation, this sometimes frames Opportunities/Threats from the client's own perspective, not generic competitor SWOT — doing part of Step 4's job unprompted. Worth checking each order's SWOT output before assuming Step 4 needs to run in full.

## Step 4 — Gaps and Opportunities
```
Based on the customer complaints and weaknesses of [COMPETITORS], what are the biggest unmet needs in this market right now? Pull from Reddit, G2, Trustpilot, and industry publications. Cite every source.
```
```
Given these unmet needs and a startup described as [DESCRIPTION], what are 5 specific opportunities they could pursue to differentiate? Focus on positioning, pricing, features, and messaging. Be concrete.
```

## Step 5 — Investor Insights (Standard/Premium only)
```
For each competitor, find any public information on funding, investors, and growth signals (Crunchbase, press releases, LinkedIn, news). Summarize in a table with sources.
```
```
How should this startup talk about competition in an investor pitch deck? Provide: a 2–3 sentence "competitive landscape" narrative, a 4–5 bullet "why we win vs. [top 3 competitors]" section, and a suggested 2x2 positioning map (describe axes and where each competitor sits).
```

## Step 6 — Report Structure (what I build from the raw research)
1. Executive Summary (1 page) — key findings, top 3–5 recommendations
2. Market & Competitor Landscape (1–2 pages)
3. Competitor Profiles (2–3 pages each)
4. Comparison Tables — features, pricing, positioning
5. SWOT Analyses — one per competitor
6. Opportunities & Strategic Recommendations (2–3 pages)
7. Investor Deck Notes (Premium only, 1–2 pages)
8. Appendix — sources and methodology

---

## QA Before Delivery
Same discipline as before: spot-check 2–3 specific claims against their cited source directly, confirm length/format match the tier, read once for tone.

## Not Yet Done
Test run with an imaginary company (Omni Shield, WiFi security for doctors' offices/homeowners/SMBs) validated Steps 1–3 and 6 end-to-end — stopped deliberately at 3 of 8 competitors once the loop itself was proven, rather than completing a fake deliverable. Real finding: round-trip overhead between Perplexity and Claude makes the time budget above optimistic until checked against an actual paid order. No real order has run through this process yet.

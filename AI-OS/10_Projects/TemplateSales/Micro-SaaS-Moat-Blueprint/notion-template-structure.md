# Micro-SaaS Moat Blueprint — Notion Template Structure

How to use this file: create one Notion page called "Micro-SaaS Moat Blueprint,"
then create the 6 modules below as sub-pages (or toggle sections). Each module
has a purpose line, a fillable table/checklist, and a ready-to-paste AI prompt.
Once built, duplicate the whole page as your Gumroad master template.

---

## Cover Page

**Micro-SaaS Moat Blueprint**
Turn competitor gaps into a validated feature roadmap — in about 60 minutes.

> Duplicate this template. Work through modules 1–6 in order. Each module
> builds on the last. By the end you'll have a prioritized roadmap and a
> defensibility score for your idea, backed by real competitor data.

Tools needed: any AI assistant that can browse the web (Perplexity, ChatGPT
with search, Claude, Gemini). No paid tools required — the free tier of any
of these works.

Progress tracker: ☐ Module 1 ☐ Module 2 ☐ Module 3 ☐ Module 4 ☐ Module 5 ☐ Module 6

---

## Module 1 — Competitor Discovery

**Purpose:** Find everyone already serving this niche, not just the 2–3 names
you already know.

**Table: Competitor Long List**

| Name | URL | Found via | First impression |
|---|---|---|---|
| | | | |

**Prompt (paste into your AI assistant):**
```
I'm evaluating a micro-SaaS idea: [describe your idea in 1-2 sentences].

Find every existing product that competes for the same buyer's budget —
direct competitors (same solution), indirect competitors (different
solution, same problem), and adjacent tools users currently duct-tape
together instead. Include small/indie tools, not just the market leaders.

For each one give: name, one-line description, pricing model, and how you
found it (search term, directory, forum mention).
```

Target: 8–15 names before moving to Module 2. Fewer than 8 usually means the
search wasn't broad enough, not that the niche is empty.

---

## Module 2 — Competitor Teardown

**Purpose:** Go deep on the 3–5 competitors who actually matter — closest
positioning, most traction, or most similar pricing.

**Table: Teardown (repeat per competitor)**

| Field | Notes |
|---|---|
| Positioning (their own words) | |
| Pricing tiers | |
| Core feature set | |
| Who they clearly target | |
| Recent changes (launches, pricing shifts) | |
| Public complaints (reviews, Reddit, Twitter) | |

**Prompt:**
```
Research [competitor name] in depth. I need:
1. Their exact pricing tiers and what's gated behind each
2. Their core feature list, grouped by category
3. Who their marketing/positioning is clearly built for
4. Any recent product or pricing changes in the last 6 months
5. Public complaints — search their name plus "alternative," "vs," 
   "sucks," or check G2/Reddit/Twitter for recurring frustrations

Cite where each finding comes from.
```

---

## Module 3 — Feature Parity Matrix

**Purpose:** See at a glance who has what, so gaps become visible instead of buried in text.

**Table: Feature Matrix**

| Feature | You (planned) | Competitor A | Competitor B | Competitor C |
|---|---|---|---|---|
| | | | | |

Fill rows with every feature that appeared across Module 2 research, even
ones you don't plan to build. The empty cells are the interesting part.

---

## Module 4 — Gap & Wedge Finder

**Purpose:** Turn the matrix into an actual opportunity, not just a list of missing checkboxes.

**Prompt:**
```
Here is a feature comparison matrix for [niche] tools: [paste Module 3 table].

Identify:
1. Gaps that are unserved because building them is hard (real moat if I solve it)
2. Gaps that are unserved because nobody asked yet (validate before building)
3. Gaps that are unserved because they're genuinely low-value (skip these)

For each real gap, name the specific buyer segment who'd care most.
```

**Table: Ranked Gaps**

| Gap | Why it's unserved | Buyer segment | Build difficulty |
|---|---|---|---|
| | | | |

---

## Module 5 — Moat Scoring

**Purpose:** Before building, score whether the gap is defensible or just a
head start someone copies in a month.

**Scorecard (1–5 each):**

| Moat factor | Score | Notes |
|---|---|---|
| Data moat — gets better with more usage/user data | | |
| Network effects — more valuable as more people use it | | |
| Switching cost — painful for users to leave once adopted | | |
| Distribution advantage — you already reach this buyer | | |
| Technical complexity — genuinely hard to clone quickly | | |

**Total: __ / 25**

Under 10: this is a feature, not a company — fine for a quick Gumroad-style
sale, risky as a subscription business.
10–17: viable niche SaaS, expect competition within 6–12 months, plan for it.
18+: worth the build time — defensibility compounds instead of eroding.

---

## Module 6 — Validated Roadmap Output

**Purpose:** Convert everything above into something you can actually act on this week.

**Prompt:**
```
Based on this research: [paste Modules 1-5 summary]

Write a prioritized v1 feature roadmap. For each feature, give:
- One-sentence user story
- Why it's prioritized where it is (tie back to the gap/moat analysis)
- Rough build effort: small / medium / large

Then write a 3-sentence positioning statement I could put on a landing page,
based on the actual gap found — not generic startup language.
```

**Output checklist before you close this template:**
- ☐ Prioritized feature list (not a wish list — ordered)
- ☐ One clear positioning statement
- ☐ Moat score recorded
- ☐ A named buyer segment, not "everyone who needs X"

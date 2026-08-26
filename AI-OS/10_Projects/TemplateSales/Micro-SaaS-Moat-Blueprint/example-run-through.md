# Example Run-Through — "AI LinkedIn Content Tool for Indie Hackers"

This is a real, researched example of the 6-module process, using actual
market data pulled in August 2026. Use this to show buyers what the output
looks like before they run their own idea through it.

**The idea being tested:** an AI tool that writes LinkedIn build-in-public
posts for solo SaaS founders — but instead of a generic "voice profile,"
it pulls directly from the founder's GitHub commits and Stripe/revenue data.

---

## Module 1 — Competitor Discovery

12 tools found searching "AI LinkedIn content tools 2026" and "AI LinkedIn
tools for founders":

| Name | Positioning (one line) | Pricing model |
|---|---|---|
| Taplio | AI post generator + viral post library + lead gen | $39–199/mo, tiered |
| AuthoredUp | Formatting/editor + analytics, no AI writing | $19.95/mo |
| Supergrow | AI-first, voice-trained, interview-to-post | $19–39/mo |
| Oiti | "AI Clone" persona + long-term memory + knowledge base | $49–79/mo |
| Podawaa | All-in-one: writing, scheduling, comment boosting | Not confirmed |
| ViralBrain | Content ideas + engagement benchmarking | Not confirmed |
| Kleo | Knowledge-base-driven drafting | $99/mo, no trial |
| Scripe | Voice memo / interview-based drafting | €69–149/mo |
| MagicPost | Cheap AI writer, free-to-start | Freemium |
| EasyGen | Fast AI drafting, trend feed | Freemium |
| Typegrow | Visual/carousel-focused | Free / $29/mo |
| Postbeam | Team-focused, employee advocacy | $39–49/mo/seat |

**Note on this list:** several of the review sites behind these numbers are
publishing comparisons that consistently rank their own product #1
(ghostwriting-ai.com is Oiti's own blog, for instance). Treat any single
source's ranking with suspicion — cross-check pricing and features against
at least two independent sources before trusting a claim. This applies to
your own research too, not just this example.

---

## Module 2 — Competitor Teardown

Four closest competitors, gone deep:

**Taplio**
- Pricing: $39/mo Starter (scheduling only, zero AI credits), $69/mo Growth (250 AI credits), $199/mo Pro (unlimited AI + lead database + outbound automation)
- Core bet: a 5-million-post viral library plus AI drafting tools, positioned as an all-in-one for LinkedIn-driven sales pipeline
- Complaints: Trustpilot rating sits around 2.1–2.4/5, with the majority of reviews citing billing issues — subscriptions charging after cancellation, no renewal notice. Separately, the advertised $39 entry price is criticized as a bait: the AI writing features people actually buy Taplio for are gated behind the $69 tier.

**AuthoredUp**
- Pricing: $19.95/mo individual, $14.95/user/mo team
- Core bet: the best formatting/preview editor in the category, deep analytics, but deliberately no AI content generation
- Complaints: occasional paste glitches (special characters/line breaks shift when copying to LinkedIn). Users report running a 3-tool stack — a separate AI writer, AuthoredUp for formatting, sometimes a third analytics tool — because AuthoredUp only solves one piece.

**Supergrow**
- Pricing: $19/mo Starter, $39/mo Pro (unlocks carousel maker + full analytics)
- Core bet: AI-first drafting from a "Content DNA" voice profile, plus a feature that turns a spoken interview into multiple posts
- Complaints: analytics is described as the weak point compared to AuthoredUp's dedicated analytics layer; the carousel maker being locked behind the $39 tier is a recurring gripe.

**Oiti**
- Pricing: $49/mo Creator (1 persona, 1GB knowledge base), $79/mo Pro (multiple personas, unlimited knowledge base)
- Core bet: the differentiator across nearly every independent comparison found is that it keeps long-term memory of corrections and lets you upload real source material (PDFs, past posts, competitor content) that grounds every draft — versus tools that read your last 20 posts once and never update.
- Caveat: as noted in Module 1, much of Oiti's #1 ranking comes from its own blog. The underlying claim (memory + knowledge base beats a one-time voice snapshot) shows up independently across several other reviewers too, so the mechanism seems real even where the ranking is self-serving.

---

## Module 3 — Feature Parity Matrix

| Feature | Our idea (planned) | Taplio | AuthoredUp | Supergrow | Oiti |
|---|---|---|---|---|---|
| AI post generation | Yes | Yes (from $69) | No | Yes | Yes |
| Grounds in founder's own voice | Yes | Generic | N/A (manual) | Voice-trained | Yes, deepest |
| Grounds in real product data (commits, revenue) | **Yes — unique** | No | No | No | No (generic KB only) |
| Long-term memory across sessions | Yes | No | No | No | Yes |
| Scheduling | Yes | Yes | Yes | Yes | Yes |
| Entry price | — | $39 (no AI) | $19.95 | $19 | $49 |

---

## Module 4 — Gap & Wedge Finder

**The gap:** every competitor's "grounding" data is generic — uploaded PDFs,
past posts, articles someone else wrote. None of them connect to the actual
artifacts a solo SaaS founder produces every week: commits, changelog
entries, a Stripe MRR screenshot. Founders currently do that translation
by hand — open GitHub, remember what shipped, write a post about it.

**Why it's unserved, not just unnoticed:** it requires real integration
work (GitHub API, Stripe API) that a general-purpose "LinkedIn tool for
founders" has no reason to build, because most of their buyers (coaches,
consultants, sales reps) don't have commits or MRR to pull from in the
first place.

**Buyer segment:** solo indie hackers / micro-SaaS builders doing
"build in public" — an identifiable, active community (r/SaaS,
r/indiehackers, Indie Hackers itself, #buildinpublic on X).

**Build difficulty:** medium. The AI-writing layer is commoditized — every
competitor above already has it. The actual work is the data pipeline
(GitHub + Stripe integration), which is also where the defensibility lives.

---

## Module 5 — Moat Scoring

| Moat factor | Score | Notes |
|---|---|---|
| Data moat | 4/5 | Compounds with every commit/revenue event pulled in — genuinely hard for a generic competitor to replicate without building the same integrations |
| Network effects | 1/5 | None. Single-player tool, no shared or marketplace layer |
| Switching cost | 3/5 | Losing months of accumulated build-in-public history and voice tuning hurts, but a data export softens it |
| Distribution advantage | 2/5 | No existing reach into the indie-hacker LinkedIn crowd specifically — would need to be built from zero |
| Technical complexity | 3/5 | GitHub/Stripe API integration plus an LLM layer — buildable solo in weeks, not defensible on difficulty alone |

**Total: 13/25** — viable niche SaaS. Expect a competitor to notice and
copy the angle within 6–12 months once it gets any traction; the data moat
(factor 1) is the piece worth protecting and deepening first, since it's
the only score above a 3.

This is a realistic score, not an inflated one — worth pointing out to
buyers directly, since a template that scores every idea 20+/25 isn't
doing real evaluation.

---

## Module 6 — Validated Roadmap Output

**v1 feature list, prioritized:**

1. **GitHub commit → post draft.** User story: "As a solo founder, I want a
   LinkedIn draft generated from what I actually shipped this week."
   Priority: highest — this is the entire wedge. Effort: medium.
2. **Stripe MRR milestone → post template.** "I want a ready post when I
   cross a revenue milestone." Effort: small, high emotional payoff for
   the build-in-public audience.
3. **Voice tuning from the founder's own past posts.** Table-stakes vs.
   every competitor above. Effort: medium.
4. **Scheduling + basic analytics.** Must-have parity feature, not a
   differentiator. Effort: medium.
5. *(v2, not v1)* Multi-platform export to X/Twitter.

**Positioning statement:**
Every AI LinkedIn tool asks you to explain your work in a text box.
This one reads it straight from your commits and your Stripe dashboard.
Built for indie hackers who'd rather ship than write.

---

## What this demonstrates

The template didn't produce a "yes, build it" verdict — it produced a
13/25, a named risk (no network effects, no distribution yet), and a
specific next action (protect the data moat first). That's the point: a
real research process outputs a decision with tradeoffs attached, not a
green light.

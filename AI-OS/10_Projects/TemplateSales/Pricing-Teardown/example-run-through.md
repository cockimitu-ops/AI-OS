# Example Run-Through — Pricing an AI LinkedIn Tool

A real run of all six modules, using market data gathered August 2026.

**Continuity note:** this is the same product idea used as the worked example
in the Micro-SaaS Moat Blueprint — an AI tool that writes LinkedIn
build-in-public posts from a founder's actual GitHub commits and Stripe
revenue. There it scored 13/25 on defensibility. Here we price it. If you own
both templates, you're watching one case study develop.

---

## Module 1 — Price Mapping

| Competitor | Entry | Mid | Top | What's gated | Public pricing |
|---|---|---|---|---|---|
| AuthoredUp | $19.95 | $14.95/user (team) | — | No AI at any tier — formatting/analytics only | Yes |
| Supergrow | $19 | $39 | — | Carousel maker + full analytics behind $39 | Yes |
| Taplio | $39 | $69 | $199 | **AI credits gated above entry**; lead database at top | Yes |
| Oiti | $49 | $79 | — | Personas, multi-account, unlimited KB above entry | Yes |
| Kleo | $99 | — | — | Nothing — single tier, no trial | Yes |
| Scripe | €69 | €149 | — | Account count | Yes |

**What the gating pattern reveals:**

The most telling data point is Taplio's. Its advertised $39 entry tier
contains **zero AI credits** — the AI writing everyone buys Taplio for starts
at $69. This is a recurring complaint in reviews, and Taplio's Trustpilot
rating sits around 2.1–2.4/5 with most negative reviews citing billing
problems.

That's a gating decision producing measurable brand damage. Useful lesson:
gating the feature that *defines* your product is the one exclusion buyers
won't forgive.

Second pattern: nobody gates the core writing function except Taplio.
Supergrow and Oiti both include AI generation at entry and gate *scale*
(personas, accounts, storage) instead. That's the market's answer to where
the upgrade pressure should come from.

Third: everybody publishes pricing. No demo-call walls. This is a
self-serve category, and hiding prices would read as enterprise
positioning the buyer isn't looking for.

---

## Module 2 — Value Metric Discovery

| Candidate metric | Scales with value | Buyer predicts it | Grows with success | Cheap to measure | Biggest risk |
|---|---|---|---|---|---|
| Per seat | Weak — it's a solo tool | Yes | No | Yes | Buyer is one person; no expansion path |
| Posts generated/month | Moderate | Yes | Somewhat | Yes | Caps discourage the habit you want to build |
| Connected repos | **Strong** | Yes | Yes | Yes | Most indie hackers have 1–2 repos; slow ladder |
| AI credits | Weak | **No** | No | Yes | Bill shock; buyer can't estimate before billing |
| Connected accounts | Moderate | Yes | Yes | Yes | Only expands for agencies, not the target buyer |

**Ranking:** connected repos > posts/month > seats > accounts > credits.

**The finding:** for this product, no single metric is strong. Connected repos
is the best fit conceptually — it scales with a founder shipping more — but
most indie hackers run one or two repos, so the expansion ladder is short.

**Market context that matters here:** pure per-seat pricing has collapsed to
roughly 8% of the SaaS market. Hybrid — a base subscription plus a metered
layer — is now the most common structure at around 37%, with usage-based at
38% adoption, up from 27% in 2023. The reason is directly relevant: AI
severs the link between value and headcount. A single founder running an AI
tool can generate value that a per-seat model simply can't capture.

**Decision:** flat rate at launch, single tier. Not because flat rate is
optimal, but because the honest answer is that no metric here has a strong
expansion ladder, and adding metering infrastructure before knowing which
metric matters is premature. Revisit at 50 customers.

**Note the discipline:** the "correct" 2026 answer would be hybrid. It's the
wrong answer for a pre-launch solo product with no usage data, and the
template's job is to make you notice when best practice doesn't apply to
your situation yet.

---

## Module 3 — Willingness to Pay

**What this buyer already pays for:**

| Adjacent spend | Typical price | Considered good value? |
|---|---|---|
| GitHub Copilot | ~$10–19/mo | Yes, widely |
| Hosting (Vercel/Railway/Fly) | $20–50/mo | Yes, accepted cost |
| AI assistant subscription | $20/mo | Yes |
| Existing LinkedIn tool | $19–49/mo | **Mixed** |
| Domain + email | ~$10/mo | Yes |

Rough existing stack: **$80–150/mo** in tooling. There's a proven budget here
— this buyer already pays for software monthly and doesn't need convincing
that tools cost money.

**Pricing complaints found:**
- Taplio's entry tier criticised directly as a bait — the AI features people
  actually want start one tier up.
- Recurring Taplio billing complaints: subscriptions charging after
  cancellation, no renewal notice.
- Supergrow's carousel maker being locked behind the $39 tier is a repeated
  gripe.
- AuthoredUp users report running a three-tool stack because it deliberately
  does one thing — the complaint is about *needing more tools*, not price.

**Ceiling and floor:** the floor is around $19 (AuthoredUp/Supergrow entry —
below that the buyer assumes hobby project). The ceiling for an unproven solo
product is around $49 — Oiti's entry — because above that you're competing
with Kleo's $99 without Kleo's track record.

**Most valuable single finding:** AuthoredUp's complaint pattern. Users
aren't angry about the price, they're annoyed at running three tools. That's
a consolidation opportunity, not a pricing one — worth noting for the
roadmap.

---

## Module 4 — Tier Architecture

Given Module 2's conclusion — no strong expansion metric yet — the structure
is deliberately minimal:

| Tier | Price | For whom | Included | Excluded, and why | Upgrade trigger |
|---|---|---|---|---|---|
| **Free** | $0 | Trying it | 3 posts/mo, 1 repo | Scheduling, Stripe integration — these are habit features, and habit is what you're charging for | Wanting to post weekly |
| **Builder** | $29/mo | The target buyer | Unlimited posts, unlimited repos, Stripe integration, scheduling | Nothing meaningful | — |

**Two tiers, one paid.** Justification: with no proven expansion metric,
a second paid tier would be inventing a distinction the buyer hasn't asked
for. Taplio's example shows what happens when you gate the defining feature
to manufacture an upgrade.

**What's wrong with this structure** (asked explicitly, as the module
instructs):

1. **No expansion revenue.** Every customer is worth exactly $29/mo forever.
   With ~$150/mo tool budgets in this segment, that's leaving money on the
   table for power users — but there's no evidence yet about who they are.
2. **The free tier may cannibalise.** Three posts a month might be enough
   for someone posting occasionally, which is a meaningful slice of the
   target buyer.
3. **$29 sits in a crowded band** — Supergrow at $19 and $39 brackets it
   directly. Being between two competitors' tiers is the least
   differentiated place to sit.

Point 3 is the one to take seriously, and it feeds directly into Module 5.

---

## Module 5 — Anchoring and Signal

**Position:** $29 sits mid-market. Above AuthoredUp ($19.95) and Supergrow
entry ($19), below Taplio's real AI tier ($69) and Oiti ($49).

**What it claims:** "more capable than the cheap formatters, less
established than the premium tools." Backable — that's accurate.

**If cheapest** (dropping to $19): buyers would assume it's another thin
wrapper. This category is full of them, and the whole differentiator here is
integration depth — pricing at wrapper level actively undercuts the
positioning claim.

**If most expensive** (moving to $59+): the justification would have to be
that GitHub and Stripe integration saves real time nothing else saves. True
in principle, unproven in practice, and unprovable pre-launch.

**Argument for 50% higher ($44):** it lands just under Oiti's $49 while
offering something Oiti doesn't. The buyer's $150/mo budget absorbs it. And
underpricing signals low confidence in a category where every competitor
charges more.

**Argument for 50% lower ($15):** removes all friction from trying, and
distribution is the actual weakness here (scored 2/5 in the Moat Blueprint
run). Price as an acquisition lever rather than a value capture.

**Resolution:** $29 holds — but only because distribution is the binding
constraint, not price. If the tool had an audience attached, $44 would be
correct. Worth revisiting the moment a distribution channel exists.

**This is the module doing its job:** the answer didn't change, but the
*reason* did. "$29 because it felt right" became "$29 because distribution is
the constraint, and here's what would change it."

---

## Module 6 — Launch Price and Iteration Plan

**Launch price: $29/mo, single paid tier, with a 3-post free tier.**

**Reasoning:** the target buyer already spends $80–150/mo on tooling, so the
budget exists and $29 doesn't require justification. Mid-market positioning
matches the actual product maturity — more capable than formatters, less
proven than premium tools. Distribution rather than price is the binding
constraint, so pricing for acquisition beats pricing for margin until a
channel exists.

**Signals I priced too low** (observable within 60 days):
1. Fewer than 5% of trial users mention price at all in cancellation feedback
2. Free-tier users hitting the 3-post cap within their first week
3. More than 30% of paying users active daily rather than weekly — indicates
   the tool is worth more to them than they're paying

**Signals I priced too high:**
1. More than 20% of cancellations name price specifically
2. Free-to-paid conversion below 2%
3. Trial users connecting a repo but never generating a second post —
   suggests the value didn't land before the decision point

**Grandfathering plan (written before launch):** anyone who pays in the first
90 days keeps $29/mo for as long as their subscription is continuous, stated
publicly at launch. Costs little at low volume and buys goodwill with exactly
the cohort most likely to talk about the product.

**First experiment:** run $29 and $39 as a split on the pricing page for 30
days. Result that would change my mind: if $39 converts within 20% of $29's
rate, raise the price — the revenue difference outweighs the volume loss at
this scale.

---

## What this run demonstrates

The output isn't just a number. It's a number, three sentences of reasoning,
six falsifiable signals with a 60-day deadline, a grandfathering commitment,
and one experiment with a pre-declared decision rule.

Note also what the process *rejected*: the textbook 2026 answer is hybrid
pricing with a metered layer, and Module 2 concluded that's wrong for a
pre-launch product with no usage data. A pricing process that always arrives
at best practice isn't reading your situation.

# The Pricing Teardown — Notion Template Structure

Build this as one Notion page with 6 sub-pages. Paste this file's content in;
Notion converts the Markdown into blocks automatically.

---

## Cover Page

**The Pricing Teardown**
Decide what to charge — and be able to defend it.

> Duplicate this template. Work modules 1–6 in order. You'll finish with a
> launch price, the reasoning behind it, and the specific signals that would
> tell you to change it.

Tools needed: any AI assistant with web access. Free tiers work.

Progress: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6

**Before you start:** you need a rough competitor list. If you don't have one,
run the Micro-SaaS Moat Blueprint first — its Module 1 output is this
template's Module 1 input.

---

## Module 1 — Price Mapping

**Purpose:** Map what the market charges, and what sits behind each paywall.
The gating logic tells you more than the numbers.

| Competitor | Tier 1 | Tier 2 | Tier 3 | What's gated where | Public pricing? |
|---|---|---|---|---|---|
| | | | | | |

**Prompt:**
```
I'm pricing a product in this space: [describe your product in 1-2
sentences]. My competitors are: [list them].

For each competitor, give me:
1. Every pricing tier, with the exact price
2. What is gated behind each tier — which specific features unlock
   at which price point
3. What their free tier or trial includes, and what it deliberately
   withholds
4. Whether they publish pricing publicly or hide it behind a demo call

Then tell me: what does the gating pattern reveal about which feature
each competitor believes is most valuable?
```

**Look for:** the feature everyone gates at the same tier. That's the market's
collective guess at where value sits.

---

## Module 2 — Value Metric Discovery

**Purpose:** Decide what you charge *per*. This is the highest-leverage
decision in pricing and the one most often made by accident.

| Candidate metric | Scales with value? | Buyer can predict it? | Grows with success? | Measurable cheaply? | Biggest risk |
|---|---|---|---|---|---|
| | | | | | |

**Prompt:**
```
My product: [describe it]. My target buyer: [describe them].

Identify 4-6 candidate value metrics — units I could charge per.
For each one, tell me:
1. Does it scale with the value the customer receives, or with my
   cost to serve? (Ideally both, but value matters more.)
2. Is it something the buyer can predict before they're billed?
3. Does it grow naturally as the customer succeeds?
4. Can I actually measure it without building complex infrastructure?

Then rank them, and name the single biggest risk of each.
```

**Context worth knowing:** pure per-seat pricing has fallen to roughly 8% of
the SaaS market, with hybrid (a base fee plus a metered layer) now the single
most common structure at around 37%. Usage-based sits near 38% adoption, up
from 27% in 2023. Seats still work where value genuinely scales with team
size — they break for AI-powered and API-first products, where one power user
can generate a hundred times the value of a casual one.

**Warning:** criterion 2 is where clever metrics die. Unpredictable bills
create bill shock, and bill shock creates churn even at a fair total price.

---

## Module 3 — Willingness to Pay

**Purpose:** You can't afford a real pricing study. This is the cheap version
that catches the worst mistakes.

| Adjacent thing buyer already pays for | Price | Considered good value? |
|---|---|---|
| | | |

**Pricing complaints found (quote them, don't summarise):**
-

**Prompt:**
```
My buyer is: [describe them specifically].

Research what this buyer already spends money on in adjacent
categories. For each, find the typical price point and whether
buyers consider it good value.

Then search for pricing complaints in this space — forums, Reddit,
review sites, "X is too expensive" or "X alternative cheaper".
Quote the specific objections, not summaries.

Finally: what does this buyer's existing spending tell me about the
ceiling and floor for my product?
```

**Why existing spend matters:** it's the most reliable free signal available.
Someone already paying $50/mo across three tools has a proven budget. Someone
paying nothing has an unproven one, and convincing them to start is a
different and much harder job than winning a share of an existing budget.

---

## Module 4 — Tier Architecture

**Purpose:** Make the right tier obvious to each segment. The goal isn't
maximising any single sale.

| Tier | Price | For whom | Included | Excluded, and why | Upgrade trigger |
|---|---|---|---|---|---|
| | | | | | |

**Prompt:**
```
Based on this research: [paste Modules 1-3 output]

Design a tier structure. For each tier give me:
- The name and price
- Exactly which buyer it's for
- What's included, and critically what's excluded and why
- The one feature that makes someone upgrade from the tier below

Rules to follow:
- No more than 3 paid tiers unless you can justify a 4th
- Every exclusion must have a reason a buyer would accept
- Name the tier most buyers should land on, and explain what makes
  it the obvious choice

Then tell me what's wrong with this structure.
```

**The last line is deliberate.** Ask a model to design something and it
produces a defence of its own work. Asking for the flaw in the same breath
gets a more useful answer.

---

## Module 5 — Anchoring and Signal

**Purpose:** Your price is a claim about what you are. Sitting at the bottom
of a market says something whether you meant it or not.

**Prompt:**
```
My proposed pricing: [paste Module 4 structure].
Competitor prices: [paste Module 1 map].

Analyse the positioning signal:
1. Where does my entry price sit relative to the market — bottom,
   middle, premium?
2. What does that position claim about my product, and can I back
   the claim up?
3. If I'm cheapest: what will buyers assume is missing, and is that
   assumption survivable?
4. If I'm most expensive: what specifically justifies it in the
   buyer's eyes, not mine?
5. What's the strongest argument for pricing 50% higher than
   I planned? And 50% lower?
```

**Answer question 5 in writing before moving on.** Solo founders underprice
far more often than they overprice, usually out of a fear of seeming
presumptuous. Argue the other side properly at least once.

---

## Module 6 — Launch Price and Iteration Plan

**Purpose:** Your day-one price is a hypothesis. Decide it, and decide what
would falsify it.

**Launch price:** ______  
**Reasoning (3 sentences):**

**Signals I priced too low** (observable within 60 days):
1.
2.
3.

**Signals I priced too high:**
1.
2.
3.

**Prompt:**
```
Based on everything above: [paste Modules 1-5 summary]

Give me:
1. A specific launch price, with the reasoning in three sentences
2. Three signals that would mean I priced too low, and three that
   would mean too high — each one observable within 60 days
3. A plan for raising prices later without punishing early
   customers
4. The one pricing experiment I should run first, and what result
   would change my mind

Be concrete. "Monitor conversion" is not a signal. "Fewer than
2 percent of trial users cite price as the reason they didn't
convert" is a signal.
```

**Closing checklist:**
- ☐ A specific number, not a range
- ☐ Three sentences explaining why it isn't 30% higher
- ☐ Six observable signals with dates
- ☐ A grandfathering plan written down *before* launch
- ☐ Calendar reminder set for 60 days out

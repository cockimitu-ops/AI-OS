# Pricing Teardown — Lead Magnet + Launch Content

---
---

# PART A: Free Lead Magnet

## The Value Metric Test (Free)

*Module 2 of The Pricing Teardown. Free, no email required.*

Most solo founders pick a price. Very few pick a **value metric** — the unit
they charge *per*. Seats, projects, API calls, resolved tickets, connected
accounts. Get this wrong and every later pricing decision inherits the error.

Here's the test.

### Score each candidate metric on four questions

**1. Does it scale with the value the customer receives?**
Not with your cost to serve. Ideally both, but value matters more. A metric
that grows with your server bill but not with customer outcomes makes you
the enemy of your own users.

**2. Can the buyer predict it before they're billed?**
This is where clever metrics die. Unpredictable bills create bill shock, and
bill shock creates churn even when the total price was fair. If your buyer
can't estimate next month's invoice, you have a retention problem you haven't
met yet.

**3. Does it grow naturally as the customer succeeds?**
The metric should climb when things go well for them. That's what makes
expansion revenue feel earned rather than extracted.

**4. Can you measure it without building infrastructure?**
Metering is real engineering. If tracking your metric requires a billing
system you haven't built, that's a cost that must be priced in.

### The prompt

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

### Context for 2026

Pure per-seat pricing has fallen to roughly 8% of the SaaS market. Hybrid —
a base subscription plus a metered layer — is now the most common structure
at around 37%, and usage-based has reached 38% adoption, up from 27% in 2023.

The reason matters more than the numbers: AI severs the link between value
and headcount. When one person running an AI tool does the work of five, a
per-seat model can't capture what you're actually delivering.

**But** — and this is where the framework earns its place — "hybrid is best
practice" doesn't mean hybrid is right for you *yet*. Building metering
infrastructure before you know which metric matters is premature
optimisation with a billing system attached. Best practice for a company
with usage data is often the wrong answer for a pre-launch product.

### What comes next

This is one module of six. The full Pricing Teardown continues:

**Module 1 — Price Mapping.** What the market charges and what's gated where.
**Module 3 — Willingness to Pay.** Built on what your buyer already spends.
**Module 4 — Tier Architecture.** How many tiers, and what you exclude.
**Module 5 — Anchoring and Signal.** What your price claims about you.
**Module 6 — Launch Price.** A number, plus six signals that would falsify it.

Full template, all prompts, plus a real product priced end to end:
**[gumroad link] — $29**

---
---

# PART B: Reddit Posts

Same rules as always: give the method away, link is a footnote. One sub per
week. Reply to everything in the first three hours.

## Post 1 — r/SaaS

**Title:** The pricing question almost nobody asks: what are you charging *per*?

**Body:**

Most pricing advice is about the number. Almost none of it is about the unit
— what you charge *per*. Seats, projects, API calls, resolved tickets.

That decision constrains everything downstream, and most solo founders make
it by copying whoever they benchmarked against.

**Four questions I now run before picking a metric:**

1. **Does it scale with value the customer gets** — not with your cost to
serve? A metric tracking your server bill instead of their outcome makes you
the adversary of your own power users.

2. **Can they predict it before the invoice?** This is where clever metrics
die. Unpredictable bills create bill shock; bill shock creates churn even at
a fair total price. If your buyer can't estimate next month, you have a
retention problem you haven't met yet.

3. **Does it grow when they succeed?** That's what makes expansion revenue
feel earned rather than extracted.

4. **Can you measure it without building infrastructure?** Metering is real
engineering. Price that cost in.

**Context:** pure per-seat is down to about 8% of the market. Hybrid — base
fee plus metered layer — is the most common structure now at ~37%,
usage-based at ~38% adoption, up from 27% in 2023. AI broke the link between
value and headcount, and seats never recovered.

**But here's the part I actually want to argue.** When I ran this on my own
product, the framework said hybrid was best practice and I concluded it was
wrong for me anyway — pre-launch, no usage data, no idea which metric would
matter. Building metering before knowing what to meter is premature
optimisation with a billing system attached.

Flat rate at launch, revisit at 50 customers. Best practice for a company
with data is frequently the wrong answer for one without.

**One more finding worth sharing.** While mapping a category's pricing I
noticed the market leader gates its *defining feature* one tier above its
advertised entry price. Its Trustpilot sits around 2.1–2.4/5, mostly billing
complaints. Gating the thing your product is *for* is the one exclusion
buyers don't forgive.

Happy to go into any of it.

---

## Post 2 — r/indiehackers

**Title:** I asked what's wrong with my own pricing structure. The answer was more useful than the structure.

**Body:**

Small process change that improved my pricing work more than anything else:
after designing a tier structure, I ask the same AI **"now tell me what's
wrong with this."**

Ask a model to design something and you get a defence of its own work. Ask
for the flaw in the same breath and you get something useful.

**What it caught in mine:**

1. **No expansion revenue.** Every customer worth exactly $29/mo forever.
My buyers spend $80–150/mo on tooling — power users were leaving money on
the table and I hadn't noticed.

2. **Free tier cannibalising.** My free cap was generous enough that a
meaningful slice of my target buyer never needed to pay.

3. **Sitting between two competitors' tiers.** $29 with competitors at $19
and $39 — the least differentiated position available. I'd landed there by
splitting the difference, which is how most people land anywhere.

Point 3 stung because it exposed that I'd never actually argued for a higher
price. So I forced it: **write the strongest case for charging 50% more, and
50% less, before deciding.**

The price didn't change. The reasoning did. "$29 because it felt right"
became "$29 because distribution is my binding constraint, not price — and
if I had an audience, $44 would be correct."

That's a decision I can revisit when something changes, instead of a number
I'm stuck with because I can't remember why I chose it.

Solo founders underprice far more than they overprice, usually from a vague
sense that charging more is presumptuous. Making yourself argue the other
side once is cheap insurance.

---

## Post 3 — r/microsaas

**Title:** Six signals that tell you whether you priced wrong, within 60 days

**Body:**

"Monitor conversion" is not a signal. It's a thing you say instead of
deciding what would change your mind.

When I set a launch price now, I write down six specific, observable
outcomes first — three that would mean too low, three that would mean too
high. All checkable within 60 days.

**Too low:**
- Under 5% of cancellations mention price at all
- Free-tier users hitting their cap in week one
- Over 30% of paying users active *daily* rather than weekly — the tool is
worth more to them than they're paying

**Too high:**
- Over 20% of cancellations name price specifically
- Free-to-paid conversion under 2%
- Trial users completing setup but never returning — value didn't land
before the decision point

The point isn't these exact thresholds. It's that they're falsifiable and
dated. Writing them before launch means you can't rationalise afterwards,
which is the actual failure mode — not choosing wrong, but choosing a
defensible price and never revisiting it.

**Two more things I now do before launch:**

**Write the grandfathering plan first.** "Anyone paying in the first 90 days
keeps this rate while their subscription stays continuous." Costs nothing at
low volume, and it's far easier to promise up front than retrofit once
people are angry about a change.

**Declare the decision rule before the experiment.** "Run $29 vs $39 for 30
days; if $39 converts within 20% of $29, raise the price." Deciding the rule
after seeing data is how you talk yourself into whatever you already wanted.

Calendar reminder at 60 days. That's the whole system.

---
---

# PART C: Buyer Emails

## Email 1 — instant delivery

**Subject:** Your Pricing Teardown — start here

Hey,

Everything's below.

**Notion template:** [duplicate link] — hit "Duplicate" top right.
**Prompt pack (PDF):** attached, all six modules offline.
**Worked example:** attached. A real product priced end to end with real
competitor data. If you're unsure what good output looks like at any module,
check what the example did there.

**Start at Module 1.** You'll need a rough competitor list — if you don't
have one, that's what the Moat Blueprint produces, and its output is this
template's input.

Budget 60–90 minutes.

One thing before you start: Module 5 asks you to argue for a price 50%
higher than you planned. Do it properly, in writing, even if you end up
keeping your original number. Solo founders underprice far more often than
they overprice, and that module is the only place the process forces you to
notice.

Stuck anywhere? Reply — I read all of them.

## Email 2 — day 4

**Subject:** What did you land on?

Hey — did you get through it?

If you did, I'd like to know what price you landed on and whether it changed
from your starting guess. Reply with both if you're up for it; I'm tracking
whether the process actually moves people or just confirms what they
already thought.

If you stalled, it's usually Module 2. The value metric question feels
abstract until you realise it's the thing constraining every tier decision
after it. Worth pushing through rather than skipping.

**Related:** if you haven't validated the idea underneath the price yet, the
Micro-SaaS Moat Blueprint runs the competitive research that feeds Module 1
here. Same format, same worked example carried through. [link]

And if you'd rather have the research done for you than do it — that's my
service. [Fiverr link]

## Email 3 — day 12

**Subject:** Quick favour

Two things.

**One:** if this was useful, a review on the product page helps more than
you'd think — it's the only social proof a solo product has. If it wasn't
useful, reply and tell me why instead. That helps more.

**Two:** your 60-day signal check from Module 6. If you set the calendar
reminder, good. If you didn't, this email is it — go set it now. The process
only pays off if you actually look at the signals you wrote down.

If your price changed based on what you found, I'd genuinely like to hear
about it.

# r/SaaS Post 1 — warm up first, then post

Purpose: Everything for the r/SaaS post per `_infra/LAUNCH-ORDER.md` and `launch-checklist.md` — just Post 1, not the other two (X-thread day 3, r/indiehackers day 7). Renamed from "ready today" on 2026-08-27: Felix confirmed the account has no comment history in r/SaaS specifically, so this isn't a same-day action anymore.
Last Updated: 2026-08-27
Status: Blocked on warm-up — do not post yet

---

## Why this actually matters, not just a formality
Confirmed via research, not assumed: r/SaaS has been actively auto-removing posters with no prior subreddit participation. General benchmark across SaaS-adjacent subs (not officially published by r/SaaS itself, but consistent across sources): 30+ days account age, visible comment history, activity across a handful of subs rather than only the target one. As of April 2026, r/SaaS also caps self-promotion — posts, comment plugs, and product mentions all count — to once every 60 days.

**That last part is the one to actually watch:** don't mention the product, the Notion template, or anything promotional in ANY warm-up comment. That would spend the 60-day allowance on a throwaway comment instead of the actual launch post. Warm-up comments should be 100% about the other person's post — genuine input, nothing about you.

## Warm-up plan
Over the next 3–5 days, leave a handful of genuine comments on other people's posts in r/SaaS — not about your product, just real input. The natural angle: you've been building the exact competitor-research process this post describes, so posts about "how do I know if my SaaS idea is worth building," pricing questions, or "why did my last idea fail" are places you can add something specific and useful without it reading as setup for a pitch. Once you've got a few real comments with real replies under them, the account has the standing this post needs.

## When you're ready to actually post
Everything below is unchanged from the original draft — title, body, and the reply templates for once it's live.

## Title
I scored my own SaaS idea 13/25 on defensibility and killed it. Here's the framework I used.

## Body

I've been testing micro-SaaS ideas for a while and kept making the same
mistake: I'd find a gap, get excited, and start building. Then three months
in I'd realise the gap was unserved because it wasn't worth serving.

So I built a scoring process to catch that earlier. Sharing it because the
last idea I ran through it scored 13/25 and I dropped it — which saved me
about two months.

**The process, 6 steps:**

1. **Find everyone.** Not the 2-3 names you know. Direct competitors,
indirect ones, and the tools people currently duct-tape together instead.
Target 8-15 names. If you find fewer than 8, your search wasn't broad
enough — an empty niche is much rarer than a badly-searched one.

2. **Tear down the closest 4.** Pricing tiers, what's gated behind each,
positioning, and — most valuable — public complaints. Search their name
plus "alternative" or "vs", check G2/Trustpilot/Reddit. Recurring complaints
are gaps people will pay to have fixed.

3. **Build a parity matrix.** Every feature that showed up anywhere, as
rows. Competitors as columns. The empty cells are where you're looking.

4. **Sort the gaps into three buckets.** Unserved because it's hard (real
moat). Unserved because nobody asked (validate first). Unserved because
it's genuinely low-value (skip). Most people treat all three as bucket one.
Big companies usually aren't stupid — if something's obviously missing,
they've usually decided it's not worth it.

5. **Score the moat, 1-5 on five axes:** data moat (gets better with usage),
network effects, switching cost, distribution advantage (do you already
reach this buyer?), technical complexity. Be harsh.

6. **Read the score.** Under 10: it's a feature, not a company. 10-17: viable
niche, expect a competitor inside 6-12 months. 18+: worth the build time.

**The example that killed my idea:**

Idea was an AI LinkedIn tool that writes build-in-public posts from your
actual GitHub commits and Stripe revenue, instead of from a generic text
box. I checked 12 existing tools — Taplio, Supergrow, AuthoredUp, Oiti and
others — and confirmed the gap was real. None of them touch real product
data.

Then the scoring: data moat 4 (compounds with every commit). Network
effects 1 (single-player tool, none). Switching cost 3. Distribution 2 (I
have zero reach into that crowd). Technical complexity 3 (GitHub + Stripe
API, buildable solo in weeks — which cuts both ways).

13/25. Real wedge, but no distribution and nothing stopping a funded
competitor from copying it in a quarter. For someone who already has an
audience of indie hackers, that's a green light. For me it wasn't.

One thing worth flagging from the research: a lot of the "best AI LinkedIn
tools" comparison articles are published by the companies that come out #1
in them. Check who owns the domain before you trust a ranking.

Happy to answer questions on any of the steps.

*(Optional last line, only if the thread goes well and someone asks:)*
I packaged this as a Notion template with the prompts pre-written — link in
my profile if useful, but the whole method is above, you don't need it.

---

## After posting: reply to every comment in the first 3 hours
Early engagement is what decides whether the post travels. Common responses, ready to paste:

**"Isn't this just a SWOT?"**
Fair, the teardown part overlaps. The difference is step 5 — SWOT tells you
what's strong or weak, it doesn't tell you whether a gap is defensible once
you fill it. The scoring is the part that changed my decisions.

**"How long does this take?"**
About 60-90 minutes for a first pass if you're using an AI assistant for the
research legwork. Faster on repeats once you know the flow.

**"What AI did you use?"**
Perplexity for the research-heavy steps because it cites sources, then any
reasoning model for the scoring. Free tiers work — the prompts are the
thing, not the model.

**"Are you selling something?"** (answer honestly, always)
Yes — I packaged this as a Notion template with the prompts written out,
it's in my profile. The full method is in the post though, you can run it
without buying anything.

---

## What's next (not today)
- **Day 3:** X-thread from `funnel-assets.md`
- **Day 7:** r/indiehackers, Post 2 from `reddit-launch-posts.md`

Don't post either early — that's the exact "all three at once" mistake the launch order warns against.

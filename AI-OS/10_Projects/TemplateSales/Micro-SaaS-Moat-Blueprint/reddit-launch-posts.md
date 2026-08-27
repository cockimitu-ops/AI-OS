# Reddit Launch Posts

**The rule that governs all of these:** Reddit punishes promotion and rewards
usefulness. Every post below gives away the entire method for free. The
product link is a footnote, not the point. If you strip the link out, the
post should still be worth posting — that's the test.

**Posting rhythm:** one sub per week, not all three in one day. Cross-posting
the same content to three subs on the same day is the fastest way to get
flagged. Reply to every comment in the first 3 hours — early engagement is
what decides whether the post travels.

**Before you post anywhere:** have some comment history in the sub. A brand
new account dropping a link reads as spam regardless of quality.

---

## Post 1 — r/SaaS

**Title:**
I scored my own SaaS idea 13/25 on defensibility and killed it. Here's the framework I used.

**Body:**

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

---

*(Optional last line, only if the thread goes well and someone asks:)*
I packaged this as a Notion template with the prompts pre-written — link in
my profile if useful, but the whole method is above, you don't need it.

---

## Post 2 — r/indiehackers

**Title:**
The "unserved gap" you found is probably unserved on purpose. A filter I now run first.

**Body:**

Pattern I kept hitting: find a feature no competitor has → assume it's an
opportunity → build it → discover nobody wanted it.

The fix was realising there are three reasons a gap exists, and only one of
them is good news:

**1. Hard to build.** Requires integration work, data access, or domain
knowledge a generalist competitor won't invest in. This is the good one —
the difficulty is the moat.

**2. Nobody asked yet.** Genuinely novel. Could be great, could be
imaginary. Needs validation before code, not after.

**3. Low value.** Everyone considered it and passed. This is most of them.

The test I use: can I explain *why* it's unserved, specifically? If I can't
articulate a reason a competitor with more resources than me chose not to
build it, I assume bucket 3 until proven otherwise.

**Worked example.** I looked at AI LinkedIn writing tools. Every one of them
grounds drafts in generic uploads — PDFs, past posts, articles. None connect
to a founder's actual commits or revenue data.

Bucket 1 or bucket 3? Bucket 1, and here's the specific reason: it needs
GitHub and Stripe integrations, and most buyers of those tools are coaches
and consultants who don't have commits or MRR to pull from. The integration
work only pays off for a narrow segment, so a general tool has no reason to
build it.

That's a real answer. If my answer had been "I guess nobody thought of it,"
I'd have treated it as bucket 3.

Then I scored it — data moat, network effects, switching cost,
distribution, technical complexity, 1-5 each. Came out 13/25. Real wedge,
but zero distribution advantage and copyable in a quarter. Didn't build it.

The scoring is the part I'd push hardest. Finding gaps is easy and
addictive. Scoring them is what stops you building the wrong one.

---

## Post 3 — r/microsaas

**Title:**
Competitor research process that ends in a number instead of a vibe

**Body:**

Most competitor research I see (mine included, for a long time) ends in a
doc full of notes and a feeling. Here's the version that ends in a score.

**Six steps:** find everyone (8-15, not 3) → tear down the closest four
including their public complaints → parity matrix → sort gaps into
hard/unvalidated/low-value → score the wedge on 5 moat axes → prioritised
roadmap.

**The five axes, 1-5 each:**
- Data moat — does it improve with usage?
- Network effects — more valuable with more users?
- Switching cost — painful to leave?
- Distribution — do you already reach this buyer?
- Technical complexity — hard to clone fast?

**Reading it:** under 10 is a feature, not a company. 10-17 is a viable
niche with a 6-12 month copy window. 18+ compounds.

I ran it on an AI-LinkedIn-tool idea last month. Scored 13. The wedge was
real (no competitor grounds posts in actual GitHub/Stripe data) but
distribution scored 2 and complexity scored 3 — meaning I had no audience
and nothing stopping someone with one from cloning it. Didn't build.

The uncomfortable part is that the score is usually lower than you want.
If you're scoring your own ideas 20+ regularly, you're grading generously —
that's the most common failure mode of doing this yourself.

Two research notes that might save you time:
- Ask whatever AI you use to cite sources, then check two. Several "best
tools in X" articles are published by a company that ranks itself #1.
- Public complaints (G2, Trustpilot, Reddit threads titled "X alternative")
are the highest-signal input in the whole process. Recurring complaints are
gaps with proven demand.

---

## Comment reply templates

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

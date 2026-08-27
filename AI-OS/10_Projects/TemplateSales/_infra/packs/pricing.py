CONFIG = {
    "product": "The Pricing Teardown",
    "eyebrow": "PRICING RESEARCH SYSTEM",
    "subtitle": "The Prompt Pack — offline copy of all six modules.",
    "accent": "#2F7D6E",
    "output": "pricing-prompt-pack.pdf",
    "intro": [
        "Every prompt here works on the free tier of Perplexity, ChatGPT, Claude, or "
        "Gemini. Paid tiers mean deeper research per prompt, not different prompts.",
        "Work the modules in order — each takes the previous one's output as input. "
        "Replace anything in [square brackets] with your own details before sending.",
    ],
    "intro_note": "The single most consequential module here is Module 2. Most solo "
                  "founders copy a competitor's tier structure without ever asking what "
                  "that competitor is charging per. Get the value metric wrong and every "
                  "later decision inherits the error.",
    "modules": [
        {
            "title": "Price Mapping",
            "intro": "Before deciding what to charge, map what the market already charges "
                     "— and more importantly, what sits behind each paywall. The gating "
                     "logic tells you more than the numbers do.",
            "prompt": """I'm pricing a product in this space: [describe your product
in 1-2 sentences]. My competitors are: [list from your competitor research].

For each competitor, give me:
1. Every pricing tier, with the exact price
2. What is gated behind each tier -- which specific features unlock
   at which price point
3. What their free tier or trial includes, and what it deliberately
   withholds
4. Whether they publish pricing publicly or hide it behind a demo call

Then tell me: what does the gating pattern reveal about which feature
each competitor believes is most valuable?""",
            "tip": "Watch for the feature that everyone gates at the same tier. That's the "
                   "market's collective guess at where the value sits — useful whether you "
                   "follow it or deliberately break from it.",
        },
        {
            "title": "Value Metric Discovery",
            "intro": "The value metric is what you charge per: per seat, per project, per "
                     "thousand API calls, per resolved ticket. This is the highest-leverage "
                     "decision in pricing, and the one most often made by accident.",
            "prompt": """My product: [describe it]. My target buyer: [describe them].

Identify 4-6 candidate value metrics -- units I could charge per.
For each one, tell me:
1. Does it scale with the value the customer receives, or with my
   cost to serve? (Ideally both, but value matters more.)
2. Is it something the buyer can predict before they're billed?
3. Does it grow naturally as the customer succeeds?
4. Can I actually measure it without building complex infrastructure?

Then rank them, and name the single biggest risk of each.""",
            "tip": "Criterion 2 is where clever metrics die. A metric the buyer can't "
                   "predict creates bill shock, and bill shock creates churn — even when "
                   "the total price was fair.",
        },
        {
            "title": "Willingness to Pay",
            "intro": "You can't run a proper pricing study as a solo founder. You can do "
                     "something cheaper that catches the worst mistakes: find what your "
                     "buyer already pays for adjacent things, and what they complain about.",
            "prompt": """My buyer is: [describe them specifically].

Research what this buyer already spends money on in adjacent
categories. For each, find the typical price point and whether
buyers consider it good value.

Then search for pricing complaints in this space -- forums, Reddit,
review sites, "X is too expensive" or "X alternative cheaper".
Quote the specific objections, not summaries.

Finally: what does this buyer's existing spending tell me about the
ceiling and floor for my product?""",
            "tip": "Existing spend is the most reliable signal you can get for free. Someone "
                   "already paying $50/mo for three tools in your category has a proven "
                   "budget; someone paying nothing has an unproven one.",
        },
        {
            "title": "Tier Architecture",
            "intro": "How many tiers, and what separates them. The goal isn't to maximise "
                     "any single sale — it's to make the right tier obvious to each segment.",
            "prompt": """Based on this research: [paste Modules 1-3 output]

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

Then tell me what's wrong with this structure.""",
            "tip": "The last instruction matters. Ask any model to design something and it "
                   "produces a defence of its own work. Asking for the flaw in the same "
                   "breath gets you a more useful answer.",
        },
        {
            "title": "Anchoring and Signal",
            "intro": "Your price is a claim about what you are. Sitting at the bottom of a "
                     "market says something whether you meant it or not.",
            "prompt": """My proposed pricing: [paste Module 4 structure].
Competitor prices: [paste Module 1 map].

Analyse the positioning signal:
1. Where does my entry price sit relative to the market -- bottom,
   middle, premium?
2. What does that position claim about my product, and can I back
   the claim up?
3. If I'm cheapest: what will buyers assume is missing, and is that
   assumption survivable?
4. If I'm most expensive: what specifically justifies it in the
   buyer's eyes, not mine?
5. What's the strongest argument for pricing 50% higher than
   I planned? And 50% lower?""",
            "tip": "Solo founders underprice far more often than they overprice, usually out "
                   "of a fear of seeming presumptuous. Question 5 exists to make you argue "
                   "the other side properly at least once.",
        },
        {
            "title": "Launch Price and Iteration Plan",
            "intro": "What you charge on day one is a hypothesis, not a commitment. This "
                     "module decides the hypothesis and the conditions under which you'd "
                     "change it.",
            "prompt": """Based on everything above: [paste Modules 1-5 summary]

Give me:
1. A specific launch price, with the reasoning in three sentences
2. Three signals that would mean I priced too low, and three that
   would mean too high -- each one observable within 60 days
3. A plan for raising prices later without punishing early
   customers
4. The one pricing experiment I should run first, and what result
   would change my mind

Be concrete. "Monitor conversion" is not a signal. "Fewer than
2 percent of trial users cite price as the reason they didn't
convert" is a signal.""",
            "tip": "Point 3 is worth writing down before launch, not after. Grandfathering "
                   "early customers is much easier to promise up front than to retrofit once "
                   "they're angry.",
        },
    ],
    "closing_eyebrow": "WHEN YOU'RE DONE",
    "closing_title": "Reading your own result",
    "closing": [
        "A finished run gives you a number, a reason for it, and the conditions under "
        "which you'd change it. If you finished with a price but couldn't explain in "
        "three sentences why it isn't 30 percent higher, go back to Module 5.",
        "The most common failure is not choosing wrong — it's choosing a defensible price "
        "and then never revisiting it. Set a calendar reminder for 60 days out to check "
        "your signals from Module 6 against what actually happened.",
    ],
    "closing_note": "Priced it, and now want the competitive picture underneath it? The "
                    "Micro-SaaS Moat Blueprint runs the six-step research process that "
                    "feeds Module 1 of this pack — link on your receipt.",
}

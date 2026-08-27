CONFIG = {
    "product": "Micro-SaaS Moat Blueprint",
    "eyebrow": "COMPETITOR RESEARCH SYSTEM",
    "subtitle": "The Prompt Pack — offline copy of all six modules.",
    "accent": "#C6841F",
    "output": "moat-prompt-pack.pdf",
    "intro": [
        "Every prompt in this pack works on the free tier of Perplexity, ChatGPT, "
        "Claude, or Gemini. Paid tiers mean deeper research per prompt, not different "
        "prompts.",
        "Work the modules in order — each one takes the previous module's output as "
        "input. Replace anything in [square brackets] with your own details before "
        "sending.",
    ],
    "intro_note": "One habit worth building: ask the AI to cite its sources, then "
                  "spot-check two of them. Review sites frequently rank their own "
                  "product first, and a competitor map built on one biased listicle is "
                  "worse than no map at all.",
    "modules": [
        {
            "title": "Competitor Discovery",
            "intro": "Find everyone already serving this niche — not just the two or "
                     "three names you already know. Aim for 8 to 15 before moving on. "
                     "Fewer than eight usually means the search wasn't broad enough, "
                     "not that the niche is empty.",
            "prompt": """I'm evaluating a micro-SaaS idea: [describe your idea in 1-2 sentences].

Find every existing product that competes for the same buyer's budget --
direct competitors (same solution), indirect competitors (different
solution, same problem), and adjacent tools users currently duct-tape
together instead. Include small/indie tools, not just market leaders.

For each one give: name, one-line description, pricing model, and how
you found it (search term, directory, forum mention).""",
            "tip": "Record where each name came from. If they all came from one "
                   "listicle, you have one source's opinion, not a market map.",
        },
        {
            "title": "Competitor Teardown",
            "intro": "Go deep on the three to five competitors that actually matter — "
                     "closest positioning, most traction, or most similar pricing. Run "
                     "this prompt once per competitor.",
            "prompt": """Research [competitor name] in depth. I need:

1. Their exact pricing tiers and what's gated behind each
2. Their core feature list, grouped by category
3. Who their marketing/positioning is clearly built for
4. Any recent product or pricing changes in the last 6 months
5. Public complaints -- search their name plus "alternative", "vs",
   "sucks", or check G2/Reddit/Trustpilot for recurring frustrations

Cite where each finding comes from.""",
            "tip": "Complaints are the highest-value field here. A recurring complaint "
                   "across multiple sources is a gap someone will pay to have solved.",
        },
        {
            "title": "Feature Parity Matrix",
            "intro": "Put every feature that surfaced in Module 2 into one table — "
                     "including features you don't plan to build. The empty cells are "
                     "the point.",
            "prompt": """Here are teardowns of [N] competitors: [paste your Module 2 notes].

Build a feature comparison matrix. Rows = every distinct feature that
appeared across any competitor. Columns = each competitor, plus a
column for my planned product.

Mark each cell: has it / partial / doesn't have it. Group related
features together. Flag any feature that ONLY one competitor has.""",
            "tip": "Build this by hand if the AI output is messy — the value is in you "
                   "seeing the gaps, not in the table being pretty.",
        },
        {
            "title": "Gap and Wedge Finder",
            "intro": "Turn the matrix into an actual opportunity. Not every empty cell "
                     "is a gap worth filling — this step separates the three kinds.",
            "prompt": """Here is a feature comparison matrix for [niche] tools:
[paste your Module 3 table].

Identify:
1. Gaps unserved because building them is hard
   (real moat if I solve it)
2. Gaps unserved because nobody asked yet
   (validate before building)
3. Gaps unserved because they're genuinely low-value
   (skip these)

For each real gap, name the specific buyer segment who'd care most.""",
            "tip": "If the AI can't explain WHY a gap is unserved, treat it as category "
                   "3 until proven otherwise. Big companies usually aren't stupid — "
                   "they've usually decided it isn't worth it.",
        },
        {
            "title": "Moat Scoring",
            "intro": "Score the gap before you build it. A gap you can fill in a weekend "
                     "is a gap a competitor can close in a weekend too.",
            "prompt": """Based on this gap analysis: [paste Module 4 output]

Score my planned wedge on each of these five factors, 1-5, with a
one-line justification for each score:

1. Data moat -- does it get better with more usage/user data?
2. Network effects -- more valuable as more people use it?
3. Switching cost -- painful for users to leave once adopted?
4. Distribution advantage -- do I already reach this buyer?
5. Technical complexity -- genuinely hard to clone quickly?

Be harsh. Justify low scores rather than inflating them.""",
            "tip": "Reading the score — under 10: this is a feature, not a company. 10 to "
                   "17: viable niche, expect competition in 6 to 12 months. 18+: "
                   "defensibility compounds, worth the build time.",
        },
        {
            "title": "Validated Roadmap",
            "intro": "Convert everything above into something you can act on this week.",
            "prompt": """Based on this research: [paste your Modules 1-5 summary]

Write a prioritized v1 feature roadmap. For each feature give:
- A one-sentence user story
- Why it's prioritized there (tie back to the gap/moat analysis)
- Rough build effort: small / medium / large

Then write a 3-sentence positioning statement for a landing page,
based on the actual gap found -- not generic startup language.""",
            "tip": "Before you close the template: prioritized list (ordered, not a wish "
                   "list), one positioning statement, moat score recorded, and a named "
                   "buyer segment.",
        },
    ],
    "closing_eyebrow": "WHEN YOU'RE DONE",
    "closing_title": "Reading your own result",
    "closing": [
        "A good run of this process does not end in a green light. It ends in a score, a "
        "named risk, and a specific next action. If your moat score came out at 20+ on "
        "the first pass, re-read your justifications — scoring your own idea generously "
        "is the most common way this process fails.",
        "A 13 out of 25 with a clear wedge and a known weakness is a more useful result "
        "than a 22 you talked yourself into.",
    ],
    "closing_note": "Want this run for you instead of by you? The done-for-you version "
                    "of this exact process is available as a service — see the link on "
                    "your Gumroad receipt.",
}

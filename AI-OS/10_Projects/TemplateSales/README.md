# Template Sales

Purpose: Sell automation/content-system templates (n8n packs, documented system templates) — Candidate Option 3 from [[10_Projects/MoneyMaking/Candidate_Options|MoneyMaking's research]]. The only option that works fully on €50 with no ongoing fixed costs, since it sells what's already been built.
Last Updated: 2026-08-26
Status: Active — three products BUILT, none published
Related Documents: [[10_Projects/README|10_Projects]], [[10_Projects/MoneyMaking/Candidate_Options|MoneyMaking Candidate Options]]

---

## What This Is
Packaging already-documented systems for sale — lowest risk, lowest capital, but more likely a supplementary cashflow than a standalone business (comparable products have shown revenue spiking then dropping once a market catches up). Its real value here is generating first revenue and portfolio proof for [[10_Projects/ContentAgency/README|ContentAgency]], not being the end goal.

## What Could Actually Be Sold
The research named this directly: **the AI OS itself is exactly the kind of packaged system this option describes.** Specific candidates:
- The Context Engine / Execution Engine / Template Framework pattern — a "how to build a token-conscious AI second brain" template, genre-agnostic, sellable to anyone running AI-assisted work, not just content creators
- The Horror Story production pipeline structure (without the horror-specific content) — a general "AI content production system" template
- Individual capability specs as smaller, cheaper standalone products

Not limited to what's already built, either — Claude's Artifacts feature can code interactive tools directly (HTML/React widgets, resume builders, flashcard sets) beyond just packaging existing Markdown specs. Broadens the product category from "AI OS templates" to "digital tools and templates generally" — platform choice (Etsy vs. Gumroad vs. Notion marketplace) should follow from researching what's actually trending/searched, not assumed.

## Platforms
Gumroad and Whop noted as low-fee options in the original research. Etsy, Shopify, and the Notion template marketplace are also live candidates depending on what gets built — worth checking current demand per platform before committing to one.

## Constraint
Whatever gets sold must be genuinely reusable by someone else, not this vault's specific content (the actual scripts, the actual client relationships) — selling the *pattern*, not the *instance*.

## Priority (set 2026-08-13, superseded 2026-08-25)
The 2026-08-13 priority was: ship **one** product first, the AI OS pattern itself, stripped of personal content.

**That is not what got built.** What exists instead is a three-product "Solo-Founder Systems" line, none of which is the AI OS pattern. The strategy changed in execution and nothing recorded the change, so this README described an unpackaged project while three finished products sat in its own subfolders. Recorded here on 2026-08-26 rather than quietly overwritten — the earlier reasoning may still be right, and reversing it should be a decision, not a drift.

What survives from the 2026-08-13 reasoning and still applies: **distribution decides this, not product quality.** Short-form video is the #1 discovery channel for Notion templates, and that capability already exists in [[10_Projects/SocialMediaContent/README|SocialMediaContent]] — currently unused for this. The launch plan instead routes through Reddit; see `_infra/LAUNCH-ORDER.md`.

## What Is Actually Built (updated 2026-08-27)
Authoritative state lives in `_infra/AI-CONTEXT.md` — that file is maintained; this section mirrors it.

| Product | Price | Built | Live | Revenue |
|---|---|---|---|---|
| Micro-SaaS Moat Blueprint | $29 | yes | **yes (2026-08-27)** | 0 |
| The Pricing Teardown | $29 | yes | no | 0 |
| Retention Engineering | $39 | yes | no | 0 |
| Validation Stack (bundle 1+2) | $45 | listing copy only | no | 0 |

Each product ships the same artifact set: `notion-template-structure.md`, a prompt-pack PDF, `example-run-through.md`, listing copy, a free lead magnet, Reddit launch posts, and `cover.svg`.

## Launch kits — pull to publish
Micro-SaaS Moat Blueprint (live): `_infra/pull_moat_blueprint_launch_kit.sh` / `.ps1`.
Pricing Teardown (staged for Week 3-4 per `_infra/LAUNCH-ORDER.md`, not yet published — do not publish before Moat Blueprint's Reddit cycle finishes): `_infra/pull_pricing_teardown_launch_kit.sh` / `.ps1`.
Both over Tailscale, both include a rendered `cover.png` — no manual screenshot-export step.

## Status
**Blocked on one manual step, not on building.** Every product is finished. Felix has to publish the Notion pages and create the Gumroad listings — roughly 20 minutes per product. Nothing else waits on anything. Covers are SVG and need a manual PNG export (no renderer available in the environment that built them).

## Next Steps
1. Publish Micro-SaaS Moat Blueprint first (Notion page + Gumroad listing + PNG cover) — it feeds product 2
2. Follow `_infra/LAUNCH-ORDER.md` for spacing; do not launch all three at once
3. Decide whether the AI-OS-pattern product from the 2026-08-13 priority is still wanted as product 4, or dropped

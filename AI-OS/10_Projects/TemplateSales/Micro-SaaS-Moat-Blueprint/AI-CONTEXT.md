# PROJECT: Micro-SaaS Moat Blueprint

<!--
AI CONTEXT FILE. Read this first, before opening any other file in this folder.
Written for token efficiency: state and decisions only, no narrative.
Update the STATUS block when something changes. Keep it under 100 lines.
-->

## STATUS
Phase: built, not launched
Blocker: Felix must publish Notion page + create Gumroad listing (manual, ~20 min)
Revenue to date: 0

## WHAT
$29 self-serve Notion template. Six-module competitor-research process ending
in a 1-25 defensibility score. Target buyer: solo indie hackers testing 3-5
micro-SaaS ideas a year.

## WHY THIS BUYER
Chosen over 4 higher-ranked alternatives (fractional PMMs, angels, corp
innovation managers, in-house PMs) on one criterion: reachability at zero ad
spend. Indie hackers live on Reddit/X where Felix already has a content
workflow. The others need LinkedIn credibility he doesn't have yet.
Fractional PMMs = phase 2, after LinkedIn presence exists.

## FUNNEL
free lead magnet (modules 1-2) -> $29 template -> $180 Fiverr done-for-you gig
Cross-sell runs both directions. Template buyers who get busy convert to the
gig; gig visitors who bounce on price convert at $29.

## FILES
| File | Purpose |
|---|---|
| notion-template-structure.md | Paste into Notion → the product itself |
| prompt-pack.pdf | Offline deliverable (built by build_prompt_pack.py) |
| example-run-through.md | Real worked example, ships with product |
| gumroad-listing-copy.md | Listing text, copy-paste ready |
| LICENSE.md | Single-user commercial license |
| free-lead-magnet.md | Free modules 1-2, top of funnel |
| reddit-launch-posts.md | 3 posts, 3 subs, staggered weekly |
| funnel-assets.md | X thread + 3 buyer emails + Fiverr cross-sell |
| launch-checklist.md | Step-by-step launch sequence |
| cover.svg | Product cover (needs manual PNG export) |

## DECISIONS MADE (don't relitigate without new information)
- English, not German. Buyer is international indie hackers; matches existing
  Fiverr gig audience. German market had lower saturation but Felix has no
  German-language distribution for this niche.
- $29, not $19 or $49. Below the impulse-purchase ceiling, above the "must be
  junk" floor for a template with a worked example attached.
- Gumroad first, Etsy later. Gumroad handles EU/UK VAT; Etsy adds search
  traffic but needs a different listing style. Don't do both at launch.
- Example scores 13/25, deliberately not inflated. A template that scores
  every idea 20+ isn't doing evaluation, and buyers notice.
- Reddit posts give away the entire method. Link is a footnote. Reddit
  punishes promotion; the giveaway IS the distribution strategy.

## OPEN / UNRESOLVED
- cover.svg → PNG: SVG renderer unavailable in this container, no network.
  Felix exports manually via browser screenshot or Canva.
- Notion write access: connector currently read-only in Claude sessions.
  Read/list works, page creation does not. Recheck if needed.
- Kleinunternehmerregelung §19 UStG threshold: Felix's call, not an AI's.

## IF ASKED TO EXTEND THIS
Highest-value next builds, in order:
1. Second template using same structure, different buyer (pricing research,
   positioning audit) — the format is proven, only content changes
2. Etsy listing variant (different copy style, search-driven not narrative)
3. Notion template gallery submission — free distribution channel, unused
Do NOT build: a SaaS version of this. It's a template business. Scoring it on
its own framework: no network effects, low switching cost, trivially cloned.

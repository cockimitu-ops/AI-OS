# PRODUCT LINE: Solo-Founder Systems

<!--
AI CONTEXT FILE. Read this before opening anything else in this folder.
State and decisions only, no narrative. Update STATUS when things change.
Keep under 120 lines.
-->

## STATUS
| Product | Price | Built | Synced to Vault | Live | Revenue |
|---|---|---|---|---|---|
| Micro-SaaS Moat Blueprint | $29 | yes | 2026-08-25 | **yes — live 2026-08-27** | 0 |
| The Pricing Teardown | $29 | yes | 2026-08-25 | no | 0 |
| Retention Engineering | $39 | yes | 2026-08-25 | no | 0 |
| Validation Stack (bundle 1+2) | $45 | listing only | no | no | 0 |

Vault sync (2026-08-25): all three products' files copied from `vault-sync.zip`
into `10_Projects/TemplateSales/`, real path confirmed. The 2026-08-25 "PAUSED,
nothing published" note that used to sit here is superseded: on **2026-08-27 the
Micro-SaaS Moat Blueprint went live** (see the table above and
`Micro_SaaS_Moat_Blueprint_Live_2026_08_27.md`). The project is no longer paused.

Blocker on the two REMAINING products (Pricing Teardown $29, Retention
Engineering $39): Felix must publish their Notion pages + create Gumroad
listings, ~20 min each. All launch assets — Gumroad copy, `cover.png` (already
rendered, not a blocker), lead magnets, buyer emails, Reddit posts — are
written and waiting. Nothing else is blocked on anything but Felix's time.

## THE PATTERN (reuse this for product 4+)
Every product is the same artifact set:
1. `notion-template-structure.md` — 6 modules, paste into Notion
2. prompt-pack PDF — built by `pack_builder.py` from a config in `packs/`
3. `example-run-through.md` — real worked example, ships with product
4. listing copy + free lead magnet (one module given away)
5. 3 Reddit posts (give method away, link is footnote) + 3 buyer emails
6. cover.svg

To add a product: write `packs/<name>.py`, run `pack_builder.py`, then the
five markdown files. Do not rewrite the PDF generator.

Three notes on actually running it (all verified 2026-08-26):
- `pack_builder.py` needs `reportlab`, which is installed nowhere on the server.
  See `requirements.txt` here — use a venv, it is not a system package.
- Each config's `output` key is a working filename (`moat-prompt-pack.pdf`), not
  the shipped one. Products ship it as `prompt-pack.pdf` inside their own folder;
  build, then move and rename.
- `packs/moat.py` was missing until 2026-08-26 — product 1 shipped a PDF that
  could not be regenerated, contradicting the rule above. Written by
  reverse-engineering the shipped PDF; the rebuilt file's rendered text is
  byte-identical to it, so the config is faithful, not approximate.

## PRODUCTS

**1. Micro-SaaS Moat Blueprint** — competitor research → defensibility score
/25 → roadmap. Buyer: indie hackers validating ideas.

**2. The Pricing Teardown** — price mapping → value metric → WTP → tiers →
anchoring → launch price + falsifiable signals. Buyer: same as #1, next step.
Module 1 input = Moat Blueprint Module 1 output.

**3. Retention Engineering** — source mining → hook hierarchy → beat map →
TTS script → visual layer → multi-part. Buyer: narrative short-form creators.
Different audience, different subreddits, no overlap with 1/2.

## WORKED EXAMPLES — CONTINUITY
Products 1 and 2 use the SAME case study (AI LinkedIn tool grounded in
GitHub/Stripe data). Scored 13/25 in #1, priced $29/mo in #2. Deliberate:
bundle buyers watch one idea developed end to end. Keep this if extending.
Product 3 is standalone (1972 Andes crash, public record).

## DECISIONS MADE (don't relitigate without new information)
- English throughout. Buyer is international; matches Felix's Fiverr audience.
- Reddit posts give the full method away. Reddit punishes promotion; the
  giveaway IS the distribution strategy. Do not "optimise" this into a pitch.
- Worked examples show the process REJECTING things — a split declined, a
  best-practice answer overruled, three hooks auto-cut. A system that always
  approves isn't a system. Preserve this.
- Retention priced $39 not $29: proprietary knowledge (Felix's tested
  workflow), not researched knowledge. Higher defensibility, higher price.
- Bundle is 1+2 only. Product 3 has a different buyer; bundling it would
  confuse both listings.
- Retention product states the 105-125s vs 42.7s-average trade openly rather
  than hiding it. Honesty about the tradeoff is a credibility asset here.
- No SaaS versions of any of these. Scored on the Moat framework: no network
  effects, low switching cost, trivially cloned. Template business stays a
  template business.

## OPEN / UNRESOLVED
- **`GUMROAD_LISTINGS_READY_TO_POST.md` recovered 2026-08-26.** Draft listing copy for two products that were never built here: "The AI-OS Framework" ($27, launch $19) — likely the "AI OS pattern" product #4 this file's own LAUNCH ORDER section left unresolved — and a separate "Short-Form AI Content Production Engine" ($29), not previously named anywhere in TemplateSales. Recovered from `~/AI_OS_Launch_Package.zip`, a home-directory archive that had never been synced into the vault. Not acted on — the AI-OS-pattern question was explicitly deferred 2026-08-26 (see [[Roadmap]]). Kept here so it isn't lost, not as a signal to build it.
- All covers are SVG. No renderer in container, no network. Felix exports PNG
  manually (browser screenshot or Canva).
- Notion connector is read-only in Claude sessions — can list/read pages,
  cannot create or edit. Recheck if needed.
- Kleinunternehmerregelung §19 UStG threshold across Gumroad + Fiverr:
  Felix's call, not an AI's.

## LAUNCH ORDER (matters)
1. Moat Blueprint — already built, launch first, it feeds #2
2. Pricing Teardown — 2-3 weeks later, email #1's buyers directly
3. Validation Stack bundle — once both exist
4. Retention Engineering — independent, can run parallel, different subs

Do not launch all at once. Each Reddit post burns a sub's goodwill for a
while; spacing them keeps three channels alive instead of exhausting one.

## IF ASKED TO EXTEND
Next products worth building, in order:
1. **Positioning Audit** — completes the trilogy with 1+2, same buyer,
   enables a $65 three-product stack
2. **Cybersecurity study system** — timed to Felix's Sept 2026 degree start.
   Frame as a learning system, NOT security expertise. He is a student, not
   an expert, and the copy must never imply otherwise.
3. **Etsy listing variants** — different copy register (search-driven, not
   narrative). Free distribution channel, currently unused.

Explicitly rejected: German BFSG/AI-Act compliance kits. Real market gap, but
selling compliance guidance with no legal background means buyers eat fines
when it's wrong. Different risk class from a template that underdelivers.

# AI Video Production

Purpose: System definition for the AI-generated video pillar of the Content system.
Last Updated: 2026-08-03
Status: Active — first concept produced 2026-08-13
Related Documents: [[10_Projects/SocialMediaContent/README|SocialMediaContent]], [[Reddit_Story_Workflow]]

---

## What It Produces
Short-form AI-generated video for TikTok, primary sub-format: oddly satisfying / ASMR-style content, chosen for strong native fit with short-form platforms and low narrative overhead compared to story-driven content.

## Tooling
Generation tool: **Veo 3.1**, selected for native synchronized audio-video output — no separate audio pass required.

## Tiering
- Start on Google's free tier: 10 generations/month, watermarked.
- **Three tiers exist, not two** (corrected 2026-08-13 — this doc previously only listed Fast/Quality): **Lite** (cheapest, noticeably lower fidelity — Google's own benchmark shows only ~55% win-rate vs. Fast in blind comparison), **Fast** (the working tier — use for prompt iteration and first-ever tests of a new concept), **Quality** (highest fidelity, reserved for a clip that's already proven itself worth the cost).
- Sequence: test new prompts on **Fast** first. Only regenerate the confirmed keeper on **Quality** before actually posting. Lite is for rough drafts where fidelity doesn't matter yet, not for judging whether a concept works.
- Upgrade path to AI Pro once volume or quality needs exceed the free tier.

## Prior Template (earlier project, German-language)
An earlier iteration used a seven-scene structure — hook, context, three main steps, reveal, CTA — with evidence-quality annotations distinguishing well-supported claims from unverified assertions. Retained here as a reference pattern, not the current default; the oddly-satisfying pillar doesn't need the same claim-verification structure a fact-based Short does.

## Capabilities
Extracted in Sprint 003: [[Veo_Prompt_Design]], [[Generation_Mode_Selection]], [[Watermark_Tier_Management]].

## First Real Concept (2026-08-13)
Glass Crush Loop — macro crystal shatter, audio synced to fracture points, 8s seamless loop. First use of this pillar since it was built.

**Cost model corrected (2026-08-13):** one 8-second generation IS the video — looped in editing, not stitched from multiple generations into 60s. Short seamless loops outperform longer content for this genre specifically (real 2026 data: the format is "built for the algorithm's preference for high-completion-rate short loops"). The 60-second figure is TikTok's Creator Rewards payout threshold, a monetization-program requirement, not a performance one — and this niche's actual earners monetize via AdSense/affiliate/sponsorship, not that program specifically. Free tier's 10 generations/month = up to 10 videos/month, not one.

**Prompt flaw found (2026-08-13, via a text-based Gemini critique — not a real video review, see note below):** the original prompt asked for a loop back to "intact crystal" without specifying a reversal mechanism. AI cannot infer reverse-motion physics from a forward-destruction prompt. Fix: either prompt the reversal explicitly (crystal reforming in reverse-motion) or design the loop around a point that doesn't require reversing destruction (e.g., loop on a held shot before the crack, not after the shatter).

**Note on review methodology:** the Gemini "critique" that caught the loop flaw opened by stating it could not actually view the rendered file — it was a generic diagnostic of known AI-video failure patterns, not analysis of the actual render. Genuinely useful as domain knowledge (the flaw above is real and worth fixing), but not evidence about this specific video. A real review requires Gemini to actually process the video file, same as the Doorbell Camera review did.

Series strategy: same mechanic, rotate only the crystal color — per current ASMR research, format consistency outperforms novelty for this genre specifically. Output not yet reviewed for real.

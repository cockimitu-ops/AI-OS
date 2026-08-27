# Knowledge Core

Purpose: A hard-capped (~10,000 characters), self-curating record of what's actually worth remembering about Felix and his situation — a Hermes-style bounded core, not a growing log. Distinct from the vault's project files: this is standing context, always cheap to load.
Last Updated: 2026-08-26
Status: Active
Stability: Dynamic
Related Documents: [[07_Context/README|07_Context]], [[Knowledge_Promotion]], [[Context_Budget]]

---

## The Rule
Capped at ~10,000 characters, hard limit. When something new earns a slot and the cap would be exceeded, the weakest existing entry is cut — weighted by [[Knowledge_Promotion]]'s existing bar: **stable/reproducible beats recent/one-off**. A fact that stays true next month outranks something relevant only to today. Checked and updated whenever a conversation surfaces something genuinely durable about Felix or his situation — not after every message, only when something real changes.

## Current Size
~3,800 characters of ~10,000 — the cap applies to the content below (Felix onward), not the standard file header. Room to grow before eviction logic actually gets tested.

---

## Felix
18, Crimmitschau, Saxony, Germany. Starting a cybersecurity degree at Hochschule Mittweida, September 2026 — offensive security/ethical hacking focus, learns via structured courses and video. Lives with his mother; low living costs, currently ~€450/month income. Has ~€10k in savings but no access until after his studies (held by his mother). Long-standing interest in nootropics/supplements. Actively working to stop cannabis use (regular use, started 2026-08-08) — nicotine and occasional psilocybin explicitly set aside for now, not part of the current effort.

## Working Style
Direct, efficiency-focused, wants honest critical feedback over reassurance. Token-conscious — prefers lean execution over exhaustive-by-default. Comfortable with technical depth. Casual tone, German/English bilingual, mixes both naturally.

## The AI OS
A Notion-synced "second brain" vault, explicitly built for multi-project work and shareable across AI tools, not just Claude. Structural principle: reusable knowledge/capabilities stay central (`02_Systems/`, `03_Capabilities/`); project-specific execution lives in `10_Projects/` (ADR-0005). As of 2026-08-11, `04_Agents/` is populated — 4 scoped roles (Vault Architect, Content Producer, Research Analyst, Business Development), manual/chat-triggered. **The "no automation" line is out of date:** since 2026-08-26 a TaskRunner runs as three systemd services on Felix's Ubuntu server — a headless Open Interpreter worker executing tasks unattended, a Telegram bridge, and a daily rclone backup to Google Drive. That is infrastructure, deliberately outside the `04_Agents/` decision, not a reversal of it. A read-only Notion-backed MCP server lives at `AI-OSmcp/`; its build was verified 2026-08-26, its Notion side has still never been exercised.

## Active Projects (10_Projects/)
- **SocialMediaContent** — Horror archived 2026-08-13 (research showed it doesn't monetize well); AI Video pillar active instead (Glass Crush Loop, Veo 3.1). New higher-CPM story topic planned, not yet chosen.
- **MoneyMaking** — research project, spawned the three below.
- **ContentAgency** — productized AI content for German B2B clients, not launched.
- **QuickTurnaroundGigs** — Fiverr startup-competitor-analysis gig ($30/$80/$180); profile bio, PDF sample, and thumbnail prompt all ready — final step (uploading a generated thumbnail image) in progress as of 2026-08-11.
- **TemplateSales** — three finished products as of 2026-08-25 (Micro-SaaS Moat Blueprint $29, Pricing Teardown $29, Retention Engineering $39, plus a $45 bundle listing). Not the AI OS itself, despite the earlier plan. Blocked only on Felix publishing Notion pages + Gumroad listings, ~20 min each.
- **FundingApplications** — **closed 2026-08-13, by choice.** InnoStartBonus/JUGEND GRÜNDET deliberately not pursued. Do not resurface this as a "missed opportunity"; it was a decision.
- **Personal** — reading list, supplement stack, substance history.
- **CyberSecurityLearning** — started 2026-08-08, pre-September head start.
- **GetClean** — started 2026-08-08, reducing cannabis use specifically.
- **LocalArbitrage** — started 2026-08-13, buying mispriced local goods to resell; car is the moat. Funding stream is €100. Not yet started.

Felix has a car (real competitive advantage for local arbitrage), multiple AI subscriptions, and has declined to pursue grant/free money by choice.

## Key Open Threads
Publishing the three TemplateSales products (the only path to first revenue that is already built). Whether running Claude Code headless off the Pro subscription is ToS-acceptable — unresolved, and it currently gates both TaskRunner's escalation tier and the entire AI-Bridge capability. QuickTurnaroundGigs gig not yet posted. AI Video Production pillar status still undecided. No story topic chosen since the Horror archival.

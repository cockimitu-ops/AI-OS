# Knowledge Core

Purpose: A hard-capped (~10,000 characters), self-curating record of what's actually worth remembering about Felix and his situation — a Hermes-style bounded core, not a growing log. Distinct from the vault's project files: this is standing context, always cheap to load.
Last Updated: 2026-09-02
Status: Active
Stability: Dynamic
Related Documents: [[07_Context/README|07_Context]], [[Knowledge_Promotion]], [[Context_Budget]]

---

## The Rule
Capped at ~10,000 characters, hard limit. When something new earns a slot and the cap would be exceeded, the weakest existing entry is cut — weighted by [[Knowledge_Promotion]]'s existing bar: **stable/reproducible beats recent/one-off**. A fact that stays true next month outranks something relevant only to today. Checked and updated whenever a conversation surfaces something genuinely durable about Felix or his situation — not after every message, only when something real changes.

## Current Size
~5,600 characters of ~10,000 — the cap applies to the content below (Felix onward), not the standard file header. Room to grow before eviction logic actually gets tested.

---

## Felix
18, Crimmitschau, Saxony, Germany. Starting a cybersecurity degree at Hochschule Mittweida on 2026-09-23 — offensive security/ethical hacking focus, learns via structured courses and video. Lives with his mother; low living costs, currently ~€450/month income. Has ~€10k in savings but no access until after his studies (held by his mother). Long-standing interest in nootropics/supplements. Actively working to stop cannabis use (regular use, started 2026-08-08) — nicotine and occasional psilocybin explicitly set aside for now, not part of the current effort.

## Working Style
Direct, efficiency-focused, wants honest critical feedback over reassurance. Token-conscious — prefers lean execution over exhaustive-by-default. Comfortable with technical depth. Casual tone, German/English bilingual, mixes both naturally.

## The AI OS
A Notion-synced "second brain" vault, explicitly built for multi-project work and shareable across AI tools, not just Claude. Structural principle: reusable knowledge/capabilities stay central (`02_Systems/`, `03_Capabilities/`); project-specific execution lives in `10_Projects/` (ADR-0005). `04_Agents/` holds 5 scoped roles (Vault Architect, Content Producer, Research Analyst, Business Development, plus routing). **The old "agents are manual/chat-only" line is fully out of date:** as of 2026-08-30 those personas run unattended on systemd timers — routed automatically per task, scheduled, self-proposing a daily plan behind a 20:00 approval gate. The TaskRunner runs ~11 systemd units on Felix's Ubuntu server: the headless Open Interpreter worker, Telegram bridge, daily backup, health check, scheduler, morning brief (07:00), status updates (10/14/18/22), evening review (20:00), the Kleinanzeigen sniper, and the nightly DMARC prospector. A read-only Notion-backed MCP server lives at `AI-OSmcp/`; its Notion side has still never been exercised.

## Active Projects (10_Projects/)
- **DMARC remediation (leg 2, active)** — the primary revenue push. `TaskRunner/prospects/` holds 3,873 local business domains; a nightly DNS audit ranks them and 659 qualify as leads (no/weak DMARC + real mail flow). 533 have postal addresses (`money_board.py` reports both counts live — qualified and mailable are not the same number). `scripts/outreach.py` renders print-ready German letters (€249 fixed-price fix). Sells via postal mail — the one UWG §7-legal channel. OUTREACH_SENDER_* is filled in `.env` as of 2026-08-31. **Blocked only on: Felix printing a batch, posting it, and answering the calls — and the Gewerbeanmeldung before invoicing anyone.**
- **LocalArbitrage (leg 1, active)** — Kleinanzeigen sniper live since 2026-08-31, polling saved searches every 3 min, alerting via Telegram. €250 allocated. Broken-phone flip sub-loop added. **Blocked on: Felix acting on alerts + Gewerbeanmeldung before buying-to-resell.**
- **TemplateSales** — 3 products built (Micro-SaaS Moat Blueprint $29 **live since 2026-08-27**; Pricing Teardown $29 and Retention Engineering $39 **still unpublished**, plus a $45 bundle). All launch assets (Gumroad copy, cover.png, emails, Reddit posts) written. **Blocked on: Felix publishing the two remaining Gumroad/Notion listings, ~20 min each.**
- **QuickTurnaroundGigs** — Fiverr startup-competitor-analysis gig ($30/$80/$180) **live since 2026-08-27**. Omni Shield sample PDF finished. **Blocked on: attaching the sample to the live gig; no order has run yet.**
- **SocialMediaContent (leg 3, deferred)** — Horror archived 2026-08-13. Planned pivot: German-language security content as lead-gen for leg 2. No topic produced yet.
- **ContentAgency** — productized AI content for German B2B; no offer defined, not launched.
- **MoneyMaking** — the research umbrella that spawned the above; not execution.
- **FundingApplications** — **closed 2026-08-13, by choice.** Do not resurface as a "missed opportunity"; it was a decision.
- **CyberSecurityLearning / GetClean / Personal** — non-revenue personal projects.

Felix has a car (real competitive advantage for local arbitrage), multiple AI subscriptions, and has declined to pursue grant/free money by choice.

## Key Open Threads
**The bottleneck is now consistently the same:** every revenue stream is built and automated up to the point where only Felix can act — publishing the last 2 Gumroad listings, posting DMARC letters + answering calls, acting on sniper alerts, doing the Gewerbeanmeldung. The AI side is not the blocker anymore; Felix's time is. The Claude-Code-via-Pro-subscription ToS question is **decided** — a paid OpenRouter tier (GLM 5.2, budget-capped) is now the escalation path, so headless-off-Pro no longer gates anything. AI Video pillar undecided; security-content pivot planned not started.

**New as of 2026-09-02, not started — see [[00_System/Roadmap|Roadmap]]'s Backlog/Planned sections for detail:** (1) give the TaskRunner worker (`aios` engine) real session memory — `memory.py` already persists bounded per-thread memory, check whether it's actually wired into the webapp chat before building anything new; (2) a planned "Server Simplification Patch" — leaner host footprint for the laptop it runs on (surviving a later move to better infra), and less time/tokens per turn across the agents working this repo (Codex, Gemini, Claude). Rolls in two unresolved worker problems: it sometimes loop-locks and stops answering through the webapp, and free-tier answer quality is inconsistent — GLM-5.3 flagged as worth testing as an alternative.
